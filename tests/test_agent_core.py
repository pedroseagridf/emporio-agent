"""Loop do agente testado com um provedor fake — sem chamadas de API."""

from datetime import datetime
from pathlib import Path

import pytest

from emporio_agent.agent import Agent
from emporio_agent.db.repository import Repository
from emporio_agent.llm.provider import LLMReply, Message, ToolCall, ToolSpec
from emporio_agent.policies import PolicyBook
from emporio_agent.tools import AgentTools

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXED_NOW = datetime(2026, 7, 29, 14, 30)  # quarta-feira, horário comercial


class FakeProvider:
    """Devolve respostas roteirizadas e grava cada requisição recebida."""

    def __init__(self, *replies: LLMReply | Exception) -> None:
        self._replies = list(replies)
        self.requests: list[dict] = []

    def complete(
        self, system: str, messages: list[Message], tools: list[ToolSpec]
    ) -> LLMReply:
        self.requests.append(
            {"system": system, "messages": [dict(m) for m in messages], "tools": tools}
        )
        reply = self._replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


@pytest.fixture()
def tools(repo: Repository) -> AgentTools:
    return AgentTools(repo, PolicyBook(REPO_ROOT / "data" / "policies.md"))


def _agent(tools: AgentTools, *replies: LLMReply | Exception) -> tuple[Agent, FakeProvider]:
    provider = FakeProvider(*replies)
    agent = Agent(provider, tools, clock=lambda: FIXED_NOW)
    return agent, provider


def test_resposta_direta_sem_ferramentas(tools: AgentTools) -> None:
    agent, provider = _agent(tools, LLMReply(text="Olá! Como posso ajudar? 🎸"))
    answer = agent.send("oi")
    assert answer == "Olá! Como posso ajudar? 🎸"
    assert [m["role"] for m in agent.history] == ["user", "assistant"]
    assert agent.last_tool_calls == []
    # O system prompt renderiza a data em PT-BR e contém as regras centrais.
    system = provider.requests[0]["system"]
    assert "quarta-feira, 29/07/2026" in system
    assert "Empório da Música" in system
    assert "NUNCA afirme preço" in system


def test_fluxo_com_ferramenta_e_resultado_de_volta(tools: AgentTools) -> None:
    agent, provider = _agent(
        tools,
        LLMReply(text=None, tool_calls=(ToolCall("t1", "dados_da_loja", {}),)),
        LLMReply(text="Estamos na Rua 14 de Maio, 3200 — Centro!"),
    )
    answer = agent.send("qual o endereço?")
    assert "Rua 14 de Maio" in answer
    assert [c.name for c in agent.last_tool_calls] == ["dados_da_loja"]
    # A segunda requisição precisa conter o resultado da ferramenta.
    second = provider.requests[1]["messages"]
    tool_msgs = [m for m in second if m["role"] == "tool"]
    assert len(tool_msgs) == 1
    assert "(67) 3341-4444" in tool_msgs[0]["content"]
    # Histórico final: user -> assistant(tool_calls) -> tool -> assistant.
    assert [m["role"] for m in agent.history] == ["user", "assistant", "tool", "assistant"]


def test_chamadas_paralelas_geram_um_resultado_por_chamada(tools: AgentTools) -> None:
    agent, provider = _agent(
        tools,
        LLMReply(
            text=None,
            tool_calls=(
                ToolCall("t1", "dados_da_loja", {}),
                ToolCall("t2", "listar_promocoes_ativas", {}),
            ),
        ),
        LLMReply(text="Prontinho!"),
    )
    agent.send("endereço e promoções?")
    tool_msgs = [m for m in provider.requests[1]["messages"] if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in tool_msgs] == ["t1", "t2"]


def test_ferramenta_desconhecida_vira_erro_para_o_modelo(tools: AgentTools) -> None:
    agent, provider = _agent(
        tools,
        LLMReply(text=None, tool_calls=(ToolCall("t1", "hackear_sistema", {}),)),
        LLMReply(text="Não consigo com isso, mas posso ajudar com instrumentos!"),
    )
    agent.send("faz algo estranho")
    tool_msg = next(m for m in provider.requests[1]["messages"] if m["role"] == "tool")
    assert "erro" in tool_msg["content"]


def test_limite_de_rodadas_devolve_fallback(tools: AgentTools) -> None:
    loop_reply = LLMReply(text=None, tool_calls=(ToolCall("t", "dados_da_loja", {}),))
    agent, _ = _agent(tools, *[loop_reply] * 8)
    answer = agent.send("oi")
    assert "atendente" in answer  # fallback oferece encaminhar para humano


def test_falha_transitoria_recupera_com_retry(tools: AgentTools) -> None:
    """Erro estocástico do provedor (ex.: tool_use_failed na Groq) → nova tentativa."""
    agent, provider = _agent(
        tools, RuntimeError("tool_use_failed"), LLMReply(text="Deu certo na segunda!")
    )
    assert agent.send("oi") == "Deu certo na segunda!"
    assert len(provider.requests) == 2


def test_erro_persistente_devolve_mensagem_amigavel(tools: AgentTools) -> None:
    falhas = [RuntimeError("api fora do ar")] * 3  # PROVIDER_ATTEMPTS
    agent, _ = _agent(tools, *falhas)
    answer = agent.send("oi")
    assert "atendente" in answer
    # A conversa não fica poluída com a falha: só a mensagem do usuário permanece.
    assert [m["role"] for m in agent.history] == ["user"]


def test_reset_limpa_a_conversa(tools: AgentTools) -> None:
    agent, _ = _agent(tools, LLMReply(text="oi!"), LLMReply(text="de novo!"))
    agent.send("olá")
    agent.reset()
    assert agent.history == []
    agent.send("olá de novo")
    assert len(agent.history) == 2
