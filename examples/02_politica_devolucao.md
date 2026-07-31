# Exemplo 2 — Aplicação da política de trocas e devoluções

> **O que este exemplo demonstra:** Pergunta sobre regra respondida consultando o manual (arrependimento em 7 dias, defeito em 30 dias) antes de coletar qualquer dado do cliente.
>
> Transcrição real gerada por `scripts/gera_exemplos.py` com o agente conectado a `groq` / `openai/gpt-oss-20b`. As ferramentas consultadas em cada turno estão anotadas.

**🧑 Cliente:** Me arrependi de uma compra que fiz no site, posso devolver?

**🎸 Agente:** Oi! 😊  
Sim, você pode devolver o produto dentro de 7 dias corridos após o recebimento, sem precisar dar um motivo.  
Para garantir o reembolso:

1. **Embalagem original** – sem sinais de uso.  
2. **Acessórios e manual** – tudo junto.  
3. O **frete de devolução** é por nossa conta (para arrependimento).  
4. O reembolso vai para a forma de pagamento original, em até 10 dias úteis.

Se quiser dar início ao processo, me passe o **número do pedido** (e, se quiser, o nome completo, para a verificação). Assim organizamos tudo pra você!

*`ferramentas consultadas: consultar_politica`*

---

**🧑 Cliente:** E se o produto chegar com defeito, qual o prazo?

**🎸 Agente:** Para defeito de fabricação o prazo é:

- **Até 30 dias corridos** após a compra, você pode solicitar a troca (ou, se preferir, o reembolso, se for o caso).  
- Se já passaram os 30 dias, o ideal é acionar a **garantia do fabricante**; a Empório da Música pode intermediar, mas não pode garantir a troca diretamente nesse prazo.

Lembrando que apenas defeitos de fabricação cobrem essa regra; danos por mau uso, quedas ou exposição a umidade não são atendidos. Se precisar abrir uma solicitação, me passe o número do pedido e o nome completo, e eu mando o passo a passo!

*`ferramentas consultadas: nenhuma`*

---
