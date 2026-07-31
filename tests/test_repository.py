"""Testes da camada de consultas, incluindo cada 'pegadinha' mapeada na auditoria
de dados (docs/data_notes.md)."""

import pytest

from emporio_agent.db.repository import IdentityVerificationError, Repository

# ------------------------------------------------------------------- produtos


def test_search_violao_ate_1000_em_estoque(repo: Repository) -> None:
    """Cenário sugerido no enunciado: 'violões disponíveis custando até R$ 1.000'."""
    results = repo.search_products(query="violão", max_price=1000, in_stock_only=True)
    ids = {p.product_id for p in results}
    assert 81 in ids  # Yamaha C40 (R$ 599,90, 12 em estoque)
    assert 96 not in ids  # ativo porém SEM estoque — não pode aparecer como disponível
    assert 113 not in ids  # descontinuado
    assert all(p.available for p in results)


def test_search_sem_filtro_de_estoque_inclui_produto_96(repo: Repository) -> None:
    ids = {p.product_id for p in repo.search_products(query="violão", max_price=1000, limit=30)}
    assert 96 in ids  # visível para o agente explicar a indisponibilidade


def test_produto_96_ativo_sem_estoque(repo: Repository) -> None:
    p = repo.get_product(product_id=96)
    assert p is not None
    assert p.status == "active"
    assert p.stock_quantity == 0
    assert not p.available


def test_produto_113_descontinuado_tem_alternativas(repo: Repository) -> None:
    p = repo.get_product(product_id=113)
    assert p is not None and p.status == "discontinued"
    similares = repo.get_similar_products(113)
    assert similares, "política §7.3: sempre sugerir alternativas disponíveis"
    assert all(s.available and s.category == "Violões" for s in similares)
    assert 113 not in {s.product_id for s in similares}


def test_get_product_por_nome_takamine_gd20(repo: Repository) -> None:
    """Cenário sugerido no enunciado: 'Quanto custa o Takamine GD20?'"""
    p = repo.get_product(name="Takamine GD20")
    assert p is not None
    assert p.product_id == 95
    assert p.price_brl == 2199


def test_busca_tolerante_a_acentos(repo: Repository) -> None:
    com_acento = {p.product_id for p in repo.search_products(query="violão")}
    sem_acento = {p.product_id for p in repo.search_products(query="violao")}
    assert com_acento == sem_acento != set()


def test_categoria_sem_produtos_retorna_vazio(repo: Repository) -> None:
    """Categorias 6, 7 e 8 (sopros e cordas orquestrais) existem mas não têm produtos."""
    assert repo.search_products(query="saxofone") == []
    assert repo.search_products(category="sopro") == []


# ------------------------------------------------------------------ promoções


def test_somente_4_promocoes_ativas(repo: Repository) -> None:
    ativas = repo.get_active_promotions()
    assert {p.product_id for p in ativas} == {127, 121, 90, 94}


def test_promocao_expirada_do_produto_96_nao_aparece(repo: Repository) -> None:
    """Existe uma promoção de 40% do produto 96 na base, porém is_active = 0.
    O agente nunca deve prometê-la (política §7.3)."""
    assert repo.get_active_promotions(product_id=96) == []


def test_promocao_ativa_calcula_preco_final_com_original(repo: Repository) -> None:
    (promo,) = repo.get_active_promotions(product_id=121)
    assert promo.discount_percent == 20
    assert promo.original_price_brl == 549
    assert promo.final_price_brl == 439.20  # sempre exibido junto do original + %


# -------------------------------------------------------------------- pedidos


def test_pedido_por_numero_com_nome_do_titular(repo: Repository) -> None:
    order = repo.get_order_status(1, "Pedro Henrique Oliveira")
    assert order is not None
    assert order.status == "delivered"
    assert order.tracking_code == "BRAB1234567BR"
    assert order.items[0].product_name.startswith("Martin D-28")


def test_pedido_aceita_subconjunto_do_nome(repo: Repository) -> None:
    assert repo.get_order_status(1, "pedro oliveira") is not None


def test_pedido_recusa_primeiro_nome_sozinho(repo: Repository) -> None:
    with pytest.raises(IdentityVerificationError):
        repo.get_order_status(1, "Pedro")


def test_pedido_recusa_nome_de_outra_pessoa(repo: Repository) -> None:
    with pytest.raises(IdentityVerificationError):
        repo.get_order_status(1, "Lucas Mendes da Silva")


def test_pedido_inexistente_retorna_none(repo: Repository) -> None:
    assert repo.get_order_status(999, "Pedro Henrique Oliveira") is None


def test_busca_de_pedidos_exige_contato(repo: Repository) -> None:
    """Nome sozinho é ambíguo (Bruno Carvalho Martins / Bruno Carvalho / Bruno
    Martins são clientes distintos) e insuficiente sob a LGPD (AS-2)."""
    with pytest.raises(IdentityVerificationError):
        repo.find_orders_by_customer("Bruno Carvalho Martins", contact="")


def test_busca_de_pedidos_por_nome_e_telefone(repo: Repository) -> None:
    orders = repo.find_orders_by_customer("Bruno Carvalho Martins", "(67) 98543-2109")
    assert [o.order_id for o in orders] == [10]


def test_busca_de_pedidos_por_nome_e_email(repo: Repository) -> None:
    orders = repo.find_orders_by_customer("Ana Carolina Ferreira", "anacarol.ferreira@coldmail.com")
    assert [o.order_id for o in orders] == [8]
    assert orders[0].status == "shipped"


def test_nome_nao_confere_com_o_dono_do_contato_falha(repo: Repository) -> None:
    """O telefone do homônimo 'Bruno Carvalho' (27) não libera os pedidos de
    'Bruno Carvalho Martins' (11) — o nome informado deve conferir com o
    cadastro dono do contato."""
    with pytest.raises(IdentityVerificationError):
        repo.find_orders_by_customer("Bruno Carvalho Martins", "(67) 99999-0000")


def test_pedido_expoe_apenas_primeiro_nome_do_cliente(repo: Repository) -> None:
    """O objeto Order não carrega telefone/e-mail/nome completo do cliente —
    minimização de dados (LGPD §9)."""
    order = repo.get_order_status(1, "Pedro Henrique Oliveira")
    assert order is not None
    assert order.customer_first_name == "Pedro"
    assert not hasattr(order, "customer_email")
    assert not hasattr(order, "customer_phone")
