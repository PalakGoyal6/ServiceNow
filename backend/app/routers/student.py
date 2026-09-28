from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.db import get_db
from backend.app.models import User, Issue, Task, Message
from backend.app.schemas import (
    IssueCreate,
    IssueStudentListCard,
    IssueStudentDetailResponse,
    TaskStudentView,
    MessageCreate,
    MessageResponse,
    ReopenIssueRequest,
)
from backend.app.auth import get_current_student
from backend.app.permissions import check_student_owns_issue, filter_messages_for_user
from backend.app.services.intake import submit_issue
from backend.app.services.dependencies import get_execution_order
from backend.app.services.tasks import student_reopen_issue, change_status
from backend.app.services.events import log_event

router = APIRouter(prefix="/student", tags=["student"])


@router.post("/issues")
def create_issue(
    issue_in: IssueCreate,
    current_student: User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    text = issue_in.text.strip()
    if len(text) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Issue description must be at least 5 characters",
        )
    created_issue = submit_issue(
        db=db,
        student=current_student,
        text=text,
        optional_deadline=issue_in.deadline,
    )
    return {"id": created_issue.id, "title": created_issue.title, "status": created_issue.status}


@router.get("/issues", response_model=List[IssueStudentListCard])
def list_my_issues(
    current_student: User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    issues = (
        db.query(Issue)
        .filter(Issue.student_id == current_student.id)
        .order_by(Issue.created_at.desc())
        .all()
    )

    result = []
    for iss in issues:
        dept_statuses = []
        for t in iss.tasks:
            dept_statuses.append({
                "department_code": t.department.code if t.department else "",
                "department_name": t.department.name if t.department else "",
                "status": t.status,
                "action_needed": t.action_needed,
            })

        result.append(IssueStudentListCard(
            id=iss.id,
            title=iss.title,
            urgency=iss.urgency,
            status=iss.status,
            created_at=iss.created_at,
            resolved_at=iss.resolved_at,
            department_statuses=dept_statuses,
        ))
    return result


@router.get("/issues/{id}", response_model=IssueStudentDetailResponse)
def get_issue_detail(
    id: str,
    current_student: User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    issue = db.query(Issue).filter(Issue.id == id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    
    check_student_owns_issue(current_student, issue)

    # Filter tasks for student view (no dept_summary, internal notes, priorities, assignee)
    tasks_student = []
    waiting_dept_name = None
    for t in issue.tasks:
        tasks_student.append(TaskStudentView(
            id=t.id,
            department_id=t.department_id,
            department_code=t.department.code if t.department else "",
            department_name=t.department.name if t.department else "",
            status=t.status,
            action_needed=t.action_needed,
            resolved_at=t.resolved_at,
        ))
        if t.status == "waiting_on_student":
            waiting_dept_name = t.department.name if t.department else "A department"

    # Execution order stages
    stages = get_execution_order(db, issue.id)

    # Messages (filtered for student: student_and_staff only)
    raw_messages = (
        db.query(Message)
        .filter(Message.issue_id == issue.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    filtered_messages = filter_messages_for_user(raw_messages, current_student)
    
    msg_responses = []
    waiting_banner = None

    for m in filtered_messages:
        author_dept_code = m.author.department.code if (m.author and m.author.department) else None
        msg_responses.append(MessageResponse(
            id=m.id,
            issue_id=m.issue_id,
            task_id=m.task_id,
            author_id=m.author_id,
            author_name=m.author.full_name if m.author else "User",
            author_role=m.author.role if m.author else "user",
            department_code=author_dept_code,
            body=m.body,
            visibility=m.visibility,
            created_at=m.created_at,
        ))

    if waiting_dept_name:
        latest_staff_msg = next((m.body for m in reversed(msg_responses) if m.author_role in ["staff", "admin"]), "Action required from you")
        waiting_banner = {
            "department_name": waiting_dept_name,
            "latest_message": latest_staff_msg,
        }

    return IssueStudentDetailResponse(
        id=issue.id,
        title=issue.title,
        status=issue.status,
        urgency=issue.urgency,
        deadline=issue.deadline,
        created_at=issue.created_at,
        resolved_at=issue.resolved_at,
        tasks=tasks_student,
        execution_order=stages,
        messages=msg_responses,
        waiting_banner=waiting_banner,
    )


@router.post("/issues/{id}/messages", response_model=MessageResponse)
def post_student_message(
    id: str,
    msg_in: MessageCreate,
    current_student: User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    issue = db.query(Issue).filter(Issue.id == id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    
    check_student_owns_issue(current_student, issue)

    msg = Message(
        issue_id=issue.id,
        task_id=msg_in.task_id,
        author_id=current_student.id,
        body=msg_in.body.strip(),
        visibility="student_and_staff",
    )
    db.add(msg)
    db.flush()

    log_event(
        db=db,
        issue_id=issue.id,
        event_type="message_posted",
        actor_id=current_student.id,
        task_id=msg_in.task_id,
        payload={"visibility": "student_and_staff", "preview": msg_in.body[:60]},
    )

    # Per §8.1: If any task was waiting_on_student, student posting message auto-moves it to in_progress
    for task in issue.tasks:
        if task.status == "waiting_on_student":
            task.status = "in_progress"
            log_event(
                db=db,
                issue_id=issue.id,
                event_type="task_status_changed",
                actor_id=current_student.id,
                task_id=task.id,
                payload={
                    "from_status": "waiting_on_student",
                    "to_status": "in_progress",
                    "reason": "Student replied with a message",
                },
            )

    db.commit()
    db.refresh(msg)

    return MessageResponse(
        id=msg.id,
        issue_id=msg.issue_id,
        task_id=msg.task_id,
        author_id=msg.author_id,
        author_name=current_student.full_name,
        author_role=current_student.role,
        department_code=None,
        body=msg.body,
        visibility=msg.visibility,
        created_at=msg.created_at,
    )


@router.post("/issues/{id}/reopen")
def reopen_issue(
    id: str,
    req: ReopenIssueRequest,
    current_student: User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    issue = db.query(Issue).filter(Issue.id == id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    
    check_student_owns_issue(current_student, issue)

    student_reopen_issue(db=db, issue=issue, student_user=current_student, message_body=req.body)
    
    # Also record the reopen message
    msg = Message(
        issue_id=issue.id,
        author_id=current_student.id,
        body=f"[Reopened issue]: {req.body}",
        visibility="student_and_staff",
    )
    db.add(msg)
    db.commit()

    return {"message": "Issue reopened successfully", "issue_id": issue.id}
