"""License Report Writer - a Langflow custom component.

Assembles the license report and writes it to disk, alongside the raw findings.

The report is in two halves, and the order matters. The first half is
**counted**: every account, the date it last saw a login, how many days ago
that was, what the seat costs, and which of the two tiers it falls in. None of
it comes from a model, so a QA Lead taking this into a budget conversation can
defend every line - including to the person whose access is on it.

The second half is the model's: which of these to do first, and whether a tool
is unused enough to renegotiate rather than trim seat by seat. That is a
judgement, it is labelled as one, and it sits under the evidence rather than in
place of it.

Two tables exist purely so nothing is hidden. Exceptions are printed with the
finding they suppressed, because an exception applied silently is indis-
tinguishable from a bug. Accounts inside the new-account grace period are
printed too, so "why isn't the new starter on here?" has an answer on the page.
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


class LicenseReportWriter(Component):
    display_name = "License Report Writer"
    description = "Writes the license report and the raw findings to disk."
    documentation = "https://playwright.dev/docs/test-reporters"
    icon = "file-text"
    name = "LicenseReportWriter"

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
                "Where license_report.md is written, and where license_findings.json is read "
                "from. Point this at the same folder as the Inactivity Filter's Reports folder."
            ),
            value="",
        ),
        MessageTextInput(
            name="report_name",
            display_name="Report file name",
            value="license_report.md",
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Summary", name="summary", method="write_report"),
        Output(display_name="Details", name="details", method="write_details"),
    ]

    # ------------------------------------------------------------- reading

    FINDINGS_FILE = "license_findings.json"

    def _findings(self, folder: Path) -> dict:
        """Read the analysis the Inactivity Filter left in the reports folder."""
        path = folder / self.FINDINGS_FILE
        if not path.is_file():
            msg = (f"No {self.FINDINGS_FILE} in {folder}. The Inactivity Filter writes it, so "
                   "set its Reports folder to this same folder and run the filter first.")
            raise ValueError(msg)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            msg = f"{path.name} is not valid JSON - {exc}"
            raise ValueError(msg) from exc
        if not isinstance(data, dict) or "accounts" not in data:
            msg = f"{path.name} does not look like an activity analysis; it has no accounts."
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

    @staticmethod
    def _account_rows(accounts: list) -> list:
        out = []
        for a in accounts:
            last_seen = a.get("last_login") or "never"
            days = a.get("days", 0)
            kind = "since last login" if a.get("days_kind") == "since_last_login" else "since created"
            out.append(
                f"| {a.get('tool', '')} | {a.get('user_name', '')} | `{a.get('user_email', '')}` "
                f"| {last_seen} | {days} ({kind}) | ${a.get('monthly_cost', 0):.2f} "
                f"| **${a.get('annual_cost', 0):.2f}** |"
            )
        return out

    def _compose(self, f: dict, recommendations: str) -> str:
        t = f.get("totals") or {}
        sc = f.get("status_counts") or {}
        per_tool = f.get("per_tool") or []
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        out = [
            "# Vendor license review",
            "",
            f"*Generated {stamp} by the Vendor License Monitor, measured against "
            f"{f.get('reference_date', '')}. Every count and every dollar below is computed "
            "from the activity log - re-run the filter to reproduce it.*",
            "",
            "## At a glance",
            "",
            "| | |",
            "|---|---|",
            f"| Accounts reviewed | {f.get('accounts_total', 0)} |",
            f"| Active | {sc.get('active', 0)} |",
            f"| Dormant | {sc.get('dormant', 0)} |",
            f"| Never activated | {sc.get('never_activated', 0)} |",
            f"| Inside grace period | {sc.get('too_new', 0)} |",
            f"| **Revoke now** | **{t.get('revoke_now_count', 0)} seats — "
            f"${t.get('revoke_now_monthly', 0):.2f}/mo, "
            f"${t.get('revoke_now_annual', 0):.2f}/yr** |",
            f"| Confirm first | {t.get('confirm_first_count', 0)} seats — "
            f"${t.get('confirm_first_monthly', 0):.2f}/mo, "
            f"${t.get('confirm_first_annual', 0):.2f}/yr |",
            "",
            f"Dormant means no login in {f.get('dormant_after_days', 60)} days. An account is "
            f"**revoke now** when it has never been used at all, or has been idle for at least "
            f"twice that. Anything between the two is **confirm first** — idle enough to cost "
            "money, not idle enough to cut without asking.",
            "",
        ]

        if per_tool:
            out.extend([
                "## By tool",
                "",
                "| Tool | Seats | Flagged | Dormant fraction | Monthly | Annual |",
                "|---|---:|---:|---:|---:|---:|",
            ])
            for tool in per_tool:
                out.append(
                    f"| {tool.get('tool', '')} | {tool.get('seats', 0)} | {tool.get('flagged', 0)} "
                    f"| {tool.get('dormant_fraction', 0):.0%} "
                    f"| ${tool.get('monthly_recoverable', 0):.2f} "
                    f"| ${tool.get('annual_recoverable', 0):.2f} |"
                )
            out.append("")

        header = ("| Tool | Person | Account | Last login | Days | Monthly | Annual |\n"
                  "|---|---|---|---|---:|---:|---:|")

        revoke = f.get("revoke_now") or []
        out.extend([f"## Revoke now ({len(revoke)})", ""])
        if revoke:
            out.append("Never used, or idle for at least twice the dormancy threshold.")
            out.extend(["", header])
            out.extend(self._account_rows(revoke))
        else:
            out.append("Nothing in this tier.")
        out.append("")

        confirm = f.get("confirm_first") or []
        out.extend([f"## Confirm first ({len(confirm)})", ""])
        if confirm:
            out.append("Dormant, but not long enough to cut without asking the seat holder.")
            out.extend(["", header])
            out.extend(self._account_rows(confirm))
        else:
            out.append("Nothing in this tier.")
        out.append("")

        excepted = f.get("exceptions_applied") or []
        if excepted:
            out.extend([
                f"## Exceptions applied ({len(excepted)})",
                "",
                "These met the criteria above and were held back by the exceptions list.",
                "",
                "| Tool | Account | Would have been | Reason given |",
                "|---|---|---|---|",
            ])
            for a in excepted:
                out.append(
                    f"| {a.get('tool', '')} | `{a.get('user_email', '')}` "
                    f"| {a.get('tier', '').replace('_', ' ')} "
                    f"| {a.get('exception_reason') or '—'} |"
                )
            out.append("")

        too_new = f.get("too_new") or []
        if too_new:
            out.extend([
                f"## Inside the grace period ({len(too_new)})",
                "",
                f"Created within the last {f.get('new_account_grace_days', 14)} days and not "
                "used yet. New, not dormant.",
                "",
            ])
            for a in too_new:
                out.append(f"- {a.get('tool', '')} — `{a.get('user_email', '')}`, "
                           f"created {a.get('days', 0)} days ago")
            out.append("")

        out.extend([
            "---",
            "",
            "## Recommendations",
            "",
            "*This section is written by a language model from the evidence above. The counts "
            "are not its work; the priorities are.*",
            "",
            recommendations,
            "",
        ])
        return "\n".join(out)

    # -------------------------------------------------------------- writing

    def _write(self) -> dict:
        folder_raw = (self.output_dir or "").strip().strip('"').strip("'")
        if not folder_raw:
            msg = "Set a reports folder on the License Report Writer."
            raise ValueError(msg)
        folder = Path(folder_raw).expanduser()
        folder.mkdir(parents=True, exist_ok=True)

        findings = self._findings(folder)
        recommendations = self._clean_markdown(self.recommendations)

        name = Path((self.report_name or "license_report.md").strip()).name or "license_report.md"
        if not name.endswith(".md"):
            name += ".md"

        report_path = folder / name
        report = self._compose(findings, recommendations)
        report_path.write_text(report if report.endswith("\n") else report + "\n", encoding="utf-8")

        t = findings.get("totals") or {}
        return {
            "report": str(report_path),
            "report_lines": len(report.splitlines()),
            "findings_json": str(folder / self.FINDINGS_FILE),
            "accounts_total": findings.get("accounts_total", 0),
            "revoke_now_count": t.get("revoke_now_count", 0),
            "revoke_now_annual": t.get("revoke_now_annual", 0),
            "confirm_first_count": t.get("confirm_first_count", 0),
            "confirm_first_annual": t.get("confirm_first_annual", 0),
            "exceptions_applied": len(findings.get("exceptions_applied") or []),
        }

    # -------------------------------------------------------------- outputs

    def write_report(self) -> Message:
        r = self._write()
        self.status = f"{r['revoke_now_count']} revoke now -> {Path(r['report']).name}"
        lines = [
            f"Reviewed {r['accounts_total']} accounts.",
            f"Revoke now: {r['revoke_now_count']} seats, ${r['revoke_now_annual']:.2f}/yr recoverable.",
            f"Confirm first: {r['confirm_first_count']} seats, ${r['confirm_first_annual']:.2f}/yr at risk.",
        ]
        if r["exceptions_applied"]:
            lines.append(f"{r['exceptions_applied']} finding(s) held back by the exceptions list.")
        lines.extend([
            "",
            f"Report:   {r['report']}  ({r['report_lines']} lines)",
            f"Findings: {r['findings_json']}",
        ])
        return Message(text="\n".join(lines))

    def write_details(self) -> Data:
        r = self._write()
        self.status = f"{r['revoke_now_count']} revoke now -> {Path(r['report']).name}"
        return Data(data=r)
