"""CI Failure Extractor - a Langflow custom component.

Finds the part of a CI log that explains why the build failed, and throws the
rest away.

A CI log is almost entirely noise. The Jenkins sample in this folder is 205
lines, of which about 30 say anything about the failure; the other 175 are
dependency downloads, git plumbing and tests that passed. Chunking the whole
thing and summarising each chunk would spend most of the token budget
describing Maven downloading jars, and would dilute the one stack trace that
matters into one paragraph among twenty.

So the selection happens in code. Anchor lines are matched by pattern,
classified into a category, normalised into a signature, and grouped - which is
the step that turns "twelve tests failed" into "nine of them are the same
NullPointerException in one page object, and the other three are unrelated".
That grouping is the whole value of the agent, and it is counting, so a model
never does it.

The model is handed the groups and their counts and asked what broke and what
to do. It never sees the log.
"""

import json
import re
from pathlib import Path

from lfx.custom.custom_component.component import Component
from lfx.io import IntInput, MessageTextInput, MultilineInput, Output
from lfx.schema.data import Data

# Timestamps and ANSI colour that CI systems prepend to every line. Stripped
# before matching so a pattern does not have to know which system it came from.
_GHA_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z\s?")
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

# How the three systems announce the thing that failed.
_CI_MARKERS = {
    "jenkins": (re.compile(r"^\[Pipeline\]|^Finished: |^Started by "), "Jenkins"),
    "github_actions": (re.compile(r"##\[(?:error|group|warning)\]|^Requested labels:"), "GitHub Actions"),
    "circleci": (re.compile(r"^====>>|Exited with code exit status|CircleCI received exit code"), "CircleCI"),
}

# A run is only analysed if one of these says it actually failed. A passing log
# must be refused rather than explained - see _verdict.
_FAILURE_MARKERS = [
    re.compile(r"^Finished: FAILURE"),
    re.compile(r"\bBUILD FAILURE\b"),
    re.compile(r"##\[error\]"),
    re.compile(r"ERROR: script returned exit code [1-9]"),
    re.compile(r"Exited with code exit status [1-9]"),
    re.compile(r"CircleCI received exit code [1-9]"),
    re.compile(r"Process completed with exit code [1-9]"),
]
_SUCCESS_MARKERS = [
    re.compile(r"^Finished: SUCCESS"),
    re.compile(r"\bBUILD SUCCESS\b"),
]

_EXIT_CODE = re.compile(r"exit(?:ed with)?(?: code)?(?: exit status)?[: ]+(\d+)", re.IGNORECASE)

# Which stage or step was running. Last one seen before the failure wins.
_STEP_MARKERS = [
    re.compile(r"^\[Pipeline\] \{ \((?P<name>[^)]+)\)"),
    re.compile(r"##\[group\]Run (?P<name>.+?)\s*$"),
    re.compile(r"^====>> (?P<name>.+?)\s*$"),
]

# ------------------------------------------------------------------ rules
# (category, human name, severity, compiled pattern). Order matters: the first
# category that matches a line claims it, so the specific causes are listed
# before the generic ones. A build that fails to resolve a dependency also
# prints "BUILD FAILURE", and the dependency error is the useful answer.
_CATEGORY_SPECS = [
    ("dependency", "Dependency resolution", "high",
     r"\bERESOLVE\b|Could not resolve dependenc|could not resolve\b|Conflicting peer dependency"
     r"|Could not find artifact|404 Not Found - GET|npm error code E[A-Z]+"),
    ("compile", "Compilation error", "high",
     r"\bCOMPILATION ERROR\b|\berror TS\d+\b|cannot find symbol|\.java:\[\d+,\d+\] error"
     r"|SyntaxError:|error: cannot find symbol"),
    ("infrastructure", "Infrastructure or resource limit", "high",
     r"OutOfMemoryError|No space left on device|exit code 137|Cannot connect to the Docker daemon"
     r"|Killed\s*$|The runner has received a shutdown signal"),
    ("configuration", "Missing configuration", "high",
     r"Input required and not supplied|environment variable .* (?:not set|is required)"
     r"|Missing required environment|could not be found in the environment"),
    ("network", "Network or connectivity", "medium",
     r"ECONNREFUSED|ETIMEDOUT|ENOTFOUND|UnknownHostException|Connection refused|Connection reset"),
    ("timeout", "Timeout", "medium",
     r"TimeoutException|TimeoutError|Timeout \d+ms exceeded|Timeout of \d+ms exceeded"
     r"|tried for \d+ second\(s\)|Expected condition failed: waiting for"),
    ("assertion", "Assertion failure", "medium",
     r"AssertionError|expect\(received\)|expected:? ?[\[<]|Expected string:|Expected substring:"
     r"|AssertionFailedError"),
    ("exception", "Unhandled exception", "high",
     r"\b(?:java|javax|org|com)\.[\w.]+(?:Exception|Error)\b|^\s*[A-Z]\w+Error:|Unhandled exception"),
]
_CATEGORIES = [
    {"id": cid, "name": name, "severity": sev, "pattern": re.compile(pat)}
    for cid, name, sev, pat in _CATEGORY_SPECS
]
_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

