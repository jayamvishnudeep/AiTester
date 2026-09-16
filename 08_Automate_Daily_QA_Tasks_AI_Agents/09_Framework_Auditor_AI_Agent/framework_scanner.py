"""Framework Scanner - a Langflow custom component.

Walks a test-automation repository and reports what is actually in it.

A repository does not fit in a prompt. A middling Selenium suite is tens of
thousands of lines, and Groq's free tier allows eight thousand input tokens a
minute, so handing the model "the codebase" is not an option that exists. That
constraint turns out to be the right architecture anyway: counting occurrences
is something code does exactly and a model does approximately, and an audit is
almost entirely counting.

So this component finds and counts every anti-pattern, reads the dependency
versions out of the build files, and passes on a compact brief - the totals,
plus a few quoted lines from the worst offenders so the recommendations can name
a file and a line rather than giving advice that would fit any repository.

Nothing here asks a model anything. The same repository always produces the same
findings.
"""

import json
import re
from pathlib import Path

from lfx.custom.custom_component.component import Component
from lfx.io import IntInput, MessageTextInput, Output
from lfx.schema.data import Data
from lfx.schema.message import Message

# Directories that are never source: dependencies, build output, tooling.
_SKIP_DIRS = {
    "node_modules", "target", "build", "dist", "out", ".git", ".idea", ".vscode",
    "__pycache__", ".pytest_cache", ".venv", "venv", "env", ".gradle", "bin",
    "test-results", "playwright-report", "allure-results", "allure-report",
    ".next", ".nuxt", "coverage", ".mvn",
}

_EXT_ECOSYSTEM = {
    ".java": "java",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "typescript",
    ".mjs": "typescript",
}

# Newest major line in wide use, and why the old one is a problem. Versions are
# compared on the leading integers only, which is all that matters at this scale.
_DEPENDENCY_BASELINE = {
    # Java / Maven
    "selenium-java": (4, "Selenium 4 has been current since 2021; 3.x predates the W3C "
                         "WebDriver protocol and bundled Selenium Manager"),
    "testng": (7, "TestNG 7 has been current since 2019 and is required for recent JDKs"),
    "junit": (5, "JUnit 4 is in maintenance only; JUnit 5 is the current platform"),
    "webdrivermanager": (5, "Selenium 4.6 manages drivers itself, so this may not be "
                            "needed at all any more"),
    "commons-lang3": (3, None),
    "maven-surefire-plugin": (3, "Surefire 3 is required for JUnit 5 and recent JDKs"),
    # npm
    "@playwright/test": (1, None),
    "typescript": (5, "TypeScript 5 has been current since 2023"),
    "dotenv": (16, "dotenv 8 is from 2020"),
}

# A minor-version floor for packages whose major number does not move.
_MINOR_BASELINE = {
    "@playwright/test": (1, 40, "Playwright ships monthly; 1.28 is from late 2022"),
    "commons-lang3": (3, 12, "commons-lang3 3.9 is from 2019"),
}

