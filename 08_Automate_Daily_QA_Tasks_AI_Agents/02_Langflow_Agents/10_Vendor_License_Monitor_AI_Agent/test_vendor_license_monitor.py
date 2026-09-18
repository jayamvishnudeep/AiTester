"""Tests for the Inactivity Filter and the License Report Writer.

This agent recommends taking someone's tool access away, so the tests are
weighted towards the two ways that goes wrong. First, the boundaries: every
threshold is checked one day either side, because "60 days" and "61 days" are
the difference between leaving a colleague alone and putting their name on a
revoke list. Second, the refusals: no log, a malformed log, a missing field or
a missing findings file must all stop the run rather than produce a confident
report about accounts nobody verified.

Run it with the Langflow virtual environment:

    09_LangFlow/.venv/Scripts/python.exe test_vendor_license_monitor.py
"""

import json
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from license_activity_filter import LicenseActivityFilter  # noqa: E402
from license_report_writer import LicenseReportWriter  # noqa: E402

passed = failed = 0
REF = "2026-09-19"
REF_DATE = date(2026, 9, 19)
HERE = Path(__file__).parent


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}" + (f"  -- {detail}" if detail else ""))


def raises(name, fn, fragment):
    """The component must refuse, and the message must say something useful."""
    try:
        fn()
    except ValueError as exc:
        check(name, fragment.lower() in str(exc).lower(), f"message was: {exc}")
    except Exception as exc:  # noqa: BLE001 - a non-ValueError is itself the failure
        check(name, False, f"raised {type(exc).__name__}: {exc}")
    else:
        check(name, False, "no error raised")


def ago(days):
    return (REF_DATE - timedelta(days=days)).isoformat()


def make_filter(**kw):
    params = {
        "log_path": "", "default_log_path": "", "pasted_log": "",
        "dormant_after_days": 60, "new_account_grace_days": 14,
        "exceptions": "", "reference_date": REF, "max_listed": 15, "output_dir": "",
    }
    params.update(kw)
    return LicenseActivityFilter(**params)


def analyze(**kw):
    return make_filter(**kw).build_findings().data


CSV_HEADER = "tool,plan,user_email,user_name,account_created,last_login,seat_cost_month"


def csv_log(rows):
    """rows = [(tool, email, created, last_login, cost)]"""
    lines = [CSV_HEADER]
    for tool, email, created, login, cost in rows:
        name = email.split("@")[0].title()
        lines.append(f"{tool},Standard,{email},{name},{created},{login},{cost}")
    return "\n".join(lines) + "\n"


def one(login=None, created="2024-01-01", cost="10.00", **kw):
    """Analyse a single-seat log and return that one account."""
    return analyze(pasted_log=csv_log([("Jira", "a@x.com", created, login or "", cost)]), **kw)


def status_of(analysis):
    a = analysis["accounts"][0]
    return a["base_status"], a["tier"]


def make_writer(**kw):
    params = {"recommendations": "Do the Jira seats first.", "output_dir": "",
              "report_name": "license_report.md"}
    params.update(kw)
    return LicenseReportWriter(**params)


def findings_dir(analysis=None, **kw):
    """A temp folder holding a license_findings.json, ready for the writer."""
    folder = Path(tempfile.mkdtemp())
    if analysis is None:
        analysis = analyze(pasted_log=csv_log([
            ("Jira", "old@x.com", "2024-01-01", ago(300), "8.50"),
            ("Jira", "ok@x.com", "2024-01-01", ago(3), "8.50"),
        ]), **kw)
    (folder / "license_findings.json").write_text(json.dumps(analysis), encoding="utf-8")
    return folder, analysis


# ------------------------------------------------------------------ dormancy

print("\nDormancy threshold (60 days), one day either side")
check("59 days idle is active", status_of(one(login=ago(59))) == ("active", None))
check("exactly 60 days idle is still active", status_of(one(login=ago(60))) == ("active", None))
check("61 days idle is dormant", status_of(one(login=ago(61))) == ("dormant", "confirm_first"))
check("a login today is active", status_of(one(login=ago(0))) == ("active", None))
check("threshold is configurable", status_of(one(login=ago(31), dormant_after_days=30)) == ("dormant", "confirm_first"))

print("\nRevoke tier (twice the threshold), one day either side")
check("119 days idle needs confirming", status_of(one(login=ago(119))) == ("dormant", "confirm_first"))
check("exactly 120 days idle is revoke now", status_of(one(login=ago(120))) == ("dormant", "revoke_now"))
check("121 days idle is revoke now", status_of(one(login=ago(121))) == ("dormant", "revoke_now"))

