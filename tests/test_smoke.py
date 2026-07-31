"""Teste de fumaça: o pacote importa e o entrypoint executa sem erro."""

from emporio_agent import __version__
from emporio_agent.__main__ import main


def test_version() -> None:
    assert __version__


def test_entrypoint_runs(capsys) -> None:
    main()
    out = capsys.readouterr().out
    assert "EMPORIO DA MUSICA" in out
