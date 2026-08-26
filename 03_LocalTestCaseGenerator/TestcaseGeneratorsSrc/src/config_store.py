from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


@dataclass
class AppConfig:
    jira_url: str = ""
    jira_email: str = ""
    jira_token: str = ""
    provider: str = "ollama"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:1b"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    acceptance_criteria_field: str = ""

    def public_values(self) -> dict[str, str]:
        values = asdict(self)
        values["jira_token"] = "" if not self.jira_token else "********"
        values["groq_api_key"] = "" if not self.groq_api_key else "********"
        return values


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = Path(__file__).resolve().parent
RUNTIME_PATH = SRC_ROOT / ".runtime" / "config.json"


def _load_environment() -> None:
    for path in (PROJECT_ROOT / ".env", SRC_ROOT / ".env", Path.cwd() / ".env"):
        if path.is_file():
            load_dotenv(path, override=False)


def _first_env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None:
            return value.strip()
    return default


def load_config() -> AppConfig:
    _load_environment()
    values: dict[str, Any] = {}
    if RUNTIME_PATH.is_file():
        try:
            values = json.loads(RUNTIME_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            values = {}

    return AppConfig(
        jira_url=_first_env("JIRA_URL", "JIRA_BASE_URL", default=str(values.get("jira_url", ""))),
        jira_email=_first_env("JIRA_EMAIL", "JIRA_EMAIL_ID", default=str(values.get("jira_email", ""))),
        jira_token=_first_env("JIRA_TOKEN", "JIRA_API_TOKEN", default=str(values.get("jira_token", ""))),
        provider=_first_env("LLM_PROVIDER", default=str(values.get("provider", "ollama"))).lower(),
        ollama_url=_first_env("OLLAMA_URL", "OLLAMA_ENDPOINT", default=str(values.get("ollama_url", "http://localhost:11434"))),
        ollama_model=_first_env("OLLAMA_MODEL", default=str(values.get("ollama_model", "gemma3:1b"))),
        groq_api_key=_first_env("GROQ_API_KEY", "GROQ_TOKEN", default=str(values.get("groq_api_key", ""))),
        groq_model=_first_env("GROQ_MODEL", default=str(values.get("groq_model", "openai/gpt-oss-20b"))),
        acceptance_criteria_field=_first_env("JIRA_ACCEPTANCE_CRITERIA_FIELD", default=str(values.get("acceptance_criteria_field", ""))),
    )


def save_config(config: AppConfig) -> None:
    RUNTIME_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_PATH.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")


def validate_config(config: AppConfig, require_provider_key: bool = True) -> list[str]:
    errors: list[str] = []
    if not config.jira_url:
        errors.append("Jira URL is required.")
    if not config.jira_email:
        errors.append("Jira email is required.")
    if not config.jira_token:
        errors.append("Jira token is required.")
    if config.provider not in {"ollama", "groq"}:
        errors.append("Provider must be Ollama or Groq.")
    if config.provider == "groq" and require_provider_key and not config.groq_api_key:
        errors.append("Groq API key is required when Groq is selected.")
    return errors
