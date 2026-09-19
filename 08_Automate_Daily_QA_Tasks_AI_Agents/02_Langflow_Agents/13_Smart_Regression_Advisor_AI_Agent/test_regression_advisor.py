"""Tests for the Regression Impact Analyzer and the Regression Plan Writer.

This agent recommends NOT running things, so the tests are weighted almost
entirely towards false negatives. A subset with one test too many costs a few
minutes; a subset with one test too few is silent - the suite goes green, the
regression ships, and nothing in the output ever looked wrong.

So the questions asked here are mostly "does this test still get selected":
through an alias, through a page object, through a re-export, across a rename.
And the escalation rules get the same treatment from the other side - a change
that cannot be modelled as a graph edge must force the whole suite rather than
produce a confident subset.

Run it with the Langflow virtual environment:

    09_LangFlow/.venv/Scripts/python.exe test_regression_advisor.py
"""

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from regression_impact_analyzer import RegressionImpactAnalyzer  # noqa: E402
from regression_plan_writer import RegressionPlanWriter  # noqa: E402

passed = failed = 0
HERE = Path(__file__).parent
REPO = HERE / "sample_repo"
DIFFS = HERE / "sample_diffs"


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


def analyzer(**kw):
    params = {"diff": "", "default_diff": "", "pasted_diff": "", "repo_path": str(REPO),
              "max_depth": 8, "large_diff_files": 40, "output_dir": ""}
    params.update(kw)
    return RegressionImpactAnalyzer(**params)


def analyse(diff_text, **kw):
    return analyzer(pasted_diff=diff_text, **kw).build_findings().data


def diff_for(path, body="-old line\n+new line"):
    return (f"diff --git a/{path} b/{path}\n"
            f"index 1111111..2222222 100644\n--- a/{path}\n+++ b/{path}\n"
            f"@@ -1,3 +1,3 @@\n{body}\n")


def selected_tests(result):
    return {r["test"] for r in result["selected"]}


def writer(**kw):
    params = {"advice": "Run the checkout spec first.", "output_dir": "",
              "report_name": "regression_plan.md"}
    params.update(kw)
    return RegressionPlanWriter(**params)


def temp_repo(files):
    root = Path(tempfile.mkdtemp())
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return root


# ---------------------------------------------------------------- the graph

print("\nA changed file reaches the tests that import it")
r = analyse(diff_for("src/utils/money.ts"))
check("a direct importer is selected", "tests/checkout.spec.ts" in selected_tests(r),
      str(selected_tests(r)))
check("it is must-run, not should-run",
      next(x["tier"] for x in r["selected"] if x["test"] == "tests/checkout.spec.ts") == "must_run")
check("unrelated tests are not selected", "tests/search.spec.ts" not in selected_tests(r))
check("the trail back to the diff is recorded",
      r["selected"][0]["because"][0]["changed"] == "src/utils/money.ts")

print("\nTransitive reach through a page object")
r = analyse(diff_for("src/utils/api.ts"))
check("all three specs are reached", selected_tests(r) ==
      {"tests/checkout.spec.ts", "tests/login.spec.ts", "tests/search.spec.ts"},
      str(selected_tests(r)))
check("two hops away is should-run",
      all(x["tier"] == "should_run" for x in r["selected"]), str(r["selected"]))

print("\nA tsconfig path alias is followed")
# login.spec.ts reaches LoginPage ONLY through '@pages/LoginPage'. If aliases
# were not resolved this test would silently drop out of every subset.
r = analyse(diff_for("src/pages/LoginPage.ts"))
check("the alias-only importer is still selected",
      "tests/login.spec.ts" in selected_tests(r), str(selected_tests(r)))

print("\nJava imports")
r = analyse(diff_for("src/main/java/com/shopfront/pages/LoginPage.java"))
check("the importing test is selected",
      "src/test/java/com/shopfront/tests/LoginTest.java" in selected_tests(r))
check("a test in the same package that does NOT use the class is left out",
      "src/test/java/com/shopfront/tests/SmokeTest.java" not in selected_tests(r),
      str(selected_tests(r)))
r = analyse(diff_for("src/main/java/com/shopfront/utils/DriverFactory.java"))
check("a shared java helper reaches both tests", len(selected_tests(r)) == 2, str(selected_tests(r)))

print("\nA changed test file selects itself")
r = analyse(diff_for("tests/search.spec.ts"))
check("the test itself is must-run", selected_tests(r) == {"tests/search.spec.ts"},
      str(selected_tests(r)))

