"""Configuração da aplicação, carregada de variáveis de ambiente (.env).

Decisão de modelo padrão (justificada no README): claude-haiku-4-5 — rápido e
barato o suficiente para o avaliador rodar o projeto sem custo relevante, com
qualidade adequada para atendimento com ferramentas. Provedores alternativos
gratuitos/locais (groq, ollama) ficam a uma variável de ambiente de distância.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

PROVIDERS = ("anthropic", "groq", "ollama")

DEFAULT_MODELS = {
    "anthropic": "claude-haiku-4-5",
    # gpt-oss-120b: melhor function calling entre os modelos da camada gratuita
    # da Groq (o llama-3.3-70b gera sintaxe de tool call malformada com frequência).
    "groq": "openai/gpt-oss-120b",
    "ollama": "qwen2.5:14b",
}

OPENAI_COMPAT_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "ollama": "http://localhost:11434/v1",
}


class ConfigError(Exception):
    """Configuração ausente ou inválida no ambiente/.env."""


@dataclass(frozen=True)
class Settings:
    provider: str
    model: str
    api_key: str | None


def load_settings() -> Settings:
    """Lê o .env (se existir) e valida a configuração do provedor."""
    load_dotenv()
    provider = os.environ.get("LLM_PROVIDER", "anthropic").strip().casefold()
    if provider not in PROVIDERS:
        raise ConfigError(
            f"LLM_PROVIDER inválido: {provider!r}. Opções: {', '.join(PROVIDERS)}."
        )

    api_key = os.environ.get("LLM_API_KEY", "").strip() or None
    if provider in ("anthropic", "groq") and not api_key:
        raise ConfigError(
            f"LLM_API_KEY é obrigatória para o provedor {provider!r}."
            " Copie .env.example para .env e preencha (detalhes no README)."
        )

    model = os.environ.get("LLM_MODEL", "").strip() or DEFAULT_MODELS[provider]
    return Settings(provider=provider, model=model, api_key=api_key)
