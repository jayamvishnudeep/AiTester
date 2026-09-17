"""Page Object Writer - a Langflow custom component.

Takes the model's reply and writes Page Object classes to disk as TypeScript.

Naming is the part worth doing in code. A Page Object file is named after the
class inside it - `LoginPage.ts` holds `class LoginPage` - and a model asked to
also invent a file name will sometimes disagree with itself between the marker
and the class it wrote. So the class wins: the file is named after the class it
actually contains, and a `// file:` marker is only a fallback for a reply that
somehow has no class in it.

Everything else is the mechanical work of turning a chat reply into a file:
find the code inside the fences, drop the commentary around it, and never let
the model choose a folder.
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
_MARKER = re.compile(r"^[ \t]*(?://|/\*)\s*file:\s*([^\s*]+)", re.MULTILINE)
_CLASS = re.compile(r"^[ \t]*(?:export[ \t]+(?:default[ \t]+)?)?class[ \t]+([A-Za-z_]\w*)",
                    re.MULTILINE)
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")

# What a Page Object is made of, for the summary line.
_LOCATOR = re.compile(r"^\s*(?:readonly\s+|private\s+|public\s+)*[A-Za-z_]\w*\s*[:=]", re.MULTILINE)
_METHOD = re.compile(r"^\s*(?:public\s+|private\s+)?async\s+([A-Za-z_]\w*)\s*\(", re.MULTILINE)

_CODE_START = ("//", "/*", "*", "import ", "export ", "const ", "let ", "var ",
               "readonly ", "private ", "public ", "await ", "async ", "class ",
               "function ", "return ", "if ", "for ", "}", ")", "@", "{")
_CODE_END = ("{", "}", ";", ")", ",", "*/", "=>", "[", "]")


class PageObjectWriter(Component):
    display_name = "Page Object Writer"
    description = "Strips the prose off a generated Page Object and writes it as TypeScript."
    documentation = "https://playwright.dev/docs/pom"
    icon = "file-code"
    name = "PageObjectWriter"

    # below this, the input is not a DOM snapshot
    MIN_HTML = 40

    inputs = [
        MessageTextInput(
            name="generated",
            display_name="Generated code",
            info="The model's reply. Fences and commentary are removed before writing.",
            value="",
            required=True,
        ),
        MessageTextInput(
            name="source_html",
            display_name="Source HTML (guard)",
            info=(
                "The snapshot the class was generated from. Wire the input node here. "
                "With nothing in it the component refuses to write, because a model given "
                "no HTML invents a plausible page that does not exist."
            ),
            value="",
        ),
        MessageTextInput(
            name="output_dir",
            display_name="Output folder",
            info="Where the .ts files are written. Created if it does not exist.",
            value="",
        ),
        MessageTextInput(
            name="default_name",
            display_name="Default file name",
            info="Used only when the reply has neither a class nor a '// file:' marker.",
            value="PageObject.ts",
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
        p = Path(name)
        return p.stem, p.suffix or ".ts"

    @staticmethod
    def _safe_name(name: str) -> str:
        """A file name, never a path - the model does not get to choose a folder."""
        stem = _SAFE.sub("-", Path(str(name).strip()).name).strip("-.")
        if not stem:
            stem = "PageObject.ts"
        if not stem.endswith(".ts"):
            stem += ".ts"
        return stem

    @classmethod
    def _name_for(cls, code: str, marker: str, default: str) -> str:
        """The class the file defines wins; the marker is only a fallback."""
        found = _CLASS.search(code or "")
        if found:
            return cls._safe_name(found.group(1))
        if marker:
            return cls._safe_name(marker)
        return cls._safe_name(default or "PageObject.ts")

    # ----------------------------------------------------------- extracting

    @staticmethod
    def _is_prose(line: str) -> bool:
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
        while lines and (not lines[-1].strip() or cls._is_prose(lines[-1])):
            lines.pop()
        return "\n".join(lines).strip()

    @classmethod
    def _code_of(cls, chunk: str) -> str:
        fenced = _FENCE_ANY.search(chunk or "")
        return cls._clean(fenced.group(1) if fenced else chunk)

    def _split(self, text: str) -> list:
        """Return [(file name, code)] from the model's reply."""
        raw = (text or "").strip()
        if not raw:
            msg = "The model returned nothing to write."
            raise ValueError(msg)

        blocks = _FENCE_ANY.findall(raw)
        # Unwrap the outer fence only when the whole reply IS one fence, or a
        # multi-block reply would be swallowed into one arbitrary block.
        body = blocks[0] if (len(blocks) == 1 and _FENCE_WHOLE.match(raw)) else raw
        default = self.default_name or "PageObject.ts"

        markers = list(_MARKER.finditer(body))
        if markers:
            files = []
            for i, m in enumerate(markers):
                newline = body.find("\n", m.end())
                start = len(body) if newline == -1 else newline + 1
                end = markers[i + 1].start() if i + 1 < len(markers) else len(body)
                code = self._code_of(body[start:end])
                if code:
                    files.append((self._name_for(code, m.group(1), default), code))
            if not files:
                msg = "No code was found in the model's reply."
                raise ValueError(msg)
            return files

        if len(blocks) > 1:
            files = []
            for i, block in enumerate(blocks):
                code = self._clean(block)
                if not code:
                    continue
                stem, suffix = self._split_name(self._safe_name(default))
                fallback = f"{stem}-{i + 1}{suffix}"
                files.append((self._name_for(code, "", fallback), code))
            if not files:
                msg = "No code was found in the model's reply."
                raise ValueError(msg)
            return files

        code = self._clean(blocks[0] if blocks else body)
        if not code:
            msg = "No code was found in the model's reply."
            raise ValueError(msg)
        return [(self._name_for(code, "", default), code)]

    # -------------------------------------------------------------- writing

    def _write(self) -> dict:
        # Refuse before writing anything if no HTML reached this component. A model
        # asked for a Page Object with no page in front of it does not say so - it
        # invents a believable login form, which is the worst thing to write out.
        html = (self.source_html or "").strip()
        if not html:
            msg = ("No HTML reached this component, so anything generated from it is "
                   "invention. Put a DOM snapshot in the input node, or wire it to the "
                   "'Source HTML (guard)' field.")
            raise ValueError(msg)
        if len(html) < self.MIN_HTML or "<" not in html:
            msg = (f"The guard input does not look like a DOM snapshot ({len(html)} "
                   "characters, no tags). Paste the element's outerHTML.")
            raise ValueError(msg)

        files = self._split(self.generated)

        folder_raw = (self.output_dir or "").strip().strip('"').strip("'")
        if not folder_raw:
            msg = "Set an output folder on the Page Object Writer."
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
            klass = _CLASS.search(code)
            methods = _METHOD.findall(code)
            written.append({
                "file": path.name,
                "path": str(path),
                "class": klass.group(1) if klass else "",
                "lines": len(code.splitlines()),
                "locators": len(_LOCATOR.findall(code)),
                "methods": methods,
                "method_count": len(methods),
            })

        return {"folder": str(folder), "written": written,
                "file_count": len(written),
                "method_count": sum(w["method_count"] for w in written)}

    # -------------------------------------------------------------- outputs

    def write_files(self) -> Message:
        result = self._write()
        n = result["file_count"]
        lines = [
            f"Wrote {n} Page Object {'class' if n == 1 else 'classes'}.",
            "",
            f"Folder: {result['folder']}",
            "",
        ]
        for w in result["written"]:
            lines.append(f"- {w['file']} — {w['locators']} locators, "
                         f"{w['method_count']} methods, {w['lines']} lines")
            if w["methods"]:
                lines.append(f"    {', '.join(w['methods'][:8])}")
        self.status = f"{n} classes, {result['method_count']} methods"
        return Message(text="\n".join(lines))

    def write_details(self) -> Data:
        result = self._write()
        self.status = f"{result['file_count']} classes, {result['method_count']} methods"
        return Data(data=result)