print("\nResolution forms that must not drop an edge")
repo = temp_repo({
    "tsconfig.json": '{"compilerOptions":{"baseUrl":".","paths":{"@lib/*":["src/lib/*"]}}}',
    "src/lib/index.ts": "export * from './core';\n",
    "src/lib/core.ts": "export const value = 1;\n",
    "src/lib/viaJs.ts": "export const other = 2;\n",
    "tests/a.spec.ts": "import { value } from '../src/lib';\n",
    "tests/b.spec.ts": "import { other } from '../src/lib/viaJs.js';\n",
    "tests/c.spec.ts": "const { value } = require('../src/lib/core');\n",
})
r = analyse(diff_for("src/lib/core.ts"), repo_path=str(repo))
check("a barrel re-export is followed", "tests/a.spec.ts" in selected_tests(r), str(selected_tests(r)))
check("require() is followed", "tests/c.spec.ts" in selected_tests(r), str(selected_tests(r)))
r = analyse(diff_for("src/lib/viaJs.ts"), repo_path=str(repo))
check("a .js specifier resolves to the .ts file",
      "tests/b.spec.ts" in selected_tests(r), str(selected_tests(r)))

print("\nA relative repository path behaves like an absolute one")
# This is the regression test for the bug that made this agent useless while
# looking fine: the file index held unresolved paths and import targets held
# resolved ones, so every reverse lookup quietly returned nothing and the
# recommendation was "no tests impacted". It only appears with a relative path.
_cwd = os.getcwd()
try:
    os.chdir(HERE)
    rel = analyse(diff_for("src/utils/money.ts"), repo_path="sample_repo")
finally:
    os.chdir(_cwd)
check("a relative repo path still finds the impacted test",
      selected_tests(rel) == {"tests/checkout.spec.ts"}, str(selected_tests(rel)))
check("and reports the same count as the absolute path",
      rel["tests_total"] == analyse(diff_for("src/utils/money.ts"))["tests_total"])

print("\nA package import is not mistaken for a repo file")
repo2 = temp_repo({
    "src/a.ts": "import { test } from '@playwright/test';\nexport const a = 1;\n",
    "tests/a.spec.ts": "import { a } from '../src/a';\n",
})
r = analyse(diff_for("src/a.ts"), repo_path=str(repo2))
check("the repo edge still resolves", "tests/a.spec.ts" in selected_tests(r))

# ------------------------------------------------------------- escalations

print("\nChanges that force the whole suite")
ESCALATE = [
    ("package-lock.json", "lockfile"),
    ("pnpm-lock.yaml", "lockfile"),
    ("yarn.lock", "lockfile"),
    ("package.json", "dependency_manifest"),
    ("pom.xml", "dependency_manifest"),
    ("tsconfig.json", "resolution_config"),
    ("playwright.config.ts", "test_runner_config"),
    ("testng.xml", "test_runner_config"),
    ("jest.config.js", "test_runner_config"),
    ("global-setup.ts", "global_setup"),
    (".github/workflows/e2e.yml", "ci_config"),
    ("Jenkinsfile", "ci_config"),
    ("src/test/resources/config.properties", "runtime_resource"),
    (".env", "runtime_resource"),
    ("features/checkout.feature", "runtime_resource"),
    ("db/migrations/003_add_column.sql", "runtime_resource"),
    ("tests/fixtures/users.json", "test_fixture_data"),
    ("src/__snapshots__/a.snap", "test_fixture_data"),
]
for path, rule in ESCALATE:
    r = analyse(diff_for(path))
    rules = {e["rule"] for e in r["escalations"]}
    check(f"{path} escalates ({rule})", r["full_suite"] and rule in rules,
          f"full={r['full_suite']} rules={rules}")
    if r["full_suite"]:
        check(f"  and selects the entire suite: {path}",
              r["tests_selected"] == r["tests_total"])

print("\nA wide diff is not narrowed")
wide = "".join(diff_for(f"src/pages/p{i}.ts") for i in range(45))
r = analyse(wide)
check("a diff over the threshold escalates", r["full_suite"])
check("and says why", any(e["rule"] == "large_diff" for e in r["escalations"]))

print("\nAn unreadable diff escalates rather than producing a partial answer")
r = analyse("diff --git a/logo.png b/logo.png\nindex 1..2 100644\nGIT binary patch\nliteral 120\n")
check("a binary patch escalates", r["full_suite"], str(r["escalations"]))
r = analyse("diff --git a/sub b/sub\nindex 1..2 160000\n-Subproject commit aaaa\n+Subproject commit bbbb\n")
check("a submodule pointer escalates", r["full_suite"])
r = analyse("diff --cc src/a.ts\nindex 1,2..3\n@@@ -1,1 -1,1 +1,1 @@@\n- a\n+ b\n")
check("a merge diff escalates", r["full_suite"], str(r["escalations"]))

