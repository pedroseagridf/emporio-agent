# 🎸 Empório da Música — Agente de Atendimento

Protótipo de um **agente de atendimento por mensagens de texto** para a loja fictícia
Empório da Música (Campo Grande/MS), desenvolvido como parte do desafio técnico para
**AI Engineer na Artefact**.

O agente assume a persona de atendente da loja e responde clientes em português,
consultando **dados operacionais** (produtos, estoque, preços, promoções e pedidos)
e o **manual de políticas** (trocas, horários, pagamento, frete) — sabendo distinguir
quando usar cada fonte e como lidar com perguntas fora do escopo.

> 🚧 **Status:** em desenvolvimento. Este README é preenchido de forma incremental a
> cada fase do projeto.

## Como executar

*(será preenchido na fase de interface — o objetivo é: clone → `uv sync` →
`cp .env.example .env` → construir a base → conversar com o agente)*

## Arquitetura e decisões técnicas

*(será preenchido conforme as decisões forem implementadas; o registro completo de
decisões, com alternativas rejeitadas, fica em [`docs/`](docs/))*

Resumo da abordagem planejada:

- **Function calling** (uso nativo de ferramentas) sobre uma base **SQLite**
  construída a partir dos CSVs fornecidos;
- **Consulta de políticas por seção** do manual (PDF → markdown), sem vector DB —
  decisão dimensionada para o tamanho do corpus e justificada no registro de decisões;
- **Loop de agente enxuto** com abstração de provedor (API paga com alternativa
  gratuita/local), em vez de framework pesado;
- Interface **CLI de chat** com memória de conversa em sessão.

## Tratamento de dados

*(será preenchido na fase de dados — os achados da auditoria dos CSVs estão em
`docs/planning/01_technical_case_analysis.md`, seção 4)*

## Suposições

O enunciado orienta a assumir interpretações razoáveis e documentá-las. Suposições
adotadas até aqui (lista atualizada a cada fase):

| # | Suposição | Justificativa |
|---|---|---|
| AS-1 | O agente conversa em **PT-BR**, com tom "informal porém profissional" | Público da loja é brasileiro; tom definido no manual de políticas (§7.1) |
| AS-2 | Consultas a pedidos exigem **verificação leve de identidade** (nº do pedido, ou nome + telefone/e-mail cadastrados) | LGPD (§9 do manual) + existência de clientes com nomes quase idênticos na base |
| AS-3 | Telefone/WhatsApp de atendimento é **(67) 3341-4444**; o número (67) 3321-4500 citado na seção 7 do manual é tratado como o canal em que o próprio agente opera | O manual traz os dois números sem conciliá-los |
| AS-4 | E-mail de contato é **contato@emporiodamusica.com.br** (sem acento) | A grafia acentuada que aparece na tabela 1.2 do manual não é um e-mail válido |
| AS-5 | Em divergências entre `name`/`specs` e `description` de um produto, **`name` + `specs` são a fonte de verdade** | A descrição é texto de marketing e contém trocas evidentes de marca/modelo (ver auditoria de dados) |
| AS-6 | Integração real com WhatsApp está **fora do escopo** — a interface de texto simula o canal | O enunciado pede protótipo com foco no agente funcionando corretamente |

## Limitações conhecidas

*(será preenchido na fase final)*

## Uso de assistentes de IA

Este projeto foi desenvolvido com **Claude (Claude Code)** em um fluxo estruturado em
três fases, todas documentadas em [`docs/planning/`](docs/planning/):

1. **Análise do caso** — leitura integral do enunciado, do manual de políticas e
   auditoria dos CSVs (com os achados de qualidade de dados);
2. **Plano de execução** — arquitetura alvo, quebra em fases com marcos e
   dependências, riscos e mitigação;
3. **Playbook de prompts** — sequência de prompts (P01–P15) que guia a implementação,
   com separação deliberada entre gerar → revisar → corrigir e checkpoint humano
   (revisão de diff + commit) a cada etapa.

A seção será expandida ao final com o relato honesto de como o fluxo funcionou na
prática.

## Exemplos de interação

*(3 a 5 conversas serão adicionadas em `examples/` na fase de documentação)*
