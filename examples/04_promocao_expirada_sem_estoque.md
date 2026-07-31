# Exemplo 4 — Promoção expirada + produto sem estoque (não trivial)

> **O que este exemplo demonstra:** Cenário NÃO TRIVIAL: o agente verifica a promoção no sistema, recusa com transparência um desconto expirado (nunca promete), constata a falta de estoque e aplica a política de sugerir alternativas disponíveis.
>
> Transcrição real gerada por `scripts/gera_exemplos.py` com o agente conectado a `groq` / `openai/gpt-oss-20b`. As ferramentas consultadas em cada turno estão anotadas.

**🧑 Cliente:** Vi que o violão Giannini GF-3D estava com 40% de desconto na Semana do Músico. Ainda consigo esse preço?

**🎸 Agente:** Oi! 🎶

O Giannini GF‑3D não está com promoção no momento (nenhum desconto na lista de promoções ativas) e, infelizmente, está sem estoque.  

Mas tenho umas alternativas que têm preço e disponibilidade próximos:

| Produto | Preço | Estoque | Link (página) |
|---------|-------|---------|---------------|
| Shelby SGD‑195E Elétrico Aço Sunburst | R$ 799,00 | 6 |  |
| Yamaha C70 Nylon Natural | R$ 849,00 | 8 |  |
| Tagima Dallas Tuner Aço Natural | R$ 749,00 | 9 |  |

Se quiser mais detalhes, fotos ou saber sobre pagamento/parcelamento, é só falar!  

Aproveito e te lembro: promoções não são cumulativas, e o desconto de PIX (5%) só aplica sobre o preço de tabela.  

Precisa de algo mais? Estou à disposição!

*`ferramentas consultadas: detalhar_produto, listar_promocoes_ativas, consultar_politica, produtos_similares, consultar_politica`*

---

**🧑 Cliente:** Poxa. E esse Yamaha F310 que você sugeriu: tem promoção? Em quantas vezes consigo parcelar ele?

**🎸 Agente:** Oi! 🎸

**Yamaha F310 –** não tem promoção ativa no momento (verifiquei a lista de promoções e não há desconto para esse modelo). O preço atual é **R$ 699,90**.

**Parcelamento**  
No nosso sistema você pode parcelar até **6 vezes sem juros** (a partir de 4x a 6x a parcela mínima é R$ 80,00).  
Para este valor:

| # de parcelas | Min. parcela | Observação |
|--------------|--------------|------------|
| 1 (à vista)  | – | – |
| 2            | – | – |
| 3            | – | – |
| 4‑6          | R$ 80,00 | Sem juros |

O valor exato da parcela será calculado no momento da compra, mas você pode usar esses limites para planejar.

Se preferir, podemos aplicar o **desconto de PIX de 5%** (apenas à vista) ou verificar outras condições de pagamento.

Precisa de mais alguma informação ou quer dar uma olhada em fotos? Estou à disposição!

*`ferramentas consultadas: buscar_produtos, consultar_politica, consultar_politica`*

---
