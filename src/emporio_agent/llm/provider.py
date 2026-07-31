"""Provedores de LLM atrás de uma interface única com function calling.

Formato neutro de mensagens usado pelo agente (independente de provedor):
- ``{"role": "user" | "assistant", "content": str}``
- ``{"role": "assistant", "content": str | None, "tool_calls": [ToolCall, ...]}``
- ``{"role": "tool", "tool_call_id": str, "name": str, "content": str}``

Ferramentas são descritas como ``{"name", "description", "input_schema"}`` (JSON
Schema) e convertidas para o formato de cada provedor.

Dois provedores cobrem as três opções de configuração:
- ``AnthropicProvider`` — SDK oficial da Anthropic (tool use nativo);
- ``OpenAICompatProvider`` — endpoint /chat/completions compatível com OpenAI,
  que atende Groq (nuvem gratuita) e Ollama (local) apenas trocando a base_url.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from emporio_agent.config import OPENAI_COMPAT_BASE_URLS, Settings

Message = dict[str, Any]
ToolSpec = dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class LLMReply:
    text: str | None
    tool_calls: tuple[ToolCall, ...] = ()


class LLMProvider(Protocol):
    def complete(
        self, system: str, messages: list[Message], tools: list[ToolSpec]
    ) -> LLMReply: ...


class AnthropicProvider:
    """Provedor via SDK oficial da Anthropic (client.messages.create + tools)."""

    def __init__(self, api_key: str, model: str, max_tokens: int = 2048) -> None:
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def complete(
        self, system: str, messages: list[Message], tools: list[ToolSpec]
    ) -> LLMReply:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            tools=[
                {
                    "name": t["name"],
                    "description": t["description"],
                    "input_schema": t["input_schema"],
                }
                for t in tools
            ],
            messages=self._convert(messages),
        )
        text_parts: list[str] = []
        calls: list[ToolCall] = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                calls.append(ToolCall(id=block.id, name=block.name, arguments=dict(block.input)))
        return LLMReply(text="\n".join(text_parts) or None, tool_calls=tuple(calls))

    @staticmethod
    def _convert(messages: list[Message]) -> list[dict[str, Any]]:
        """Converte o formato neutro para blocos da API Anthropic.

        Resultados de ferramentas consecutivos são agrupados em UMA mensagem de
        usuário (exigência da API para chamadas paralelas).
        """
        converted: list[dict[str, Any]] = []
        for msg in messages:
            if msg["role"] == "tool":
                block = {
                    "type": "tool_result",
                    "tool_use_id": msg["tool_call_id"],
                    "content": msg["content"],
                }
                previous = converted[-1] if converted else None
                if (
                    previous is not None
                    and previous["role"] == "user"
                    and isinstance(previous["content"], list)
                ):
                    previous["content"].append(block)
                else:
                    converted.append({"role": "user", "content": [block]})
            elif msg["role"] == "assistant" and msg.get("tool_calls"):
                content: list[dict[str, Any]] = []
                if msg.get("content"):
                    content.append({"type": "text", "text": msg["content"]})
                content.extend(
                    {"type": "tool_use", "id": c.id, "name": c.name, "input": c.arguments}
                    for c in msg["tool_calls"]
                )
                converted.append({"role": "assistant", "content": content})
            else:
                converted.append({"role": msg["role"], "content": msg["content"]})
        return converted


class OpenAICompatProvider:
    """Provedor via endpoint compatível com OpenAI (Groq, Ollama)."""

    def __init__(self, api_key: str | None, model: str, base_url: str) -> None:
        from openai import OpenAI

        # Ollama não exige chave, mas o SDK exige o campo preenchido.
        self._client = OpenAI(api_key=api_key or "sem-chave", base_url=base_url)
        self._model = model

    def complete(
        self, system: str, messages: list[Message], tools: list[ToolSpec]
    ) -> LLMReply:
        converted: list[dict[str, Any]] = [{"role": "system", "content": system}]
        for msg in messages:
            if msg["role"] == "assistant" and msg.get("tool_calls"):
                converted.append(
                    {
                        "role": "assistant",
                        "content": msg.get("content"),
                        "tool_calls": [
                            {
                                "id": c.id,
                                "type": "function",
                                "function": {
                                    "name": c.name,
                                    "arguments": json.dumps(c.arguments, ensure_ascii=False),
                                },
                            }
                            for c in msg["tool_calls"]
                        ],
                    }
                )
            elif msg["role"] == "tool":
                converted.append(
                    {
                        "role": "tool",
                        "tool_call_id": msg["tool_call_id"],
                        "content": msg["content"],
                    }
                )
            else:
                converted.append({"role": msg["role"], "content": msg["content"]})

        response = self._client.chat.completions.create(
            model=self._model,
            messages=converted,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["input_schema"],
                    },
                }
                for t in tools
            ],
        )
        choice = response.choices[0].message
        calls = tuple(
            ToolCall(
                id=tc.id,
                name=tc.function.name,
                arguments=json.loads(tc.function.arguments or "{}"),
            )
            for tc in (choice.tool_calls or [])
        )
        return LLMReply(text=choice.content, tool_calls=calls)


def create_provider(settings: Settings) -> LLMProvider:
    """Instancia o provedor configurado no .env."""
    if settings.provider == "anthropic":
        assert settings.api_key is not None  # garantido por load_settings
        return AnthropicProvider(api_key=settings.api_key, model=settings.model)
    return OpenAICompatProvider(
        api_key=settings.api_key,
        model=settings.model,
        base_url=OPENAI_COMPAT_BASE_URLS[settings.provider],
    )
