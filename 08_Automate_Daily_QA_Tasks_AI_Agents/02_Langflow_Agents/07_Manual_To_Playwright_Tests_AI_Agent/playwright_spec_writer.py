"""Playwright Spec Writer - a Langflow custom component.

Takes whatever the model wrote and turns it into files on disk.

A language model asked for code returns prose around it: a fenced block, a
sentence of explanation, sometimes a "Here you go:". None of that belongs in a
.spec.ts file, and a tester should not have to strip it by hand. This component
does the mechanical part - find the code, name the file, write it - so the model
is only ever responsible for the code itself.

It writes one file per `// file: name.spec.ts` marker. With no markers it writes
a single file under the configured default name, so a simple prompt still works.
"""

import re
from pathlib import Path

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, MessageTextInput, Output
from lfx.schema.data import Data
from lfx.schema.message import Message

# One fenced block. Non-greedy and unanchored, so it stops at the FIRST closing
# fence rather than running on to the last one in the reply.
_FENCE_ANY = re.compile(r"```[a-zA-Z]*[ \t]*\n(.*?)\n?[ \t]*```", re.DOTALL)
# The whole reply as a single fence. Only trusted when there is exactly one block.
_FENCE_WHOLE = re.compile(r"^\s*```[a-zA-Z]*[ \t]*\n(.*?)\n?[ \t]*```\s*$", re.DOTALL)
# A file marker the prompt asks the model to emit above each block. The name is
# captured; whatever else is on that line is skipped with it.
_MARKER = re.compile(r"^[ \t]*(?://|/\*)\s*file:\s*([^\s*]+)", re.MULTILINE)
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")

# Line openings and endings that mean "this is code, not commentary".
_CODE_START = ("//", "/*", "*", "import ", "export ", "const ", "let ", "var ",
               "test", "await ", "expect", "async ", "function ", "class ", "return ",
               "if ", "for ", "}", ")", "@", "{")
_CODE_END = ("{", "}", ";", ")", ",", "*/", "=>", "[", "]")


