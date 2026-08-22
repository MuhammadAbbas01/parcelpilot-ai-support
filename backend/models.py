"""
Pydantic schemas for ParcelPilot internal ops chatbot.
Field names mirror the real ParcelPilot_Assessment_Data.xlsx columns
(accounts / orders / tickets sheets) exactly.
"""
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime


class Account(BaseModel):
    account_id: str
    account_name: str
    plan: str  # Enterprise / Growth / Standard
    status: str
    csm: Optional[str] = None
    contract_file: Optional[str] = None  # filename of signed agreement, if any
    premium_support: bool = False
    notes: Optional[str] = None


class Order(BaseModel):
    order_id: str
    account_id: str
    carrier: Optional[str] = None
    status: str  # DRAFT / BOOKED / PICKED_UP / DELIVERED
    booked_at: Optional[datetime] = None
    pickup_window_start: Optional[datetime] = None
    pickup_window_end: Optional[datetime] = None
    pickup_actual_at: Optional[datetime] = None
    shipment_fee_inr: Optional[float] = None
    carrier_fault: bool = False
    customer_fault: bool = False
    cancellation_requested_at: Optional[datetime] = None
    notes: Optional[str] = None


class Ticket(BaseModel):
    ticket_id: str
    account_id: str
    created_at: Optional[datetime] = None
    status: str  # open / closed
    subject: Optional[str] = None
    description: Optional[str] = None
    channel: Optional[str] = None
    assigned_to: Optional[str] = None
    last_customer_message_at: Optional[datetime] = None
    historical_resolution: Optional[str] = None  # CONTEXT ONLY - may be wrong


class UserContext(BaseModel):
    """Mocked auth. In prod this would come from an SSO/JWT layer."""
    user_id: str
    role: Literal["support_agent", "ops_manager", "admin"]
    name: str


class ChatRequest(BaseModel):
    message: str
    session_id: str
    user: UserContext


class PendingAction(BaseModel):
    action_type: Literal["create_escalation", "update_ticket", "create_follow_up_task"]
    payload: dict
    confirmation_token: str
