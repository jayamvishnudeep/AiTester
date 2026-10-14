"""The Test Skill Finder MCP server: QA and test-automation skills as tools, resources and prompts.

The skills folder is the source of truth; every tool reads it fresh when it changes. Every
tool description ends with an example input, so people browsing the tools (for example in MCP
Inspector) see how to call them.
"""

# No `from __future__ import annotations`: the tools are defined inside build_server, and
# FastMCP must be able to read their parameter types.

import json
from pathlib import PurePosixPath
from typing import Annotated, Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ResourceError, ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from . import __version__, authoring
from .catalog import CatalogStore
from .models import (
    BundleFile, CategoryInfo, CreatedSkill, FindResult, Overview, RecommendedStep, Recommendation, RelatedSkill,
    RelatedSkills, SearchHit, SearchResult, SkillBundle, SkillDetail, SkillFile, SkillList, SyncReport,
    ValidationReport, Workflow, WorkflowPack, WorkflowPhase, flexible_list, reject_pasted_example,
)
from .search import words
from .settings import Settings, load_settings
from .sync import sync as run_sync

READ = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
CREATE = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False)
SYNC = ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=True, open_world_hint=True)
MAX_FILE = 200_000
RECOMMEND_FLOOR = 0.5
UI_FRAMEWORKS = {"Playwright pack": "playwright", "Selenium pack": "selenium", "Cypress pack": "cypress"}


def flow_position(skill) -> float:
    """Where a skill sits in the testing flow: its STLC phase, or execution for the packs (5.5 sits
    between Test Execution and Defect Management)."""
    return skill.order if skill.kind == "stlc-phase" else 5.5


INSTRUCTIONS = """\
Test Skill Finder serves {count} QA and test-automation skills (Agent Skills: a SKILL.md with instructions per skill):
the STLC phases (requirement analysis, test planning, test design, test cases, execution, defects, closure) plus
packs for Playwright, Selenium, Cypress, API testing, mobile, performance, security, LLM evaluation, AI agents and MCP.

- Find a skill by keyword: search_skills ("playwright api", "test case creator", "bug report", "prompt injection").
- Know the name roughly: find_skill. Browse: list_categories, list_skills, get_stlc_workflow.
- Plan a whole task across phases: recommend_skills. Similar skills: related_skills.
- Use a skill: get_skill returns the full SKILL.md to follow; get_skill_file reads its templates and scripts;
  download_skill returns every file to install it (for example under ~/.claude/skills/<name>/).
- Maintain the library: validate_skills, create_skill (new skill in the house format), sync_upstream_skills
  (pull updates from github.com/PramodDutta/skillmasterclass; dry run unless apply=true).
"""

SkillName = Annotated[str, Field(description="Skill name, e.g. 'pw-api-tester'. Case-insensitive; a unique part of the name works.",
                                 examples=["pw-api-tester"])]
Category = Annotated[str | None, Field(description="A category from list_categories, e.g. 'Test Planning' or 'Cypress pack'.",
                                       examples=["Cypress pack"])]
SourceFilter = Annotated[Literal["upstream", "local"] | None,
                         Field(description="'upstream' = from PramodDutta/skillmasterclass, 'local' = added in this repository.")]


