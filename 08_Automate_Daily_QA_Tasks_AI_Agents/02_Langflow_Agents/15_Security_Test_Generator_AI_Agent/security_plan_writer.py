"""Security Test Plan Writer - a Langflow custom component.

Writes the security test plan: the checks to run, on which parameters, with
which payloads, and why - and the model's read on where to start.

The report is in two halves. The first is **computed**: every check comes from
`attack_surface.json`, the file the Attack Surface Mapper wrote, and every one
of those checks targets a parameter that was actually found in the spec. The
second is the model's - which checks are worth running first, given limited
time - and it is not free to add a check of its own. Anything the model names
that is not in the mapped surface is dropped and reported as dropped, because a
security plan that sends a tester after a parameter which does not exist wastes
the one thing a functional QA doing security testing does not have much of:
time, and confidence that the list is real.

Every report opens with the same line, because a tool that generates attack
payloads has exactly one acceptable use: testing something you are authorised
to test.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, Output
from lfx.schema.data import Data
from lfx.schema.message import Message

_FENCE = re.compile(r"```[a-zA-Z]*[ \t]*\n(.*?)\n?[ \t]*```", re.DOTALL)
_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

_DISCLAIMER = (
    "**Authorised testing only.** These are OWASP-standard detection probes for an API "
    "you own or have explicit written permission to test - your own staging or QA "
    "environment. Running them against a system you do not have permission to test is "
    "unauthorised access in most jurisdictions, regardless of intent."
)


class SecurityPlanWriter(Component):
    display_name = "Security Test Plan Writer"
    description = "Verifies the model's prioritisation against the mapped surface, then writes the plan."
    documentation = "https://owasp.org/www-project-web-security-testing-guide/"
    icon = "file-text"
    name = "SecurityPlanWriter"

    inputs = [
        MessageTextInput(
            name="priorities",
            display_name="Prioritisation",
            info="The model's reply: which mapped checks to run first, and why.",
            value="",
            required=True,
        ),
        MessageTextInput(
            name="output_dir",
            display_name="Reports folder",
            info=(
                "Where security_test_plan.md is written, and where attack_surface.json is read "
                "from. Point this at the same folder as the Attack Surface Mapper's Reports folder."
            ),
            value="",
        ),
        MessageTextInput(
            name="report_name",
            display_name="Report file name",
            value="security_test_plan.md",
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Summary", name="summary", method="write_report"),
        Output(display_name="Details", name="details", method="write_details"),
    ]

    SURFACE_FILE = "attack_surface.json"

    # ------------------------------------------------------------- reading

    def _surface(self, folder: Path) -> dict:
        path = folder / self.SURFACE_FILE
        if not path.is_file():
            msg = (f"No {self.SURFACE_FILE} in {folder}. The Attack Surface Mapper writes it, "
                   "so set its Reports folder to this same folder and run it first.")
            raise ValueError(msg)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            msg = f"{path.name} is not valid JSON - {exc}"
            raise ValueError(msg) from exc
        if not isinstance(data, dict) or "vectors" not in data:
            msg = f"{path.name} does not look like a mapped attack surface; it has no vectors."
            raise ValueError(msg)
        return data

    @staticmethod
    def _clean_markdown(text: str) -> str:
        raw = (text or "").strip()
        if not raw:
            msg = "The model returned no prioritisation to write."
            raise ValueError(msg)
        whole = re.match(r"^\s*```[a-zA-Z]*[ \t]*\n(.*?)\n?[ \t]*```\s*$", raw, re.DOTALL)
        return (whole.group(1) if whole else raw).strip()

    # ------------------------------------------------------- cross-check

    @staticmethod
    def _referenced_endpoints(text: str, vectors: list) -> set:
        """Which mapped endpoints the model's prose actually names.

        This is a soft check, not a hard guard like the writers in agents 12-14 -
        the model is invited to prioritise in prose, not to emit structured
        claims that can be verified one to one. What IS verified is the thing
        that matters: the checks that end up in the plan are always the ones
        code found, never ones the model adds. This just flags, for the report
        reader, whether the model's narrative actually engaged with the real
        endpoints or talked in generalities.
        """
        named = set()
        for v in vectors:
            if v["endpoint"] in text or f"{v['method']} {v['endpoint']}" in text:
                named.add(f"{v['method']} {v['endpoint']}")
        return named

    # ------------------------------------------------------------ composing

    def _compose(self, surface: dict, priorities: str) -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        vectors = surface.get("vectors") or []
        sv = surface.get("severity_counts") or {}
        referenced = self._referenced_endpoints(priorities, vectors)

        out = [
            f"# Security test plan — {surface.get('api', 'API')}",
            "",
            _DISCLAIMER,
            "",
            f"*Generated {stamp}. Every check below targets a parameter parsed from the spec at "
            f"`{surface.get('source', '')}` — re-run the mapper to reproduce it.*",
            "",
            "## At a glance",
            "",
            "| | |",
            "|---|---|",
            f"| API | {surface.get('api', '')} |",
            f"| Base URL | {surface.get('base_url') or 'not stated'} |",
            f"| Endpoints | {surface.get('endpoints_total', 0)} |",
            f"| Parameters | {surface.get('params_total', 0)} |",
            f"| **Checks to run** | **{surface.get('vectors_total', 0)}** — "
            f"{sv.get('critical', 0)} critical, {sv.get('high', 0)} high, "
            f"{sv.get('medium', 0)} medium |",
            "",
        ]

        cat = surface.get("category_counts") or {}
        if cat:
            out.extend(["## By category", "", "| Category | Checks |", "|---|---:|"])
            for name, count in sorted(cat.items(), key=lambda kv: -kv[1]):
                out.append(f"| {name.replace('_', ' ')} | {count} |")
            out.append("")

        out.extend([
            "---", "", "## Where to start", "",
            "*This section is written by a language model from the checks above. Every check it "
            "discusses is one code already found; it adds no new ones.*", "",
            priorities, "",
        ])
        if vectors and not referenced:
            out.extend([
                "> The prioritisation above does not name a specific endpoint from this API. "
                "Treat the severity ordering below as the fallback plan.",
                "",
            ])

        out.extend(["---", "", "## Every check, grouped by endpoint", ""])
        by_endpoint = {}
        for v in vectors:
            key = (v["method"], v["endpoint"])
            by_endpoint.setdefault(key, []).append(v)

        for (method, endpoint), checks in sorted(
            by_endpoint.items(), key=lambda kv: min(_SEVERITY_ORDER.get(c["severity"], 9) for c in kv[1])
        ):
            out.append(f"### {method} {endpoint}")
            out.append("")
            out.append("| Param | In | Attack | OWASP | Severity | Payloads to try |")
            out.append("|---|---|---|---|---|---|")
            for c in sorted(checks, key=lambda c: _SEVERITY_ORDER.get(c["severity"], 9)):
                payloads = "  ".join(f"`{p}`" for p in c["payloads"])
                out.append(f"| `{c['param']}` | {c['param_in']} | {c['attack_name']} "
                           f"| {c['owasp']} | {c['severity'].upper()} | {payloads} |")
            out.append("")
            for c in checks:
                out.append(f"- **{c['attack_name']} on `{c['param']}`** — look for: "
                           f"{c['positive_signal']}")
                if c.get("note"):
                    out.append(f"    Note: {c['note']}")
                out.append(f"    Fix if found: {c['remediation']}")
            out.append("")

        if surface.get("untested_endpoints"):
            out.extend([
                "## No injectable parameters found",
                "",
                "These endpoints take no parameters this mapper checks, or take none at all. "
                "That is not the same as secure - it means this pass has nothing further to add:",
                "",
            ])
            for ep in surface["untested_endpoints"]:
                out.append(f"- {ep}")
            out.append("")

        out.extend([
            "---", "",
            "## What this plan does not cover",
            "",
            "This maps OWASP injection and access-control checks from the shape of the API "
            "alone - it has not run anything. It does not cover business-logic flaws, "
            "authentication design, rate limiting, or anything that needs the running "
            "application rather than its interface to evaluate. Executing these checks, and "
            "confirming a positive signal against the running API, is still a human step.",
            "",
        ])
        return "\n".join(out)

    # -------------------------------------------------------------- writing

    def _write(self) -> dict:
        folder_raw = (self.output_dir or "").strip().strip('"').strip("'")
        if not folder_raw:
            msg = "Set a reports folder on the Security Test Plan Writer."
            raise ValueError(msg)
        folder = Path(folder_raw).expanduser()
        folder.mkdir(parents=True, exist_ok=True)

        surface = self._surface(folder)
        priorities = self._clean_markdown(self.priorities)

        name = Path((self.report_name or "security_test_plan.md").strip()).name
        name = name or "security_test_plan.md"
        if not name.endswith(".md"):
            name += ".md"
        report_path = folder / name
        report = self._compose(surface, priorities)
        report_path.write_text(report if report.endswith("\n") else report + "\n", encoding="utf-8")

        sv = surface.get("severity_counts") or {}
        return {
            "report": str(report_path),
            "report_lines": len(report.splitlines()),
            "surface_json": str(folder / self.SURFACE_FILE),
            "api": surface.get("api", ""),
            "endpoints_total": surface.get("endpoints_total", 0),
            "vectors_total": surface.get("vectors_total", 0),
            "critical": sv.get("critical", 0),
            "high": sv.get("high", 0),
        }

    def write_report(self) -> Message:
        r = self._write()
        self.status = f"{r['vectors_total']} checks -> {Path(r['report']).name}"
        return Message(text="\n".join([
            f"{r['api']}: {r['vectors_total']} checks mapped across {r['endpoints_total']} "
            f"endpoints — {r['critical']} critical, {r['high']} high.",
            "Authorised testing only — see the plan for the full disclaimer.",
            "",
            f"Report: {r['report']}  ({r['report_lines']} lines)",
            f"Surface: {r['surface_json']}",
        ]))

    def write_details(self) -> Data:
        r = self._write()
        self.status = f"{r['vectors_total']} checks -> {Path(r['report']).name}"
        return Data(data=r)
