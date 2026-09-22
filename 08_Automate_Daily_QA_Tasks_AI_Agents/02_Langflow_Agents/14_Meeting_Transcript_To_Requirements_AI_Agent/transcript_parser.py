"""Transcript Parser - a Langflow custom component.

Reads a meeting transcript and hands the model the part of it that could
possibly contain a commitment.

A transcript is mostly not requirements. Greetings, "you're on mute",
scheduling chatter and one-word acknowledgements are the bulk of the lines, and
the few turns that actually commit to something are scattered among them. This
component parses the three formats a QA lead is likely to have - Zoom's WEBVTT,
the plain text Teams exports, and a bare "Name: text" log - splits it into
attributed turns, drops the filler, and passes on what is left with the speaker
and timestamp still attached to every line.

The attribution is the part that matters later. Every turn keeps a stable id, so
when the model claims a requirement was agreed, the claim can be checked against
the exact line it came from rather than taken on trust. Extracting requirements
is a language problem and the model does that work; proving the requirement was
actually said is a lookup, and lookups belong in code.

Nothing here decides what a requirement is. It decides what could not possibly
be one.
"""

import json
import re
from pathlib import Path

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, IntInput, MessageTextInput, MultilineInput, Output
from lfx.schema.data import Data
from lfx.schema.message import Message

_WEBVTT_TIME = re.compile(
    r"^(\d{2}:)?\d{2}:\d{2}[.,]\d{3}\s*-->\s*(\d{2}:)?\d{2}:\d{2}[.,]\d{3}")
_CUE_NUMBER = re.compile(r"^\d+$")
# "Priya Sharma: text"  /  "Priya Sharma (Guest): text"
_INLINE_SPEAKER = re.compile(r"^\s*([A-Z][\w.'-]*(?:\s+[A-Z][\w.'-]*){0,3})\s*(?:\([^)]*\))?\s*:\s*(.+)$")
# Teams: "Priya Sharma   0:14"  on its own line, text on the next
_TEAMS_SPEAKER = re.compile(r"^\s*([A-Z][\w.'-]*(?:\s+[A-Z][\w.'-]*){0,3})\s{2,}(\d{1,2}:\d{2}(?::\d{2})?)\s*$")

# Turns that cannot carry a commitment. Matched on the whole utterance, not on a
# substring: "okay" is filler, "okay, tax goes on its own line" is not.
_FILLER_EXACT = {
    "yes", "yeah", "yep", "no", "nope", "ok", "okay", "sure", "right", "mm", "mhm",
    "mmhm", "uh huh", "hmm", "cool", "great", "thanks", "thank you", "cheers",
    "bye", "goodbye", "see you", "morning", "good morning", "afternoon", "hi",
    "hi everyone", "hello", "hey", "same", "agreed", "understood", "got it",
    "sounds right", "sounds good", "fair enough", "will do", "please", "exactly",
    "of course", "no worries", "sorry", "my bad", "true", "indeed", "fine",
}
_FILLER_PATTERNS = [
    re.compile(r"^(?:you'?re|you are) on mute\b", re.I),
    re.compile(r"^can you hear me\b", re.I),
    re.compile(r"^(?:sorry|sorry,?\s*sorry)[,.\s]*$", re.I),
    re.compile(r"^(?:are we all here|is everyone here)\b", re.I),
    re.compile(r"^(?:how was|how's) (?:the )?(?:your )?weekend\b", re.I),
    re.compile(r"^(?:i|we) should (?:jump|hop) (?:on|off)\b", re.I),
    re.compile(r"^catch you later\b", re.I),
    re.compile(r"^(?:that'?s me|that is me)[.,\s]*(?:thanks)?[.\s]*$", re.I),
]


