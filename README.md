<div align="center">

# 📦 ParcelPilot AI Ops Assistant

### A tool-using LLM agent for logistics support & operations — built for the CalQuity AI Engineer assessment

[![Python](https://img.shields.io/badge/python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Groq](https://img.shields.io/badge/LLM-Groq%20%7C%20gpt--oss--120b-F55036)](https://groq.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-live%20demo-brightgreen)](#-live-demo)

**[🚀 Live Demo](#-live-demo)** · **[🧪 Test It Yourself](docs/test_prompts.md)** · **[🏗 Architecture](#-architecture)** · **[📋 Docs](#-documentation)**

</div>

---

## Why this isn't just an LLM wrapper

Most "AI support agent" demos are a system prompt bolted onto a chat
window. This one treats three things as load-bearing, not decoration:

| | |
|---|---|
| 🔒 **Authority is data, not a suggestion** | Every document is ranked (`contract` > `policy`/`sop` > `product_doc`); deprecated docs are filtered out of retrieval entirely — the model literally cannot cite them, prompt or no prompt. |
| 🛡 **Access control lives in the tool layer** | Role checks run inside the tool functions, not the system prompt — a prompt-injection attempt still can't reach data it shouldn't. |
| ✋ **Actions are structurally two-phase** | `propose_action` computes what *would* happen and returns a one-time token; `execute_action` requires that exact token. There is no code path that skips confirmation. |

> **Verified live:** *"Can Northstar cancel ORD-1001 without a
> cancellation fee?"* → the agent chains `get_order` →
> `get_account` → `search_documents`, correctly ranks Northstar's
> signed contract above the general SOP, and answers **yes — the
> fee is waived regardless of timing.** Full tool-trace in
> [`docs/architecture_note.md`](docs/architecture_note.md).

---

## 🚀 Live Demo

**https://extraversive-intendedly-nathalie.ngrok-free.dev**

This is a live tunnel to the app running locally — not a permanent
cloud deployment, and there's a reason for that worth two sentences:
by mid-2026, every major free-tier PaaS for Docker hosting closed its
doors (Hugging Face → PRO-only, Render → card verification, Koyeb →
closed to new signups, Fly.io → no free tier since 2024). Rather than
put a card on file for a hiring assessment, the app runs locally with
a public tunnel in front — genuinely free, genuinely live. Full
reasoning and how to spin up your own link in **[Hosting
notes](#-hosting-notes)**.

**Don't know what to ask it?** → **[docs/test_prompts.md](docs/test_prompts.md)**
has 8 ready-to-paste prompts, each targeting a specific capability
(multi-step reasoning, contract-vs-policy conflicts, the
confirm-before-action flow, access control, and more) — every one
verified working against the real data before being written down.

---

## ✅ What's included

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
| **Bonus: Proactive Issue Detection** | `backend/insights.py` + `/dashboard.html` |

---

## 🏁 Quick start

```bash
git clone https://github.com/MuhammadAbbas01/parcelpilot-ai-support.git
cd parcelpilot-ai-support
pip install -r requirements.txt
```

Get a **free** Groq API key at [console.groq.com](https://console.groq.com)
(no card required), then create `.env` in the project root:

```
GROQ_API_KEY=your_key_here
```

> The synthetic data pack (`data_pack/`) is already included in this
> repo — no manual download step needed.

```bash
cd backend
uvicorn main:app --reload --port 8000
```

- **http://localhost:8000** — the chatbot
- **http://localhost:8000/dashboard.html** — proactive issue dashboard
  (pick `ops_manager` or `admin` in the role dropdown)

Want a public link like the live demo above?
```bash
ngrok http 8000
```

---

## 🏗 Architecture

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
deterministic, rule-based pass over the same data — and powers the
proactive issue dashboard without spending an LLM call per page load.

## 🔌 Hosting notes

The live demo link is an **ngrok tunnel** to the app running locally.
As of mid-2026 every major free-tier Docker/FastAPI host has closed:
Hugging Face Spaces now requires PRO for Docker, Render's free tier
asks new accounts for card verification despite its own marketing,
Koyeb closed free signups after its Feb 2026 Mistral AI acquisition,
and Fly.io dropped its free tier back in 2024. This was a deliberate
trade-off, not an oversight — see `docs/product_note.md` for the full
reasoning. The model, `openai/gpt-oss-120b` on Groq's free tier, is
isolated to one constant in `agent.py` so a lineup change is a
one-line fix.

## 🧠 Design decisions

- **Keyword search, not a vector index**, for the 6 short (one-page)
  PDFs — right-sized for the scale; the authority-ranking logic sits
  *around* retrieval so swapping in embeddings later is a one-function
  change.
- **"Business hours/days" simplified to flat hour counts** in SLA math
  — documented gap for production use.
- **In-memory sessions** — resets on restart, fine for a demo.
- **Internal-only, not customer-facing** — deliberate depth-over-breadth
  choice; same tool layer would support a customer-facing agent with
  account-scoped instead of role-scoped access.

Full reasoning in [`docs/architecture_note.md`](docs/architecture_note.md)
and [`docs/product_note.md`](docs/product_note.md).

---

## 📁 Project structure

```
backend/
  models.py             Pydantic schemas (Account, Order, Ticket, UserContext)
  data_loader.py         Loads real data from the xlsx at startup
  agent.py                Groq tool-use loop + system prompt (authority rules)
  insights.py               Proactive issue detection (SLA risk, clusters, anomalies)
  main.py                  FastAPI app, mocked auth, routes
  tools/
    document_search.py       Authority-ranked retrieval over the PDF pack
    structured_data.py       Account/order/ticket lookups + calculations
    actions.py                 Two-phase state-changing action tool
frontend/
  index.html / app.js        Chat UI, live tool-call trace
  dashboard.html / .js         Proactive issue detection dashboard
docs/
  architecture_note.md       Agent/tool design, conflict handling, trade-offs
  product_note.md              Chosen bonus problem, roadmap, scope, one metric
  ai_tool_usage.md               How AI coding tools were used in this build
  test_prompts.md                  8 verified prompts to try against the live demo
data_pack/                Supplied synthetic assessment data
```

## 📋 Documentation

| Doc | Covers |
|---|---|
| [`docs/architecture_note.md`](docs/architecture_note.md) | Agent design, tool design, source-conflict handling, trade-offs |
| [`docs/product_note.md`](docs/product_note.md) | Chosen bonus problem, what's next, what's out of scope, one success metric |
| [`docs/ai_tool_usage.md`](docs/ai_tool_usage.md) | How AI coding tools were used in this build |
| [`docs/test_prompts.md`](docs/test_prompts.md) | 8 verified prompts covering every core capability |

---

<div align="center">

Built by **Muhammad Abbas** for the CalQuity AI Engineer assessment.

</div>
