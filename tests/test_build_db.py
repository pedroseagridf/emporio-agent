"""A base é construída fielmente a partir dos CSVs (sem alterar os dados originais)."""

import sqlite3
from pathlib import Path

from emporio_agent.db.build_db import build

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_row_counts(tmp_path: Path) -> None:
    counts = build(data_dir=REPO_ROOT / "data", db_path=tmp_path / "db.sqlite3")
    assert counts == {
        "categories": 9,
        "products": 65,
        "customers": 50,
        "orders": 20,
        "order_items": 22,
        "promotions": 25,
    }


def test_build_is_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "db.sqlite3"
    build(data_dir=REPO_ROOT / "data", db_path=db)
    counts = build(data_dir=REPO_ROOT / "data", db_path=db)  # segunda execução
    assert counts["products"] == 65


def test_empty_strings_become_null(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    # Pedido 9 (confirmed) ainda não tem rastreio nem previsão de entrega.
    row = conn.execute(
        "SELECT tracking_code, estimated_delivery FROM orders WHERE order_id = 9"
    ).fetchone()
    assert row == (None, None)


def test_order_3_total_mismatch_is_preserved(db_path: Path) -> None:
    """Inconsistência conhecida do dado original: o total gravado do pedido 3
    (R$ 3.450) difere da soma dos itens (2 × R$ 1.749 = R$ 3.498). Decisão:
    preservar o dado e tratar o total gravado como fonte de verdade do pedido."""
    conn = sqlite3.connect(db_path)
    total, item_sum = conn.execute(
        """SELECT o.total_brl, SUM(oi.quantity * p.price_brl)
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.order_id
        JOIN products p ON p.product_id = oi.product_id
        WHERE o.order_id = 3"""
    ).fetchone()
    assert total == 3450
    assert item_sum == 3498
