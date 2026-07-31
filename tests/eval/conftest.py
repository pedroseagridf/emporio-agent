"""Infraestrutura da suíte comportamental (P09).

Roda o agente REAL contra o provedor configurado no .env. Sem chave configurada,
a suíte inteira é pulada — a suíte unitária continua rodando sem custo algum.
Ao final da execução, gera docs/eval_results.md com a tabela caso → ferramentas
chamadas → resultado.
"""

from __future__ import annotations

import time

import pytest

from emporio_agent.agent import Agent
from emporio_agent.config import ConfigError, load_settings
from emporio_agent.db.build_db import DEFAULT_DB_PATH, build
from emporio_agent.db.repository import Repository
from emporio_agent.llm.provider import create_provider
from emporio_agent.paths import PROJECT_ROOT
from emporio_agent.policies import PolicyBook
from emporio_agent.tools import AgentTools

RESULTS: list[dict] = []
META: dict = {}


@pytest.fixture(scope="session")
def live_provider():
    try:
        settings = load_settings()
    except ConfigError as exc:
        pytest.skip(f"suíte comportamental requer chave de API configurada ({exc})")
    META["provedor"] = settings.provider
    META["modelo"] = settings.model
    return create_provider(settings)


@pytest.fixture(scope="session")
def live_tools():
    if not DEFAULT_DB_PATH.exists():
        build(db_path=DEFAULT_DB_PATH)
    repository = Repository(DEFAULT_DB_PATH)
    yield AgentTools(repository, PolicyBook())
    repository.close()


@pytest.fixture()
def agent(live_provider, live_tools) -> Agent:
    time.sleep(2)  # cortesia com o rate limit da camada gratuita
    return Agent(live_provider, live_tools, retry_wait=2)


@pytest.fixture()
def registrar(request):
    """Registra o caso ANTES das asserções, para o relatório incluir falhas."""

    def _registrar(caso: str, pergunta: str, ferramentas: list[str]) -> None:
        request.node._eval_row = {
            "caso": caso,
            "pergunta": pergunta,
            "ferramentas": ", ".join(ferramentas) if ferramentas else "—",
        }

    return _registrar


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and hasattr(item, "_eval_row"):
        RESULTS.append({**item._eval_row, "passou": report.passed})


def pytest_sessionfinish(session, exitstatus):
    if not RESULTS:
        return
    total = len(RESULTS)
    ok = sum(1 for r in RESULTS if r["passou"])
    lines = [
        "# Resultados da suíte comportamental (P09)",
        "",
        f"Gerado automaticamente pela última execução de `pytest tests/eval`"
        f" — provedor `{META.get('provedor', '?')}`, modelo `{META.get('modelo', '?')}`.",
        f"As asserções verificam ferramentas chamadas e fatos-chave, nunca texto exato."
        f" Resultado: **{ok}/{total}**.",
        "",
        "| Caso | Pergunta | Ferramentas chamadas | Resultado |",
        "|---|---|---|---|",
    ]
    lines.extend(
        f"| {r['caso']} | {r['pergunta']} | {r['ferramentas']} |"
        f" {'✅' if r['passou'] else '❌'} |"
        for r in RESULTS
    )
    out = PROJECT_ROOT / "docs" / "eval_results.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
