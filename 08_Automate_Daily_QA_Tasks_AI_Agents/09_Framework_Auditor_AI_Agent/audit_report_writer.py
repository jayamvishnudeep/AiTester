"""Audit Report Writer - a Langflow custom component.

Assembles the audit report and writes it to disk, alongside the raw findings.

The report is deliberately in two halves. The first is **counted**: how many
files, how many findings, which rules fired, which dependencies are behind, every
occurrence with its file and line. None of it comes from a model, so an SDET Lead
taking the report into a planning meeting can defend every number in it.

The second half is the model's: what to fix first, and why it is worth the time.
That is a judgement, it is labelled as one, and it sits under the evidence rather
than in place of it.

The JSON is written next to the report because a number in a document is a claim,
and a number in a file someone can re-run the scanner against is a fact.
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
_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


class AuditReportWriter(Component):
    display_name = "Audit Report Writer"
    description = "Writes the audit report and the raw findings to disk."
    documentation = "https://martinfowler.com/bliki/TechnicalDebt.html"
    icon = "file-text"
    name = "AuditReportWriter"

    inputs = [
        MessageTextInput(
            name="recommendations",
            display_name="Recommendations",
            info="The model's write-up. Placed under the counted evidence, not in place of it.",
            value="",
            required=True,
        ),
        MessageTextInput(
            name="output_dir",
            display_name="Reports folder",
            info=(
                "Where audit_report.md is written, and where audit_findings.json is read "
                "from. Point this at the same folder as the scanner's Reports folder."
            ),
            value="",
        ),
        MessageTextInput(
            name="report_name",
            display_name="Report file name",
            value="audit_report.md",
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Summary", name="summary", method="write_report"),
        Output(display_name="Details", name="details", method="write_details"),
    ]

    # ------------------------------------------------------------- reading

    FINDINGS_FILE = "audit_findings.json"

    def _audit(self, folder: Path) -> dict:
        """Read the scan the Framework Scanner left in the reports folder."""
        path = folder / self.FINDINGS_FILE
        if not path.is_file():
            msg = (f"No {self.FINDINGS_FILE} in {folder}. The Framework Scanner writes it, so "
                   "set its Reports folder to this same folder and run the scan first.")
            raise ValueError(msg)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            msg = f"{path.name} is not valid JSON - {exc}"
            raise ValueError(msg) from exc
        if not isinstance(data, dict) or "findings" not in data:
            msg = f"{path.name} does not look like a scan; it has no findings."
            raise ValueError(msg)
        return data

    @staticmethod
    def _clean_markdown(text: str) -> str:
        """Models sometimes wrap a whole markdown document in a fence."""
        raw = (text or "").strip()
        if not raw:
            msg = "The model returned no recommendations to write."
            raise ValueError(msg)
        whole = _FENCE_WHOLE.match(raw)
        return (whole.group(1) if whole else raw).strip()

    # ------------------------------------------------------------ composing

    def _compose(self, audit: dict, recommendations: str) -> str:
        sev = audit.get("severity_counts") or {}
        stale = audit.get("dependencies_stale") or []
        rules = audit.get("rules_triggered") or []
        by_eco = audit.get("files_by_ecosystem") or {}
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        out = [
            f"# Framework audit — {Path(audit.get('repository', 'repository')).name}",
            "",
            f"*Generated {stamp} by the Framework Auditor. Every count below is measured, not "
            "estimated — re-run the scanner to reproduce it.*",
            "",
            "## At a glance",
            "",
            "| | |",
            "|---|---|",
            f"| Repository | `{audit.get('repository', '')}` |",
            f"| Files scanned | {audit.get('files_scanned', 0)}"
            f"{' (' + ', '.join(f'{v} {k}' for k, v in sorted(by_eco.items())) + ')' if by_eco else ''} |",
            f"| Lines scanned | {audit.get('lines_scanned', 0):,} |",
            f"| Findings | **{audit.get('findings_total', 0)}** "
            f"— {sev.get('high', 0)} high, {sev.get('medium', 0)} medium, {sev.get('low', 0)} low |",
            f"| Dependencies behind | {len(stale)} of {audit.get('dependencies_total', 0)} |",
            "",
        ]

        if rules:
            out.extend([
                "## What was found",
                "",
                "| Severity | Anti-pattern | Occurrences | Files |",
                "|---|---|---:|---:|",
            ])
            for r in rules:
                out.append(f"| {r.get('severity', '').upper()} | {r.get('name', '')} "
                           f"| {r.get('count', 0)} | {r.get('files', 0)} |")
            out.append("")

        if stale:
            out.extend([
                "## Dependencies behind the current line",
                "",
                "| Package | Pinned at | Why it matters |",
                "|---|---|---|",
            ])
            for d in stale:
                out.append(f"| `{d.get('name', '')}` | `{d.get('version', '')}` "
                           f"| {d.get('note') or 'behind the current release'} |")
            out.append("")

        out.extend(["---", "", "## Recommendations", "",
                    "*This section is written by a language model from the evidence above. The "
                    "counts are not its work; the priorities are.*", "",
                    recommendations, "", "---", ""])

        findings = audit.get("findings") or []
        if findings:
            grouped = {}
            for f in findings:
                grouped.setdefault(f.get("rule", ""), []).append(f)
            order = sorted(
                grouped.items(),
                key=lambda kv: (_SEVERITY_ORDER.get(kv[1][0].get("severity", ""), 9), -len(kv[1])),
            )
            out.extend([f"## Appendix — every occurrence ({len(findings)})", ""])
            for _, items in order:
                head = items[0]
                out.append(f"### {head.get('name', '')} — {len(items)} "
                           f"[{head.get('severity', '')}]")
                out.append("")
                for f in items:
                    out.append(f"- `{f.get('file', '')}:{f.get('line', '')}` — "
                               f"`{f.get('snippet', '')}`")
                out.append("")

        return "\n".join(out)

    # -------------------------------------------------------------- writing

    def _write(self) -> dict:
        folder_raw = (self.output_dir or "").strip().strip('"').strip("'")
        if not folder_raw:
            msg = "Set a reports folder on the Audit Report Writer."
            raise ValueError(msg)
        folder = Path(folder_raw).expanduser()
        folder.mkdir(parents=True, exist_ok=True)

        audit = self._audit(folder)
        recommendations = self._clean_markdown(self.recommendations)

        name = Path((self.report_name or "audit_report.md").strip()).name or "audit_report.md"
        if not name.endswith(".md"):
            name += ".md"

        report_path = folder / name
        report = self._compose(audit, recommendations)
        report_path.write_text(report if report.endswith("\n") else report + "\n", encoding="utf-8")

        return {
            "report": str(report_path), "report_lines": len(report.splitlines()),
            "findings_json": str(folder / self.FINDINGS_FILE),
            "findings_total": audit.get("findings_total", 0),
            "severity_counts": audit.get("severity_counts") or {},
            "stale_dependencies": len(audit.get("dependencies_stale") or []),
            "files_scanned": audit.get("files_scanned", 0),
        }

    # -------------------------------------------------------------- outputs

    def write_report(self) -> Message:
        r = self._write()
        sev = r["severity_counts"]
        self.status = f"{r['findings_total']} findings -> {Path(r['report']).name}"
        return Message(text="\n".join([
            f"Audited {r['files_scanned']} files and found {r['findings_total']} issues "
            f"— {sev.get('high', 0)} high, {sev.get('medium', 0)} medium, {sev.get('low', 0)} low.",
            f"{r['stale_dependencies']} dependencies are behind the current line.",
            "",
            f"Report:   {r['report']}  ({r['report_lines']} lines)",
            f"Findings: {r['findings_json']}",
        ]))

    def write_details(self) -> Data:
        r = self._write()
        self.status = f"{r['findings_total']} findings -> {Path(r['report']).name}"
        return Data(data=r)
