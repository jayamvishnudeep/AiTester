"""Downloads the upstream skills (PramodDutta/skillmasterclass) and merges them into skills/.

skills/.upstream.json records every file that came from upstream with its SHA-256 (line endings
ignored, so a CRLF checkout matches an LF original). A sync adds new upstream files, updates
changed ones and removes ones upstream deleted — but only when the local copy is still what was
downloaded. Files someone edited locally are
reported as conflicts and kept unless force=True. Skills added locally are never touched.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import tarfile
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from fastmcp.exceptions import ToolError

from .catalog import MANIFEST, read_manifest
from .models import SyncReport
from .settings import Settings

TIMEOUT = 60


def _download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "test-skill-finder-mcp"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise ToolError(f"Could not download {url}: {error}") from None


def _latest_commit(settings: Settings) -> str:
    """Best effort: the commit the branch points at (GitHub API, no token needed)."""
    try:
        data = _download(f"https://api.github.com/repos/{settings.upstream_repo}/commits/{settings.upstream_branch}")
        return json.loads(data)["sha"]
    except (ToolError, ValueError, KeyError):
        return "unknown"


def _safe(rel: str) -> bool:
    path = PurePosixPath(rel)
    return bool(rel) and not path.is_absolute() and ".." not in path.parts and "\\" not in rel and ":" not in rel


def fetch_upstream(settings: Settings) -> tuple[dict[str, bytes], str]:
    """Every file under the upstream skills folder, keyed by its path inside that folder."""
    archive = _download(f"https://codeload.github.com/{settings.upstream_repo}/tar.gz/refs/heads/{settings.upstream_branch}")
    prefix = settings.upstream_path.strip("/") + "/"
    files: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            inside_repo = "/".join(PurePosixPath(member.name).parts[1:])  # drop "<repo>-<branch>/"
            if not inside_repo.startswith(prefix):
                continue
            rel = inside_repo[len(prefix):]
            if _safe(rel) and rel != MANIFEST:
                extracted = tar.extractfile(member)
                if extracted is not None:
                    files[rel] = extracted.read()
    if not any(rel.endswith("SKILL.md") for rel in files):
        raise ToolError(f"No skills found under '{settings.upstream_path}' in {settings.upstream_repo}@{settings.upstream_branch}.")
    return files, _latest_commit(settings)


def _sha(data: bytes) -> str:
    """SHA-256 ignoring line endings: git on Windows checks files out with CRLF, elsewhere with LF."""
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def _local_sha(path: Path) -> str | None:
    return _sha(path.read_bytes()) if path.is_file() else None


@dataclass
class Plan:
    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    forced_writes: list[str] = field(default_factory=list)  # conflicts that force=True overwrites
    forced_removals: list[str] = field(default_factory=list)


def plan_sync(root: Path, upstream: dict[str, bytes], manifest: dict) -> Plan:
    known: dict[str, str] = manifest.get("files", {})
    plan = Plan()
    for rel, data in sorted(upstream.items()):
        new, local, recorded = _sha(data), _local_sha(root / rel), known.get(rel)
        if local == new:
            plan.unchanged.append(rel)
        elif local is None:
            plan.added.append(rel)
        elif recorded is not None and local == recorded:
            plan.updated.append(rel)  # upstream changed, local copy untouched since the last sync
        else:
            plan.conflicts.append(f"{rel}: changed locally" if recorded else f"{rel}: a local file with this name exists")
            plan.forced_writes.append(rel)
    for rel, recorded in sorted(known.items()):
        if rel in upstream:
            continue
        local = _local_sha(root / rel)
        if local is None:
            continue
        if local == recorded:
            plan.removed.append(rel)
        else:
            plan.conflicts.append(f"{rel}: removed upstream but changed locally")
            plan.forced_removals.append(rel)
    return plan


def sync(settings: Settings, apply: bool = False, force: bool = False) -> SyncReport:
    root = settings.skills_dir
    upstream, commit = fetch_upstream(settings)
    manifest = read_manifest(root)
    plan = plan_sync(root, upstream, manifest)
    notes = []
    if apply:
        writes = plan.added + plan.updated + (plan.forced_writes if force else [])
        removals = plan.removed + (plan.forced_removals if force else [])
        for rel in writes:
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(upstream[rel])
        for rel in removals:
            target = root / rel
            target.unlink(missing_ok=True)
            for parent in target.parents:  # drop folders the removal left empty
                if parent == root or any(parent.iterdir()):
                    break
                parent.rmdir()
        # Record what now matches upstream; conflicts kept locally keep their old entry, so the
        # next sync still reports them.
        files = dict(manifest.get("files", {}))
        for rel in plan.added + plan.updated + plan.unchanged + (plan.forced_writes if force else []):
            files[rel] = _sha(upstream[rel])
        for rel in removals:
            files.pop(rel, None)
        manifest.update({
            "repository": f"https://github.com/{settings.upstream_repo}",
            "path": settings.upstream_path, "branch": settings.upstream_branch, "commit": commit,
            "synced_at": dt.datetime.now().isoformat(timespec="seconds"), "files": files,
        })
        (root / MANIFEST).write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
        notes.append(f"Applied: {len(writes)} written, {len(removals)} removed.")
    else:
        notes.append("Dry run: nothing was changed. Call again with apply=true to make these changes.")
    if plan.conflicts and not force:
        notes.append("Conflicts were kept as they are locally; force=true overwrites them with upstream.")
    return SyncReport(
        repository=f"https://github.com/{settings.upstream_repo}", branch=settings.upstream_branch, commit=commit,
        applied=apply, added=plan.added, updated=plan.updated, removed=plan.removed, unchanged=len(plan.unchanged),
        conflicts=plan.conflicts, notes=notes,
    )
