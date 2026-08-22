<div align="center">

# ParcelPilot AI Ops Assistant

**A tool-using LLM agent for logistics support & operations** — built for the CalQuity AI Engineer assessment

[![Python](https://img.shields.io/badge/python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Groq](https://img.shields.io/badge/LLM-Groq%20%7C%20gpt--oss--120b-F55036)](https://groq.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

**Live demo:** https://extraversive-intendedly-nathalie.ngrok-free.dev
**Test prompts:** [`docs/test_prompts.md`](docs/test_prompts.md)

</div>

---

## Overview

ParcelPilot is a B2B logistics platform. Its support team fields
questions that require reasoning across signed customer contracts,
support policy, product known-issues, and live order/ticket data —
sources that sometimes disagree with each other. This agent answers
those questions correctly by treating source authority as structured
data rather than something the model has to infer from a prompt, and
it refuses to guess when the sources don't cover a case.

**Verified example:** *"Can Northstar cancel ORD-1001 without a
cancellation fee?"* — the agent calls `get_order` → `get_account` →
`search_documents`, ranks Northstar's signed contract above the
general cancellation SOP, and correctly answers **yes, the contract
waives the fee regardless of timing.** Full trace in
[`docs/architecture_note.md`](docs/architecture_note.md).

## What makes this more than a prompt

- **Authority is enforced in code, not suggested in a prompt.**
  Documents are ranked (`contract` > `policy`/`sop` > `product_doc`)
  and deprecated documents are excluded from retrieval entirely — the
  model cannot cite them even if it tried.
- **Access control lives in the tool layer.** Role checks run inside
  the tool functions themselves, so a prompt-injection attempt still
  can't reach data it shouldn't reach.
- **State-changing actions are structurally two-phase.**
  `propose_action` computes what would happen and returns a one-time
  token; `execute_action` requires that exact token. There's no code
  path that skips confirmation.

## What's included

| Assessment requirement | Where it lives |
|---|---|
| Natural-language chatbot | `frontend/index.html` + `backend/agent.py` |
| Document retrieval tool | `tools/document_search.py` |
| Structured-data / calculation tool | `tools/structured_data.py` |
| State-changing action tool | `tools/actions.py` |
| Confirm-before-action | Two-phase `propose_action` → `execute_action` |
| Multi-step, multi-source reasoning | Verified: order → account → contract → SOP → answer |
| Access control | Role checks in the data layer, not just the prompt |
| Chat UI showing live tool use | Tool-call trace rendered inline, in real time |
| Bonus: proactive issue detection | `backend/insights.py` + `/dashboard.html` |

## Quick start

```bash
git clone https://github.com/MuhammadAbbas01/parcelpilot-ai-support.git
cd parcelpilot-ai-support
pip install -r requirements.txt
```

Get a free Groq API key at [console.groq.com](https://console.groq.com)
(no card required), then create `.env` in the project root:

```
GROQ_API_KEY=your_key_here
```

The synthetic data pack (`data_pack/`) is already included in this
repo, so no manual download step is needed.

```bash
cd backend
uvicorn main:app --reload --port 8000
```

- `http://localhost:8000` — the chatbot
- `http://localhost:8000/dashboard.html` — proactive issue dashboard
  (pick `ops_manager` or `admin` in the role dropdown)

To get a public link like the live demo above, run `ngrok http 8000`
in a second terminal (free ngrok account, no card).

## Architecture

```
User (chat UI or dashboard)
        |
        v
  FastAPI (main.py) -- mocked auth via X-User-Role / X-User-Name headers
        |
        v
  Agent loop (agent.py) -- Groq tool-use API, up to 6 tool rounds/turn
        |
        |-- search_documents / search_deprecated_history
        |     -> tools/document_search.py: authority-ranked text
        |        from the 6 supplied PDFs
        |
        |-- get_account / get_order / get_tickets_for_account /
        |   get_all_open_tickets / calc_late_pickup_hours /
        |   calc_minutes_since_booking / get_dataset_snapshot_time
        |     -> tools/structured_data.py: role-checked access to
        |        data loaded from the xlsx via data_loader.py
        |
        `-- propose_action / execute_action
              -> tools/actions.py: two-phase confirm-before-write
```

`backend/insights.py` runs independently of the chat agent — a
deterministic, rule-based pass over the same underlying data — and
powers the proactive issue dashboard without spending an LLM call on
every page load.

## Hosting

The live demo link above is an **ngrok tunnel to the app running
locally**, not a persistent cloud deployment. That's a deliberate
trade-off: as of mid-2026, every major free-tier host for a
Docker/FastAPI backend has closed its doors — Hugging Face Spaces now
requires a PRO subscription for Docker, Render's free tier asks new
accounts for card verification despite its own marketing, Koyeb
closed free signups after its February 2026 acquisition by Mistral
AI, and Fly.io dropped its free tier back in 2024. Rather than put a
card on file for a hiring-assessment side project, the app runs
locally behind a free tunnel — genuinely live, genuinely free, with
the honest trade-off that it's only reachable while the tunnel process
is running. Full reasoning in [`docs/product_note.md`](docs/product_note.md).

The LLM is Groq's `openai/gpt-oss-120b` on their free tier. Groq's
model lineup changes over time; the model name is isolated to one
constant in `backend/agent.py`, so a lineup change is a one-line fix.

## Design decisions

- **Keyword search, not a vector index**, for the 6 short (one-page)
  PDFs — right-sized for the scale. The authority-ranking logic sits
  around the retrieval call, so swapping in embeddings later is a
  one-function change, not a redesign.
- **"Business hours/days" simplified to flat hour counts** in SLA and
  cluster calculations — a documented gap for production use, not an
  oversight.
- **In-memory sessions** — conversation history resets on restart;
  the right call for a demo, not for production.
- **Internal-only, not customer-facing** — a deliberate depth-over-
  breadth choice. The same tool layer would support a customer-facing
  agent with account-scoped access instead of role-scoped access.

Full reasoning for each of these is in
[`docs/architecture_note.md`](docs/architecture_note.md) and
[`docs/product_note.md`](docs/product_note.md).

## Project structure

| Path | Description |
|---|---|
| `backend/models.py` | Pydantic schemas — `Account`, `Order`, `Ticket`, `UserContext` |
| `backend/data_loader.py` | Loads real data from the xlsx at startup |
| `backend/agent.py` | Groq tool-use loop + system prompt (authority rules) |
| `backend/insights.py` | Proactive issue detection — SLA risk, ticket clusters, order anomalies |
| `backend/main.py` | FastAPI app, mocked auth, routes |
| `backend/tools/document_search.py` | Authority-ranked retrieval over the PDF pack |
| `backend/tools/structured_data.py` | Account/order/ticket lookups and calculations |
| `backend/tools/actions.py` | Two-phase state-changing action tool |
| `frontend/index.html`, `app.js` | Chat UI with live tool-call trace |
| `frontend/dashboard.html`, `dashboard.js` | Proactive issue detection dashboard |
| `docs/architecture_note.md` | Agent/tool design, conflict handling, trade-offs |
| `docs/product_note.md` | Chosen bonus problem, roadmap, scope, one success metric |
| `docs/ai_tool_usage.md` | How AI coding tools were used in this build |
| `docs/test_prompts.md` | 8 verified prompts covering every core capability |
| `data_pack/` | Supplied synthetic assessment data |

---

<div align="center">

Built by **Muhammad Abbas** for the CalQuity AI Engineer assessment.

</div>
