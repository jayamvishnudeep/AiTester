from __future__ import annotations

from unittest.mock import Mock

from config_store import AppConfig
from jira_client import JiraClient, JiraClientError, check_jira_connection, extract_ticket_key


def test_extract_ticket_key_is_case_insensitive():
    assert extract_ticket_key("create tc for vwo-49") == "VWO-49"


def test_extract_ticket_key_returns_none_when_missing():
    assert extract_ticket_key("create a login checklist") is None


def test_fetch_ticket_maps_jira_fields():
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "key": "PROJ-123",
        "fields": {
            "summary": "Add login validation",
            "description": {"content": [{"content": [{"text": "Validate invalid credentials"}]}]},
            "customfield_10000": "User sees a validation message",
        },
    }
    session = Mock()
    session.get.return_value = response
    client = JiraClient(AppConfig(jira_url="https://jira.example", jira_email="qa@example.com", jira_token="token", acceptance_criteria_field="customfield_10000"), session)

    ticket = client.fetch_ticket("PROJ-123")

    assert ticket.summary == "Add login validation"
    assert "Validate invalid credentials" in ticket.description
    assert ticket.acceptance_criteria == "User sees a validation message"
    session.get.assert_called_once()


def test_fetch_ticket_rejects_invalid_key():
    client = JiraClient(AppConfig(jira_url="https://jira.example", jira_email="qa@example.com", jira_token="token"), Mock())
    try:
        client.fetch_ticket("not-a-ticket")
    except JiraClientError as error:
        assert "valid Jira ticket key" in str(error)
    else:
        raise AssertionError("Expected invalid Jira key to fail")


def test_check_jira_connection_fails_when_config_incomplete():
    ok, message = check_jira_connection(AppConfig(jira_url="https://jira.example"))
    assert ok is False
    assert "required" in message


def test_check_jira_connection_fails_on_unauthorized():
    response = Mock()
    response.status_code = 401
    session = Mock()
    session.get.return_value = response
    config = AppConfig(jira_url="https://jira.example", jira_email="qa@example.com", jira_token="bad-token")

    ok, message = check_jira_connection(config, session)

    assert ok is False
    assert "rejected" in message


def test_check_jira_connection_succeeds_when_authorized():
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"displayName": "QA Bot"}
    session = Mock()
    session.get.return_value = response
    config = AppConfig(jira_url="https://jira.example", jira_email="qa@example.com", jira_token="good-token")

    ok, message = check_jira_connection(config, session)

    assert ok is True
    assert "QA Bot" in message
