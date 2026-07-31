# Phase 1 — Technical Case Analysis
**Artefact — AI Engineer (Full-Stack, Generative AI) — Technical Challenge**
Analysis date: 2026-07-29

---

## 1. What the challenge is

Build a **Python prototype of a text-message customer-service agent** for **Empório da Música**, a fictional musical-instrument store in Campo Grande/MS. The store's human team is overloaded with recurring questions (opening hours, order status, product price/availability), and the agent must assist with those.

The evaluators state explicitly what they measure: **logic, clarity, and initiative** — *how you solve the problem and make decisions*, not a perfect solution. Every technical choice must be **justified in the README**.

### Provided materials

| File | Content | Key facts |
|---|---|---|
| `desafio_tecnico_ai_eng_artefact.pdf` | The case statement | Requirements, deliverables, submission rules |
| `data/políticas_da_loja.pdf` | Internal policies manual (8 pages, v2.1, June 2025) | Store info, hours, payment, returns, shipping, promotions, service guidelines, warranty, LGPD |
| `data/*.csv` (6 files) | Operational data | categories (9), products (65 rows, ids 81–145), customers (50), orders (20), order_items (22), promotions (25, only 4 active) |

Note: you are **not required to use all data** — use what improves the customer experience.

---

## 2. Explicit requirements

**Functional (the agent must):**
1. Assume a **persona** aligned with the store's identity and tone.
2. Receive and answer text messages grounded in the provided context.
3. **Know when to query data** (availability, prices, order status) **vs. when to query policies** (returns, hours, payment methods) — i.e., routing/tool-selection is a first-class evaluation target.
4. Handle **out-of-scope questions** appropriately.

**Technical:**
- **Python as the main language** — the only hard technical constraint.
- Free choice (but justified in README) of: agent approach (RAG, function calling, ReAct, SQL agent, hybrid), model/provider (paid/free, local/API), interface (CLI, notebook, API, simple UI), conversation-history persistence ("implement if it makes sense for UX"), data treatment ("do what you judge necessary").

**Deliverables:**
1. **Public GitHub repo** with a commit history showing *real progress* — explicitly: no force-push of everything into one commit; no changes after the submission deadline.
2. **README.md** containing: (a) full run instructions (env setup, model provider, commands); (b) justification of technical decisions (framework, LLM, retrieval architecture, prompt strategy); (c) known limitations + what you'd do with more time; (d) **how you used AI coding assistants** — they want to see your workflow; sophisticated use is a plus.
3. **3–5 example conversations** (`.md`, `.txt`, or images) covering varied scenarios; **at least one non-trivial** (live data query or policy-rule application). Suggested scenarios: guitars under R$1000 (catalog filter), store address (general info), Takamine GD20 price (price lookup), "I regret my purchase, can I return it?" (return-policy application).

**Submission:** reply to the process email with the repo link, by the deadline stated in that email (deadline is *not* in the PDF — check the email).

---

## 3. Implicit requirements (hidden in the policies PDF)

The policies manual is written *for the service team including the virtual assistant* (§10 says so explicitly). It effectively contains **behavioral requirements for the agent**:

- **Never state prices, stock, or deadlines without consulting the system** (§7.1 "Informações precisas") — this is an anti-hallucination requirement; a grounded tool-first design is expected.
- **Out-of-stock product** → say it's temporarily unavailable and **suggest similar alternatives**; never confirm availability without checking current stock (§7.3).
- **Discontinued product** → say it left the catalog and **offer equivalents/successors** (§7.3).
- **Expired promotion** → check `is_active`; be transparent, present the current price; **never promise an expired discount** (§7.3).
- **Promotional prices must always be shown with the original price and the discount %** (§6.2).
- **Promotions are not cumulative**; the 5% PIX discount does **not** apply on top of promotional prices (§6.2).
- **Scope**: instruments only; requests for accessories (strings, cables, picks, pedals, amps, cases) must be **politely redirected**, suggesting partner stores when possible (§7.1).
- **Tone of voice**: "informal but professional — like a friend who knows music"; avoid robotic/overly formal language (§7.1). Conversations should be in **PT-BR**.
- **Standard service flow**: greet (by name if available) → understand need → consult system → answer clearly with prices/conditions → confirm anything else + cordial close (§7.2).
- **Complaints** → listen with empathy, register, escalate to a human; 24-business-hour response commitment (§7.3).
- **Off-hours**: the assistant must inform when the store will respond (§2, §7.1).
- **LGPD** (§9): personal data used only for stated purposes → implies the agent must **not leak one customer's data to another** (order lookup should require some identity verification, e.g., matching name + phone/email or order id).
- **When policy application is unclear, consult management before informing the customer** (§10) → implies an "escalate to human" fallback behavior.

