"""Núcleo do agente: loop de function calling com memória de conversa.

Decisão (justificada no README): loop próprio e enxuto em vez de framework de
agentes — o formato neutro de mensagens permite trocar de provedor (Anthropic,
Groq, Ollama) sem reescrever o agente, e o fluxo fica inteiramente inspecionável.

O histórico vive em memória durante a sessão. Cada resposta registra em
``last_tool_calls`` as ferramentas usadas — é o que os testes comportamentais
verificam (comportamento, não texto exato).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from emporio_agent.llm.provider import LLMProvider, Message, ToolCall
from emporio_agent.text_utils import format_datetime_ptbr
from emporio_agent.tools import AgentTools

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "system.md"

MAX_TOOL_ROUNDS = 8

#: Tentativas por chamada ao provedor. Modelos abertos ocasionalmente geram a
#: sintaxe da chamada de ferramenta malformada (erro 400 "tool_use_failed" na
#: Groq); uma nova amostragem costuma resolver.
PROVIDER_ATTEMPTS = 3

_FALLBACK_LIMITE = (
    "Puxa, essa consulta ficou mais complexa do que o esperado e não consegui"
    " concluir por aqui. 🙏 Pode reformular a pergunta, ou se preferir eu encaminho"
    " para um atendente humano da equipe?"
)

_FALLBACK_ERRO = (
    "Opa, tive um probleminha técnico aqui do meu lado e não consegui completar"
    " a consulta agora. Pode tentar de novo em instantes? Se continuar, é só pedir"
    " que eu encaminho você para um atendente da equipe."
)


class Agent:
    """Agente de atendimento da Empório da Música."""

    def __init__(
        self,
        provider: LLMProvider,
        tools: AgentTools,
        system_prompt: str | None = None,
        max_tool_rounds: int = MAX_TOOL_ROUNDS,
        clock: Callable[[], datetime] = datetime.now,
        retry_wait: float = 0.5,
    ) -> None:
        self._provider = provider
        self._tools = tools
        self._system_template = system_prompt or SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
        self._max_tool_rounds = max_tool_rounds
        self._clock = clock
        self._retry_wait = retry_wait
        self._history: list[Message] = []
        self.last_tool_calls: list[ToolCall] = []

    @property
    def history(self) -> list[Message]:
        return list(self._history)

    def reset(self) -> None:
        """Começa uma conversa do zero."""
        self._history.clear()
        self.last_tool_calls = []

    def _system_prompt(self) -> str:
        return self._system_template.replace(
            "{data_hora_atual}", format_datetime_ptbr(self._clock())
        )

    def send(self, user_message: str) -> str:
        """Processa uma mensagem do cliente e retorna a resposta do agente."""
        self.last_tool_calls = []
        self._history.append({"role": "user", "content": user_message})
        pending: list[Message] = []

        try:
            for _ in range(self._max_tool_rounds):
                reply = self._complete_with_retry(self._history + pending)
                if not reply.tool_calls:
                    self._history.extend(pending)
                    self._history.append({"role": "assistant", "content": reply.text or ""})
                    return reply.text or ""

                pending.append(
                    {"role": "assistant", "content": reply.text, "tool_calls": reply.tool_calls}
                )
                for call in reply.tool_calls:
                    self.last_tool_calls.append(call)
                    logger.info("ferramenta=%s args=%s", call.name, call.arguments)
                    result = self._tools.execute(call.name, call.arguments)
                    pending.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "name": call.name,
                            "content": result,
                        }
                    )
        except Exception:
            logger.exception("Falha ao processar a mensagem (provedor ou ferramenta)")
            # Mantém apenas a mensagem do usuário e limpa o trace: a próxima
            # tentativa recomeça limpa e a CLI não exibe ferramentas de um turno
            # que falhou.
            self.last_tool_calls = []
            return _FALLBACK_ERRO

        logger.warning("Limite de %d rodadas de ferramentas atingido", self._max_tool_rounds)
        self._history.extend(pending)
        self._history.append({"role": "assistant", "content": _FALLBACK_LIMITE})
        return _FALLBACK_LIMITE

    def _complete_with_retry(self, messages: list[Message]):
        """Chama o provedor, tentando de novo apenas em falhas transitórias.

        Erros permanentes (autenticação/permissão/modelo inexistente — status
        401/403/404 nos SDKs) não são retentados: repetir uma chamada idêntica
        só multiplicaria requisições fadadas ao mesmo erro.
        """
        last_error: Exception | None = None
        for attempt in range(1, PROVIDER_ATTEMPTS + 1):
            try:
                return self._provider.complete(
                    system=self._system_prompt(),
                    messages=messages,
                    tools=self._tools.specs,
                )
            except Exception as exc:
                if getattr(exc, "status_code", None) in (401, 403, 404):
                    raise
                last_error = exc
                logger.warning(
                    "Falha no provedor (tentativa %d/%d): %s", attempt, PROVIDER_ATTEMPTS, exc
                )
                if attempt < PROVIDER_ATTEMPTS and self._retry_wait > 0:
                    time.sleep(self._retry_wait * attempt)
        assert last_error is not None
        raise last_error