print("\nA changed file that is not in the repository escalates")
r = analyse(diff_for("src/generated/client.ts"))
check("an unknown path escalates rather than contributing nothing", r["full_suite"],
      str(r["escalations"]))
check("and names the file",
      any(e["rule"] == "file_not_in_repo" for e in r["escalations"]))

print("\nA deleted file is not treated as missing")
deleted = ("diff --git a/src/pages/Gone.ts b/src/pages/Gone.ts\n"
           "deleted file mode 100644\nindex 1111111..0000000\n"
           "--- a/src/pages/Gone.ts\n+++ /dev/null\n@@ -1,2 +0,0 @@\n-export const x = 1;\n")
r = analyse(deleted)
check("a deletion does not escalate as a missing file",
      not any(e["rule"] == "file_not_in_repo" for e in r["escalations"]), str(r["escalations"]))

# --------------------------------------------------------- nothing to run

print("\nChanges that select nothing")
r = analyse(diff_for("src/utils/money.ts", "+// a comment about pennies\n+"))
check("a comment-only change is ignored", r["tests_selected"] == 0, str(r["selected"]))
check("and says so", r["skipped_changes"][0]["reason"].startswith("only comments"))
check("it does not escalate", not r["full_suite"])
# Built rather than written literally: a fixture whose meaning lives in trailing
# spaces stops meaning it the moment something trims the line.
r = analyse(diff_for("src/utils/money.ts", "-" + " " * 2 + "\n+" + " " * 4))
check("a whitespace-only change is ignored", r["tests_selected"] == 0, str(r["skipped_changes"]))
r = analyse(diff_for("src/utils/money.ts", "-const a = 1;\n+// now a comment\n+const a = 2;"))
check("a mixed change is NOT ignored", r["tests_selected"] > 0)

# ------------------------------------------------------------- the diff

print("\nReading the diff")
check("added files are recognised",
      analyse("diff --git a/src/new.ts b/src/new.ts\nnew file mode 100644\n"
              "--- /dev/null\n+++ b/src/new.ts\n@@ -0,0 +1 @@\n+export const a = 1;\n"
              )["changed_files"][0]["change"] == "added")
check("renames are recognised",
      analyse("diff --git a/src/old.ts b/src/newer.ts\nsimilarity index 95%\n"
              "--- a/src/old.ts\n+++ b/src/newer.ts\n@@ -1 +1 @@\n-a\n+b\n"
              )["changed_files"][0]["change"] == "renamed")
check("the line count is read", analyse(diff_for("src/utils/money.ts"))["changed_files"][0]["lines_changed"] == 2)
check("multiple files are read", analyse(diff_for("src/utils/money.ts") + diff_for("src/utils/api.ts"))["files_changed"] == 2)

# ----------------------------------------------------------------- guards

print("\nGuards")
raises("no diff is refused", lambda: analyzer().build_findings(), "no diff reached")
raises("a greeting instead of a diff is refused",
       lambda: analyzer(diff="hello there").build_findings(), "no diff reached")
raises("no repository path is refused",
       lambda: analyzer(pasted_diff=diff_for("a.ts"), repo_path="").build_findings(),
       "no readable repository path")
raises("a repository with no source is refused",
       lambda: analyzer(pasted_diff=diff_for("a.ts"),
                        repo_path=str(temp_repo({"readme.md": "hi"}))).build_findings(),
       "no typescript or java source")
raises("prose instead of a diff is refused",
       lambda: analyse("not a diff at all, just prose\nwith two lines"),
       "no changed files were found")

print("\nBlind spots are always reported")
for source in (diff_for("src/utils/money.ts"), diff_for("package-lock.json")):
    r = analyse(source)
    check("every run carries its blind spots", len(r["blind_spots"]) >= 5)
check("the selector blind spot names the sibling agent",
      any("agent 12" in s for s in analyse(diff_for("src/utils/money.ts"))["blind_spots"]))

print("\nA runnable command is produced")
r = analyse(diff_for("src/utils/money.ts"))
check("a playwright command is emitted",
      r["commands"][0]["command"].startswith("npx playwright test"), str(r["commands"]))
check("it names the selected spec", "tests/checkout.spec.ts" in r["commands"][0]["command"])
r = analyse(diff_for("src/main/java/com/shopfront/pages/LoginPage.java"))
check("a maven command names the class", "-Dtest=LoginTest" in r["commands"][0]["command"],
      str(r["commands"]))

