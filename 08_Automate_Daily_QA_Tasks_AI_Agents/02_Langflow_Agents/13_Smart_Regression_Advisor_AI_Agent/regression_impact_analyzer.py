"""Regression Impact Analyzer - a Langflow custom component.

Reads a git diff, works out which tests can reach the changed code, and
recommends running those instead of everything.

The whole value of this agent is a *subset*, and a subset is a promise: the
tests left out would not have caught this change. That promise is the dangerous
part. Recommending one test too many wastes a few minutes; recommending one test
too few is silent - the suite goes green, the regression ships, and nothing in
the output ever looked wrong.

So the set is computed, never judged. Code parses the diff, builds an import
graph over the repository, and walks it backwards from each changed file to the
tests that reach it. A language model is handed the finished set and asked to
explain and order it; it is never asked which tests to run, because a model that
is approximately right about that is worse than useless.

And because a static import graph cannot see every real dependency - a selector
matching markup it never imports, a config value read by name, an HTTP boundary
between two services - the agent escalates to "run everything" whenever the diff
touches something whose blast radius it cannot model, and prints its own blind
spots next to every recommendation rather than at the bottom of a footnote.
"""

import json
import re
from pathlib import Path

from lfx.custom.custom_component.component import Component
from lfx.io import IntInput, MessageTextInput, MultilineInput, Output
from lfx.schema.data import Data
from lfx.schema.message import Message

_SKIP_DIRS = {
    "node_modules", "target", "build", "dist", "out", ".git", ".idea", ".vscode",
    "__pycache__", ".pytest_cache", ".venv", "venv", "env", ".gradle", "bin",
    "test-results", "playwright-report", "allure-results", ".next", "coverage", ".mvn",
}

_TS_EXT = (".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs")
_INDEX_FILES = tuple(f"index{ext}" for ext in _TS_EXT)

# import x from 'y' / export * from 'y' / require('y') / import('y')
_TS_IMPORT = re.compile(
    r"""(?:^|\s)(?:import|export)\s+(?:[^'"]*?\sfrom\s+)?['"]([^'"]+)['"]"""
    r"""|require\s*\(\s*['"]([^'"]+)['"]\s*\)"""
    r"""|import\s*\(\s*['"]([^'"]+)['"]\s*\)""",
    re.MULTILINE,
)
_JAVA_IMPORT = re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+)\s*;", re.MULTILINE)
_JAVA_PACKAGE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.MULTILINE)

_DIFF_FILE = re.compile(r"^diff --git a/(.+?) b/(.+?)$", re.MULTILINE)
_DIFF_HUNK = re.compile(r"^@@ .*? @@", re.MULTILINE)
_COMMENT_LINE = re.compile(r"^\s*(?://|/\*|\*|#|<!--)")

