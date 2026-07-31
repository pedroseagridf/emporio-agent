# Revisão adversarial (P07) — achados e disposição

Revisão executada por um agente com contexto limpo ("revisor que não escreveu o
código"), com cada suspeita **verificada executando o código contra a base real**
antes de ser reportada. Este documento registra os achados e o que foi feito com
cada um (P08). Os fixes referenciam os commits correspondentes.

## Críticos (P1)

| # | Achado | Cenário verificado | Disposição |
|---|---|---|---|
| 1 | Verificação de identidade aceitava partícula + sobrenome como "nome + sobrenome" | `consultar_pedido(4, "da Silva")` liberava o pedido de "Lucas Mendes da Silva" | ✅ Corrigido: partículas (da/de/do/das/dos/e) são descartadas antes da exigência de ≥ 2 termos |
| 2 | `preco_unitario` dos itens de pedido era o preço **atual** do catálogo, não o pago | Pedido 3: itens "somavam" R$ 3.498 vs total R$ 3.450; pedido 20: R$ 1.488 vs R$ 1.400 (não documentado) | ✅ Chave renomeada para `preco_atual_catalogo`; D6 atualizado cobrindo o pedido 20, com teste |
| 3 | Mensagens distintas para "pedido não existe" vs "nome não confere" permitiam enumerar pedidos | IDs sequenciais 1–20 + força-bruta de sobrenome (combinado com o achado 1) | ✅ Mensagem neutra única para os dois casos |

## Importantes (P2)

| # | Achado | Disposição |
|---|---|---|
| 4 | `apenas_disponiveis="false"` (string) virava `True` | ✅ Coerção explícita de booleanos textuais |
| 5 | Argumento não numérico virava "falha interna, procure um humano" | ✅ `ValueError/TypeError` → erro específico que o modelo corrige sozinho |
| 6 | Retry cego: 401/403/404 retentados 3× (até 24 requisições por turno) | ✅ Erros com `status_code` 401/403/404 não são retentados; backoff entre tentativas |
| 7 | Erro no meio do loop deixava `last_tool_calls` sujo (CLI imprimia "ferramentas consultadas" sob mensagem de falha) | ✅ Trace limpo no tratamento de erro; log corrigido |
| 8 | `Repository.close()` era dead code; conexão nunca fechada na CLI | ✅ CLI fecha em `finally` |
| 9 | `%`/`_` sem escape no LIKE: buscar "%" devolvia o catálogo inteiro | ✅ Escape com `ESCAPE '\'` |
| 10 | Telefone com DDI (+55) não localizava o cliente | ✅ Casamento pelos últimos 11 dígitos |
| 11 | `limite=-1` desativava o LIMIT (65 produtos no contexto) | ✅ Clamp 1–50 |

## Menores / higiene

| # | Achado | Disposição |
|---|---|---|
| 12 | `.env` real no diretório (não rastreado no git) | ℹ️ Sem ação — alerta operacional: nunca zipar a pasta em vez de clonar |
| 13 | Caminhos relativos ao cwd quebravam execução fora da raiz | ✅ Resolvidos a partir da raiz do projeto (`paths.py`); instalação via wheel segue como limitação conhecida do protótipo (README) |
| 14 | `python -m pytest` puro falhava (sem `pythonpath`) | ✅ `pythonpath = ["src"]` no pyproject |
| 15 | Marker `llm` sem uso | ➡️ Mantido de propósito: a suíte comportamental (P09) o utiliza |
| 16 | `PolicyBook.topics()` dead code | ✅ Removido |
| 17 | `KeyError` opaco se o manual mudar de numeração | ✅ Mensagem explícita |
| 18 | Docstring de `describe_payment` não batia com o comportamento | ✅ Parsing corrigido |

## Áreas auditadas e limpas

SQL injection (todas as queries parametrizadas; interpolações apenas de
constantes e placeholders), normalização de acentos, formatação R$, matemática
de promoções, filtro `is_active`, minimização de dados no payload de pedidos
(sem telefone/e-mail/nome completo), agrupamento de `tool_result` para a API
Anthropic (incluindo texto + tool_calls na mesma resposta) e encoding UTF-8.
