"""Selector Healer - a Langflow custom component.

Takes a selector that no longer finds its element and proposes one that does.

The rule that makes this safe to use is that **nothing is proposed that has not
been run against the page first**. Candidates are generated from the new DOM,
each is evaluated, and any that matches zero elements or several is thrown away
before scoring. A healed selector that resolves to nothing is worse than the
broken one it replaces, because the test now fails somewhere further along; a
healed selector that resolves to the wrong element is worse still, because the
test passes.

So the division of labour is: code reads the old element's identity, builds
candidates, evaluates them against the markup and scores them; the model is
asked only the question code cannot answer, which is whether the surviving
candidate is really the same thing the test meant.

Three outcomes other than a heal are first-class results, not errors:

- **not_broken** - the selector still resolves. Nothing to do, and saying so is
  more useful than quietly proposing a replacement nobody needed.
- **ambiguous** - several candidates are equally good. Picking one would be a
  coin flip that looks like an answer.
- **gone** - nothing in the new page plausibly corresponds to the old element.
  The feature was removed and the test needs rewriting, not a new selector.

No browser is involved. CSS is evaluated with soupsieve, which is a real
selector engine rather than a lookalike. XPath, which is what most Selenium
suites break on, is translated into CSS over a documented subset and evaluated
the same way; an XPath outside that subset degrades to a thin identity read from
the selector text and says so, which is better than a second parser whose
elements the first one cannot recognise. Nothing emitted is ever XPath.
"""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from lfx.custom.custom_component.component import Component
from lfx.io import IntInput, MessageTextInput, MultilineInput, Output
from lfx.schema.data import Data
from lfx.schema.message import Message

PARSER = "html.parser"

# Attributes a team puts on an element specifically so tests can find it.
_TESTID_ATTRS = ("data-testid", "data-test-id", "data-test", "data-qa", "data-cy", "data-automation-id")

# An id that looks generated rather than authored. Healing onto one of these
# produces a selector that breaks on the next render, which is a worse outcome
# than the break being fixed, because it looks fixed.
_GENERATED_ID = re.compile(
    r"^(?::r[0-9a-z]+:|[0-9a-f]{8}-[0-9a-f]{4}|mui-\d+|radix-|headlessui-|ember\d+|react-aria-\d+|:\w+:)"
    r"|^[a-z]+[-_]?\d{6,}$|^[0-9a-f]{16,}$",
    re.IGNORECASE,
)

# Class names that describe how a thing looks, not what it is. These are the
# classes that changed in the first place, so they are never used to heal.
_STYLING_CLASS = re.compile(
    r"^(?:[a-z]+:)?(?:text|bg|border|p|px|py|pt|pb|pl|pr|m|mx|my|mt|mb|ml|mr|w|h|min|max|flex|grid|gap|"
    r"items|justify|self|order|rounded|shadow|opacity|z|top|left|right|bottom|col|row|space|divide|"
    r"font|leading|tracking|uppercase|lowercase|truncate|overflow|absolute|relative|fixed|sticky|block|"
    r"inline|hidden|table|transition|duration|ease|transform|scale|rotate|translate|cursor|select|"
    r"pointer|ring|outline|underline|tabular|grow|shrink|basis|container|mx|antialiased)"
    r"(?:-|$)",
    re.IGNORECASE,
)

_WS = re.compile(r"\s+")

# tag -> implicit ARIA role, for the role+name rung of the ladder.
_IMPLICIT_ROLE = {
    "button": "button", "a": "link", "select": "combobox", "textarea": "textbox",
    "h1": "heading", "h2": "heading", "h3": "heading", "h4": "heading",
    "h5": "heading", "h6": "heading", "img": "img", "nav": "navigation",
    "main": "main", "table": "table", "ul": "list", "ol": "list", "li": "listitem",
    "form": "form", "header": "banner", "footer": "contentinfo", "aside": "complementary",
    "section": "region", "dialog": "dialog", "progress": "progressbar",
}
_INPUT_ROLE = {
    "text": "textbox", "email": "textbox", "tel": "textbox", "url": "textbox",
    "password": "textbox", "search": "searchbox", "number": "spinbutton",
    "checkbox": "checkbox", "radio": "radio", "range": "slider",
    "submit": "button", "button": "button", "reset": "button", "image": "button",
}

# Attributes that say what an element IS rather than how it looks.
_STABLE_ATTRS = ("name", "type", "href", "placeholder", "alt", "title", "value", "for", "autocomplete")


def _norm(text: str) -> str:
    return _WS.sub(" ", (text or "").strip())


def _looks_like_xpath(selector: str) -> bool:
    s = (selector or "").strip()
    return s.startswith(("/", "(", "./")) or s.startswith("xpath=") or "//" in s


