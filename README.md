# ParcelPilot Internal Ops Assistant

**An AI agent for ParcelPilot's internal support & operations team** —
built for the CalQuity AI Engineer first-round assessment.

A tool-using LLM agent that answers real support questions by reasoning
across signed customer contracts, current policy documents, product
known-issues, and live account/order/ticket data — correctly resolving
conflicts between sources instead of guessing, and requiring explicit
human confirmation before taking any state-changing action.

> **Live example, verified end-to-end:** *"Can Northstar cancel
> ORD-1001 without a cancellation fee? Explain why."*
> The agent calls `get_order` → `get_account` → `search_documents`,
> correctly ranks Northstar's signed Enterprise Agreement above the
> general Cancellation SOP, and answers **yes — the contract waives
> the fee regardless of timing, which overrides the SOP's standard
> 30-minute / ₹250 rule.** See `docs/architecture_note.md` for the
> full tool-trace.

---

## Why this isn't just a wrapper around an LLM

Three things this build treats as first-class, not afterthoughts:

1. **Source authority is data, not a prompt suggestion.** Every
   document has a rank (`contract` > `policy`/`sop` > `product_doc`);
   deprecated documents are filtered out of retrieval entirely — the
   model can't accidentally cite them even if it wanted to.
2. **Access control lives in the tool layer.** Role checks happen
   inside `tools/structured_data.py`, not just in the system prompt —
   so a prompt-injection attempt against the model still can't reach
   data it shouldn't.
3. **State-changing actions are structurally two-phase.**
   `propose_action` computes what *would* happen and returns a
   one-time token; `execute_action` requires that exact token. There
   is no code path where the model can skip confirmation, even if it
   "decides" to.

---

## What's included

| Requirement | Where |
|---|---|
| Natural-language chatbot | `frontend/index.html` + `backend/agent.py` |
| Document retrieval tool | `tools/document_search.py` |
| Structured-data/calc tool | `tools/structured_data.py` |
| State-changing action tool | `tools/actions.py` |
| Confirm-before-action | Two-phase `propose_action`/`execute_action` |
| Multi-step reasoning | Verified: order → account → contract → SOP → answer |
| Access control | Role checks in the data layer, not the prompt |
| Chat interface showing tool use | Live tool-call trace rendered inline |
| **Bonus — Proactive Issue Detection** | `backend/insights.py` + `/dashboard.html` |

---

## Quick start

```bash
git clone <this-repo-url>
cd ParcelPilot_AI_Support
pip install -r requirements.txt
```

