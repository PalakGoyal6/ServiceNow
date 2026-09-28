from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.models import Task, Issue, Department, TaskDependency, User
from backend.app.services.events import log_event
from backend.app.services.dependencies import (
    recompute_block_states,
    would_create_cycle,
    get_blockers,
)
from backend.app.services.priority import recompute_issue_priorities


# Map of allowed transitions: current_status -> set of allowed next statuses
ALLOWED_TRANSITIONS = {
    "blocked": {"rejected"},  # Staff can only reject a blocked task directly
    "pending": {"in_progress", "waiting_on_student", "resolved", "rejected"},
    "in_progress": {"waiting_on_student", "resolved", "rejected"},
    "waiting_on_student": {"in_progress", "resolved", "rejected"},
    "resolved": {"in_progress"},  # Reopening
    "rejected": set(),  # Terminal state unless reassigned/re-added
}


def get_allowed_transitions_for_task(task: Task) -> List[str]:
    return sorted(list(ALLOWED_TRANSITIONS.get(task.status, set())))


def check_and_update_issue_resolution(db: Session, issue_id: str, actor_id: Optional[str] = None) -> None:
    """
    Checks if all tasks on an issue are resolved or rejected.
    If so (and >=1 is resolved), marks issue as resolved.
    """
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        return

    tasks = db.query(Task).filter(Task.issue_id == issue_id).all()
    if not tasks:
        return

    all_done = all(t.status in ["resolved", "rejected"] for t in tasks)
    has_at_least_one_resolved = any(t.status == "resolved" for t in tasks)

    now = datetime.now(timezone.utc)

    if all_done and has_at_least_one_resolved:
        if issue.status != "resolved":
            issue.status = "resolved"
            issue.resolved_at = now
            issue.updated_at = now
            log_event(
                db=db,
                issue_id=issue_id,
                event_type="issue_resolved",
                actor_id=actor_id,
                payload={"resolved_tasks_count": sum(1 for t in tasks if t.status == "resolved")},
            )
    else:
        if issue.status == "resolved":
            issue.status = "open"
            issue.resolved_at = None
            issue.updated_at = now
            log_event(
                db=db,
                issue_id=issue_id,
                event_type="issue_reopened",
                actor_id=actor_id,
                payload={"reopened_at": now.isoformat()},
            )
    db.flush()


def change_status(
    db: Session,
    task: Task,
    new_status: str,
    actor: User,
    reason: Optional[str] = None,
    note: Optional[str] = None,
) -> Task:
    """
    Validates and executes a task status transition with all side effects.
    """
    old_status = task.status
    if old_status == new_status:
        return task

    # Check permission
    if actor.role != "admin" and (not actor.department_id or actor.department_id != task.department_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only change status of tasks in your department",
        )

    # Validate transition
    allowed = ALLOWED_TRANSITIONS.get(old_status, set())
    if new_status not in allowed and actor.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition task from '{old_status}' to '{new_status}'. Allowed: {list(allowed)}",
        )

    # Rejection requires reason/note
    if new_status == "rejected" and not (note or reason):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A note/reason is required when rejecting a task",
        )

    now = datetime.now(timezone.utc)
    task.status = new_status
    task.updated_at = now

    if new_status == "resolved":
        task.resolved_at = now
    elif old_status == "resolved" and new_status != "resolved":
        task.resolved_at = None

    # Log status change event
    event_payload = {
        "from_status": old_status,
        "to_status": new_status,
        "note": note or reason,
        "department_code": task.department.code if task.department else "",
    }
    event_type = "task_rejected" if new_status == "rejected" else "task_status_changed"
    log_event(
        db=db,
        issue_id=task.issue_id,
        event_type=event_type,
        actor_id=actor.id,
        task_id=task.id,
        payload=event_payload,
    )

    db.flush()

    # 1. Trigger unblocking on dependent tasks if resolving or rejecting
    if new_status in ["resolved", "rejected"]:
        recompute_block_states(db, task.issue_id, actor_id=actor.id)

    # 2. Check rejection fallback to DSW if no non-rejected tasks remain (§8.4)
    if new_status == "rejected":
        all_tasks = db.query(Task).filter(Task.issue_id == task.issue_id).all()
        non_rejected = [t for t in all_tasks if t.status != "rejected"]
        if not non_rejected:
            # Reroute to DSW
            dsw_dept = db.query(Department).filter(Department.code == "DSW").first()
            if dsw_dept and not any(t.department_id == dsw_dept.id for t in all_tasks):
                dsw_task = Task(
                    issue_id=task.issue_id,
                    department_id=dsw_dept.id,
                    status="pending",
                    dept_summary=f"Re-routed to DSW because all previous departments rejected their tasks. Last rejection note: {note or reason}",
                    action_needed="Re-route: previous department marked not relevant",
                    base_priority=task.base_priority,
                    effective_priority=task.effective_priority,
                )
                db.add(dsw_task)
                db.flush()
                log_event(
                    db=db,
                    issue_id=task.issue_id,
                    event_type="department_added",
                    actor_id=actor.id,
                    task_id=dsw_task.id,
                    payload={"department_code": "DSW", "reason": "All previous tasks rejected"},
                )

    # 3. Check overall issue resolution
    check_and_update_issue_resolution(db, task.issue_id, actor_id=actor.id)

    # 4. Recompute priorities
    recompute_issue_priorities(db, task.issue_id)

    db.commit()
    db.refresh(task)
    return task


