"""Cada tópico da camada de políticas devolve a seção certa do manual."""

from pathlib import Path

import pytest

from emporio_agent.policies import TOPICS, PolicyBook, get_store_info

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def book() -> PolicyBook:
    return PolicyBook(REPO_ROOT / "data" / "policies.md")


@pytest.mark.parametrize(
    ("topic", "expected_snippet"),
    [
        ("sobre_a_loja", "fundada em 2008"),
        ("horarios", "09:00 às 18:00"),
        ("pagamento", "5% de desconto"),
        ("trocas_e_devolucoes", "7 (sete) dias corridos"),
        ("frete_e_entregas", "R$ 35,00"),
        ("promocoes", "não são cumulativas"),
        ("atendimento", "informal mas profissional"),
        ("garantia", "(noventa) dias contra defeitos de fabricação"),
        ("privacidade", "LGPD"),
    ],
)
def test_topico_retorna_secao_correta(book: PolicyBook, topic: str, expected_snippet: str) -> None:
    assert expected_snippet in book.get_policy(topic)


def test_todas_as_secoes_do_manual_foram_parseadas(book: PolicyBook) -> None:
    # Manual tem seções 1 a 10; todas as mapeadas em TOPICS devem existir.
    for topic in TOPICS:
        assert book.get_policy(topic).startswith("## ")


def test_topico_desconhecido_lista_os_validos(book: PolicyBook) -> None:
    with pytest.raises(KeyError, match="horarios"):
        book.get_policy("astrologia")


def test_topico_e_tolerante_a_caixa(book: PolicyBook) -> None:
    assert book.get_policy("HORARIOS") == book.get_policy("horarios")


def test_store_info_aplica_assuncoes_do_readme() -> None:
    info = get_store_info()
    assert info["telefone_whatsapp"] == "(67) 3341-4444"  # AS-3
    assert info["email"] == "contato@emporiodamusica.com.br"  # AS-4 (sem acento)
    assert "Rua 14 de Maio, 3200" in info["endereco"]


def test_regra_critica_de_promocao_esta_no_texto(book: PolicyBook) -> None:
    """A regra que o agente mais precisa citar: PIX não desconta sobre promoção."""
    promo = book.get_policy("promocoes")
    assert "PIX (5%) não se aplica" in promo
