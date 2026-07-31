"""As ferramentas expostas ao modelo devolvem JSON correto e tratam erros de negócio."""

import json
from pathlib import Path

import pytest

from emporio_agent.db.repository import Repository
from emporio_agent.policies import PolicyBook
from emporio_agent.tools import TOOL_SPECS, AgentTools

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def tools(repo: Repository) -> AgentTools:
    return AgentTools(repo, PolicyBook(REPO_ROOT / "data" / "policies.md"))


def _run(tools: AgentTools, name: str, **args) -> dict | list:
    return json.loads(tools.execute(name, args))


def test_specs_tem_schema_valido() -> None:
    for spec in TOOL_SPECS:
        assert spec["name"] and spec["description"]
        assert spec["input_schema"]["type"] == "object"


def test_buscar_produtos_disponiveis_ate_1000(tools: AgentTools) -> None:
    result = _run(tools, "buscar_produtos", termo="violão", preco_maximo=1000,
                  apenas_disponiveis=True)
    ids = {p["id"] for p in result}
    assert 81 in ids and 96 not in ids
    assert all(p["disponivel"] for p in result)
    assert all(p["preco_formatado"].startswith("R$ ") for p in result)


def test_detalhar_produto_por_nome(tools: AgentTools) -> None:
    result = _run(tools, "detalhar_produto", nome="Takamine GD20")
    assert result["id"] == 95
    assert result["preco_formatado"] == "R$ 2.199,00"


def test_detalhar_produto_inexistente(tools: AgentTools) -> None:
    assert "erro" in _run(tools, "detalhar_produto", nome="Stradivarius 1700")


def test_promocoes_ativas_com_precos_formatados(tools: AgentTools) -> None:
    result = _run(tools, "listar_promocoes_ativas")
    assert {p["produto_id"] for p in result} == {127, 121, 90, 94}
    promo_121 = next(p for p in result if p["produto_id"] == 121)
    assert promo_121["preco_original"] == "R$ 549,00"
    assert promo_121["preco_promocional"] == "R$ 439,20"


def test_promocao_expirada_nao_aparece(tools: AgentTools) -> None:
    assert _run(tools, "listar_promocoes_ativas", produto_id=96) == []


def test_consultar_pedido_ok(tools: AgentTools) -> None:
    result = _run(tools, "consultar_pedido", numero_pedido=1,
                  nome_cliente="Pedro Henrique Oliveira")
    assert result["status_descricao"] == "entregue"
    assert result["codigo_rastreio"] == "BRAB1234567BR"
    assert result["itens"][0]["produto"].startswith("Martin")


def test_consultar_pedido_identidade_insuficiente(tools: AgentTools) -> None:
    result = _run(tools, "consultar_pedido", numero_pedido=1, nome_cliente="Pedro")
    assert "erro" in result and "nome" in result["erro"].casefold()


def test_buscar_pedidos_sem_contato_valido(tools: AgentTools) -> None:
    result = _run(tools, "buscar_pedidos_por_cliente",
                  nome_completo="Bruno Carvalho Martins", contato="123")
    assert "erro" in result


def test_consultar_politica(tools: AgentTools) -> None:
    result = _run(tools, "consultar_politica", topico="horarios")
    assert "09:00 às 18:00" in result["secao_do_manual"]


def test_consultar_politica_topico_invalido_lista_validos(tools: AgentTools) -> None:
    result = _run(tools, "consultar_politica", topico="astrologia")
    assert "erro" in result and "horarios" in result["erro"]


def test_dados_da_loja_aplica_assuncoes(tools: AgentTools) -> None:
    result = _run(tools, "dados_da_loja")
    assert result["telefone_whatsapp"] == "(67) 3341-4444"
    assert result["email"] == "contato@emporiodamusica.com.br"


def test_ferramenta_desconhecida(tools: AgentTools) -> None:
    assert "erro" in _run(tools, "abrir_cofre")
