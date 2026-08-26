# Run Locally

From this `src` directory:

```powershell
py -3 -m pip install -r requirements.txt
py -3 -m pytest
py -3 -m streamlit run app.py
```

Create `.env` in `03_LocalTestCaseGenerator` or `TestcaseGeneratorsSrc/src` with the values supplied by the user. Do not commit it.

Supported environment variables:

```text
JIRA_URL=
JIRA_EMAIL=
JIRA_TOKEN=
LLM_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:1b
GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-20b
JIRA_ACCEPTANCE_CRITERIA_FIELD=
```

The application never pulls the Ollama model. Groq is used only when selected or when Ollama fails and a Groq key is configured.
