"""Tests for the CI Failure Extractor and the RCA Report Writer.

The agent's value is entirely in what it throws away and how it groups what is
left, so that is what these tests are about. A grouping that splits one npm
error block into four failures, or that counts a runner's closing summary as a
second set of failures, produces a report that looks thorough and is wrong
about the most basic question: how many things broke.

The other half is the refusals. A log from a build that passed must be refused
rather than explained, because a model asked to explain a failure that did not
happen will write a convincing explanation of one.

Run it with the Langflow virtual environment:

    09_LangFlow/.venv/Scripts/python.exe test_ci_failure_analyzer.py
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ci_failure_extractor import CIFailureExtractor  # noqa: E402
from rca_report_writer import RCAReportWriter  # noqa: E402

passed = failed = 0
HERE = Path(__file__).parent
SAMPLES = HERE / "sample_logs"


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


def extract(**kw):
    params = {"log_path": "", "default_log_path": "", "pasted_log": "",
              "max_quoted_lines": 6, "max_groups": 8, "output_dir": ""}
    params.update(kw)
    return CIFailureExtractor(**params)


def analyse(log, **kw):
    return extract(pasted_log=log, **kw).build_findings().data


def make_writer(**kw):
    params = {"rca": "The checkout page object returned null.", "output_dir": "",
              "report_name": "rca_report.md"}
    params.update(kw)
    return RCAReportWriter(**params)


def findings_dir(analysis):
    folder = Path(tempfile.mkdtemp())
    (folder / "ci_findings.json").write_text(json.dumps(analysis), encoding="utf-8")
    return folder


JENKINS_MIN = """Started by user Priya
[Pipeline] { (Test)
+ mvn -B clean test
[INFO] Tests run: 3, Failures: 1, Errors: 0, Skipped: 0
java.lang.AssertionError: expected [1] but found [2]
\tat com.shopfront.tests.CartTest.total(CartTest.java:21)
[INFO] BUILD FAILURE
ERROR: script returned exit code 1
Finished: FAILURE
"""

GHA_MIN = """2026-09-18T22:11:15.0012300Z ##[group]Run npx playwright test
2026-09-18T22:11:15.0013100Z ##[endgroup]
2026-09-18T22:11:52.8814500Z     TimeoutError: locator.click: Timeout 30000ms exceeded.
2026-09-18T22:11:52.8815200Z     Call log:
2026-09-18T22:11:52.8815900Z       - waiting for getByTestId('place-order-button')
2026-09-18T22:12:45.9981200Z   29 passed (1.5m)
2026-09-18T22:12:46.2210300Z ##[error]Process completed with exit code 1.
"""

CIRCLE_MIN = """====>> npm ci
npm error code ERESOLVE
npm error ERESOLVE could not resolve
npm error While resolving: @shopfront/design-system@4.0.0
npm error Conflicting peer dependency: react@19.0.0
Exited with code exit status 1
"""

# --------------------------------------------------------- CI system detection

print("\nWhich CI system wrote the log")
check("Jenkins is recognised", analyse(JENKINS_MIN)["ci_system"] == "jenkins")
check("GitHub Actions is recognised", analyse(GHA_MIN)["ci_system"] == "github_actions")
check("CircleCI is recognised", analyse(CIRCLE_MIN)["ci_system"] == "circleci")
check("the display name is carried through",
      analyse(GHA_MIN)["ci_system_name"] == "GitHub Actions")

print("\nTimestamps and colour codes do not defeat matching")
check("a GitHub Actions timestamp prefix is stripped before matching",
      analyse(GHA_MIN)["failures_total"] == 1)
check("ANSI colour is stripped before matching",
      analyse("====>> build\n\x1b[31mnpm error code ERESOLVE\x1b[0m\n"
              "Exited with code exit status 1\n")["failures_total"] == 1)

# ------------------------------------------------------------------- verdict

print("\nDid the run actually fail")
raises("a successful build is refused, not explained",
       lambda: analyse("[Pipeline] { (Test)\n[INFO] BUILD SUCCESS\nFinished: SUCCESS\n"),
       "does not contain a failure")
raises("a log with no failure marker is refused",
       lambda: analyse("[Pipeline] { (Test)\nsome output\nmore output\n"),
       "does not contain a failure")
raises("a failed run with no recognisable error is refused rather than guessed at",
       lambda: analyse("[Pipeline] { (Test)\nsomething went wrong somehow\n"
                       "ERROR: script returned exit code 1\nFinished: FAILURE\n"),
       "no recognisable error line")

def _refusal_message(log):
    try:
        analyse(log)
    except ValueError as exc:
        return str(exc)
    return ""


check("a passing build's refusal says the build passed",
      "successful build" in _refusal_message("[INFO] BUILD SUCCESS\nFinished: SUCCESS\n"))
check("a run reporting exit code 0 is not a failure",
      "does not contain a failure" in _refusal_message(
          "##[group]Run npm test\nProcess completed with exit code 0.\n"))

print("\nExit code and failed step")
check("Jenkins exit code is read", analyse(JENKINS_MIN)["exit_code"] == 1)
check("the Jenkins stage name is the failed step", analyse(JENKINS_MIN)["failed_step"] == "Test")
check("the GitHub Actions step name is the failed step",
      analyse(GHA_MIN)["failed_step"] == "npx playwright test")
check("the CircleCI step name is the failed step", analyse(CIRCLE_MIN)["failed_step"] == "npm ci")

# ------------------------------------------------------------------ grouping

print("\nGrouping: the same failure many times is one group")
repeated = "[Pipeline] { (Test)\n" + "".join(
    f'java.lang.NullPointerException: Cannot invoke "String.replace()" because getTotalText() is null\n'
    f"\tat com.shopfront.pages.CheckoutPage.getTotal(CheckoutPage.java:88)\n"
    f"\tat com.shopfront.tests.CheckoutTest.test{i}(CheckoutTest.java:{40 + i})\n"
    for i in range(9)
) + "[INFO] BUILD FAILURE\nFinished: FAILURE\n"
r = analyse(repeated)
check("nine identical exceptions are one group", r["group_count"] == 1, str(r["group_count"]))
check("all nine are still counted", r["groups"][0]["occurrences"] == 9)
check("the group keeps the line it was first seen at", r["groups"][0]["first_line"] == 2)
check("up to three examples are kept for the report", len(r["groups"][0]["examples"]) == 3)

print("\nGrouping: a stack frame is not a failure of its own")
check("frames under an exception do not become their own groups", r["group_count"] == 1)
check("a timeout's stack frames are absorbed",
      analyse("[Pipeline] { (Test)\n"
              "org.openqa.selenium.TimeoutException: Expected condition failed: waiting for x\n"
              "\tat org.openqa.selenium.support.ui.WebDriverWait.timeoutException(WebDriverWait.java:96)\n"
              "\tat com.shopfront.tests.CheckoutTest.underLoad(CheckoutTest.java:184)\n"
              "[INFO] BUILD FAILURE\nFinished: FAILURE\n")["group_count"] == 1)

print("\nGrouping: one npm error block is one failure")
check("the whole ERESOLVE block is a single group", analyse(CIRCLE_MIN)["group_count"] == 1)
check("and a single occurrence", analyse(CIRCLE_MIN)["failures_total"] == 1)

print("\nGrouping: values that differ between runs are normalised away")
two_numbers = ("[Pipeline] { (Test)\n"
               "java.lang.AssertionError: expected [2 items] but found [3 items]\n"
               "java.lang.AssertionError: expected [7 items] but found [9 items]\n"
               "[INFO] BUILD FAILURE\nFinished: FAILURE\n")
check("the same assertion with different numbers groups together",
      analyse(two_numbers)["group_count"] == 1, str(analyse(two_numbers)["group_count"]))
different = ("[Pipeline] { (Test)\n"
             "java.lang.AssertionError: expected [Card expired] but found [Payment declined]\n"
             "java.lang.AssertionError: expected [2 items] but found [3 items]\n"
             "[INFO] BUILD FAILURE\nFinished: FAILURE\n")
check("genuinely different assertions stay apart", analyse(different)["group_count"] == 2)

print("\nGrouping: a runner's closing summary is not a second set of failures")
recap = ("[Pipeline] { (Test)\n"
         "java.lang.AssertionError: expected [Card expired] but found [Payment declined]\n"
         "\tat com.shopfront.tests.CheckoutTest.expired(CheckoutTest.java:151)\n"
         "[INFO] Results:\n"
         "[ERROR] Failures:\n"
         "[ERROR]   CheckoutTest.expired:151 expected [Card expired] but found [Payment declined]\n"
         "[INFO] ------------------------------------------------------------------------\n"
         "[INFO] BUILD FAILURE\nFinished: FAILURE\n")
check("the recap does not double the count", analyse(recap)["failures_total"] == 1,
      str(analyse(recap)["failures_total"]))
check("the recap does not add a group", analyse(recap)["group_count"] == 1)

# ---------------------------------------------------------------- categories

print("\nCategories")
CASES = [
    ("dependency", "npm error code ERESOLVE"),
    ("dependency", "[ERROR] Failed to execute goal: Could not resolve dependencies for project"),
    ("compile", "[ERROR] COMPILATION ERROR :"),
    ("compile", "src/app.ts(14,22): error TS2345: Argument of type 'string' is not assignable"),
    ("infrastructure", "java.lang.OutOfMemoryError: Java heap space"),
    ("infrastructure", "write /dev/stdout: No space left on device"),
    ("configuration", "Error: Input required and not supplied: api-key"),
    ("network", "Error: connect ECONNREFUSED 127.0.0.1:4723"),
    ("timeout", "TimeoutError: locator.click: Timeout 30000ms exceeded."),
    ("assertion", "Error: expect(received).toHaveText(expected)"),
    ("assertion", "java.lang.AssertionError: expected [1] but found [2]"),
    ("exception", "java.lang.IllegalStateException: driver has already quit"),
]
for expected_category, line in CASES:
    log = f"[Pipeline] {{ (Test)\n{line}\n[INFO] BUILD FAILURE\nFinished: FAILURE\n"
    got = analyse(log)["groups"][0]["category"]
    check(f"{expected_category}: {line[:52]}", got == expected_category, f"got {got}")

print("\nThe specific cause wins over the generic one")
both = ("[Pipeline] { (Test)\n"
        "npm error code ERESOLVE\n"
        "[INFO] BUILD FAILURE\n"
        "[ERROR] Failed to execute goal on project app: There are test failures.\n"
        "Finished: FAILURE\n")
check("a dependency error is not filed as a generic build failure",
      analyse(both)["groups"][0]["category"] == "dependency")

print("\nNoise is not matched")
quiet = ("[Pipeline] { (Test)\n"
         "Downloading from central: https://repo.maven.apache.org/maven2/org/testng/testng.jar\n"
         "[INFO] Test loginWithValidCredentials PASSED\n"
         "[INFO] Copying 3 resources from src/main/resources\n"
         "java.lang.AssertionError: expected [1] but found [2]\n"
         "[INFO] BUILD FAILURE\nFinished: FAILURE\n")
check("passing tests and downloads are not failures", analyse(quiet)["failures_total"] == 1)
check("noise ratio reflects how much was discarded", analyse(quiet)["noise_ratio"] > 0.5)

# ------------------------------------------------------------- test totals

print("\nCounted test results")
check("Maven totals are read", analyse(JENKINS_MIN)["tests"] ==
      {"total": 3, "failed": 1, "passed": 2, "skipped": 0})
check("Maven failures and errors are added together",
      analyse("[Pipeline] { (Test)\n[INFO] Tests run: 25, Failures: 3, Errors: 9, Skipped: 2\n"
              "java.lang.AssertionError: expected [1] but found [2]\n"
              "[INFO] BUILD FAILURE\nFinished: FAILURE\n")["tests"]["failed"] == 12)
check("the final Maven total wins over per-class lines",
      analyse("[Pipeline] { (Test)\n[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0\n"
              "[INFO] Tests run: 25, Failures: 3, Errors: 9, Skipped: 2\n"
              "java.lang.AssertionError: expected [1] but found [2]\n"
              "[INFO] BUILD FAILURE\nFinished: FAILURE\n")["tests"]["total"] == 25)
check("Playwright counts are read", analyse(GHA_MIN)["tests"]["passed"] == 29)
check("a run with no tests reports none", analyse(CIRCLE_MIN)["tests"] == {})

# ---------------------------------------------------------- input handling

print("\nWhere the log comes from")
tmp = Path(tempfile.mkdtemp())
log_file = tmp / "build.log"
log_file.write_text(JENKINS_MIN, encoding="utf-8")
check("a path is read from disk", extract(log_path=str(log_file)).build_findings().data["failures_total"] == 1)
check("a quoted path is accepted", extract(log_path=f'"{log_file}"').build_findings().data["failures_total"] == 1)
check("a missing path falls back to the default",
      extract(log_path="C:/nope.log", default_log_path=str(log_file)).build_findings().data["failures_total"] == 1)
check("a pasted log beats the path",
      extract(log_path=str(log_file), pasted_log=CIRCLE_MIN).build_findings().data["ci_system"] == "circleci")
raises("no log at all is refused", lambda: extract().build_findings(), "no ci log reached")
raises("a greeting typed into the path field is refused",
       lambda: extract(log_path="hello there").build_findings(), "no ci log reached")
raises("an empty log is refused", lambda: analyse("   \n  \n"), "no ci log reached")

# ------------------------------------------------------------------- brief

print("\nThe brief sent to the model")
brief = extract(pasted_log=SAMPLES.joinpath("jenkins_maven_failure.log").read_text(encoding="utf-8")).build_brief().data["text"]
check("the brief leads with the counted facts", brief.startswith("# CI failure analysis"))
check("the brief names the failed step", "Failed step: Build" in brief)
check("the brief states how much was discarded", "irrelevant to the failure" in brief)
check("the brief carries the largest group first", brief.index("Unhandled exception") < brief.index("Timeout"))
check("the brief quotes the evidence", "CheckoutPage.getTotal" in brief)
capped = extract(pasted_log=SAMPLES.joinpath("jenkins_maven_failure.log").read_text(encoding="utf-8"),
                 max_groups=2).build_brief().data["text"]
check("the brief caps how many groups it describes", "and 2 smaller group(s)" in capped, capped[-200:])
check("the brief is Data so the splitter can chunk it",
      "text" in extract(pasted_log=JENKINS_MIN).build_brief().data)

# -------------------------------------------------------------- persistence

print("\nHand-off to the report writer")
out = Path(tempfile.mkdtemp())
extract(pasted_log=JENKINS_MIN, output_dir=str(out)).build_brief()
check("the brief writes ci_findings.json", (out / "ci_findings.json").is_file())
check("the findings file is valid JSON with groups",
      "groups" in json.loads((out / "ci_findings.json").read_text(encoding="utf-8")))
nested = Path(tempfile.mkdtemp()) / "nested" / "reports"
extract(pasted_log=JENKINS_MIN, output_dir=str(nested)).build_findings()
check("a missing reports folder is created", (nested / "ci_findings.json").is_file())
check("no reports folder is not an error",
      extract(pasted_log=JENKINS_MIN).build_brief().data["text"].startswith("# CI"))

# ------------------------------------------------------------ report writer

print("\nReport writer guards")
raises("no reports folder is refused", lambda: make_writer().write_report(), "set a reports folder")
raises("a missing findings file is named",
       lambda: make_writer(output_dir=tempfile.mkdtemp()).write_report(), "ci_findings.json")
bad = Path(tempfile.mkdtemp())
(bad / "ci_findings.json").write_text("{not json", encoding="utf-8")
raises("a corrupt findings file is refused",
       lambda: make_writer(output_dir=str(bad)).write_report(), "not valid json")
wrong = Path(tempfile.mkdtemp())
(wrong / "ci_findings.json").write_text('{"exit_code": 1}', encoding="utf-8")
raises("a findings file with no groups is refused",
       lambda: make_writer(output_dir=str(wrong)).write_report(), "no failure groups")
good = findings_dir(analyse(SAMPLES.joinpath("jenkins_maven_failure.log").read_text(encoding="utf-8")))
raises("an empty analysis is refused",
       lambda: make_writer(output_dir=str(good), rca="  ").write_report(), "no analysis")

print("\nReport writer output")
summary = make_writer(output_dir=str(good),
                      rca="```markdown\nOne page object returns null.\n```").write_report()
report = (good / "rca_report.md").read_text(encoding="utf-8")
check("a fenced reply is unwrapped", "One page object returns null." in report and "```markdown" not in report)
check("the analysis is labelled as model-written", "written by a language model" in report)
check("the report opens with the at-a-glance table", "## At a glance" in report)
check("the report has a what-failed table", "## What failed" in report)
check("the report quotes the evidence with line numbers", "First at line 102" in report)
check("the report names the failed step", "| Failed step | Build |" in report)
check("the report states the noise discarded", "discarded as noise" in report)
check("the report carries the test totals", "12 failed" in report)
check("the summary names the report file", "rca_report.md" in summary.text)
check("the summary leads with the failing step", "the 'Build' step failed" in summary.text)

make_writer(output_dir=str(good), rca="Plain prose.").write_report()
report = (good / "rca_report.md").read_text(encoding="utf-8")
check("an unfenced reply is written as-is", "Plain prose." in report)
make_writer(output_dir=str(good), rca="Ok.", report_name="build-1842").write_report()
check("a report name without an extension gets .md", (good / "build-1842.md").is_file())
check("the details output reports where it wrote",
      make_writer(output_dir=str(good), rca="Ok.").write_details().data["report"].endswith("rca_report.md"))

# ----------------------------------------------------------- the real logs

print("\nThe sample logs in this folder")
EXPECTED = {
    "jenkins_maven_failure.log": ("jenkins", 12, 4, "Build"),
    "github_actions_playwright_failure.log": ("github_actions", 3, 2, "npx playwright test --reporter=list"),
    "circleci_npm_failure.log": ("circleci", 1, 1, "npm ci"),
}
for name, (system, failures, groups, step) in EXPECTED.items():
    path = SAMPLES / name
    if not path.is_file():
        check(f"{name} exists", False, str(path))
        continue
    a = extract(log_path=str(path)).build_findings().data
    check(f"{name}: {system}", a["ci_system"] == system, a["ci_system"])
    check(f"{name}: {failures} failures in {groups} group(s)",
          a["failures_total"] == failures and a["group_count"] == groups,
          f"{a['failures_total']} in {a['group_count']}")
    check(f"{name}: failed step is {step!r}", a["failed_step"] == step, a["failed_step"])

jm = extract(log_path=str(SAMPLES / "jenkins_maven_failure.log")).build_findings().data
check("jenkins sample: the failure count matches the run's own total",
      jm["failures_total"] == jm["tests"]["failed"],
      f"{jm['failures_total']} vs {jm['tests']['failed']}")
check("jenkins sample: nine failures share one cause",
      jm["groups"][0]["occurrences"] == 9 and jm["groups"][0]["category"] == "exception")
check("jenkins sample: over 90% of the log is discarded", jm["noise_ratio"] > 0.9,
      f"{jm['noise_ratio']:.2%}")

gha = extract(log_path=str(SAMPLES / "github_actions_playwright_failure.log")).build_findings().data
check("github actions sample: the failure count matches the run's own total",
      gha["failures_total"] == gha["tests"]["failed"])
check("github actions sample: both timeouts are the same locator",
      gha["groups"][0]["occurrences"] == 2 and gha["groups"][0]["category"] == "timeout")

raises("the passing sample is refused",
       lambda: extract(log_path=str(SAMPLES / "jenkins_successful_build.log")).build_findings(),
       "successful build")

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
