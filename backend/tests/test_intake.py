import pytest
from backend.app.models import Issue, Task, TaskDependency, Event
from backend.app.services.intake import submit_issue
from backend.tests.conftest import auth_header_for


def test_intake_pipeline_end_to_end(db_session, seeded_db):
    s1 = seeded_db["student1"]
    text = "My scholarship hasn't been credited so I couldn't pay my semester fees, and now my name isn't on the exam list."

    issue = submit_issue(db=db_session, student=s1, text=text)
    assert issue.id is not None
    assert issue.student_id == s1.id
    assert issue.status == "open"

    tasks = db_session.query(Task).filter(Task.issue_id == issue.id).all()
    task_codes = [t.department.code for t in tasks]
    assert "SCHOL" in task_codes
    assert "FIN" in task_codes
    assert "EXAM" in task_codes

    # Check dependencies: EXAM should be blocked, FIN should be blocked by SCHOL, SCHOL should be pending
    schol_task = next(t for t in tasks if t.department.code == "SCHOL")
    fin_task = next(t for t in tasks if t.department.code == "FIN")
    exam_task = next(t for t in tasks if t.department.code == "EXAM")

    assert schol_task.status == "pending"
    assert fin_task.status == "blocked"
    assert exam_task.status == "blocked"

    # Verify audit events were logged
    events = db_session.query(Event).filter(Event.issue_id == issue.id).all()
    event_types = [e.type for e in events]
    assert "issue_created" in event_types
    assert "classified" in event_types
    assert "task_created" in event_types
