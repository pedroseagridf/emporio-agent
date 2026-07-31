"""Ponto de entrada do projeto.

Por enquanto exibe apenas o banner da loja; a interface de chat (CLI) será
conectada aqui na fase de interface.
"""

from emporio_agent import __version__

BANNER = r"""
=====================================================
   EMPORIO DA MUSICA - Atendimento Virtual  (v{v})
   "Sua musica comeca aqui."
=====================================================
""".strip("\n")


def main() -> None:
    print(BANNER.format(v=__version__))
    print("\nInterface de chat ainda nao conectada (em desenvolvimento).")


if __name__ == "__main__":
    main()