# Lines that continue an anchor: stack frames, call logs, npm's error block.
# A continuation is never an anchor in its own right - without this, one npm
# ERESOLVE block becomes four "failures" and every stack frame mentioning an
# exception class becomes a fifth.
_CONTINUATION = re.compile(r"^\s*(?:at\s|\.\.\.\s|Caused by:|npm error|Call log:|- waiting for|Expected |Received |•)")

# The recap a test runner prints after the fact. Every line in it names a
# failure that was already reported where it happened, so counting the recap
# too would report twice as many failures as the run actually had.
_RECAP_START = re.compile(r"^\[INFO\] Results:|^\[ERROR\] (?:Failures|Errors):|^\s*\d+ failed\b")
_RECAP_END = re.compile(r"^\[INFO\] -{5,}|BUILD (?:FAILURE|SUCCESS)|^\[Pipeline\]|^##\[")

# Counted results the systems print.
_MAVEN_TOTALS = re.compile(
    r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+),\s*Skipped:\s*(\d+)")
_PW_PASSED = re.compile(r"^\s*(\d+) passed\b")
_PW_FAILED = re.compile(r"^\s*(\d+) failed\b")

# Signature normalisation: everything that varies between two occurrences of
# the same failure is removed, so they collapse into one group.
_NORM_RULES = [
    (re.compile(r"0x[0-9a-fA-F]+"), "#"),
    (re.compile(r"\b[0-9a-fA-F]{7,}\b"), "#"),
    (re.compile(r"\b\d+(?:\.\d+)?(?:ms|s|m|h|MiB|MB|kB|GB)\b"), "#"),
    (re.compile(r":\d+(?::\d+)?\b"), ":#"),
    (re.compile(r"\b\d+\b"), "#"),
    (re.compile(r"\s+"), " "),
]


