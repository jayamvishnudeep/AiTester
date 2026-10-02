# Prompt Engineering

Where a prompt technique gets taken all the way through to working code. The
folder is best read as one chain, in numbered order, plus a library of reusable
templates on the side.

## The chain

```
00_Task1.md                    the assignment
   -> 01_RICE_POT_Template.md      the blank structure
   -> 02_RICE_POT.example.md       the structure filled in for that assignment
   -> 04_Plan_Framework.md         the plan the prompt produced
   -> 03_Selenium_Salesforce_Framework/   the project that got built
```

**`00_Task1.md`** — one line: *write Selenium code for the Salesforce login page*.
Exactly the kind of under-specified request that produces a bad answer.

**`01_RICE_POT_Template.md`** — the blank template. Seven slots:

| | |
|---|---|
| **R**OLE | the expertise to assume |
| **I**nstructions | the purpose |
| **C**ONTEXT | background the model cannot infer |
| **E**XPECTED | what success looks like |
| **P**ARAMETERS | constraints |
| **O**UTPUT | required format |
| **T**ONE | how to say it |

**`02_RICE_POT.example.md`** — the same assignment, rewritten into all seven
slots: a QA automation tester with nine years of CRM experience, an
enterprise-grade Selenium/Java/Maven/TestNG framework, valid and invalid login
paths against a named URL. The contrast with `00_Task1.md` is the lesson.

**`04_Plan_Framework.md`** — the plan that came back, including the observation
that no Java project existed anywhere in the workspace, so everything had to be
built from scratch.

**`03_Selenium_Salesforce_Framework/`** — and it was. A real Maven project:

```
pom.xml                selenium-java + testng, compiler and surefire plugins
testng.xml             SalesforceLoginSuite -> ValidLoginTests, InvalidLoginTests
src/main/java/.../pages/LoginPage.java        Page Object, PageFactory @FindBy
src/test/java/.../tests/ValidLoginTest.java
src/test/java/.../tests/InvalidLoginTest.java
src/test/resources/config.properties
```

`LoginPage` is a proper Page Object — `@FindBy` locators for username, password,
login button, Remember Me and the error div, a `WebDriverWait` held on the class,
and behaviour exposed as methods (`enterUsername`, `toggleRememberMe`, `doLogin`)
rather than raw elements. `InvalidLoginTest` covers invalid password,
unregistered username, malformed username and empty username, each asserting the
error message appears, with `Assert.fail` carrying the exception rather than
swallowing it.

That is the payoff worth remembering: **a filled-in RICE-POT prompt produced a
structured framework, not a script.** The same request in one line would not have.

## The template library

`prompt_templates/` — around a thousand lines of reusable prompts, grouped by
job:

| File | Contents |
|---|---|
| `test_case_prompts.md` | test-case generation |
| `_bug_report_prompts.md` | bug reporting |
| `api_testing_prompts.md` | API test design |
| `API_Error_Handling_Tests.md` | error-path API tests |
| `code_review_prompts.md` | code review |
| `context_templates.md` | how to build context as `.md` files |

`context_templates.md` is the one to reread — supplying context as files is what
the whole repo ends up doing, from the QA template in
`03_LocalTestCaseGenerator` to the agent contracts in `07_` and `08_`.

## The worked test plan

`VWO test plan and test cases/VWO_Login_Test_Plan.md` applies
`01_LLM_Basics/ANTI-HALLUCINATION.rules.md` to a real login page. It opens with
**Verified Facts** — the URL, an email field, a password field, a Remember Me
control — every one traceable to supplied evidence, with nothing assumed about
behaviour that was never shown. That output shape comes straight from the rules
file, and it is what makes the plan auditable.

## Worth remembering

- **The gap between `00_Task1.md` and `02_RICE_POT.example.md` is the entire
  point of the folder.** Same task, same model; the difference is seven slots
  filled in.
- **CONTEXT and PARAMETERS carry the most weight.** ROLE flatters the model;
  the constraints and the background are what change the output.
- **Anything reused belongs in a file, not in a chat message.** That is the
  `context_templates.md` idea, and it is exactly what `07_.../01_Jira_n8n_AI_Agents`
  got wrong — those agents kept their instructions in the chat box and could not
  be re-run to the same result.

## Note

`03_Selenium_Salesforce_Framework/target/` holds compiled output. It is
gitignored, so a fresh clone needs `mvn test` to rebuild before the suite runs.