print("\nNew-account grace period (14 days), one day either side")
check("never used, created 13 days ago, is too new", status_of(one(created=ago(13))) == ("too_new", None))
check("never used, created exactly 14 days ago, is too new", status_of(one(created=ago(14))) == ("too_new", None))
check("never used, created 15 days ago, is never activated",
      status_of(one(created=ago(15))) == ("never_activated", "revoke_now"))
check("never activated is always revoke now, however recent",
      status_of(one(created=ago(15)))[1] == "revoke_now")
check("grace period is configurable", status_of(one(created=ago(20), new_account_grace_days=30)) == ("too_new", None))

print("\nDays reported, and what they are counted from")
check("an idle account counts from its last login",
      (lambda a: a["days"] == 90 and a["days_kind"] == "since_last_login")(one(login=ago(90))["accounts"][0]))
check("an unused account counts from its creation date",
      (lambda a: a["days"] == 400 and a["days_kind"] == "since_created")(one(created=ago(400))["accounts"][0]))

# -------------------------------------------------------------------- money

print("\nCost arithmetic")
acc = one(login=ago(200), cost="42.00")["accounts"][0]
check("monthly cost comes from the log", acc["monthly_cost"] == 42.00)
check("annual cost is twelve months", acc["annual_cost"] == 504.00)

money = analyze(pasted_log=csv_log([
    ("Jira", "a@x.com", "2024-01-01", ago(300), "8.50"),     # revoke now
    ("BrowserStack", "b@x.com", "2024-01-01", ago(300), "42.00"),  # revoke now
    ("Jira", "c@x.com", "2024-01-01", ago(70), "8.50"),      # confirm first
    ("Jira", "d@x.com", "2024-01-01", ago(2), "8.50"),       # active
]))
check("revoke-now total sums only that tier", money["totals"]["revoke_now_annual"] == 606.00,
      str(money["totals"]))
check("confirm-first total is kept separate", money["totals"]["confirm_first_annual"] == 102.00)
check("monthly totals are separate from annual", money["totals"]["revoke_now_monthly"] == 50.50)
check("tier counts match the lists", money["totals"]["revoke_now_count"] == 2
      and money["totals"]["confirm_first_count"] == 1)
check("an active seat contributes nothing", money["totals"]["revoke_now_annual"] == 606.00)
check("revoke list is sorted by annual saving, biggest first",
      [a["annual_cost"] for a in money["revoke_now"]] == [504.00, 102.00])

# ------------------------------------------------------------------ per tool

print("\nPer-tool rollup")
tools = {t["tool"]: t for t in money["per_tool"]}
check("seats are counted per tool", tools["Jira"]["seats"] == 3 and tools["BrowserStack"]["seats"] == 1)
check("flagged counts both tiers", tools["Jira"]["flagged"] == 2)
check("dormant fraction is flagged over evaluated", tools["Jira"]["dormant_fraction"] == 0.67,
      str(tools["Jira"]))
check("a fully dormant tool reads 1.0", tools["BrowserStack"]["dormant_fraction"] == 1.0)
check("per-tool recoverable is its own seats only", tools["BrowserStack"]["annual_recoverable"] == 504.00)
check("tools are ordered by what they could save",
      [t["tool"] for t in money["per_tool"]] == ["BrowserStack", "Jira"])

# ---------------------------------------------------------------- exceptions

print("\nExceptions list")
EX_LOG = csv_log([
    ("Jira", "leave@x.com", "2024-01-01", ago(300), "8.50"),
    ("Jira", "gone@x.com", "2024-01-01", ago(300), "8.50"),
])
ex = analyze(pasted_log=EX_LOG, exceptions="leave@x.com")
check("a bare email suppresses the finding", ex["totals"]["revoke_now_count"] == 1)
check("the suppressed account is reported, not dropped", len(ex["exceptions_applied"]) == 1)
check("the suppression records what it would have been",
      ex["exceptions_applied"][0]["tier"] == "revoke_now")
check("an excepted seat is not in the revoke list",
      all(a["user_email"] != "leave@x.com" for a in ex["revoke_now"]))
check("an excepted seat's money is not counted as recoverable",
      ex["totals"]["revoke_now_annual"] == 102.00)

