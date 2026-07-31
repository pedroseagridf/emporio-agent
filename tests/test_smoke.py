"""Teste de fumaça: o pacote importa e a interface expõe banner e comandos."""

from emporio_agent import __version__
from emporio_agent.cli import AJUDA, BANNER


def test_version() -> None:
    assert __version__


def test_banner_e_ajuda() -> None:
    assert "EMPÓRIO DA MÚSICA" in BANNER
    assert __version__ in BANNER
    for command in ("/reset", "/ajuda", "/sair"):
        assert command in AJUDA
