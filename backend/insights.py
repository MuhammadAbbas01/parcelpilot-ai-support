"""
Proactive Issue Detection (Additional Client Problem 1).

Deterministic, rule-based analysis over the real ticket/account/order data
— deliberately NOT another LLM call per dashboard load, so it's fast,
free, and reproducible. Flags: SLA risk, multi-ticket/multi-customer
clusters around the same known issue, and unusual single-ticket signals
(e.g. a security incident) that warrant immediate attention regardless
of volume.

Simplification (documented in the product note): "business hours/days"
in the source policies are treated as flat hour counts (1 business day
= 8h) rather than a real business calendar. Fine for a synthetic
snapshot dataset; would need a real calendar for production.
"""
from datetime import datetime
from data_loader import ACCOUNTS, ORDERS, TICKETS, DATASET_SNAPSHOT

DEFAULT_TARGETS_HOURS = {
    "Enterprise": {"P1": 0.5, "P2": 2, "P3": 8},
    "Growth": {"P1": 2, "P2": 4, "P3": 16},
    "Standard": {"P1": 4, "P2": 8, "P3": 16},
}
# Contract-specific overrides (see 05_Northstar / 06_LumenWorks agreements)
CONTRACT_OVERRIDE_HOURS = {
    "ACCT-001": {"P1": 0.25, "P2": 1, "P3": 8},    # Northstar
    "ACCT-002": {"P1": 2, "P2": 4, "P3": 16},      # LumenWorks
}

P1_KEYWORDS = ["outage", "down", "all shipment", "every user", "security",
               "credential", "exposure", "cannot create any"]
P2_KEYWORDS = ["fails", "failing", "error", "bug", "degraded", "not working"]


def _now():
    d = DATASET_SNAPSHOT.split(" ")
    return datetime.strptime(d[0] + " " + d[1], "%Y-%m-%d %H:%M")


def _infer_severity(subject: str, description: str) -> str:
    text = f"{subject} {description}".lower()
    if any(k in text for k in P1_KEYWORDS):
        return "P1"
    if any(k in text for k in P2_KEYWORDS):
        return "P2"
    return "P3"


def _target_hours(account_id: str, plan: str, severity: str) -> float:
    overrides = CONTRACT_OVERRIDE_HOURS.get(account_id)
    if overrides:
        return overrides[severity]
    return DEFAULT_TARGETS_HOURS.get(plan, DEFAULT_TARGETS_HOURS["Standard"])[severity]


def sla_risk_report() -> list[dict]:
    """Every open ticket, ranked by how close it is to (or past) its
    first-response SLA target."""
    now = _now()
    rows = []
    for t in TICKETS.values():
        if t.status != "open":
            continue
        acc = ACCOUNTS.get(t.account_id)
        severity = _infer_severity(t.subject or "", t.description or "")
        target = _target_hours(t.account_id, acc.plan if acc else "Standard", severity)
        elapsed = (now - t.created_at).total_seconds() / 3600 if t.created_at else 0
        pct = elapsed / target if target else 0
        status = "breached" if pct >= 1 else "approaching" if pct >= 0.8 else "on_track"
        rows.append({
            "ticket_id": t.ticket_id, "account_id": t.account_id,
            "account_name": acc.account_name if acc else t.account_id,
            "subject": t.subject, "inferred_severity": severity,
            "target_hours": target, "elapsed_hours": round(elapsed, 2),
            "sla_status": status,
        })
    order = {"breached": 0, "approaching": 1, "on_track": 2}
    return sorted(rows, key=lambda r: (order[r["sla_status"]], -r["elapsed_hours"]))


TOPIC_KEYWORDS = {
    "bulk_upload_failure": ["bulk upload", "csv"],
    "shipment_creation_failure": ["shipment creation", "http 500", "creating any shipment"],
    "pickup_status_mismatch": ["still shows booked", "pickup"],
    "security_incident": ["api key", "credential", "security"],
}


def cluster_report() -> list[dict]:
    """Groups OPEN tickets by shared topic keywords to surface 'multiple
    tickets, same underlying issue' and 'affects multiple customers'
    patterns that a single-ticket view would miss."""
    open_tickets = [t for t in TICKETS.values() if t.status == "open"]
    clusters = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        matches = [t for t in open_tickets
                   if any(k in f"{t.subject} {t.description}".lower() for k in keywords)]
        if not matches:
            continue
        accounts_affected = sorted({m.account_id for m in matches})
        clusters.append({
            "topic": topic,
            "ticket_count": len(matches),
            "accounts_affected": accounts_affected,
            "multi_customer": len(accounts_affected) > 1,
            "ticket_ids": [m.ticket_id for m in matches],
        })
    return sorted(clusters, key=lambda c: (-c["ticket_count"], -len(c["accounts_affected"])))


def order_anomaly_report() -> list[dict]:
    """Orders where the carrier is at fault and pickup still hasn't
    happened as of the snapshot — a leading indicator of upcoming
    service-credit / cancellation tickets before the customer even
    complains."""
    now = _now()
    rows = []
    for o in ORDERS.values():
        if o.carrier_fault and o.pickup_actual_at is None and o.status != "DELIVERED":
            late_hours = round((now - o.pickup_window_end).total_seconds() / 3600, 2) \
                if o.pickup_window_end else None
            acc = ACCOUNTS.get(o.account_id)
            rows.append({
                "order_id": o.order_id, "account_id": o.account_id,
                "account_name": acc.account_name if acc else o.account_id,
                "carrier": o.carrier, "late_hours": late_hours,
                "status": o.status,
            })
    return sorted(rows, key=lambda r: -(r["late_hours"] or 0))


def full_report() -> dict:
    return {
        "dataset_snapshot": DATASET_SNAPSHOT,
        "sla_risk": sla_risk_report(),
        "clusters": cluster_report(),
        "order_anomalies": order_anomaly_report(),
    }
