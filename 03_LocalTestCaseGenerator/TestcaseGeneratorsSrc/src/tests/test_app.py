from __future__ import annotations

from app import build_prompt, load_template


def test_load_template_reads_existing_template():
    assert "Generate [NUMBER] test cases" in load_template()


def test_build_prompt_merges_ticket_content_into_template():
    prompt = build_prompt("FORMAT: table", "PROJ-1", "Summary", "Description", "Criteria")
    assert "FORMAT: table" in prompt
    assert "PROJ-1" in prompt
    assert "Summary" in prompt
    assert "Criteria" in prompt
