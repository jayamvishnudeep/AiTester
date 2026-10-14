"""Reads the skills folder — the source of truth — into a catalog, and reloads it when files change.

A skill is any folder holding a SKILL.md with YAML frontmatter (name, description, metadata).
Its category comes from where it lives: an STLC phase folder (01-requirement-analysis ...
07-test-closure) or a pack folder (framework-packs/<x>-pack, domain-packs/<x>-pack).
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import threading
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import yaml

from .models import CategoryInfo, SkillBrief, SkillDetail, resolve

STLC_PHASES = ("Requirement Analysis", "Test Planning", "Test Design", "Test Case Development",
               "Test Execution", "Defect Management", "Test Closure")
PACK_NAMES = {
    "playwright": "Playwright", "selenium": "Selenium", "cypress": "Cypress", "api": "API testing",
    "mobile": "Mobile", "performance": "Performance", "security": "Security",
    "llm-evaluation": "LLM evaluation", "ai-agents": "AI agents", "mcp": "MCP",
}
PACK_FOLDERS = ("framework-packs", "domain-packs")
MANIFEST = ".upstream.json"
REQUIRED_SECTIONS = ("When to use", "Workflow", "Output shape", "Guardrails")
FRONTMATTER = re.compile(r"\A---[ \t]*\n(?P<meta>.*?)\n---[ \t]*\n(?P<body>.*)\Z", re.S)
FIRST_SENTENCE = re.compile(r"^(.+?[.!?])(?:\s|$)")


class CatalogError(RuntimeError):
    """The skills folder is missing or unreadable."""


@dataclass(frozen=True)
class Skill:
    name: str
    title: str
    description: str
    folder: str  # e.g. "02-test-planning/test-plan-generator"
    category: str
    kind: str  # stlc-phase | framework-pack | domain-pack
    order: int  # position of the category: STLC phases 1-7, then the packs
    stlc_phase: str | None
    pack: str | None
    author: str
    version: str
    license: str
    source: str  # upstream | local
    body: str
    sections: tuple[tuple[str, str], ...]
    files: tuple[str, ...]  # supporting files next to SKILL.md
    content: str  # the whole SKILL.md

    @property
    def summary(self) -> str:
        match = FIRST_SENTENCE.match(self.description)
        return match.group(1) if match else self.description

    def section(self, heading: str) -> str:
        return next((text for title, text in self.sections if title.lower().startswith(heading.lower())), "")

    def brief(self) -> SkillBrief:
        return SkillBrief(name=self.name, title=self.title, category=self.category, summary=self.summary, source=self.source)

    def detail(self) -> SkillDetail:
        return SkillDetail(
            **self.brief().model_dump(), description=self.description, stlc_phase=self.stlc_phase, pack=self.pack,
            author=self.author, version=self.version, license=self.license, path=f"skills/{self.folder}",
            files=list(self.files), content=self.content,
        )


def classify(folder: str, metadata: dict) -> tuple[str, str, int, str | None, str | None]:
    """Category, kind, order, STLC phase and pack of a skill folder."""
    parts = folder.split("/")
    phase, pack = metadata.get("stlc-phase"), metadata.get("pack")
    if parts[0] in PACK_FOLDERS and len(parts) >= 3:
        pack = str(pack or parts[1].removesuffix("-pack"))
        kind = "framework-pack" if parts[0] == "framework-packs" else "domain-pack"
        order = 100 + (list(PACK_NAMES).index(pack) if pack in PACK_NAMES else 50)
        return f"{PACK_NAMES.get(pack, pack.replace('-', ' ').title())} pack", kind, order, phase, pack
    number = int(parts[0].split("-", 1)[0]) if parts[0][:2].isdigit() else 99
    phase = str(phase or (STLC_PHASES[number - 1] if 1 <= number <= len(STLC_PHASES) else parts[0]))
    return phase, "stlc-phase", number, phase, pack


def split_sections(body: str) -> tuple[tuple[str, str], ...]:
    sections, heading, lines = [], None, []
    for line in body.splitlines():
        if line.startswith("## "):
            if heading is not None:
                sections.append((heading, "\n".join(lines).strip()))
            heading, lines = line[3:].strip(), []
        elif heading is not None:
            lines.append(line)
    if heading is not None:
        sections.append((heading, "\n".join(lines).strip()))
    return tuple(sections)


def parse_skill(path: Path, root: Path, upstream_files: set[str]) -> Skill:
    content = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    match = FRONTMATTER.match(content)
    if not match:
        raise ValueError("SKILL.md has no YAML frontmatter between '---' lines")
    meta = yaml.safe_load(match["meta"]) or {}
    if not isinstance(meta, dict):
        raise ValueError("the frontmatter is not a YAML mapping")
    folder_path = path.parent
    folder = folder_path.relative_to(root).as_posix()
    metadata = meta.get("metadata") if isinstance(meta.get("metadata"), dict) else {}
    body = match["body"].strip()
    category, kind, order, phase, pack = classify(folder, metadata)
    return Skill(
        name=str(meta.get("name") or folder_path.name).strip(),
        title=next((line[2:].strip() for line in body.splitlines() if line.startswith("# ")), folder_path.name),
        description=" ".join(str(meta.get("description") or "").split()),
        folder=folder,
        category=category,
        kind=kind,
        order=order,
        stlc_phase=phase,
        pack=pack,
        author=str(metadata.get("author") or ""),
        version=str(metadata.get("version") or ""),
        license=str(meta.get("license") or ""),
        source="upstream" if f"{folder}/SKILL.md" in upstream_files else "local",
        body=body,
        sections=split_sections(body),
        files=tuple(sorted(p.relative_to(folder_path).as_posix() for p in folder_path.rglob("*")
                           if p.is_file() and p.name != "SKILL.md")),
        content=content,
    )


def read_manifest(root: Path) -> dict:
    try:
        return json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


class Catalog:
    """One snapshot of the skills folder."""

    def __init__(self, skills: list[Skill], root: Path, manifest: dict, warnings: list[str]):
        self.skills = tuple(sorted(skills, key=lambda s: (s.order, s.name)))
        self.by_name = {skill.name: skill for skill in self.skills}
        self.root = root
        self.manifest = manifest
        self.warnings = tuple(warnings)
        self.loaded_at = dt.datetime.now().isoformat(timespec="seconds")

    def find(self, name: str) -> Skill | None:
        """Exact name, ignoring case."""
        wanted = name.strip().lower()
        return next((skill for skill in self.skills if skill.name.lower() == wanted), None)

    def get(self, name: str) -> Skill:
        """Exact name, or the one skill a partial or misspelt name points to; ToolError otherwise."""
        return self.find(name) or self.by_name[resolve(name, self.by_name, "skill")]

    @cached_property
    def categories(self) -> list[CategoryInfo]:
        groups: dict[str, list[Skill]] = {}
        for skill in self.skills:
            groups.setdefault(skill.category, []).append(skill)
        return [
            CategoryInfo(name=name, kind=members[0].kind, order=members[0].order,
                         folder=members[0].folder.rsplit("/", 1)[0], skills=len(members),
                         skill_names=[s.name for s in members])
            for name, members in sorted(groups.items(), key=lambda item: item[1][0].order)
        ]

    def category(self, name: str) -> CategoryInfo:
        chosen = resolve(name, [c.name for c in self.categories], "category")
        return next(c for c in self.categories if c.name == chosen)

    @cached_property
    def search_index(self):
        from .search import SearchIndex  # built once per snapshot, on first use

        return SearchIndex(self.skills)


def load_catalog(root: Path) -> Catalog:
    if not root.is_dir():
        raise CatalogError(f"Skills folder not found: {root}. Set TSF_SKILLS_DIR to the folder that holds the skills.")
    manifest = read_manifest(root)
    upstream_files = set(manifest.get("files", {}))
    skills: list[Skill] = []
    warnings: list[str] = []
    seen: dict[str, str] = {}
    for path in sorted(root.rglob("SKILL.md")):
        folder = path.parent.relative_to(root).as_posix()
        try:
            skill = parse_skill(path, root, upstream_files)
        except (ValueError, yaml.YAMLError, UnicodeDecodeError) as error:
            warnings.append(f"{folder}: {error}")
            continue
        if skill.name in seen:
            warnings.append(f"{folder}: the name '{skill.name}' is already used by {seen[skill.name]}; skipped")
            continue
        seen[skill.name] = folder
        skills.append(skill)
    return Catalog(skills, root, manifest, warnings)


def _stamp(root: Path) -> tuple[int, int, int]:
    count = newest = size = 0
    for folder, _, files in os.walk(root):
        for name in files:
            try:
                stat = os.stat(os.path.join(folder, name))
            except OSError:
                continue
            count, size, newest = count + 1, size + stat.st_size, max(newest, stat.st_mtime_ns)
    return count, newest, size


class CatalogStore:
    """Hands out the current snapshot and rebuilds it when anything in the skills folder changes."""

    def __init__(self, root: Path):
        self.root = root
        self._lock = threading.Lock()
        self._catalog: Catalog | None = None
        self._stamp: tuple | None = None

    def get(self) -> Catalog:
        stamp = _stamp(self.root)
        if self._catalog is None or stamp != self._stamp:
            with self._lock:
                stamp = _stamp(self.root)
                if self._catalog is None or stamp != self._stamp:
                    self._catalog = load_catalog(self.root)
                    self._stamp = stamp
        return self._catalog
