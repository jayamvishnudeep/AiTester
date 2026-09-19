# Plan — Auto-Update Selectors, Self-Healing (Langflow AI Agent)

| | |
|---|---|
| **Role** | Automation |
| **Problem** | UI tests break on minor layout changes |
| **Input** | A failed selector and the page DOM |
| **Output** | A healed XPath or CSS selector |
| **Shape** | Text Input → Prompt Template → LLM → Structured Output |

## The failure that defines this agent

There are two ways to get a selector wrong and they are not equally bad.

A selector that resolves to **nothing** fails on the next run, loudly, with a
message naming the selector. Someone fixes it. Annoying, visible, cheap.

A selector that resolves to the **wrong element** passes. The suite stays green
while testing something it was never meant to test — clicking the wrong button,
asserting on the wrong total. Nobody finds out until the thing it was supposed
to be covering ships broken.

So the agent is built so that the first can never happen and the second is
refused rather than risked:

- **Nothing is proposed that has not been run against the page.** Candidates are
  generated from the new DOM, evaluated with a real selector engine, and thrown
  away unless they resolve to exactly one element. This is a property of the
  pipeline, not something the model promises.
- **When several elements match equally well, it says so.** Choosing between
  them would be a coin flip that looks like an answer.
- **When nothing matches, it refuses.** A test pointing at a deleted feature
  needs rewriting, not re-pointing.

## Where this departs from the brief

The given shape is Text Input → Prompt → LLM → Structured Output: hand the model
the DOM and the broken selector, take back a new selector. That produces
something that looks right every time and is unverifiable every time, which for
this particular job is the worst available property.

So the split is: **code does everything that can be checked, the model does the
one thing that cannot.** Code parses the DOM, reads the old element's identity,
builds candidates, evaluates them and scores them. The model is asked whether
the element that was found is the element the test *meant* — a question about
intent, which no amount of parsing answers.

## Verification without a browser

The agent has no browser, so "does this selector resolve uniquely" has to be
answerable another way. BeautifulSoup ships with **soupsieve**, a genuine CSS
level-4 selector engine, so CSS is evaluated properly rather than approximated.

XPath was the harder half, because Selenium suites are full of it. The obvious
move is to add lxml, which does XPath natively — and it is the wrong move:
elements found by lxml cannot be recognised in the BeautifulSoup tree, so the
element you located is not an element you can then fingerprint. Two parsers
means two incompatible notions of "this element".

Instead XPath is **translated into CSS over a documented subset** —
`//tag[@attr='v']`, `contains()`, `text()`, positional `[n]`, absolute and
descendant steps — and evaluated by the same engine. Anything with axes,
`position()`, `last()` or boolean logic is **declined rather than
half-translated**, because a half-translated selector does not fail, it silently
resolves to something else.

## The rung ladder, and a cross-agent constraint

Healed selectors climb a ladder: test id, authored id, role plus accessible
name, label, text, stable attribute, scoped CSS. Absolute XPath, `nth-child` and
styling-class selectors are never emitted.

That is not just taste. **Agent 09 in this same repository flags exactly those
as anti-patterns.** A healer that emitted `//div[3]/span[2]` would be
manufacturing debt that a sibling agent then reports. Healing should leave the
suite better than it found it, and the selector that survived this layout change
should also survive the next one.

The same reasoning rejects framework-generated ids — `:r3:`, `mui-1234`,
`headlessui-menu-8`. They look like stable identity and regenerate on the next
render.

## Scoring, and the normalisation that matters

Similarity is a weighted sum over signals: test id, id, accessible name, text,
name attribute, sibling context, role, ancestor ids, tag, classes, attributes,
section heading, depth.

The important detail is the denominator. **Only signals the old element actually
had count towards the total.** Score an element out of thirteen signals when it
only ever carried four, and every element on a page without test ids scores
badly — which is most elements on most pages.

Sibling context earns its weight in the case this agent exists for. Three
identical "Remove" buttons in a basket are indistinguishable by tag, role, text
and class; what separates them is the product name sitting next to each one.
That is how the second row's button heals to the second row.

## Two bugs worth recording

