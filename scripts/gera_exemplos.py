"""Gera os exemplos de conversa de examples/ conversando com o agente REAL.

Uso: python -m uv run python scripts/gera_exemplos.py
Requer .env configurado. As transcrições registram o modelo usado e as
ferramentas consultadas em cada turno.
"""

from __future__ import annotations

import sys

from emporio_agent.agent import Agent
from emporio_agent.config import load_settings
from emporio_agent.db.build_db import DEFAULT_DB_PATH, build
from emporio_agent.db.repository import Repository
from emporio_agent.llm.provider import create_provider
from emporio_agent.paths import PROJECT_ROOT
from emporio_agent.policies import PolicyBook
from emporio_agent.tools import AgentTools

EXEMPLOS = [
    {
        "arquivo": "01_catalogo_violoes.md",
        "titulo": "Exemplo 1 — Busca no catálogo com filtro de preço",
        "demonstra": (
            "Consulta de catálogo com filtros (disponibilidade + preço máximo), exclusão"
            " de produto sem estoque e recomendação com desconto PIX calculado conforme"
            " a política."
        ),
        "turnos": [
            "Oi! Quais violões disponíveis vocês têm por até R$ 1.000?",
            "Qual desses você recomenda para um iniciante? Vou pagar no PIX.",
        ],
    },
    {
        "arquivo": "02_politica_devolucao.md",
        "titulo": "Exemplo 2 — Aplicação da política de trocas e devoluções",
        "demonstra": (
            "Pergunta sobre regra respondida consultando o manual (arrependimento em 7"
            " dias, defeito em 30 dias) antes de coletar qualquer dado do cliente."
        ),
        "turnos": [
            "Me arrependi de uma compra que fiz no site, posso devolver?",
            "E se o produto chegar com defeito, qual o prazo?",
        ],
    },
    {
        "arquivo": "03_pedido_com_verificacao.md",
        "titulo": "Exemplo 3 — Status de pedido com verificação de identidade (não trivial)",
        "demonstra": (
            "Cenário NÃO TRIVIAL: o agente se recusa a revelar dados do pedido sem"
            " verificação (LGPD), verifica a identidade quando o titular se apresenta,"
            " consulta o pedido em tempo real e explica o rastreamento pela política."
        ),
        "turnos": [
            "Qual o status do pedido 1?",
            "Claro! O pedido é o número 1 e eu sou o Pedro Henrique Oliveira.",
            "Perfeito, obrigado! E o que significa esse código de rastreio?",
        ],
    },
    {
        "arquivo": "04_promocao_expirada_sem_estoque.md",
        "titulo": "Exemplo 4 — Promoção expirada + produto sem estoque (não trivial)",
        "demonstra": (
            "Cenário NÃO TRIVIAL: o agente verifica a promoção no sistema, recusa com"
            " transparência um desconto expirado (nunca promete), constata a falta de"
            " estoque e aplica a política de sugerir alternativas disponíveis."
        ),
        "turnos": [
            "Vi que o violão Giannini GF-3D estava com 40% de desconto na Semana do"
            " Músico. Ainda consigo esse preço?",
            "Poxa. E esse Yamaha F310 que você sugeriu: tem promoção? Em quantas vezes"
            " consigo parcelar ele?",
        ],
    },
    {
        "arquivo": "05_escopo_e_redirecionamento.md",
        "titulo": "Exemplo 5 — Escopo da loja e assuntos fora do atendimento",
        "demonstra": (
            "Acessórios educadamente redirecionados (a loja só vende instrumentos) e"
            " assunto fora do escopo recusado com simpatia, trazendo a conversa de volta."
        ),
        "turnos": [
            "Vocês vendem cabo P10 e pedal de distorção?",
            "Beleza. Aproveitando que você é inteligente: resolve uma equação de física"
            " pra mim?",
        ],
    },
]


def main() -> None:
    settings = load_settings()
    if not DEFAULT_DB_PATH.exists():
        build(db_path=DEFAULT_DB_PATH)
    repository = Repository(DEFAULT_DB_PATH)
    tools = AgentTools(repository, PolicyBook())
    out_dir = PROJECT_ROOT / "examples"
    out_dir.mkdir(exist_ok=True)

    try:
        for exemplo in EXEMPLOS:
            agent = Agent(create_provider(settings), tools, retry_wait=2)
            lines = [
                f"# {exemplo['titulo']}",
                "",
                f"> **O que este exemplo demonstra:** {exemplo['demonstra']}",
                ">",
                f"> Transcrição real gerada por `scripts/gera_exemplos.py` com o agente"
                f" conectado a `{settings.provider}` / `{settings.model}`. As ferramentas"
                f" consultadas em cada turno estão anotadas.",
                "",
            ]
            for mensagem in exemplo["turnos"]:
                resposta = agent.send(mensagem)
                usadas = ", ".join(c.name for c in agent.last_tool_calls) or "nenhuma"
                lines += [
                    f"**🧑 Cliente:** {mensagem}",
                    "",
                    f"**🎸 Agente:** {resposta}",
                    "",
                    f"*`ferramentas consultadas: {usadas}`*",
                    "",
                    "---",
                    "",
                ]
            path = out_dir / exemplo["arquivo"]
            path.write_text("\n".join(lines), encoding="utf-8")
            print(f"gerado: {path.name}", flush=True)
    finally:
        repository.close()


if __name__ == "__main__":
    sys.exit(main())
