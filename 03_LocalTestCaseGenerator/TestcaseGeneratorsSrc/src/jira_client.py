from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import requests

from config_store import AppConfig


TICKET_KEY_PATTERN = re.compile(r"\b[A-Z][A-Z0-9_]*-\d+\b")


class JiraClientError(RuntimeError):
    pass


@dataclass
class JiraTicket:
    key: str
    summary: str
    description: str
    acceptance_criteria: str


def extract_ticket_key(message: str) -> str | None:
    match = TICKET_KEY_PATTERN.search(message.upper())
    return match.group(0) if match else None


def _text_from_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(part for item in value if (part := _text_from_value(item)))
    if isinstance(value, dict):
        if "text" in value:
            return str(value["text"])
        return "\n".join(part for item in value.values() if (part := _text_from_value(item)))
    return str(value)


def _extract_fields(payload: dict[str, Any], acceptance_field: str) -> JiraTicket:
    fields = payload.get("fields") or {}
    key = str(payload.get("key") or "")
    acceptance = fields.get(acceptance_field) if acceptance_field else None
    if acceptance is None:
        for name, value in fields.items():
            if "acceptance" in name.lower():
                acceptance = value
                break
    return JiraTicket(
        key=key,
        summary=_text_from_value(fields.get("summary")),
        description=_text_from_value(fields.get("description")),
        acceptance_criteria=_text_from_value(acceptance),
    )


class JiraClient:
    def __init__(self, config: AppConfig, session: requests.Session | None = None) -> None:
        self.config = config
        self.session = session or requests.Session()

    def fetch_ticket(self, ticket_key: str) -> JiraTicket:
        if not TICKET_KEY_PATTERN.fullmatch(ticket_key.upper()):
            raise JiraClientError("Enter a valid Jira ticket key, for example PROJ-123.")
        base_url = self.config.jira_url.rstrip("/")
        url = f"{base_url}/rest/api/2/issue/{ticket_key.upper()}"
        try:
            response = self.session.get(
                url,
                auth=(self.config.jira_email, self.config.jira_token),
                headers={"Accept": "application/json"},
                timeout=20,
            )
        except requests.RequestException as exc:
            raise JiraClientError("Jira could not be reached. Check the URL or network connection.") from exc
        if response.status_code in {401, 403}:
            raise JiraClientError("Jira rejected the configured credentials or permissions.")
        if response.status_code == 404:
            raise JiraClientError(f"Jira ticket {ticket_key.upper()} was not found.")
        if response.status_code >= 400:
            raise JiraClientError(f"Jira returned HTTP {response.status_code}.")
        try:
            return _extract_fields(response.json(), self.config.acceptance_criteria_field)
        except (ValueError, TypeError) as exc:
            raise JiraClientError("Jira returned an unreadable issue response.") from exc


def check_jira_connection(config: AppConfig, session: requests.Session | None = None) -> tuple[bool, str]:
    if not config.jira_url or not config.jira_email or not config.jira_token:
        return False, "Jira URL, email, and API token are all required."
    session = session or requests.Session()
    base_url = config.jira_url.rstrip("/")
    try:
        response = session.get(
            f"{base_url}/rest/api/2/myself",
            auth=(config.jira_email, config.jira_token),
            headers={"Accept": "application/json"},
            timeout=10,
        )
    except requests.RequestException as exc:
        return False, f"Could not reach Jira at {config.jira_url}: {exc}"
    if response.status_code in {401, 403}:
        return False, "Jira rejected the configured credentials or permissions."
    if response.status_code >= 400:
        return False, f"Jira returned HTTP {response.status_code}."
    try:
        display_name = str(response.json().get("displayName", "")).strip()
    except (ValueError, TypeError):
        display_name = ""
    return True, f"Connected to Jira as {display_name}." if display_name else "Connected to Jira."
