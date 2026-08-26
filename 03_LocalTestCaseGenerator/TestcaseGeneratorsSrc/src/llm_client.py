from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from config_store import AppConfig


class LLMClientError(RuntimeError):
    pass


@dataclass
class GenerationResult:
    text: str
    provider: str


def _groq_error_detail(response: requests.Response) -> str:
    try:
        message = response.json().get("error", {}).get("message", "")
    except (ValueError, AttributeError):
        message = ""
    return f"HTTP {response.status_code} - {message or response.text[:200]}"


class LLMClient:
    def __init__(self, config: AppConfig, session: requests.Session | None = None) -> None:
        self.config = config
        self.session = session or requests.Session()

    def generate(self, prompt: str) -> GenerationResult:
        if self.config.provider == "groq":
            return GenerationResult(self._groq(prompt), "groq")
        try:
            return GenerationResult(self._ollama(prompt), "ollama")
        except LLMClientError:
            if not self.config.groq_api_key:
                raise LLMClientError("Ollama is unavailable and no Groq API key is configured for fallback.")
            return GenerationResult(self._groq(prompt), "groq-fallback")

    def _ollama(self, prompt: str) -> str:
        try:
            response = self.session.post(
                f"{self.config.ollama_url.rstrip('/')}/api/generate",
                json={"model": self.config.ollama_model, "prompt": prompt, "stream": False},
                timeout=120,
            )
            response.raise_for_status()
            body: dict[str, Any] = response.json()
            text = str(body.get("response", "")).strip()
            if not text:
                raise LLMClientError("Ollama returned an empty response.")
            return text
        except (requests.RequestException, ValueError, LLMClientError) as exc:
            if isinstance(exc, LLMClientError):
                raise
            raise LLMClientError("Ollama generation failed.") from exc

    def _groq(self, prompt: str) -> str:
        if not self.config.groq_api_key:
            raise LLMClientError("Groq API key is not configured.")
        try:
            response = self.session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.config.groq_api_key}"},
                json={
                    "model": self.config.groq_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                },
                timeout=120,
            )
        except requests.RequestException as exc:
            raise LLMClientError("Groq could not be reached. Check your network connection.") from exc
        if response.status_code >= 400:
            raise LLMClientError(f"Groq request failed: {_groq_error_detail(response)}")
        try:
            body: dict[str, Any] = response.json()
            text = str(body["choices"][0]["message"]["content"]).strip()
        except (ValueError, KeyError, IndexError) as exc:
            raise LLMClientError("Groq returned an unreadable response.") from exc
        if not text:
            raise LLMClientError("Groq returned an empty response.")
        return text


def check_ollama_connection(config: AppConfig, session: requests.Session | None = None) -> tuple[bool, str]:
    session = session or requests.Session()
    if not config.ollama_url:
        return False, "Ollama URL is not configured."
    try:
        response = session.get(f"{config.ollama_url.rstrip('/')}/api/tags", timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        return False, f"Could not reach Ollama at {config.ollama_url}: {exc}"
    try:
        models = [item.get("name", "") for item in response.json().get("models", [])]
    except (ValueError, AttributeError):
        return True, "Connected to Ollama."
    if config.ollama_model and models and config.ollama_model not in models:
        return True, f"Connected to Ollama, but model '{config.ollama_model}' was not found locally."
    return True, "Connected to Ollama."


def check_groq_connection(config: AppConfig, session: requests.Session | None = None) -> tuple[bool, str]:
    if not config.groq_api_key:
        return False, "Groq API key is not configured."
    session = session or requests.Session()
    try:
        response = session.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {config.groq_api_key}"},
            timeout=10,
        )
    except requests.RequestException as exc:
        return False, f"Could not reach Groq: {exc}"
    if response.status_code in {401, 403}:
        return False, "Groq rejected the configured API key."
    if response.status_code >= 400:
        return False, f"Groq returned HTTP {response.status_code}."
    return True, "Connected to Groq."
