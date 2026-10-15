# Hosted UI

A standalone page for the [Flaky Test Case Finder](../README.md#the-hosted-version-no-install): no Langflow, no API
key, nothing to install.

| File | What it is |
|---|---|
| [index.html](index.html) | The page. It is the same file that is deployed |
| [Flaky_Test_Finder_Hosted_UI.png](Flaky_Test_Finder_Hosted_UI.png) | The page after two reports were uploaded: 2 flaky tests found, with each one's attempts in both runs |

Open `index.html` in a browser (or the hosted link in the parent README), press **Upload files**, and pick two
Playwright JSON reports. The comparison runs in the browser and the reports are never uploaded. The page reads each
report's `stats.startTime`, so the order you pick them in does not matter. It gives the same verdict as the Langflow
flow, without the written summary.
