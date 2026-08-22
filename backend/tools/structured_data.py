"""
Tool 2: Structured-data lookup/calculation.
Access control is enforced HERE, not just via model prompting.
"""
from data_loader import ACCOUNTS, ORDERS, TICKETS, DATASET_SNAPSHOT
from models import UserContext


def _check_role(user: UserContext):
    if user.role not in ("support_agent", "ops_manager", "admin"):
        raise PermissionError("Unauthorised role for structured data access.")


def get_dataset_snapshot_time() -> dict:
    """Reference 'now' for all time-based reasoning, per the README sheet."""
    return {"dataset_snapshot": DATASET_SNAPSHOT}


def get_account(user: UserContext, account_id: str):
    _check_role(user)
    acc = ACCOUNTS.get(account_id)
    return acc.model_dump() if acc else {"error": f"No account {account_id}"}


def get_order(user: UserContext, order_id: str):
    _check_role(user)
    order = ORDERS.get(order_id)
    return order.model_dump() if order else {"error": f"No order {order_id}"}


def get_tickets_for_account(user: UserContext, account_id: str):
    _check_role(user)
    return [t.model_dump() for t in TICKETS.values() if t.account_id == account_id]


def get_all_open_tickets(user: UserContext):
    """Internal-only, cross-account view — used for the proactive issue
    detection dashboard, not for per-customer answers."""
    _check_role(user)
    return [t.model_dump() for t in TICKETS.values() if t.status == "open"]


def _now():
    """Reference 'now' is the dataset snapshot time, not wall-clock time —
    per the assessment brief, all time-based questions use this."""
    from datetime import datetime
    return datetime.strptime(DATASET_SNAPSHOT.split(" ")[0] + " " + DATASET_SNAPSHOT.split(" ")[1],
                              "%Y-%m-%d %H:%M")


def calc_late_pickup_hours(user: UserContext, order_id: str) -> dict:
    """How late (vs the end of the scheduled pickup window) an order's
    pickup is. Uses pickup_actual_at if picked up, otherwise the dataset
    snapshot time if still pending. LLM should combine this with
    carrier_fault/customer_fault and the applicable SOP/contract via
    search_documents to decide service-credit eligibility."""
    _check_role(user)
    order = ORDERS.get(order_id)
    if not order:
        return {"error": f"No order {order_id}"}
    if not order.pickup_window_end:
        return {"error": "No scheduled pickup window for this order"}
    reference_time = order.pickup_actual_at or _now()
    delta = reference_time - order.pickup_window_end
    return {
        "order_id": order_id, "status": order.status,
        "late_hours": round(delta.total_seconds() / 3600, 2),
        "still_pending": order.pickup_actual_at is None,
        "carrier_fault": order.carrier_fault, "customer_fault": order.customer_fault,
        "shipment_fee_inr": order.shipment_fee_inr,
    }


def calc_minutes_since_booking(user: UserContext, order_id: str) -> dict:
    """Minutes between booking and cancellation request (or now, if no
    cancellation was requested yet) — needed for the SOP's 30-minute
    no-fee cancellation window."""
    _check_role(user)
    order = ORDERS.get(order_id)
    if not order:
        return {"error": f"No order {order_id}"}
    if not order.booked_at:
        return {"error": "No booked_at time for this order"}
    reference_time = order.cancellation_requested_at or _now()
    delta = reference_time - order.booked_at
    return {
        "order_id": order_id, "status": order.status,
        "minutes_since_booking": round(delta.total_seconds() / 60, 1),
        "cancellation_requested": order.cancellation_requested_at is not None,
    }
