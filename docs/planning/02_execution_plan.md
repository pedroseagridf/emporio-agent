# Phase 2 — Execution Strategy
**Empório da Música — Customer-Service Agent (Artefact Technical Case)**

---

## 0. Recommended target architecture (summary)

**Approach: hybrid — function calling over structured data + policy knowledge layer, on a thin agent loop.**

```
┌─────────────────────────────────────────────────────────┐
│  Interface (CLI chat; optional Streamlit UI)            │
├─────────────────────────────────────────────────────────┤
│  Agent core (LLM + system prompt persona + tool loop)   │
│   • conversation memory (in-session; optional SQLite)   │
│   • guardrails: scope, grounding, LGPD verification     │
├───────────────────────────┬─────────────────────────────┤
│  Structured-data tools    │  Policy knowledge            │
│  (SQLite built from CSVs) │  (PDF → markdown sections)   │
│  • search_products        │  • get_policy(topic) tool    │
│  • get_product_details    │    (section retrieval; the   │
│  • get_active_promotions  │    doc is ~3–4k tokens, so   │
│  • get_order_status       │    section-level lookup —    │
│    (with identity check)  │    no vector DB needed)      │
│  • store facts (hours,    │                              │
│    address, payment)      │                              │
└───────────────────────────┴─────────────────────────────┘
```

**Key justifications (to reproduce in the README):**
- **Function calling (native tool use) over ReAct-prompting**: deterministic parsing, fewer failure modes, native support in all major APIs. The "when to consult data vs. policies" requirement maps 1:1 onto tool selection.
- **SQLite over raw pandas**: testable, injection-safe parametrized queries, honest answer to "SQL agent?" (we expose *curated* query tools, not free-form SQL — safer and more predictable for a customer-facing bot; free-form text-to-SQL is a documented rejected alternative).
- **Section-based policy lookup over embeddings RAG**: the policy doc is 8 small pages. A vector DB is unjustifiable overhead; a `get_policy(topic)` tool over pre-chunked markdown sections keeps answers grounded and citable. *Document that classic RAG would be the path if the corpus grew* (this is the kind of judgment Artefact says it evaluates).
- **Thin agent loop (direct SDK or PydanticAI) over LangChain**: inspectable, less dependency risk, shows understanding of the mechanics. (If you prefer to signal framework fluency, LangGraph is the defensible alternative — pick one and justify; recommendation: thin loop.)
- **Model**: default to a cheap fast API model (e.g., claude-haiku / gpt-4o-mini class) with provider abstraction and a documented free/local fallback (Groq or Ollama) so evaluators can run it without cost.
- **Persona**: system prompt encodes tone (§7.1), the 5-step service flow (§7.2), special-situation rules (§7.3), scope limits, grounding rules, LGPD verification, and PT-BR.

---

## 1. Work breakdown — phases, milestones, dependencies

> Suggested calendar assuming ~1 week part-time. Compress/stretch to the real deadline from the email. **Commit at every milestone** (the commit history is itself a deliverable).

### Phase A — Repo & scaffolding (½ day)
**Depends on:** nothing.
- Create public GitHub repo; MIT license; `.gitignore`; `README` skeleton with assumptions section started.
- Tooling: `uv` (or poetry), `ruff`, `pytest`, `pre-commit` (optional); `src/` layout; `.env.example` (`LLM_PROVIDER`, `API_KEY`, `MODEL`).
- **Milestone A:** empty-but-running skeleton (`python -m emporio_agent` prints a banner); 2–4 commits.

### Phase B — Data layer (1 day)
**Depends on:** A.
- Ingestion script: CSVs → SQLite (`data/build_db.py`), parsing `specs` JSON, normalizing prices/dates.
- **Data-treatment decisions implemented & documented:** name/description conflicts (canonical = name+specs), status handling (`active`/`discontinued`/`coming_soon`), stock-0 semantics, active-promotion filtering, near-duplicate customers.
- Repository/query functions (pure Python, no LLM): product search with filters (category, text, price ceiling, in-stock), product detail, active promos (with original + discounted price + %), order status by order-id or by customer identity (name + phone/email match).
- Unit tests for every query function, including the trap cases (product 96 stock 0; product 113 discontinued; promo on 96 inactive; Bruno Carvalho ambiguity).
- **Milestone B:** `pytest` green on the data layer; documented data-audit note (`docs/data_notes.md`).

### Phase C — Policy knowledge layer (½ day)
**Depends on:** A (parallel with B).
- Extract PDF → `data/policies.md`, split by numbered section; fix/flag the two internal inconsistencies (phones, email).
- `get_policy(topic)` tool: keyword/section mapping (hours, payment, returns, shipping, promotions rules, warranty, privacy, store info). Return the section text verbatim for the LLM to ground on.
- Store-facts constants (address, hours, phone) exposed via a `get_store_info` tool.
- Tests: each topic returns the right section.
- **Milestone C:** policy tools tested.

