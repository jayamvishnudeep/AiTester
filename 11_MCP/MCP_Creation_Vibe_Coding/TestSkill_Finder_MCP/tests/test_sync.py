"""Syncing from upstream with a fake GitHub archive: what is added, updated, removed or kept."""

import io
import json
import tarfile

import pytest
from fastmcp.exceptions import ToolError

from conftest import make_settings
from test_skill_finder_mcp import sync
from test_skill_finder_mcp.catalog import MANIFEST, read_manifest

PREFIX = "skillmasterclass-main/skillmasterclass/skills/"
PLAN = "02-test-planning/test-plan-generator/SKILL.md"
TEMPLATE = "02-test-planning/test-plan-generator/references/test-plan-template.md"
BUG = "06-defect-management/bug-reporter/SKILL.md"


def archive(files: dict[str, bytes], extra: dict[str, bytes] | None = None) -> bytes:
    """A tar.gz shaped like GitHub's: everything under '<repo>-<branch>/'."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, data in {**{PREFIX + rel: data for rel, data in files.items()}, **(extra or {})}.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


@pytest.fixture
def upstream(monkeypatch):
    """What GitHub serves; tests change it, then sync."""
    state = {"files": {PLAN: b"plan v1\n", TEMPLATE: b"template v1\n", BUG: b"bug v1\n"}, "extra": {}}

    def download(url: str) -> bytes:
        if "codeload.github.com" in url:
            return archive(state["files"], state["extra"])
        return json.dumps({"sha": "c0ffee" * 6 + "abcd"}).encode()

    monkeypatch.setattr(sync, "_download", download)
    return state


@pytest.fixture
def settings(tmp_path):
    root = tmp_path / "skills"
    root.mkdir()
    return make_settings(root)


def test_first_sync_adds_everything_and_records_it(settings, upstream):
    dry = sync.sync(settings)
    assert dry.added == sorted(upstream["files"]) and not dry.applied
    assert not (settings.skills_dir / PLAN).exists()  # a dry run writes nothing

    report = sync.sync(settings, apply=True)
    assert report.applied and report.commit.startswith("c0ffee")
    assert (settings.skills_dir / PLAN).read_bytes() == b"plan v1\n"
    manifest = read_manifest(settings.skills_dir)
    assert set(manifest["files"]) == set(upstream["files"])
    assert manifest["repository"] == "https://github.com/PramodDutta/skillmasterclass"

    again = sync.sync(settings, apply=True)
    assert again.unchanged == 3 and again.added == again.updated == again.removed == again.conflicts == []


def test_an_untouched_file_follows_upstream(settings, upstream):
    sync.sync(settings, apply=True)
    upstream["files"][PLAN] = b"plan v2\n"
    report = sync.sync(settings, apply=True)
    assert report.updated == [PLAN]
    assert (settings.skills_dir / PLAN).read_bytes() == b"plan v2\n"


def test_a_local_edit_is_kept_unless_forced(settings, upstream):
    sync.sync(settings, apply=True)
    (settings.skills_dir / PLAN).write_bytes(b"my own plan\n")
    upstream["files"][PLAN] = b"plan v2\n"

    kept = sync.sync(settings, apply=True)
    assert kept.conflicts == [f"{PLAN}: changed locally"] and kept.updated == []
    assert (settings.skills_dir / PLAN).read_bytes() == b"my own plan\n"
    assert sync.sync(settings).conflicts == kept.conflicts  # still reported next time

    forced = sync.sync(settings, apply=True, force=True)
    assert forced.conflicts == kept.conflicts
    assert (settings.skills_dir / PLAN).read_bytes() == b"plan v2\n"
    assert sync.sync(settings).conflicts == []


def test_a_file_upstream_deleted_goes_unless_edited(settings, upstream):
    sync.sync(settings, apply=True)
    del upstream["files"][TEMPLATE]
    report = sync.sync(settings, apply=True)
    assert report.removed == [TEMPLATE]
    assert not (settings.skills_dir / TEMPLATE).exists()
    assert not (settings.skills_dir / TEMPLATE).parent.exists()  # the emptied folder goes too
    assert TEMPLATE not in read_manifest(settings.skills_dir)["files"]

    (settings.skills_dir / BUG).write_bytes(b"my bug notes\n")
    del upstream["files"][BUG]
    kept = sync.sync(settings, apply=True)
    assert kept.conflicts == [f"{BUG}: removed upstream but changed locally"]
    assert (settings.skills_dir / BUG).exists()


def test_line_endings_are_not_local_edits(settings, upstream):
    sync.sync(settings, apply=True)
    plan = settings.skills_dir / PLAN
    plan.write_bytes(plan.read_bytes().replace(b"\n", b"\r\n"))  # what git on Windows checks out
    assert sync.sync(settings).conflicts == []
    upstream["files"][PLAN] = b"plan v2\n"
    assert sync.sync(settings, apply=True).updated == [PLAN]


def test_local_skills_are_never_touched(settings, upstream):
    mine = settings.skills_dir / "03-test-design/my-skill/SKILL.md"
    mine.parent.mkdir(parents=True)
    mine.write_bytes(b"mine\n")
    sync.sync(settings, apply=True, force=True)
    assert mine.read_bytes() == b"mine\n"


def test_a_local_file_where_upstream_adds_one_is_a_conflict(settings, upstream):
    clash = settings.skills_dir / BUG
    clash.parent.mkdir(parents=True)
    clash.write_bytes(b"written here first\n")
    report = sync.sync(settings, apply=True)
    assert report.conflicts == [f"{BUG}: a local file with this name exists"]
    assert clash.read_bytes() == b"written here first\n"


def test_unsafe_paths_in_the_archive_are_ignored(settings, upstream):
    upstream["extra"] = {PREFIX + "../escape.md": b"x", PREFIX + MANIFEST: b"{}", "elsewhere/README.md": b"x"}
    report = sync.sync(settings, apply=True)
    assert sorted(report.added) == sorted(upstream["files"])
    assert not (settings.skills_dir.parent / "escape.md").exists()


def test_an_archive_without_skills_is_refused(settings, upstream):
    upstream["files"] = {"README.md": b"nothing here"}
    with pytest.raises(ToolError, match="No skills found"):
        sync.sync(settings)


def test_the_commit_is_best_effort(settings, upstream, monkeypatch):
    real = sync._download

    def no_api(url: str) -> bytes:
        if "api.github.com" in url:
            raise ToolError("rate limited")
        return real(url)

    monkeypatch.setattr(sync, "_download", no_api)
    assert sync.sync(settings).commit == "unknown"
