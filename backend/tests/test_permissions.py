import pytest
from datetime import datetime, timezone
from backend.app.models import Issue, Task, Message, Event
from backend.tests.conftest import auth_header_for


def test_student_cannot_probe_other_student_issue(client, seeded_db, db_session):
    s1 = seeded_db["student1"]
    s2 = seeded_db["student2"]
    dept_fin = seeded_db["dept_fin"]

    # Create issue for student1
    iss = Issue(student_id=s1.id, title="Priya fee issue", description="Private financial details", urgency=2, status="open")
    db_session.add(iss)
    db_session.flush()

    # S2 tries to get s1's issue -> 404 per spec
    resp = client.get(f"/student/issues/{iss.id}", headers=auth_header_for(s2))
    assert resp.status_code == 404


def test_student_never_receives_dept_summary_or_internal_notes(client, seeded_db, db_session):
    s1 = seeded_db["student1"]
    staff_fin = seeded_db["staff_fin"]
    dept_fin = seeded_db["dept_fin"]

    iss = Issue(student_id=s1.id, title="Fee waiver", description="Raw text", urgency=2, status="open")
    db_session.add(iss)
    db_session.flush()

    task = Task(
        issue_id=iss.id,
        department_id=dept_fin.id,
        status="pending",
        dept_summary="Confidential finance summary with ledger codes",
        action_needed="Review waiver",
    )
    db_session.add(task)
    db_session.flush()

    # Add 1 public message and 1 internal note
    m_pub = Message(issue_id=iss.id, author_id=staff_fin.id, body="Public message to student", visibility="student_and_staff")
    m_priv = Message(issue_id=iss.id, author_id=staff_fin.id, body="Internal note: secret remarks", visibility="department_only")
    db_session.add_all([m_pub, m_priv])
    db_session.commit()

    resp = client.get(f"/student/issues/{iss.id}", headers=auth_header_for(s1))
    assert resp.status_code == 200
    data = resp.json()

    # Task view for student must NOT have dept_summary
    for t in data["tasks"]:
        assert "dept_summary" not in t
        assert "base_priority" not in t
        assert "effective_priority" not in t

    # Messages must only contain public message
    messages = data["messages"]
    assert len(messages) == 1
    assert messages[0]["body"] == "Public message to student"


def test_uninvolved_staff_gets_403(client, seeded_db, db_session):
    s1 = seeded_db["student1"]
    staff_fin = seeded_db["staff_fin"]
    staff_couns = seeded_db["staff_couns"]
    dept_fin = seeded_db["dept_fin"]

    iss = Issue(student_id=s1.id, title="Finance only issue", description="Text", urgency=2, status="open")
    db_session.add(iss)
    db_session.flush()

    t_fin = Task(issue_id=iss.id, department_id=dept_fin.id, status="pending", dept_summary="Fin summary", action_needed="Act")
    db_session.add(t_fin)
    db_session.commit()

    # COUNS staff is not on this issue -> 403
    resp = client.get(f"/staff/tasks/{t_fin.id}", headers=auth_header_for(staff_couns))
    assert resp.status_code == 403


def test_staff_cannot_read_other_dept_summary(client, seeded_db, db_session):
    s1 = seeded_db["student1"]
    staff_fin = seeded_db["staff_fin"]
    dept_fin = seeded_db["dept_fin"]
    dept_couns = seeded_db["dept_couns"]

    iss = Issue(student_id=s1.id, title="Multi-dept issue", description="Text", urgency=2, status="open")
    db_session.add(iss)
    db_session.flush()

    t_fin = Task(issue_id=iss.id, department_id=dept_fin.id, status="pending", dept_summary="FIN confidential summary", action_needed="Clear fees")
    t_couns = Task(issue_id=iss.id, department_id=dept_couns.id, status="pending", dept_summary="COUNS highly sensitive mental health summary", action_needed="Provide therapy")
    db_session.add_all([t_fin, t_couns])
    db_session.commit()

    # FIN staff views their task
    resp = client.get(f"/staff/tasks/{t_fin.id}", headers=auth_header_for(staff_fin))
    assert resp.status_code == 200
    data = resp.json()

    # Own task has full summary
    assert data["task"]["dept_summary"] == "FIN confidential summary"

    # Other tasks list must NOT expose COUNS sensitive summary
    for other in data["other_tasks"]:
        assert "dept_summary" not in other
        assert other["action_needed"] == "Provide therapy"


def test_raw_description_endpoint_audited(client, seeded_db, db_session):
    s1 = seeded_db["student1"]
    staff_fin = seeded_db["staff_fin"]
    dept_fin = seeded_db["dept_fin"]

    iss = Issue(student_id=s1.id, title="Fee issue", description="Student raw private description", urgency=2, status="open")
    db_session.add(iss)
    db_session.flush()

    t_fin = Task(issue_id=iss.id, department_id=dept_fin.id, status="pending", dept_summary="Summary", action_needed="Act")
    db_session.add(t_fin)
    db_session.commit()

    # Request raw description
    resp = client.get(f"/staff/tasks/{t_fin.id}/original-message", headers=auth_header_for(staff_fin))
    assert resp.status_code == 200
    assert resp.json()["description"] == "Student raw private description"

    # Verify audit event was logged
    event = db_session.query(Event).filter(Event.issue_id == iss.id, Event.type == "raw_description_viewed").first()
    assert event is not None
    assert event.actor_id == staff_fin.id