class TranscriptParser(Component):
    display_name = "Transcript Parser"
    description = "Parses a meeting transcript into attributed turns and drops the filler."
    documentation = "https://developer.mozilla.org/en-US/docs/Web/API/WebVTT_API"
    icon = "captions"
    name = "TranscriptParser"

    inputs = [
        MessageTextInput(
            name="transcript_path",
            display_name="Transcript path",
            info="A .vtt, .txt or .md transcript. Leave empty to use the pasted transcript below.",
            value="",
            tool_mode=True,
        ),
        MessageTextInput(
            name="default_transcript_path",
            display_name="Default transcript path",
            info="Used whenever the path above is empty or does not exist.",
            value="",
        ),
        MultilineInput(
            name="pasted_transcript",
            display_name="Pasted transcript",
            info="Paste a transcript here instead of reading one from disk.",
            value="",
            advanced=True,
        ),
        MessageTextInput(
            name="meeting_title",
            display_name="Meeting title",
            info="Used in the report and in the Jira summaries. Empty means the file name.",
            value="",
        ),
        IntInput(
            name="min_words",
            display_name="Minimum words in a turn",
            info="Turns shorter than this carry no commitment and are dropped.",
            value=4,
            advanced=True,
        ),
        IntInput(
            name="max_brief_chars",
            display_name="Maximum characters sent to the model",
            info=(
                "A transcript longer than this is cut, and the cut is reported rather than "
                "hidden - the turns that did not fit are named in the output."
            ),
            value=12000,
            advanced=True,
        ),
        BoolInput(
            name="drop_filler",
            display_name="Drop filler turns",
            info="Off sends every turn, which is slower and rarely better.",
            value=True,
            advanced=True,
        ),
        MessageTextInput(
            name="output_dir",
            display_name="Reports folder",
            info=(
                "Where transcript_turns.json is written. The requirements writer reads it back "
                "from here to verify quotes, so both nodes must point at the same folder."
            ),
            value="",
        ),
    ]

    outputs = [
        Output(display_name="Brief", name="brief", method="build_brief"),
        Output(display_name="Turns", name="turns", method="build_turns"),
    ]

    # ------------------------------------------------------------- loading

    def _source(self) -> tuple:
        pasted = (self.pasted_transcript or "").strip()
        if pasted:
            return pasted, "pasted transcript"
        for candidate in (self.transcript_path, self.default_transcript_path):
            cleaned = (candidate or "").strip().strip('"').strip("'")
            if cleaned and Path(cleaned).is_file():
                try:
                    return Path(cleaned).read_text(encoding="utf-8", errors="replace"), cleaned
                except OSError as exc:
                    msg = f"Could not read {cleaned} - {exc}"
                    raise ValueError(msg) from exc
        msg = (
            "No transcript reached this component. A model asked what was agreed in a meeting "
            "it cannot see will write a plausible set of requirements that nobody said, and "
            "there is no way to tell those apart from real ones afterwards. Set 'Default "
            "transcript path', or paste a transcript."
        )
        raise ValueError(msg)

    # ------------------------------------------------------------- parsing

    @classmethod
    def _parse(cls, text: str) -> tuple:
        """(turns, format). A turn is {id, speaker, time, text}."""
        raw_lines = text.splitlines()
        if any(line.strip().upper().startswith("WEBVTT") for line in raw_lines[:3]):
            return cls._parse_vtt(raw_lines), "webvtt"

        turns, fmt = cls._parse_teams(raw_lines)
        if turns:
            return turns, fmt
        return cls._parse_inline(raw_lines), "inline"

    @staticmethod
    def _parse_vtt(lines: list) -> list:
        turns, time = [], ""
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.upper().startswith("WEBVTT") or _CUE_NUMBER.match(stripped):
                continue
            timing = _WEBVTT_TIME.match(stripped)
            if timing:
                time = stripped.split("-->")[0].strip()
                continue
            found = _INLINE_SPEAKER.match(stripped)
            speaker, body = (found.group(1), found.group(2)) if found else ("", stripped)
            if turns and not found and turns[-1]["time"] == time:
                turns[-1]["text"] += " " + body
                continue
            turns.append({"id": f"T{len(turns) + 1}", "speaker": speaker.strip(),
                          "time": time, "text": body.strip()})
        return turns

    @staticmethod
    def _parse_teams(lines: list) -> tuple:
        turns, speaker, time, buffer = [], "", "", []

        def flush():
            if speaker and buffer:
                turns.append({"id": f"T{len(turns) + 1}", "speaker": speaker,
                              "time": time, "text": " ".join(buffer).strip()})

        for line in lines:
            header = _TEAMS_SPEAKER.match(line.rstrip())
            if header:
                flush()
                speaker, time, buffer = header.group(1).strip(), header.group(2), []
                continue
            if line.strip():
                buffer.append(line.strip())
        flush()
        return (turns, "teams") if turns else ([], "")

    @staticmethod
    def _parse_inline(lines: list) -> list:
        turns = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            found = _INLINE_SPEAKER.match(stripped)
            if found:
                turns.append({"id": f"T{len(turns) + 1}", "speaker": found.group(1).strip(),
                              "time": "", "text": found.group(2).strip()})
            elif turns:
                turns[-1]["text"] += " " + stripped
        return turns

    # ------------------------------------------------------------ filtering

    @classmethod
    def _is_filler(cls, text: str, min_words: int) -> bool:
        cleaned = re.sub(r"[^\w\s']", " ", text).strip().lower()
        cleaned = re.sub(r"\s+", " ", cleaned)
        if not cleaned:
            return True
        if cleaned in _FILLER_EXACT:
            return True
        if any(p.match(text.strip()) for p in _FILLER_PATTERNS):
            return True
        return len(cleaned.split()) < max(int(min_words), 1)

    # ----------------------------------------------------------- analysing

    def _analyse(self) -> dict:
        text, origin = self._source()
        turns, fmt = self._parse(text)
        if not turns:
            msg = (
                f"No speaker turns were found in {origin}. This parser reads Zoom WEBVTT, the "
                "plain text Microsoft Teams export, and a simple 'Name: what they said' log. "
                "Without attributed turns there is nothing to trace a requirement back to."
            )
            raise ValueError(msg)

        min_words = max(int(self.min_words or 4), 1)
        drop = bool(self.drop_filler)
        kept, dropped = [], []
        for turn in turns:
            if drop and self._is_filler(turn["text"], min_words):
                dropped.append(turn)
            else:
                kept.append(turn)

        if not kept:
            msg = (
                f"Every one of the {len(turns)} turns in this transcript is filler - greetings, "
                "acknowledgements and chatter. There is nothing in it that could carry a "
                "requirement, and a model asked to find some anyway would invent them."
            )
            raise ValueError(msg)

        budget = max(int(self.max_brief_chars or 12000), 500)
        sent, omitted, used = [], [], 0
        for turn in kept:
            line = self._render(turn)
            if used + len(line) > budget and sent:
                omitted.append(turn)
                continue
            sent.append(turn)
            used += len(line)

        speakers = sorted({t["speaker"] for t in turns if t["speaker"]})
        title = (self.meeting_title or "").strip() or Path(origin).stem.replace("_", " ")
        return {
            "meeting": title,
            "source": origin,
            "format": fmt,
            "speakers": speakers,
            "turns_total": len(turns),
            "turns_filler": len(dropped),
            "turns_kept": len(kept),
            "turns_sent": len(sent),
            "turns_omitted": [{"id": t["id"], "speaker": t["speaker"], "time": t["time"]} for t in omitted],
            "filler_ratio": round(len(dropped) / len(turns), 4) if turns else 0.0,
            "sent": sent,
            "all_turns": turns,
        }

    @staticmethod
    def _render(turn: dict) -> str:
        stamp = f" [{turn['time']}]" if turn["time"] else ""
        who = turn["speaker"] or "unknown"
        return f"({turn['id']}){stamp} {who}: {turn['text']}\n"

    # -------------------------------------------------------------- disk

    TURNS_FILE = "transcript_turns.json"

    def _persist(self, analysis: dict) -> None:
        """The writer reads this back to check the model's quotes are real.

        It is also the reason a requirement can be argued with: every line the
        model was shown is on disk with the speaker and timestamp attached, so
        "who agreed to this" has an answer that is not a recollection.
        """
        folder_raw = (self.output_dir or "").strip().strip('"').strip("'")
        if not folder_raw:
            return
        folder = Path(folder_raw).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
        (folder / self.TURNS_FILE).write_text(
            json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------ outputs

    def _brief_text(self, a: dict) -> str:
        lines = [
            f"# {a['meeting']}", "",
            f"Format: {a['format']}   Speakers: {', '.join(a['speakers']) or 'not attributed'}",
            f"Turns: {a['turns_total']} total, {a['turns_filler']} filler dropped "
            f"({a['filler_ratio']:.0%}), {a['turns_sent']} below",
        ]
        if a["turns_omitted"]:
            lines.append(f"WARNING: {len(a['turns_omitted'])} turns did not fit the budget and are "
                         "NOT below. Do not treat this transcript as fully reviewed.")
        lines.extend(["", "## Transcript", ""])
        for turn in a["sent"]:
            lines.append(self._render(turn).rstrip())
        return "\n".join(lines)

    def build_brief(self) -> Message:
        a = self._analyse()
        self._persist(a)
        self.status = self._status(a)
        return Message(text=self._brief_text(a))

    def build_turns(self) -> Data:
        a = self._analyse()
        self._persist(a)
        self.status = self._status(a)
        return Data(data=a)

    @staticmethod
    def _status(a: dict) -> str:
        return f"{a['turns_sent']}/{a['turns_total']} turns, {a['filler_ratio']:.0%} filler"
