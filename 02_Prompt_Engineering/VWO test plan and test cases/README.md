# VWO test plan and test cases

[VWO_Login_Test_Plan.md](VWO_Login_Test_Plan.md) is a test plan for the VWO login page
(`https://app.vwo.com/#/login`), written under the rules in
[`01_LLM_Basics/ANTI-HALLUCINATION.rules.md`](../../01_LLM_Basics/ANTI-HALLUCINATION.rules.md).

It opens with **Verified Facts** (only what the supplied evidence shows: the URL, the email and password fields,
Remember me, Sign in, and the other sign-in options) and **Missing / Unknown Information** (credentials, error
messages, lockout and MFA behaviour, and more, none of it assumed). Then come:
- the RICE-POT test approach;
- scope;
- entry and exit criteria;
- test data;
- 16 test cases, `VWO-LOGIN-001` to `VWO-LOGIN-016`;
- two self-validation checks.

Where the evidence does not say what should happen, a test case's expected result starts with "Insufficient
information to determine the expected…" instead of inventing one. That is the point of the plan. The
[Prompt Engineering README](../README.md#the-worked-test-plan) explains where it fits.
