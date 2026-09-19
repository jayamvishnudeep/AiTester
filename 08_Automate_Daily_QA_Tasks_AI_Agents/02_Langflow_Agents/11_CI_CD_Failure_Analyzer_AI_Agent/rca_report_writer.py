"""RCA Report Writer - a Langflow custom component.

Assembles the root cause analysis and writes it to disk, alongside the raw
findings.

The report is in two halves. The first is **counted**: which step failed, the
exit code, how many failures there were, how they group, and the exact lines
they were read from. An engineer who disagrees with the analysis can check it
against the log, because every line is quoted with the number it came from.

The second half is the model's - what broke and what to do about it - and it is
labelled as the model's. It sits under the evidence rather than in place of it,
because the point of this agent is to stop someone scrolling a log for twenty
minutes, not to replace the log with something that cannot be checked.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, Output
from lfx.schema.data import Data
from lfx.schema.message import Message

_FENCE_WHOLE = re.compile(r"^\s*```[a-zA-Z]*[ \t]*\n(.*?)\n?[ \t]*```\s*$", re.DOTALL)


class RCAReportWriter(Component):
    display_name = "RCA Report Writer"
    description = "Writes the root cause analysis and the raw findings to disk."
    documentation = "https://www.atlassian.com/incident-management/postmortem/root-cause-analysis"
    icon = "file-text"
    name = "RCAReportWriter"

    inputs = [
        MessageTextInput(
            name="rca",
            display_name="Root cause analysis",
            info="The model's write-up. Placed under the counted evidence, not in place of it.",
            value="",
            required=True,
        ),
        MessageTextInput(
            name="output_dir",
            display_name="Reports folder",
            info=(
                "Where rca_report.md is written, and where ci_findings.json is read from. "
                "Point this at the same folder as the CI Failure Extractor's Reports folder."
            ),
            value="",
        ),
        MessageTextInput(
            name="report_name",
            display_name="Report file name",
            value="rca_report.md",
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Summary", name="summary", method="write_report"),
        Output(display_name="Details", name="details", method="write_details"),
    ]

    # ------------------------------------------------------------- reading

    FINDINGS_FILE = "ci_findings.json"

    def _findings(self, folder: Path) -> dict:
        path = folder / self.FINDINGS_FILE
        if not path.is_file():
            msg = (f"No {self.FINDINGS_FILE} in {folder}. The CI Failure Extractor writes it, "
                   "so set its Reports folder to this same folder and run the extractor first.")
            raise ValueError(msg)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            msg = f"{path.name} is not valid JSON - {exc}"
            raise ValueError(msg) from exc
        if not isinstance(data, dict) or "groups" not in data:
            msg = f"{path.name} does not look like a CI analysis; it has no failure groups."
            raise ValueError(msg)
        return data

    @staticmethod
    def _clean_markdown(text: str) -> str:
        raw = (text or "").strip()
        if not raw:
            msg = "The model returned no analysis to write."
            raise ValueError(msg)
        whole = _FENCE_WHOLE.match(raw)
        return (whole.group(1) if whole else raw).strip()

    # ------------------------------------------------------------ composing

    def _compose(self, f: dict, rca: str) -> str:
        groups = f.get("groups") or []
        tests = f.get("tests") or {}
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        exit_code = f.get("exit_code")

        out = [
            f"# CI failure analysis — {f.get('ci_system_name', 'CI run')}",
            "",
            f"*Generated {stamp} by the Smart CI/CD Failure Analyzer. Every count and every "
            "quoted line below is read from the log - re-run the extractor to reproduce it.*",
            "",
            "## At a glance",
            "",
            "| | |",
            "|---|---|",
            f"| CI system | {f.get('ci_system_name', '')} |",
            f"| Failed step | {f.get('failed_step') or 'not identified'} |",
            f"| Exit code | {exit_code if exit_code is not None else 'not reported'} |",
            f"| Log length | {f.get('lines_total', 0):,} lines |",
            f"| Read by the model | {f.get('lines_quoted', 0)} lines "
            f"({f.get('noise_ratio', 0):.0%} of the log discarded as noise) |",
            f"| Failures | **{f.get('failures_total', 0)}** in "
            f"{f.get('group_count', 0)} distinct group(s) |",
        ]
        if tests:
            out.append(f"| Tests | {tests.get('total', 0)} run, **{tests.get('failed', 0)} failed**, "
                       f"{tests.get('passed', 0)} passed, {tests.get('skipped', 0)} skipped |")
        out.append("")

        if groups:
            out.extend([
                "## What failed",
                "",
                "| Severity | Category | Occurrences | First seen |",
                "|---|---|---:|---:|",
            ])
            for g in groups:
                out.append(
                    f"| {str(g.get('severity', '')).upper()} | {g.get('category_name', '')} "
                    f"| {g.get('occurrences', 0)} | line {g.get('first_line', 0)} |")
            out.append("")

            out.extend(["## The evidence", "",
                        "Quoted from the log, with the line each group was first seen at.", ""])
            for i, g in enumerate(groups, 1):
                count = g.get("occurrences", 0)
                plural = "occurrence" if count == 1 else "occurrences"
                out.append(f"### {i}. {g.get('category_name', '')} — {count} {plural}")
                out.append("")
                out.append(f"First at line {g.get('first_line', 0)}:")
                out.append("")
                out.append("```")
                out.extend(g.get("quote") or [])
                out.append("```")
                out.append("")
                others = [e for e in (g.get("examples") or [])][1:]
                if others:
                    out.append("Also at " + ", ".join(f"line {e.get('line')}" for e in others)
                               + (" and elsewhere." if count > len(others) + 1 else "."))
                    out.append("")

        out.extend([
            "---",
            "",
            "## Root cause analysis",
            "",
            "*This section is written by a language model from the evidence above. The counts "
            "and the grouping are not its work; the explanation is.*",
            "",
            rca,
            "",
        ])
        return "\n".join(out)

    # -------------------------------------------------------------- writing

    def _write(self) -> dict:
        folder_raw = (self.output_dir or "").strip().strip('"').strip("'")
        if not folder_raw:
            msg = "Set a reports folder on the RCA Report Writer."
            raise ValueError(msg)
        folder = Path(folder_raw).expanduser()
        folder.mkdir(parents=True, exist_ok=True)

        findings = self._findings(folder)
        rca = self._clean_markdown(self.rca)

        name = Path((self.report_name or "rca_report.md").strip()).name or "rca_report.md"
        if not name.endswith(".md"):
            name += ".md"

        report_path = folder / name
        report = self._compose(findings, rca)
        report_path.write_text(report if report.endswith("\n") else report + "\n", encoding="utf-8")

        groups = findings.get("groups") or []
        return {
            "report": str(report_path),
            "report_lines": len(report.splitlines()),
            "findings_json": str(folder / self.FINDINGS_FILE),
            "ci_system": findings.get("ci_system_name", ""),
            "failed_step": findings.get("failed_step", ""),
            "failures_total": findings.get("failures_total", 0),
            "group_count": findings.get("group_count", 0),
            "lines_total": findings.get("lines_total", 0),
            "lines_quoted": findings.get("lines_quoted", 0),
            "noise_ratio": findings.get("noise_ratio", 0),
            "largest_group": groups[0].get("category_name", "") if groups else "",
        }

    # -------------------------------------------------------------- outputs

    def write_report(self) -> Message:
        r = self._write()
        self.status = f"{r['failures_total']} failures -> {Path(r['report']).name}"
        lines = [
            f"{r['ci_system']}: the '{r['failed_step']}' step failed with "
            f"{r['failures_total']} failure(s) in {r['group_count']} group(s).",
            f"Read {r['lines_quoted']} lines of a {r['lines_total']:,}-line log "
            f"({r['noise_ratio']:.0%} discarded as noise).",
            "",
            f"Report:   {r['report']}  ({r['report_lines']} lines)",
            f"Findings: {r['findings_json']}",
        ]
        return Message(text="\n".join(lines))

    def write_details(self) -> Data:
        r = self._write()
        self.status = f"{r['failures_total']} failures -> {Path(r['report']).name}"
        return Data(data=r)
