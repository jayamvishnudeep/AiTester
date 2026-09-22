"""Requirements Writer - a Langflow custom component.

Takes the requirements the model extracted, throws away the ones nobody said,
and writes what survives as Jira-ready JSON and a report.

This is the guard the whole agent is built around. Asked what was agreed in a
meeting, a model produces a tidy list of requirements - and some of them were
never said. They are not obviously wrong: they are the sensible things a team
*would* agree given that discussion, phrased exactly like the real ones. A QA
lead reading the list cannot tell which is which, and neither can the developer
who gets the ticket.

So every extracted item has to carry a **quote**, and every quote is checked
against the parsed transcript before the item is allowed through. An invented
requirement has nothing to quote, so it cannot survive the check. Items that
fail are dropped, counted, and printed - a silent drop would just be a quieter
version of the same problem.

Attribution is taken from the matched turn rather than from the model. The model
says what was agreed; the transcript says who said it and when.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from lfx.custom.custom_component.component import Component
from lfx.io import IntInput, MessageTextInput, Output
from lfx.schema.data import Data
from lfx.schema.message import Message

_FENCE = re.compile(r"```[a-zA-Z]*[ \t]*\n(.*?)\n?[ \t]*```", re.DOTALL)
_PUNCT = re.compile(r"[^\w\s]")
_SPACE = re.compile(r"\s+")

_CATEGORIES = ("requirement", "action_item", "decision", "open_question")
_JIRA_TYPE = {
    "requirement": "Story",
    "action_item": "Task",
    "decision": "Task",
    "open_question": "Task",
}


def _normalise(text: str) -> str:
    return _SPACE.sub(" ", _PUNCT.sub(" ", (text or "").lower())).strip()


class RequirementsWriter(Component):
    display_name = "Requirements Writer"
    description = "Verifies every extracted requirement against the transcript, then writes them."
    documentation = "https://support.atlassian.com/jira-software-cloud/docs/what-is-an-issue/"
    icon = "clipboard-check"
    name = "RequirementsWriter"

    inputs = [
        MessageTextInput(
            name="extracted",
            display_name="Extracted requirements",
            info="The model's JSON reply. Every item must carry a quote or it is dropped.",
            value="",
            required=True,
        ),
        MessageTextInput(
            name="output_dir",
            display_name="Reports folder",
            info=(
                "Where requirements.json and the report are written, and where "
                "transcript_turns.json is read from. Point this at the same folder as the "
                "Transcript Parser's Reports folder."
            ),
            value="",
        ),
        IntInput(
            name="min_quote_words",
            display_name="Minimum words in a quote",
            info=(
                "A quote shorter than this matches too easily to prove anything. Three words "
                "of common English will appear in almost any transcript."
            ),
            value=4,
            advanced=True,
        ),
        MessageTextInput(
            name="report_name",
            display_name="Report file name",
            value="requirements_report.md",
            advanced=True,
        ),
        MessageTextInput(
            name="project_key",
            display_name="Jira project key",
            info="Used to build the issue payloads. Nothing is sent anywhere.",
            value="QA",
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Summary", name="summary", method="write_report"),
        Output(display_name="Details", name="details", method="write_details"),
    ]

    TURNS_FILE = "transcript_turns.json"
    ISSUES_FILE = "requirements.json"

    # ------------------------------------------------------------- reading

    def _turns(self, folder: Path) -> dict:
        path = folder / self.TURNS_FILE
        if not path.is_file():
            msg = (f"No {self.TURNS_FILE} in {folder}. The Transcript Parser writes it, and "
                   "without it there is no transcript to check the model's quotes against - "
                   "which is the only thing separating a real requirement from a plausible "
                   "one. Set its Reports folder to this same folder and run it first.")
            raise ValueError(msg)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            msg = f"{path.name} is not valid JSON - {exc}"
            raise ValueError(msg) from exc
        if not isinstance(data, dict) or "all_turns" not in data:
            msg = f"{path.name} does not look like a parsed transcript; it has no turns."
            raise ValueError(msg)
        return data

    @staticmethod
    def _extract_json(text: str):
        """Models wrap JSON in fences, prose, or both."""
        raw = (text or "").strip()
        if not raw:
            msg = "The model returned nothing to verify."
            raise ValueError(msg)

        candidates = [block for block in _FENCE.findall(raw)]
        candidates.append(raw)
        for start, end in (("[", "]"), ("{", "}")):
            first, last = raw.find(start), raw.rfind(end)
            if first != -1 and last > first:
                candidates.append(raw[first:last + 1])

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                for key in ("requirements", "items", "results", "extracted", "output"):
                    if isinstance(parsed.get(key), list):
                        return parsed[key]
                return [parsed]
        msg = ("The model's reply was not JSON. It must return a list of items, each with a "
               "quote taken from the transcript.")
        raise ValueError(msg)

    # -------------------------------------------------------- verification

    def _verify(self, quote: str, turns: list, min_words: int):
        """The turn this quote came from, or None if nobody said it.

        A quote is matched on normalised text so punctuation and casing do not
        decide whether a requirement is real. It has to be long enough to mean
        something: a three-word quote of ordinary English matches almost any
        transcript and would let an invented requirement borrow a real turn's
        attribution.
        """
        cleaned = _normalise(quote)
        if not cleaned or len(cleaned.split()) < max(int(min_words), 1):
            return None
        for turn in turns:
            if cleaned in _normalise(turn.get("text", "")):
                return turn
        return None

    def _analyse(self, folder: Path) -> dict:
        parsed = self._turns(folder)
        turns = parsed.get("all_turns") or []
        items = self._extract_json(self.extracted)
        min_words = max(int(self.min_quote_words or 4), 1)
        project = (self.project_key or "QA").strip() or "QA"

        verified, rejected, seen = [], [], set()
        for raw in items:
            if not isinstance(raw, dict):
                rejected.append({"text": str(raw)[:160], "reason": "not an object"})
                continue
            text = str(raw.get("text") or raw.get("requirement") or raw.get("summary") or "").strip()
            quote = str(raw.get("quote") or raw.get("evidence") or "").strip()
            category = str(raw.get("category") or raw.get("type") or "requirement").strip().lower()
            if category not in _CATEGORIES:
                category = "requirement"
            if not text:
                rejected.append({"text": "", "quote": quote, "reason": "no requirement text"})
                continue
            if not quote:
                rejected.append({"text": text, "quote": "", "category": category,
                                 "reason": "no quote - nothing to check it against"})
                continue

            turn = self._verify(quote, turns, min_words)
            if turn is None:
                rejected.append({"text": text, "quote": quote, "category": category,
                                 "reason": "quote does not appear in the transcript"})
                continue

            key = _normalise(text)
            if key in seen:
                rejected.append({"text": text, "quote": quote, "category": category,
                                 "reason": "duplicate of an item already accepted"})
                continue
            seen.add(key)

            verified.append({
                "text": text,
                "category": category,
                "quote": quote,
                # Attribution comes from the transcript, not from the model.
                "said_by": turn.get("speaker") or "unattributed",
                "at": turn.get("time") or "",
                "turn_id": turn.get("id") or "",
                "jira": {
                    "project": project,
                    "issuetype": _JIRA_TYPE[category],
                    "summary": text if len(text) <= 120 else text[:117].rstrip() + "...",
                    "labels": ["from-meeting", category.replace("_", "-")],
                },
            })

        counts = {c: sum(1 for v in verified if v["category"] == c) for c in _CATEGORIES}
        return {
            "meeting": parsed.get("meeting", ""),
            "source": parsed.get("source", ""),
            "speakers": parsed.get("speakers", []),
            "turns_total": parsed.get("turns_total", 0),
            "turns_sent": parsed.get("turns_sent", 0),
            "turns_omitted": parsed.get("turns_omitted", []),
            "proposed": len(items),
            "verified_count": len(verified),
            "rejected_count": len(rejected),
            "counts": counts,
            "verified": verified,
            "rejected": rejected,
        }

    # ------------------------------------------------------------ composing

    def _compose(self, a: dict) -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out = [
            f"# Requirements from {a['meeting'] or 'the meeting'}",
            "",
            f"*Generated {stamp} by the Meeting Transcript to Requirements agent. Every item "
            "below quotes the line it came from, and every quote was checked against the "
            "transcript before it was accepted.*",
            "",
            "## At a glance",
            "",
            "| | |",
            "|---|---|",
            f"| Meeting | {a['meeting']} |",
            f"| Present | {', '.join(a['speakers']) or 'not attributed'} |",
            f"| Turns reviewed | {a['turns_sent']} of {a['turns_total']} |",
            f"| Items proposed | {a['proposed']} |",
            f"| **Verified** | **{a['verified_count']}** |",
            f"| Rejected | {a['rejected_count']} |",
            "",
        ]
        if a["turns_omitted"]:
            out.extend([
                f"> {len(a['turns_omitted'])} turns did not fit the model's budget and were "
                "never reviewed. This meeting is not fully covered - split the transcript or "
                "raise the budget before treating this list as complete.",
                "",
            ])

        labels = {"requirement": "Requirements", "action_item": "Action items",
                  "decision": "Decisions", "open_question": "Open questions"}
        for category, heading in labels.items():
            items = [v for v in a["verified"] if v["category"] == category]
            if not items:
                continue
            out.extend([f"## {heading} ({len(items)})", ""])
            for item in items:
                stamp_bit = f" at {item['at']}" if item["at"] else ""
                out.append(f"**{item['text']}**")
                out.append("")
                out.append(f"> {item['quote']}")
                out.append("")
                out.append(f"— {item['said_by']}{stamp_bit} ({item['turn_id']})")
                out.append("")

        if not a["verified"]:
            out.extend([
                "## Nothing was agreed",
                "",
                "No item survived verification. That is a real result, not a failure: some "
                "meetings do not produce requirements, and a list invented to fill the gap "
                "would be worse than an empty one.",
                "",
            ])

        if a["rejected"]:
            out.extend([
                f"## Rejected ({a['rejected_count']})",
                "",
                "These were proposed and thrown out. They are printed because a silent drop is "
                "indistinguishable from a filter that stopped working.",
                "",
                "| Proposed | Why it was rejected |",
                "|---|---|",
            ])
            for item in a["rejected"]:
                text = (item.get("text") or "(empty)").replace("|", "\\|")
                out.append(f"| {text[:90]} | {item.get('reason', '')} |")
            out.append("")

        out.extend([
            "---",
            "",
            "## How to read this",
            "",
            "Every verified item quotes a line somebody actually said, and the attribution "
            "comes from the transcript rather than from the model. What the agent cannot do is "
            "know whether an agreement was *meant* as a commitment - a firm \"we will\" and a "
            "thinking-aloud \"we could\" read alike in text. Check the quote before raising the "
            "ticket.",
            "",
        ])
        return "\n".join(out)

    # -------------------------------------------------------------- writing

    def _write(self) -> dict:
        folder_raw = (self.output_dir or "").strip().strip('"').strip("'")
        if not folder_raw:
            msg = "Set a reports folder on the Requirements Writer."
            raise ValueError(msg)
        folder = Path(folder_raw).expanduser()
        folder.mkdir(parents=True, exist_ok=True)

        a = self._analyse(folder)

        name = Path((self.report_name or "requirements_report.md").strip()).name
        name = name or "requirements_report.md"
        if not name.endswith(".md"):
            name += ".md"
        report_path = folder / name
        report = self._compose(a)
        report_path.write_text(report if report.endswith("\n") else report + "\n", encoding="utf-8")

        issues_path = folder / self.ISSUES_FILE
        issues_path.write_text(json.dumps({
            "meeting": a["meeting"],
            "source": a["source"],
            "issues": [{**v["jira"], "description":
                        f"{v['text']}\n\nSaid by {v['said_by']}"
                        f"{' at ' + v['at'] if v['at'] else ''} ({v['turn_id']}):\n"
                        f"\"{v['quote']}\"\n\nExtracted from {a['source']}."}
                       for v in a["verified"]],
            "rejected": a["rejected"],
        }, indent=2, ensure_ascii=False), encoding="utf-8")

        return {
            "report": str(report_path),
            "report_lines": len(report.splitlines()),
            "issues_json": str(issues_path),
            "meeting": a["meeting"],
            "proposed": a["proposed"],
            "verified_count": a["verified_count"],
            "rejected_count": a["rejected_count"],
            "counts": a["counts"],
            "turns_omitted": len(a["turns_omitted"]),
        }

    def write_report(self) -> Message:
        r = self._write()
        c = r["counts"]
        self.status = f"{r['verified_count']} verified, {r['rejected_count']} rejected"
        lines = [
            f"{r['meeting']}: {r['verified_count']} of {r['proposed']} proposed items verified "
            f"against the transcript.",
            f"{c['requirement']} requirements, {c['action_item']} action items, "
            f"{c['decision']} decisions, {c['open_question']} open questions.",
        ]
        if r["rejected_count"]:
            lines.append(f"{r['rejected_count']} rejected - nobody said them, or they had no quote.")
        if r["turns_omitted"]:
            lines.append(f"WARNING: {r['turns_omitted']} turns were never reviewed.")
        lines.extend([
            "",
            f"Report: {r['report']}  ({r['report_lines']} lines)",
            f"Issues: {r['issues_json']}",
        ])
        return Message(text="\n".join(lines))

    def write_details(self) -> Data:
        r = self._write()
        self.status = f"{r['verified_count']} verified, {r['rejected_count']} rejected"
        return Data(data=r)
