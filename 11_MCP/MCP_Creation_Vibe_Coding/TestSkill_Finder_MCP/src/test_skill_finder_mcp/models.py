"""The shapes the tools return, and the name matching every tool shares."""

from __future__ import annotations

import difflib
import json
import re
from collections.abc import Iterable
from typing import Any, Literal

from fastmcp.exceptions import ToolError
from pydantic import BaseModel, BeforeValidator, Field

Source = Literal["upstream", "local"]


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def flexible_list(field: str) -> BeforeValidator:
    """A list parameter that also takes what people type into a form field: one value, comma- or
    line-separated text, a JSON list as text, or the whole example ({field: [...]}) pasted into the box."""

    def coerce(value: Any) -> Any:
        if isinstance(value, dict):
            if set(value) != {field}:
                raise ValueError(f"The whole example seems to be pasted into the '{field}' field. Type only that "
                                 "field's value there, or turn on 'Edit as JSON' and paste the whole example.")
            value = value[field]
        if isinstance(value, str):
            text = value.strip()
            if text.startswith(("[", "{")):
                try:
                    return coerce(json.loads(text))
                except json.JSONDecodeError:
                    pass
            separator = "\n" if "\n" in text else ","
            return [part.strip().strip("'\"") for part in text.split(separator) if part.strip().strip("'\"")]
        return value

    return BeforeValidator(coerce)


def reject_pasted_example(value: str, field: str) -> None:
    """A text field that starts with '{' almost always holds the whole example pasted into one box."""
    if value.strip().startswith("{"):
        raise ToolError(f"The whole example seems to be pasted into the '{field}' field. Type only its value there, "
                        "or turn on 'Edit as JSON' and paste the whole example.")


def resolve(value: str, choices: Iterable[str], what: str) -> str:
    """Match what someone typed to one real value, or explain which values exist."""
    choices = list(choices)
    reject_pasted_example(value, what)
    by_norm = {norm(choice): choice for choice in choices}
    key = norm(value)
    if not key:
        raise ToolError(f"Empty {what}.")
    if key in by_norm:
        return by_norm[key]
    starts = [choice for n, choice in by_norm.items() if n.startswith(key)]
    if len(starts) == 1:
        return starts[0]
    inside = [choice for n, choice in by_norm.items() if key in n] if len(key) >= 3 else []
    if not starts and len(inside) == 1:
        return inside[0]
    if starts or inside:
        options = (starts or inside)[:10]
        raise ToolError(f"'{value}' matches several {what}s: {', '.join(options)}. Pick one.")
    close = [by_norm[n] for n in difflib.get_close_matches(key, list(by_norm), n=3, cutoff=0.5)]
    hint = f" Did you mean: {', '.join(close)}?" if close else ""
    listing = f" Valid values: {', '.join(choices)}." if len(choices) <= 30 else " Use list_skills or search_skills to find it."
    raise ToolError(f"Unknown {what} '{value}'.{hint}{listing}")


class SkillBrief(BaseModel):
    name: str
    title: str
    category: str
    summary: str = Field(description="The first sentence of the skill's description")
    source: Source = Field(description="'upstream' (PramodDutta/skillmasterclass) or 'local' (added in this repository)")


class SkillDetail(SkillBrief):
    description: str
    stlc_phase: str | None
    pack: str | None
    author: str
    version: str
    license: str
    path: str = Field(description="Folder of the skill inside skills/")
    files: list[str] = Field(description="Supporting files next to SKILL.md (templates, scripts, references)")
    content: str = Field(description="The whole SKILL.md")


class SearchHit(BaseModel):
    rank: int
    score: float
    matched: list[str] = Field(description="Words of the query this skill matched")
    why: str
    skill: SkillBrief


class SearchResult(BaseModel):
    query: str
    total_matches: int
    returned: int
    filters: dict[str, str]
    hits: list[SearchHit]
    note: str | None = Field(None, description="Set when the query was spell-corrected or nothing matched")


class FindResult(BaseModel):
    query: str
    exact: bool
    match: SkillBrief | None
    alternatives: list[SkillBrief]


class SkillList(BaseModel):
    total: int
    returned: int
    offset: int
    next_offset: int | None
    filters: dict[str, str]
    skills: list[SkillBrief]


class CategoryInfo(BaseModel):
    name: str
    kind: Literal["stlc-phase", "framework-pack", "domain-pack"]
    order: int
    folder: str
    skills: int
    skill_names: list[str]


class Overview(BaseModel):
    total_skills: int
    upstream_skills: int
    local_skills: int
    categories: int
    by_kind: dict[str, int]
    by_category: dict[str, int]
    upstream_repository: str
    upstream_commit: str
    upstream_synced_at: str
    loaded_at: str
    warnings: list[str]


class SkillFile(BaseModel):
    skill: str
    path: str
    size: int
    truncated: bool
    content: str


class BundleFile(BaseModel):
    path: str
    content: str


class SkillBundle(BaseModel):
    skill: str
    folder_name: str
    files: list[BundleFile]
    install: dict[str, str] = Field(description="Where to save the files for each client")


class RecommendedStep(BaseModel):
    step: int
    category: str
    why: str
    skill: SkillBrief


class Recommendation(BaseModel):
    task: str
    steps: list[RecommendedStep]
    note: str


class RelatedSkill(BaseModel):
    similarity: float
    skill: SkillBrief


class RelatedSkills(BaseModel):
    skill: str
    related: list[RelatedSkill]


class WorkflowPhase(BaseModel):
    order: int
    phase: str
    skills: list[SkillBrief]


class WorkflowPack(BaseModel):
    pack: str
    kind: str
    skills: list[SkillBrief]


class Workflow(BaseModel):
    flow: str
    phases: list[WorkflowPhase]
    packs: list[WorkflowPack]


class SkillProblem(BaseModel):
    skill: str
    problem: str


class ValidationReport(BaseModel):
    total: int
    valid: int
    problems: list[SkillProblem]


class SyncReport(BaseModel):
    repository: str
    branch: str
    commit: str
    applied: bool
    added: list[str]
    updated: list[str]
    removed: list[str]
    unchanged: int
    conflicts: list[str] = Field(description="Upstream files you changed locally; kept as they are unless force=true")
    notes: list[str]


class CreatedSkill(BaseModel):
    name: str
    category: str
    path: str
    warnings: list[str]
    content: str