ex_dash = analyze(pasted_log=EX_LOG, exceptions="leave@x.com - parental leave until March")
check("'email - reason' parses", ex_dash["exceptions_applied"][0]["exception_reason"] == "parental leave until March")
ex_colon = analyze(pasted_log=EX_LOG, exceptions="leave@x.com: shared service account")
check("'email: reason' parses", ex_colon["exceptions_applied"][0]["exception_reason"] == "shared service account")
check("a bare email has no reason", ex["exceptions_applied"][0]["exception_reason"] == "")

ex_case = analyze(pasted_log=csv_log([("Jira", "Mixed.Case@X.com", "2024-01-01", ago(300), "8.50")]),
                  exceptions="mixed.case@x.com")
check("matching ignores case", len(ex_case["exceptions_applied"]) == 1)

ex_multi = analyze(pasted_log=EX_LOG, exceptions="\n  leave@x.com  \n\n  gone@x.com : left the company \n")
check("blank lines and padding are ignored", ex_multi["totals"]["revoke_now_count"] == 0)
check("every exception line is applied", len(ex_multi["exceptions_applied"]) == 2)
check("exceptions_defined counts the list, not the matches", ex_multi["exceptions_defined"] == 2)

ex_active = analyze(pasted_log=csv_log([("Jira", "busy@x.com", "2024-01-01", ago(2), "8.50")]),
                    exceptions="busy@x.com")
check("an exception on an active seat suppresses nothing", ex_active["exceptions_applied"] == [])

ex_tool = analyze(pasted_log=csv_log([
    ("Jira", "leave@x.com", "2024-01-01", ago(300), "8.50"),
    ("Jira", "busy@x.com", "2024-01-01", ago(2), "8.50"),
]), exceptions="leave@x.com")
jira = ex_tool["per_tool"][0]
check("an excepted seat leaves the dormant-fraction denominator",
      jira["evaluated_seats"] == 1 and jira["dormant_fraction"] == 0.0, str(jira))
check("an excepted seat still counts as a seat", jira["seats"] == 2)

# --------------------------------------------------------------- CSV parsing

print("\nCSV parsing")
csv_ok = analyze(pasted_log=csv_log([
    ("Jira", "a@x.com", "2024-01-01", ago(3), "8.50"),
    ("TestRail", "b@x.com", "2024-01-01", "", "34.00"),
]))
check("every row is read", csv_ok["accounts_total"] == 2)
check("a blank last_login means never logged in", csv_ok["accounts"][1]["last_login"] is None)
check("plan is carried through", csv_ok["accounts"][0]["plan"] == "Standard")
check("the person's name is carried through", csv_ok["accounts"][0]["user_name"] == "A")

raises("a missing column is named", lambda: analyze(pasted_log="tool,user_email\nJira,a@x.com\n"),
       "missing column")
raises("a blank tool stops the run",
       lambda: analyze(pasted_log=CSV_HEADER + "\n,Standard,a@x.com,A,2024-01-01,,8.50\n"),
       "line 2: missing 'tool'")
raises("a blank email stops the run",
       lambda: analyze(pasted_log=CSV_HEADER + "\nJira,Standard,,A,2024-01-01,,8.50\n"),
       "missing 'user_email'")
raises("a blank account_created stops the run",
       lambda: analyze(pasted_log=CSV_HEADER + "\nJira,Standard,a@x.com,A,,,8.50\n"),
       "missing 'account_created'")
raises("a malformed date stops the run",
       lambda: analyze(pasted_log=csv_log([("Jira", "a@x.com", "01/02/2024", "", "8.50")])),
       "not a valid date")
raises("a malformed last_login stops the run",
       lambda: analyze(pasted_log=csv_log([("Jira", "a@x.com", "2024-01-01", "last tuesday", "8.50")])),
       "not a valid date")
raises("a non-numeric seat cost stops the run",
       lambda: analyze(pasted_log=csv_log([("Jira", "a@x.com", "2024-01-01", "", "free")])),
       "not a valid seat cost")
raises("a negative seat cost stops the run",
       lambda: analyze(pasted_log=csv_log([("Jira", "a@x.com", "2024-01-01", "", "-8.50")])),
       "cannot be negative")
raises("a header with no rows stops the run", lambda: analyze(pasted_log=CSV_HEADER + "\n"),
       "no user rows")

# -------------------------------------------------------------- JSON parsing

