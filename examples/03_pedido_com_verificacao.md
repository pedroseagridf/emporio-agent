# Exemplo 3 — Status de pedido com verificação de identidade (não trivial)

> **O que este exemplo demonstra:** Cenário NÃO TRIVIAL: o agente se recusa a revelar dados do pedido sem verificação (LGPD), verifica a identidade quando o titular se apresenta, consulta o pedido em tempo real e explica o rastreamento pela política.
>
> Transcrição real gerada por `scripts/gera_exemplos.py` com o agente conectado a `groq` / `qwen/qwen3.6-27b`. As ferramentas consultadas em cada turno estão anotadas.

**🧑 Cliente:** Qual o status do pedido 1?

**🎸 Agente:** Olá! Tudo bem? 🎶 

Para eu consultar o status do pedido nº 1 e garantir a segurança dos seus dados (padrão LGPD), preciso que você me informe o **nome completo do titular** (nome + sobrenome). 

Assim que você mandar aqui, já corro o número pra mim e te passo a atualizado! 🎸

*`ferramentas consultadas: nenhuma`*

---

**🧑 Cliente:** Claro! O pedido é o número 1 e eu sou o Pedro Henrique Oliveira.

**🎸 Agente:** Fala, Pedro! Que bom ter você por aqui. 🎶

Aqui está o status da sua compra:

📦 **Pedido nº 1**
✅ **Status:** Entregue
📅 **Data do pedido:** 15/10/2025
💰 **Valor total:** R$ 11.499,00 (Pago via PIX)
📍 **Código de rastreio:** BRAB1234567BR

📝 **Itens comprados:**
• 1x Martin D-28 Dreadnought Natural

Tudo certo por aqui? Se precisar de algo mais, como garantir a nota fiscal ou dúvidas sobre a garantia do instrumento, é só me chamar. 👊🎸

*`ferramentas consultadas: consultar_pedido`*

---

**🧑 Cliente:** Perfeito, obrigado! E o que significa esse código de rastreio?

**🎸 Agente:** O código de rastreio é, basicamente, a "impressão digital" da sua encomenda no sistema da transportadora! 📦

Com ele, você entra no site dos Correios ou da Jadlog e consegue seguir o histórico de viagem do seu instrumento: saída, trânsito e entrega.

No caso do seu pedido, como já consta como **entregue** por aqui, o rastreio deve estar finalizado. Normal, mas o código sempre é enviado por WhatsApp junto com a confirmação de envio, caso você precise consultá-lo mais tarde por qualquer motivo.

Se precisar de mais alguma informação sobre o Martin ou tiver outra dúvida, estou à disposição! 🎸

*`ferramentas consultadas: consultar_politica`*

---
