# Plan — Meeting Transcript to Requirements (Langflow AI Agent)

| | |
|---|---|
| **Role** | QA Lead |
| **Problem** | Verbal requirements lost after calls |
| **Input** | A Zoom or Teams transcript |
| **Output** | Jira requirements and sub-tasks |
| **Shape** | File Input → Text Splitter → Prompt Template → LLM → JSON Output |

## The failure this agent has to avoid

Ask a model what was agreed in a meeting and it returns a tidy list of
requirements. Some of them were never said.

They are not obviously wrong — that is the whole problem. They are the sensible
things a team *would* agree given that discussion, phrased exactly like the real
ones, sitting in the same list. The QA lead reading it cannot tell which is
which. Neither can the developer who picks up the ticket. And unlike a wrong
number, there is nothing to re-derive it from: the meeting is over, and the only
record of what was said is the transcript nobody is going to re-read.

So this agent's central mechanism is not extraction. **It is proof.**

## Every requirement must quote its source

The model is required to return, with each item, a **quote copied verbatim from
one transcript line**. Before anything is written, code checks that quote
against the parsed transcript. If it is not there, the item is thrown away.

An invented requirement has nothing to quote. It can only be accompanied by an
invented quote, and an invented quote does not appear in the transcript, so the
check catches it. This is the same shape as agent 12's rule that no selector is
proposed without being run against the page first: **the model may propose, but
only code may confirm.**

Three details make it actually work rather than nearly work:

- **A quote must be at least four words.** Three words of ordinary English
  appear in almost any transcript, so a short quote would let an invented
  requirement borrow a real turn's attribution and pass.
- **Matching normalises punctuation and casing, not words.** "Default off in
  production." and "default off in production" are the same quote; "default off
  in staging" is not.
- **Attribution is read from the matched turn, never from the model.** The model
  says *what* was agreed; the transcript says *who* said it and *when*. When the
  model volunteers a speaker, it is ignored.

Rejected items are printed in the report. A silent drop would be a quieter
version of the original problem — if nobody sees what the filter removed, nobody
notices when it stops removing anything.

## Where this departs from the brief

The given shape is File Input → Text Splitter → Prompt Template → LLM → JSON
Output, and the departure is the same one agent 11 made for CI logs, for the
same reason: **the input is mostly not the thing you want.**

A transcript is greetings, "you're on mute", scheduling chatter and one-word
acknowledgements, with the few committing turns scattered among them. In the
sample here, **30% of turns are filler**. Chunking the whole thing and
summarising each chunk spends the budget on "Can you hear me now?" and dilutes
the four turns that matter.

So the parser drops what could not possibly be a commitment, keeps everything
else with its speaker and timestamp attached, and sends that. The splitter's job
— bounding what reaches the model — is done inside the parser instead, with one
difference that matters: **when the transcript does not fit, the turns that were
cut are named in the output and the report carries a warning.** A subset of a
meeting presented as the whole meeting is exactly the failure this agent exists
to prevent, so it is not allowed to happen quietly.

The filler rule is deliberately narrow. It matches whole utterances, never
substrings: `"okay"` is filler, `"okay, tax goes on its own line"` is not. The
parser decides what *cannot* be a requirement; it never decides what is one.

## Agreed is not the same as discussed

The second judgement the prompt insists on, and the one a naive extractor gets
wrong every time: somebody raising an idea is not the team committing to it.

In the sample, Raj asks whether they should look at payment retry. Priya says
she would like to but there is no capacity, and then "let's park it". A careless
extraction produces a requirement to build payment retry. The correct reading is
a **decision not to**, and that is what the agent records — with the quote
attached, so a reader can disagree with the call in one glance.

The same distinction gives the empty answer its legitimacy. `coffee_catchup.txt`
is eleven turns of small talk and produces zero items, and the report says
"Nothing was agreed" rather than finding something to justify the run.

## Pipeline

```
Text Input (transcript path)
  → Transcript Parser      detects WEBVTT / Teams / inline, splits into
                           attributed turns, drops filler, reports anything
                           that did not fit, writes transcript_turns.json
  → Prompt Template        the turns, tagged with ids, speakers and timestamps
  → Groq                   extracts items, each with a verbatim quote
  → Requirements Writer    checks every quote against the transcript, drops
                           what nobody said, writes the report and the Jira
                           payloads
  → Chat Output
```

Nothing is sent to Jira. `requirements.json` is a set of payloads to review and
post, which keeps a wrong extraction a document rather than a ticket.

## Verified

- **108 component tests**, no Langflow or network needed: all three transcript
  formats, continuation lines, filler versus meaning, the budget warning, and
  every verification rule.
- **Mutation-checked, eleven defects.** Removing the quote check, allowing
  items with no quote, dropping the minimum quote length, taking attribution
  from the model, no longer reporting rejections, analysing an all-filler
  transcript — each was introduced alone and the suite went red for every one.
  One first attempt was **inert** (a no-op line) and had to be rewritten as a
  real defect before it proved anything, which is the same trap agent 13 hit.
- **All three transcripts run end to end** through the real flow: 8 verified
  items from the checkout sync, 4 from the regression triage, **0 from the
  coffee catch-up**.
- **The verification was tested adversarially**, with three invented
  requirements written in the same register as the real ones. All three were
  rejected.
- **Canvas edge count re-checked after opening in the UI** — five of five.