def student_reopen_issue(db: Session, issue: Issue, student_user: User, message_body: str) -> Task:
    """
    Allows a student to reopen a resolved issue within 7 days (§8.7).
    Reopens the most recently resolved task.
    """
    if issue.status != "resolved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Issue is not resolved",
        )

    now = datetime.now(timezone.utc)
    if issue.resolved_at:
        resolved_utc = issue.resolved_at if issue.resolved_at.tzinfo else issue.resolved_at.replace(tzinfo=timezone.utc)
        if (now - resolved_utc) > timedelta(days=7):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Issues resolved more than 7 days ago cannot be reopened. Please submit a new issue.",
            )

    # Find most recently resolved task
    tasks = db.query(Task).filter(Task.issue_id == issue.id, Task.status == "resolved").order_by(Task.resolved_at.desc()).all()
    if not tasks:
        # If none resolved (e.g. all rejected), take the last modified task
        tasks = db.query(Task).filter(Task.issue_id == issue.id).order_by(Task.updated_at.desc()).all()
    
    if not tasks:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No tasks found to reopen")

    target_task = tasks[0]
    target_task.status = "in_progress"
    target_task.resolved_at = None
    target_task.updated_at = now

    issue.status = "open"
    issue.resolved_at = None
    issue.updated_at = now

    log_event(
        db=db,
        issue_id=issue.id,
        event_type="issue_reopened",
        actor_id=student_user.id,
        task_id=target_task.id,
        payload={"reopen_message": message_body},
    )

    recompute_issue_priorities(db, issue.id)
    db.commit()
    db.refresh(target_task)
    return target_task


def add_department_to_issue(
    db: Session,
    issue_id: str,
    department_code: str,
    note: str,
    actor: User,
    blocked_by_task_id: Optional[str] = None,
) -> Task:
    """
    Adds a new department to an active issue (§8.5).
    """
    dept = db.query(Department).filter(Department.code == department_code).first()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Department '{department_code}' not found")

    existing_task = db.query(Task).filter(Task.issue_id == issue_id, Task.department_id == dept.id).first()
    if existing_task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Department '{department_code}' is already assigned to this issue",
        )

    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    status_initial = "blocked" if blocked_by_task_id else "pending"

    new_task = Task(
        issue_id=issue_id,
        department_id=dept.id,
        status=status_initial,
        dept_summary=f"Added by {actor.full_name}: {note}",
        action_needed=note,
        base_priority=issue.urgency * 20,
        effective_priority=issue.urgency * 20,
    )
    db.add(new_task)
    db.flush()

    if blocked_by_task_id:
        dep = TaskDependency(
            task_id=new_task.id,
            blocked_by_task_id=blocked_by_task_id,
            reason="Configured when department was added",
            created_by=actor.id,
        )
        db.add(dep)
        db.flush()

    log_event(
        db=db,
        issue_id=issue_id,
        event_type="department_added",
        actor_id=actor.id,
        task_id=new_task.id,
        payload={"department_code": department_code, "note": note},
    )

    recompute_block_states(db, issue_id, actor_id=actor.id)
    recompute_issue_priorities(db, issue_id)
    check_and_update_issue_resolution(db, issue_id, actor_id=actor.id)

    db.commit()
    db.refresh(new_task)
    return new_task


def add_dependency(
    db: Session,
    issue_id: str,
    task_id: str,
    blocked_by_task_id: str,
    reason: str,
    actor: User,
) -> TaskDependency:
    """
    Adds a dependency edge between two tasks on the same issue (§8.6).
    """
    t1 = db.query(Task).filter(Task.id == task_id, Task.issue_id == issue_id).first()
    t2 = db.query(Task).filter(Task.id == blocked_by_task_id, Task.issue_id == issue_id).first()
    if not t1 or not t2:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tasks not found on this issue")

    if would_create_cycle(db, issue_id, task_id, blocked_by_task_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add dependency: this would create a circular dependency cycle",
        )

    existing = (
        db.query(TaskDependency)
        .filter(TaskDependency.task_id == task_id, TaskDependency.blocked_by_task_id == blocked_by_task_id)
        .first()
    )
    if existing:
        return existing

    dep = TaskDependency(
        task_id=task_id,
        blocked_by_task_id=blocked_by_task_id,
        reason=reason,
        created_by=actor.id,
    )
    db.add(dep)
    db.flush()

    log_event(
        db=db,
        issue_id=issue_id,
        event_type="dependency_added",
        actor_id=actor.id,
        task_id=task_id,
        payload={
            "task_id": task_id,
            "blocked_by_task_id": blocked_by_task_id,
            "reason": reason,
        },
    )

    recompute_block_states(db, issue_id, actor_id=actor.id)
    recompute_issue_priorities(db, issue_id)
    db.commit()
    return dep


def remove_dependency(
    db: Session,
    issue_id: str,
    task_id: str,
    blocked_by_task_id: str,
    actor: User,
) -> bool:
    """
    Removes a dependency edge and unblocks tasks if appropriate.
    """
    dep = (
        db.query(TaskDependency)
        .filter(TaskDependency.task_id == task_id, TaskDependency.blocked_by_task_id == blocked_by_task_id)
        .first()
    )
    if not dep:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dependency not found")

    db.delete(dep)
    db.flush()

    log_event(
        db=db,
        issue_id=issue_id,
        event_type="dependency_removed",
        actor_id=actor.id,
        task_id=task_id,
        payload={"task_id": task_id, "blocked_by_task_id": blocked_by_task_id},
    )

    recompute_block_states(db, issue_id, actor_id=actor.id)
    recompute_issue_priorities(db, issue_id)
    db.commit()
    return True
