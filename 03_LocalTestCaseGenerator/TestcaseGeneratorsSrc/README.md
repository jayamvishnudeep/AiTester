# TestcaseGeneratorsSrc

The source of the [Local Test Case Generator](../README.md): a Streamlit app that turns a Jira ticket into test
cases with a model on your own machine (Ollama), falling back to Groq.

| Path | What it is |
|---|---|
| [src/](src/) | The app: `app.py` (chat screen and request flow), `pages/settings.py`, `config_store.py`, `jira_client.py`, `llm_client.py`, `requirements.txt`, and pytest suites in `tests/` |
| [prompt.md](prompt.md), [finetuned_prompt.md](finetuned_prompt.md) | The build prompt before and after tuning |
| [Application_chart.png](Application_chart.png) | The hand-drawn wireframe the app was built from |
| [Test_Results_images/](Test_Results_images/) | Screenshots of the app answering with Ollama and with Groq, and of its settings screen |

## Run

```powershell
cd 03_LocalTestCaseGenerator/TestcaseGeneratorsSrc/src
py -3 -m pip install -r requirements.txt
py -3 -m pytest
py -3 -m streamlit run app.py
```

Install Ollama and run `ollama pull gemma3:1b` first: the app never pulls the model itself. Settings (Jira and
the model providers) go in the Settings screen or a gitignored `.env`; the full list is in the
[parent README](../README.md#running-it).
