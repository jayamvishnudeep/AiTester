"""Tests for the Framework Scanner and the Audit Report Writer.

An auditor is only worth running if its findings are trusted, and the fastest way
to lose that trust is a rule that fires on reasonable code. So every rule here is
tested twice: once on a line it must catch, and once on a line an experienced
engineer would actually write, which it must leave alone.

Run it with the Langflow virtual environment:

    09_LangFlow/.venv/Scripts/python.exe test_framework_auditor.py
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from audit_report_writer import AuditReportWriter  # noqa: E402
from framework_scanner import FrameworkScanner  # noqa: E402

passed = failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}" + (f"  -- {detail}" if detail else ""))


def scan(files, **kw):
    """Write files into a temp repo and scan it. files = {relative path: text}."""
    root = Path(tempfile.mkdtemp())
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    s = FrameworkScanner(repo_path=str(root), fallback_path="",
                         max_snippets=kw.get("max_snippets", 12),
                         max_file_kb=kw.get("max_file_kb", 512))
    return s.build_findings().data, root


def rules_hit(audit):
    return {r["rule"] for r in audit["rules_triggered"]}


# (rule id, file path, line that MUST be caught, line that must NOT be)
CASES = [
    ("hard_sleep_java", "src/test/java/T.java",
     "        Thread.sleep(3000);",
     "        wait.until(ExpectedConditions.visibilityOf(banner));"),
    ("hard_sleep_ts", "tests/a.spec.ts",
     "  await page.waitForTimeout(3000);",
     "  await expect(page.getByRole('alert')).toBeVisible();"),
    ("implicit_wait", "src/test/java/T.java",
     "        driver.manage().timeouts().implicitlyWait(30, SECONDS);",
     "        WebDriverWait wait = new WebDriverWait(driver, Duration.ofSeconds(10));"),
    ("absolute_xpath", "src/test/java/T.java",
     '        driver.findElement(By.xpath("/html/body/div[1]/form/button")).click();',
     '        driver.findElement(By.xpath("//button[@data-testid=\'submit\']")).click();'),
    ("indexed_xpath", "src/test/java/T.java",
     '        driver.findElement(By.xpath("//ul/li[3]/a")).click();',
     '        driver.findElement(By.xpath("//li[@data-id=\'3\']/a")).click();'),
    ("styling_css_selector", "tests/a.spec.ts",
     "  await page.click('button.btn--primary');",
     "  await page.getByRole('button', { name: 'Sign in' }).click();"),
    ("nth_child_selector", "tests/a.spec.ts",
     "  await page.click('ul > li:nth-child(2)');",
     "  await page.getByRole('listitem').nth(1).click();"),
    ("driver_in_test", "src/test/java/T.java",
     '        driver.findElement(By.id("email")).sendKeys(user);',
     "        loginPage.enterEmail(user);"),
    ("raw_page_call_in_test", "tests/a.spec.ts",
     "  await page.fill('#email', user);",
     "  await loginPage.enterEmail(user);"),
    ("assertion_in_page_object", "src/main/java/pages/P.java",
     '        Assert.assertTrue(driver.getCurrentUrl().contains("dashboard"));',
     "        return driver.getCurrentUrl();"),
    ("static_mutable_driver", "src/main/java/utils/D.java",
     "    public static WebDriver driver;",
     "    public static WebDriver getDriver() {"),
    ("disabled_test_java", "src/test/java/T.java",
     "    @Ignore",
     "    @Test(groups = \"smoke\")"),
    ("disabled_test_ts", "tests/a.spec.ts",
     "test.skip('not ready', async ({ page }) => {",
     "test('signs in', async ({ page }) => {"),
    ("console_output_java", "src/test/java/T.java",
     '        System.out.println("current url " + url);',
     "        log.info(\"current url {}\", url);"),
    ("console_output_ts", "tests/a.spec.ts",
     "  console.log('url is ' + page.url());",
     "  test.info().annotations.push({ type: 'url', description: page.url() });"),
    ("empty_catch", "src/main/java/utils/D.java",
     "        try { driver.quit(); } catch (Exception e) {}",
     "        try { driver.quit(); } catch (Exception e) { log.warn(\"quit failed\", e); }"),
    ("hardcoded_credential", "src/test/java/T.java",
     '    private static final String PASSWORD = "Passw0rd123";',
     '    private static final String PASSWORD = System.getenv("SHOPFRONT_PASSWORD");'),
    ("hardcoded_environment_url", "tests/a.spec.ts",
     "  await page.goto('https://shopfront.example.com/login');",
     "  await page.goto('/login');"),
]

print("\nevery rule catches what it should")
for rule_id, path, bad, _good in CASES:
    audit, _ = scan({path: f"class X {{\n{bad}\n}}\n"})
    check(f"{rule_id} catches the bad line", rule_id in rules_hit(audit),
          "hit: " + ", ".join(sorted(rules_hit(audit))) or "nothing")

print("\nand leaves reasonable code alone")
for rule_id, path, _bad, good in CASES:
    audit, _ = scan({path: f"class X {{\n{good}\n}}\n"})
    check(f"{rule_id} ignores the good line", rule_id not in rules_hit(audit),
          "wrongly hit; all: " + ", ".join(sorted(rules_hit(audit))))

print("\ncomments are not counted as code")
audit, _ = scan({"src/test/java/T.java":
                 "class X {\n    // Thread.sleep(3000);\n    /* System.out.println(\"x\"); */\n}\n"})
check("a commented-out anti-pattern is skipped", not rules_hit(audit),
      ", ".join(sorted(rules_hit(audit))))

print("\nlayer awareness")
audit, _ = scan({"src/main/java/pages/LoginPage.java":
                 'class P {\n    void f() { driver.findElement(By.id("a")).click(); }\n}\n'})
check("findElement in a page object is not a test-layer finding",
      "driver_in_test" not in rules_hit(audit))
audit, _ = scan({"src/test/java/LoginTest.java":
                 'class T {\n    void f() { Assert.assertTrue(true); }\n}\n'})
check("an assertion in a test is not a page-object finding",
      "assertion_in_page_object" not in rules_hit(audit))

print("\ndependencies")
POM = """<project><dependencies>
<dependency><groupId>org.seleniumhq.selenium</groupId><artifactId>selenium-java</artifactId><version>3.141.59</version></dependency>
<dependency><groupId>org.testng</groupId><artifactId>testng</artifactId><version>7.9.0</version></dependency>
</dependencies><properties><maven.compiler.target>8</maven.compiler.target></properties></project>"""
audit, _ = scan({"pom.xml": POM, "src/test/java/T.java": "class T {}\n"})
stale = {d["name"] for d in audit["dependencies_stale"]}
check("selenium 3 is flagged", "selenium-java" in stale, str(stale))
check("testng 7 is not flagged", "testng" not in stale, str(stale))
check("an old compiler target is flagged", "maven.compiler.target" in stale, str(stale))

PKG = json.dumps({"devDependencies": {"@playwright/test": "^1.28.0", "typescript": "^5.4.0",
                                      "ts-node": "*"}})
audit, _ = scan({"package.json": PKG, "tests/a.spec.ts": "const x = 1;\n"})
stale = {d["name"] for d in audit["dependencies_stale"]}
check("an old playwright minor is flagged", "@playwright/test" in stale, str(stale))
check("a current typescript is not flagged", "typescript" not in stale, str(stale))
check("an unpinned version is flagged", "ts-node" in stale, str(stale))

print("\nwhat the scanner skips")
audit, _ = scan({"node_modules/pkg/index.js": "await page.waitForTimeout(1);\n",
                 "target/classes/T.java": "Thread.sleep(1);\n",
                 "tests/a.spec.ts": "const x = 1;\n"})
check("node_modules and target are not scanned", audit["files_scanned"] == 1,
      str(audit["files_scanned"]))

print("\nthe scanner's guards")
try:
    FrameworkScanner(repo_path="", fallback_path="", max_snippets=5,
                     max_file_kb=512).build_findings()
    check("no path raises", False, "it did not raise")
except ValueError as e:
    check("no path raises", "No readable repository path" in str(e), str(e))

empty = Path(tempfile.mkdtemp())
(empty / "notes.txt").write_text("nothing to see", encoding="utf-8")
try:
    FrameworkScanner(repo_path=str(empty), fallback_path="", max_snippets=5,
                     max_file_kb=512).build_findings()
    check("a folder with no source raises", False, "it did not raise")
except ValueError as e:
    check("a folder with no source raises", "No Java or TypeScript" in str(e), str(e))

print("\nthe report writer")
audit, _ = scan({"src/test/java/T.java":
                 'class T {\n    void f() throws Exception { Thread.sleep(1000); }\n}\n'})
out = Path(tempfile.mkdtemp())


def seed(folder, payload):
    """The scanner leaves audit_findings.json here; the writer reads it back."""
    (folder / "audit_findings.json").write_text(json.dumps(payload), encoding="utf-8")


seed(out, audit)
res = AuditReportWriter(recommendations="Fix the sleeps first.", output_dir=str(out),
                        report_name="audit_report.md").write_details().data
report = Path(res["report"]).read_text(encoding="utf-8")
check("the report is written", Path(res["report"]).is_file())
check("counts in the report come from the scan", "**1**" in report,
      "findings total not rendered")
check("the model's section is labelled as such",
      "written by a language model" in report)
check("the recommendations are included", "Fix the sleeps first." in report)
check("the appendix lists the occurrence", "Thread.sleep(1000)" in report)

r2 = Path(AuditReportWriter(recommendations="```markdown\nFenced advice.\n```",
                            output_dir=str(out), report_name="fenced.md")
          .write_details().data["report"]).read_text(encoding="utf-8")
check("a fenced reply is unwrapped", "Fenced advice." in r2 and "```markdown" not in r2)

try:
    AuditReportWriter(recommendations="", output_dir=str(out),
                      report_name="x.md").write_details()
    check("empty recommendations raise", False, "it did not raise")
except ValueError as e:
    check("empty recommendations raise", "no recommendations" in str(e).lower(), str(e))

bare = Path(tempfile.mkdtemp())
try:
    AuditReportWriter(recommendations="something", output_dir=str(bare),
                      report_name="x.md").write_details()
    check("a missing scan raises", False, "it did not raise")
except ValueError as e:
    check("a missing scan raises", "audit_findings.json" in str(e), str(e))

seed(bare, {"not": "a scan"})
try:
    AuditReportWriter(recommendations="something", output_dir=str(bare),
                      report_name="x.md").write_details()
    check("a json that is not a scan raises", False, "it did not raise")
except ValueError as e:
    check("a json that is not a scan raises", "no findings" in str(e), str(e))

print("\nthe scanner writes what the writer reads")
src_root = Path(tempfile.mkdtemp())
(src_root / "src").mkdir()
(src_root / "src" / "T.java").write_text(
    "class T { void f() { Thread.sleep(1); } }\n", encoding="utf-8")
reports = Path(tempfile.mkdtemp())
FrameworkScanner(repo_path=str(src_root), fallback_path="", output_dir=str(reports),
                 max_snippets=5, max_file_kb=512).build_brief()
check("the scanner leaves audit_findings.json", (reports / "audit_findings.json").is_file())
handed = AuditReportWriter(recommendations="Advice.", output_dir=str(reports),
                           report_name="audit_report.md").write_details().data
check("the writer reads it back", Path(handed["report"]).is_file())

print()
print("=" * 58)
print(f"{passed} passed, {failed} failed")
print("=" * 58)
sys.exit(1 if failed else 0)
