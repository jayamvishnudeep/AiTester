# Templates

[testcase_creator.md](testcase_creator.md) is the QA prompt template the [Local Test Case Generator](../README.md)
pastes above every Jira ticket. It sets the role (a senior QA engineer) and the task (generate test cases for a
feature), plus three constraints:
- use only the provided requirements;
- do not assume undocumented behaviour;
- write "Not specified" when information is missing.

The app loads this file at run time, so editing it changes every generated suite. If it is missing, the app uses
the bundled copy in `TestcaseGeneratorsSrc/src/templates/`.
