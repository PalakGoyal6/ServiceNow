import json
from typing import Optional, Any, Dict
from sqlalchemy.orm import Session
from backend.app.models import Event


def log_event(
    db: Session,
    issue_id: str,
    event_type: str,
    actor_id: Optional[str] = None,
    task_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> Event:
    """
    Appends an immutable audit event to the events table.
    """
    payload_str = json.dumps(payload) if payload is not None else None
    event = Event(
        issue_id=issue_id,
        task_id=task_id,
        actor_id=actor_id,
        type=event_type,
        payload=payload_str,
    )
    db.add(event)
    db.flush()
    return event
