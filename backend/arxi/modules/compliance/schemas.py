from datetime import datetime

from pydantic import BaseModel, model_validator


class FieldChange(BaseModel):
    field: str
    from_value: str | None = None
    to_value: str | None = None


class AuditLogEntry(BaseModel):
    id: str
    timestamp: datetime
    action: str
    actor_id: str
    actor_role: str
    resource_type: str
    resource_id: str
    detail: dict | None = None
    changes: list[FieldChange] = []

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def compute_changes(cls, data):
        """Diff before_state and after_state into a changes list."""
        if hasattr(data, "__dict__"):
            # ORM model — extract attributes
            before = data.before_state or {}
            after = data.after_state or {}
            obj = {
                "id": data.id,
                "timestamp": data.timestamp,
                "action": data.action,
                "actor_id": data.actor_id,
                "actor_role": data.actor_role,
                "resource_type": data.resource_type,
                "resource_id": data.resource_id,
                "detail": data.detail,
                "changes": _diff_states(before, after),
            }
            return obj
        # Already a dict
        before = (data.get("before_state") or {})
        after = (data.get("after_state") or {})
        data["changes"] = _diff_states(before, after)
        return data


def _diff_states(before: dict, after: dict) -> list[dict]:
    changes = []
    all_keys = set(list(before.keys()) + list(after.keys()))
    for key in sorted(all_keys):
        old = before.get(key)
        new = after.get(key)
        if old != new:
            changes.append({
                "field": key,
                "from_value": str(old) if old is not None else None,
                "to_value": str(new) if new is not None else None,
            })
    return changes


class AuditLogResponse(BaseModel):
    logs: list[AuditLogEntry]
    total: int
