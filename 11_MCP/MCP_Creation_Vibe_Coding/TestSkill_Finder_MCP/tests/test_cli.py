"""The tsf-mcp command line, apart from serving."""

import pytest

from test_skill_finder_mcp.__main__ import main


def test_validate_passes(capsys):
    with pytest.raises(SystemExit) as exited:
        main(["validate"])
    assert exited.value.code == 0
    assert "100/100 skills valid" in capsys.readouterr().out


def test_catalog_prints_a_markdown_table(capsys):
    main(["catalog"])
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("| # | Skill |") and len(lines) == 102
    assert "| 1 | `acceptance-criteria-writer` | Requirement Analysis | local |" in lines[2]


def test_a_missing_skills_folder_exits_with_a_message(monkeypatch, tmp_path):
    monkeypatch.setenv("TSF_SKILLS_DIR", str(tmp_path / "nowhere"))
    with pytest.raises(SystemExit, match="Skills folder not found"):
        main(["validate"])
