"""Camada de conhecimento de políticas da loja.

O manual (8 páginas, ~4 mil tokens) é pequeno demais para justificar embeddings +
vector store: a consulta é feita por seção numerada, com o texto devolvido íntegro
para o modelo fundamentar a resposta. A decisão (e quando ela deixaria de valer)
está registrada em docs/planning/02_execution_plan.md.

``get_store_info`` devolve os dados cadastrais já com as interpretações AS-3 e AS-4
do README aplicadas (conflito de telefones e e-mail com acento do PDF original).
"""

from __future__ import annotations

import re
from pathlib import Path

DEFAULT_POLICIES_PATH = Path("data") / "policies.md"

#: tópico exposto ao agente -> (número da seção no manual, descrição curta)
TOPICS: dict[str, tuple[str, str]] = {
    "sobre_a_loja": ("1", "história, missão e dados cadastrais da empresa"),
    "horarios": ("2", "horário de funcionamento da loja e do WhatsApp"),
    "pagamento": ("3", "formas de pagamento, desconto PIX e regras de parcelamento"),
    "trocas_e_devolucoes": ("4", "arrependimento, defeito, preferência e itens não elegíveis"),
    "frete_e_entregas": ("5", "valores, prazos, transportadoras e rastreamento"),
    "promocoes": ("6", "campanhas do ano e regras de descontos (não cumulativos)"),
    "atendimento": ("7", "tom de voz, fluxo padrão e situações especiais"),
    "garantia": ("8", "garantia legal, do fabricante e o que não é coberto"),
    "privacidade": ("9", "LGPD e uso de dados pessoais"),
}


class PolicyBook:
    """Acesso por tópico às seções do manual de políticas."""

    def __init__(self, path: Path = DEFAULT_POLICIES_PATH) -> None:
        if not Path(path).exists():
            raise FileNotFoundError(f"Manual de políticas não encontrado em {path}.")
        self._sections = self._parse(Path(path).read_text(encoding="utf-8"))

    @staticmethod
    def _parse(markdown: str) -> dict[str, str]:
        """Divide o markdown nas seções de nível 2 ('## N. Título')."""
        sections: dict[str, str] = {}
        for match in re.finditer(
            r"^## (\d+)\. .*?(?=^## \d+\. |\Z)", markdown, flags=re.MULTILINE | re.DOTALL
        ):
            sections[match.group(1)] = match.group(0).strip()
        return sections

    def get_policy(self, topic: str) -> str:
        """Retorna o texto integral da seção do manual referente ao tópico."""
        key = topic.strip().casefold()
        if key not in TOPICS:
            valid = ", ".join(sorted(TOPICS))
            raise KeyError(f"Tópico desconhecido: {topic!r}. Tópicos válidos: {valid}.")
        section_number, _ = TOPICS[key]
        return self._sections[section_number]

    def topics(self) -> dict[str, str]:
        """Tópicos disponíveis com descrição curta (usado na definição da ferramenta)."""
        return {topic: description for topic, (_, description) in TOPICS.items()}


def get_store_info() -> dict[str, str]:
    """Dados cadastrais consolidados da loja, com AS-3 e AS-4 aplicadas."""
    return {
        "nome": "Empório da Música",
        "slogan": "Sua música começa aqui.",
        "endereco": "Rua 14 de Maio, 3200 — Centro, Campo Grande - MS, CEP 79202-333",
        "telefone_whatsapp": "(67) 3341-4444",
        "email": "contato@emporiodamusica.com.br",
        "fundacao": "2008",
        "horario_semana": "segunda a sexta, das 09:00 às 18:00",
        "horario_sabado": "sábado, das 09:00 às 13:00",
        "horario_domingo_feriados": "fechado",
    }
