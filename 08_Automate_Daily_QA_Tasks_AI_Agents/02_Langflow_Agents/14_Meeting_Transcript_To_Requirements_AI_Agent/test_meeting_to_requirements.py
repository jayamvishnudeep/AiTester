"""Tests for the Transcript Parser and the Requirements Writer.

The failure this agent exists to prevent is a requirement nobody said. It does
not look like a bug: it looks like a tidy Jira ticket, phrased exactly like the
real ones, describing the sensible thing a team *would* have agreed. Nobody
reading the list can tell it apart, and the developer who picks it up certainly
cannot.

So most of what follows is about the verification step - that a quote which is
not in the transcript cannot get through, that a quote too short to mean
anything cannot get through either, and that attribution is taken from the
transcript rather than from whatever the model claimed.

Run it with the Langflow virtual environment:

    09_LangFlow/.venv/Scripts/python.exe test_meeting_to_requirements.py
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from requirements_writer import RequirementsWriter  # noqa: E402
from transcript_parser import TranscriptParser  # noqa: E402

passed = failed = 0
HERE = Path(__file__).parent
SAMPLES = HERE / "sample_transcripts"


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


def parser(**kw):
    params = {"transcript_path": "", "default_transcript_path": "", "pasted_transcript": "",
              "meeting_title": "", "min_words": 4, "max_brief_chars": 12000,
              "drop_filler": True, "output_dir": ""}
    params.update(kw)
    return TranscriptParser(**params)


def parse(text, **kw):
    return parser(pasted_transcript=text, **kw).build_turns().data


def writer(**kw):
    params = {"extracted": "[]", "output_dir": "", "min_quote_words": 4,
              "report_name": "requirements_report.md", "project_key": "QA"}
    params.update(kw)
    return RequirementsWriter(**params)


INLINE = """Priya Sharma: The flag has to default to off in production until legal sign off.
Raj Patel: Okay.
Mei Lin: I will raise a ticket to flip it before Friday.
"""

VTT = """WEBVTT

1
00:00:07.000 --> 00:00:11.000
Priya Sharma: The order total needs tax as a separate line item.

2
00:00:12.000 --> 00:00:14.000
Raj Patel: Yeah.

3
00:00:15.000 --> 00:00:19.000
Mei Lin: Is that a hard number or just a target for this sprint?
"""

TEAMS = """Regression Triage

Ada Lovelace   0:04
Any test failing twice in a week should be quarantined automatically.

Sam Okafor   0:12
Okay.

