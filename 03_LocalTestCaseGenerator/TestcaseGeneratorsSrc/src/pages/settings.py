from __future__ import annotations

import streamlit as st

from config_store import AppConfig, load_config, save_config, validate_config
from jira_client import check_jira_connection
from llm_client import check_groq_connection, check_ollama_connection


st.set_page_config(page_title="Settings | Jira Test Case Generator", page_icon="⚙️", layout="wide")
st.title("Settings")
st.caption("Configure Jira and AI providers. Secrets are never displayed after saving.")

config = load_config()

st.subheader("Jira")
jira_url = st.text_input("Jira URL", value=config.jira_url, placeholder="https://your-domain.atlassian.net")
jira_email = st.text_input("Jira email", value=config.jira_email)
jira_token = st.text_input("Jira API token", value="", type="password", help="Leave blank to keep the configured token.")
acceptance_field = st.text_input("Acceptance criteria field", value=config.acceptance_criteria_field, placeholder="customfield_10000")
if st.button("Test Jira Connection"):
    ok, message = check_jira_connection(
        AppConfig(jira_url=jira_url.strip(), jira_email=jira_email.strip(), jira_token=jira_token or config.jira_token)
    )
    (st.success if ok else st.error)(message)

st.subheader("LLM Provider")
st.session_state.setdefault("use_ollama", config.provider == "ollama")
st.session_state.setdefault("use_groq", config.provider == "groq")


def _keep_one_selected(changed_key: str, other_key: str) -> None:
    if st.session_state[changed_key]:
        st.session_state[other_key] = False
    elif not st.session_state[other_key]:
        st.session_state[changed_key] = True


provider_col1, provider_col2 = st.columns(2)
with provider_col1:
    st.checkbox("Ollama", key="use_ollama", on_change=_keep_one_selected, args=("use_ollama", "use_groq"))
with provider_col2:
    st.checkbox("Groq", key="use_groq", on_change=_keep_one_selected, args=("use_groq", "use_ollama"))

ollama_col, groq_col = st.columns(2)
with ollama_col:
    st.markdown("**Ollama**")
    ollama_url = st.text_input("Ollama URL", value=config.ollama_url)
    ollama_model = st.text_input("Ollama model", value=config.ollama_model)
    if st.button("Test Ollama Connection"):
        ok, message = check_ollama_connection(AppConfig(ollama_url=ollama_url.strip(), ollama_model=ollama_model.strip()))
        (st.success if ok else st.error)(message)

with groq_col:
    st.markdown("**Groq**")
    groq_api_key = st.text_input("Groq API key", value="", type="password", help="Leave blank to keep the configured key.")
    groq_model = st.text_input("Groq model", value=config.groq_model)
    if st.button("Test Groq Connection"):
        ok, message = check_groq_connection(AppConfig(groq_api_key=groq_api_key or config.groq_api_key, groq_model=groq_model.strip()))
        (st.success if ok else st.error)(message)

if st.button("Save settings", type="primary"):
    updated = AppConfig(
        jira_url=jira_url.strip(),
        jira_email=jira_email.strip(),
        jira_token=jira_token or config.jira_token,
        provider="ollama" if st.session_state.use_ollama else "groq",
        ollama_url=ollama_url.strip(),
        ollama_model=ollama_model.strip(),
        groq_api_key=groq_api_key or config.groq_api_key,
        groq_model=groq_model.strip(),
        acceptance_criteria_field=acceptance_field.strip(),
    )
    errors = validate_config(updated)
    if errors:
        for error in errors:
            st.error(error)
    else:
        save_config(updated)
        st.success("Settings saved securely in the local runtime store.")
        st.json(updated.public_values())
