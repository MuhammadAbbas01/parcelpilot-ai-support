# Architecture Note

## Agent design
Single-agent tool-use loop against Groq's OpenAI-compatible API
(`openai/gpt-oss-120b`, free tier). One system prompt encodes the
source-authority and confirmation rules; the model is looped up to 6
tool-call rounds per turn (`backend/agent.py:run_agent`). Conversation
history is kept server-side per `session_id` in an in-memory dict —
sufficient for a demo/assessment; would move to Redis/Postgres for
multi-instance production.

## Tool design
Three-plus tools, dispatched through one router (`agent.py:_dispatch`)
so every call path enforces access control in the same place:
- `search_documents` / `search_deprecated_history` — document retrieval
- `get_account`, `get_order`, `get_tickets_for_account`,
  `get_all_open_tickets`, `calc_late_pickup_hours`,
  `calc_minutes_since_booking`, `get_dataset_snapshot_time` — structured
  data + calculation
- `propose_action` / `execute_action` — the state-changing action,
  split into two calls on purpose (see below)

## Document and structured-data handling
The 6 supplied PDFs are short (one page each), so their text was
extracted once and stored as ranked chunks in
`tools/document_search.py` rather than built into a vector index —
correct trade-off for ~7 fixed documents, wrong one if the pack grew to
hundreds of pages (would swap in embeddings + a vector store without
touching the tool's calling contract). The xlsx is loaded via pandas at
startup (`backend/data_loader.py`) into typed Pydantic models
(`Account`, `Order`, `Ticket`), so every tool works with validated data
instead of raw rows.

## Source reliability and conflict handling
Encoded at two levels, not just in the prompt:
- **Data layer**: `AUTHORITY_RANK` (contract=3, policy/SOP=2,
  product_doc=1) sorts every `search_documents` result; documents
  marked `deprecated` are filtered out of the default search path
  entirely and only reachable via the explicit
  `search_deprecated_history` tool, which the system prompt forbids
  using to answer current questions.
- **Prompt layer**: the system prompt states the precedence order
  (contract > policy/SOP > product doc; historical ticket resolutions
  are context-only and may be wrong) and instructs the model to
  surface conflicts and recommend escalation rather than guess.
This was verified against the brief's own example — Northstar/ORD-1001
— where the agent correctly ranks the signed contract above the
general SOP and gives the right answer with the right reasoning.

## Major technical trade-offs
- **Keyword search, not embeddings** — right-sized for 7 short
  documents; would not scale past a few dozen pages.
- **In-memory sessions, no database** — simplest thing that works for
  a demo; loses history on restart, doesn't scale across instances.
- **Mocked auth via request headers** (`X-User-Role`, `X-User-Name`)
  instead of real SSO — explicitly allowed by the brief, but access
  control logic itself lives in the tool functions, not just the
  header check, so swapping in real auth doesn't touch the tools.
- **"Business hours/days" treated as flat hour counts** (1 business
  day = 8h) in the SLA and cluster calculations — a real business
  calendar (weekends, holidays, after-hours per the LumenWorks
  contract) was out of scope for the time available.
- **Free-tier model dependency** — Groq's available model list changed
  under me mid-build (see README); the code isolates the model name to
  one constant in `agent.py` for exactly this reason.