# A change to one of these cannot be modelled as a graph edge, so the honest
# answer is the whole suite. Each entry is (id, pattern, why).
_ESCALATIONS = [
    ("lockfile", r"(?:^|/)(?:package-lock\.json|pnpm-lock\.yaml|yarn\.lock)$",
     "A dependency version changed. Nothing imports a lockfile, so no edge exists to follow, "
     "and the new version can alter behaviour anywhere it is used."),
    ("dependency_manifest", r"(?:^|/)(?:package\.json|pom\.xml|build\.gradle(?:\.kts)?)$",
     "The dependency set or the scripts that run the suite changed."),
    ("resolution_config", r"(?:^|/)(?:tsconfig.*\.json|jsconfig.*\.json|vite\.config\.[jt]s|"
     r"webpack\.config\.[jt]s|babel\.config\.[jt]s|\.babelrc)$",
     "This file decides how module specifiers resolve, so every edge in the graph was computed "
     "under rules that have now changed."),
    ("test_runner_config", r"(?:^|/)(?:playwright\.config\.[jt]s|jest\.config\.[jt]s|"
     r"vitest\.config\.[jt]s|cypress\.config\.[jt]s|testng.*\.xml|karma\.conf\.js)$",
     "This file decides which tests run and how, so any subset chosen under the old rules is "
     "not trustworthy."),
    ("global_setup", r"(?:^|/)(?:global-?setup|global-?teardown|setup-?tests?|jest\.setup|"
     r"conftest|TestBase|BaseTest|BasePage)\.[\w.]+$",
     "Global setup runs for every test, including tests that never import it."),
    ("ci_config", r"(?:^|/)(?:\.github/workflows/.+\.ya?ml|\.circleci/.+|Jenkinsfile|"
     r"azure-pipelines\.ya?ml|\.gitlab-ci\.ya?ml)$",
     "How the suite is built and invoked changed."),
    ("runtime_resource", r"\.(?:properties|env|ini|toml|feature|sql)$|(?:^|/)\.env(?:\..+)?$",
     "This is read at runtime by name rather than imported, so no import edge to it can exist. "
     "Any test that reads it is invisible to the graph."),
    ("test_fixture_data", r"(?:^|/)(?:fixtures?|testdata|test-data|__snapshots__|"
     r"src/test/resources)/.+$",
     "Fixture and snapshot files are loaded by path at runtime, not imported."),
]
_ESCALATION_RULES = [(rid, re.compile(pat), why) for rid, pat, why in _ESCALATIONS]

# What this agent structurally cannot see. Printed with every recommendation.
_BLIND_SPOTS = [
    "A selector or test id matching markup the test never imports. Changing an id in a "
    "component breaks the page object that looks for it, with no edge between them - which is "
    "the coupling agent 12 in this section exists to repair.",
    "Anything across an HTTP or process boundary. A test calling an endpoint implemented "
    "elsewhere has no import path to it.",
    "Database migrations, seed data and stored procedures, which reach tests through the data "
    "rather than through code.",
    "Values read by name at runtime - environment variables, feature flags, system properties.",
    "Cucumber and other BDD glue, which binds steps to features by regular expression rather "
    "than by import.",
    "Shared state between tests: a seeded account, a tenant, a port, a browser profile. A "
    "change that makes one test leave dirt behind breaks another that imports nothing from it.",
    "Timing. A change that makes a page slower can trip a timeout in a test with no structural "
    "relationship to it.",
]


