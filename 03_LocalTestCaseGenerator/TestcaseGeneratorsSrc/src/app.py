from __future__ import annotations

from pathlib import Path

from config_store import load_config, validate_config
from jira_client import JiraClient, JiraClientError, extract_ticket_key
from llm_client import LLMClient, LLMClientError


TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "templates" / "testcase_creator.md"
BUNDLED_TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "testcase_creator.md"


def load_template() -> str:
    for path in (TEMPLATE_PATH, BUNDLED_TEMPLATE_PATH):
        try:
            content = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if content:
            return content
    raise RuntimeError("The local test-case template could not be loaded.")


def build_prompt(template: str, ticket_key: str, summary: str, description: str, acceptance_criteria: str) -> str:
    ticket_content = (
        f"JIRA TICKET: {ticket_key}\n"
        f"SUMMARY: {summary or 'Not specified'}\n"
        f"DESCRIPTION: {description or 'Not specified'}\n"
        f"ACCEPTANCE CRITERIA: {acceptance_criteria or 'Not specified'}"
    )
    return f"{template}\n\nREQUIREMENTS FROM JIRA:\n{ticket_content}"


def process_request(message: str) -> tuple[str, str]:
    config = load_config()
    errors = validate_config(config)
    if errors:
        return "\n".join(errors), "configuration"
    ticket_key = extract_ticket_key(message)
    if not ticket_key:
        return "Enter a Jira ticket key such as PROJ-123 in your request.", "validation"
    try:
        ticket = JiraClient(config).fetch_ticket(ticket_key)
        prompt = build_prompt(load_template(), ticket.key, ticket.summary, ticket.description, ticket.acceptance_criteria)
        result = LLMClient(config).generate(prompt)
        return f"Provider: {result.provider}\n\n{result.text}", "success"
    except (JiraClientError, LLMClientError, RuntimeError) as exc:
        return str(exc), "error"


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="Jira Test Case Generator", page_icon="🧪", layout="wide")
    st.title("Jira Test Case Generator")
    st.caption("Create a draft test-case suite from a Jira ticket.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    request = st.chat_input("Example: create test cases for PROJ-123")
    if request:
        st.session_state.messages.append({"role": "user", "content": request})
        with st.chat_message("user"):
            st.markdown(request)
        with st.chat_message("assistant"):
            with st.spinner("Fetching Jira requirements and generating test cases..."):
                response, status = process_request(request)
            if status == "success":
                st.markdown(response)
            else:
                st.error(response)
        st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()