def build_server(settings: Settings | None = None) -> FastMCP:
    settings = settings or load_settings()
    store = CatalogStore(settings.skills_dir)
    count = len(store.get().skills)  # fails at start-up, not on the first call, when the folder is missing
    mcp = FastMCP("Test Skill Finder", instructions=INSTRUCTIONS.format(count=count), version=__version__)

    def category_filter(catalog, category, source):
        chosen = catalog.category(category).name if category else None
        filters = {k: v for k, v in (("category", chosen), ("source", source)) if v}
        return (lambda s: (not chosen or s.category == chosen) and (not source or s.source == source)), filters

    def run_search(catalog, query, allowed=lambda skill: True):
        """Search hits, the query actually used, and a note: the spelling it corrected, or that nothing matched."""
        index = catalog.search_index
        hits, note = index.search(query, allowed), None
        corrected = index.correct(query)
        if corrected and (fixed := index.search(corrected, allowed)):
            hits, query, note = fixed, corrected, f"Showing results for '{corrected}' (corrected from '{query}')."
        if not hits:
            note = ("No skill matches. Try broader words (for example 'api', 'performance', 'bug report'), "
                    "drop the filters, or browse with list_categories.")
        if hits and "stlc" in words(query):
            note = " ".join(filter(None, [note, "Tip: get_stlc_workflow lists every STLC phase with its skills."]))
        return hits, query, note

    # --- Finding skills -----------------------------------------------------------------

    @mcp.tool(title="Search skills by keyword", annotations=READ, tags={"find"})
    def search_skills(
        query: Annotated[str, Field(min_length=1, description="Keywords or a short task, e.g. 'playwright api' or 'write test cases'.",
                                    examples=["playwright api"])],
        category: Category = None,
        source: SourceFilter = None,
        limit: Annotated[int, Field(ge=1, le=25, description="How many skills to return (1-25).")] = 5,
    ) -> SearchResult:
        """Skills that match keywords, best first, with what matched. Understands QA shorthand: pw = Playwright,
        bug = defect, creator/generator/writer = create, so "test case creator" finds test-case-writer.

        Example input (paste with 'Edit as JSON' on):
        {"query": "playwright api", "limit": 5}

        Returns: ranked hits, each with a score, the words it matched, why, and the skill's name, title,
        category and one-line summary.
        """
        reject_pasted_example(query, "query")
        catalog = store.get()
        allowed, filters = category_filter(catalog, category, source)
        hits, _, note = run_search(catalog, query, allowed)
        return SearchResult(
            query=query, total_matches=len(hits), returned=min(limit, len(hits)), filters=filters,
            hits=[SearchHit(rank=n, score=score, matched=matched, why=why, skill=skill.brief())
                  for n, (skill, score, matched, why) in enumerate(hits[:limit], 1)],
            note=note,
        )

    @mcp.tool(title="Find a skill by name", annotations=READ, tags={"find"})
    def find_skill(name: Annotated[str, Field(min_length=1, description="The name, or part of it, e.g. 'test plan generator'.",
                                              examples=["test plan generator"])]) -> FindResult:
        """The skill with this name, ignoring case, dashes and spelling slips; or the closest alternatives.

        Example input (paste with 'Edit as JSON' on):
        {"name": "test plan generator"}

        Returns: exact (true or false), the matched skill, and alternatives worth a look.
        """
        reject_pasted_example(name, "name")
        catalog = store.get()
        exact = catalog.find(name) or catalog.find("-".join(name.split()))
        try:
            match = exact or catalog.get(name)
        except ToolError:
            match = None  # no single skill: the alternatives below say what is close
        hits = [s for s, *_ in catalog.search_index.search(name)]
        alternatives = [s.brief() for s in hits if not match or s.name != match.name][:5]
        return FindResult(query=name, exact=exact is not None, match=match.brief() if match else None,
                          alternatives=alternatives)

    @mcp.tool(title="Recommend skills for a task", annotations=READ, tags={"find"})
    def recommend_skills(
        task: Annotated[str, Field(min_length=3, description="What you need to do, in plain words.",
                                   examples=["test the new checkout API before the release"])],
        limit: Annotated[int, Field(ge=1, le=10, description="How many steps (1-10).")] = 5,
    ) -> Recommendation:
        """The skills a task needs, as steps in the order testing flows: requirements, planning, design,
        test cases, execution (where the Playwright, Selenium, Cypress, API, mobile, performance, security,
        LLM, agent and MCP packs come in), defects, closure.

        Example input (paste with 'Edit as JSON' on):
        {"task": "test the new checkout API before the release", "limit": 5}

        Returns: numbered steps, each with the category, the skill and why it fits.
        """
        reject_pasted_example(task, "task")
        hits, used, note = run_search(store.get(), task)
        if not hits:
            raise ToolError(note)
        named = {category for category, word in UI_FRAMEWORKS.items() if word in words(used)}
        if named:  # "... with playwright" should not get Cypress or Selenium steps
            hits = [hit for hit in hits if hit[0].category not in UI_FRAMEWORKS or hit[0].category in named]
        floor = hits[0][1] * RECOMMEND_FLOOR  # only skills that fit nearly as well as the best one
        chosen = [hit for hit in hits if hit[1] >= floor][:limit]
        chosen.sort(key=lambda hit: (flow_position(hit[0]), hit[0].order, -hit[1]))
        return Recommendation(
            task=task,
            steps=[RecommendedStep(step=n, category=skill.category, why=why, skill=skill.brief())
                   for n, (skill, score, matched, why) in enumerate(chosen, 1)],
            note=" ".join(filter(None, [note, "Steps are in testing order. Open each with get_skill, or apply one "
                                              "with the use_skill prompt."])),
        )

    @mcp.tool(title="Related skills", annotations=READ, tags={"find"})
    def related_skills(name: SkillName, limit: Annotated[int, Field(ge=1, le=10, description="How many (1-10).")] = 5) -> RelatedSkills:
        """Skills most similar to this one, by the words they use, for "what else should I look at".

        Example input (paste with 'Edit as JSON' on):
        {"name": "pw-flaky-debugger", "limit": 5}

        Returns: related skills with a similarity score from 0 to 1.
        """
        catalog = store.get()
        skill = catalog.get(name)
        return RelatedSkills(skill=skill.name, related=[RelatedSkill(similarity=sim, skill=s.brief())
                                                        for s, sim in catalog.search_index.related(skill.name, limit)])

    # --- Browsing ------------------------------------------------------------------------

    @mcp.tool(title="Catalog overview", annotations=READ, tags={"browse"})
    def get_catalog_overview() -> Overview:
        """How many skills there are, where they come from, and how many each category holds.

        Example input (paste with 'Edit as JSON' on):
        {}

        Returns: totals, counts per kind and category, and the upstream commit the skills were synced from.
        """
        catalog = store.get()
        by_kind: dict[str, int] = {}
        for skill in catalog.skills:
            by_kind[skill.kind] = by_kind.get(skill.kind, 0) + 1
        upstream = sum(1 for s in catalog.skills if s.source == "upstream")
        return Overview(
            total_skills=len(catalog.skills), upstream_skills=upstream, local_skills=len(catalog.skills) - upstream,
            categories=len(catalog.categories), by_kind=by_kind, by_category={c.name: c.skills for c in catalog.categories},
            upstream_repository=catalog.manifest.get("repository", "none"),
            upstream_commit=str(catalog.manifest.get("commit", "unknown"))[:12],
            upstream_synced_at=catalog.manifest.get("synced_at", "never"),
            loaded_at=catalog.loaded_at, warnings=list(catalog.warnings),
        )

    @mcp.tool(title="Categories", annotations=READ, tags={"browse"})
    def list_categories() -> list[CategoryInfo]:
        """The 7 STLC phases in order, then the framework packs and domain packs, with their skills.

        Example input (paste with 'Edit as JSON' on):
        {}

        Returns: one entry per category: name, kind, folder, number of skills and their names.
        """
        return store.get().categories

    @mcp.tool(title="List skills", annotations=READ, tags={"browse"})
    def list_skills(
        category: Category = None,
        source: SourceFilter = None,
        limit: Annotated[int, Field(ge=1, le=100, description="Most skills to return (1-100).")] = 50,
        offset: Annotated[int, Field(ge=0, description="Skip this many; pass next_offset from the previous reply.")] = 0,
    ) -> SkillList:
        """All skills, or the skills of one category, in testing order.

        Example input (paste with 'Edit as JSON' on):
        {"category": "Cypress pack"}

        Returns: the skills (name, title, category, summary, source) with paging.
        """
        catalog = store.get()
        allowed, filters = category_filter(catalog, category, source)
        skills = [s for s in catalog.skills if allowed(s)]
        chunk = skills[offset : offset + limit]
        end = offset + len(chunk)
        return SkillList(total=len(skills), returned=len(chunk), offset=offset,
                         next_offset=end if end < len(skills) else None, filters=filters,
                         skills=[s.brief() for s in chunk])

    @mcp.tool(title="STLC workflow", annotations=READ, tags={"browse"})
    def get_stlc_workflow() -> Workflow:
        """The testing life cycle in order, with the skills for each phase, and the packs that plug into it.

        Example input (paste with 'Edit as JSON' on):
        {}

        Returns: the flow, the 7 phases with their skills, and the framework and domain packs.
        """
        catalog = store.get()
        phases = [WorkflowPhase(order=c.order, phase=c.name, skills=[catalog.by_name[n].brief() for n in c.skill_names])
                  for c in catalog.categories if c.kind == "stlc-phase"]
        packs = [WorkflowPack(pack=c.name, kind=c.kind, skills=[catalog.by_name[n].brief() for n in c.skill_names])
                 for c in catalog.categories if c.kind != "stlc-phase"]
        flow = ("Requirement Analysis → Test Planning → Test Design → Test Case Development → Test Execution "
                "(Playwright, Selenium, Cypress, API, mobile packs) → Defect Management → Test Closure. "
                "Performance, security, LLM evaluation, AI agents and MCP packs plug into planning, design and execution. "
                "Every skill stops at a human-review gate.")
        return Workflow(flow=flow, phases=phases, packs=packs)

    # --- Using a skill ---------------------------------------------------------------------

    @mcp.tool(title="Get a skill", annotations=READ, tags={"use"})
    def get_skill(name: SkillName) -> SkillDetail:
        """The whole skill: its SKILL.md (instructions to follow), metadata and the list of supporting files.

        Example input (paste with 'Edit as JSON' on):
        {"name": "test-plan-generator"}

        Returns: name, title, category, description, author, version, path, files and the full SKILL.md content.
        """
        return store.get().get(name).detail()

    @mcp.tool(title="Read a skill's supporting file", annotations=READ, tags={"use"})
    def get_skill_file(
        name: SkillName,
        path: Annotated[str, Field(description="A path from the skill's files list, e.g. 'references/test-plan-template.md'.",
                                   examples=["references/test-plan-template.md"])],
    ) -> SkillFile:
        """One template, checklist, script or prompt file that ships with a skill.

        Example input (paste with 'Edit as JSON' on):
        {"name": "test-plan-generator", "path": "references/test-plan-template.md"}

        Returns: the file's text (up to 200 KB) and its size.
        """
        reject_pasted_example(path, "path")
        catalog = store.get()
        skill = catalog.get(name)
        wanted = PurePosixPath(path.strip().replace("\\", "/")).as_posix()
        known = ("SKILL.md", *skill.files)
        # Forgiving: the full repository path or just the file name works too, when it is unique.
        candidates = [f for f in known if wanted == f or wanted.endswith("/" + f)] or \
                     [f for f in known if PurePosixPath(f).name == wanted]
        if len(candidates) > 1:
            raise ToolError(f"'{path}' matches several files of {skill.name}: {', '.join(candidates)}. Give the full path.")
        if not candidates:
            raise ToolError(f"{skill.name} has no file '{path}'. Its files: {', '.join(known)}.")
        wanted = candidates[0]
        data = (catalog.root / skill.folder / wanted).read_bytes()
        text = data[:MAX_FILE].decode("utf-8", errors="replace")
        return SkillFile(skill=skill.name, path=wanted, size=len(data), truncated=len(data) > MAX_FILE, content=text)

    @mcp.tool(title="Download a skill", annotations=READ, tags={"use"})
    def download_skill(name: SkillName) -> SkillBundle:
        """Every file of a skill, ready to save, with where to put them for Claude Code and GitHub Copilot.

        Example input (paste with 'Edit as JSON' on):
        {"name": "test-plan-generator"}

        Returns: the files (path and text) and install instructions.
        """
        catalog = store.get()
        skill = catalog.get(name)
        files = [BundleFile(path="SKILL.md", content=skill.content)]
        for rel in skill.files:
            data = (catalog.root / skill.folder / rel).read_bytes()
            files.append(BundleFile(path=rel, content=data[:MAX_FILE].decode("utf-8", errors="replace")))
        return SkillBundle(
            skill=skill.name, folder_name=skill.name, files=files,
            install={
                "claude_code_personal": f"Save the files under ~/.claude/skills/{skill.name}/ (keep the folder layout).",
                "claude_code_project": f"Save the files under .claude/skills/{skill.name}/ in the repository.",
                "github_copilot": f"Copy the body of SKILL.md into .github/prompts/{skill.name}.prompt.md.",
                "from_this_repository": f"cp -r skills/{skill.folder} ~/.claude/skills/",
            },
        )

    # --- Maintaining the library -------------------------------------------------------------

    @mcp.tool(title="Validate all skills", annotations=READ, tags={"maintain"})
    def validate_skills() -> ValidationReport:
        """Checks every skill against the house format: frontmatter, name equals folder, description, a phase or
        pack, and the When to use, Workflow, Output shape and Guardrails sections.

        Example input (paste with 'Edit as JSON' on):
        {}

        Returns: totals and one line per problem found.
        """
        return authoring.validate(store.get())

    @mcp.tool(title="Create a skill", annotations=CREATE, tags={"write"})
    def create_skill(
        name: Annotated[str, Field(description="New kebab-case name, e.g. 'k6-soak-tester'.", examples=["k6-soak-tester"])],
        category: Annotated[str, Field(description="An existing category, e.g. 'Performance pack' or 'Test Design'.",
                                       examples=["Performance pack"])],
        description: Annotated[str, Field(description="What it does and 'Use when ...' with the phrases that should trigger it.")],
        when_to_use: Annotated[list[str], flexible_list("when_to_use"), Field(min_length=1, description='Situations, e.g. ["A service must run for days"].')],
        workflow: Annotated[list[str], flexible_list("workflow"), Field(min_length=1, description="Steps in order.")],
        output_shape: Annotated[str, Field(description="An example of what the skill produces.")],
        guardrails: Annotated[list[str], flexible_list("guardrails"), Field(min_length=1, description="What it must never do.")],
        title: Annotated[str | None, Field(description="Heading; defaults to the name in title case.")] = None,
        summary: Annotated[str | None, Field(description="One line under the heading; defaults to the first sentence of the description.")] = None,
    ) -> CreatedSkill:
        """Adds a new skill to the skills folder in the house format (frontmatter + the four sections). It is
        searchable at once.

        Example input (paste with 'Edit as JSON' on):
        {"name": "k6-soak-tester", "category": "Performance pack",
         "description": "Plans and scripts k6 soak tests that run for hours to find memory leaks. Use when a team says 'run a soak test' or 'does it leak under load'.",
         "when_to_use": ["A service must run for days without a restart."],
         "workflow": ["Agree the duration and load.", "Script it in k6 with a constant arrival rate.", "Watch memory and connections over time."],
         "output_shape": "k6 script plus a memory trend per hour",
         "guardrails": ["Never run against production without approval."]}

        Returns: the new skill's name, category, path, warnings and its SKILL.md.
        """
        return authoring.create(store.get(), name, category, description, when_to_use, workflow, output_shape,
                                guardrails, title, summary)

    @mcp.tool(title="Sync upstream skills from GitHub", annotations=SYNC, tags={"write"})
    def sync_upstream_skills(
        apply: Annotated[bool, Field(description="false = dry run that only reports; true = write the changes.")] = False,
        force: Annotated[bool, Field(description="Also overwrite upstream files that were edited locally.")] = False,
    ) -> SyncReport:
        """Downloads the latest skills from github.com/PramodDutta/skillmasterclass and merges them into the skills
        folder. Skills added locally are never touched; upstream files edited locally are kept unless force=true.

        Example input (paste with 'Edit as JSON' on):
        {"apply": false}

        Returns: the upstream commit and the files added, updated, removed, unchanged and in conflict.
        """
        return run_sync(settings, apply=apply, force=force)

    # --- Resources -----------------------------------------------------------------------------

    @mcp.resource("skills://catalog", name="catalog", title="Skill catalog", mime_type="application/json",
                  description="Every skill: name, title, category, summary and source.")
    def catalog_resource() -> str:
        return json.dumps([s.brief().model_dump() for s in store.get().skills], indent=1)

    @mcp.resource("skills://categories", name="categories", title="Categories", mime_type="application/json",
                  description="The STLC phases and packs with their skills.")
    def categories_resource() -> str:
        return json.dumps([c.model_dump() for c in store.get().categories], indent=1)

    @mcp.resource("skills://skill/{name}", name="skill", title="A skill's SKILL.md", mime_type="text/markdown",
                  description="The SKILL.md of one skill, e.g. skills://skill/pw-api-tester.")
    def skill_resource(name: str) -> str:
        skill = store.get().find(name)
        if skill is None:
            raise ResourceError(f"No skill named '{name}'. Use search_skills to find it.")
        return skill.content

    @mcp.resource("skills://skill/{name}/files/{path*}", name="skill_file", title="A skill's supporting file",
                  mime_type="text/plain", description="e.g. skills://skill/test-plan-generator/files/references/test-plan-template.md")
    def skill_file_resource(name: str, path: str) -> str:
        catalog = store.get()
        skill = catalog.find(name)
        if skill is None or path not in skill.files:
            raise ResourceError(f"No file '{path}' in skill '{name}'.")
        return (catalog.root / skill.folder / path).read_bytes()[:MAX_FILE].decode("utf-8", errors="replace")

    # --- Prompts -------------------------------------------------------------------------------

    @mcp.prompt(name="use_skill", title="Use a skill for a task", tags={"use"},
                description="Loads a skill's instructions and applies them to your task.")
    def use_skill(skill: str, task: str) -> str:
        found = store.get().get(skill)
        return (f"Follow the skill below to do this task: {task}\n\n"
                f"Skill: {found.name} ({found.category})\n\n{found.body}\n\n"
                "If the skill needs inputs you do not have, ask for them instead of inventing them. "
                "Stop at the skill's human-review gate.")

    @mcp.prompt(name="find_skill_for_task", title="Find the right skill", tags={"find"},
                description="Searches the library and picks the best skill for a task.")
    def find_skill_for_task(task: str) -> str:
        return (f"Find the best skill in the Test Skill Finder library for this task: {task}\n"
                "1. Call search_skills with the key words of the task (limit 5), and recommend_skills with the task.\n"
                "2. Compare the top candidates by their summaries; open the best two with get_skill.\n"
                "3. Say which skill fits best and why, and what inputs it needs from me.\n"
                "4. Then follow that skill's workflow for the task.")

    @mcp.prompt(name="stlc_walkthrough", title="STLC walkthrough", tags={"browse"},
                description="Takes a feature through every STLC phase with the matching skills.")
    def stlc_walkthrough(feature: str) -> str:
        return (f"Walk the feature '{feature}' through the software testing life cycle with the Test Skill Finder skills.\n"
                "1. Call get_stlc_workflow to see the phases and their skills.\n"
                "2. For each phase in order, pick the skill that fits this feature (use recommend_skills if unsure), "
                "open it with get_skill, and produce that phase's output.\n"
                "3. Stop at every human-review gate and wait for my go-ahead before the next phase.")

    @mcp.prompt(name="compare_skills", title="Compare two skills", tags={"find"},
                description="Explains the difference between two skills and when to use each.")
    def compare_skills(first: str, second: str) -> str:
        a, b = store.get().get(first), store.get().get(second)
        return (f"Compare these two skills and tell me when to use each.\n\n"
                f"## {a.name} ({a.category})\n{a.description}\n\n## {b.name} ({b.category})\n{b.description}\n\n"
                "Cover: the situations each one fits, what each produces, and whether they work together.")

    if settings.profile == "readonly":
        mcp.disable(tags={"write"})
    return mcp


mcp = build_server()  # for `fastmcp run`, `fastmcp dev inspector` and the tsf-mcp command