print("\nJSON parsing")
JSON_OK = json.dumps({"tools": [{
    "name": "Postman", "plan": "Team", "seat_cost_month": 12.00,
    "users": [
        {"email": "a@x.com", "name": "Ada", "account_created": "2024-01-01", "last_login": ago(3)},
        {"email": "b@x.com", "name": "Ben", "account_created": "2024-01-01", "last_login": None},
    ],
}]})
js = analyze(pasted_log=JSON_OK)
check("nested users are flattened to rows", js["accounts_total"] == 2)
check("the tool name reaches every row", {a["tool"] for a in js["accounts"]} == {"Postman"})
check("the tool's seat cost reaches every row",
      all(a["monthly_cost"] == 12.00 for a in js["accounts"]))
check("a null last_login means never logged in", js["accounts"][1]["last_login"] is None)
check("a null last_login past grace is revoke now", js["accounts"][1]["tier"] == "revoke_now")

raises("a JSON array is refused as the wrong shape", lambda: analyze(pasted_log="[]"), '"tools" list')
raises("JSON without tools is refused", lambda: analyze(pasted_log='{"users": []}'), '"tools" list')
raises("a tool without a name is refused",
       lambda: analyze(pasted_log=json.dumps({"tools": [{"seat_cost_month": 1, "users": []}]})),
       "missing 'name'")
raises("a tool without users is refused",
       lambda: analyze(pasted_log=json.dumps({"tools": [{"name": "Postman", "seat_cost_month": 1}]})),
       "missing a 'users' list")
raises("a tool without a seat cost is refused",
       lambda: analyze(pasted_log=json.dumps({"tools": [{"name": "Postman", "users": []}]})),
       "not a valid seat cost")
raises("a user without an email is refused",
       lambda: analyze(pasted_log=json.dumps({"tools": [{"name": "Postman", "seat_cost_month": 1,
                                                         "users": [{"account_created": "2024-01-01"}]}]})),
       "missing 'email'")
raises("a user without a creation date is refused",
       lambda: analyze(pasted_log=json.dumps({"tools": [{"name": "Postman", "seat_cost_month": 1,
                                                         "users": [{"email": "a@x.com"}]}]})),
       "missing 'account_created'")
raises("a JSON tool with no users at all stops the run",
       lambda: analyze(pasted_log=json.dumps({"tools": [{"name": "Postman", "seat_cost_month": 1, "users": []}]})),
       "no user rows")

# ------------------------------------------------------------ input handling

print("\nWhere the log comes from")
tmp = Path(tempfile.mkdtemp())
csv_file = tmp / "activity.csv"
csv_file.write_text(csv_log([("Jira", "a@x.com", "2024-01-01", ago(300), "8.50")]), encoding="utf-8")
json_file = tmp / "activity.json"
json_file.write_text(JSON_OK, encoding="utf-8")

check("a CSV path is read from disk", analyze(log_path=str(csv_file))["accounts_total"] == 1)
check("a JSON path is read from disk", analyze(log_path=str(json_file))["accounts_total"] == 2)
check("a quoted path is accepted", analyze(log_path=f'"{csv_file}"')["accounts_total"] == 1)
check("a missing path falls back to the default",
      analyze(log_path="C:/nope/missing.csv", default_log_path=str(csv_file))["accounts_total"] == 1)
check("a pasted log beats both paths",
      analyze(log_path=str(json_file), pasted_log=csv_log([("Jira", "a@x.com", "2024-01-01", "", "8.50")]))["accounts_total"] == 1)

bom_file = tmp / "bom.csv"
bom_file.write_bytes(b"\xef\xbb\xbf" + csv_log([("Jira", "a@x.com", "2024-01-01", ago(300), "8.50")]).encode())
check("a byte-order mark does not break the header", analyze(log_path=str(bom_file))["accounts_total"] == 1)

raises("no log at all is refused", lambda: analyze(), "invented revoke list")
raises("a greeting typed into the path field is refused", lambda: analyze(log_path="hello"),
       "no activity log")

# --------------------------------------------------------------- date basis

print("\nReference date")
check("the reference date is reported", one(login=ago(100))["reference_date"] == REF)
check("an empty reference date means today",
      analyze(reference_date="", pasted_log=csv_log([("Jira", "a@x.com", "2024-01-01", "", "8.50")]))["reference_date"]
      == date.today().isoformat())
raises("a malformed reference date is refused",
       lambda: one(login=ago(100), reference_date="19-09-2026"), "not a valid date")

# -------------------------------------------------------------- persistence

print("\nHand-off to the report writer")
out = Path(tempfile.mkdtemp())
make_filter(pasted_log=csv_log([("Jira", "a@x.com", "2024-01-01", ago(300), "8.50")]),
            output_dir=str(out)).build_brief()
