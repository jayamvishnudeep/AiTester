# Test Creator data

[vwo_5000_test_cases.csv](vwo_5000_test_cases.csv) is the test case library Test Creator MCP serves: 5,000 test
cases, `VWO-1001` to `VWO-6000`, across 17 VWO modules. Each case has a priority, test type, status, browser, device,
4 steps and an expected result.

The server only reads this file and reloads it when it changes. Test cases created through the `create_test_case`
and `create_environment_variants` tools are written to `new_test_cases.csv` in this folder; the library itself is
never edited. Point the server at another library with `TC_MCP_CSV`, or the new cases elsewhere with
`TC_MCP_NEW_CASES`; see the [README](../README.md#settings).
