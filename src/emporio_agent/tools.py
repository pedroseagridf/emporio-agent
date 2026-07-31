"""Ferramentas expostas ao modelo — a única forma de o agente acessar dados.

Cada ferramenta devolve JSON (chaves em PT-BR, preços já formatados em R$) para
o modelo copiar valores sem recalcular. Erros de negócio (identidade, tópico
inválido) voltam como ``{"erro": ...}`` para o modelo se corrigir; erros
inesperados são registrados em log e devolvem uma mensagem genérica.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from emporio_agent.db.repository import (
    IdentityVerificationError,
    Order,
    Product,
    Promotion,
    Repository,
)
from emporio_agent.policies import TOPICS, PolicyBook, get_store_info
from emporio_agent.text_utils import describe_order_status, describe_payment, format_brl

logger = logging.getLogger(__name__)

_TOPICOS_DESC = "; ".join(f"'{t}' ({d})" for t, (_, d) in TOPICS.items())

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "buscar_produtos",
        "description": (
            "Busca instrumentos no catálogo por texto livre (nome, tipo, marca), categoria"
            " e faixa de preço. Use apenas_disponiveis=true quando o cliente quer comprar."
            " Lista vazia significa que não há produtos com esses critérios."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "termo": {"type": "string", "description": "Texto livre, ex.: 'violão nylon'"},
                "categoria": {"type": "string", "description": "Nome da categoria, ex.: 'Violões'"},
                "preco_maximo": {"type": "number"},
                "preco_minimo": {"type": "number"},
                "apenas_disponiveis": {
                    "type": "boolean",
                    "description": "true para listar somente produtos ativos com estoque",
                },
                "limite": {"type": "integer", "description": "Máximo de resultados (padrão 10)"},
            },
        },
    },
    {
        "name": "detalhar_produto",
        "description": (
            "Detalhes completos de um produto pelo id ou pelo nome (melhor correspondência):"
            " preço, estoque, status (active/discontinued/coming_soon) e especificações."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "produto_id": {"type": "integer"},
                "nome": {"type": "string"},
            },
        },
    },
    {
        "name": "produtos_similares",
        "description": (
            "Alternativas DISPONÍVEIS da mesma categoria, por proximidade de preço. Use"
            " sempre que um produto estiver sem estoque, descontinuado ou 'em breve'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"produto_id": {"type": "integer"}},
            "required": ["produto_id"],
        },
    },
    {
        "name": "listar_promocoes_ativas",
        "description": (
            "Promoções VIGENTES (todas, ou de um produto específico), com preço original,"
            " percentual e preço promocional. Se um produto não aparecer aqui, ele NÃO tem"
            " promoção válida — não prometa descontos fora desta lista."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"produto_id": {"type": "integer"}},
        },
    },
    {
        "name": "consultar_pedido",
        "description": (
            "Status de um pedido pelo número. Exige o nome do titular (nome + sobrenome)"
            " para verificação de identidade. Retorna status, itens, rastreio e previsão."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "numero_pedido": {"type": "integer"},
                "nome_cliente": {"type": "string", "description": "Nome e sobrenome do titular"},
            },
            "required": ["numero_pedido", "nome_cliente"],
        },
    },
    {
        "name": "buscar_pedidos_por_cliente",
        "description": (
            "Localiza os pedidos de um cliente que não sabe o número. Exige nome completo"
            " E um contato cadastrado (telefone com DDD ou e-mail) — LGPD."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "nome_completo": {"type": "string"},
                "contato": {"type": "string", "description": "Telefone com DDD ou e-mail"},
            },
            "required": ["nome_completo", "contato"],
        },
    },
    {
        "name": "consultar_politica",
        "description": (
            "Texto oficial de uma seção do manual de políticas da loja. Consulte ANTES de"
            f" responder sobre esses assuntos. Tópicos: {_TOPICOS_DESC}."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"topico": {"type": "string", "enum": sorted(TOPICS)}},
            "required": ["topico"],
        },
    },
    {
        "name": "dados_da_loja",
        "description": "Endereço, telefone/WhatsApp, e-mail e horários oficiais da loja.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def _product_payload(product: Product) -> dict[str, Any]:
    return {
        "id": product.product_id,
        "nome": product.name,
        "categoria": product.category,
        "preco": product.price_brl,
        "preco_formatado": format_brl(product.price_brl),
        "estoque": product.stock_quantity,
        "status": product.status,
        "disponivel": product.available,
        "descricao": product.description,
        "especificacoes": product.specs,
    }


def _promotion_payload(promo: Promotion) -> dict[str, Any]:
    return {
        "produto_id": promo.product_id,
        "produto": promo.product_name,
        "campanha": promo.description,
        "desconto_percentual": promo.discount_percent,
        "preco_original": format_brl(promo.original_price_brl),
        "preco_promocional": format_brl(promo.final_price_brl),
    }


def _order_payload(order: Order) -> dict[str, Any]:
    return {
        "numero": order.order_id,
        "titular_primeiro_nome": order.customer_first_name,
        "data": order.order_date,
        "status": order.status,
        "status_descricao": describe_order_status(order.status),
        "total": format_brl(order.total_brl),
        "pagamento": describe_payment(order.payment_method) if order.payment_method else None,
        "codigo_rastreio": order.tracking_code,
        "previsao_entrega": order.estimated_delivery,
        "observacoes": order.notes,
        "itens": [
            {
                "produto": item.product_name,
                "quantidade": item.quantity,
                "preco_unitario": format_brl(item.unit_price_brl),
            }
            for item in order.items
        ],
    }


class AgentTools:
    """Executor das ferramentas: valida, consulta as camadas de dados/políticas
    e serializa o resultado em JSON para o modelo."""

    def __init__(self, repository: Repository, policy_book: PolicyBook) -> None:
        self._repo = repository
        self._policies = policy_book

    @property
    def specs(self) -> list[dict[str, Any]]:
        return TOOL_SPECS

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        try:
            result = self._dispatch(name, arguments)
        except (IdentityVerificationError, KeyError) as exc:
            message = str(exc.args[0]) if exc.args else str(exc)
            result = {"erro": message}
        except Exception:
            logger.exception("Erro inesperado na ferramenta %s com args %r", name, arguments)
            result = {
                "erro": "Falha interna ao consultar o sistema. Peça para o cliente tentar"
                " novamente em instantes ou encaminhe para um atendente humano."
            }
        return json.dumps(result, ensure_ascii=False)

    def _dispatch(self, name: str, args: dict[str, Any]) -> Any:
        match name:
            case "buscar_produtos":
                products = self._repo.search_products(
                    query=args.get("termo"),
                    category=args.get("categoria"),
                    max_price=args.get("preco_maximo"),
                    min_price=args.get("preco_minimo"),
                    in_stock_only=bool(args.get("apenas_disponiveis", False)),
                    limit=int(args.get("limite", 10)),
                )
                return [_product_payload(p) for p in products]
            case "detalhar_produto":
                product = self._repo.get_product(
                    product_id=args.get("produto_id"), name=args.get("nome")
                )
                if product is None:
                    return {"erro": "Produto não encontrado no catálogo."}
                return _product_payload(product)
            case "produtos_similares":
                similar = self._repo.get_similar_products(int(args["produto_id"]))
                return [_product_payload(p) for p in similar]
            case "listar_promocoes_ativas":
                product_id = args.get("produto_id")
                promos = self._repo.get_active_promotions(
                    product_id=int(product_id) if product_id is not None else None
                )
                return [_promotion_payload(p) for p in promos]
            case "consultar_pedido":
                order = self._repo.get_order_status(
                    int(args["numero_pedido"]), str(args["nome_cliente"])
                )
                if order is None:
                    return {"erro": "Pedido não encontrado. Confira o número informado."}
                return _order_payload(order)
            case "buscar_pedidos_por_cliente":
                orders = self._repo.find_orders_by_customer(
                    str(args["nome_completo"]), str(args["contato"])
                )
                return [_order_payload(o) for o in orders]
            case "consultar_politica":
                return {"secao_do_manual": self._policies.get_policy(str(args["topico"]))}
            case "dados_da_loja":
                return get_store_info()
            case _:
                return {"erro": f"Ferramenta desconhecida: {name}."}
