from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.models import User, Issue, Task, Message


def check_student_owns_issue(user: User, issue: Issue) -> None:
    if issue.student_id != user.id:
        # Per spec: Return 404 when students probe other students' issues
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )


def check_staff_on_issue(user: User, issue_id: str, db: Session) -> Task:
    """
    Verifies that the staff member's department has a task on this issue.
    Admin can also view.
    Returns the staff member's department task on this issue.
    """
    if user.role == "admin":
        first_task = db.query(Task).filter(Task.issue_id == issue_id).first()
        if not first_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Issue not found",
            )
        return first_task

    if not user.department_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not assigned to any department",
        )

    task = (
        db.query(Task)
        .filter(Task.issue_id == issue_id, Task.department_id == user.department_id)
        .first()
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your department is not assigned to this issue",
        )
    return task


def check_staff_can_modify_task(user: User, task: Task) -> None:
    if user.role == "admin":
        return
    if not user.department_id or task.department_id != user.department_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify tasks belonging to your own department",
        )


def filter_messages_for_user(messages: List[Message], user: User) -> List[Message]:
    """
    Filters messages based on user role and department:
    - Students see only 'student_and_staff'
    - Staff see 'student_and_staff' + 'department_only' from their own department
    - Admin sees all
    """
    filtered = []
    for msg in messages:
        if msg.visibility == "student_and_staff":
            filtered.append(msg)
        elif msg.visibility == "department_only":
            if user.role == "admin":
                filtered.append(msg)
            elif user.role == "staff" and user.department_id:
                # Check if author belongs to same department or message linked to staff task
                if msg.author and msg.author.department_id == user.department_id:
                    filtered.append(msg)
                elif msg.task and msg.task.department_id == user.department_id:
                    filtered.append(msg)
    return filtered
