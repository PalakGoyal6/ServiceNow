from datetime import date, datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.models import Issue, Task, TaskDependency, Department, User
from backend.app.services.classifier import classify_issue
from backend.app.services.priority import recompute_issue_priorities
from backend.app.services.dependencies import recompute_block_states
from backend.app.services.events import log_event


def safety_screen(text: str) -> None:
    """
    Reserved for future crisis-detection and emergency escalation step (§6.1).
    Runs before classification. Currently a no-op per hackathon scope.
    """
    pass


def submit_issue(
    db: Session,
    student: User,
    text: str,
    optional_deadline: Optional[date] = None,
) -> Issue:
    """
    Orchestrates the complete intake pipeline in a single database transaction:
    1. Safety screen
    2. Classification (LLM or fallback)
    3. Normalization
    4. Issue, Tasks, and Dependencies creation
    5. Priority computation & Block status resolution
    6. Audit Event logging
    """
    # 1. Safety screen hook
    safety_screen(text)

    # 2. Retrieve all active departments
    departments = db.query(Department).all()
    dept_code_to_model = {d.code: d for d in departments}

    # 3. Classify issue
    classification, source = classify_issue(text, departments, optional_deadline)

    # 4. Create Issue record
    now = datetime.now(timezone.utc)
    issue = Issue(
        student_id=student.id,
        title=classification.title,
        description=text,
        urgency=classification.urgency,
        deadline=classification.deadline,
        status="open",
        classification_source=source,
        classification_raw=classification.model_dump_json(),
        created_at=now,
        updated_at=now,
    )
    db.add(issue)
    db.flush()  # Generate issue.id

    # 5. Create Tasks for assigned departments
    code_to_task = {}
    for assignment in classification.departments:
        dept = dept_code_to_model.get(assignment.department_code)
        if not dept:
            continue

        task = Task(
            issue_id=issue.id,
            department_id=dept.id,
            status="pending",  # Will be adjusted by dependencies
            dept_summary=assignment.dept_summary,
            action_needed=assignment.action_needed,
            base_priority=classification.urgency * 20,
            effective_priority=classification.urgency * 20,
            created_at=now,
            updated_at=now,
        )
        db.add(task)
        db.flush()
        code_to_task[assignment.department_code] = task

        log_event(
            db=db,
            issue_id=issue.id,
            event_type="task_created",
            actor_id=None,  # AI/System
            task_id=task.id,
            payload={
                "department_code": assignment.department_code,
                "action_needed": assignment.action_needed,
            },
        )

    # 6. Create Dependencies
    for dep in classification.dependencies:
        blocked_task = code_to_task.get(dep.blocked_department_code)
        blocker_task = code_to_task.get(dep.blocked_by_department_code)

        if blocked_task and blocker_task and blocked_task.id != blocker_task.id:
            task_dep = TaskDependency(
                task_id=blocked_task.id,
                blocked_by_task_id=blocker_task.id,
                reason=dep.reason,
                created_by="ai",
            )
            db.add(task_dep)
            db.flush()

            log_event(
                db=db,
                issue_id=issue.id,
                event_type="dependency_added",
                actor_id=None,
                task_id=blocked_task.id,
                payload={
                    "blocked_department": dep.blocked_department_code,
                    "blocked_by_department": dep.blocked_by_department_code,
                    "reason": dep.reason,
                },
            )

    # 7. Log Issue Created and Classified events
    log_event(
        db=db,
        issue_id=issue.id,
        event_type="issue_created",
        actor_id=student.id,
        payload={"title": issue.title, "urgency": issue.urgency},
    )
    log_event(
        db=db,
        issue_id=issue.id,
        event_type="classified",
        actor_id=None,
        payload={
            "source": source,
            "departments": [d.department_code for d in classification.departments],
            "urgency": classification.urgency,
            "urgency_reason": classification.urgency_reason,
        },
    )

    # 8. Recompute block states (initial status: blocked if has blockers)
    recompute_block_states(db, issue.id)

    # 9. Compute initial priorities and transitive inheritance
    recompute_issue_priorities(db, issue.id)

    db.commit()
    db.refresh(issue)
    return issue
