"""Utilitários de texto e formatação em PT-BR usados em toda a aplicação."""

from __future__ import annotations

import unicodedata
from datetime import datetime

_DIAS_SEMANA = (
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
)

_STATUS_PEDIDO = {
    "pending": "aguardando confirmação do pagamento",
    "confirmed": "confirmado, em preparação",
    "shipped": "enviado",
    "delivered": "entregue",
    "cancelled": "cancelado",
}

_PAGAMENTOS = {
    "pix": "PIX",
    "boleto": "boleto bancário",
    "debit": "cartão de débito",
}


def normalize(text: str) -> str:
    """Remove acentos e caixa para comparações tolerantes ('Violão' -> 'violao')."""
    stripped = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return " ".join(stripped.casefold().split())


def only_digits(text: str) -> str:
    """Extrai apenas os dígitos de um telefone ('(67) 99812-3456' -> '67998123456')."""
    return "".join(ch for ch in text if ch.isdigit())


def format_brl(value: float) -> str:
    """Formata um valor em reais no padrão brasileiro: 1234.5 -> 'R$ 1.234,50'."""
    formatted = f"{value:,.2f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return f"R$ {formatted}"


def format_datetime_ptbr(moment: datetime) -> str:
    """'quarta-feira, 30/07/2026, 14:32' — independente do locale do sistema."""
    return f"{_DIAS_SEMANA[moment.weekday()]}, {moment:%d/%m/%Y}, {moment:%H:%M}"


def describe_order_status(status: str) -> str:
    """Traduz o status interno do pedido para uma descrição amigável em PT-BR."""
    return _STATUS_PEDIDO.get(status, status)


def describe_payment(method: str) -> str:
    """Traduz o método de pagamento ('credit_6x' -> 'cartão de crédito em 6x')."""
    if method.startswith("credit_"):
        installments = method.removeprefix("credit_")
        return f"cartão de crédito em {installments}"
    return _PAGAMENTOS.get(method, method)