Sam Okafor   0:15
I will set that up this afternoon and document the rule.
"""


def prepared(transcript=INLINE, **kw):
    """A folder holding a parsed transcript, ready for the writer."""
    folder = Path(tempfile.mkdtemp())
    parser(pasted_transcript=transcript, output_dir=str(folder), **kw).build_brief()
    return folder


# ----------------------------------------------------------------- parsing

print("\nThe three transcript formats")
check("inline 'Name: text' is read", parse(INLINE)["format"] == "inline")
check("WEBVTT is read", parse(VTT)["format"] == "webvtt")
check("the Teams export is read", parse(TEAMS)["format"] == "teams")
check("inline turns are counted", parse(INLINE)["turns_total"] == 3)
check("vtt turns are counted", parse(VTT)["turns_total"] == 3)
check("teams turns are counted", parse(TEAMS)["turns_total"] == 3)

print("\nSpeakers and timestamps survive parsing")
check("inline speakers are attributed",
      parse(INLINE)["speakers"] == ["Mei Lin", "Priya Sharma", "Raj Patel"])
check("vtt timestamps are kept",
      parse(VTT)["all_turns"][0]["time"] == "00:00:07.000",
      parse(VTT)["all_turns"][0]["time"])
check("teams timestamps are kept", parse(TEAMS)["all_turns"][0]["time"] == "0:04")
check("every turn gets a stable id",
      [t["id"] for t in parse(INLINE)["all_turns"]] == ["T1", "T2", "T3"])
check("a teams speaker heading is not mistaken for speech",
      "0:04" not in parse(TEAMS)["all_turns"][0]["text"])

print("\nA turn split across lines is one turn")
wrapped = parse("Ada Lovelace   0:04\nThis is the first line\nand this continues it.\n\nSam Okafor   0:10\nRight, understood completely.\n")
check("teams continuation lines are joined", wrapped["turns_total"] == 2, str(wrapped["turns_total"]))
check("and the text is joined in order",
      "first line and this continues it" in wrapped["all_turns"][0]["text"])

# ---------------------------------------------------------------- filler

print("\nFiller is dropped, meaning is not")
F = TranscriptParser._is_filler
for filler in ["Okay.", "Yeah", "Mm", "Thanks", "Bye", "Got it", "Sounds right",
               "you're on mute", "Can you hear me?", "Sorry, sorry.", "Hi everyone"]:
    check(f"filler: {filler!r}", F(filler, 4), "kept when it should be dropped")
for real in ["Okay, tax goes on its own line.",
             "Yeah, but only in production though.",
             "The flag defaults to off in production.",
             "I will raise a ticket to flip it."]:
    check(f"kept: {real[:40]!r}", not F(real, 4), "dropped when it should be kept")

check("a short turn is dropped", F("Fine by me", 4))
check("the minimum is configurable", not F("Fine by me", 2))
check("filler is counted, not deleted from the record",
      parse(INLINE)["turns_total"] == 3 and parse(INLINE)["turns_kept"] == 2)
check("the filler ratio is reported", parse(INLINE)["filler_ratio"] > 0)
check("filler dropping can be switched off",
      parse(INLINE, drop_filler=False)["turns_kept"] == 3)

# ---------------------------------------------------------------- budget

print("\nA transcript that does not fit says so")
long_talk = "".join(
    f"Speaker One: This is substantive turn number {i} about the checkout flow and its behaviour.\n"
    for i in range(200))
cut = parse(long_talk, max_brief_chars=2000)
check("the budget is enforced", cut["turns_sent"] < cut["turns_kept"])
check("the turns that did not fit are named", len(cut["turns_omitted"]) > 0)
check("the brief warns about them",
      "did not fit" in parser(pasted_transcript=long_talk, max_brief_chars=2000).build_brief().text)
check("a transcript that fits omits nothing", parse(INLINE)["turns_omitted"] == [])

# ---------------------------------------------------------------- guards

print("\nParser guards")
raises("no transcript is refused", lambda: parser().build_turns(), "no transcript reached")
raises("a greeting in the path field is refused",
       lambda: parser(transcript_path="hello").build_turns(), "no transcript reached")
raises("text with no speaker turns is refused",
       lambda: parse("just some prose with no speakers in it at all"), "no speaker turns")
raises("an all-filler transcript is refused",
       lambda: parse("Liam: Hi.\nNoor: Hey.\nLiam: Bye.\n"), "every one of")
raises("the all-filler refusal explains the risk rather than just failing",
       lambda: parse("Liam: Hi.\nNoor: Hey.\nLiam: Bye.\n"), "would invent them")

print("\nReading from disk")
tmp = Path(tempfile.mkdtemp())
(tmp / "m.txt").write_text(INLINE, encoding="utf-8")
check("a path is read", parser(transcript_path=str(tmp / "m.txt")).build_turns().data["turns_total"] == 3)
check("a quoted path is read",
      parser(transcript_path=f'"{tmp / "m.txt"}"').build_turns().data["turns_total"] == 3)
check("a missing path falls back to the default",
      parser(transcript_path="C:/nope.txt",
             default_transcript_path=str(tmp / "m.txt")).build_turns().data["turns_total"] == 3)
check("the meeting title defaults to the file name",
      parser(transcript_path=str(tmp / "m.txt")).build_turns().data["meeting"] == "m")
check("an explicit title wins",
      parser(transcript_path=str(tmp / "m.txt"), meeting_title="Sprint sync"
             ).build_turns().data["meeting"] == "Sprint sync")

# ---------------------------------------------------------- verification

print("\nVerification: a quote that was never said cannot get through")
folder = prepared()
real_quote = "The flag has to default to off in production"
r = writer(output_dir=str(folder), extracted=json.dumps([
    {"text": "Flag defaults to off in production", "category": "requirement", "quote": real_quote},
    {"text": "Add two-factor authentication to checkout", "category": "requirement",
     "quote": "we agreed to add two factor authentication at checkout"},
])).write_details().data
check("the real requirement is kept", r["verified_count"] == 1, str(r))
check("the invented one is rejected", r["rejected_count"] == 1)

issues = json.loads((folder / "requirements.json").read_text(encoding="utf-8"))
check("the rejection says why",
      "does not appear in the transcript" in issues["rejected"][0]["reason"])
check("the invented requirement is nowhere in the output",
      "two-factor" not in json.dumps(issues["issues"]))

print("\nAn item with no quote is not a finding")
r = writer(output_dir=str(folder), extracted=json.dumps([
    {"text": "Something nobody can check", "category": "requirement", "quote": ""},
])).write_details().data
check("no quote means rejected", r["verified_count"] == 0 and r["rejected_count"] == 1)
check("and the reason names the problem",
      "nothing to check it against" in json.loads(
          (folder / "requirements.json").read_text(encoding="utf-8"))["rejected"][0]["reason"])

print("\nA quote too short to prove anything is rejected")
r = writer(output_dir=str(folder), extracted=json.dumps([
    {"text": "Borrowed attribution", "category": "requirement", "quote": "the flag"},
])).write_details().data
check("a three-word quote does not verify", r["verified_count"] == 0, str(r))
check("the threshold is configurable",
      writer(output_dir=str(folder), min_quote_words=2, extracted=json.dumps([
          {"text": "Short but allowed", "category": "requirement", "quote": "the flag has"},
      ])).write_details().data["verified_count"] == 1)

print("\nMatching ignores punctuation and casing, not words")
for quote, should_pass in [
    ("the FLAG has to DEFAULT to off in production", True),
    ("the flag has to default to off in production.", True),
    ("the  flag   has to default to off in production", True),
    ("the flag has to default to on in production", False),
]:
    got = writer(output_dir=str(folder), extracted=json.dumps([
        {"text": "x", "category": "requirement", "quote": quote}])).write_details().data
    check(f"{'accepts' if should_pass else 'rejects'}: {quote[:46]!r}",
          (got["verified_count"] == 1) == should_pass, str(got["verified_count"]))

print("\nAttribution comes from the transcript, not from the model")
detail = writer(output_dir=str(folder), extracted=json.dumps([
    {"text": "Flag off in production", "category": "requirement", "quote": real_quote,
     "said_by": "Somebody Else", "owner": "Somebody Else"},
])).write_details().data
issues = json.loads((folder / "requirements.json").read_text(encoding="utf-8"))
check("the speaker is read from the matched turn",
      "Priya Sharma" in issues["issues"][0]["description"], issues["issues"][0]["description"][:120])
check("the model's claimed speaker is ignored",
      "Somebody Else" not in issues["issues"][0]["description"])
check("the turn id is recorded", "T1" in issues["issues"][0]["description"])

print("\nDuplicates are collapsed")
r = writer(output_dir=str(folder), extracted=json.dumps([
    {"text": "Flag defaults off", "category": "requirement", "quote": real_quote},
    {"text": "flag defaults off.", "category": "requirement", "quote": real_quote},
])).write_details().data
check("the same requirement twice is kept once", r["verified_count"] == 1, str(r))
check("and the duplicate is reported", r["rejected_count"] == 1)

# ------------------------------------------------------------ the reply

print("\nReading the model's reply")
cases = [
    ("a bare array", json.dumps([{"text": "a", "category": "requirement", "quote": real_quote}])),
    ("a fenced array", "```json\n" + json.dumps([{"text": "a", "category": "requirement", "quote": real_quote}]) + "\n```"),
    ("an object with a requirements key",
     json.dumps({"requirements": [{"text": "a", "category": "requirement", "quote": real_quote}]})),
    ("prose around the JSON",
     "Here is what I found:\n[" + json.dumps({"text": "a", "category": "requirement", "quote": real_quote}) + "]\nHope that helps."),
]
for label, reply in cases:
    got = writer(output_dir=str(folder), extracted=reply).write_details().data
    check(f"{label} parses", got["verified_count"] == 1, str(got))

check("an empty array is a valid answer",
      writer(output_dir=str(folder), extracted="[]").write_details().data["verified_count"] == 0)
raises("prose with no JSON is refused",
       lambda: writer(output_dir=str(folder), extracted="I could not find anything.").write_report(),
       "not json")
raises("an empty reply is refused",
       lambda: writer(output_dir=str(folder), extracted="   ").write_report(), "nothing to verify")

print("\nCategories")
for category, jira_type in [("requirement", "Story"), ("action_item", "Task"),
                            ("decision", "Task"), ("open_question", "Task")]:
    writer(output_dir=str(folder), extracted=json.dumps([
        {"text": f"a {category}", "category": category, "quote": real_quote}])).write_report()
    issues = json.loads((folder / "requirements.json").read_text(encoding="utf-8"))
    check(f"{category} maps to {jira_type}", issues["issues"][0]["issuetype"] == jira_type)
    check(f"{category} is labelled", category.replace("_", "-") in issues["issues"][0]["labels"])
writer(output_dir=str(folder), extracted=json.dumps([
    {"text": "x", "category": "nonsense", "quote": real_quote}])).write_report()
check("an unknown category falls back to requirement",
      json.loads((folder / "requirements.json").read_text(encoding="utf-8"))["issues"][0]["issuetype"] == "Story")

# ------------------------------------------------------- writer guards

print("\nWriter guards")
raises("no reports folder is refused", lambda: writer().write_report(), "set a reports folder")
raises("a missing turns file is named",
       lambda: writer(output_dir=tempfile.mkdtemp()).write_report(), "transcript_turns.json")
bad = Path(tempfile.mkdtemp())
(bad / "transcript_turns.json").write_text("{nope", encoding="utf-8")
raises("a corrupt turns file is refused",
       lambda: writer(output_dir=str(bad)).write_report(), "not valid json")
wrong = Path(tempfile.mkdtemp())
(wrong / "transcript_turns.json").write_text('{"meeting": "x"}', encoding="utf-8")
raises("a turns file with no turns is refused",
       lambda: writer(output_dir=str(wrong)).write_report(), "no turns")

# ------------------------------------------------------------- the report

print("\nThe report")
writer(output_dir=str(folder), extracted=json.dumps([
    {"text": "Flag defaults to off in production", "category": "requirement", "quote": real_quote},
    {"text": "Invented thing", "category": "requirement", "quote": "nobody ever said this sentence"},
])).write_report()
report = (folder / "requirements_report.md").read_text(encoding="utf-8")
check("verified items are listed", "Flag defaults to off in production" in report)
check("each carries its quote", real_quote in report)
check("each carries its speaker", "Priya Sharma" in report)
check("rejected items get their own table", "## Rejected (1)" in report)
check("the rejected item is named", "Invented thing" in report)
check("the report explains why rejections are printed", "silent drop" in report)
check("the report says attribution comes from the transcript",
      "comes from the transcript rather than from the model" in report)

empty_report_dir = prepared()
writer(output_dir=str(empty_report_dir), extracted="[]").write_report()
empty_report = (empty_report_dir / "requirements_report.md").read_text(encoding="utf-8")
check("a meeting that agreed nothing says so", "## Nothing was agreed" in empty_report)
check("and defends the empty answer", "worse than an empty one" in empty_report)

omitted_dir = prepared(long_talk, max_brief_chars=2000)
writer(output_dir=str(omitted_dir), extracted="[]").write_report()
check("an unreviewed tail is warned about in the report",
      "never reviewed" in (omitted_dir / "requirements_report.md").read_text(encoding="utf-8"))
check("and in the summary line",
      "never reviewed" in writer(output_dir=str(omitted_dir), extracted="[]").write_report().text)

named = writer(output_dir=str(folder), extracted="[]", report_name="sprint-12").write_report()
check("a report name without an extension gets .md", (folder / "sprint-12.md").is_file())
check("the details output reports where it wrote",
      writer(output_dir=str(folder), extracted="[]").write_details().data["report"].endswith("requirements_report.md"))
check("the project key reaches the payload",
      writer(output_dir=str(folder), project_key="PLAT", extracted=json.dumps([
          {"text": "x", "category": "requirement", "quote": real_quote}])).write_details().data
      and json.loads((folder / "requirements.json").read_text(encoding="utf-8"))["issues"][0]["project"] == "PLAT")

# ----------------------------------------------------------- the samples

print("\nThe sample transcripts in this folder")
EXPECTED = {
    "checkout_release_sync.vtt": ("webvtt", 33, ["Mei Lin", "Priya Sharma", "Raj Patel"]),
    "regression_triage_weekly.txt": ("teams", 19, ["Ada Lovelace", "Sam Okafor"]),
    "coffee_catchup.txt": ("teams", 11, ["Liam Fitzgerald", "Noor Hassan"]),
}
for name, (fmt, turns, speakers) in EXPECTED.items():
    path = SAMPLES / name
    if not path.is_file():
        check(f"{name} exists", False, str(path))
        continue
    a = parser(transcript_path=str(path)).build_turns().data
    check(f"{name}: parsed as {fmt}", a["format"] == fmt, a["format"])
    check(f"{name}: {turns} turns", a["turns_total"] == turns, str(a["turns_total"]))
    check(f"{name}: speakers", a["speakers"] == speakers, str(a["speakers"]))

check("the checkout sample drops about a third as filler",
      0.2 < parser(transcript_path=str(SAMPLES / "checkout_release_sync.vtt")
                   ).build_turns().data["filler_ratio"] < 0.45)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
