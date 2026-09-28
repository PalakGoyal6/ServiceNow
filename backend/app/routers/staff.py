from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.db import get_db
from backend.app.models import User, Issue, Task, Department, Message, Event
from backend.app.schemas import (
    StaffTaskListItem,
    StaffTaskDetailResponse,
    TaskStaffSelfView,
    TaskStaffOtherView,
    TaskUpdateStatusRequest,
    TaskAssignRequest,
    MessageCreate,
    MessageResponse,
    EventResponse,
    AddDepartmentRequest,
    AddDependencyRequest,
    DeleteDependencyRequest,
    DepartmentSchema,
    StaffStatsResponse,
)
from backend.app.auth import get_current_staff
from backend.app.permissions import (
    check_staff_on_issue,
    check_staff_can_modify_task,
    filter_messages_for_user,
)
from backend.app.services.priority import (
    get_priority_label,
    get_priority_inheritance_info,
)
from backend.app.services.dependencies import get_execution_order
from backend.app.services.tasks import (
    change_status,
    add_department_to_issue,
    add_dependency,
    remove_dependency,
    get_allowed_transitions_for_task,
)
from backend.app.services.events import log_event

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("/departments", response_model=List[DepartmentSchema])
def list_departments(
    current_staff: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    return db.query(Department).order_by(Department.name.asc()).all()


@router.get("/stats", response_model=StaffStatsResponse)
def get_staff_stats(
    current_staff: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    dept_id = current_staff.department_id
    dept = db.query(Department).filter(Department.id == dept_id).first() if dept_id else None
    
    dept_name = dept.name if dept else "All Departments"
    dept_code = dept.code if dept else "ALL"

    query = db.query(Task)
    if dept_id and current_staff.role != "admin":
        query = query.filter(Task.department_id == dept_id)

    tasks = query.all()
    
    active_count = sum(1 for t in tasks if t.status in ["pending", "in_progress", "waiting_on_student"])
    blocked_count = sum(1 for t in tasks if t.status == "blocked")
    
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    resolved_week = sum(
        1 for t in tasks 
        if t.status == "resolved" and t.resolved_at and (t.resolved_at.replace(tzinfo=timezone.utc) if not t.resolved_at.tzinfo else t.resolved_at) >= week_ago
    )

    return StaffStatsResponse(
        active_count=active_count,
        blocked_count=blocked_count,
        resolved_this_week_count=resolved_week,
        department_name=dept_name,
        department_code=dept_code,
    )


@router.get("/tasks", response_model=List[StaffTaskListItem])
def list_staff_tasks(
    status_filter: str = Query("active", alias="status"),
    sort: str = Query("priority", alias="sort"),
    current_staff: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    query = db.query(Task)
    if current_staff.role != "admin" and current_staff.department_id:
        query = query.filter(Task.department_id == current_staff.department_id)

    # Status filter
    if status_filter == "active":
        query = query.filter(Task.status.in_(["pending", "in_progress", "waiting_on_student"]))
    elif status_filter == "blocked":
        query = query.filter(Task.status == "blocked")
    elif status_filter == "resolved":
        query = query.filter(Task.status.in_(["resolved", "rejected"]))
    # 'all' shows all

    tasks = query.all()

    # Sort
    if sort == "created":
        tasks.sort(key=lambda t: t.created_at, reverse=True)
    else:  # priority default
        tasks.sort(key=lambda t: (t.effective_priority, t.created_at), reverse=True)

    now = datetime.now(timezone.utc)
    one_day_ago = now - timedelta(days=1)

    result = []
    for t in tasks:
        issue = t.issue
        student = issue.student if issue else None
        student_name = student.full_name if student else "Student"
        roll_no = student.student_profile.roll_no if (student and student.student_profile) else None

        # Check newly unblocked (<24h)
        is_newly_unblocked = False
        if t.unblocked_at:
            unblocked_utc = t.unblocked_at.replace(tzinfo=timezone.utc) if not t.unblocked_at.tzinfo else t.unblocked_at
            if unblocked_utc >= one_day_ago and t.status in ["pending", "in_progress"]:
                is_newly_unblocked = True

        is_inherited, _ = get_priority_inheritance_info(db, t)

        other_tasks = [other for other in issue.tasks if other.id != t.id] if issue else []
        other_preview = [
            {"code": o.department.code if o.department else "", "status": o.status}
            for o in other_tasks
        ]

        result.append(StaffTaskListItem(
            task_id=t.id,
            issue_id=t.issue_id,
            title=issue.title if issue else "Task",
            student_name=student_name,
            student_roll_no=roll_no,
            status=t.status,
            dept_summary=t.dept_summary,
            action_needed=t.action_needed,
            effective_priority=t.effective_priority,
            priority_label=get_priority_label(t.effective_priority),
            priority_inherited=is_inherited,
            deadline=issue.deadline if issue else None,
            created_at=t.created_at,
            unblocked_at=t.unblocked_at,
            is_newly_unblocked=is_newly_unblocked,
            is_auto_classified=(issue.classification_source == "fallback") if issue else False,
            other_departments_count=len(other_tasks),
            other_departments_preview=other_preview,
        ))

    return result


@router.get("/tasks/{id}", response_model=StaffTaskDetailResponse)
def get_task_detail(
    id: str,
    current_staff: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Check permission: staff's department must have a task on this issue
    check_staff_on_issue(current_staff, task.issue_id, db)

    issue = task.issue
    student = issue.student
    student_profile = student.student_profile if student else None

    # Priority inheritance details
    is_inherited, reason = get_priority_inheritance_info(db, task)

    now = datetime.now(timezone.utc)
    is_newly_unblocked = False
    if task.unblocked_at:
        unblocked_utc = task.unblocked_at.replace(tzinfo=timezone.utc) if not task.unblocked_at.tzinfo else task.unblocked_at
        if (now - unblocked_utc) <= timedelta(days=1) and task.status in ["pending", "in_progress"]:
            is_newly_unblocked = True

    self_view = TaskStaffSelfView(
        id=task.id,
        issue_id=task.issue_id,
        department_id=task.department_id,
        department_code=task.department.code if task.department else "",
        department_name=task.department.name if task.department else "",
        status=task.status,
        dept_summary=task.dept_summary,
        action_needed=task.action_needed,
        base_priority=task.base_priority,
        effective_priority=task.effective_priority,
        priority_label=get_priority_label(task.effective_priority),
        priority_inherited=is_inherited,
        priority_inheritance_reason=reason,
        assigned_to=task.assigned_to,
        assignee_name=task.assignee.full_name if task.assignee else None,
        created_at=task.created_at,
        updated_at=task.updated_at,
        resolved_at=task.resolved_at,
        unblocked_at=task.unblocked_at,
        is_newly_unblocked=is_newly_unblocked,
    )

    # Other departments' tasks (PRIVACY RULE: status and action_needed ONLY, not dept_summary)
    other_tasks = []
    for other in issue.tasks:
        if other.id != task.id:
            other_tasks.append(TaskStaffOtherView(
                id=other.id,
                department_id=other.department_id,
                department_code=other.department.code if other.department else "",
                department_name=other.department.name if other.department else "",
                status=other.status,
                action_needed=other.action_needed,
                resolved_at=other.resolved_at,
            ))

    # Execution order stages
    stages = get_execution_order(db, issue.id)

    # Messages (filtered: student_and_staff + dept_only for own dept)
    raw_messages = (
        db.query(Message)
        .filter(Message.issue_id == issue.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    filtered_messages = filter_messages_for_user(raw_messages, current_staff)
    message_responses = [
        MessageResponse(
            id=m.id,
            issue_id=m.issue_id,
            task_id=m.task_id,
            author_id=m.author_id,
            author_name=m.author.full_name if m.author else "User",
            author_role=m.author.role if m.author else "user",
            department_code=m.author.department.code if (m.author and m.author.department) else None,
            body=m.body,
            visibility=m.visibility,
            created_at=m.created_at,
        )
        for m in filtered_messages
    ]

    # Timeline events
    events = (
        db.query(Event)
        .filter(Event.issue_id == issue.id)
        .order_by(Event.created_at.desc())
        .all()
    )
    event_responses = [
        EventResponse(
            id=e.id,
            issue_id=e.issue_id,
            task_id=e.task_id,
            actor_id=e.actor_id,
            actor_name=e.actor.full_name if e.actor else "System",
            type=e.type,
            payload=e.payload,
            created_at=e.created_at,
        )
        for e in events
    ]

    allowed_transitions = get_allowed_transitions_for_task(task)

    student_info = {
        "name": student.full_name if student else "Unknown",
        "roll_no": student_profile.roll_no if student_profile else "N/A",
        "programme": student_profile.programme if student_profile else "N/A",
        "year_of_study": student_profile.year_of_study if student_profile else 1,
    }

    return StaffTaskDetailResponse(
        task=self_view,
        issue_id=issue.id,
        issue_title=issue.title,
        issue_status=issue.status,
        issue_urgency=issue.urgency,
        issue_deadline=issue.deadline,
        issue_created_at=issue.created_at,
        classification_source=issue.classification_source,
        student_info=student_info,
        other_tasks=other_tasks,
        execution_order=stages,
        messages=message_responses,
        events=event_responses,
        allowed_transitions=allowed_transitions,
    )


@router.get("/tasks/{id}/original-message")
def get_original_message(
    id: str,
    current_staff: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """
    Explicit audited endpoint to view student's raw unredacted description (§7).
    Requires staff department to be on the issue.
    Logs event 'raw_description_viewed'.
    """
    task = db.query(Task).filter(Task.id == id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    check_staff_on_issue(current_staff, task.issue_id, db)

    issue = task.issue

    # Log audit event per §7
    log_event(
        db=db,
        issue_id=issue.id,
        event_type="raw_description_viewed",
        actor_id=current_staff.id,
        task_id=task.id,
        payload={
            "viewer_email": current_staff.email,
            "department_code": current_staff.department.code if current_staff.department else "ADMIN",
        },
    )
    db.commit()

    return {"description": issue.description, "student_name": issue.student.full_name if issue.student else "Student"}


@router.patch("/tasks/{id}/status", response_model=TaskStaffSelfView)
def update_task_status(
    id: str,
    req: TaskUpdateStatusRequest,
    current_staff: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    check_staff_can_modify_task(current_staff, task)

    updated_task = change_status(
        db=db,
        task=task,
        new_status=req.status,
        actor=current_staff,
        note=req.note,
    )

    is_inherited, reason = get_priority_inheritance_info(db, updated_task)
    return TaskStaffSelfView(
        id=updated_task.id,
        issue_id=updated_task.issue_id,
        department_id=updated_task.department_id,
        department_code=updated_task.department.code if updated_task.department else "",
        department_name=updated_task.department.name if updated_task.department else "",
        status=updated_task.status,
        dept_summary=updated_task.dept_summary,
        action_needed=updated_task.action_needed,
        base_priority=updated_task.base_priority,
        effective_priority=updated_task.effective_priority,
        priority_label=get_priority_label(updated_task.effective_priority),
        priority_inherited=is_inherited,
        priority_inheritance_reason=reason,
        assigned_to=updated_task.assigned_to,
        assignee_name=updated_task.assignee.full_name if updated_task.assignee else None,
        created_at=updated_task.created_at,
        updated_at=updated_task.updated_at,
        resolved_at=updated_task.resolved_at,
        unblocked_at=updated_task.unblocked_at,
        is_newly_unblocked=False,
    )


@router.patch("/tasks/{id}/assign")
def assign_task(
    id: str,
    req: TaskAssignRequest,
    current_staff: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    check_staff_can_modify_task(current_staff, task)

    if req.user_id:
        target_user = db.query(User).filter(User.id == req.user_id).first()
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignee user not found")
        if target_user.department_id != task.department_id and target_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assignee must belong to the same department as the task",
            )
        task.assigned_to = target_user.id
    else:
        task.assigned_to = None

    log_event(
        db=db,
        issue_id=task.issue_id,
        event_type="task_reassigned",
        actor_id=current_staff.id,
        task_id=task.id,
        payload={"assigned_to": req.user_id},
    )
    db.commit()
    return {"message": "Task assigned successfully", "assigned_to": task.assigned_to}


@router.post("/tasks/{id}/messages", response_model=MessageResponse)
def post_staff_message(
    id: str,
    msg_in: MessageCreate,
    current_staff: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    check_staff_on_issue(current_staff, task.issue_id, db)

    msg = Message(
        issue_id=task.issue_id,
        task_id=task.id,
        author_id=current_staff.id,
        body=msg_in.body.strip(),
        visibility=msg_in.visibility if msg_in.visibility in ["student_and_staff", "department_only"] else "student_and_staff",
    )
    db.add(msg)
    db.flush()

    log_event(
        db=db,
        issue_id=task.issue_id,
        event_type="message_posted",
        actor_id=current_staff.id,
        task_id=task.id,
        payload={"visibility": msg.visibility, "preview": msg.body[:60]},
    )
    db.commit()
    db.refresh(msg)

    return MessageResponse(
        id=msg.id,
        issue_id=msg.issue_id,
        task_id=msg.task_id,
        author_id=msg.author_id,
        author_name=current_staff.full_name,
        author_role=current_staff.role,
        department_code=current_staff.department.code if current_staff.department else None,
        body=msg.body,
        visibility=msg.visibility,
        created_at=msg.created_at,
    )


@router.post("/issues/{issue_id}/departments")
def add_department(
    issue_id: str,
    req: AddDepartmentRequest,
    current_staff: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    check_staff_on_issue(current_staff, issue_id, db)
    task = add_department_to_issue(
        db=db,
        issue_id=issue_id,
        department_code=req.department_code,
        note=req.note,
        actor=current_staff,
        blocked_by_task_id=req.blocked_by_task_id,
    )
    return {"message": "Department added successfully", "task_id": task.id}


@router.post("/issues/{issue_id}/dependencies")
def create_dependency(
    issue_id: str,
    req: AddDependencyRequest,
    current_staff: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    check_staff_on_issue(current_staff, issue_id, db)
    dep = add_dependency(
        db=db,
        issue_id=issue_id,
        task_id=req.task_id,
        blocked_by_task_id=req.blocked_by_task_id,
        reason=req.reason,
        actor=current_staff,
    )
    return {"message": "Dependency added successfully"}


@router.delete("/issues/{issue_id}/dependencies")
def delete_dependency(
    issue_id: str,
    req: DeleteDependencyRequest,
    current_staff: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    check_staff_on_issue(current_staff, issue_id, db)
    remove_dependency(
        db=db,
        issue_id=issue_id,
        task_id=req.task_id,
        blocked_by_task_id=req.blocked_by_task_id,
        actor=current_staff,
    )
    return {"message": "Dependency removed successfully"}
