import pytest
from datetime import date, timedelta
from backend.app.models import Issue, Task, TaskDependency
from backend.app.services.priority import (
    calculate_base_priority,
    recompute_issue_priorities,
    get_priority_label,
    get_priority_inheritance_info,
)


def test_base_priority_calculation():
    today = date.today()
    # Urgency 4 = 80
    assert calculate_base_priority(4, None, today, "pending") == 80
    # Urgency 4 + deadline in 1 day (+15) = 95
    assert calculate_base_priority(4, today + timedelta(days=1), today, "pending") == 95
    # Urgency 1 = 20
    assert calculate_base_priority(1, None, today, "pending") == 20


def test_priority_labels():
    assert get_priority_label(95) == "Critical"
    assert get_priority_label(85) == "Critical"
    assert get_priority_label(70) == "High"
    assert get_priority_label(50) == "Medium"
    assert get_priority_label(30) == "Low"


def test_priority_transitive_inheritance(db_session, seeded_db):
    s1 = seeded_db["student1"]
    dept_fin = seeded_db["dept_fin"]
    dept_exam = seeded_db["dept_exam"]
    dept_schol = seeded_db["dept_schol"]

    exam_deadline = date.today() + timedelta(days=2)
    iss = Issue(
        student_id=s1.id,
        title="Chain priority",
        description="text",
        urgency=4,
        deadline=exam_deadline,
        status="open",
    )
    db_session.add(iss)
    db_session.flush()

    t_schol = Task(issue_id=iss.id, department_id=dept_schol.id, status="pending", dept_summary="s", action_needed="a")
    t_fin = Task(issue_id=iss.id, department_id=dept_fin.id, status="blocked", dept_summary="f", action_needed="a")
    t_exam = Task(issue_id=iss.id, department_id=dept_exam.id, status="blocked", dept_summary="e", action_needed="a")
    db_session.add_all([t_schol, t_fin, t_exam])
    db_session.flush()

    # SCHOL -> FIN -> EXAM
    db_session.add_all([
        TaskDependency(task_id=t_fin.id, blocked_by_task_id=t_schol.id, reason="r1", created_by="ai"),
        TaskDependency(task_id=t_exam.id, blocked_by_task_id=t_fin.id, reason="r2", created_by="ai"),
    ])
    db_session.commit()

    recompute_issue_priorities(db_session, iss.id)
    db_session.refresh(t_schol)
    db_session.refresh(t_fin)
    db_session.refresh(t_exam)

    # Base priority of EXAM (sink) is 80 + 15 (deadline in 2 days) = 95
    assert t_exam.effective_priority == 95
    assert t_exam.base_priority == 95
    
    # SCHOL base priority is 80, inherits 95 from EXAM
    assert t_schol.base_priority == 80
    assert t_schol.effective_priority == 95
    assert get_priority_label(t_schol.effective_priority) == "Critical"

    is_inherited, reason = get_priority_inheritance_info(db_session, t_schol)
    assert is_inherited is True
    assert "waiting on this" in reason
