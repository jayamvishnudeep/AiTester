"""Tests for the Page Object Writer component.

The component exists because model replies are unreliable, so what is worth
testing is every shape a reply arrives in, how the file gets its name, and the
replies that must be refused.

Run it with the Langflow virtual environment:

    09_LangFlow/.venv/Scripts/python.exe test_page_object_writer.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from page_object_writer import PageObjectWriter  # noqa: E402

HTML = ('<main data-testid="login-page"><form><label for="email">Email</label>'
        '<input id="email" /><button type="submit">Sign in</button></form></main>')

CODE = """import { type Page, type Locator } from '@playwright/test';

export class LoginPage {
  readonly page: Page;
  readonly email: Locator;
  readonly signIn: Locator;

  constructor(page: Page) {
    this.page = page;
    this.email = page.getByLabel('Email');
    this.signIn = page.getByRole('button', { name: 'Sign in' });
  }

  async goto() {
    await this.page.goto('/login');
  }

  async signInAs(email: string) {
    await this.email.fill(email);
    await this.signIn.click();
  }
}"""

CHECKOUT = CODE.replace("LoginPage", "CheckoutPage").replace("/login", "/checkout")

passed = failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}" + (f"  -- {detail}" if detail else ""))


def run(reply, html=HTML, default="PageObject.ts", overwrite=True, existing=None):
    folder = Path(tempfile.mkdtemp())
    for pre in existing or []:
        (folder / pre).write_text("// already here\n", encoding="utf-8")
    writer = PageObjectWriter(
        generated=reply, source_html=html, output_dir=str(folder),
        default_name=default, overwrite=overwrite,
    )
    data = writer.write_details().data
    names = [w["file"] for w in data["written"]]
    texts = {w["file"]: Path(w["path"]).read_text(encoding="utf-8") for w in data["written"]}
    return names, texts, data


def raises(reply, html=HTML):
    try:
        run(reply, html=html)
    except ValueError as exc:
        return str(exc)
    return None


print("\nnaming")
names, _, data = run(CODE)
check("file is named after the class", names == ["LoginPage.ts"], str(names))
check("class is reported", data["written"][0]["class"] == "LoginPage")

names, _, _ = run(f"// file: WrongName.ts\n{CODE}")
check("the class beats a disagreeing marker", names == ["LoginPage.ts"], str(names))

names, _, _ = run("export const helpers = { a: 1 };")
check("no class falls back to the default name", names == ["PageObject.ts"], str(names))

names, _, _ = run("// file: Helpers.ts\nexport const helpers = { a: 1 };")
check("no class uses the marker when there is one", names == ["Helpers.ts"], str(names))

names, _, _ = run(CODE.replace("export class LoginPage", "export default class LoginPage"))
check("'export default class' is recognised", names == ["LoginPage.ts"], str(names))

print("\nreply shapes")
names, texts, _ = run(f"```typescript\n{CODE}\n```")
check("single fenced block", names == ["LoginPage.ts"] and "```" not in texts["LoginPage.ts"])

names, texts, _ = run(f"Here is the Page Object:\n\n```ts\n{CODE}\n```")
check("leading commentary is dropped", texts["LoginPage.ts"].startswith("import "))

names, texts, _ = run(f"```ts\n{CODE}\n```\n\nAdd this to your pages folder.")
check("trailing commentary is dropped",
      "Add this to your pages folder" not in texts["LoginPage.ts"],
      repr(texts["LoginPage.ts"][-60:]))

names, texts, _ = run(f"```ts\n{CODE}\n```\n\n```ts\n{CHECKOUT}\n```")
check("two blocks become two classes",
      sorted(names) == ["CheckoutPage.ts", "LoginPage.ts"], str(names))
check("no stray fence survives", all("```" not in t for t in texts.values()))

names, _, _ = run(f"// file: a.ts\n{CODE}\n\n// file: b.ts\n{CHECKOUT}")
check("markers with classes are named by class",
      sorted(names) == ["CheckoutPage.ts", "LoginPage.ts"], str(names))

names, texts, _ = run(f"/* file: LoginPage.ts */\n{CODE}")
check("block-comment marker leaves no '*/'", "*/" not in texts["LoginPage.ts"].split("\n")[0],
      repr(texts["LoginPage.ts"][:40]))

names, _, _ = run(f"// file: ../../etc/passwd\nexport const x = 1;")
check("a path in a marker cannot escape the folder", names == ["passwd.ts"], str(names))

print("\nwhat it counts")
_, _, data = run(CODE)
w = data["written"][0]
check("methods are listed", w["methods"] == ["goto", "signInAs"], str(w["methods"]))
check("locators are counted", w["locators"] >= 3, str(w["locators"]))

print("\nnumbered copies when overwrite is off")
names, _, _ = run(CODE, overwrite=False, existing=["LoginPage.ts"])
check("second copy is numbered", names == ["LoginPage-2.ts"], str(names))

print("\nreplies that must be refused")
check("empty reply", raises("") is not None)
check("prose with no code", "No code was found" in (raises("I cannot do that.") or ""))
check("a marker with nothing after it",
      "No code was found" in (raises("// file: LoginPage.ts\n\n") or ""))

print("\nthe HTML guard")
check("no HTML at all", "No HTML reached" in (raises(CODE, html="") or ""))
check("HTML too short", "does not look like" in (raises(CODE, html="<b>hi</b>") or ""))
check("text with no tags", "does not look like"
      in (raises(CODE, html="please generate a login page object for me") or ""))
check("real HTML is accepted", raises(CODE, html=HTML) is None)

print()
print("=" * 58)
print(f"{passed} passed, {failed} failed")
print("=" * 58)
sys.exit(1 if failed else 0)