class RegressionImpactAnalyzer(Component):
    display_name = "Regression Impact Analyzer"
    description = "Works out which tests can reach the code a diff changed."
    documentation = "https://martinfowler.com/articles/rise-test-impact-analysis.html"
    icon = "git-compare"
    name = "RegressionImpactAnalyzer"

    inputs = [
        MessageTextInput(
            name="diff",
            display_name="Git diff",
            info="A path to a .diff or .patch file, or the diff text itself.",
            value="",
            tool_mode=True,
        ),
        MessageTextInput(
            name="default_diff",
            display_name="Default git diff",
            info="Used whenever the field above is empty.",
            value="",
        ),
        MultilineInput(
            name="pasted_diff",
            display_name="Pasted diff",
            info="Paste a diff here instead of reading one from disk.",
            value="",
            advanced=True,
        ),
        MessageTextInput(
            name="repo_path",
            display_name="Repository path",
            info="The repository the diff applies to. The import graph is built from it.",
            value="",
        ),
        IntInput(
            name="max_depth",
            display_name="Maximum walk depth",
            info="How far to follow imports backwards from a changed file.",
            value=8,
            advanced=True,
        ),
        IntInput(
            name="large_diff_files",
            display_name="Large-diff threshold",
            info="A diff touching more files than this escalates to the whole suite.",
            value=40,
            advanced=True,
        ),
        MessageTextInput(
            name="output_dir",
            display_name="Reports folder",
            info=(
                "Where impacted_tests.json is written. The plan writer reads it back from here, "
                "so both nodes must point at the same folder."
            ),
            value="",
        ),
    ]

    outputs = [
        Output(display_name="Brief", name="brief", method="build_brief"),
        Output(display_name="Findings", name="findings", method="build_findings"),
    ]

    # ------------------------------------------------------------- loading

    def _diff_text(self) -> tuple:
        pasted = (self.pasted_diff or "").strip()
        if pasted:
            return pasted, "pasted diff"
        for candidate in (self.diff, self.default_diff):
            raw = (candidate or "").strip().strip('"').strip("'")
            if not raw:
                continue
            if Path(raw).is_file():
                try:
                    return Path(raw).read_text(encoding="utf-8", errors="replace"), raw
                except OSError as exc:
                    msg = f"Could not read the diff from {raw} - {exc}"
                    raise ValueError(msg) from exc
            if "diff --git" in raw or raw.lstrip().startswith(("--- ", "@@")):
                return raw, "inline diff"
        msg = (
            "No diff reached this component. Without one there is nothing to compute an "
            "impacted set from, and a model asked which tests to run with no diff in front of "
            "it will produce a confident list of test names that mean nothing. Set 'Default "
            "git diff' to a file, or paste a diff."
        )
        raise ValueError(msg)

    def _root(self) -> Path:
        raw = (self.repo_path or "").strip().strip('"').strip("'")
        if raw and Path(raw).is_dir():
            return Path(raw).resolve()
        msg = (
            "No readable repository path. The impacted set is computed from the repository's "
            "own import graph, so the diff alone is not enough. Set 'Repository path' to the "
            "checkout the diff applies to."
        )
        raise ValueError(msg)

    # ------------------------------------------------------------- the diff

    @staticmethod
    def _parse_diff(text: str) -> dict:
        files, unreadable = {}, []
        if "diff --cc" in text or re.search(r"^@@@ ", text, re.MULTILINE):
            unreadable.append("a combined (merge) diff, which this parser does not read")

        blocks = list(_DIFF_FILE.finditer(text))
        for i, match in enumerate(blocks):
            old_path, new_path = match.group(1).strip(), match.group(2).strip()
            body = text[match.end():blocks[i + 1].start() if i + 1 < len(blocks) else len(text)]

            if "GIT binary patch" in body:
                unreadable.append(f"{new_path} is a binary patch")
                continue
            if "Subproject commit" in body:
                unreadable.append(f"{new_path} is a submodule pointer change")
                continue

            kind = "modified"
            if re.search(r"^new file mode", body, re.MULTILINE):
                kind = "added"
            elif re.search(r"^deleted file mode", body, re.MULTILINE):
                kind = "deleted"
            elif old_path != new_path:
                kind = "renamed"
            elif not _DIFF_HUNK.search(body) and re.search(r"^old mode", body, re.MULTILINE):
                kind = "mode-only"

            changed, substantive = [], False
            for line in body.splitlines():
                if line.startswith(("+++", "---")):
                    continue
                if line.startswith(("+", "-")) and len(line) > 1:
                    content = line[1:]
                    changed.append(content)
                    if content.strip() and not _COMMENT_LINE.match(content):
                        substantive = True

            files[new_path] = {
                "path": new_path,
                "old_path": old_path,
                "change": kind,
                "lines_changed": len(changed),
                "comment_or_whitespace_only": bool(changed) and not substantive,
            }
        return {"files": list(files.values()), "unreadable": unreadable}

    # ------------------------------------------------------------- the repo

    def _index(self, root: Path) -> list:
        """Every source file, as a RESOLVED path.

        Resolved consistently and everywhere on purpose. Import targets have to
        be resolved to be compared, and mixing the two forms means a lookup
        quietly returns nothing rather than failing - which for this agent
        shows up as an empty impacted set, the exact false negative the whole
        design is meant to prevent.
        """
        found = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in _SKIP_DIRS for part in path.parts):
                continue
            if path.suffix.lower() in (*_TS_EXT, ".java"):
                found.append(path.resolve())
        return sorted(found)

    @staticmethod
    def _rel(root: Path, path: Path) -> str:
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            return path.as_posix()

    @staticmethod
    def _ts_aliases(root: Path) -> dict:
        """tsconfig paths, so '@utils/money' resolves like the bundler resolves it."""
        aliases = {}
        for name in ("tsconfig.json", "jsconfig.json"):
            config = root / name
            if not config.is_file():
                continue
            try:
                text = re.sub(r"//.*?$|/\*.*?\*/", "", config.read_text(encoding="utf-8"),
                              flags=re.MULTILINE | re.DOTALL)
                data = json.loads(text)
            except (OSError, json.JSONDecodeError):
                continue
            options = data.get("compilerOptions") or {}
            base = options.get("baseUrl") or "."
            for pattern, targets in (options.get("paths") or {}).items():
                if targets:
                    aliases[pattern] = (base, targets[0])
        return aliases

    def _resolve_ts(self, specifier: str, from_file: Path, root: Path, index: set, aliases: dict):
        if specifier.startswith("."):
            base = (from_file.parent / specifier).resolve()
        else:
            base = None
            for pattern, (alias_base, target) in aliases.items():
                prefix = pattern.rstrip("*")
                if pattern.endswith("*") and specifier.startswith(prefix):
                    rest = specifier[len(prefix):]
                    base = (root / alias_base / target.rstrip("*")).resolve() / rest
                    break
                if pattern == specifier:
                    base = (root / alias_base / target).resolve()
                    break
            if base is None:
                return None  # a package, not a file in this repo

        candidates = [base]
        stem = base.with_suffix("")
        # './money' -> money.ts ; './money.js' -> money.ts (TS writes .js on purpose)
        candidates += [Path(str(base) + ext) for ext in _TS_EXT]
        candidates += [Path(str(stem) + ext) for ext in _TS_EXT]
        candidates += [base / name for name in _INDEX_FILES]
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved in index:
                return resolved
        return None

    def _graph(self, root: Path, files: list) -> tuple:
        index = {p.resolve() for p in files}
        aliases = self._ts_aliases(root)
        java_by_fqn = {}
        text_of = {}

        for path in files:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            text_of[path] = text
            if path.suffix == ".java":
                package = _JAVA_PACKAGE.search(text)
                fqn = f"{package.group(1)}.{path.stem}" if package else path.stem
                java_by_fqn[fqn] = path

        imports = {}
        for path, text in text_of.items():
            targets = set()
            if path.suffix == ".java":
                own_package = _JAVA_PACKAGE.search(text)
                own_package = own_package.group(1) if own_package else ""
                for fqn in _JAVA_IMPORT.findall(text):
                    hit = java_by_fqn.get(fqn)
                    if hit is None and fqn.endswith(".*"):
                        prefix = fqn[:-2] + "."
                        for known, known_path in java_by_fqn.items():
                            if known.startswith(prefix):
                                targets.add(known_path)
                        continue
                    if hit is not None:
                        targets.add(hit)
                # Same-package classes need no import statement, but visibility
                # is not dependency: adding an edge for every class in the
                # package makes each test class depend on its neighbours and
                # selects the lot. The class has to actually be named.
                for known, known_path in java_by_fqn.items():
                    if known_path == path or not own_package:
                        continue
                    if known.rsplit(".", 1)[0] != own_package:
                        continue
                    simple = known.rsplit(".", 1)[-1]
                    if re.search(rf"\b{re.escape(simple)}\b", text):
                        targets.add(known_path)
            else:
                for groups in _TS_IMPORT.findall(text):
                    specifier = next((g for g in groups if g), "")
                    if not specifier:
                        continue
                    hit = self._resolve_ts(specifier, path, root, index, aliases)
                    if hit is not None:
                        targets.add(hit)
            imports[path] = targets

        importers = {path: set() for path in text_of}
        for path, targets in imports.items():
            for target in targets:
                importers.setdefault(target, set()).add(path)
        return imports, importers

    @staticmethod
    def _is_test(root: Path, path: Path) -> bool:
        rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else path.as_posix()
        name = path.name
        if path.suffix == ".java":
            return name.endswith(("Test.java", "Tests.java", "IT.java")) or "/src/test/" in f"/{rel}"
        return (".spec." in name or ".test." in name
                or rel.startswith("tests/") or "/tests/" in f"/{rel}"
                or rel.startswith("e2e/") or "/__tests__/" in f"/{rel}")

    # ----------------------------------------------------------- analysing

    def _analyse(self) -> dict:
        diff_text, diff_origin = self._diff_text()
        root = self._root()
        parsed = self._parse_diff(diff_text)
        if not parsed["files"] and not parsed["unreadable"]:
            msg = (f"No changed files were found in the diff ({diff_origin}). Check it is a "
                   "unified diff produced by git.")
            raise ValueError(msg)

        files = self._index(root)
        if not files:
            msg = (f"No TypeScript or Java source files under {root}. Point the analyzer at the "
                   "root of the repository the diff applies to.")
            raise ValueError(msg)

        imports, importers = self._graph(root, files)
        tests = sorted(p for p in files if self._is_test(root, p))
        by_rel = {self._rel(root, p): p for p in files}

        escalations, unmapped, skipped = [], [], []
        seeds = []
        for entry in parsed["files"]:
            path_str = entry["path"]
            for rule_id, pattern, why in _ESCALATION_RULES:
                if pattern.search(path_str):
                    escalations.append({"rule": rule_id, "file": path_str, "why": why})
                    break
            else:
                if entry["comment_or_whitespace_only"]:
                    skipped.append({**entry, "reason": "only comments or whitespace changed"})
                    continue
                if entry["change"] == "mode-only":
                    skipped.append({**entry, "reason": "file mode changed, content did not"})
                    continue
                hit = by_rel.get(path_str)
                if hit is None and entry["change"] != "deleted":
                    unmapped.append(entry)
                elif hit is not None:
                    seeds.append((hit, entry))

        if len(parsed["files"]) > max(int(self.large_diff_files or 40), 1):
            escalations.append({
                "rule": "large_diff", "file": f"{len(parsed['files'])} files",
                "why": "A diff this wide is not usefully narrowed; the subset would be most of "
                       "the suite with the risk of missing the one test that mattered.",
            })
        for note in parsed["unreadable"]:
            escalations.append({"rule": "unreadable_diff", "file": note,
                                "why": "Part of the diff could not be read, so the changed-file "
                                       "list is incomplete and any subset from it is partial."})
        for entry in unmapped:
            escalations.append({
                "rule": "file_not_in_repo", "file": entry["path"],
                "why": "This path is not in the repository being analysed, so nothing can be "
                       "walked from it. Either the repository path is wrong or the file is "
                       "generated.",
            })

        depth_limit = max(int(self.max_depth or 8), 1)
        impact = {}
        for seed, entry in seeds:
            seen = {seed: 0}
            frontier = [seed]
            depth = 0
            while frontier and depth < depth_limit:
                depth += 1
                nxt = []
                for node in frontier:
                    for importer in importers.get(node, ()):
                        if importer not in seen:
                            seen[importer] = depth
                            nxt.append(importer)
                frontier = nxt
            for node, distance in seen.items():
                if not self._is_test(root, node):
                    continue
                rel = self._rel(root, node)
                record = impact.setdefault(rel, {"test": rel, "distance": distance, "because": []})
                record["distance"] = min(record["distance"], distance)
                record["because"].append({"changed": self._rel(root, seed), "hops": distance})

        full_suite = bool(escalations)
        if full_suite:
            selected = [{"test": self._rel(root, t), "tier": "full_suite",
                         "distance": None, "because": []} for t in tests]
        else:
            selected = []
            for rel, record in sorted(impact.items()):
                tier = "must_run" if record["distance"] <= 1 else "should_run"
                selected.append({"test": rel, "tier": tier,
                                 "distance": record["distance"],
                                 "because": record["because"][:4]})
            selected.sort(key=lambda r: (r["tier"] != "must_run", r["test"]))

        counts = {
            "must_run": sum(1 for r in selected if r["tier"] == "must_run"),
            "should_run": sum(1 for r in selected if r["tier"] == "should_run"),
            "full_suite": sum(1 for r in selected if r["tier"] == "full_suite"),
        }
        total_tests = len(tests)
        selected_count = len(selected)
        return {
            "diff_source": diff_origin,
            "repository": str(root),
            "files_changed": len(parsed["files"]),
            "changed_files": parsed["files"],
            "skipped_changes": skipped,
            "source_files_indexed": len(files),
            "tests_total": total_tests,
            "tests_selected": selected_count,
            "percent_skipped": round(100.0 * (total_tests - selected_count) / total_tests, 1)
            if total_tests else 0.0,
            "full_suite": full_suite,
            "escalations": escalations,
            "counts": counts,
            "selected": selected,
            "commands": self._commands(root, selected),
            "blind_spots": _BLIND_SPOTS,
        }

    @staticmethod
    def _commands(root: Path, selected: list) -> list:
        ts = [r["test"] for r in selected if r["test"].endswith(_TS_EXT)]
        java = [Path(r["test"]).stem for r in selected if r["test"].endswith(".java")]
        out = []
        if ts:
            out.append({"ecosystem": "typescript", "command": "npx playwright test " + " ".join(ts)})
        if java:
            out.append({"ecosystem": "java", "command": f"mvn test -Dtest={','.join(sorted(set(java)))}"})
        return out

    # -------------------------------------------------------------- disk

    FINDINGS_FILE = "impacted_tests.json"

    def _persist(self, analysis: dict) -> None:
        folder_raw = (self.output_dir or "").strip().strip('"').strip("'")
        if not folder_raw:
            return
        folder = Path(folder_raw).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
        (folder / self.FINDINGS_FILE).write_text(
            json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------ outputs

    def _brief_text(self, a: dict) -> str:
        lines = [
            "# Regression impact", "",
            f"Diff: {a['files_changed']} file(s) changed",
            f"Repository: {a['repository']} ({a['source_files_indexed']} source files indexed)",
            f"Tests in the suite: {a['tests_total']}",
        ]
        if a["full_suite"]:
            lines.append("VERDICT: run the whole suite. A subset would not be honest here.")
        else:
            lines.append(f"Selected: {a['tests_selected']} of {a['tests_total']} "
                         f"({a['percent_skipped']:.0f}% of the suite skipped) - "
                         f"{a['counts']['must_run']} must-run, {a['counts']['should_run']} should-run")

        if a["escalations"]:
            lines.extend(["", "## Why the whole suite"])
            for e in a["escalations"]:
                lines.append(f"- {e['file']} [{e['rule']}]: {e['why']}")

        lines.extend(["", "## Changed files"])
        for f in a["changed_files"]:
            lines.append(f"- {f['path']} ({f['change']}, {f['lines_changed']} lines changed)")
        for s in a["skipped_changes"]:
            lines.append(f"- {s['path']}: ignored - {s['reason']}")

        if not a["full_suite"] and a["selected"]:
            lines.extend(["", "## Selected tests"])
            for r in a["selected"]:
                trail = ", ".join(f"{b['changed']} ({b['hops']} hop(s))" for b in r["because"][:2])
                lines.append(f"- [{r['tier']}] {r['test']} <- {trail}")

        lines.extend(["", "## What this analysis cannot see"])
        for spot in a["blind_spots"]:
            lines.append(f"- {spot}")
        return "\n".join(lines)

    def build_brief(self) -> Message:
        a = self._analyse()
        self._persist(a)
        self.status = self._status(a)
        return Message(text=self._brief_text(a))

    def build_findings(self) -> Data:
        a = self._analyse()
        self._persist(a)
        self.status = self._status(a)
        return Data(data=a)

    @staticmethod
    def _status(a: dict) -> str:
        if a["full_suite"]:
            return f"full suite ({a['tests_total']} tests)"
        return f"{a['tests_selected']}/{a['tests_total']} tests, {a['percent_skipped']:.0f}% skipped"
