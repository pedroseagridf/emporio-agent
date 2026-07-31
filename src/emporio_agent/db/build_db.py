"""Constrói a base SQLite a partir dos CSVs fornecidos pelo desafio.

Decisões de tratamento (detalhes em docs/data_notes.md):
- Os dados originais NÃO são alterados: inconsistências conhecidas (ex.: nome vs.
  descrição de produtos, total do pedido 3) são preservadas e resolvidas na camada
  de consulta/prompt, onde a decisão fica visível e testável.
- Colunas derivadas são adicionadas apenas para busca: ``search_text`` em produtos
  (nome + categoria + descrição, sem acentos) e ``name_norm``/``phone_digits`` em
  clientes, para verificação de identidade tolerante a grafia.
- Strings vazias em colunas opcionais (tracking, datas, notas) viram NULL.

Uso: ``python -m emporio_agent.db.build_db [--data-dir data] [--db data/emporio.sqlite3]``
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path

from emporio_agent.paths import DATA_DIR
from emporio_agent.text_utils import normalize, only_digits

CSV_PREFIX = "desafio_tecnico_ai_eng - "
DEFAULT_DATA_DIR = DATA_DIR
DEFAULT_DB_PATH = DATA_DIR / "emporio.sqlite3"

SCHEMA = """
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS promotions;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS categories;

CREATE TABLE categories (
    category_id INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT
);

CREATE TABLE products (
    product_id     INTEGER PRIMARY KEY,
    name           TEXT NOT NULL,
    category_id    INTEGER NOT NULL REFERENCES categories (category_id),
    price_brl      REAL NOT NULL,
    description    TEXT,
    stock_quantity INTEGER NOT NULL,
    status         TEXT NOT NULL CHECK (status IN ('active', 'discontinued', 'coming_soon')),
    specs          TEXT,
    created_at     TEXT,
    search_text    TEXT NOT NULL
);

CREATE TABLE customers (
    customer_id  INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    phone        TEXT,
    email        TEXT,
    city         TEXT,
    name_norm    TEXT NOT NULL,
    phone_digits TEXT
);

CREATE TABLE orders (
    order_id           INTEGER PRIMARY KEY,
    customer_id        INTEGER NOT NULL REFERENCES customers (customer_id),
    order_date         TEXT NOT NULL,
    status             TEXT NOT NULL
        CHECK (status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled')),
    total_brl          REAL NOT NULL,
    payment_method     TEXT,
    tracking_code      TEXT,
    estimated_delivery TEXT,
    notes              TEXT
);

CREATE TABLE order_items (
    order_id   INTEGER NOT NULL REFERENCES orders (order_id),
    product_id INTEGER NOT NULL REFERENCES products (product_id),
    quantity   INTEGER NOT NULL
);

CREATE TABLE promotions (
    promotion_id     INTEGER PRIMARY KEY,
    product_id       INTEGER NOT NULL REFERENCES products (product_id),
    discount_percent REAL NOT NULL,
    description      TEXT,
    is_active        INTEGER NOT NULL CHECK (is_active IN (0, 1))
);
"""


def _read_csv(data_dir: Path, table: str) -> list[dict[str, str]]:
    path = data_dir / f"{CSV_PREFIX}{table}.csv"
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _opt(value: str | None) -> str | None:
    """Converte string vazia em NULL."""
    value = (value or "").strip()
    return value or None


def build(data_dir: Path = DEFAULT_DATA_DIR, db_path: Path = DEFAULT_DB_PATH) -> dict[str, int]:
    """(Re)constrói a base a partir dos CSVs. Idempotente. Retorna contagem por tabela."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)

        categories = _read_csv(data_dir, "categories")
        conn.executemany(
            "INSERT INTO categories VALUES (:category_id, :name, :description)", categories
        )
        category_names = {int(c["category_id"]): c["name"] for c in categories}

        products = _read_csv(data_dir, "products")
        conn.executemany(
            "INSERT INTO products VALUES (:product_id, :name, :category_id, :price_brl,"
            " :description, :stock_quantity, :status, :specs, :created_at, :search_text)",
            [
                {
                    "product_id": int(p["product_id"]),
                    "name": p["name"],
                    "category_id": int(p["category_id"]),
                    "price_brl": float(p["price_brl"]),
                    "description": p["description"],
                    "stock_quantity": int(p["stock_quantity"]),
                    "status": p["status"],
                    "specs": _opt(p["specs"]),
                    "created_at": _opt(p["created_at"]),
                    "search_text": normalize(
                        f"{p['name']} {category_names[int(p['category_id'])]} {p['description']}"
                    ),
                }
                for p in products
            ],
        )

        conn.executemany(
            "INSERT INTO customers VALUES (:customer_id, :name, :phone, :email, :city,"
            " :name_norm, :phone_digits)",
            [
                {
                    "customer_id": int(c["customer_id"]),
                    "name": c["name"],
                    "phone": _opt(c["phone"]),
                    "email": _opt(c["email"]),
                    "city": _opt(c["city"]),
                    "name_norm": normalize(c["name"]),
                    "phone_digits": only_digits(c["phone"] or ""),
                }
                for c in _read_csv(data_dir, "customers")
            ],
        )

        conn.executemany(
            "INSERT INTO orders VALUES (:order_id, :customer_id, :order_date, :status,"
            " :total_brl, :payment_method, :tracking_code, :estimated_delivery, :notes)",
            [
                {
                    "order_id": int(o["order_id"]),
                    "customer_id": int(o["customer_id"]),
                    "order_date": o["order_date"],
                    "status": o["status"],
                    "total_brl": float(o["total_brl"]),
                    "payment_method": _opt(o["payment_method"]),
                    "tracking_code": _opt(o["tracking_code"]),
                    "estimated_delivery": _opt(o["estimated_delivery"]),
                    "notes": _opt(o["notes"]),
                }
                for o in _read_csv(data_dir, "orders")
            ],
        )

        conn.executemany(
            "INSERT INTO order_items (order_id, quantity, product_id)"
            " VALUES (:order_id, :quantity, :product_id)",
            _read_csv(data_dir, "order_items"),
        )

        conn.executemany(
            "INSERT INTO promotions VALUES (:promotion_id, :product_id, :discount_percent,"
            " :description, :is_active)",
            _read_csv(data_dir, "promotions"),
        )

        conn.commit()
        counts = {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608
            for table in (
                "categories",
                "products",
                "customers",
                "orders",
                "order_items",
                "promotions",
            )
        }
        return counts
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Constrói a base SQLite a partir dos CSVs.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()

    counts = build(args.data_dir, args.db)
    print(f"Base criada em {args.db}:")
    for table, count in counts.items():
        print(f"  {table}: {count} registros")


if __name__ == "__main__":
    main()
