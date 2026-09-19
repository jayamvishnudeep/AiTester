"""Tests for the Selector Healer and the Healing Report Writer.

The thing that makes this agent safe is that it never proposes a selector it has
not run against the page, so most of these tests are about the two ways that
guarantee could be quietly lost: proposing something that resolves to nothing,
and proposing something that resolves to the wrong element.

The second is the one that matters. A selector resolving to nothing fails loudly
on the next run and someone fixes it. A selector resolving to the wrong element
passes, and the suite goes on reporting green about a thing it is no longer
testing.

Run it with the Langflow virtual environment:

    09_LangFlow/.venv/Scripts/python.exe test_self_healing_selectors.py
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from bs4 import BeautifulSoup  # noqa: E402
from healing_report_writer import HealingReportWriter  # noqa: E402
from selector_healer import _GENERATED_ID, _STYLING_CLASS, SelectorHealer  # noqa: E402

passed = failed = 0
HERE = Path(__file__).parent
DOM = HERE / "sample_dom"


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}" + (f"  -- {detail}" if detail else ""))


def raises(name, fn, fragment):
    try:
        fn()
    except ValueError as exc:
        check(name, fragment.lower() in str(exc).lower(), f"message was: {exc}")
    except Exception as exc:  # noqa: BLE001
        check(name, False, f"raised {type(exc).__name__}: {exc}")
    else:
        check(name, False, "no error raised")


def healer(**kw):
    params = {"broken_selectors": "", "default_selectors": "", "dom_after_path": "",
              "dom_after": "", "dom_before_path": "", "dom_before": "",
              "heal_threshold": 45, "ambiguity_margin": 12, "output_dir": ""}
    params.update(kw)
    return SelectorHealer(**params)


def heal(selectors, after, before="", **kw):
    return healer(broken_selectors=selectors, dom_after=after, dom_before=before,
                  **kw).build_findings().data


def one(selectors, after, before="", **kw):
    return heal(selectors, after, before, **kw)["results"][0]


def soup(html):
    return BeautifulSoup(html, "html.parser")


def writer(**kw):
    params = {"review": "Looks right.", "output_dir": "", "report_name": "healing_report.md"}
    params.update(kw)
    return HealingReportWriter(**params)


# ------------------------------------------------------- XPath translation

print("\nXPath translated into CSS")
T = SelectorHealer._xpath_to_css
CASES = [
    ("//button[@id='submit']", "button#submit"),
    ("//*[@id='submit']", "#submit"),
    ("//input[@name='email']", 'input[name="email"]'),
    ("//div[@class='a b']", "div.a.b"),
    ("/html/body/div/button", "html > body > div > button"),
    ("//div[@class='wrap']//span", "div.wrap span"),
    ("//button[contains(@class,'primary')]", 'button[class*="primary"]'),
    ("//ul/li[3]", "ul > li:nth-of-type(3)"),
    ("xpath=//button[@id='go']", "button#go"),
]
for xpath, expected in CASES:
    got = T(xpath)
    check(f"{xpath} -> {expected}", got is not None and got[0] == expected,
          str(got[0]) if got else "declined")

check("text() becomes a post-filter, not CSS",
      T("//button[text()='Save']") == ("button", "Save", ""))
check("contains(text()) becomes a post-filter",
      T("//button[contains(text(),'Sav')]") == ("button", "", "Sav"))

print("\nXPath outside the subset is declined rather than half-translated")
for expr in ["//button[position()=2]", "//div/following-sibling::span",
             "//a[@href='/x' and @class='y']", "//button[last()]",
             "//div[not(@hidden)]", "//a[@x='1'] | //b[@y='2']",
             "//input[starts-with(@id,'ship')]"]:
    check(f"declined: {expr}", T(expr) is None, str(T(expr)))

print("\nSelector subject, not its ancestors")
S = SelectorHealer._split_compounds
check("descendant chain splits", S("#summary > div:nth-child(4) > span.value")
      == ["#summary", "div:nth-child(4)", "span.value"])
check("a combinator inside brackets does not split",
      S('div[href="a > b"] span') == ['div[href="a > b"]', "span"])
check("a combinator inside parentheses does not split",
      S("div:not(a > b) span") == ["div:not(a > b)", "span"])
check("sibling combinators split", S("h2 + p ~ span") == ["h2", "p", "span"])
check("xpath splits on steps", S("//div[@id='a']/span") == ["div[@id='a']", "span"])

fp = SelectorHealer._fingerprint_from_selector("#summary > div:nth-child(4) > span.summary-row__value")
check("identity comes from the subject, not an ancestor id", fp["id"] == "",
      f"id was {fp['id']!r}")
check("the ancestor id is kept as context", fp["ancestor_ids"] == ["summary"])
check("the subject's meaningful class is kept", "summary-row__value" in fp["classes"])
fp2 = SelectorHealer._fingerprint_from_selector('button[data-testid="go"]')
check("a test id in the subject is read", fp2["testid"] == "go")
check("the subject tag is read", fp2["tag"] == "button")

# ----------------------------------------------------------- the list itself

print("\nReading the selector list")
check("an id selector is not mistaken for a comment",
      len(healer(broken_selectors="#submit\n.foo")._selector_list()) == 2)
check("a real comment is skipped",
      healer(broken_selectors="# a note\n#submit")._selector_list() == ["#submit"])
check("blank lines are skipped",
      healer(broken_selectors="\n\n#submit\n\n")._selector_list() == ["#submit"])
check("a bare hash is a comment", healer(broken_selectors="#\n#submit")._selector_list() == ["#submit"])
check("the default field is used when the input is empty",
      healer(default_selectors="#submit")._selector_list() == ["#submit"])
raises("no selectors at all is refused", lambda: healer()._selector_list(), "no broken selectors")
raises("a comment-only list is refused",
       lambda: healer(broken_selectors="# nothing here")._selector_list(), "no selectors")

# ------------------------------------------------------------- accessibility

print("\nAccessible name and role")
A = SelectorHealer._accessible_name
R = SelectorHealer._role
s = soup('<label for="e">Email</label><input id="e" type="text">'
         '<button aria-label="Close dialog">x</button>'
         '<img alt="Company logo" src="l.png">'
         '<a href="/x">Go home</a>'
         '<input id="p" type="text" placeholder="Search here">'
         '<span id="lbl">Named by ref</span><div aria-labelledby="lbl">content</div>')
check("label[for] names an input", A(s.select_one("#e"), s) == "Email")
check("aria-label wins for a button", A(s.select_one("button"), s) == "Close dialog")
check("alt names an image", A(s.select_one("img"), s) == "Company logo")
check("text names a link", A(s.select_one("a"), s) == "Go home")
check("placeholder is a last resort", A(s.select_one("#p"), s) == "Search here")
check("aria-labelledby is followed", A(s.select_one("[aria-labelledby]"), s) == "Named by ref")
check("button role", R(s.select_one("button")) == "button")
check("link role needs an href", R(s.select_one("a")) == "link")
check("text input role", R(s.select_one("#e")) == "textbox")
check("explicit role wins", R(soup('<div role="alert">x</div>').select_one("div")) == "alert")
check("checkbox role", R(soup('<input type="checkbox">').select_one("input")) == "checkbox")

# ------------------------------------------------------------- the ladder

print("\nWhat it is willing to emit")
page = soup('<div id="panel"><button data-testid="go" class="bg-sky-600 px-4">Pay now</button>'
            '<button class="px-4">Cancel</button></div>')
cands = SelectorHealer._candidates(page.select_one("[data-testid=go]"), page)
rungs = [c["rung"] for c in cands]
check("the test id is the first rung", rungs[0] == "test id")
check("role and name is offered", "role and name" in rungs)
check("no candidate is XPath", not any("//" in (c.get("css") or "") for c in cands))
check("no candidate uses nth-child", not any("nth-child" in (c.get("css") or "") for c in cands))
check("no candidate uses a styling class",
      not any("bg-sky" in (c.get("css") or "") or "px-4" in (c.get("css") or "") for c in cands),
      str([c.get("css") for c in cands]))
check("getByTestId is rendered for data-testid",
      any(c["playwright"] == "page.getByTestId('go')" for c in cands))

print("\nGenerated ids are not used to heal")
G = _GENERATED_ID
for bad in [":r3:", "mui-12", "radix-:r1:", "headlessui-menu-8", "a1b2c3d4-e5f6", "ember1234",
            "input-9481726", "3f8a9b2c1d4e5f60"]:
    check(f"generated: {bad}", bool(G.search(bad)), "not detected")
for good in ["ship-post", "card-number", "submit", "main-nav", "user_email"]:
    check(f"authored: {good}", not G.search(good), "wrongly called generated")

print("\nStyling classes are not used to heal")
for bad in ["px-4", "bg-sky-600", "text-sm", "mt-2", "rounded", "flex", "tabular-nums",
            "md:grid", "grow", "justify-between"]:
    check(f"styling: {bad}", bool(_STYLING_CLASS.match(bad)), "not detected")
for good in ["basket-item__remove", "checkout-submit", "js-apply-gift", "panel--payment"]:
    check(f"meaningful: {good}", not _STYLING_CLASS.match(good), "wrongly stripped")

# ------------------------------------------------------------- the outcomes

print("\nNothing to heal")
r = one("#keep", '<div><button id="keep">Go</button></div>')
check("a selector that still resolves is reported as not broken", r["outcome"] == "not_broken")
check("and nothing is proposed for it", "healed" not in r)

print("\nA plain heal")
before = '<div id="w"><button class="btn-old" id="pay">Place order</button></div>'
after = '<div id="w"><button class="rounded px-4" id="pay" data-testid="pay-now">Pay now</button></div>'
r = one(".btn-old", after, before)
check("a restyled element is healed", r["outcome"] == "healed", r["outcome"])
check("it heals onto the test id", r["healed"]["playwright"] == "page.getByTestId('pay-now')")
check("alternatives are offered", len(r.get("alternatives", [])) >= 1)
check("the evidence is recorded", bool(r.get("evidence")))

print("\nThe element is gone")
r = one(".js-gift", '<div id="w"><button id="pay">Pay</button></div>',
        '<div id="w"><a class="js-gift" href="/g">Apply a gift card</a><button id="pay">Pay</button></div>')
check("a removed element is reported gone", r["outcome"] == "gone", r["outcome"])
check("the refusal explains itself", "removed rather than restyled" in r["why"])
check("nothing is proposed", "healed" not in r)

print("\nThe wrong-element trap")
rows_before = ('<ul>' + ''.join(
    f'<li class="row"><span>{name}</span><button class="rm">Remove</button></li>'
    for name in ("Keyboard", "Cable", "Stand")) + '</ul>')
rows_after = ('<ul>' + ''.join(
    f'<li class="flex"><span>{name}</span>'
    f'<button class="text-sm" aria-label="Remove {name}">Remove</button></li>'
    for name in ("Keyboard", "Cable", "Stand")) + '</ul>')
r = one(".row:nth-child(2) .rm", rows_after, rows_before)
check("the second row's button heals to the second row", r["outcome"] == "healed", r["outcome"])
check("and to the RIGHT row, not the first",
      "Cable" in r["healed"]["playwright"], r["healed"]["playwright"])

print("\nAmbiguity is reported rather than guessed")
same_before = '<ul><li><button class="rm">Remove</button></li><li><button class="rm">Remove</button></li></ul>'
same_after = '<ul><li><button class="x">Remove</button></li><li><button class="x">Remove</button></li></ul>'
r = one("li:nth-child(2) .rm", same_after, same_before)
check("indistinguishable candidates are not chosen between",
      r["outcome"] == "ambiguous", f"{r['outcome']} / {r.get('healed')}")
check("the competing candidates are listed", len(r.get("competing", [])) >= 2)
check("the refusal explains the risk", "silently" in r["why"] or "guess" in r["why"])

print("\nA candidate that is not unique is never emitted")
# The target is identifiable by its neighbours, but every selector FOR it is
# shared with two other buttons: no test id, no id, same role, same name, same
# text. Verification must reject all of them and the run must end in a refusal
# rather than proposing a locator that resolves to three elements.
shared_before = ('<ul>' + ''.join(
    f'<li><span>{n}</span><button class="rm">Remove</button></li>'
    for n in ("Keyboard", "Cable", "Stand")) + '</ul>')
shared_after = ('<ul>' + ''.join(
    f'<li><span>{n}</span><button class="x">Remove</button></li>'
    for n in ("Keyboard", "Cable", "Stand")) + '</ul>')
r = one("li:nth-child(2) .rm", shared_after, shared_before)
check("with no unique selector available, nothing is proposed",
      r["outcome"] != "healed", f"proposed {r.get('healed', {}).get('playwright')}")
check("and the reason names the fix", "test id" in r["why"] or "guess" in r["why"], r["why"])
shared_soup = soup(shared_after)
target_button = shared_soup.select("button")[1]
offered = SelectorHealer._candidates(target_button, shared_soup)
survived = healer()._verified(target_button, shared_soup, "")
check("the ladder does generate candidates for it", len(offered) > 0)
check("but verification rejects every one of them", survived == [],
      str([c["playwright"] for c in survived]))
check("each rejected candidate really did match more than one element",
      all(len(SelectorHealer._matches(c, shared_soup)) != 1 for c in offered),
      str([(c["rung"], len(SelectorHealer._matches(c, shared_soup))) for c in offered]))

print("\nHidden copies are not healing targets")
# The same control rendered twice, one copy hidden for the other breakpoint.
# Both match every signal equally; healing onto the hidden one gives a selector
# that resolves, passes verification, and then times out for ever.
dup_before = '<div><button class="save">Save</button></div>'
dup_after = ('<div>'
             '<div class="mobile" aria-hidden="true"><button id="save-m" class="x">Save</button></div>'
             '<div class="desktop"><button id="save-d" class="x">Save</button></div>'
             '</div>')
r = one(".save", dup_after, dup_before)
check("a hidden duplicate does not win", r.get("healed", {}).get("playwright", "") != "page.locator('#save-m')",
      str(r.get("healed")))
check("the visible copy is chosen", r["outcome"] == "healed"
      and "save-d" in r["healed"]["playwright"], f"{r['outcome']} {r.get('healed')}")

H = SelectorHealer._is_hidden
check("aria-hidden is hidden", H(soup('<div aria-hidden="true">x</div>').select_one("div")))
check("the hidden attribute is hidden", H(soup("<div hidden>x</div>").select_one("div")))
check("display:none is hidden", H(soup('<div style="display: none">x</div>').select_one("div")))
check("visibility:hidden is hidden", H(soup('<div style="visibility:hidden">x</div>').select_one("div")))
check("a hidden input is hidden", H(soup('<input type="hidden" name="country">').select_one("input")))
check("a normal element is not hidden", not H(soup("<div>x</div>").select_one("div")))
check("aria-hidden=false is not hidden", not H(soup('<div aria-hidden="false">x</div>').select_one("div")))

hidden_field = ('<form><input type="hidden" name="country" value="GB">'
                '<div role="combobox" aria-label="Country">United Kingdom</div></form>')
r = one('input[name="country"]', hidden_field,
        '<form><input type="text" name="country" value="GB"></form>')
check("a hidden input shadowing a widget is not healed onto",
      r.get("healed", {}).get("playwright", "").find("input") == -1, str(r.get("healed")))

print("\nFound but unaddressable is not the same as ambiguous")
r = one("li:nth-child(2) .rm", shared_after, shared_before)
check("it is reported with its own reason", r.get("reason") == "unaddressable", str(r.get("reason")))
check("the explanation says the fix is a test id, not a cleverer selector",
      "test id in the markup" in r["why"], r["why"])
tie = one("li:nth-child(2) .rm", same_after, same_before)
check("a genuine tie is reported as a tie", tie.get("reason") == "tied", str(tie.get("reason")))

print("\nEvery proposal resolves to exactly one element")
allr = heal(str(DOM / "broken_selectors.txt"),
            (DOM / "checkout_after.html").read_text(encoding="utf-8"),
            (DOM / "checkout_before.html").read_text(encoding="utf-8"))
after_soup = soup((DOM / "checkout_after.html").read_text(encoding="utf-8"))
for res in allr["results"]:
    if res["outcome"] != "healed":
        continue
    cand = res["healed"]
    matched = SelectorHealer._matches(cand, after_soup)
    check(f"unique: {cand['playwright'][:52]}", len(matched) == 1, f"matched {len(matched)}")

print("\nA generated id is never offered as a selector")
gen = soup('<div><button id="mui-1234" class="x">Save</button>'
           '<button id=":r7:" class="y">Load</button></div>')
for element, bad_id in ((gen.select_one("#mui-1234"), "mui-1234"), (gen.select_one("[id=':r7:']"), ":r7:")):
    offered = SelectorHealer._candidates(element, gen)
    check(f"no #{bad_id} candidate",
          not any(c.get("css") == f"#{bad_id}" for c in offered),
          str([c.get("css") for c in offered]))
    check(f"no scoped selector anchored on #{bad_id}",
          not any(f"#{bad_id}" in (c.get("css") or "") for c in offered),
          str([c.get("css") for c in offered]))

# --------------------------------------------------------------- scoring

print("\nScoring counts only the signals the old element had")
target = {"tag": "button", "id": "", "testid": "", "classes": [], "text": "Go",
          "accessible_name": "Go", "role": "button", "attrs": {}, "ancestors": [],
          "ancestor_ids": [], "section": "", "siblings": [], "depth": 1}
same, _ = SelectorHealer._score(target, dict(target))
check("an identical element scores 100", same == 100.0, str(same))
different, _ = SelectorHealer._score(target, {**target, "tag": "a", "text": "Totally other",
                                              "accessible_name": "Totally other", "role": "link"})
check("an unrelated element scores low", different < 30, str(different))
check("an element with no test id can still score full marks", same == 100.0)

# ---------------------------------------------------------------- guards

print("\nGuards")
raises("no current DOM is refused", lambda: heal("#a", ""), "no current dom")
raises("a DOM with no elements is refused", lambda: heal("#a", "   "), "no current dom")
raises("text that is not markup is refused", lambda: heal("#a", "just some words"),
       "no elements")

print("\nThe previous DOM is optional but reported")
with_before = heal("#pay", after, before)
without = heal("#pay", after)
check("with a previous DOM it says so", with_before["had_previous_dom"] is True)
check("without one it says so", without["had_previous_dom"] is False)
r = one(".btn-old", after)
check("with no previous DOM, a styling-only selector is refused rather than guessed",
      r["outcome"] in ("gone", "ambiguous"), r["outcome"])
check("and the identity source is recorded", "selector text" in r.get("identity_source", ""))

print("\nReading from disk")
tmp = Path(tempfile.mkdtemp())
(tmp / "sel.txt").write_text("#pay\n", encoding="utf-8")
(tmp / "after.html").write_text(after, encoding="utf-8")
check("selectors are read from a file",
      healer(broken_selectors=str(tmp / "sel.txt"),
             dom_after_path=str(tmp / "after.html")).build_findings().data["selectors_total"] == 1)
check("a quoted path works",
      healer(broken_selectors=f'"{tmp / "sel.txt"}"',
             dom_after_path=f'"{tmp / "after.html"}"').build_findings().data["selectors_total"] == 1)

print("\nPersistence")
out = Path(tempfile.mkdtemp())
healer(broken_selectors="#pay", dom_after=after, output_dir=str(out)).build_brief()
check("the brief writes healed_selectors.json", (out / "healed_selectors.json").is_file())
check("the findings file has results",
      "results" in json.loads((out / "healed_selectors.json").read_text(encoding="utf-8")))

# --------------------------------------------------------- report writer

print("\nReport writer guards")
raises("no reports folder is refused", lambda: writer().write_report(), "set a reports folder")
raises("a missing findings file is named",
       lambda: writer(output_dir=tempfile.mkdtemp()).write_report(), "healed_selectors.json")
bad = Path(tempfile.mkdtemp())
(bad / "healed_selectors.json").write_text("{nope", encoding="utf-8")
raises("a corrupt findings file is refused",
       lambda: writer(output_dir=str(bad)).write_report(), "not valid json")
wrong = Path(tempfile.mkdtemp())
(wrong / "healed_selectors.json").write_text('{"counts": {}}', encoding="utf-8")
raises("a findings file with no results is refused",
       lambda: writer(output_dir=str(wrong)).write_report(), "no results")
good = Path(tempfile.mkdtemp())
(good / "healed_selectors.json").write_text(json.dumps(allr), encoding="utf-8")
raises("an empty review is refused",
       lambda: writer(output_dir=str(good), review="  ").write_report(), "no review")

print("\nReport writer output")
summary = writer(output_dir=str(good), review="```markdown\nAll four look right.\n```").write_report()
report = (good / "healing_report.md").read_text(encoding="utf-8")
check("a fenced review is unwrapped", "All four look right." in report and "```markdown" not in report)
check("the review is labelled as model-written", "written by a language model" in report)
check("the report opens with the at-a-glance table", "## At a glance" in report)
check("healed selectors get a table", "## Healed (4)" in report)
check("gone elements get their own section", "## Element gone (1)" in report)
check("selectors that were fine are listed", "Were never broken (1)" in report)
check("a paste-ready replacement block is included", "## Replacements" in report)
check("the summary carries the counts", "4 healed" in summary.text)
check("the summary states the uniqueness guarantee",
      "resolves to exactly one element" in summary.text)

no_before = dict(allr)
no_before["had_previous_dom"] = False
nb = Path(tempfile.mkdtemp())
(nb / "healed_selectors.json").write_text(json.dumps(no_before), encoding="utf-8")
writer(output_dir=str(nb), review="Ok.").write_report()
check("a run with no previous DOM says the evidence was thin",
      "No previous DOM was supplied" in (nb / "healing_report.md").read_text(encoding="utf-8"))
writer(output_dir=str(good), review="Ok.", report_name="round-2").write_report()
check("a report name without an extension gets .md", (good / "round-2.md").is_file())
check("the details output reports where it wrote",
      writer(output_dir=str(good), review="Ok.").write_details().data["report"].endswith("healing_report.md"))

# ----------------------------------------------------------- the fixtures

print("\nThe sample DOM in this folder")
check("all six selectors are read", allr["selectors_total"] == 6, str(allr["selectors_total"]))
check("four heal, one is gone, one was fine",
      allr["counts"] == {"healed": 4, "ambiguous": 0, "gone": 1, "not_broken": 1},
      str(allr["counts"]))
healed_by_selector = {r["selector"]: r for r in allr["results"] if r["outcome"] == "healed"}
check("the submit button heals to its new test id",
      healed_by_selector[".btn-primary.checkout-submit"]["healed"]["playwright"]
      == "page.getByTestId('place-order')")
check("the positional total heals to the new test id",
      healed_by_selector["#summary > div:nth-child(4) > span.summary-row__value"]["healed"]["playwright"]
      == "page.getByTestId('order-total')")
check("the second basket row heals to the second basket row",
      "USB-C cable" in healed_by_selector[".basket-item:nth-child(2) .basket-item__remove"]["healed"]["playwright"])
check("the payment field heals to its id",
      healed_by_selector[".panel--payment .input--text"]["healed"]["playwright"]
      == "page.locator('#card-number')")

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