class PlaywrightSpecWriter(Component):
    display_name = "Playwright Spec Writer"
    description = "Strips the prose off generated code and writes .spec.ts files."
    documentation = "https://playwright.dev/docs/writing-tests"
    icon = "file-code"
    name = "PlaywrightSpecWriter"

    # how much text counts as a real set of manual steps rather than a stray word
    MIN_STEPS = 40

    inputs = [
        MessageTextInput(
            name="generated",
            display_name="Generated code",
            info="The model's reply. Fences and commentary are removed before writing.",
            value="",
            required=True,
        ),
        MessageTextInput(
            name="source_steps",
            display_name="Manual steps (guard)",
            info=(
                "The manual cases the code was generated from. Wire the input node here. "
                "With nothing in it the component refuses to write, because a model given an "
                "empty brief returns confident, well-formed, entirely invented tests."
            ),
            value="",
        ),
        MessageTextInput(
            name="output_dir",
            display_name="Output folder",
            info="Where the .spec.ts files are written. Created if it does not exist.",
            value="",
        ),
        MessageTextInput(
            name="default_name",
            display_name="Default file name",
            info="Used when the model emits no '// file:' marker.",
            value="generated.spec.ts",
        ),
        BoolInput(
            name="overwrite",
            display_name="Overwrite existing files",
            info="Off: an existing file is kept and a numbered copy is written beside it.",
            value=True,
        ),
    ]

    outputs = [
        Output(display_name="Summary", name="summary", method="write_files"),
        Output(display_name="Details", name="details", method="write_details"),
    ]

    # ------------------------------------------------------------- naming

    @staticmethod
    def _split_name(name: str) -> tuple:
        """Stem and suffix, honouring the double extension in '.spec.ts'."""
        if name.endswith(".spec.ts"):
            return name[: -len(".spec.ts")], ".spec.ts"
        p = Path(name)
        return p.stem, p.suffix or ".ts"

    @classmethod
    def _safe_name(cls, name: str) -> str:
        """A file name, never a path - the model does not get to choose a folder."""
        stem = _SAFE.sub("-", Path(name.strip()).name).strip("-.")
        if not stem:
            stem = "generated.spec.ts"
        if not stem.endswith(".ts"):
            stem += ".spec.ts" if not stem.endswith(".spec") else ".ts"
        return stem

    # ----------------------------------------------------------- extracting

    @staticmethod
    def _is_prose(line: str) -> bool:
        """A line that reads like a sentence about the code rather than code."""
        s = line.strip()
        if not s or s.startswith(_CODE_START) or s.endswith(_CODE_END):
            return False
        return " " in s

    @classmethod
    def _clean(cls, code: str) -> str:
        """Drop stray fences, and commentary on either side of the code."""
        lines = [ln for ln in (code or "").splitlines() if not ln.strip().startswith("```")]
        while lines and not lines[0].strip():
            lines.pop(0)
        if lines and cls._is_prose(lines[0]):
            lines.pop(0)
        # a closing paragraph after the code is just as unwelcome as a leading one
        while lines and (not lines[-1].strip() or cls._is_prose(lines[-1])):
            lines.pop()
        return "\n".join(lines).strip()

    @classmethod
    def _code_of(cls, chunk: str) -> str:
        """The code in one chunk: the fenced part if there is one, else the chunk."""
        fenced = _FENCE_ANY.search(chunk or "")
        return cls._clean(fenced.group(1) if fenced else chunk)

    def _split(self, text: str) -> list:
        """Return [(file name, code)] from the model's reply."""
        raw = (text or "").strip()
        if not raw:
            msg = "The model returned nothing to write."
            raise ValueError(msg)

        blocks = _FENCE_ANY.findall(raw)
        # Unwrap the outer fence only when the whole reply IS one fence. Doing it
        # on a multi-block reply would swallow the fences in between and keep one
        # arbitrary block as if it were the whole answer.
        body = blocks[0] if (len(blocks) == 1 and _FENCE_WHOLE.match(raw)) else raw

        markers = list(_MARKER.finditer(body))
        if markers:
            files = []
            for i, m in enumerate(markers):
                # start after the marker's whole LINE, so nothing else on it leaks in
                newline = body.find("\n", m.end())
                start = len(body) if newline == -1 else newline + 1
                end = markers[i + 1].start() if i + 1 < len(markers) else len(body)
                code = self._code_of(body[start:end])
                if code:
                    files.append((self._safe_name(m.group(1)), code))
            if not files:
                msg = "No code was found in the model's reply."
                raise ValueError(msg)
            return files

        default = self._safe_name(self.default_name or "generated.spec.ts")
        if len(blocks) > 1:
            stem, suffix = self._split_name(default)
            files = [(f"{stem}-{i + 1}{suffix}", self._clean(b)) for i, b in enumerate(blocks)]
            files = [(n, c) for n, c in files if c]
            if not files:
                msg = "No code was found in the model's reply."
                raise ValueError(msg)
            return files

        code = self._clean(blocks[0] if blocks else body)
        if not code:
            msg = "No code was found in the model's reply."
            raise ValueError(msg)
        return [(default, code)]

    # -------------------------------------------------------------- writing

    def _write(self) -> dict:
        # Refuse before writing anything if there were no steps to convert. An empty
        # brief does not produce an empty reply - it produces invented tests that look
        # entirely plausible, which is the worst thing this component could write.
        steps = (self.source_steps or "").strip()
        if not steps:
            msg = ("No manual steps reached this component, so anything generated from them "
                   "is invention. Put the cases in the input node, or wire it to the "
                   "'Manual steps (guard)' field.")
            raise ValueError(msg)
        if len(steps) < self.MIN_STEPS:
            msg = (f"Only {len(steps)} characters of manual steps were given. That is too "
                   "little to convert, and the model will invent the rest.")
            raise ValueError(msg)

        files = self._split(self.generated)

        folder_raw = (self.output_dir or "").strip().strip('"').strip("'")
        if not folder_raw:
            msg = "Set an output folder on the Playwright Spec Writer."
            raise ValueError(msg)
        folder = Path(folder_raw).expanduser()
        folder.mkdir(parents=True, exist_ok=True)

        written = []
        for name, code in files:
            path = folder / name
            if path.exists() and not self.overwrite:
                stem, suffix = self._split_name(name)
                n = 2
                while path.exists():
                    path = folder / f"{stem}-{n}{suffix}"
                    n += 1
            body = code if code.endswith("\n") else code + "\n"
            path.write_text(body, encoding="utf-8")
            written.append({
                "file": path.name,
                "path": str(path),
                "lines": len(code.splitlines()),
                "bytes": len(body.encode("utf-8")),
                # test( and test.only( count; test.describe( is a group, not a test
                "tests": len(re.findall(r"^\s*test\s*(?:\.(?:only|skip|fixme))?\s*\(",
                                        code, re.MULTILINE)),
            })

        return {"folder": str(folder), "written": written,
                "file_count": len(written),
                "test_count": sum(w["tests"] for w in written)}

    # -------------------------------------------------------------- outputs

    def write_files(self) -> Message:
        result = self._write()
        lines = [
            f"Wrote {result['file_count']} "
            f"{'file' if result['file_count'] == 1 else 'files'} "
            f"holding {result['test_count']} "
            f"{'test' if result['test_count'] == 1 else 'tests'}.",
            "",
            f"Folder: {result['folder']}",
            "",
        ]
        for w in result["written"]:
            lines.append(f"- {w['file']} — {w['tests']} tests, {w['lines']} lines")
        self.status = f"{result['file_count']} files, {result['test_count']} tests"
        return Message(text="\n".join(lines))

    def write_details(self) -> Data:
        result = self._write()
        self.status = f"{result['file_count']} files, {result['test_count']} tests"
        return Data(data=result)