# ---------------------------------------------------------------- the rules
# Each rule is (id, name, ecosystem, severity, why, compiled pattern, fix).
# Detection is deterministic: a regex run line by line. Rules are deliberately
# narrow - a rule that fires on reasonable code costs more trust than it earns.
_RULE_SPECS = [
    # -- waits and synchronisation -----------------------------------------
    ("hard_sleep_java", "Hard-coded sleep", "java", "high",
     "A fixed sleep is either longer than needed, which slows every run, or shorter than "
     "needed, which makes the test flaky. It cannot be both right and fast.",
     r"\bThread\s*\.\s*sleep\s*\(",
     "Replace with WebDriverWait and an ExpectedCondition for the state you are waiting for."),
    ("hard_sleep_ts", "Hard-coded sleep", "typescript", "high",
     "waitForTimeout pauses for a fixed period regardless of whether the page is ready, "
     "which is the single most common source of flakiness in a Playwright suite.",
     r"\bwaitForTimeout\s*\(",
     "Use a web-first assertion or locator wait - Playwright retries until the condition holds."),
    ("implicit_wait", "Implicit wait", "java", "medium",
     "An implicit wait applies to every findElement in the session and interacts badly with "
     "explicit waits, producing timeouts far longer than either setting suggests.",
     r"implicitlyWait\s*\(",
     "Remove it and wait explicitly where a wait is actually needed."),

    # -- locators ----------------------------------------------------------
    ("absolute_xpath", "Absolute XPath", "both", "high",
     "An absolute XPath encodes the whole document structure, so any markup change anywhere "
     "above the element breaks it.",
     # Playwright writes these as "xpath=/html/...", Selenium as a bare "/html/..."
     r"""["'`]\s*(?:xpath\s*=\s*)?/html/""",
     "Locate by role, label, test id or a stable attribute instead."),
    ("indexed_xpath", "Index-based XPath", "both", "medium",
     "An XPath that selects by position breaks as soon as a sibling is added or reordered.",
     r"""["'`][^"'`]*/(?:div|span|li|tr|td|section|label|input|button)\[\d+\]""",
     "Anchor on an attribute or accessible name rather than position."),
    ("styling_css_selector", "Selector tied to styling", "both", "medium",
     "A selector built from utility or styling classes breaks when the design changes, which "
     "is exactly when nobody expects the tests to break.",
     r"""["'`][^"'`]*\.(?:text-|bg-|btn--|col-|mt-|mb-|px-|py-)[A-Za-z0-9_-]+""",
     "Use a data-testid or an accessible role and name."),
    ("nth_child_selector", "Positional CSS selector", "typescript", "medium",
     "nth-child ties the selector to sibling order, so inserting an element anywhere before "
     "it silently changes what the test clicks.",
     r"nth-child\s*\(",
     "Select by role, label or test id."),

    # -- structure ---------------------------------------------------------
    ("driver_in_test", "WebDriver call in the test layer", "java", "medium",
     "findElement inside a test method means the locator lives in the test, so the same "
     "element is re-located in every test that touches it and one markup change edits many files.",
     r"driver\s*\.\s*findElement\s*\(",
     "Move the locator into a page object and call a named method from the test."),
    ("raw_page_call_in_test", "Raw selector in the test layer", "typescript", "medium",
     "page.click and page.fill with a literal selector put the locator in the test, which is "
     "the thing a Page Object exists to prevent.",
     r"\bpage\s*\.\s*(?:click|fill|type|\$\$?eval|\$\$?)\s*\(\s*['\"`]",
     "Move the locator into a Page Object and expose a named action."),
    ("assertion_in_page_object", "Assertion inside a page object", "java", "high",
     "A page object that asserts decides whether a test passes, so the test no longer says "
     "what it is checking and the page object cannot be reused by a test that expects failure.",
     r"\bAssert\s*\.\s*(?:assert|fail)",
     "Return the value and let the test assert on it."),
    ("static_mutable_driver", "Static mutable driver", "java", "high",
     "A static WebDriver is shared by every class in the JVM, so the suite can never run in "
     "parallel and one test's state leaks into the next.",
     # requires "= " or ";" after the name, so a static METHOD returning a WebDriver
     # - getDriver() - is not mistaken for a shared static field
     r"\bstatic\s+(?:WebDriver|ChromeDriver|RemoteWebDriver)\s+\w+\s*(?:=|;)",
     "Hold the driver per test instance, or in a ThreadLocal if it must be shared."),

    # -- hygiene -----------------------------------------------------------
    ("disabled_test_java", "Disabled test", "java", "medium",
     "A disabled test is coverage the team believes it has and does not. They are rarely "
     "re-enabled once the reason is forgotten.",
     r"@Ignore\b|@Test\s*\(\s*enabled\s*=\s*false",
     "Fix it, or delete it and record the gap."),
    ("disabled_test_ts", "Disabled test", "typescript", "medium",
     "A skipped test is coverage the team believes it has and does not.",
     r"\btest\s*\.\s*(?:skip|fixme)\s*\(|\bdescribe\s*\.\s*skip\s*\(",
     "Fix it, or delete it and record the gap."),
    ("console_output_java", "Console output instead of logging", "java", "low",
     "System.out has no level, no timestamp and no destination, so it is invisible in CI and "
     "cannot be turned down.",
     r"\bSystem\s*\.\s*(?:out|err)\s*\.\s*print",
     "Use a logger."),
    ("console_output_ts", "Console output instead of logging", "typescript", "low",
     "console.log in a test is noise in the CI log and tells you nothing on a failure that the "
     "trace does not already show.",
     r"\bconsole\s*\.\s*(?:log|debug)\s*\(",
     "Remove it, or attach the information to the test report."),
    ("empty_catch", "Empty catch block", "java", "high",
     "A swallowed exception turns a real failure into a pass. It is the only anti-pattern here "
     "that can make a broken suite look green.",
     r"catch\s*\([^)]*\)\s*\{\s*\}",
     "Handle it, log it, or let it propagate."),
    ("hardcoded_credential", "Credential in source", "both", "high",
     "A password committed to the repository is a password that has to be rotated when anyone "
     "leaves, and it is in the history for ever.",
     r"(?i)\b(?:password|passwd|secret|api[_-]?token|apikey|api[_-]?key)\s*[:=]\s*[\"'][^\"']{6,}[\"']",
     "Read it from the environment or a secret store."),
    ("hardcoded_environment_url", "Environment URL in source", "both", "medium",
     "A URL written into the test means the suite can only ever run against one environment.",
     r"""["'`]https?://(?!localhost|127\.0\.0\.1)[^"'`\s]+["'`]""",
     "Take the base URL from configuration."),
]

