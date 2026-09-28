import pytest
from backend.app.models import Issue, Task, TaskDependency
from backend.app.services.dependencies import would_create_cycle, recompute_block_states, get_execution_order
from backend.app.services.tasks import change_status
from backend.tests.conftest import auth_header_for


def test_cycle_detection(db_session, seeded_db):
    s1 = seeded_db["student1"]
    dept_fin = seeded_db["dept_fin"]
    dept_exam = seeded_db["dept_exam"]
    dept_schol = seeded_db["dept_schol"]

    iss = Issue(student_id=s1.id, title="Test cycle", description="text", urgency=2, status="open")
    db_session.add(iss)
    db_session.flush()

    t_schol = Task(issue_id=iss.id, department_id=dept_schol.id, status="pending", dept_summary="s", action_needed="a")
    t_fin = Task(issue_id=iss.id, department_id=dept_fin.id, status="pending", dept_summary="f", action_needed="a")
    t_exam = Task(issue_id=iss.id, department_id=dept_exam.id, status="pending", dept_summary="e", action_needed="a")
    db_session.add_all([t_schol, t_fin, t_exam])
    db_session.flush()

    # SCHOL -> FIN (FIN blocked by SCHOL)
    dep1 = TaskDependency(task_id=t_fin.id, blocked_by_task_id=t_schol.id, reason="r", created_by="ai")
    # FIN -> EXAM (EXAM blocked by FIN)
    dep2 = TaskDependency(task_id=t_exam.id, blocked_by_task_id=t_fin.id, reason="r", created_by="ai")
    db_session.add_all([dep1, dep2])
    db_session.commit()

    # Try adding EXAM -> SCHOL (SCHOL blocked by EXAM) => CYCLE!
    assert would_create_cycle(db_session, iss.id, task_id=t_schol.id, blocked_by_task_id=t_exam.id) is True
    # Self-cycle
    assert would_create_cycle(db_session, iss.id, task_id=t_schol.id, blocked_by_task_id=t_schol.id) is True


def test_unblocking_requires_all_blockers_resolved(db_session, seeded_db):
    s1 = seeded_db["student1"]
    staff_fin = seeded_db["staff_fin"]
    staff_schol = seeded_db["staff_schol"]
    dept_fin = seeded_db["dept_fin"]
    dept_exam = seeded_db["dept_exam"]
    dept_schol = seeded_db["dept_schol"]

    iss = Issue(student_id=s1.id, title="Multi-blocker issue", description="text", urgency=2, status="open")
    db_session.add(iss)
    db_session.flush()

    t_schol = Task(issue_id=iss.id, department_id=dept_schol.id, status="pending", dept_summary="s", action_needed="a")
    t_fin = Task(issue_id=iss.id, department_id=dept_fin.id, status="pending", dept_summary="f", action_needed="a")
    t_exam = Task(issue_id=iss.id, department_id=dept_exam.id, status="pending", dept_summary="e", action_needed="a")
    db_session.add_all([t_schol, t_fin, t_exam])
    db_session.flush()

    # EXAM is blocked by BOTH SCHOL and FIN
    d1 = TaskDependency(task_id=t_exam.id, blocked_by_task_id=t_schol.id, reason="r1", created_by="ai")
    d2 = TaskDependency(task_id=t_exam.id, blocked_by_task_id=t_fin.id, reason="r2", created_by="ai")
    db_session.add_all([d1, d2])
    db_session.commit()

    recompute_block_states(db_session, iss.id)
    assert t_exam.status == "blocked"

    # Resolve SCHOL only
    change_status(db_session, t_schol, "resolved", staff_schol)
    db_session.refresh(t_exam)
    # EXAM must STILL be blocked because FIN is not resolved
    assert t_exam.status == "blocked"

    # Now resolve FIN
    change_status(db_session, t_fin, "resolved", staff_fin)
    db_session.refresh(t_exam)
    # Now EXAM unblocks!
    assert t_exam.status == "pending"
    assert t_exam.unblocked_at is not None


def test_execution_order_stages(db_session, seeded_db):
    s1 = seeded_db["student1"]
    dept_fin = seeded_db["dept_fin"]
    dept_exam = seeded_db["dept_exam"]
    dept_schol = seeded_db["dept_schol"]

    iss = Issue(student_id=s1.id, title="Chain issue", description="text", urgency=2, status="open")
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

    stages = get_execution_order(db_session, iss.id)
    assert len(stages) == 3
    assert stages[0]["stage_number"] == 1
    assert stages[0]["tasks"][0]["department_code"] == "SCHOL"
    assert stages[1]["stage_number"] == 2
    assert stages[1]["tasks"][0]["department_code"] == "FIN"
    assert stages[2]["stage_number"] == 3
    assert stages[2]["tasks"][0]["department_code"] == "EXAM"
