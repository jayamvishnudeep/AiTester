from __future__ import annotations

from unittest.mock import Mock

import requests

from config_store import AppConfig
from llm_client import LLMClient, check_groq_connection, check_ollama_connection


def response(payload: dict, status_code: int = 200) -> Mock:
    item = Mock()
    item.status_code = status_code
    item.json.return_value = payload
    item.raise_for_status.side_effect = None if status_code < 400 else RuntimeError("failure")
    return item


def test_ollama_is_used_by_default():
    session = Mock()
    session.post.return_value = response({"response": "generated"})
    result = LLMClient(AppConfig(), session).generate("prompt")
    assert result.text == "generated"
    assert result.provider == "ollama"
    assert session.post.call_args.args[0].endswith("/api/generate")


def test_groq_fallback_is_used_when_ollama_fails():
    session = Mock()
    session.post.side_effect = [requests.ConnectionError("ollama down"), response({"choices": [{"message": {"content": "fallback"}}]})]
    config = AppConfig(groq_api_key="groq-secret")
    result = LLMClient(config, session).generate("prompt")
    assert result.text == "fallback"
    assert result.provider == "groq-fallback"


def test_check_ollama_connection_succeeds_when_reachable():
    session = Mock()
    session.get.return_value = response({"models": [{"name": "gemma3:1b"}]})
    ok, message = check_ollama_connection(AppConfig(ollama_model="gemma3:1b"), session)
    assert ok is True
    assert "Connected" in message


def test_check_ollama_connection_fails_when_unreachable():
    session = Mock()
    session.get.side_effect = requests.ConnectionError("no route")
    ok, message = check_ollama_connection(AppConfig(), session)
    assert ok is False
    assert "Could not reach Ollama" in message


def test_check_groq_connection_fails_without_api_key():
    ok, message = check_groq_connection(AppConfig(groq_api_key=""))
    assert ok is False
    assert "API key" in message


def test_check_groq_connection_fails_on_unauthorized():
    session = Mock()
    session.get.return_value = response({}, status_code=401)
    ok, message = check_groq_connection(AppConfig(groq_api_key="bad-key"), session)
    assert ok is False
    assert "rejected" in message


def test_check_groq_connection_succeeds_when_authorized():
    session = Mock()
    session.get.return_value = response({"data": []})
    ok, message = check_groq_connection(AppConfig(groq_api_key="good-key"), session)
    assert ok is True
    assert "Connected" in message
