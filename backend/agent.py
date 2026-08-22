"""
Agent orchestration loop using Groq's OpenAI-compatible tool-use API
(free tier, no Anthropic dependency). Internal ops chatbot: authorised
ParcelPilot staff only.
"""
import os
import json
from datetime import datetime
from groq import Groq
from models import UserContext
from tools import document_search, structured_data, actions


def _json_default(o):
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")


client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "openai/gpt-oss-120b"  # current Groq free-tier model with strong tool calling

SYSTEM_PROMPT = """You are ParcelPilot's internal support/ops assistant.
Audience: authorised ParcelPilot staff only (never customers).

Source authority rules (apply strictly):
1. A customer's own signed agreement overrides general policy for that account.
2. Current policy/SOP documents are authoritative for everything not
   overridden by an agreement. NEVER cite a document marked deprecated as
   the basis for an answer.
3. Historical ticket resolution notes are CONTEXT ONLY and may be wrong.
   Never treat them as a source of truth; flag if a past resolution
   contradicts current policy.
4. If sources conflict, or the question requires human judgment, an
   unsupported exception, or an action outside your tools, say so plainly
   and recommend escalation instead of guessing.

For any state-changing action (escalation, ticket update, follow-up task):
call propose_action first, show the user exactly what will happen, and
ONLY call execute_action after the user explicitly confirms in a
follow-up message. Never call execute_action in the same turn as
propose_action.
"""


def _tool(name, description, properties, required):
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties, "required": required}}}


TOOLS = [
    _tool("search_documents",
          "Search policies, SOPs, product docs, and customer agreements. "
          "Returns results ranked by authority (contract > policy/SOP > product doc), "
          "excluding deprecated documents.",
          {"query": {"type": "string"},
           "account_id": {"type": ["string", "null"],
                          "description": "Restricts contract results to this account. Pass null if not scoping to an account."}},
          ["query"]),
    _tool("get_account", "Look up an account's plan tier and whether it has a custom agreement.",
          {"account_id": {"type": "string"}}, ["account_id"]),
    _tool("get_order", "Look up an order's status, carrier, pickup times, and fault party.",
          {"order_id": {"type": "string"}}, ["order_id"]),
    _tool("get_tickets_for_account", "List all tickets for an account.",
          {"account_id": {"type": "string"}}, ["account_id"]),
    _tool("calc_late_pickup_hours",
          "Compute how many hours late a pickup is/was vs the scheduled window end, "
          "plus carrier_fault/customer_fault and shipment_fee_inr.",
          {"order_id": {"type": "string"}}, ["order_id"]),
    _tool("calc_minutes_since_booking",
          "Compute minutes between booking and cancellation request (or now), for the "
          "SOP's 30-minute no-fee cancellation window.",
          {"order_id": {"type": "string"}}, ["order_id"]),
    _tool("get_dataset_snapshot_time",
          "Get the reference 'now' timestamp to use for all time-based reasoning.",
          {}, []),
    _tool("get_all_open_tickets",
          "List all open tickets across every account (internal-only, for spotting patterns "
          "like SLA risk or clusters of similar complaints).",
          {}, []),
    _tool("search_deprecated_history",
          "Look up superseded/deprecated policy text — ONLY use this if the user explicitly "
          "asks what an old policy used to say. Never use it to answer a current question.",
          {"query": {"type": "string"}}, ["query"]),
    _tool("propose_action",
          "Prepare (but do not execute) a state-changing action. Returns a confirmation_token.",
          {"action_type": {"type": "string", "enum": ["create_escalation", "update_ticket", "create_follow_up_task"]},
           "payload": {"type": "object"}}, ["action_type", "payload"]),
    _tool("execute_action",
          "Execute a previously proposed action. Requires the user's explicit confirmation first.",
          {"confirmation_token": {"type": "string"}}, ["confirmation_token"]),
]


def _dispatch(name: str, tool_input: dict, user: UserContext) -> dict:
    """Every tool call is routed through here, and access-control checks
    (role, account scoping) live inside the tool functions themselves —
    the model can request anything, but the data layer decides what it
    actually gets back."""
    if name == "search_documents":
        return {"results": document_search.search_documents(
            tool_input["query"], tool_input.get("account_id"))}
    if name == "get_account":
        return structured_data.get_account(user, tool_input["account_id"])
    if name == "get_order":
        return structured_data.get_order(user, tool_input["order_id"])
    if name == "get_tickets_for_account":
        return {"tickets": structured_data.get_tickets_for_account(user, tool_input["account_id"])}
    if name == "calc_late_pickup_hours":
        return structured_data.calc_late_pickup_hours(user, tool_input["order_id"])
    if name == "calc_minutes_since_booking":
        return structured_data.calc_minutes_since_booking(user, tool_input["order_id"])
    if name == "get_dataset_snapshot_time":
        return structured_data.get_dataset_snapshot_time()
    if name == "get_all_open_tickets":
        return {"tickets": structured_data.get_all_open_tickets(user)}
    if name == "search_deprecated_history":
        return {"results": document_search.search_deprecated_history(tool_input["query"])}
    if name == "propose_action":
        return actions.propose_action(tool_input["action_type"], tool_input["payload"])
    if name == "execute_action":
        return actions.execute_action(tool_input["confirmation_token"])
    return {"error": f"Unknown tool {name}"}


def run_agent(message: str, history: list[dict], user: UserContext) -> dict:
    """Runs one turn of the tool-use loop (OpenAI-style messages, since
    Groq's API is OpenAI-compatible). Returns the final reply plus a
    trace of which tools were called, for the UI's 'which tool is being
    used' requirement."""
    messages = history or [{"role": "system", "content": SYSTEM_PROMPT}]
    messages = messages + [{"role": "user", "content": message}]
    tool_trace = []

    for _ in range(6):  # hard cap so a bad loop can't run forever
        resp = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS, tool_choice="auto",
        )
        choice = resp.choices[0].message

        if not choice.tool_calls:
            messages.append({"role": "assistant", "content": choice.content})
            return {"reply": choice.content, "tool_trace": tool_trace, "messages": messages}

        messages.append({"role": "assistant", "content": choice.content,
                          "tool_calls": [tc.model_dump() for tc in choice.tool_calls]})
        for tc in choice.tool_calls:
            args = json.loads(tc.function.arguments)
            result = _dispatch(tc.function.name, args, user)
            tool_trace.append({"tool": tc.function.name, "input": args, "result": result})
            messages.append({"role": "tool", "tool_call_id": tc.id,
                              "content": json.dumps(result, default=_json_default)})

    return {"reply": "I wasn't able to complete this in the allotted steps — "
                      "escalating to a human.", "tool_trace": tool_trace, "messages": messages}
