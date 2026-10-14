"""Checks every skill against the house format, and scaffolds new skills in that format."""

from __future__ import annotations

import re
import textwrap

from fastmcp.exceptions import ToolError

from .catalog import PACK_NAMES, REQUIRED_SECTIONS, STLC_PHASES, Catalog
from .models import CreatedSkill, SkillProblem, ValidationReport

NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate(catalog: Catalog) -> ValidationReport:
    problems = [SkillProblem(skill=w.split(":", 1)[0], problem=w.split(":", 1)[1].strip()) for w in catalog.warnings]
    for skill in catalog.skills:
        folder_name = skill.folder.rsplit("/", 1)[-1]
        if skill.name != folder_name:
            problems.append(SkillProblem(skill=skill.name, problem=f"name differs from its folder '{folder_name}'"))
        if not NAME.match(skill.name):
            problems.append(SkillProblem(skill=skill.name, problem="name is not lower-case kebab-case"))
        if len(skill.description) < 40:
            problems.append(SkillProblem(skill=skill.name, problem="description is missing or shorter than 40 characters"))
        if skill.kind == "stlc-phase" and not 1 <= skill.order <= len(STLC_PHASES):
            problems.append(SkillProblem(skill=skill.name, problem="not in an STLC phase folder (01-requirement-analysis "
                                         "... 07-test-closure) or a pack folder (framework-packs/<x>-pack, "
                                         "domain-packs/<x>-pack)"))
        for heading in REQUIRED_SECTIONS:
            if not any(title.lower().startswith(heading.lower()) for title, _ in skill.sections):
                problems.append(SkillProblem(skill=skill.name, problem=f"missing the '## {heading}' section"))
    bad = {p.skill for p in problems}
    return ValidationReport(total=len(catalog.skills) + len(catalog.warnings),
                            valid=sum(1 for s in catalog.skills if s.name not in bad), problems=problems)


def _bullets(items: list[str], numbered: bool = False) -> str:
    cleaned = [" ".join(item.split()) for item in items if item and item.strip()]
    return "\n".join(f"{n}. {item}" if numbered else f"- {item}" for n, item in enumerate(cleaned, 1))


def create(catalog: Catalog, name: str, category: str, description: str, when_to_use: list[str], workflow: list[str],
           output_shape: str, guardrails: list[str], title: str | None = None, summary: str | None = None,
           author: str = "AiTester") -> CreatedSkill:
    name = name.strip().lower()
    errors, warnings = [], []
    if not NAME.match(name) or not 3 <= len(name) <= 64:
        errors.append("name must be lower-case kebab-case, 3-64 characters, e.g. 'k6-soak-tester'")
    if catalog.find(name):
        errors.append(f"a skill named '{name}' already exists ({catalog.find(name).folder})")
    target = catalog.category(category)  # ToolError with suggestions when unknown
    description = " ".join(description.split())
    if len(description) < 40:
        errors.append("description must say what the skill does and when to use it (at least 40 characters)")
    elif "use when" not in description.lower():
        warnings.append("descriptions usually include 'Use when ...' with the phrases that should trigger the skill")
    for label, items in (("when_to_use", when_to_use), ("workflow", workflow), ("guardrails", guardrails)):
        if not [i for i in items if i and i.strip()]:
            errors.append(f"{label} needs at least one item")
    if not output_shape.strip():
        errors.append("output_shape needs an example of what the skill produces")
    if errors:
        raise ToolError("The skill was not created:\n- " + "\n- ".join(errors))

    if target.kind == "stlc-phase":
        classifier = f"stlc-phase: {target.name}"
    else:
        pack = next((k for k, v in PACK_NAMES.items() if f"{v} pack" == target.name), target.folder.rsplit("/", 1)[-1].removesuffix("-pack"))
        classifier = f"pack: {pack}"
    folded = textwrap.fill(description, width=90, initial_indent="  ", subsequent_indent="  ")
    title = (title or name.replace("-", " ").title()).strip()
    summary = " ".join((summary or description.split(". ")[0].rstrip(".") + ".").split())
    content = (
        f"---\nname: {name}\ndescription: >-\n{folded}\nlicense: MIT\nmetadata:\n  author: {author}\n"
        f"  {classifier}\n  version: 1.0.0\n---\n\n# {title}\n\n{summary}\n\n"
        f"## When to use\n{_bullets(when_to_use)}\n\n## Workflow\n{_bullets(workflow, numbered=True)}\n\n"
        f"## Output shape\n```\n{output_shape.strip()}\n```\n\n## Guardrails\n{_bullets(guardrails)}\n"
    )
    folder = catalog.root / target.folder / name
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "SKILL.md").write_text(content, encoding="utf-8", newline="\n")
    return CreatedSkill(name=name, category=target.name, path=f"skills/{target.folder}/{name}/SKILL.md",
                        warnings=warnings, content=content)