### Phase D — Agent core (1–1.5 days) ← the heart of the evaluation
**Depends on:** B + C.
- Provider abstraction (one class; Anthropic/OpenAI/Groq/Ollama behind a flag).
- Tool schemas for all tools from B/C; agent loop: user msg → LLM → tool calls → tool results → final answer; max-iteration guard; graceful API-error handling.
- **System prompt** (versioned file, not inline string): persona "Empório da Música" attendant; PT-BR; informal-professional tone; the 5-step flow; grounding rules ("never state price/stock/order info that didn't come from a tool"); special situations (out-of-stock → alternatives; discontinued → successors; expired promo → transparent + current price; PIX 5% not cumulative; promo price shown with original + %); scope rules (instruments only; accessories politely redirected; off-topic → friendly refusal + bridge back); LGPD (verify order id or name+phone/email before order details); complaint → empathy + escalate to human (24h business); off-hours notice.
- In-session conversation memory; optional `--persist` flag storing history in SQLite (justify: recurring WhatsApp-style conversations benefit; keep optional for reviewer simplicity).
- **Milestone D:** end-to-end conversation works for the 4 suggested scenarios; commits per sub-step (provider, tools wiring, prompt, memory).

### Phase E — Interface (½ day)
**Depends on:** D.
- CLI chat with `rich` (colors, store banner, `/reset`, `/exit`). This is the required deliverable surface.
- Optional (time-permitting): Streamlit one-pager for a screenshot-friendly demo. Do **not** let it eat agent-quality time.
- **Milestone E:** `uv run emporio-agent` gives a polished chat.

### Phase F — Behavioral test-set & hardening (1 day)
**Depends on:** D.
- Scripted eval (pytest, mock-or-live flag): ~12–15 cases —
  happy paths (price lookup Takamine GD20 → R$2,199; violões ≤ R$1000 in stock; address; return policy 7 days),
  traps (product 96: must say unavailable + suggest similar; product 113: discontinued + successor; "tem 40% no Giannini?" → expired promo, offer current price; PIX on promo price → not cumulative; order status without identity → asks verification; "Bruno" order → disambiguation; saxophone → category empty, honest answer; "sell me a guitar cable" → polite redirect; "write my homework" → out-of-scope refusal; prompt-injection attempt "ignore your instructions" → stays in persona).
- Fix prompt/tools based on failures; log token/latency notes for README.
- **Milestone F:** eval table green; this table becomes README material.

### Phase G — Example conversations & README (1 day)
**Depends on:** F.
- Capture 4–5 real transcripts (`examples/01_...md` …): catalog filter, policy application (return), **one non-trivial** (e.g., order status with identity verification + tracking explanation, or promo + PIX cumulative-discount reasoning), out-of-scope handling, out-of-stock + alternative.
- README final: quickstart (≤5 commands), architecture diagram, decision table with justifications & rejected alternatives, data-audit findings, assumptions list, known limitations & next steps (e.g., real WhatsApp adapter, embeddings RAG at corpus scale, human-handoff queue, observability/tracing, LLM-as-judge evals), **AI-assistant workflow section** (this 3-phase Claude-driven process: analysis → plan → prompt-driven implementation; include the planning docs in the repo — strong differentiator for the "workflow" criterion).
- **Milestone G:** a stranger can clone → configure key → run in <5 min.

### Phase H — Final review & freeze (½ day)
**Depends on:** G.
- Fresh-clone test on a clean env (ideally another machine/container); README followed literally.
- Repo hygiene: no secrets, no dead code, consistent commit history; tag `v1.0`.
- Submit repo link by email; **no pushes after the deadline**.

### Dependency graph
```
A ──► B ──┐
A ──► C ──┼──► D ──► E ──► (G)
          │      └──► F ──► G ──► H
```
(B and C parallel; E and F parallel after D.)

---

## 2. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Hallucinated facts slip through | Grounding rules in prompt + every factual answer via tool + eval cases asserting refusal |
| Reviewer cannot run it (keys, OS) | Provider flag with free option; pinned deps; tested fresh-clone; Windows/Linux-neutral paths |
| Prompt injection / persona break | Explicit adversarial eval case; tools return data only (no instructions); narrow tool surface |
| Scope creep (UI, extra features) | Agent correctness first (phases B–D–F); UI strictly time-boxed |
| Trap data mishandled silently | Data audit is its own phase (B) with tests naming each trap |
| Fake-looking history | Commit per milestone/sub-step with meaningful messages from day 1 |
| LLM nondeterminism in tests | Assert on tool-call traces + key substrings, not exact wording; temperature 0 for evals |

---

## 3. Standards

- **Code**: `src/` layout; type hints everywhere; pydantic models for tool I/O; docstrings on public functions; ruff clean; no hardcoded secrets; parametrized SQL only.
- **Commits**: conventional commits (`feat:`, `test:`, `docs:`…), small and thematic — the history should *narrate* the build.
- **Testing**: unit (data/policy tools) + behavioral evals (agent); `pytest -m "not llm"` runs without any API key.
- **Docs**: README (PT-BR) + `docs/` (data notes, decision log, this planning trio).
- **Deployment**: out of scope for the case; note in README how it would go (Dockerfile optional stretch — nice signal, low cost).
