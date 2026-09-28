from datetime import datetime, date, timezone
from typing import Dict, List, Tuple, Optional
from sqlalchemy.orm import Session
from backend.app.models import Issue, Task, TaskDependency, Department


def get_priority_label(priority: int) -> str:
    if priority >= 85:
        return "Critical"
    elif priority >= 65:
        return "High"
    elif priority >= 45:
        return "Medium"
    else:
        return "Low"


def calculate_base_priority(urgency: int, deadline: Optional[date], created_at: datetime, status: str) -> int:
    """
    Computes base priority (0-100):
    - urgency: urgency * 20 (20-80)
    - deadline proximity: +15 if <= 2 days, +8 if <= 7 days, +0 otherwise
    - aging: +1 per full day task has been open (not blocked), capped at +10
    - clamped to 100
    """
    score = max(1, min(4, urgency)) * 20

    today = date.today()
    if deadline:
        days_until_deadline = (deadline - today).days
        if days_until_deadline <= 2:
            score += 15
        elif days_until_deadline <= 7:
            score += 8

    # Aging: +1 per full day if not blocked
    if status != "blocked":
        now = datetime.now(timezone.utc)
        if isinstance(created_at, datetime):
            created_utc = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
        else:
            created_utc = datetime.combine(created_at, datetime.min.time(), tzinfo=timezone.utc)
        days_open = (now - created_utc).days
        if days_open > 0:
            score += min(10, days_open)

    return min(100, max(0, score))



def recompute_issue_priorities(db: Session, issue_id: str) -> None:
    """
    Recomputes base and effective priorities for all tasks in an issue
    applying transitive priority inheritance per §9.
    """
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        return

    tasks = db.query(Task).filter(Task.issue_id == issue_id).all()
    if not tasks:
        return

    task_map = {t.id: t for t in tasks}

    # Get dependencies: task_id is blocked by blocked_by_task_id
    deps = (
        db.query(TaskDependency)
        .filter(TaskDependency.task_id.in_(list(task_map.keys())))
        .all()
    )

    # Set of task IDs that block at least one other task
    blocker_task_ids = {dep.blocked_by_task_id for dep in deps}

    # 1. Compute base priorities:
    # Tasks that block other tasks have base priority from urgency + aging (without deadline bonus),
    # while leaf/sink tasks (or tasks in single-task issues) receive the deadline bonus directly.
    for task in tasks:
        task_deadline = None if (task.id in blocker_task_ids and len(tasks) > 1) else issue.deadline
        task.base_priority = calculate_base_priority(
            urgency=issue.urgency,
            deadline=task_deadline,
            created_at=task.created_at,
            status=task.status,
        )

    # Graph of blocked_by -> list of dependent tasks
    dependents_map = {t.id: [] for t in tasks}
    for dep in deps:
        if dep.blocked_by_task_id in dependents_map:
            dependents_map[dep.blocked_by_task_id].append(dep.task_id)

    # 2. Transitive propagation (DFS / Memoization)
    memo: Dict[str, int] = {}
    visited = set()

    def get_effective(t_id: str) -> int:
        if t_id in memo:
            return memo[t_id]
        if t_id in visited:
            return task_map[t_id].base_priority
        visited.add(t_id)

        t = task_map[t_id]
        max_priority = t.base_priority

        for dep_task_id in dependents_map.get(t_id, []):
            if dep_task_id in task_map:
                dep_effective = get_effective(dep_task_id)
                if dep_effective > max_priority:
                    max_priority = dep_effective

        visited.remove(t_id)
        memo[t_id] = max_priority
        return max_priority

    for task in tasks:
        task.effective_priority = get_effective(task.id)

    db.flush()



def get_priority_inheritance_info(db: Session, task: Task) -> Tuple[bool, Optional[str]]:
    """
    Checks if a task inherited higher priority from any task it blocks.
    Returns (is_inherited, reason_string).
    """
    if task.effective_priority <= task.base_priority:
        return False, None

    # Find which dependent task caused the increase
    dependents = (
        db.query(TaskDependency)
        .filter(TaskDependency.blocked_by_task_id == task.id)
        .all()
    )

    for dep in dependents:
        dep_task = db.query(Task).filter(Task.id == dep.task_id).first()
        if dep_task and dep_task.effective_priority == task.effective_priority:
            dept_name = dep_task.department.name if dep_task.department else "another department"
            deadline_str = ""
            if task.issue and task.issue.deadline:
                days = (task.issue.deadline - date.today()).days
                if days == 0:
                    deadline_str = " (deadline today)"
                elif days == 1:
                    deadline_str = " (deadline tomorrow)"
                elif days > 1:
                    deadline_str = f" (deadline in {days} days)"
            return True, f"Priority raised because {dept_name} is waiting on this{deadline_str}."

    return True, "Priority raised because a dependent department task has higher urgency."


def recompute_all_open_priorities(db: Session) -> int:
    """
    Recomputes priorities across all open issues in the system.
    """
    open_issues = db.query(Issue.id).filter(Issue.status == "open").all()
    count = 0
    for row in open_issues:
        recompute_issue_priorities(db, row[0])
        count += 1
    db.commit()
    return count
