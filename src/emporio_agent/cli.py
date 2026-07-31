"""Interface de chat no terminal (rich) — a superfície de interação do protótipo.

Simula o canal de mensagens de texto (estilo WhatsApp) no terminal. Deve ser
executada a partir da raiz do repositório (os caminhos de dados são relativos).
Se a base SQLite ainda não existir, ela é construída automaticamente.
"""

from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from emporio_agent import __version__
from emporio_agent.agent import Agent
from emporio_agent.config import ConfigError, Settings, load_settings
from emporio_agent.db.build_db import DEFAULT_DB_PATH, build
from emporio_agent.db.repository import Repository
from emporio_agent.llm.provider import create_provider
from emporio_agent.policies import PolicyBook
from emporio_agent.tools import AgentTools

BANNER = f"""[bold magenta]EMPÓRIO DA MÚSICA[/] — Atendimento Virtual  [dim]v{__version__}[/]
[italic]"Sua música começa aqui."[/]"""

AJUDA = """[bold]Comandos:[/]
  [cyan]/reset[/]  — começa uma conversa do zero
  [cyan]/ajuda[/]  — mostra esta mensagem
  [cyan]/sair[/]   — encerra o atendimento (Ctrl+C também funciona)"""

DESPEDIDA = "Até logo! Sua música começa aqui. 🎶"


def _bootstrap(console: Console) -> tuple[Agent, Settings, Repository]:
    """Carrega configuração, garante a base construída e monta o agente."""
    settings = load_settings()
    if not DEFAULT_DB_PATH.exists():
        console.print("[dim]Base de dados ainda não existe — construindo a partir dos CSVs…[/]")
        build(db_path=DEFAULT_DB_PATH)
    repository = Repository(DEFAULT_DB_PATH)
    tools = AgentTools(repository, PolicyBook())
    return Agent(create_provider(settings), tools), settings, repository


def main() -> None:
    console = Console()
    console.print(Panel(BANNER, border_style="magenta", expand=False))

    try:
        agent, settings, repository = _bootstrap(console)
    except (ConfigError, FileNotFoundError) as exc:
        console.print(f"[bold red]Erro de configuração:[/] {exc}")
        raise SystemExit(1) from exc

    console.print(f"[dim]provedor: {settings.provider} · modelo: {settings.model}[/]")
    console.print(AJUDA)
    console.print()

    try:
        _chat_loop(console, agent)
    finally:
        repository.close()


def _chat_loop(console: Console, agent: Agent) -> None:
    while True:
        try:
            text = console.input("[bold cyan]você ›[/] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print(f"\n{DESPEDIDA}")
            break

        if not text:
            continue
        command = text.casefold()
        if command in ("/sair", "/exit", "/quit"):
            console.print(DESPEDIDA)
            break
        if command == "/reset":
            agent.reset()
            console.print("[dim]Conversa reiniciada.[/]\n")
            continue
        if command == "/ajuda":
            console.print(AJUDA)
            continue

        with console.status("[dim]consultando…[/]", spinner="dots"):
            answer = agent.send(text)
        console.print(
            Panel(
                Markdown(answer),
                title="🎸 Empório da Música",
                title_align="left",
                border_style="magenta",
            )
        )
        if agent.last_tool_calls:
            used = ", ".join(call.name for call in agent.last_tool_calls)
            console.print(f"[dim]ferramentas consultadas: {used}[/]")
        console.print()


if __name__ == "__main__":
    main()