class CIFailureExtractor(Component):
    display_name = "CI Failure Extractor"
    description = "Finds and groups the failures in a Jenkins, GitHub Actions or CircleCI log."
    documentation = "https://www.jenkins.io/doc/book/pipeline/running-pipelines/"
    icon = "search-x"
    name = "CIFailureExtractor"

    inputs = [
        MessageTextInput(
            name="log_path",
            display_name="Log file path",
            info="Path to the CI log. Leave empty to use the pasted log below.",
            value="",
            tool_mode=True,
        ),
        MessageTextInput(
            name="default_log_path",
            display_name="Default log path",
            info="Used whenever the path above is empty or does not exist.",
            value="",
        ),
        MultilineInput(
            name="pasted_log",
            display_name="Pasted log",
            info="Paste a CI log here to use it instead of reading from disk.",
            value="",
            advanced=True,
        ),
        IntInput(
            name="max_quoted_lines",
            display_name="Quoted lines per group",
            info="How much of each failure is quoted for the model.",
            value=6,
            advanced=True,
        ),
        IntInput(
            name="max_groups",
            display_name="Groups in the brief",
            info="Caps how many failure groups are described to the model, largest first.",
            value=8,
            advanced=True,
        ),
        MessageTextInput(
            name="output_dir",
            display_name="Reports folder",
            info=(
                "Where ci_findings.json is written. The report writer reads it back from "
                "here, so both nodes must point at the same folder."
            ),
            value="",
        ),
    ]

    outputs = [
        Output(display_name="Brief", name="brief", method="build_brief"),
        Output(display_name="Findings", name="findings", method="build_findings"),
    ]

    # ------------------------------------------------------------- loading

    def _source(self) -> tuple:
        pasted = (self.pasted_log or "").strip()
        if pasted:
            return pasted, "pasted log"

        for candidate in (self.log_path, self.default_log_path):
            cleaned = (candidate or "").strip().strip('"').strip("'")
            if cleaned and Path(cleaned).is_file():
                try:
                    return Path(cleaned).read_text(encoding="utf-8", errors="replace"), cleaned
                except OSError as exc:
                    msg = f"Could not read {cleaned} - {exc}"
                    raise ValueError(msg) from exc

        msg = (
            "No CI log reached this component. A model asked to explain a failure it "
            "cannot see will invent a plausible one, so there is nothing safe to do here. "
            "Set 'Default log path' to a log file, or paste one into 'Pasted log'."
        )
        raise ValueError(msg)

    @staticmethod
    def _clean(line: str) -> str:
        return _GHA_TIMESTAMP.sub("", _ANSI.sub("", line)).rstrip()

    # ------------------------------------------------------------ reading

    @staticmethod
    def _ci_system(lines: list) -> tuple:
        scores = {key: 0 for key in _CI_MARKERS}
        for line in lines:
            for key, (pattern, _) in _CI_MARKERS.items():
                if pattern.search(line):
                    scores[key] += 1
        best = max(scores, key=lambda k: scores[k])
        if not scores[best]:
            return "unknown", "an unrecognised CI system"
        return best, _CI_MARKERS[best][1]

    @staticmethod
    def _verdict(lines: list) -> tuple:
        """(failed, exit_code). A passing log is refused, not explained."""
        failed = False
        exit_code = None
        for line in lines:
            if any(p.search(line) for p in _FAILURE_MARKERS):
                failed = True
                found = _EXIT_CODE.search(line)
                if found and exit_code is None:
                    exit_code = int(found.group(1))
        return failed, exit_code

    @staticmethod
    def _failed_step(lines: list, first_failure_index: int) -> str:
        step = ""
        for line in lines[:first_failure_index if first_failure_index >= 0 else len(lines)]:
            for pattern in _STEP_MARKERS:
                found = pattern.search(line)
                if found:
                    step = found.group("name").strip()
        return step

    @staticmethod
    def _signature(text: str) -> str:
        out = text.strip()
        for pattern, replacement in _NORM_RULES:
            out = pattern.sub(replacement, out)
        return out.strip()[:200]

    def _categorise(self, line: str):
        for rule in _CATEGORIES:
            if rule["pattern"].search(line):
                return rule
        return None

    # ----------------------------------------------------------- analysing

    def _analyse(self) -> dict:
        text, origin = self._source()
        raw_lines = text.splitlines()
        lines = [self._clean(line) for line in raw_lines]
        if not any(line.strip() for line in lines):
            msg = f"The log ({origin}) is empty."
            raise ValueError(msg)

        system_id, system_name = self._ci_system(lines)
        failed, exit_code = self._verdict(lines)

        if not failed:
            passed = any(p.search(line) for line in lines for p in _SUCCESS_MARKERS)
            msg = (
                f"This log does not contain a failure - "
                + ("it reports a successful build. " if passed else "no failure marker was found. ")
                + "There is no root cause to analyse, and a model asked for one anyway would "
                "write a convincing explanation of a failure that did not happen."
            )
            raise ValueError(msg)

        groups = {}
        first_failure_index = -1
        max_quoted = max(int(self.max_quoted_lines or 6), 1)
        consumed = set()
        in_recap = False

        for i, line in enumerate(lines):
            if not line.strip() or i in consumed:
                continue
            # A runner's closing summary repeats failures already counted above.
            if in_recap:
                if _RECAP_END.search(line):
                    in_recap = False
                else:
                    continue
            if _RECAP_START.search(line):
                in_recap = True
                continue

            rule = self._categorise(line)
            if not rule:
                continue
            if first_failure_index < 0:
                first_failure_index = i

            # Swallow this occurrence's continuation lines whether or not the
            # group is new, so a repeat's stack frames cannot become anchors.
            # Consumption runs to the end of the block while quoting stops at
            # max_quoted: how much belongs to this failure and how much of it
            # is worth showing are different questions. npm's ERESOLVE block is
            # twenty lines and one failure.
            quote, blanks = [line.strip()], 0
            for j in range(i + 1, len(lines)):
                follow = lines[j]
                if not follow.strip():
                    blanks += 1
                    if blanks > 1:
                        break
                    continue
                if not _CONTINUATION.search(follow):
                    break
                consumed.add(j)
                if len(quote) < max_quoted:
                    quote.append(follow.strip())

            key = (rule["id"], self._signature(line))
            slot = groups.get(key)
            if slot is None:
                slot = groups[key] = {
                    "category": rule["id"],
                    "category_name": rule["name"],
                    "severity": rule["severity"],
                    "signature": self._signature(line),
                    "occurrences": 0,
                    "first_line": i + 1,
                    "quote": quote,
                    "examples": [],
                }
            slot["occurrences"] += 1
            if len(slot["examples"]) < 3:
                slot["examples"].append({"line": i + 1, "text": line.strip()[:240]})

        if not groups:
            msg = (
                "The log says the run failed but no recognisable error line was found in it. "
                "Rather than guess, check whether the failing step wrote its output somewhere "
                "else - a separate test report or an artefact."
            )
            raise ValueError(msg)

        ordered = sorted(
            groups.values(),
            key=lambda g: (_SEVERITY_ORDER.get(g["severity"], 9), -g["occurrences"], g["first_line"]),
        )

        maven = _MAVEN_TOTALS.findall("\n".join(lines))
        tests = {}
        if maven:
            run, failures, errors, skipped = (int(v) for v in maven[-1])
            tests = {"total": run, "failed": failures + errors, "skipped": skipped,
                     "passed": run - failures - errors - skipped}
        else:
            passed = [int(m.group(1)) for line in lines if (m := _PW_PASSED.search(line))]
            failed_n = [int(m.group(1)) for line in lines if (m := _PW_FAILED.search(line))]
            if passed or failed_n:
                p, f = (passed[-1] if passed else 0), (failed_n[-1] if failed_n else 0)
                tests = {"total": p + f, "failed": f, "skipped": 0, "passed": p}

        quoted_lines = sum(len(g["quote"]) for g in ordered)
        return {
            "source": origin,
            "ci_system": system_id,
            "ci_system_name": system_name,
            "exit_code": exit_code,
            "failed_step": self._failed_step(lines, first_failure_index),
            "lines_total": len(lines),
            "lines_quoted": quoted_lines,
            "noise_ratio": round(1 - (quoted_lines / len(lines)), 4) if lines else 0.0,
            "failures_total": sum(g["occurrences"] for g in ordered),
            "group_count": len(ordered),
            "category_counts": {
                c["id"]: sum(g["occurrences"] for g in ordered if g["category"] == c["id"])
                for c in _CATEGORIES
                if any(g["category"] == c["id"] for g in ordered)
            },
            "tests": tests,
            "groups": ordered,
        }

    # -------------------------------------------------------------- disk

    FINDINGS_FILE = "ci_findings.json"

    def _persist(self, analysis: dict) -> None:
        """Hand the findings to the report writer through a file, not a second edge.

        Langflow lets a component expose only one selected output on the canvas,
        and a second wired edge is dropped the moment the flow is opened in the
        UI. The file is the hand-off - and it is worth keeping anyway, since the
        report's tables are built from it rather than from the model's reply.
        """
        folder_raw = (self.output_dir or "").strip().strip('"').strip("'")
        if not folder_raw:
            return
        folder = Path(folder_raw).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
        (folder / self.FINDINGS_FILE).write_text(
            json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------ outputs

    def _brief_text(self, a: dict) -> str:
        """The counted summary first, then the evidence.

        Order matters here. Everything downstream of this component can be
        truncated by the splitter if a pathological log produces a very large
        brief, and what survives truncation is the top. So the facts go first
        and the quoted evidence, which is the expendable part, goes last.
        """
        cap = max(int(self.max_groups or 8), 1)
        tests = a["tests"]
        lines = [
            "# CI failure analysis",
            "",
            f"CI system: {a['ci_system_name']}",
            f"Failed step: {a['failed_step'] or 'not identified'}",
            f"Exit code: {a['exit_code'] if a['exit_code'] is not None else 'not reported'}",
            f"Log length: {a['lines_total']} lines "
            f"({a['noise_ratio']:.0%} of them irrelevant to the failure)",
            f"Failure lines matched: {a['failures_total']}, "
            f"falling into {a['group_count']} distinct group(s)",
        ]
        if tests:
            lines.append(
                f"Tests: {tests['total']} run, {tests['failed']} failed, "
                f"{tests['passed']} passed, {tests['skipped']} skipped")
        lines.extend(["", "## Failure groups, largest first", ""])

        for i, g in enumerate(a["groups"][:cap], 1):
            plural = "occurrence" if g["occurrences"] == 1 else "occurrences"
            lines.append(
                f"{i}. [{g['severity'].upper()}] {g['category_name']} - "
                f"{g['occurrences']} {plural}, first at line {g['first_line']}")
            for quoted in g["quote"]:
                lines.append(f"      {quoted}")
            lines.append("")
        if len(a["groups"]) > cap:
            lines.append(f"... and {len(a['groups']) - cap} smaller group(s), in the findings file.")
        return "\n".join(lines)

    def build_brief(self) -> Data:
        a = self._analyse()
        self._persist(a)
        self.status = f"{a['group_count']} groups, {a['failures_total']} failure lines"
        return Data(data={"text": self._brief_text(a)})

    def build_findings(self) -> Data:
        a = self._analyse()
        self._persist(a)
        self.status = f"{a['group_count']} groups, {a['failures_total']} failure lines"
        return Data(data=a)