print("\nPersistence")
out = Path(tempfile.mkdtemp())
analyzer(pasted_diff=diff_for("src/utils/money.ts"), output_dir=str(out)).build_brief()
check("the brief writes impacted_tests.json", (out / "impacted_tests.json").is_file())
check("the findings have a selected set",
      "selected" in json.loads((out / "impacted_tests.json").read_text(encoding="utf-8")))

# ------------------------------------------------------------ plan writer

print("\nPlan writer guards")
raises("no reports folder is refused", lambda: writer().write_report(), "set a reports folder")
raises("a missing findings file is named",
       lambda: writer(output_dir=tempfile.mkdtemp()).write_report(), "impacted_tests.json")
bad = Path(tempfile.mkdtemp())
(bad / "impacted_tests.json").write_text("{nope", encoding="utf-8")
raises("a corrupt findings file is refused",
       lambda: writer(output_dir=str(bad)).write_report(), "not valid json")
wrong = Path(tempfile.mkdtemp())
(wrong / "impacted_tests.json").write_text('{"counts": {}}', encoding="utf-8")
raises("a findings file with no selected set is refused",
       lambda: writer(output_dir=str(wrong)).write_report(), "no selected tests")
good = Path(tempfile.mkdtemp())
(good / "impacted_tests.json").write_text(
    json.dumps(analyse(diff_for("src/utils/money.ts"))), encoding="utf-8")
raises("empty advice is refused",
       lambda: writer(output_dir=str(good), advice="  ").write_report(), "no advice")

print("\nPlan writer output")
summary = writer(output_dir=str(good), advice="```markdown\nRun checkout first.\n```").write_report()
plan = (good / "regression_plan.md").read_text(encoding="utf-8")
check("a fenced reply is unwrapped", "Run checkout first." in plan and "```markdown" not in plan)
check("the advice is labelled as model-written", "written by a language model" in plan)
check("the plan opens with the at-a-glance table", "## At a glance" in plan)
check("the plan lists what changed", "## What changed" in plan)
check("the plan lists the tests with their trail", "Reached from" in plan)
check("the plan ends with the blind spots", "## What this analysis cannot see" in plan)
check("the plan carries a runnable command", "npx playwright test" in plan)
check("the summary states the saving", "skipping 80% of the suite" in summary.text, summary.text)

full = Path(tempfile.mkdtemp())
(full / "impacted_tests.json").write_text(
    json.dumps(analyse(diff_for("package-lock.json"))), encoding="utf-8")
writer(output_dir=str(full), advice="Everything.").write_report()
full_plan = (full / "regression_plan.md").read_text(encoding="utf-8")
check("an escalated run says run the whole suite", "Run the whole suite" in full_plan)
check("and explains which rule fired", "## Why the whole suite" in full_plan)
check("the escalated summary says so",
      "whole suite" in writer(output_dir=str(full), advice="x").write_report().text)

empty = Path(tempfile.mkdtemp())
(empty / "impacted_tests.json").write_text(
    json.dumps(analyse(diff_for("src/utils/money.ts", "+// just a note"))), encoding="utf-8")
writer(output_dir=str(empty), advice="Nothing to do.").write_report()
check("a plan selecting nothing warns rather than reassures",
      "before taking that as permission" in (empty / "regression_plan.md").read_text(encoding="utf-8"))

check("the details output reports where it wrote",
      writer(output_dir=str(good), advice="x").write_details().data["report"].endswith("regression_plan.md"))

# ------------------------------------------------------------- the samples

print("\nThe sample diffs in this folder")
EXPECTED = {
    "01_change_money_util.diff": (False, {"tests/checkout.spec.ts"}),
    "02_change_shared_api.diff": (False, {"tests/checkout.spec.ts", "tests/login.spec.ts",
                                          "tests/search.spec.ts"}),
    "03_bump_lockfile.diff": (True, None),
    "04_change_config_properties.diff": (True, None),
    "05_comment_only.diff": (False, set()),
    "06_change_java_page.diff": (False, {"src/test/java/com/shopfront/tests/LoginTest.java"}),
}
for name, (expect_full, expect_tests) in EXPECTED.items():
    path = DIFFS / name
    if not path.is_file():
        check(f"{name} exists", False, str(path))
        continue
    r = analyzer(diff=str(path)).build_findings().data
    check(f"{name}: {'full suite' if expect_full else 'subset'}", r["full_suite"] == expect_full,
          f"full_suite={r['full_suite']}")
    if expect_tests is not None:
        check(f"{name}: selects the right tests", selected_tests(r) == expect_tests,
              str(selected_tests(r)))

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