written = out / "license_findings.json"
check("the brief writes license_findings.json", written.is_file())
check("the findings file is valid JSON with accounts",
      "accounts" in json.loads(written.read_text(encoding="utf-8")))

out2 = Path(tempfile.mkdtemp()) / "nested" / "reports"
make_filter(pasted_log=csv_log([("Jira", "a@x.com", "2024-01-01", ago(300), "8.50")]),
            output_dir=str(out2)).build_findings()
check("a missing reports folder is created", (out2 / "license_findings.json").is_file())

no_dir = make_filter(pasted_log=csv_log([("Jira", "a@x.com", "2024-01-01", ago(300), "8.50")]))
check("no reports folder is not an error", no_dir.build_brief().text.startswith("# Vendor license activity"))

print("\nThe prompt brief")
brief = make_filter(pasted_log=csv_log([
    ("Jira", "a@x.com", "2024-01-01", ago(300), "8.50"),
    ("Jira", "b@x.com", "2024-01-01", ago(2), "8.50"),
    ("Jira", "c@x.com", ago(3), "", "8.50"),
    ("Jira", "d@x.com", "2024-01-01", ago(70), "8.50"),
]), exceptions="e@x.com").build_brief().text
check("the brief states the reference date", REF in brief)
check("the brief carries the totals", "Revoke now: 1 seats" in brief)
check("the brief breaks down by tool", "## Per tool" in brief)
check("the brief lists the flagged accounts", "a@x.com" in brief)
check("the brief shows accounts inside the grace period", "## Too new to judge" in brief)
# The prompt asks the model to name these; given only a count it reports the tier empty.
check("the brief names the confirm-first accounts, not just the count",
      "## Confirm first, all 1" in brief and "d@x.com" in brief, brief)
capped = make_filter(pasted_log=csv_log([
    ("Jira", f"u{i}@x.com", "2024-01-01", ago(300), "8.50") for i in range(5)
]), max_listed=2).build_brief().text
check("the brief caps the list it sends the model", "... and 3 more" in capped)

# ------------------------------------------------------------ report writer

print("\nReport writer guards")
raises("no reports folder is refused", lambda: make_writer().write_report(),
       "set a reports folder")
raises("a missing findings file is named",
       lambda: make_writer(output_dir=tempfile.mkdtemp()).write_report(),
       "license_findings.json")

bad = Path(tempfile.mkdtemp())
(bad / "license_findings.json").write_text("{not json", encoding="utf-8")
raises("a corrupt findings file is refused", lambda: make_writer(output_dir=str(bad)).write_report(),
       "not valid json")

wrong = Path(tempfile.mkdtemp())
(wrong / "license_findings.json").write_text('{"totals": {}}', encoding="utf-8")
raises("a findings file with no accounts is refused",
       lambda: make_writer(output_dir=str(wrong)).write_report(), "no accounts")

good_dir, good_analysis = findings_dir()
raises("empty recommendations are refused",
       lambda: make_writer(output_dir=str(good_dir), recommendations="   ").write_report(),
       "no recommendations")

print("\nReport writer output")
fenced = make_writer(output_dir=str(good_dir),
                     recommendations="```markdown\nCut the Jira seat first.\n```").write_report()
report = (good_dir / "license_report.md").read_text(encoding="utf-8")
check("a fenced reply is unwrapped", "Cut the Jira seat first." in report and "```" not in report)
check("the recommendations are labelled as model-written",
      "written by a language model" in report)
check("the summary names the report file", "license_report.md" in fenced.text)
check("the summary carries the counts", "Revoke now: 1 seats" in fenced.text)

make_writer(output_dir=str(good_dir), recommendations="Plain prose, no fence.").write_report()
report = (good_dir / "license_report.md").read_text(encoding="utf-8")
check("an unfenced reply is written as-is", "Plain prose, no fence." in report)
check("the report opens with the at-a-glance table", "## At a glance" in report)
check("the report breaks down by tool", "## By tool" in report)
check("the report has a revoke-now table", "## Revoke now (1)" in report)
check("the report has a confirm-first section", "## Confirm first (0)" in report)
check("an empty tier says so rather than showing an empty table",
      "Nothing in this tier." in report)
check("the flagged account is named in full", "old@x.com" in report)
check("the active account is not on a revoke list", "ok@x.com" not in report)
check("the report states what dormant means", "no login in 60 days" in report)

