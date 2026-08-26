from __future__ import annotations

from config_store import AppConfig, validate_config


def test_validate_config_requires_jira_values():
    errors = validate_config(AppConfig())
    assert "Jira URL is required." in errors
    assert "Jira email is required." in errors
    assert "Jira token is required." in errors


def test_public_values_redact_secrets():
    config = AppConfig(jira_token="jira-secret", groq_api_key="groq-secret")
    values = config.public_values()
    assert values["jira_token"] == "********"
    assert values["groq_api_key"] == "********"
    assert "jira-secret" not in str(values)
    assert "groq-secret" not in str(values)
