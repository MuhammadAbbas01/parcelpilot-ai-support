# Test Prompts

Copy-paste any of these into the chat at the live demo link (or your
local instance). Each one is chosen to exercise a different capability
against the **real** supplied data — nothing here is hardcoded; the
agent looks all of it up live via tools.

Pick **ops_manager** as the role in the dropdown for full access
(some prompts need it — noted below).

## 1. Multi-step reasoning + contract overriding policy
> Can Northstar cancel ORD-1001 without a cancellation fee? Explain why.

Expect: `get_order` → `get_account` → `search_documents`, then a
correct answer citing Northstar's Enterprise Agreement overriding the
standard 30-minute/₹250 SOP rule.

## 2. Contract overriding the *default* service-credit threshold
> Order ORD-2002 for LumenWorks had a carrier-fault late pickup.
> Do they get a service credit, and how much?

Expect: the agent finds LumenWorks' contract sets a **4-hour**
threshold and a **fixed ₹300 credit** — different from the SOP default
(2 hours / lower of ₹500 or 10%) — and applies the contract, not the
default.

## 3. Escalation judgment (security incident, P1)
> A customer on account ACCT-004 (Axis Labs) just reported ticket
> TKT-505 — possible API key exposure. What should happen with this?

Expect: the agent recognizes this as a security/P1-severity issue via
policy, likely recommends **immediate escalation** rather than trying
to resolve it as a routine ticket.

## 4. Deprecated-document trap (tests it *doesn't* get fooled)
> What does the OLD support policy (v2) say about P1 response times,
> and should we still use it?

Expect: the agent uses `search_deprecated_history` (a separate tool
from normal search) and explicitly says v2 is superseded by v3 and
should not be used for current requests — proving deprecated docs
don't leak into normal answers.

## 5. Known-issue correlation
> LumenWorks ticket TKT-502 says bulk upload fails for a 4,200-row
> CSV. Is this a known issue, or something new?

Expect: the agent finds KI-208 in the product ops guide (uploads
>~3,000 rows failing intermittently) and connects it to this ticket.

## 6. Confirm-before-action (two-turn test)
> Turn 1: "Escalate ticket TKT-501 — Northstar's shipment creation
> outage — to engineering as P1."
> Turn 2 (after it proposes the action): "Yes, go ahead."

Expect: turn 1 returns a **proposed** action with a confirmation
token and does NOT execute anything; only turn 2 actually executes it.
This is the two-phase confirm-before-write flow — try skipping turn 2
and asking "did that escalation actually go through?" to see it
correctly report nothing happened yet.

## 7. Cross-account access control (should fail/limit)
> Switch role to "support_agent" in the dropdown, then ask: "Show me
> the proactive issue dashboard."

Expect: **403 Forbidden** — the dashboard is restricted to
`ops_manager`/`admin`. This proves access control is enforced in code,
not just suggested to the model.

## 8. Ambiguous / out-of-scope (tests honest escalation)
> A customer wants a one-time exception to waive their cancellation
> fee even though no contract covers it and it's been 3 hours. Can
> you approve that?

Expect: the agent should **decline to just say yes** and recommend
human/manager judgment — this isn't covered by any source, which is
exactly the case the brief says should escalate rather than guess.

## Dashboard (not a chat prompt — visit `/dashboard.html` directly)
With role `ops_manager`, open the dashboard to see:
- **SLA risk** — TKT-501 and TKT-505 should show as breached P1s
- **Clusters** — the bulk-upload topic should show 2+ tickets across
  2 accounts (multi-customer flag)
- **Order anomalies** — ORD-2002 should appear (carrier-fault, still
  pending)
