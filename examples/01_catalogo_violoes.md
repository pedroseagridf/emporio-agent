# Exemplo 1 — Busca no catálogo com filtro de preço

> **O que este exemplo demonstra:** Consulta de catálogo com filtros (disponibilidade + preço máximo), exclusão de produto sem estoque e recomendação com desconto PIX calculado conforme a política.
>
> Transcrição real gerada por `scripts/gera_exemplos.py` com o agente conectado a `groq` / `openai/gpt-oss-20b`. As ferramentas consultadas em cada turno estão anotadas.

**🧑 Cliente:** Oi! Quais violões disponíveis vocês têm por até R$ 1.000?

**🎸 Agente:** Oi! 👋  
Aqui vão os violões que temos em estoque e que custam até R$ 1.000:

| # | Modelo | Preço |
|---|--------|-------|
| 1 | Tagima Memphis AC‑39 Nylon Natural | R$ 429,90 |
| 2 | Rozini RC‑104 Nylon Estudante | R$ 459,90 |
| 3 | Shelby SN‑100 Folk Aço Preto | R$ 549,00 |
| 4 | Giannini GF‑1R Aço Folk Sunburst | R$ 579,90 |
| 5 | Yamaha C40 Nylon Natural | R$ 599,90 |
| 6 | Giannini GN‑15 Nylon Cedr Natural | R$ 689,00 |
| 7 | Yamaha F310 Aço Natural | R$ 699,90 |
| 8 | Tagima Dallas Tuner Aço Natural | R$ 749,00 |
| 9 | Shelby SGD‑195E Elétrico Aço Sunburst | R$ 799,00 |
|10 | Yamaha C70 Nylon Natural | R$ 849,00 |

Qualquer modelo chama a sua atenção? Posso enviar fotos, detalhes de construção ou ajuda com a escolha!

*`ferramentas consultadas: buscar_produtos`*

---

**🧑 Cliente:** Qual desses você recomenda para um iniciante? Vou pagar no PIX.

**🎸 Agente:** Para quem está começando, eu recomendo **Tagima Memphis AC‑39 Nylon Natural** – um violão clássico, leve, com cordas de nylon e ótimas primeiras experiências de toque.

**Preço**: R$ 429,90  
**PIX**: 5 % de desconto → R$ 408,40 (pagamento à vista)

O violão tem corpo de Linden, tampo de Linden, braço de Nato e escala de 650 mm – tudo o que você precisa para praticar sem esforço. Se quiser mais detalhes, fotos ou comparar com outro modelo, é só falar!

*`ferramentas consultadas: consultar_politica`*

---