### Key policy facts the agent must answer correctly
- Address: Rua 14 de Maio, 3200 — Centro, Campo Grande–MS, CEP 79202-333. Founded 2008.
- Hours: Mon–Fri 09:00–18:00; Sat 09:00–13:00; Sun/holidays closed.
- Payment: PIX (5% off), debit, credit up to 12x interest-free (min. installment rules: ≤3x no minimum except <R$50; 4–6x min R$80; 7–12x min R$100), boleto (compensates in up to 3 business days). Mixed payment allowed above R$2,000.
- Returns: 7-day regret window (online purchases, original packaging, store pays return shipping, refund in ≤10 business days); 30-day defect exchange (after that, manufacturer warranty; store can intermediate); 7-day preference exchange (subject to availability); **not exchangeable**: customized/setup instruments, "final sale" clearance items, wind-instrument mouthpieces.
- Shipping: metro Campo Grande — free ≥R$500, else flat R$35, 1–3 business days, own courier; elsewhere — PAC 5–12 d, SEDEX 2–5 d, Jadlog 3–8 d, all tracked & insured; big items need individual quotes. Tracking code format `BR#########BR`, sent by email/WhatsApp on dispatch.
- Warranty: 90-day legal + 6–24-month manufacturer; excludes natural wear, misuse, unauthorized repairs, cosmetic damage.

---

## 4. Data audit — findings, traps, and quality issues

These look **deliberately planted** to test whether the candidate actually inspects the data ("Tratamento dos dados: faça o tratamento que julgar necessário").