ex_dir, _ = findings_dir(analyze(pasted_log=EX_LOG, exceptions="leave@x.com - parental leave"))
make_writer(output_dir=str(ex_dir), recommendations="Ok.").write_report()
ex_report = (ex_dir / "license_report.md").read_text(encoding="utf-8")
check("exceptions get their own table", "## Exceptions applied (1)" in ex_report)
check("the exception's reason is printed", "parental leave" in ex_report)

new_dir, _ = findings_dir(analyze(pasted_log=csv_log([
    ("Jira", "new@x.com", ago(3), "", "8.50"),
    ("Jira", "old@x.com", "2024-01-01", ago(300), "8.50"),
])))
make_writer(output_dir=str(new_dir), recommendations="Ok.").write_report()
new_report = (new_dir / "license_report.md").read_text(encoding="utf-8")
check("accounts inside the grace period are shown, not hidden",
      "## Inside the grace period (1)" in new_report and "new@x.com" in new_report)

named = make_writer(output_dir=str(good_dir), recommendations="Ok.", report_name="q3-review").write_report()
check("a report name without an extension gets .md", (good_dir / "q3-review.md").is_file())
check("the details output reports where it wrote",
      make_writer(output_dir=str(good_dir), recommendations="Ok.").write_details().data["report"].endswith("license_report.md"))

# ----------------------------------------------------------- the real samples

print("\nThe sample logs in this folder")
csv_sample = HERE / "sample_logs" / "tool_activity.csv"
json_sample = HERE / "sample_logs" / "vendor_tools.json"

if csv_sample.is_file():
    s = analyze(log_path=str(csv_sample))
    check("CSV sample: 24 accounts", s["accounts_total"] == 24, str(s["accounts_total"]))
    check("CSV sample: status mix is the one the demo needs",
          s["status_counts"] == {"active": 10, "dormant": 10, "never_activated": 2, "too_new": 2},
          str(s["status_counts"]))
    check("CSV sample: 10 seats to revoke now", s["totals"]["revoke_now_count"] == 10)
    check("CSV sample: $3,210.00 a year recoverable", s["totals"]["revoke_now_annual"] == 3210.00,
          str(s["totals"]["revoke_now_annual"]))
    check("CSV sample: 2 seats to confirm first", s["totals"]["confirm_first_count"] == 2)
    check("CSV sample: $204.00 a year at risk", s["totals"]["confirm_first_annual"] == 204.00)
    check("CSV sample: BrowserStack is the worst-value tool",
          s["per_tool"][0]["tool"] == "BrowserStack")
    check("CSV sample: BrowserStack is two thirds dormant",
          s["per_tool"][0]["dormant_fraction"] == 0.67, str(s["per_tool"][0]))

    s_ex = analyze(log_path=str(csv_sample), exceptions="kai@shopfront.example.com - approved leave")
    check("CSV sample: the exceptions demo removes exactly one seat",
          s_ex["totals"]["revoke_now_count"] == 9 and s_ex["totals"]["revoke_now_annual"] == 3108.00,
          str(s_ex["totals"]))
    check("CSV sample: the held-back seat is still reported",
          len(s_ex["exceptions_applied"]) == 1
          and s_ex["exceptions_applied"][0]["exception_reason"] == "approved leave")
else:
    check("CSV sample exists", False, str(csv_sample))

if json_sample.is_file():
    j = analyze(log_path=str(json_sample))
    check("JSON sample: 11 accounts", j["accounts_total"] == 11, str(j["accounts_total"]))
    check("JSON sample: status mix is the one the demo needs",
          j["status_counts"] == {"active": 3, "dormant": 6, "never_activated": 1, "too_new": 1},
          str(j["status_counts"]))
    check("JSON sample: 5 seats to revoke now", j["totals"]["revoke_now_count"] == 5)
    check("JSON sample: $5,544.00 a year recoverable", j["totals"]["revoke_now_annual"] == 5544.00,
          str(j["totals"]["revoke_now_annual"]))
    check("JSON sample: 2 seats to confirm first", j["totals"]["confirm_first_count"] == 2)
    check("JSON sample: $1,944.00 a year at risk", j["totals"]["confirm_first_annual"] == 1944.00,
          str(j["totals"]["confirm_first_annual"]))
    check("JSON sample: Sauce Labs is the worst-value tool", j["per_tool"][0]["tool"] == "Sauce Labs")
else:
    check("JSON sample exists", False, str(json_sample))

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
