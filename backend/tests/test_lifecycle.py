import pytest
from backend.app.models import Issue, Task, Department
from backend.app.services.tasks import change_status, student_reopen_issue


def test_issue_auto_resolution_and_reopen(db_session, seeded_db):
    s1 = seeded_db["student1"]
    staff_fin = seeded_db["staff_fin"]
    dept_fin = seeded_db["dept_fin"]

    iss = Issue(student_id=s1.id, title="Single task issue", description="text", urgency=2, status="open")
    db_session.add(iss)
    db_session.flush()

    t_fin = Task(issue_id=iss.id, department_id=dept_fin.id, status="in_progress", dept_summary="f", action_needed="a")
    db_session.add(t_fin)
    db_session.commit()

    # Resolve the only task
    change_status(db_session, t_fin, "resolved", staff_fin)
    db_session.refresh(iss)
    assert iss.status == "resolved"
    assert iss.resolved_at is not None

    # Reopen the task
    change_status(db_session, t_fin, "in_progress", staff_fin)
    db_session.refresh(iss)
    assert iss.status == "open"
    assert iss.resolved_at is None


def test_rejecting_last_task_creates_dsw_task(db_session, seeded_db):
    s1 = seeded_db["student1"]
    staff_fin = seeded_db["staff_fin"]
    dept_fin = seeded_db["dept_fin"]

    iss = Issue(student_id=s1.id, title="Mistargeted issue", description="text", urgency=2, status="open")
    db_session.add(iss)
    db_session.flush()

    t_fin = Task(issue_id=iss.id, department_id=dept_fin.id, status="pending", dept_summary="f", action_needed="a")
    db_session.add(t_fin)
    db_session.commit()

    # Reject task with note
    change_status(db_session, t_fin, "rejected", staff_fin, note="Not finance matter")
    
    # Check that DSW task was automatically created
    tasks = db_session.query(Task).filter(Task.issue_id == iss.id).all()
    assert len(tasks) == 2
    dsw_task = next(t for t in tasks if t.department.code == "DSW")
    assert dsw_task.status == "pending"
    assert dsw_task.action_needed == "Re-route: previous department marked not relevant"


def test_student_reopen_resolved_issue(db_session, seeded_db):
    s1 = seeded_db["student1"]
    staff_fin = seeded_db["staff_fin"]
    dept_fin = seeded_db["dept_fin"]

    iss = Issue(student_id=s1.id, title="Issue to reopen", description="text", urgency=2, status="open")
    db_session.add(iss)
    db_session.flush()

    t_fin = Task(issue_id=iss.id, department_id=dept_fin.id, status="in_progress", dept_summary="f", action_needed="a")
    db_session.add(t_fin)
    db_session.commit()

    change_status(db_session, t_fin, "resolved", staff_fin)
    db_session.refresh(iss)
    assert iss.status == "resolved"

    # Student reopens
    reopened_task = student_reopen_issue(db_session, iss, s1, "Issue is not actually fixed")
    db_session.refresh(iss)
    db_session.refresh(reopened_task)

    assert iss.status == "open"
    assert reopened_task.status == "in_progress"
