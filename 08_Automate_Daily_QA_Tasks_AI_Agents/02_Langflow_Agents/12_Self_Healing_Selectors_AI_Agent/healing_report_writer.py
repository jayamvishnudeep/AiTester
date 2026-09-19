"""Healing Report Writer - a Langflow custom component.

Writes the healing report and the structured replacements to disk.

The report is in two halves. The first is **checked**: for every selector, what
it was, what it resolves to now, what is proposed instead, and the score the
proposal earned. Every proposed selector in it has been run against the page and
resolves to exactly one element - that is a property of the pipeline, not a
claim the model is making.

The second half is the model's, and is labelled as the model's: whether the
element it found is really the element the test meant. That is a judgement about
intent, which is the one thing here that cannot be computed.

The JSON beside the report is the part a script can use. A human reads the
markdown; a codemod reads `healed_selectors.json` and rewrites the suite.
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


class HealingReportWriter(Component):
    display_name = "Healing Report Writer"
    description = "Writes the healed selectors and the healing report to disk."
    documentation = "https://playwright.dev/docs/locators"
    icon = "file-text"
    name = "HealingReportWriter"

    inputs = [
        MessageTextInput(
            name="review",
            display_name="Review",
            info="The model's judgement. Placed under the checked evidence, not in place of it.",
            value="",
            required=True,
        ),
        MessageTextInput(
            name="output_dir",
            display_name="Reports folder",
            info=(
                "Where healing_report.md is written, and where healed_selectors.json is read "
                "from. Point this at the same folder as the Selector Healer's Reports folder."
            ),
            value="",
        ),
        MessageTextInput(
            name="report_name",
            display_name="Report file name",
            value="healing_report.md",
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Summary", name="summary", method="write_report"),
        Output(display_name="Details", name="details", method="write_details"),
    ]

    # ------------------------------------------------------------- reading

    FINDINGS_FILE = "healed_selectors.json"

    def _findings(self, folder: Path) -> dict:
        path = folder / self.FINDINGS_FILE
        if not path.is_file():
            msg = (f"No {self.FINDINGS_FILE} in {folder}. The Selector Healer writes it, so set "
                   "its Reports folder to this same folder and run the healer first.")
            raise ValueError(msg)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            msg = f"{path.name} is not valid JSON - {exc}"
            raise ValueError(msg) from exc
        if not isinstance(data, dict) or "results" not in data:
            msg = f"{path.name} does not look like a healing run; it has no results."
            raise ValueError(msg)
        return data

    @staticmethod
    def _clean_markdown(text: str) -> str:
        raw = (text or "").strip()
        if not raw:
            msg = "The model returned no review to write."
            raise ValueError(msg)
        whole = _FENCE_WHOLE.match(raw)
        return (whole.group(1) if whole else raw).strip()

    # ------------------------------------------------------------ composing

    def _compose(self, f: dict, review: str) -> str:
        results = f.get("results") or []
        counts = f.get("counts") or {}
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        by = {k: [r for r in results if r.get("outcome") == k]
              for k in ("healed", "ambiguous", "gone", "not_broken")}

        out = [
            "# Selector healing report",
            "",
            f"*Generated {stamp} by the Self-Healing Selectors agent. Every selector proposed "
            "below was run against the current page and resolves to exactly one element.*",
            "",
            "## At a glance",
            "",
            "| | |",
            "|---|---|",
            f"| Selectors checked | {f.get('selectors_total', 0)} |",
            f"| **Healed** | **{counts.get('healed', 0)}** |",
            f"| Need a decision | {counts.get('ambiguous', 0)} |",
            f"| Element gone | {counts.get('gone', 0)} |",
            f"| Were never broken | {counts.get('not_broken', 0)} |",
            f"| Previous DOM supplied | {'yes' if f.get('had_previous_dom') else 'no'} |",
            f"| Elements searched | {f.get('elements_searched', 0)} |",
            "",
        ]
        if not f.get("had_previous_dom"):
            out.extend([
                "> No previous DOM was supplied, so each element's identity was inferred from "
                "the selector text alone. That is thin evidence, and the healer refuses more "
                "often because of it. Supplying a snapshot from when the suite passed is the "
                "single biggest improvement available here.",
                "",
            ])

        if by["healed"]:
            out.extend([
                f"## Healed ({len(by['healed'])})",
                "",
                "| Was | Now | Via | Score |",
                "|---|---|---|---:|",
            ])
            for r in by["healed"]:
                healed = r.get("healed") or {}
                out.append(f"| `{r.get('selector', '')}` | `{healed.get('playwright', '')}` "
                           f"| {healed.get('rung', '')} | {r.get('score', 0):.0f} |")
            out.append("")
            out.extend(["Why each one matched:", ""])
            for r in by["healed"]:
                evidence = "; ".join(r.get("evidence") or []) or "structural similarity only"
                out.append(f"- `{r.get('selector', '')}` — {evidence}")
                for alt in r.get("alternatives") or []:
                    out.append(f"    - or `{alt.get('playwright', '')}` (via {alt.get('rung', '')})")
            out.append("")

        if by["ambiguous"]:
            out.extend([
                f"## Need a decision ({len(by['ambiguous'])})",
                "",
                "Several elements matched about equally well. Picking one would be a guess, and "
                "a selector pointed at the wrong element fails silently rather than loudly.",
                "",
            ])
            for r in by["ambiguous"]:
                out.append(f"**`{r.get('selector', '')}`** — {r.get('why', '')}")
                out.append("")
                for tie in r.get("competing") or []:
                    candidate = (tie.get("candidates") or [{}])
                    proposed = candidate[0].get("playwright", "") if candidate else ""
                    out.append(f"- scored {tie.get('score', 0):.0f}: {tie.get('preview', '')!r}"
                               + (f" → `{proposed}`" if proposed else ""))
                out.append("")

        if by["gone"]:
            out.extend([
                f"## Element gone ({len(by['gone'])})",
                "",
                "Nothing in the current page corresponds to these. A test pointing at a removed "
                "feature needs rewriting, not a new selector.",
                "",
            ])
            for r in by["gone"]:
                out.append(f"- `{r.get('selector', '')}` — best match scored "
                           f"{r.get('best_score', 0):.0f}, below the threshold of "
                           f"{f.get('heal_threshold', 0)}")
            out.append("")

        if by["not_broken"]:
            out.extend([f"## Were never broken ({len(by['not_broken'])})", ""])
            for r in by["not_broken"]:
                out.append(f"- `{r.get('selector', '')}` — still resolves to exactly one element")
            out.append("")

        if by["healed"]:
            out.extend(["## Replacements", "",
                        "Ready to apply. The JSON beside this report carries the same pairs for "
                        "a codemod.", "", "```text"])
            for r in by["healed"]:
                out.append(f"{r.get('selector', '')}")
                out.append(f"  -> {(r.get('healed') or {}).get('playwright', '')}")
            out.extend(["```", ""])

        out.extend([
            "---",
            "",
            "## Review",
            "",
            "*This section is written by a language model from the evidence above. That each "
            "selector resolves uniquely is checked in code; whether it is the element the test "
            "meant is the judgement below.*",
            "",
            review,
            "",
        ])
        return "\n".join(out)

    # -------------------------------------------------------------- writing

    def _write(self) -> dict:
        folder_raw = (self.output_dir or "").strip().strip('"').strip("'")
        if not folder_raw:
            msg = "Set a reports folder on the Healing Report Writer."
            raise ValueError(msg)
        folder = Path(folder_raw).expanduser()
        folder.mkdir(parents=True, exist_ok=True)

        findings = self._findings(folder)
        review = self._clean_markdown(self.review)

        name = Path((self.report_name or "healing_report.md").strip()).name or "healing_report.md"
        if not name.endswith(".md"):
            name += ".md"

        report_path = folder / name
        report = self._compose(findings, review)
        report_path.write_text(report if report.endswith("\n") else report + "\n", encoding="utf-8")

        counts = findings.get("counts") or {}
        return {
            "report": str(report_path),
            "report_lines": len(report.splitlines()),
            "findings_json": str(folder / self.FINDINGS_FILE),
            "selectors_total": findings.get("selectors_total", 0),
            "healed": counts.get("healed", 0),
            "ambiguous": counts.get("ambiguous", 0),
            "gone": counts.get("gone", 0),
            "not_broken": counts.get("not_broken", 0),
            "had_previous_dom": findings.get("had_previous_dom", False),
        }

    # -------------------------------------------------------------- outputs

    def write_report(self) -> Message:
        r = self._write()
        self.status = f"{r['healed']} healed -> {Path(r['report']).name}"
        lines = [
            f"Checked {r['selectors_total']} selectors: {r['healed']} healed, "
            f"{r['ambiguous']} need a decision, {r['gone']} gone, "
            f"{r['not_broken']} were never broken.",
            "Every proposed selector resolves to exactly one element on the current page.",
            "",
            f"Report:   {r['report']}  ({r['report_lines']} lines)",
            f"Findings: {r['findings_json']}",
        ]
        return Message(text="\n".join(lines))

    def write_details(self) -> Data:
        r = self._write()
        self.status = f"{r['healed']} healed -> {Path(r['report']).name}"
        return Data(data=r)