### 4.1 Product catalog (`products.csv`, 65 rows, ids 81–145)
- **Name ↔ description mismatches** (clear traps) in ids 135–144: e.g., id 135 "Music Man Bass 1X" described as a *Fender Jazz Bass*; id 136 "Ibanez Bass 2X" described as a *Precision*; id 139 "Bateria Yamaha Kit 1" described as a *Pearl Export*; id 140 "Pearl Kit 2" described as a *Tama*; id 142 "Korg Synth 1" described as a *Roland workstation with 88 keys* while `specs` says 61 keys; id 144 "Roland Synth 3" described as a *Yamaha arranger*. → Decide a source of truth (recommend: `name` + `specs` as canonical, treat description as unreliable marketing text; document the decision).
- **Empty categories**: categories 6, 7, 8 (woodwinds, brass, orchestral strings) have **zero products**, although the policy PDF claims a 300+ instrument catalog including them. Only categories 1, 2, 3, 4, 5, 9 have products. The agent must gracefully handle "do you have saxophones?" (in-scope per policies, but no data).
- **Status values**: `active`, `discontinued` (ids 113, 136), `coming_soon` (id 130). Also **id 96 is `active` with stock 0** — the canonical out-of-stock test case (and it's the "Giannini GF-3D" ~R$799.90, matching the suggested conversation about violões).
- `specs` is a JSON string embedded in the CSV (needs parsing; keys differ per category).
- Prices span R$159.90 – R$19,567 (float; needs PT-BR currency formatting `R$ 1.234,56`).

### 4.2 Orders (`orders.csv` + `order_items.csv`)
- Statuses: `pending`, `confirmed`, `shipped`, `delivered`, `cancelled`. Only delivered/shipped rows have tracking codes; cancelled rows have a `notes` reason (e.g., "payment not confirmed"). Dates range 2025-10-15 → 2026-03-22 (all in the past relative to today).
- **Order 3 total mismatch**: 2 × product 130 (R$1,749 each = R$3,498) vs. recorded total R$3,450 — and product 130 is `coming_soon` yet was *delivered* in Dec 2025. Minor inconsistency worth a note, not a blocker.
- Order lookup requires joining orders → order_items → products.

### 4.3 Customers (`customers.csv`, 50 rows)
- **Near-duplicate names**: "Bruno Carvalho Martins" (11) vs "Bruno Carvalho" (27) vs "Bruno Martins" (43); "Diego Fernandes Castro" (13) vs "Diego Castro" (47); "Letícia Gonçalves Rocha" (14) vs "Leticia Gomes" (44), etc. → Name alone is **not** a safe key for order lookup; supports the LGPD-driven design of verifying phone/email (or order id) before disclosing order data.
- Fake email domains (jmail, coldmail, inlook, hayoo) — fine, it's synthetic data.

### 4.4 Promotions (`promotions.csv`, 25 rows)
- **Only 4 active**: product 127 (10%), 121 (20%), 90 (18%), 94 (8%). All others `is_active = 0`, including tempting ones (40% off product 96). Tests whether the agent filters on `is_active` and refuses to honor expired discounts.
- Products 93, 96, 99 appear in multiple (inactive) promotions — dedupe/filter needed.

### 4.5 Internal inconsistencies in the policies PDF
- **Two phone numbers**: cover/company table says (67) 3341-4444 (phone/WhatsApp); §7 says the WhatsApp channel is **(67) 3321-4500**. → Assume 3341-4444 = store phone/WhatsApp general line, 3321-4500 = the service channel this agent lives on; document the assumption.
- **Email typo** in the company table: `contato@empóriodamusica.com.br` (accented "ó") vs. the cover's `contato@emporiodamusica.com.br`. Use the unaccented one (accented domains in that form are invalid); document.

---

## 5. What is likely being evaluated (reading between the lines)

| Dimension | Evidence in the statement | What a strong submission shows |
|---|---|---|
| **Agent-engineering judgment** | "RAG, function calling, ReAct, SQL agent, hybrid… justify" | A *fit-for-purpose* choice (e.g., function calling + light retrieval) with honest trade-off discussion — not maximal complexity |
| **Grounding / anti-hallucination** | Policy §7.1 "never inform price/stock without consulting the system" | Every price/stock/order answer traceable to a tool call; refusal to invent |
| **Routing data vs. policies** | Core bullet of "what to build" | Clean separation: structured tools for CSVs, retrieval/context for the PDF |
| **Edge-case & data handling** | Planted traps (stock 0, discontinued, inactive promos, name/description conflicts, duplicate customer names) | The traps are detected, decisions documented, agent behaves per policy §7.3 |
| **Scope discipline** | "Handle off-topic questions"; policy scope section | Polite refusal + redirect for accessories/off-topic; no jailbreak into general chatbot |
| **Persona & UX quality** | "Persona aligned with identity and tone"; §7.1–7.2 | Consistent PT-BR persona, warm-but-professional, follows the 5-step service flow |
| **Software craft** | Python requirement; repo + README deliverables | Clear structure, typing, tests, error handling, easy setup |
| **Process & communication** | Commit-history rule; README justifications; "document assumptions" | Incremental commits, decision log, assumptions section |
| **AI-assisted workflow maturity** | Dedicated README bullet on assistant usage | Transparent, structured description of how AI tools were used (this planning workflow itself is evidence) |
| **Autonomy under ambiguity** | "Dúvidas?" section: assume, document, move on | No blocking questions; reasonable documented assumptions |

---

## 6. Technology surface likely required

- **Python 3.11+**, dependency manager (`uv` or `poetry`), `.env` config.
- **LLM provider**: one primary (e.g., Anthropic Claude or OpenAI via API; or a free tier like Groq/Gemini, or local Ollama) — must be justified; ideally provider-agnostic or cheap/free to let evaluators run it.
- **Agent layer**: either a thin framework (LangGraph, PydanticAI, OpenAI Agents SDK) or direct SDK function-calling loop. Given the case size, a lightweight, inspectable approach is defensible and shows understanding rather than framework dependence.
- **Data layer**: pandas or **SQLite** loaded from the CSVs (SQLite gives clean, testable query tools and an easy path to "SQL agent" talking points).
- **Policy layer**: PDF → markdown; either (a) full-document context injection (it's only ~3–4k tokens — cheapest, zero retrieval risk) or (b) chunked RAG with embeddings (demonstrates retrieval architecture). A documented hybrid (structured store-facts + retrieval or full-context) is the sweet spot; the choice must be argued either way.
- **Interface**: CLI chat (e.g., `rich`) at minimum; optional simple UI (Streamlit/Gradio) or FastAPI endpoint — "the focus is the agent working correctly."
- **Testing**: pytest for tools/data layer; a small scripted eval set for agent behaviors.
- **Tooling**: ruff/black, GitHub repo, conventional commits.

---

## 7. Ambiguities & assumptions to document in the README (per the case's own instruction, assume-and-document rather than ask)

1. **Submission deadline** — only in the process email. *(The one thing the user must check themselves.)*
2. **"Current date" semantics** for order status/delivery estimates (data ends 2026-03; assume system date, or pin a reference date for reproducibility).
3. **Identity verification for order lookups** — not required explicitly; assume LGPD-motivated light verification (order id, or name + registered phone/email) given duplicate-name data.
4. **Conflicting phone numbers / email typo** in the policy PDF — pick and document (see §4.5).
5. **Source of truth for product name/description conflicts** — recommend name+specs; document.
6. **Empty categories vs. "300+ instruments" claim** — agent answers from actual data, offers what exists.
7. **Language** — PT-BR for agent persona and example conversations (audience is Brazilian customers); README language (PT-BR recommended since evaluators are Brazilian; EN acceptable).
8. **Model budget** — whether evaluators will run with their own API key; mitigate with a free-tier/local option or very cheap default model and a clear `.env.example`.
9. **Conversation persistence** — optional per statement; in-session memory is required UX-wise; cross-session persistence is a justified nice-to-have.
10. **Prototype, not production**: no real WhatsApp integration expected — a text interface simulating the channel is sufficient (but architecting so a channel adapter could be added is a talking point).

---

## 8. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Agent hallucinates prices/stock | Fails the central evaluation criterion | Tool-first design; system prompt forbids unverified claims; eval tests |
| Over-engineering (heavy framework, vector DB for a 3k-token PDF) | Signals poor judgment | Right-size; justify simplicity explicitly |
| Under-engineering (prompt-stuffing everything, no tools) | Fails "knows when to query data vs. policies" | Function-calling with distinct tools per source |
| Missing the data traps | Evaluators planted them | Data-audit step + explicit handling + README notes |
| LGPD leak (order data by name alone) | Professionalism red flag | Verification step in the order tool |
| Commit history looks fake / single dump | Explicit disqualifier in the statement | Incremental commits from day one, per work phase |
| Evaluator can't run the project | README criterion | Pinned deps, `.env.example`, one-command setup, cheap/free model path |
| Repo changed after deadline | Explicit disqualifier | Freeze after submission; tag the release |
