# VWO Login Test Plan

## Verified Facts

- The supplied application URL is `https://app.vwo.com/#/login`.
- The available login-page evidence identifies an email address field.
- The available login-page evidence identifies a password field.
- The available login-page evidence identifies a Remember me control.
- The available login-page evidence identifies a Sign in control.
- The available login-page evidence identifies Forgot Password, Google sign-in, SSO sign-in, and Passkey sign-in controls.
- The available page evidence displays the title `Login - Wingify`.
- The available page evidence displays `app.vwo.com has transitioned to app.wingify.com`.

## Missing / Unknown Information

- Valid test credentials are not provided.
- The expected successful-login URL is not provided.
- The exact invalid-credential message is not provided.
- The exact required-field validation messages are not provided.
- The exact email-format validation behavior is not provided.
- The Remember me persistence behavior is not provided.
- CAPTCHA, MFA, rate limiting, lockout, and session-timeout behavior are not provided.
- Supported browsers, devices, environments, and accessibility criteria are not provided.
- The ownership and expected behavior of the Google, SSO, Passkey, and Forgot Password flows are not provided.

## RICE-POT Test Approach

| RICE-POT Element | Test Approach | VWO Application | Evidence or Status |
|---|---|---|---|
| Role | Apply a QA perspective focused on traceability and reproducibility. | Validate only the supplied VWO login-page facts and record observed behavior. | QA role is an approach definition; organizational role is not provided. |
| Instructions | Start with fact verification, then execute positive and negative cases only when data and expected results are available. | Check the supplied URL, page title, transition notice, and identified controls before attempting authentication. | Test cases are documented; execution status is `Not Executed`. |
| Context | Use the target URL and available page evidence as the test baseline. | Target: `https://app.vwo.com/#/login`; controls include email, password, Remember me, Sign in, Forgot Password, Google sign-in, SSO sign-in, and Passkey sign-in. | URL and page evidence are available. |
| Expected Outcome | Compare actual results with documented requirements; never infer a pass condition. | Confirm supplied page facts. For login, validation, redirect, and persistence behavior, capture results until requirements are supplied. | Missing outcomes are marked `Insufficient information to determine.` |
| Parameters | Use only supplied test data and environment details. | Credentials, invalid values, environment, browsers, devices, validation rules, persistence rules, and security policies must be supplied or captured. | Most execution parameters are not provided. |
| Output | Produce a single evidence-based plan containing scope, cases, missing information, and status. | Maintain the test cases in this document and attach reproducible evidence for failures. | This document is the combined output. |
| Tone | Keep decisions deterministic, precise, and explicit about uncertainty. | Use `Not Executed`, `Blocked`, `Pass`, or `Fail` only when supported by execution evidence. | Applied throughout this document. |

## Test Objective

Verify the facts supplied for the VWO login page and identify behavior that requires confirmation from requirements or controlled execution.

## Scope

### In Scope

- Page availability at the supplied URL.
- Page title and transition notice shown in the available evidence.
- Presence and usability of the supplied email, password, Remember me, and Sign in controls.
- Validation behavior for missing and invalid credentials, subject to confirmation of expected results.
- Authentication behavior with credentials supplied through an approved secure channel.
- Discovery of the supplied secondary controls without assuming their downstream behavior.

### Out of Scope

- Any behavior not supplied in the verified facts or confirmed during execution.
- Authenticated application features after login.
- Security, performance, compatibility, and accessibility acceptance criteria until they are provided.

## Entry Criteria

- The supplied URL is reachable in the test environment.
- Test credentials and expected outcomes are provided through an approved secure channel when authenticated testing is required.
- Expected validation messages and redirect behavior are documented or captured as execution evidence.

## Exit Criteria

- Every in-scope case has a Pass, Fail, Blocked, or Not Executed result.
- Failed results include reproducible evidence.
- Unknown requirements remain explicitly recorded and are not converted into assumptions.

## Test Data and Configuration

