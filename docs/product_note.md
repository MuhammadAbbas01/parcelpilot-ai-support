# Product Note

## Additional client problem chosen: Proactive Issue Detection
Built a rule-based (not LLM-per-load) internal dashboard
(`/dashboard.html`, `backend/insights.py`) with three views:
1. **SLA risk** — every open ticket ranked by elapsed time vs. its
   first-response target, with severity inferred from
   subject/description and contract overrides applied per account.
2. **Issue clusters** — open tickets grouped by shared keywords, so a
   pattern like "3 customers all reporting bulk-upload failures" is
   visible at a glance instead of buried across separate tickets.
3. **Order anomalies** — carrier-fault orders with pickup still
   pending, surfaced *before* the customer files a ticket about it.

Chose rule-based over an LLM call on every dashboard load because it's
free, instant, and fully reproducible — appropriate for a small,
well-structured dataset. Trust/reliability (Problem 2) wasn't ignored
either: it's addressed as a cross-cutting requirement in the core
chatbot itself (authority ranking, deprecated-doc exclusion,
confirm-before-action), since a system that can't be trusted on single
questions can't be trusted with a dashboard's aggregate claims either.

## What I'd build next, in priority order
1. **Real business-hours calendar** for SLA math — the current flat
   hour-count approximation is the single biggest accuracy gap between
   this demo and something a support team would actually rely on.
2. **Persistent storage** (Postgres) for sessions and action logs —
   currently in-memory, lost on restart.
3. **Customer-facing chatbot** — this build is internal-only by
   choice, to go deep on one context rather than shallow on two; a
   customer-facing agent would reuse the same tools with
   account_id-scoped access instead of role-scoped.
4. **Alerting off the dashboard** (Slack/email when a ticket crosses
   "approaching" SLA) — right now someone has to open the page.
5. **Embeddings-based document search** — only matters once the real
   doc pack grows past what fits comfortably as ranked keyword chunks.
6. **Outcome feedback loop** — flag when a *current* ticket's
   resolution contradicts an earlier "historical_resolution" note, so
   wrong past guidance (like TKT-450/451 in this dataset) gets
   corrected at the source instead of silently overridden every time.

## What I intentionally left out
- The customer-facing chatbot (see above — depth over breadth).
- A real database — sessions are in-memory and reset on restart.
- A real business calendar for SLA hours.
- Automated alerting from the insights dashboard.
- CI/CD, tests beyond manual verification against the brief's own
  example question.

## One metric I'd use
**Precision on non-escalated answers**: of the answers the assistant
gives directly (i.e. doesn't escalate), what fraction are actually
correct? For a support tool, a confidently wrong answer is worse than
an unnecessary escalation — so this metric punishes exactly the
failure mode the brief calls out as the biggest adoption risk, rather
than rewarding raw answer volume.
