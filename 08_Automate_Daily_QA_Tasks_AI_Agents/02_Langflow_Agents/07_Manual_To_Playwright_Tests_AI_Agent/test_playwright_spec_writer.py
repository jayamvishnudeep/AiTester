"""Tests for the Playwright Spec Writer component.

The component exists because model replies are unreliable, so the thing worth
testing is every shape a reply actually arrives in: bare code, fenced, fenced
with commentary on either side, several blocks at once, file markers in both
comment styles, and the replies that should be refused outright.

Run it with the Langflow virtual environment:

    09_LangFlow/.venv/Scripts/python.exe test_playwright_spec_writer.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from playwright_spec_writer import PlaywrightSpecWriter  # noqa: E402

STEPS = ("TC-01 - Sign in with valid credentials. 1. Open the login page. "
         "2. Enter the email. Expected: the dashboard is shown.")

CODE = """import { test, expect } from '@playwright/test';

test('sign in with valid credentials', async ({ page }) => {
  await page.goto('/login');
  await expect(page.getByTestId('account-menu')).toBeVisible();
});"""

CART = CODE.replace("sign in with valid credentials", "add a single item to the cart")
SEARCH = CODE.replace("sign in with valid credentials", "search for a product")

passed = failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}" + (f"  -- {detail}" if detail else ""))


def run(reply, steps=STEPS, default="generated.spec.ts", overwrite=True, existing=None):
    """Write a reply into a fresh folder; return (names, {name: text})."""
    folder = Path(tempfile.mkdtemp())
    for pre in existing or []:
        (folder / pre).write_text("// already here\n", encoding="utf-8")
    writer = PlaywrightSpecWriter(
        generated=reply, source_steps=steps, output_dir=str(folder),
        default_name=default, overwrite=overwrite,
    )
    data = writer.write_details().data
    names = [w["file"] for w in data["written"]]
    texts = {w["file"]: Path(w["path"]).read_text(encoding="utf-8") for w in data["written"]}
    return names, texts, data


def raises(reply, steps=STEPS):
    try:
        run(reply, steps=steps)
    except ValueError as exc:
        return str(exc)
    return None


print("\nreply shapes")
names, texts, _ = run(CODE)
check("bare code", names == ["generated.spec.ts"] and "@playwright/test" in texts[names[0]])

names, texts, _ = run(f"```typescript\n{CODE}\n```")
check("single fenced block", names == ["generated.spec.ts"]
      and "```" not in texts[names[0]])

names, texts, _ = run(f"Here you go:\n\n```ts\n{CODE}\n```\n")
check("leading commentary is dropped", texts[names[0]].startswith("import {"))

names, texts, _ = run(f"```ts\n{CODE}\n```\n\nThese tests assume a configured base URL.")
check("trailing commentary is dropped",
      "These tests assume" not in texts[names[0]], repr(texts[names[0]][-60:]))

print("\nseveral blocks in one reply")
names, texts, _ = run(f"```ts\n{CODE}\n```\n\n```ts\n{CART}\n```\n\n```ts\n{SEARCH}\n```")
check("three fenced blocks become three files", len(names) == 3, str(names))
check("each block keeps its own test",
      any("sign in" in t for t in texts.values())
      and any("add a single item" in t for t in texts.values())
      and any("search for a product" in t for t in texts.values()))

names, texts, _ = run(f"```ts\n{CODE}\n```\n\n```ts\n{CART}\n```")
check("two fenced blocks become two files", len(names) == 2, str(names))
check("no stray fence survives", all("```" not in t for t in texts.values()))

print("\nfile markers")
names, texts, _ = run(f"// file: login.spec.ts\n{CODE}\n\n// file: cart.spec.ts\n{CART}")
check("two markers name two files", names == ["login.spec.ts", "cart.spec.ts"], str(names))

names, texts, _ = run(f"```ts\n// file: auth.spec.ts\n{CODE}\n```")
check("marker inside a fence", names == ["auth.spec.ts"], str(names))

names, texts, _ = run(f"```ts\n// file: login.spec.ts\n{CODE}\n```\n\n"
                      "These tests assume the base URL is configured.")
check("marker branch drops the closing paragraph",
      "These tests assume" not in texts["login.spec.ts"],
      repr(texts["login.spec.ts"][-70:]))

names, texts, _ = run(f"/* file: login.spec.ts */\n{CODE}")
check("block-comment marker leaves no '*/' in the code",
      "*/" not in texts["login.spec.ts"], repr(texts["login.spec.ts"][:60]))

names, texts, _ = run(f"// file: login.spec.ts (3 tests)\n{CODE}")
check("trailing text on the marker line is not written",
      "(3 tests)" not in texts[names[0]], str(names))

names, _, _ = run(f"// file: ../../etc/passwd\n{CODE}")
check("a path in a marker cannot escape the folder", names == ["passwd.spec.ts"], str(names))

names, _, _ = run(f"// file: login\n{CODE}")
check("a marker without an extension gets one", names == ["login.spec.ts"], str(names))

print("\nnumbered copies when overwrite is off")
names, _, _ = run(f"// file: login.spec.ts\n{CODE}", overwrite=False,
                  existing=["login.spec.ts"])
check("second .spec.ts is numbered", names == ["login-2.spec.ts"], str(names))

names, _, _ = run(f"// file: login.ts\n{CODE}", overwrite=False, existing=["login.ts"])
check("a plain .ts name keeps its own suffix", names == ["login-2.ts"], str(names))

print("\ncounting")
_, _, data = run(f"// file: login.spec.ts\n{CODE}")
check("one test counted", data["test_count"] == 1, str(data["test_count"]))

wrapped = ("import { test, expect } from '@playwright/test';\n\n"
           "test.describe('Login', () => {\n"
           "  test('a', async ({ page }) => { await page.goto('/'); });\n"
           "  test('b', async ({ page }) => { await page.goto('/'); });\n"
           "});")
_, _, data = run(f"// file: login.spec.ts\n{wrapped}")
check("test.describe is not counted as a test", data["test_count"] == 2, str(data["test_count"]))

print("\nreplies that must be refused")
check("empty reply", raises("") is not None)
check("prose with no code", "No code was found" in (raises("I could not do that, sorry.") or ""))
check("a marker with nothing after it",
      "No code was found" in (raises("// file: login.spec.ts\n\n") or ""))

print("\nthe empty-steps guard")
check("no steps at all", "No manual steps" in (raises(CODE, steps="") or ""))
check("too few steps", "too" in (raises(CODE, steps="login") or "").lower())
check("real steps are accepted", raises(CODE, steps=STEPS) is None)

print()
print("=" * 58)
print(f"{passed} passed, {failed} failed")
print("=" * 58)
sys.exit(1 if failed else 0)