**The comment character is also a CSS selector.** The selector list skips lines
starting with `#`. Half the selectors in the sample are ids — `#ship-post` —
and they were being silently dropped. Six selectors went in, four came out, no
error. Comments now require `# ` with a space.

**Identity was being read from the wrong part of the selector.** For
`#summary > div:nth-child(4) > span.summary-row__value` the element being
addressed is the span, but the fingerprint was reading the id out of anywhere in
the string and finding `summary`. With no previous DOM it then healed
confidently onto the `#summary` section — a textbook wrong-element heal
committed by the very code meant to prevent them. Identity now comes from the
selector's *subject*, the last compound, with ancestor ids kept as context
rather than identity.

## Two more traps, found by attacking the design

**The hidden twin.** A component rendered twice — a desktop copy and a mobile
one, or a form duplicated behind an open modal — gives two elements that match
every signal identically. Heal onto the hidden one and the selector resolves,
passes verification, and then times out for ever. Hidden elements are therefore
out of the candidate pool, and hiddenness is inherited: `aria-hidden`, `hidden`
and `display:none` apply to a whole subtree, so a visible-looking button inside
a hidden wrapper is still unreachable. A hidden `<input>` is the same trap in
another hat — it holds the value while a custom widget holds the interaction, so
filling it silently does nothing.

**"Found but unaddressable" is not "ambiguous".** When identification succeeds
and every candidate is shared with a sibling, the earlier code reported it as
ambiguity, which is a different problem with a different fix. Nothing is
ambiguous there — the element is known, it just has nothing to address it by,
and the answer is a test id in the markup rather than a cleverer selector. The
two now carry distinct reasons.

## Known blind spots

An adversarial pass over the design surfaced cases this build does **not**
handle. They are recorded rather than quietly left out, because the agent's
whole claim is about not being confidently wrong:

- **A recycled or moved test id.** If a `data-testid` is deleted from one
  element and reused on another, the top rung of the ladder lies. Verification
  passes — it resolves to exactly one element — and the heal is silently wrong.
  The most-trusted signal is the one with no cross-check.
- **Reused text after a rewording.** If the target's label changes and a
  different element inherits the old text verbatim, the text rung resolves
  uniquely to the wrong element, and uniqueness supplies false confidence.
- **Boundaries.** An element moved into an iframe, a shadow root, or a portal
  rendered at `<body>` level cannot be expressed as one selector string. The
  honest outcome is a qualified refusal; today it is scored like any other move.
- **A snapshot captured in the wrong state.** A loading skeleton or an empty-list
  page contains placeholder furniture that structurally mimics the target. The
  right answer is "recapture after load", not a heal.
- **Selectors backing a negative assertion.** For `expect(x).not.toBeVisible()`
  a disappeared element is the expected state, and healing it inverts the test.
- **A changed interaction model.** `<button>` becoming `<a role="button">`, or a
  native `<select>` becoming a listbox, needs the test rewritten rather than
  re-pointed; a new selector alone is not the fix.

## Pipeline

```
Text Input (selector list)
  → Selector Healer      parse both DOMs, fingerprint the old element, build
                         candidates, verify each resolves uniquely, score,
                         decide heal / ambiguous / gone / not_broken,
                         write healed_selectors.json
  → Prompt Template      the brief: outcomes, proposals, scores, evidence
  → Groq                 judges intent; forbidden to write selectors of its own
  → Healing Report Writer  evidence first, judgement under it, plus a
                         paste-ready replacement list
  → Chat Output
```

## Verified

- **156 component tests**, no Langflow or network needed: the XPath subset and
  what it declines, subject extraction, accessible name and role, the ladder's
  refusals, all four outcomes, and both writers' guards.
- **Mutation-checked, and it found two real gaps.** Nine defects were
  introduced one at a time; on the first pass two survived — dropping the
  uniqueness check, and allowing generated ids back in. Both were holes in the
  tests, not the code, and the most important property of the agent was one of
  them. Tests were added for each and all nine are now caught.
- **The demo runs end to end** through the real flow, and the numbers in the
  README are the ones it produced.
- **Canvas edge count re-checked after opening in the UI** — five of five.
