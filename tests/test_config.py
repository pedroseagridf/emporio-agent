"""Carregamento e validação da configuração de ambiente."""

import pytest

from emporio_agent.config import ConfigError, load_settings


def test_provider_invalido(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "skynet")
    with pytest.raises(ConfigError, match="skynet"):
        load_settings()


def test_anthropic_exige_chave(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_API_KEY", "")
    with pytest.raises(ConfigError, match="LLM_API_KEY"):
        load_settings()


def test_ollama_dispensa_chave_e_usa_modelo_padrao(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_MODEL", "")
    settings = load_settings()
    assert settings.provider == "ollama"
    assert settings.api_key is None
    assert settings.model  # modelo padrão preenchido


def test_modelo_customizado_prevalece(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_MODEL", "llama3.1:8b")
    assert load_settings().model == "llama3.1:8b"
