"""
Tool 3: State-changing actions (mocked locally — no real ticketing system).

Two-phase flow enforced HERE (not just via prompting):
  1. propose_action() computes what WOULD happen and returns a
     confirmation_token, but writes nothing.
  2. execute_action() requires that exact token to actually write.
This means even if the model "decides" to skip confirmation, there is no
tool call that performs the write without a valid token from step 1 —
the gate lives in code, not in instructions.
"""
import uuid
from models import PendingAction

_PENDING: dict[str, PendingAction] = {}
_ACTION_LOG: list[dict] = []


def propose_action(action_type: str, payload: dict) -> dict:
    token = str(uuid.uuid4())
    _PENDING[token] = PendingAction(action_type=action_type, payload=payload,
                                     confirmation_token=token)
    return {"confirmation_token": token, "action_type": action_type,
            "payload": payload, "status": "awaiting_user_confirmation"}


def execute_action(confirmation_token: str) -> dict:
    pending = _PENDING.pop(confirmation_token, None)
    if not pending:
        return {"error": "Invalid or already-used confirmation token. "
                          "Propose the action again."}
    record = {"action_type": pending.action_type, "payload": pending.payload,
              "executed": True}
    _ACTION_LOG.append(record)
    return record


def get_action_log() -> list[dict]:
    return _ACTION_LOG
