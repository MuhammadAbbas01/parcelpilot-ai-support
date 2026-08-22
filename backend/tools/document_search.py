"""
Tool 1: Document search/retrieval over the real ParcelPilot data pack.
Text below was extracted from the 6 supplied PDFs (each is short — one
page — so each is stored as 1-2 logical chunks rather than requiring a
vector index; this can be swapped for embedding-based retrieval if the
real docs were longer).

Authority order when sources conflict (highest wins):
  1. Customer-specific agreement (overrides general policy for that account)
  2. Current policy / SOP (v3 / v4, marked CURRENT)
  3. Product ops guide / known issues (factual, not policy)
  4. Deprecated policy versions -> NEVER used to answer, only surfaced if
     explicitly asked about history
  5. Historical ticket resolutions -> context only, may be WRONG (see
     TKT-450, TKT-451 in the data pack), never the basis for an answer
"""
DOC_REGISTRY = [
    {"filename": "01_Support_Policy_v3_CURRENT.pdf", "authority": "policy", "status": "current",
     "chunks": [
        "Support Policy v3, CURRENT, effective 1 May 2026, supersedes v2. "
        "Source precedence: signed customer agreement first, then current support policy, "
        "then current product documentation. Historical tickets are context only.",
        "Severity: P1 Critical = complete production outage / confirmed security incident / "
        "credential exposure / immediate material business risk with no workaround. "
        "P2 High = major feature unavailable or degraded but workaround exists. "
        "P3 Normal = minor defect, how-to, config request, limited impact. "
        "Default first-response targets: Enterprise P1 30min 24x7 / P2 2hr / P3 1 business day. "
        "Growth P1 2 business hours / P2 4 business hours / P3 2 business days. "
        "Standard P1 4 business hours / P2 1 business day / P3 2 business days. "
        "P1 incidents should be escalated immediately; if a target is already breached, state the "
        "breach clearly and recommend escalation.",
     ]},
    {"filename": "02_Support_Policy_v2_DEPRECATED.pdf", "authority": "policy", "status": "deprecated",
     "chunks": ["Support Policy v2, DEPRECATED, DO NOT USE FOR CURRENT REQUESTS, superseded by v3 "
                "effective 1 May 2026. Retained for historical reference only."]},
    {"filename": "03_Cancellation_and_Service_Credit_SOP_v4.pdf", "authority": "sop", "status": "current",
     "chunks": [
        "Cancellation & Service Credit SOP v4, CURRENT, effective 15 June 2026. "
        "Order cancellation: DRAFT may be cancelled free. BOOKED-not-yet-PICKED_UP may be cancelled; "
        "no fee within 30 minutes of booking; after 30 minutes charge INR 250 unless a customer "
        "agreement explicitly waives the cancellation fee. PICKED_UP: do not cancel, use "
        "return-to-origin workflow. DELIVERED: cannot be cancelled.",
        "Failed-pickup service credits: under the default policy, eligible when pickup is more than "
        "2 hours past the end of the scheduled pickup window, the carrier is at fault, and there is "
        "no customer-caused issue. Default credit is the lower of INR 500 or 10% of the shipment fee. "
        "A signed customer agreement may replace the default threshold, credit amount, or cap. "
        "Any individual credit above INR 1,000 requires manager approval. Do not promise a credit "
        "when carrier fault, pickup timing, or customer fault is unknown; flag conflicts for "
        "verification before any state-changing action.",
     ]},
    {"filename": "04_Product_Operations_Guide_and_Known_Issues.pdf", "authority": "product_doc", "status": "current",
     "chunks": [
        "Product Operations Guide, updated 14 August 2026. Plan capabilities: Bulk Upload available "
        "on Growth and Enterprise, up to 5,000 rows per CSV; not included on Standard. BOOKED means "
        "shipment created but pickup not yet confirmed; PICKED_UP means carrier pickup confirmed.",
        "KI-208 (opened 10 Aug 2026, Investigating): Growth/Enterprise customers see intermittent "
        "failures on CSV uploads above ~3,000 rows even though the product limit is 5,000; workaround "
        "is to split uploads below 3,000 rows; single-shipment creation unaffected. "
        "KI-211 (opened 12 Aug 2026, Monitoring): SwiftShip pickup webhooks can arrive up to 20 "
        "minutes late — a parcel may be physically collected while ParcelPilot still shows BOOKED; "
        "verify carrier status or wait out the delay window before telling a customer pickup did not "
        "occur. KI-176 (address validation) was resolved 18 Jul 2026 — do not use it to explain new "
        "incidents unless evidence specifically matches it.",
     ]},
    {"filename": "05_Northstar_Logistics_Enterprise_Agreement.pdf", "authority": "contract", "status": "current",
     "account_id": "ACCT-001",
     "chunks": [
        "Northstar Logistics Enterprise Agreement (ACCT-001), term 1 Jan-31 Dec 2026, ACTIVE. "
        "Support terms replace standard policy: P1 15 minutes 24x7, P2 1 hour, P3 8 business hours. "
        "Cancellation: Northstar may cancel any BOOKED shipment before pickup with NO cancellation "
        "fee, regardless of how long ago it was booked; once PICKED_UP the standard return-to-origin "
        "process applies. Service credits: monthly aggregate capped at INR 5,000; otherwise the "
        "current ParcelPilot service-credit SOP applies. Dedicated CSM: Priya Mehta.",
     ]},
    {"filename": "06_LumenWorks_Service_Agreement.pdf", "authority": "contract", "status": "current",
     "account_id": "ACCT-002",
     "chunks": [
        "LumenWorks Service Agreement (ACCT-002), Growth plan, term 1 Mar 2026-28 Feb 2027, ACTIVE. "
        "Support terms: P1 2 business hours, P2 4 business hours, P3 2 business days; no weekend or "
        "after-hours coverage. Cancellation: no special fee waiver, use the current SOP as-is. "
        "Failed-pickup credits: if pickup is more than 4 hours past the end of the scheduled window, "
        "carrier at fault, and customer not at fault, LumenWorks receives a FIXED INR 300 credit — "
        "this replaces the SOP's default amount and timing threshold for this account.",
     ]},
]


AUTHORITY_RANK = {"contract": 3, "policy": 2, "sop": 2, "product_doc": 1}


def search_documents(query: str, account_id: str | None = None) -> list[dict]:
    """Keyword search over DOC_REGISTRY. Small, fixed doc set (7 short
    PDFs) makes keyword matching sufficient here; swap for embedding
    similarity if the real pack were larger — the return shape and
    authority-ranked sort stays the same either way."""
    query_terms = [t for t in query.lower().split() if len(t) > 2]
    results = []
    for doc in DOC_REGISTRY:
        if doc["status"] == "deprecated":
            continue  # never surfaced unless explicitly asked for history
        if doc.get("account_id") and doc["account_id"] != account_id:
            continue  # a contract belonging to another account is invisible
        for chunk in doc["chunks"]:
            text = chunk.lower()
            if any(term in text for term in query_terms) or not query_terms:
                results.append({
                    "filename": doc["filename"], "authority": doc["authority"],
                    "rank": AUTHORITY_RANK.get(doc["authority"], 0), "snippet": chunk,
                })
    return sorted(results, key=lambda r: -r["rank"])


def search_deprecated_history(query: str) -> list[dict]:
    """Separate, explicit tool for when a user asks about past/superseded
    policy — never called by the default search path."""
    return [{"filename": d["filename"], "chunks": d["chunks"]}
            for d in DOC_REGISTRY if d["status"] == "deprecated"]
