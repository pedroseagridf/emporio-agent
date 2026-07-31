from emporio_agent.text_utils import (
    describe_order_status,
    describe_payment,
    format_brl,
    normalize,
    only_digits,
)


def test_normalize_strips_accents_and_case() -> None:
    assert normalize("Violão  Clássico") == "violao classico"


def test_only_digits() -> None:
    assert only_digits("(67) 99812-3456") == "67998123456"


def test_format_brl_brazilian_convention() -> None:
    assert format_brl(1234.5) == "R$ 1.234,50"
    assert format_brl(11499) == "R$ 11.499,00"
    assert format_brl(159.9) == "R$ 159,90"


def test_describe_payment() -> None:
    assert describe_payment("credit_6x") == "cartão de crédito em 6x"
    assert describe_payment("pix") == "PIX"


def test_describe_order_status() -> None:
    assert describe_order_status("shipped") == "enviado"