_RULES = [
    {"id": rid, "name": name, "ecosystem": eco, "severity": sev, "why": why,
     "pattern": re.compile(pat), "fix": fix}
    for rid, name, eco, sev, why, pat, fix in _RULE_SPECS
]

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
_DEP_RE = re.compile(r"<artifactId>([^<]+)</artifactId>\s*<version>([^<]+)</version>", re.DOTALL)
_VERSION_NUMS = re.compile(r"(\d+)(?:\.(\d+))?")


class FrameworkScanner(Component):
    display_name = "Framework Scanner"
    description = "Walks a test-automation repository and counts its anti-patterns."
    documentation = "https://playwright.dev/docs/best-practices"
    icon = "search-code"
    name = "FrameworkScanner"

    inputs = [
        MessageTextInput(
            name="repo_path",
            display_name="Repository path",
            info="Folder holding the automation framework to audit.",
            value="",
            tool_mode=True,
        ),
        MessageTextInput(
            name="fallback_path",
            display_name="Default repository path",
            info="Used whenever the path above is empty or does not exist.",
            value="",
        ),
        MessageTextInput(
            name="output_dir",
            display_name="Reports folder",
            info=(
                "Where audit_findings.json is written. The report writer reads it back from "
                "here, so both nodes must point at the same folder."
            ),
            value="",
        ),
        IntInput(
            name="max_snippets",
            display_name="Quoted lines in the brief",
            info="How many of the worst offenders are quoted for the model.",
            value=12,
            advanced=True,
        ),
        IntInput(
            name="max_file_kb",
            display_name="Skip files larger than (KB)",
            info="Guards against minified bundles and checked-in artefacts.",
            value=512,
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Audit brief", name="brief", method="build_brief"),
        Output(display_name="Findings", name="findings", method="build_findings"),
    ]

    # ------------------------------------------------------------- walking

    def _root(self) -> Path:
        for candidate in (self.repo_path, self.fallback_path):
            cleaned = (candidate or "").strip().strip('"').strip("'")
            if cleaned and Path(cleaned).is_dir():
                return Path(cleaned)
        msg = ("No readable repository path. Set 'Default repository path' on the Framework "
               "Scanner to the folder holding the framework you want audited.")
        raise ValueError(msg)

    def _source_files(self, root: Path) -> list:
        limit = max(int(self.max_file_kb or 512), 1) * 1024
        found = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in _SKIP_DIRS for part in path.parts):
                continue
            eco = _EXT_ECOSYSTEM.get(path.suffix.lower())
            if not eco:
                continue
            try:
                if path.stat().st_size > limit:
                    continue
            except OSError:
                continue
            found.append((path, eco))
        return sorted(found)

    # ------------------------------------------------------------ scanning

    def _scan_files(self, root: Path, files: list) -> tuple:
        findings, lines_total = [], 0
        for path, eco in files:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            lines = text.splitlines()
            lines_total += len(lines)
            rel = path.relative_to(root).as_posix()
            in_test_layer = "/test" in f"/{rel}" or rel.endswith(("Test.java", ".spec.ts", ".test.ts"))

            for number, line in enumerate(lines, 1):
                stripped = line.strip()
                # a commented-out line is debt of a different kind; do not double-count it
                if stripped.startswith(("//", "*", "/*", "#")):
                    continue
                for rule in _RULES:
                    if rule["ecosystem"] not in (eco, "both"):
                        continue
                    if rule["id"] in ("driver_in_test", "raw_page_call_in_test") and not in_test_layer:
                        continue
                    if rule["id"] == "assertion_in_page_object" and in_test_layer:
                        continue
                    if rule["pattern"].search(line):
                        findings.append({
                            "rule": rule["id"], "name": rule["name"],
                            "severity": rule["severity"], "file": rel, "line": number,
                            "snippet": stripped[:160],
                        })
        return findings, lines_total

    # -------------------------------------------------------- dependencies

    @staticmethod
    def _version_parts(raw: str) -> tuple:
        m = _VERSION_NUMS.search(raw or "")
        if not m:
            return (None, None)
        return (int(m.group(1)), int(m.group(2)) if m.group(2) else 0)

    def _dependencies(self, root: Path) -> list:
        out = []
        for pom in root.rglob("pom.xml"):
            if any(part in _SKIP_DIRS for part in pom.parts):
                continue
            try:
                text = " ".join(pom.read_text(encoding="utf-8", errors="replace").split())
            except OSError:
                continue
            rel = pom.relative_to(root).as_posix()
            for artifact, version in _DEP_RE.findall(text):
                out.append(self._judge(artifact.strip(), version.strip(), rel))
            target = re.search(r"<maven\.compiler\.target>\s*([^<]+)</maven\.compiler\.target>", text)
            if target:
                major, _ = self._version_parts(target.group(1))
                if major is not None and major < 17:
                    out.append({"name": "maven.compiler.target", "version": target.group(1).strip(),
                                "file": rel, "stale": True,
                                "note": "Java 17 and 21 are the current LTS releases"})

        for pkg in root.rglob("package.json"):
            if any(part in _SKIP_DIRS for part in pkg.parts):
                continue
            try:
                data = json.loads(pkg.read_text(encoding="utf-8", errors="replace"))
            except (OSError, json.JSONDecodeError):
                continue
            rel = pkg.relative_to(root).as_posix()
            for section in ("dependencies", "devDependencies"):
                for name, version in (data.get(section) or {}).items():
                    out.append(self._judge(name, str(version), rel))
        return out

    def _judge(self, name: str, version: str, where: str) -> dict:
        entry = {"name": name, "version": version, "file": where, "stale": False, "note": None}
        if version.strip() in ("*", "latest", ""):
            entry["stale"] = True
            entry["note"] = "unpinned - the build is not reproducible"
            return entry
        major, minor = self._version_parts(version)
        if major is None:
            return entry
        floor = _DEPENDENCY_BASELINE.get(name)
        if floor and major < floor[0]:
            entry["stale"] = True
            entry["note"] = floor[1] or f"{name} {floor[0]}.x is the current line"
            return entry
        minor_floor = _MINOR_BASELINE.get(name)
        if minor_floor and major == minor_floor[0] and minor < minor_floor[1]:
            entry["stale"] = True
            entry["note"] = minor_floor[2]
        return entry

    # ------------------------------------------------------------- results

    def _audit(self) -> dict:
        root = self._root()
        files = self._source_files(root)
        if not files:
            msg = (f"No Java or TypeScript source files under {root}. Point the scanner at the "
                   "root of an automation framework.")
            raise ValueError(msg)

        findings, lines_total = self._scan_files(root, files)
        deps = self._dependencies(root)

        by_rule = {}
        for f in findings:
            slot = by_rule.setdefault(f["rule"], {
                "rule": f["rule"], "name": f["name"], "severity": f["severity"],
                "count": 0, "files": set(),
            })
            slot["count"] += 1
            slot["files"].add(f["file"])
        rules_hit = sorted(
            ({**v, "files": len(v["files"])} for v in by_rule.values()),
            key=lambda r: (_SEVERITY_ORDER.get(r["severity"], 9), -r["count"]),
        )

        severity_counts = {"high": 0, "medium": 0, "low": 0}
        for f in findings:
            severity_counts[f["severity"]] = severity_counts.get(f["severity"], 0) + 1

        worst = sorted(
            findings,
            key=lambda f: (_SEVERITY_ORDER.get(f["severity"], 9), f["file"], f["line"]),
        )[: max(int(self.max_snippets or 12), 1)]

        stale = [d for d in deps if d["stale"]]
        by_eco = {}
        for _, eco in files:
            by_eco[eco] = by_eco.get(eco, 0) + 1

        return {
            "repository": str(root),
            "files_scanned": len(files),
            "files_by_ecosystem": by_eco,
            "lines_scanned": lines_total,
            "findings_total": len(findings),
            "severity_counts": severity_counts,
            "rules_triggered": rules_hit,
            "worst_offenders": worst,
            "dependencies_total": len(deps),
            "dependencies_stale": stale,
            "findings": findings,
            "rule_reference": [
                {"id": r["id"], "name": r["name"], "severity": r["severity"],
                 "why": r["why"], "fix": r["fix"]}
                for r in _RULES
            ],
        }

    FINDINGS_FILE = "audit_findings.json"

    def _persist(self, audit: dict) -> str:
        """Write the structured scan next to the report.

        Langflow lets a component expose only one output on the canvas, so the
        findings cannot also travel to the report writer down a second edge -
        opening the flow in the UI deletes it. They go through a file instead,
        which the writer reads back. The file is a deliverable in its own right:
        a number in a document is a claim, a number in a file someone can
        re-generate is a fact.
        """
        folder_raw = (self.output_dir or "").strip().strip('"').strip("'")
        if not folder_raw:
            return ""
        folder = Path(folder_raw).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / self.FINDINGS_FILE
        path.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(path)

    def build_brief(self) -> Message:
        """A compact brief for the prompt - totals, not source."""
        a = self._audit()
        self._persist(a)
        lines = [
            "# Framework audit findings", "",
            f"Repository: {a['repository']}",
            f"Files scanned: {a['files_scanned']} "
            f"({', '.join(f'{v} {k}' for k, v in sorted(a['files_by_ecosystem'].items()))})",
            f"Lines scanned: {a['lines_scanned']}",
            f"Findings: {a['findings_total']} "
            f"({a['severity_counts'].get('high', 0)} high, "
            f"{a['severity_counts'].get('medium', 0)} medium, "
            f"{a['severity_counts'].get('low', 0)} low)",
            "",
            "## Anti-patterns found",
        ]
        rules_by_id = {r["id"]: r for r in _RULES}
        for r in a["rules_triggered"]:
            spec = rules_by_id.get(r["rule"], {})
            lines.append(f"- [{r['severity'].upper()}] {r['name']}: {r['count']} "
                         f"occurrences across {r['files']} files")
            if spec.get("why"):
                lines.append(f"    why it costs: {spec['why']}")

        if a["dependencies_stale"]:
            lines.extend(["", f"## Out-of-date dependencies ({len(a['dependencies_stale'])} "
                              f"of {a['dependencies_total']})"])
            for d in a["dependencies_stale"]:
                note = f" — {d['note']}" if d.get("note") else ""
                lines.append(f"- {d['name']} {d['version']} ({d['file']}){note}")

        if a["worst_offenders"]:
            lines.extend(["", "## Worst offenders, quoted"])
            for f in a["worst_offenders"]:
                lines.append(f"- {f['file']}:{f['line']}  [{f['severity']}] {f['name']}")
                lines.append(f"    {f['snippet']}")

        self.status = f"{a['findings_total']} findings in {a['files_scanned']} files"
        return Message(text="\n".join(lines))

    def build_findings(self) -> Data:
        a = self._audit()
        self.status = f"{a['findings_total']} findings in {a['files_scanned']} files"
        return Data(data=a)