Get a free Groq API key at [console.groq.com](https://console.groq.com)
(no credit card required), then create a `.env` file in the project
root:

```
GROQ_API_KEY=your_key_here
```

**Data pack:** this repo does not include CalQuity's supplied PDFs/xlsx
(see *Data Pack* below) — drop the 7 files into `data_pack/` at the
project root, matching the original filenames.

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000** for the chatbot, or
**http://localhost:8000/dashboard.html** for the proactive issue
dashboard (requires `ops_manager` or `admin` role, selectable in the
chat UI's role dropdown).

### Data Pack
The assessment's PDFs and spreadsheet are CalQuity's material, not
redistributed here. Place them at:
```
data_pack/
  01_Support_Policy_v3_CURRENT.pdf
  02_Support_Policy_v2_DEPRECATED.pdf
  03_Cancellation_and_Service_Credit_SOP_v4.pdf
  04_Product_Operations_Guide_and_Known_Issues.pdf
  05_Northstar_Logistics_Enterprise_Agreement.pdf
  06_LumenWorks_Service_Agreement.pdf
  ParcelPilot_Assessment_Data.xlsx
```
`backend/data_loader.py` reads the xlsx directly at startup;
`tools/document_search.py` contains pre-extracted, authority-ranked
text from the PDFs (see *Design Decisions* below for why this wasn't
built as a vector index).

---

## Architecture

```
User (chat UI or dashboard)
        │
        ▼
  FastAPI (main.py) ── mocked auth via X-User-Role / X-User-Name headers
        │
        ▼
  Agent loop (agent.py) ── Groq tool-use API, ≤6 tool rounds/turn
        │
        ├── search_documents / search_deprecated_history
        │     └── tools/document_search.py — authority-ranked text
        │         from the 6 supplied PDFs
        │
        ├── get_account / get_order / get_tickets_for_account /
        │   get_all_open_tickets / calc_late_pickup_hours /
        │   calc_minutes_since_booking / get_dataset_snapshot_time
        │     └── tools/structured_data.py — role-checked access to
        │         data loaded from the xlsx via data_loader.py
        │
        └── propose_action / execute_action
              └── tools/actions.py — two-phase confirm-before-write
```

`backend/insights.py` runs independently of the chat agent — a
deterministic, rule-based pass over the same underlying data — and
powers the proactive issue dashboard without spending an LLM call per
page load.

## Model & hosting notes

- **LLM:** Groq (`openai/gpt-oss-120b`), free tier, OpenAI-compatible
  tool-calling API. Groq's available model lineup changes over time —
  the model name is isolated to one constant in `agent.py` so a swap
  never touches the tool logic. If you see a `model_not_found` error,
  check `console.groq.com/docs/models` and update it there.
- **Hosting:** designed for free-tier deployment on **Hugging Face
  Spaces** (Docker SDK) — see `Dockerfile`. Render's free web-service
  tier also works but sleeps after idle periods.

---

## Design decisions worth knowing about

- **Keyword search over a vector index for documents.** The supplied
  pack is 6 short (one-page) PDFs — an embedding pipeline would add
  latency and infrastructure for zero retrieval-quality benefit at
  this scale. The `search_documents` interface is stable, though: the
  authority-ranking and deprecated-filtering logic sits *around* the
  retrieval call, so swapping in a vector store later is a one-function
  change, not a redesign.
- **"Business hours/days" simplified to flat hour counts** (1 business
  day = 8h) in SLA and cluster calculations. Correct trade-off for a
  synthetic snapshot dataset; would need a real business calendar
  (weekends, holidays, LumenWorks' "no after-hours coverage" clause)
  for production use — flagged explicitly in `docs/product_note.md`.
- **In-memory session storage.** Conversation history resets on
  restart. Right call for a single-instance demo; would move to
  Redis/Postgres for anything multi-instance or production-grade.
- **Internal-only, not customer-facing.** The brief allows either or
  both; this build goes deep on the internal ops context (including
  the proactive-detection bonus) rather than building both contexts
  shallowly. A customer-facing agent would reuse the same tool layer
  with account-scoped access instead of role-scoped.

Full reasoning for all of the above — including what's explicitly out
of scope and why — is in `docs/architecture_note.md` and
`docs/product_note.md`.

## Project structure

```
backend/
  models.py          Pydantic schemas (Account, Order, Ticket, UserContext)
  data_loader.py      Loads real data from the xlsx at startup
  agent.py            Groq tool-use loop + system prompt (authority rules)
  insights.py          Proactive issue detection (SLA risk, clusters, anomalies)
  main.py             FastAPI app, mocked auth, routes
  tools/
    document_search.py   Authority-ranked retrieval over the PDF pack
    structured_data.py   Account/order/ticket lookups + calculations
    actions.py            Two-phase state-changing action tool
frontend/
  index.html / app.js       Chat UI, shows live tool-call trace
  dashboard.html / .js       Proactive issue detection dashboard
docs/
  architecture_note.md   Agent/tool design, conflict handling, trade-offs
  product_note.md        Chosen bonus problem, roadmap, scope, one metric
  ai_tool_usage.md        How AI coding tools were used in this build
data_pack/               (gitignored — see "Data Pack" above)
```

## AI tool usage

See `docs/ai_tool_usage.md`.