- Application URL: `https://app.vwo.com/#/login`
- Valid email: `Not provided`
- Valid password: `Not provided`
- Invalid email: `Not provided`
- Invalid password: `Not provided`
- Environment: `Not provided`
- Browser and device matrix: `Not provided`

## Defect Evidence

For each failure, record the test ID, URL, environment, browser, timestamp, exact steps, actual result, expected result source, console or network evidence where applicable, and screenshot or trace.

## Test Cases

| Test ID | Priority | Scenario | Preconditions | Steps | Expected Result | Status |
|---|---|---|---|---|---|---|
| VWO-LOGIN-001 | High | Open the supplied login URL | Network access is available | Navigate to `https://app.vwo.com/#/login` | The supplied URL opens. | Not Executed |
| VWO-LOGIN-002 | Medium | Verify page title from evidence | Login page is open | Read the page title | The title is `Login - Wingify`. | Not Executed |
| VWO-LOGIN-003 | Medium | Verify transition notice from evidence | Login page is open | Inspect the page content | The text `app.vwo.com has transitioned to app.wingify.com` is displayed. | Not Executed |
| VWO-LOGIN-004 | High | Verify email field is available | Login page is open | Locate the email address field | The email address field is available. | Not Executed |
| VWO-LOGIN-005 | High | Verify password field is available | Login page is open | Locate the password field | The password field is available. | Not Executed |
| VWO-LOGIN-006 | High | Verify Sign in control is available | Login page is open | Locate the Sign in control | The Sign in control is available. | Not Executed |
| VWO-LOGIN-007 | Medium | Verify Remember me control is available | Login page is open | Locate the Remember me control | The Remember me control is available. | Not Executed |
| VWO-LOGIN-008 | High | Submit empty credentials | Login page is open | Select Sign in without entering values | Insufficient information to determine the expected validation behavior. Capture the actual result. | Not Executed |
| VWO-LOGIN-009 | High | Submit an invalid email format | Login page is open; invalid email data is available | Enter the invalid email and a password; select Sign in | Insufficient information to determine the expected validation behavior. Capture the actual result. | Not Executed |
| VWO-LOGIN-010 | Critical | Submit unknown credentials | Login page is open; invalid credential data is available | Enter invalid credentials; select Sign in | Insufficient information to determine the expected authentication error and navigation behavior. Capture the actual result. | Not Executed |
| VWO-LOGIN-011 | Critical | Submit valid credentials | Login page is open; approved valid credentials are available | Enter valid credentials; select Sign in | Insufficient information to determine the expected success URL and authenticated result. Capture the actual result. | Not Executed |
| VWO-LOGIN-012 | Medium | Toggle Remember me | Login page is open | Select Remember me; inspect the control state | Insufficient information to determine whether the state changes and persists. Capture the actual result. | Not Executed |
| VWO-LOGIN-013 | Medium | Discover Forgot Password control | Login page is open | Locate and select Forgot Password | Insufficient information to determine the expected destination and behavior. Capture the actual result. | Not Executed |
| VWO-LOGIN-014 | Medium | Discover Google sign-in control | Login page is open | Locate and select Google sign-in | Insufficient information to determine the expected authentication flow. Capture the actual result. | Not Executed |
| VWO-LOGIN-015 | Medium | Discover SSO sign-in control | Login page is open | Locate and select SSO sign-in | Insufficient information to determine the expected authentication flow. Capture the actual result. | Not Executed |
| VWO-LOGIN-016 | Medium | Discover Passkey sign-in control | Login page is open | Locate and select Passkey sign-in | Insufficient information to determine the expected authentication flow. Capture the actual result. | Not Executed |

## Test Case Self-Validation Check

- Each case is traceable to the verified facts or explicitly states that the expected result is unknown.
- No credentials, error text, redirect URL, security policy, or browser requirement has been invented.
- Cases are marked `Not Executed` because no execution result was supplied.

## Anti-Hallucination Self-Validation Check

- Facts are limited to the supplied URL and available page evidence.
- No error message, redirect, security rule, credential, or downstream flow has been invented.
- Unknown behavior is listed under `Missing / Unknown Information` or marked as requiring confirmation.
