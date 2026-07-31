"""Consultas tipadas sobre a base SQLite — a única porta de acesso do agente aos dados.

Regras de negócio embutidas aqui (e não no prompt) para serem testáveis:
- Promoções: apenas ``is_active = 1`` são retornadas; preço final é calculado e
  sempre acompanhado do preço original e do percentual (política §6.2).
- Pedidos: dados só são retornados com verificação leve de identidade (AS-2 do
  README) — nº do pedido + nome do titular, ou nome + telefone/e-mail cadastrados.
- Alternativas: produtos similares são da mesma categoria, ativos e com estoque
  (política §7.3 — sugerir alternativas quando indisponível).

Somente SQL parametrizado; nenhuma query recebe texto do usuário por interpolação.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from emporio_agent.db.build_db import DEFAULT_DB_PATH
from emporio_agent.text_utils import normalize, only_digits


class IdentityVerificationError(Exception):
    """Verificação de identidade insuficiente ou divergente para consultar um pedido."""


#: Mensagem única para pedido inexistente OU nome divergente: respostas distintas
#: permitiriam enumerar quais números de pedido existem (achado #3 da revisão).
ORDER_LOOKUP_FAILED = (
    "Não localizei um pedido com esse número e esse titular. Confira o número do"
    " pedido e o nome completo usado na compra (ou peça nome + telefone/e-mail"
    " cadastrados para buscar os pedidos do cliente)."
)

#: Partículas que não contam como sobrenome na verificação de identidade
#: (achado #1 da revisão: "da Silva" não pode valer por "nome + sobrenome").
_PARTICULAS = {"da", "de", "do", "das", "dos", "e"}


@dataclass(frozen=True)
class Product:
    product_id: int
    name: str
    category: str
    price_brl: float
    stock_quantity: int
    status: str
    description: str
    specs: dict[str, str] = field(default_factory=dict)

    @property
    def available(self) -> bool:
        return self.status == "active" and self.stock_quantity > 0


@dataclass(frozen=True)
class Promotion:
    promotion_id: int
    product_id: int
    product_name: str
    description: str
    discount_percent: float
    original_price_brl: float
    final_price_brl: float


@dataclass(frozen=True)
class OrderItem:
    product_id: int
    product_name: str
    quantity: int
    unit_price_brl: float


@dataclass(frozen=True)
class Order:
    order_id: int
    customer_first_name: str
    order_date: str
    status: str
    total_brl: float
    payment_method: str | None
    tracking_code: str | None
    estimated_delivery: str | None
    notes: str | None
    items: tuple[OrderItem, ...]


def _row_to_product(row: sqlite3.Row) -> Product:
    return Product(
        product_id=row["product_id"],
        name=row["name"],
        category=row["category"],
        price_brl=row["price_brl"],
        stock_quantity=row["stock_quantity"],
        status=row["status"],
        description=row["description"],
        specs=json.loads(row["specs"]) if row["specs"] else {},
    )


def _name_tokens_match(informed: str, registered: str) -> bool:
    """Nome informado confere se todos os seus termos constam do nome cadastrado.

    Exige ao menos 2 termos significativos (nome + sobrenome, descontando
    partículas como "da"/"de") para evitar liberar dados com um primeiro nome
    apenas — decisão AS-2 (LGPD + nomes quase duplicados na base).
    """
    informed_tokens = set(normalize(informed).split())
    significant = informed_tokens - _PARTICULAS
    return len(significant) >= 2 and informed_tokens <= set(normalize(registered).split())


class Repository:
    """Fachada de leitura sobre a base SQLite gerada por ``build_db``."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        if not Path(db_path).exists():
            raise FileNotFoundError(
                f"Base {db_path} não encontrada. Rode: python -m emporio_agent.db.build_db"
            )
        self._conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------ produtos

    _PRODUCT_SELECT = (
        "SELECT p.product_id, p.name, c.name AS category, p.price_brl, p.stock_quantity,"
        " p.status, p.description, p.specs"
        " FROM products p JOIN categories c ON c.category_id = p.category_id"
    )

    def search_products(
        self,
        query: str | None = None,
        category: str | None = None,
        max_price: float | None = None,
        min_price: float | None = None,
        in_stock_only: bool = False,
        limit: int = 10,
    ) -> list[Product]:
        """Busca produtos por texto livre (sem acentos), categoria e faixa de preço."""
        sql = [self._PRODUCT_SELECT, "WHERE 1=1"]
        params: list[object] = []
        for term in normalize(query or "").split():
            # Escape de curingas: sem isso, buscar "%" devolveria o catálogo inteiro.
            escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            sql.append("AND p.search_text LIKE ? ESCAPE '\\'")
            params.append(f"%{escaped}%")
        if category:
            # Resolvido em Python: LOWER() do SQLite não normaliza acentos ('Violões').
            cat_norm = normalize(category)
            cat_ids = [
                row["category_id"]
                for row in self._conn.execute("SELECT category_id, name FROM categories")
                if cat_norm in normalize(row["name"]) or normalize(row["name"]) in cat_norm
            ]
            if not cat_ids:
                return []
            sql.append(f"AND p.category_id IN ({','.join('?' * len(cat_ids))})")
            params.extend(cat_ids)
        if max_price is not None:
            sql.append("AND p.price_brl <= ?")
            params.append(max_price)
        if min_price is not None:
            sql.append("AND p.price_brl >= ?")
            params.append(min_price)
        if in_stock_only:
            sql.append("AND p.status = 'active' AND p.stock_quantity > 0")
        sql.append("ORDER BY p.price_brl LIMIT ?")
        params.append(max(1, min(limit, 50)))  # LIMIT negativo no SQLite = sem limite
        rows = self._conn.execute(" ".join(sql), params).fetchall()
        return [_row_to_product(r) for r in rows]

    def get_product(
        self, product_id: int | None = None, name: str | None = None
    ) -> Product | None:
        """Localiza um produto por id ou pelo melhor casamento de nome."""
        if product_id is not None:
            row = self._conn.execute(
                f"{self._PRODUCT_SELECT} WHERE p.product_id = ?", (product_id,)
            ).fetchone()
            return _row_to_product(row) if row else None
        if name:
            matches = self.search_products(query=name, limit=1)
            return matches[0] if matches else None
        return None

    def get_similar_products(self, product_id: int, limit: int = 3) -> list[Product]:
        """Alternativas disponíveis (ativas, com estoque) da mesma categoria,
        ordenadas pela proximidade de preço — apoio à política §7.3."""
        rows = self._conn.execute(
            f"""{self._PRODUCT_SELECT}
            WHERE p.category_id = (SELECT category_id FROM products WHERE product_id = ?)
              AND p.product_id != ? AND p.status = 'active' AND p.stock_quantity > 0
            ORDER BY ABS(
                p.price_brl - (SELECT price_brl FROM products WHERE product_id = ?)
            ) LIMIT ?""",
            (product_id, product_id, product_id, limit),
        ).fetchall()
        return [_row_to_product(r) for r in rows]

    # ----------------------------------------------------------------- promoções

    def get_active_promotions(self, product_id: int | None = None) -> list[Promotion]:
        """Somente promoções vigentes (``is_active = 1``), já com o preço final
        calculado ao lado do original e do percentual (política §6.2)."""
        sql = (
            "SELECT pr.promotion_id, pr.product_id, p.name AS product_name, pr.description,"
            " pr.discount_percent, p.price_brl"
            " FROM promotions pr JOIN products p ON p.product_id = pr.product_id"
            " WHERE pr.is_active = 1"
        )
        params: tuple[object, ...] = ()
        if product_id is not None:
            sql += " AND pr.product_id = ?"
            params = (product_id,)
        return [
            Promotion(
                promotion_id=r["promotion_id"],
                product_id=r["product_id"],
                product_name=r["product_name"],
                description=r["description"],
                discount_percent=r["discount_percent"],
                original_price_brl=r["price_brl"],
                final_price_brl=round(r["price_brl"] * (1 - r["discount_percent"] / 100), 2),
            )
            for r in self._conn.execute(sql, params).fetchall()
        ]

    # ------------------------------------------------------------------- pedidos

    def _load_order(self, row: sqlite3.Row) -> Order:
        items = self._conn.execute(
            "SELECT oi.product_id, p.name AS product_name, oi.quantity, p.price_brl"
            " FROM order_items oi JOIN products p ON p.product_id = oi.product_id"
            " WHERE oi.order_id = ?",
            (row["order_id"],),
        ).fetchall()
        return Order(
            order_id=row["order_id"],
            customer_first_name=row["customer_name"].split()[0],
            order_date=row["order_date"],
            status=row["status"],
            total_brl=row["total_brl"],
            payment_method=row["payment_method"],
            tracking_code=row["tracking_code"],
            estimated_delivery=row["estimated_delivery"],
            notes=row["notes"],
            items=tuple(
                OrderItem(
                    product_id=i["product_id"],
                    product_name=i["product_name"],
                    quantity=i["quantity"],
                    unit_price_brl=i["price_brl"],
                )
                for i in items
            ),
        )

    _ORDER_SELECT = (
        "SELECT o.*, c.name AS customer_name FROM orders o"
        " JOIN customers c ON c.customer_id = o.customer_id"
    )

    def get_order_status(self, order_id: int, customer_name: str) -> Order:
        """Consulta um pedido pelo número, verificando que o nome informado
        (nome + sobrenome) confere com o titular.

        Pedido inexistente e nome divergente levantam o MESMO erro com a MESMA
        mensagem (``ORDER_LOOKUP_FAILED``) para não permitir enumeração de pedidos.
        """
        row = self._conn.execute(
            f"{self._ORDER_SELECT} WHERE o.order_id = ?", (order_id,)
        ).fetchone()
        if row is None or not _name_tokens_match(customer_name, row["customer_name"]):
            raise IdentityVerificationError(ORDER_LOOKUP_FAILED)
        return self._load_order(row)

    def find_orders_by_customer(self, name: str, contact: str) -> list[Order]:
        """Localiza pedidos pelo nome + um contato cadastrado (telefone ou e-mail).

        O contato é obrigatório: nome sozinho é ambíguo na base (clientes homônimos)
        e insuficiente sob a LGPD (AS-2).
        """
        contact = contact.strip()
        digits = only_digits(contact)
        if "@" in contact:
            rows = self._conn.execute(
                "SELECT * FROM customers WHERE LOWER(email) = ?", (contact.casefold(),)
            ).fetchall()
        elif len(digits) >= 8:
            # Últimos 11 dígitos: tolera DDI na frente ("+55 (67) 9..." — padrão WhatsApp).
            rows = self._conn.execute(
                "SELECT * FROM customers WHERE phone_digits LIKE ?", (f"%{digits[-11:]}",)
            ).fetchall()
        else:
            raise IdentityVerificationError(
                "Para localizar pedidos preciso de um contato cadastrado: telefone"
                " (com DDD) ou e-mail, junto com o nome completo."
            )
        matches = [r for r in rows if _name_tokens_match(name, r["name"])]
        if not matches:
            raise IdentityVerificationError(
                "Não encontrei cadastro com esse nome e contato. Confira se o telefone/e-mail"
                " é o mesmo usado na compra e informe o nome completo."
            )
        order_rows = self._conn.execute(
            f"{self._ORDER_SELECT} WHERE o.customer_id IN"
            f" ({','.join('?' * len(matches))}) ORDER BY o.order_date DESC",
            [m["customer_id"] for m in matches],
        ).fetchall()
        return [self._load_order(r) for r in order_rows]
