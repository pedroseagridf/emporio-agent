# Notas da auditoria de dados

Achados da inspeção dos CSVs fornecidos pelo desafio e as decisões de tratamento
adotadas. Princípio geral: **os dados originais não são alterados na ingestão** —
inconsistências são preservadas na base e resolvidas na camada de consulta ou de
prompt, onde a decisão fica explícita e coberta por teste.

## Achados e decisões

| # | Achado | Evidência | Decisão | Teste |
|---|---|---|---|---|
| D1 | Divergência entre `name`/`specs` e `description` de produtos (marcas/modelos trocados) | ids 135, 136, 137, 139, 140, 142, 144 (ex.: 135 "Music Man Bass" descrito como "Fender Jazz Bass"; 142 "Korg" descrito como Roland de 88 teclas com `specs` de 61) | `name` + `specs` são a fonte de verdade (AS-5); a descrição é exibida, mas o agente é instruído a não afirmar marca/modelo a partir dela quando conflitar | — (decisão de prompt, fase D) |
| D2 | Produto **ativo com estoque 0** | id 96 (Giannini GF-3D, R$ 799,90) | `available = status='active' AND stock>0`; busca com `in_stock_only` o exclui; agente informa indisponibilidade e sugere similares (§7.3) | `test_produto_96_ativo_sem_estoque`, `test_search_violao_ate_1000_em_estoque` |
| D3 | Produtos **descontinuados** | ids 113, 136 | Nunca ofertados como disponíveis; `get_similar_products` fornece alternativas ativas da mesma categoria | `test_produto_113_descontinuado_tem_alternativas` |
| D4 | Produto **coming_soon** vendido em pedido antigo | id 130 (pedido 3, entregue em 2025) | Status atual prevalece para novas vendas ("em breve"); histórico do pedido permanece consultável | — (comportamento de prompt) |
| D5 | **21 de 25 promoções expiradas**, incluindo 40% no produto 96 | `is_active = 0` | Camada de consulta só retorna `is_active = 1` (ativas: produtos 127, 121, 90, 94); preço promocional sempre calculado junto do original + % (§6.2) | `test_somente_4_promocoes_ativas`, `test_promocao_expirada_do_produto_96_nao_aparece` |
| D6 | **Total de pedido ≠ soma dos itens ao preço atual** — pedidos 3 (R$ 3.450 vs R$ 3.498) e 20 (R$ 1.400 vs R$ 1.488); `order_items` não guarda preço histórico | orders.csv / order_items.csv | Preservado; o total gravado é a fonte de verdade do pedido. O payload de itens expõe o preço como `preco_atual_catalogo` para o agente nunca afirmar um valor que o cliente pode não ter pago | `test_totais_divergentes_da_soma_dos_itens_sao_preservados` |
| D7 | **Clientes com nomes quase idênticos** | "Bruno Carvalho Martins" (11) / "Bruno Carvalho" (27) / "Bruno Martins" (43); "Diego (Fernandes) Castro" (13/47) etc. | Nome sozinho não identifica: consulta de pedido exige nº do pedido + nome do titular (≥ 2 termos), ou nome + telefone/e-mail cadastrados (AS-2, LGPD §9) | testes de `get_order_status` e `find_orders_by_customer` |
| D8 | **Categorias sem nenhum produto** (6, 7, 8 — sopros e cordas orquestrais), embora o manual cite "300+ instrumentos" | products.csv só tem categorias 1–5 e 9 | O agente responde com o catálogo real; para itens dessas categorias, informa indisponibilidade no momento sem inventar produtos | `test_categoria_sem_produtos_retorna_vazio` |
| D9 | Campos opcionais como **string vazia** (tracking, previsão, notas) | pedidos pending/confirmed/cancelled | Convertidos para `NULL` na ingestão | `test_empty_strings_become_null` |
| D10 | `specs` é **JSON embutido** no CSV, com chaves distintas por categoria | todos os produtos | Armazenado como texto e desserializado na camada de consulta (`Product.specs: dict`) | cobertura indireta nos testes de produto |
| D11 | Inconsistências internas do PDF de políticas (dois telefones; e-mail com acento) | §1.2 vs §7; tabela 1.2 | Assunções AS-3 e AS-4 do README | — |

## Colunas derivadas (não alteram os dados)

- `products.search_text`: nome + nome da categoria + descrição, normalizados sem
  acentos — permite achar "violão"/"violao" mesmo sem a palavra no nome do produto.
- `customers.name_norm`, `customers.phone_digits`: comparação de identidade
  tolerante a grafia/formatação.

## Minimização de dados (LGPD)

O objeto `Order` retornado ao agente expõe apenas o **primeiro nome** do titular —
telefone, e-mail e nome completo nunca chegam ao contexto do modelo
(`test_pedido_expoe_apenas_primeiro_nome_do_cliente`).