class SelectorHealer(Component):
    display_name = "Selector Healer"
    description = "Proposes a verified replacement for a selector that no longer finds its element."
    documentation = "https://playwright.dev/docs/locators"
    icon = "wrench"
    name = "SelectorHealer"

    inputs = [
        MessageTextInput(
            name="broken_selectors",
            display_name="Broken selectors",
            info=(
                "A path to a file of selectors, one per line, or the selectors themselves. "
                "Blank lines and # comments are ignored."
            ),
            value="",
            tool_mode=True,
        ),
        MessageTextInput(
            name="default_selectors",
            display_name="Default broken selectors",
            info="Used whenever the field above is empty. A path, or the selectors themselves.",
            value="",
        ),
        MessageTextInput(
            name="dom_after_path",
            display_name="Current DOM path",
            info="Path to an HTML snapshot of the page as it is now.",
            value="",
        ),
        MultilineInput(
            name="dom_after",
            display_name="Current DOM",
            info="Paste the current HTML here instead of reading it from disk.",
            value="",
            advanced=True,
        ),
        MessageTextInput(
            name="dom_before_path",
            display_name="Previous DOM path",
            info=(
                "Optional. A snapshot from when the selector still worked. With it the healer "
                "knows what the element actually was; without it, it can only infer the "
                "element's identity from the selector text."
            ),
            value="",
        ),
        MultilineInput(
            name="dom_before",
            display_name="Previous DOM",
            info="Paste the previous HTML here instead of reading it from disk.",
            value="",
            advanced=True,
        ),
        IntInput(
            name="heal_threshold",
            display_name="Heal threshold (0-100)",
            info="Below this score the element is reported as gone rather than healed.",
            value=45,
            advanced=True,
        ),
        IntInput(
            name="ambiguity_margin",
            display_name="Ambiguity margin",
            info=(
                "If the best candidate beats the runner-up by less than this, the result is "
                "reported as ambiguous rather than picking between them."
            ),
            value=12,
            advanced=True,
        ),
        MessageTextInput(
            name="output_dir",
            display_name="Reports folder",
            info=(
                "Where healed_selectors.json is written. The report writer reads it back from "
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

    @staticmethod
    def _read(path_field: str, pasted: str, label: str, required: bool) -> str:
        pasted = (pasted or "").strip()
        if pasted:
            return pasted
        cleaned = (path_field or "").strip().strip('"').strip("'")
        if cleaned and Path(cleaned).is_file():
            try:
                return Path(cleaned).read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                msg = f"Could not read {label} from {cleaned} - {exc}"
                raise ValueError(msg) from exc
        if required:
            msg = (
                f"No {label} reached this component. Without the page markup there is nothing "
                "to verify a healed selector against, and a selector that has not been run "
                "against the page is a guess. Set the path field or paste the HTML."
            )
            raise ValueError(msg)
        return ""

    def _selector_list(self) -> list:
        raw = (self.broken_selectors or "").strip().strip('"').strip("'")
        if not raw:
            raw = (self.default_selectors or "").strip().strip('"').strip("'")
        if not raw:
            msg = ("No broken selectors were given. Put a selector, or a path to a file of them, "
                   "in the input node, or set 'Default broken selectors' on the Selector Healer.")
            raise ValueError(msg)
        if Path(raw).is_file():
            try:
                raw = Path(raw).read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                msg = f"Could not read the selector list from {raw} - {exc}"
                raise ValueError(msg) from exc
        out = []
        for line in raw.splitlines():
            line = line.strip()
            # "# note" is a comment; "#submit" is an id selector. Requiring the
            # space is the difference between reading six selectors and silently
            # reading four.
            is_comment = line.startswith("#") and (len(line) == 1 or line[1] in " \t")
            if line and not is_comment:
                out.append(line)
        if not out:
            msg = "The selector list contained no selectors, only blank lines or comments."
            raise ValueError(msg)
        return out

    # ------------------------------------------------------------ matching

    @staticmethod
    def _select(soup: BeautifulSoup, css: str) -> list:
        try:
            return soup.select(css)
        except Exception:  # noqa: BLE001 - an unparseable selector is a result, not a crash
            return []

    @staticmethod
    def _xpath_to_css(xpath: str):
        """Translate the XPath a test suite actually contains into CSS.

        Returns (css, text_equals, text_contains) or None when the expression is
        outside the subset. The subset is: absolute and descendant steps, tag or
        *, [@attr='v'], [contains(@attr,'v')], [text()='v'],
        [contains(text(),'v')] and positional [n]. Anything with axes, functions
        or boolean logic is declined rather than half-translated, because a
        half-translated selector silently resolves to the wrong element.
        """
        expr = (xpath or "").strip()
        if expr.startswith("xpath="):
            expr = expr[len("xpath="):].strip()
        if not expr or not expr.startswith(("/", "(", "./")):
            return None
        if re.search(r"\b(?:following|preceding|ancestor|descendant|parent|sibling|self)\s*::", expr):
            return None
        if re.search(r"\b(?:last|position|count|not|starts-with|normalize-space|concat)\s*\(", expr):
            return None
        if " and " in expr or " or " in expr or "|" in expr:
            return None
        expr = expr.strip("()")

        text_equals = text_contains = ""
        parts, buffer, depth = [], "", 0
        for ch in expr:
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
            if ch == "/" and depth == 0:
                parts.append(buffer)
                buffer = ""
            else:
                buffer += ch
        parts.append(buffer)

        css_steps, descendant = [], False
        for raw in parts:
            if raw == "":
                descendant = True
                continue
            step = raw.strip()
            tag_match = re.match(r"^([A-Za-z][\w-]*|\*)", step)
            if not tag_match:
                return None
            tag = tag_match.group(1)
            rest = step[tag_match.end():]
            css = "" if tag == "*" else tag
            for predicate in re.findall(r"\[([^\]]*)\]", rest):
                predicate = predicate.strip()
                m = re.fullmatch(r"@([\w:-]+)\s*=\s*['\"]([^'\"]*)['\"]", predicate)
                if m:
                    attr, value = m.group(1), m.group(2)
                    if attr == "id":
                        css += f"#{value}"
                    elif attr == "class":
                        css += "".join(f".{c}" for c in value.split())
                    else:
                        css += f'[{attr}="{value}"]'
                    continue
                m = re.fullmatch(r"contains\s*\(\s*@([\w:-]+)\s*,\s*['\"]([^'\"]*)['\"]\s*\)", predicate)
                if m:
                    css += f'[{m.group(1)}*="{m.group(2)}"]'
                    continue
                m = re.fullmatch(r"text\s*\(\s*\)\s*=\s*['\"]([^'\"]*)['\"]", predicate)
                if m:
                    text_equals = m.group(1)
                    continue
                m = re.fullmatch(r"contains\s*\(\s*text\s*\(\s*\)\s*,\s*['\"]([^'\"]*)['\"]\s*\)", predicate)
                if m:
                    text_contains = m.group(1)
                    continue
                m = re.fullmatch(r"(\d+)", predicate)
                if m:
                    css += f":nth-of-type({m.group(1)})"
                    continue
                return None
            if not css:
                css = "*"
            css_steps.append((" " if descendant else " > ", css))
            descendant = False

        if not css_steps:
            return None
        selector = css_steps[0][1]
        for combinator, step in css_steps[1:]:
            selector += combinator + step
        return selector.strip(), text_equals, text_contains

    @classmethod
    def _resolve(cls, soup: BeautifulSoup, selector: str) -> tuple:
        """(elements, how) - how is 'css', 'xpath-translated' or 'untranslatable'."""
        if not _looks_like_xpath(selector):
            return cls._select(soup, selector), "css"
        translated = cls._xpath_to_css(selector)
        if translated is None:
            return [], "untranslatable"
        css, text_equals, text_contains = translated
        found = cls._select(soup, css)
        if text_equals:
            found = [e for e in found if _norm(e.get_text()) == text_equals]
        if text_contains:
            found = [e for e in found if text_contains in _norm(e.get_text())]
        return found, "xpath-translated"

    # --------------------------------------------------------- fingerprint

    @classmethod
    def _accessible_name(cls, el, soup) -> str:
        """A deliberately small subset of the accessible-name algorithm."""
        labelled_by = el.get("aria-labelledby")
        if labelled_by:
            parts = []
            for ref in str(labelled_by).split():
                target = soup.find(id=ref) if soup is not None else None
                if target is not None:
                    parts.append(_norm(target.get_text()))
            if any(parts):
                return _norm(" ".join(parts))
        for attr in ("aria-label", "alt", "title"):
            value = _norm(str(el.get(attr) or ""))
            if value:
                return value
        el_id = el.get("id")
        if el_id and soup is not None:
            label = soup.select_one(f'label[for="{el_id}"]')
            if label is not None:
                return _norm(label.get_text())
        if el.name in ("input", "textarea", "select"):
            parent = el.parent
            while parent is not None and getattr(parent, "name", None) not in (None, "[document]"):
                if parent.name == "label":
                    return _norm(parent.get_text())
                parent = parent.parent
            placeholder = _norm(str(el.get("placeholder") or ""))
            if placeholder:
                return placeholder
            return ""
        return _norm(el.get_text())

    @classmethod
    def _role(cls, el) -> str:
        explicit = _norm(str(el.get("role") or ""))
        if explicit:
            return explicit.split()[0]
        if el.name == "input":
            return _INPUT_ROLE.get(_norm(str(el.get("type") or "text")).lower(), "textbox")
        if el.name == "a":
            return "link" if el.get("href") is not None else ""
        return _IMPLICIT_ROLE.get(el.name, "")

    @classmethod
    def _testid(cls, el) -> tuple:
        for attr in _TESTID_ATTRS:
            value = _norm(str(el.get(attr) or ""))
            if value:
                return attr, value
        return "", ""

    @classmethod
    def _meaningful_classes(cls, el) -> list:
        classes = el.get("class") or []
        if isinstance(classes, str):
            classes = classes.split()
        return [c for c in classes if c and not _STYLING_CLASS.match(c)]

    @classmethod
    def _fingerprint(cls, el, soup) -> dict:
        testid_attr, testid = cls._testid(el)
        ancestors, section = [], ""
        parent = el.parent
        while parent is not None and getattr(parent, "name", None) not in (None, "[document]"):
            entry = {"tag": parent.name, "id": parent.get("id") or "",
                     "classes": cls._meaningful_classes(parent)}
            ancestors.append(entry)
            if not section:
                heading = parent.find(["h1", "h2", "h3", "h4", "h5", "h6"], recursive=True) \
                    if isinstance(parent, Tag) else None
                if heading is not None:
                    section = _norm(heading.get_text())
            parent = parent.parent

        siblings = []
        if el.parent is not None:
            for sib in el.parent.find_all(recursive=False):
                if sib is el:
                    continue
                text = _norm(sib.get_text())
                if text:
                    siblings.append(text[:80])

        attrs = {}
        for attr in _STABLE_ATTRS:
            value = _norm(str(el.get(attr) or ""))
            if value:
                attrs[attr] = value

        element_id = _norm(str(el.get("id") or ""))
        return {
            "tag": el.name,
            "id": element_id,
            "id_generated": bool(element_id and _GENERATED_ID.search(element_id)),
            "testid_attr": testid_attr,
            "testid": testid,
            "classes": cls._meaningful_classes(el),
            "text": _norm(el.get_text())[:200],
            "own_text": _norm("".join(el.find_all(string=True, recursive=False)))[:200],
            "accessible_name": cls._accessible_name(el, soup),
            "role": cls._role(el),
            "attrs": attrs,
            "ancestors": ancestors[:6],
            "ancestor_ids": [a["id"] for a in ancestors if a["id"]],
            "section": section,
            "siblings": siblings[:6],
            "depth": len(ancestors),
        }

    @staticmethod
    def _split_compounds(selector: str) -> list:
        """A selector's steps, outermost first, split on top-level combinators.

        Brackets and parentheses are tracked so a combinator inside
        [href="a > b"] or :not(a > b) does not split the selector.
        """
        s = (selector or "").strip()
        if s.startswith("xpath="):
            s = s[len("xpath="):].strip()
        if _looks_like_xpath(s):
            return [p.strip() for p in re.split(r"/+", s) if p.strip()]
        parts, buffer, square, round_ = [], "", 0, 0
        for ch in s:
            if ch == "[":
                square += 1
            elif ch == "]":
                square -= 1
            elif ch == "(":
                round_ += 1
            elif ch == ")":
                round_ -= 1
            if square == 0 and round_ == 0 and (ch.isspace() or ch in ">+~"):
                if buffer.strip():
                    parts.append(buffer.strip())
                buffer = ""
                continue
            buffer += ch
        if buffer.strip():
            parts.append(buffer.strip())
        return parts

    @classmethod
    def _fingerprint_from_selector(cls, selector: str) -> dict:
        """When there is no previous DOM, the selector string is all there is.

        This is deliberately thin. It reads the literals a selector carries -
        an id, a test id, a name, quoted text - and nothing else, because
        anything more would be inventing an element's identity out of its
        address.

        Only the SUBJECT of the selector is read for identity. In
        "#summary > div:nth-child(4) > span.value" the element being addressed
        is the span; reading the id off "#summary" would fingerprint the
        section and heal confidently onto the wrong element. Ancestor ids are
        kept, but as context rather than as the element's own identity.
        """
        compounds = cls._split_compounds(selector)
        subject = compounds[-1] if compounds else (selector or "")
        ancestors = compounds[:-1]

        fp = {
            "tag": "", "id": "", "id_generated": False, "testid_attr": "", "testid": "",
            "classes": [], "text": "", "own_text": "", "accessible_name": "", "role": "",
            "attrs": {}, "ancestors": [], "ancestor_ids": [], "section": "", "siblings": [],
            "depth": 0, "inferred_from_selector": True,
        }
        tag = re.match(r"^\s*([a-zA-Z][\w-]*)", subject)
        if tag and tag.group(1).lower() not in ("html", "body", "div", "span"):
            fp["tag"] = tag.group(1).lower()
        found_id = re.search(r"#([\w-]+)|@id\s*=\s*['\"]([^'\"]+)", subject)
        if found_id:
            fp["id"] = found_id.group(1) or found_id.group(2) or ""
        for attr in _TESTID_ATTRS:
            m = re.search(rf"{re.escape(attr)}\s*=\s*['\"]?([\w .:-]+)", subject)
            if m:
                fp["testid_attr"], fp["testid"] = attr, m.group(1).strip("'\"")
                break
        name = re.search(r"\[\s*name\s*=\s*['\"]([^'\"]+)|@name\s*=\s*['\"]([^'\"]+)", subject)
        if name:
            fp["attrs"]["name"] = name.group(1) or name.group(2) or ""
        text = re.search(r"text\(\)\s*=\s*['\"]([^'\"]+)|:has-text\(['\"]([^'\"]+)", subject)
        if text:
            fp["text"] = (text.group(1) or text.group(2) or "").strip()
        for cls_name in re.findall(r"\.([A-Za-z][\w-]*)", subject):
            if not _STYLING_CLASS.match(cls_name):
                fp["classes"].append(cls_name)

        for step in ancestors:
            ancestor_id = re.search(r"#([\w-]+)|@id\s*=\s*['\"]([^'\"]+)", step)
            if ancestor_id:
                fp["ancestor_ids"].append(ancestor_id.group(1) or ancestor_id.group(2) or "")
        return fp

    # ---------------------------------------------------------- candidates

    @classmethod
    def _candidates(cls, el, soup) -> list:
        """Every way of addressing this element, best rung of the ladder first.

        Each entry carries the CSS actually used to verify it and a
        framework-agnostic rendering for a Playwright suite. Absolute XPath,
        nth-child and styling classes never appear: healing onto one of those
        buys a green run now and the same break next sprint.
        """
        out = []
        testid_attr, testid = cls._testid(el)
        if testid:
            out.append({
                "rung": "test id", "rank": 1,
                "css": f'[{testid_attr}="{testid}"]',
                "playwright": f'page.getByTestId({testid!r})' if testid_attr == "data-testid"
                              else f'page.locator(\'[{testid_attr}="{testid}"]\')',
            })

        element_id = _norm(str(el.get("id") or ""))
        if element_id and not _GENERATED_ID.search(element_id):
            out.append({"rung": "id", "rank": 2, "css": f"#{element_id}",
                        "playwright": f"page.locator({'#' + element_id!r})"})

        role, name = cls._role(el), cls._accessible_name(el, soup)
        if role and name:
            out.append({"rung": "role and name", "rank": 3, "css": "", "role": role, "name": name,
                        "playwright": f"page.getByRole({role!r}, name={name!r})"})

        element_id = element_id or ""
        if el.name in ("input", "textarea", "select") and name:
            out.append({"rung": "label", "rank": 4, "css": "", "label": name,
                        "playwright": f"page.getByLabel({name!r})"})

        text = _norm(el.get_text())
        if text and len(text) <= 60 and el.name not in ("html", "body", "main", "section", "div"):
            out.append({"rung": "text", "rank": 5, "css": "", "text": text,
                        "playwright": f"page.getByText({text!r}, exact=True)"})

        for attr in ("name", "href", "placeholder", "alt", "autocomplete"):
            value = _norm(str(el.get(attr) or ""))
            if value:
                attr_css = '{}[{}="{}"]'.format(el.name, attr, value)
                out.append({"rung": f"{attr} attribute", "rank": 6, "css": attr_css,
                            "playwright": f"page.locator({attr_css!r})"})

        scoped = cls._scoped_css(el)
        if scoped:
            out.append({"rung": "scoped CSS", "rank": 7, "css": scoped,
                        "playwright": f"page.locator({scoped!r})"})
        return out

    @classmethod
    def _scoped_css(cls, el) -> str:
        """A short path anchored on the nearest authored id, never on position."""
        bits = []
        own = cls._meaningful_classes(el)
        if own:
            bits.append(f"{el.name}.{'.'.join(own[:2])}")
        else:
            attr_bits = [f'[{a}="{_norm(str(el.get(a)))}"]'
                         for a in ("type", "name") if _norm(str(el.get(a) or ""))]
            if not attr_bits:
                return ""
            bits.append(el.name + "".join(attr_bits))

        parent = el.parent
        while parent is not None and getattr(parent, "name", None) not in (None, "[document]"):
            pid = _norm(str(parent.get("id") or ""))
            if pid and not _GENERATED_ID.search(pid):
                return f"#{pid} {bits[0]}"
            parent = parent.parent
        return bits[0]

    # -------------------------------------------------------- verification

    @classmethod
    def _matches(cls, candidate: dict, soup: BeautifulSoup) -> list:
        """Run the candidate against the page. This is the whole safety story."""
        if candidate.get("css"):
            return cls._select(soup, candidate["css"])
        if candidate["rung"] == "role and name":
            return [e for e in soup.find_all(True)
                    if cls._role(e) == candidate["role"]
                    and cls._accessible_name(e, soup) == candidate["name"]]
        if candidate["rung"] == "label":
            return [e for e in soup.find_all(["input", "textarea", "select"])
                    if cls._accessible_name(e, soup) == candidate["label"]]
        if candidate["rung"] == "text":
            return [e for e in soup.find_all(True)
                    if _norm(e.get_text()) == candidate["text"]
                    and not any(_norm(c.get_text()) == candidate["text"]
                                for c in e.find_all(True, recursive=False))]
        return []

    # ------------------------------------------------------------- scoring
    # Only signals the old element actually HAD count towards the denominator.
    # Scoring an element out of a signal it never carried would mean an element
    # with no test id could never score well, which is most elements on most
    # pages.
    _WEIGHTS = {
        "testid": 34, "id": 26, "accessible_name": 22, "text": 16, "name_attr": 14,
        "siblings": 12, "role": 9, "ancestor_id": 8, "tag": 7, "classes": 7,
        "attrs": 6, "section": 6, "depth": 3,
    }

    @staticmethod
    def _text_similarity(a: str, b: str) -> float:
        a, b = (a or "").strip().lower(), (b or "").strip().lower()
        if not a or not b:
            return 0.0
        if a == b:
            return 1.0
        if a in b or b in a:
            return 0.6
        ta, tb = set(a.split()), set(b.split())
        if not ta or not tb:
            return 0.0
        overlap = len(ta & tb) / len(ta | tb)
        return overlap if overlap >= 0.34 else 0.0

    @staticmethod
    def _overlap(a: list, b: list) -> float:
        sa, sb = {str(x).strip().lower() for x in a if str(x).strip()}, \
                 {str(x).strip().lower() for x in b if str(x).strip()}
        if not sa or not sb:
            return 0.0
        return len(sa & sb) / len(sa | sb)

    @classmethod
    def _score(cls, target: dict, fp: dict) -> tuple:
        earned = possible = 0.0
        reasons = []

        def award(key, fraction, why):
            nonlocal earned, possible
            weight = cls._WEIGHTS[key]
            possible += weight
            if fraction > 0:
                earned += weight * fraction
                if fraction >= 0.5 and why:
                    reasons.append(why)

        if target.get("testid"):
            same = target["testid"] == fp.get("testid")
            award("testid", 1.0 if same else 0.0, f"same test id {target['testid']!r}" if same else "")
        if target.get("id") and not target.get("id_generated"):
            same = target["id"] == fp.get("id")
            award("id", 1.0 if same else 0.0, f"same id {target['id']!r}" if same else "")
        if target.get("accessible_name"):
            sim = cls._text_similarity(target["accessible_name"], fp.get("accessible_name", ""))
            award("accessible_name", sim, f"accessible name {fp.get('accessible_name')!r}" if sim else "")
        if target.get("text"):
            sim = cls._text_similarity(target["text"], fp.get("text", ""))
            award("text", sim, f"text {fp.get('text')!r}" if sim >= 1.0 else "")
        if target.get("attrs", {}).get("name"):
            same = target["attrs"]["name"] == fp.get("attrs", {}).get("name")
            award("name_attr", 1.0 if same else 0.0,
                  f"same name attribute {target['attrs']['name']!r}" if same else "")
        if target.get("siblings"):
            sim = cls._overlap(target["siblings"], fp.get("siblings", []))
            award("siblings", sim, "sits beside the same content" if sim >= 0.5 else "")
        if target.get("role"):
            same = target["role"] == fp.get("role")
            award("role", 1.0 if same else 0.0, f"still a {target['role']}" if same else "")
        if target.get("ancestor_ids"):
            sim = cls._overlap(target["ancestor_ids"], fp.get("ancestor_ids", []))
            award("ancestor_id", sim, "inside the same identified region" if sim >= 0.5 else "")
        if target.get("tag"):
            same = target["tag"] == fp.get("tag")
            award("tag", 1.0 if same else 0.0, "")
        if target.get("classes"):
            award("classes", cls._overlap(target["classes"], fp.get("classes", [])), "")
        other = {k: v for k, v in (target.get("attrs") or {}).items() if k != "name"}
        if other:
            matched = sum(1 for k, v in other.items() if fp.get("attrs", {}).get(k) == v)
            award("attrs", matched / len(other), "")
        if target.get("section"):
            sim = cls._text_similarity(target["section"], fp.get("section", ""))
            award("section", sim, f"under the {fp.get('section')!r} heading" if sim >= 1.0 else "")

        if not target.get("inferred_from_selector"):
            gap = abs(int(target.get("depth", 0)) - int(fp.get("depth", 0)))
            award("depth", max(0.0, 1.0 - gap / 6.0), "")

        if possible <= 0:
            return 0.0, []
        return round(100.0 * earned / possible, 1), reasons[:4]

    # ----------------------------------------------------------- analysing

    _SKIP_TAGS = {"html", "body", "head", "script", "style", "meta", "link", "title", "noscript"}

    @staticmethod
    def _is_hidden(el) -> bool:
        """Elements a test cannot interact with are not healing targets.

        The case this exists for is a component rendered twice - a desktop copy
        and a mobile one, or a form duplicated behind an open modal - where one
        copy is hidden. Both match equally well on every signal, and healing
        onto the hidden one produces a selector that resolves, passes
        verification, and then times out for ever. A hidden input is the same
        trap wearing a different hat: it holds the value while a custom widget
        holds the interaction, so filling it silently does nothing.
        """
        if el.name == "input" and _norm(str(el.get("type") or "")).lower() == "hidden":
            return True
        # hidden, aria-hidden and display:none all apply to the whole subtree, so
        # a visible-looking button inside a hidden wrapper is still unreachable.
        node = el
        while node is not None and getattr(node, "name", None) not in (None, "[document]"):
            if node.has_attr("hidden"):
                return True
            if _norm(str(node.get("aria-hidden") or "")).lower() == "true":
                return True
            style = _norm(str(node.get("style") or "")).replace(" ", "").lower()
            if "display:none" in style or "visibility:hidden" in style:
                return True
            node = node.parent
        return False

    def _heal_one(self, selector, before, after, elements, threshold, margin) -> dict:
        still, how = self._resolve(after, selector)
        result = {"selector": selector, "kind": "xpath" if _looks_like_xpath(selector) else "css",
                  "resolution": how, "matches_now": len(still)}

        if how == "untranslatable":
            result["note"] = (
                "This XPath uses axes or functions the translator does not cover, so the element's "
                "identity was read from the selector text alone. Supply a previous DOM, or a CSS "
                "selector, for a stronger match."
            )

        if len(still) == 1:
            return {**result, "outcome": "not_broken",
                    "why": "This selector still resolves to exactly one element. Nothing to heal."}

        target, source = None, ""
        if before is not None:
            found, _ = self._resolve(before, selector)
            if len(found) == 1:
                target, source = self._fingerprint(found[0], before), "previous DOM"
            elif len(found) > 1:
                source = f"selector matched {len(found)} elements in the previous DOM"
            else:
                source = "selector did not resolve in the previous DOM either"
        if target is None:
            target = self._fingerprint_from_selector(selector)
            source = source or "no previous DOM supplied"
            source = f"selector text ({source})"
        result["identity_source"] = source
        result["target"] = {k: target.get(k) for k in
                            ("tag", "id", "testid", "role", "accessible_name", "text", "section")}

        scored = []
        for el in elements:
            score, reasons = self._score(target, self._fingerprint(el, after))
            if score > 0:
                scored.append((score, reasons, el))
        scored.sort(key=lambda row: -row[0])

        best = scored[0][0] if scored else 0.0
        runner_up = scored[1][0] if len(scored) > 1 else 0.0
        result["best_score"] = best
        result["runner_up_score"] = runner_up

        if not scored or best < threshold:
            return {**result, "outcome": "gone",
                    "why": (f"Nothing in the current page resembles this element closely enough "
                            f"(best match scored {best:.0f} against a threshold of {threshold}). "
                            "It looks removed rather than restyled, so the test needs rewriting "
                            "rather than a new selector.")}

        if best - runner_up < margin and runner_up >= threshold:
            tied = [{"score": s, "why": r, "preview": _norm(e.get_text())[:60] or f"<{e.name}>",
                     "candidates": self._verified(e, after, selector)[:1]}
                    for s, r, e in scored[:3] if best - s < margin]
            return {**result, "outcome": "ambiguous", "reason": "tied", "competing": tied,
                    "why": (f"{len(tied)} elements match about equally well ({best:.0f} against "
                            f"{runner_up:.0f}). Choosing between them would be a guess, and a "
                            "selector pointed at the wrong element fails silently.")}

        score, reasons, winner = scored[0]
        verified = self._verified(winner, after, selector)
        if not verified:
            # Identification succeeded and addressing failed. Those are different
            # problems with different fixes, so they are not reported as the same
            # thing: nothing here is ambiguous, the element is simply not
            # addressable without someone adding a hook to the markup.
            return {**result, "outcome": "ambiguous", "reason": "unaddressable",
                    "score": score, "evidence": reasons,
                    "why": ("The element was identified confidently, but no selector for it "
                            "resolves to exactly one element - every candidate it has is shared "
                            "with a sibling. This is not an ambiguous match; it is an element "
                            "with nothing to address it by, and the fix is a test id in the "
                            "markup rather than a cleverer selector."),
                    "competing": [{"score": score, "why": reasons,
                                   "preview": _norm(winner.get_text())[:60]}]}
        return {**result, "outcome": "healed", "score": score, "evidence": reasons,
                "healed": verified[0], "alternatives": verified[1:3],
                "why": f"Matched at {score:.0f} out of 100."}

    def _verified(self, el, soup, original: str) -> list:
        """Candidates for this element that resolve to exactly one element."""
        out = []
        for candidate in sorted(self._candidates(el, soup), key=lambda c: c["rank"]):
            if candidate.get("css") and candidate["css"].strip() == (original or "").strip():
                continue
            matched = self._matches(candidate, soup)
            if len(matched) == 1 and matched[0] is el:
                out.append({k: v for k, v in candidate.items() if k != "rank"})
        return out

    def _analyse(self) -> dict:
        after_html = self._read(self.dom_after_path, self.dom_after, "current DOM", required=True)
        before_html = self._read(self.dom_before_path, self.dom_before, "previous DOM", required=False)

        after = BeautifulSoup(after_html, PARSER)
        before = BeautifulSoup(before_html, PARSER) if before_html.strip() else None
        if not after.find_all(True):
            msg = "The current DOM contains no elements. Check the snapshot is real HTML."
            raise ValueError(msg)

        threshold = min(max(int(self.heal_threshold or 45), 0), 100)
        margin = max(int(self.ambiguity_margin or 12), 0)
        elements = [e for e in after.find_all(True)
                    if e.name not in self._SKIP_TAGS and not self._is_hidden(e)]

        results = [self._heal_one(s, before, after, elements, threshold, margin)
                   for s in self._selector_list()]

        counts = {k: sum(1 for r in results if r["outcome"] == k)
                  for k in ("healed", "ambiguous", "gone", "not_broken")}
        return {
            "selectors_total": len(results),
            "counts": counts,
            "had_previous_dom": before is not None,
            "heal_threshold": threshold,
            "ambiguity_margin": margin,
            "elements_searched": len(elements),
            "results": results,
        }

    # -------------------------------------------------------------- brief

    def _brief_text(self, a: dict) -> str:
        c = a["counts"]
        lines = [
            "# Selector healing", "",
            f"Selectors checked: {a['selectors_total']}",
            f"Healed: {c['healed']}  Ambiguous: {c['ambiguous']}  "
            f"Gone: {c['gone']}  Still fine: {c['not_broken']}",
            f"Previous DOM supplied: {'yes' if a['had_previous_dom'] else 'no'}",
            f"Elements searched in the current page: {a['elements_searched']}",
            "",
            "Every proposal below was run against the current page and resolves to exactly "
            "one element. Scores are similarity to the original element, out of 100.",
            "",
        ]
        for r in a["results"]:
            lines.append(f"## {r['selector']}")
            lines.append(f"- outcome: {r['outcome']}")
            lines.append(f"- {r['why']}")
            if r.get("identity_source"):
                lines.append(f"- identity read from: {r['identity_source']}")
            if r["outcome"] == "healed":
                lines.append(f"- proposed: {r['healed']['playwright']}  "
                             f"(via {r['healed']['rung']}, score {r['score']:.0f})")
                if r.get("evidence"):
                    lines.append(f"- evidence: {'; '.join(r['evidence'])}")
                for alt in r.get("alternatives", []):
                    lines.append(f"- alternative: {alt['playwright']} (via {alt['rung']})")
            if r["outcome"] == "ambiguous":
                for tie in r.get("competing", []):
                    first = (tie.get("candidates") or [{}])[0].get("playwright", "")
                    lines.append(f"- competing at {tie['score']:.0f}: {tie.get('preview', '')!r}"
                                 + (f" -> {first}" if first else ""))
            lines.append("")
        return "\n".join(lines)

    # -------------------------------------------------------------- outputs

    FINDINGS_FILE = "healed_selectors.json"

    def _persist(self, analysis: dict) -> None:
        folder_raw = (self.output_dir or "").strip().strip('"').strip("'")
        if not folder_raw:
            return
        folder = Path(folder_raw).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
        (folder / self.FINDINGS_FILE).write_text(
            json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")

    def build_brief(self) -> Message:
        analysis = self._analyse()
        self._persist(analysis)
        self.status = self._status(analysis)
        return Message(text=self._brief_text(analysis))

    def build_findings(self) -> Data:
        analysis = self._analyse()
        self._persist(analysis)
        self.status = self._status(analysis)
        return Data(data=analysis)

    @staticmethod
    def _status(analysis: dict) -> str:
        c = analysis["counts"]
        return (f"{c['healed']} healed, {c['ambiguous']} ambiguous, "
                f"{c['gone']} gone, {c['not_broken']} fine")
