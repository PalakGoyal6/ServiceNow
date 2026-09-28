import statistics
from datetime import datetime, timezone
from typing import List, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.db import get_db
from backend.app.models import User, Issue, Task, Department, TaskDependency
from backend.app.schemas import AdminAnalyticsResponse
from backend.app.auth import get_current_admin
from backend.app.services.priority import recompute_all_open_priorities

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/analytics", response_model=AdminAnalyticsResponse)
def get_analytics(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    total_issues = db.query(Issue).count()
    open_issues_count = db.query(Issue).filter(Issue.status == "open").count()
    resolved_issues_count = db.query(Issue).filter(Issue.status == "resolved").count()

    # 1. Open tasks by department
    departments = db.query(Department).all()
    open_by_dept = []
    for d in departments:
        count = (
            db.query(Task)
            .filter(
                Task.department_id == d.id,
                Task.status.in_(["pending", "in_progress", "waiting_on_student", "blocked"])
            )
            .count()
        )
        open_by_dept.append({"department_code": d.code, "department_name": d.name, "count": count})

    # 2. Median resolution time by department (in hours)
    resolution_times = []
    for d in departments:
        resolved_tasks = (
            db.query(Task)
            .filter(
                Task.department_id == d.id,
                Task.status == "resolved",
                Task.resolved_at.isnot(None),
            )
            .all()
        )
        durations = []
        for t in resolved_tasks:
            t_created = t.created_at if t.created_at.tzinfo else t.created_at.replace(tzinfo=timezone.utc)
            t_resolved = t.resolved_at if t.resolved_at.tzinfo else t.resolved_at.replace(tzinfo=timezone.utc)
            hours = max(0.1, (t_resolved - t_created).total_seconds() / 3600.0)
            durations.append(hours)

        median_hours = round(statistics.median(durations), 1) if durations else 0.0
        resolution_times.append({
            "department_code": d.code,
            "department_name": d.name,
            "median_hours": median_hours,
            "sample_size": len(durations),
        })

    # 3. Currently blocked tasks
    blocked_count = db.query(Task).filter(Task.status == "blocked").count()

    # 4. Bottleneck departments (departments whose unresolved tasks block other tasks)
    # Get all active blocked dependencies where blocker task is not resolved
    blocked_deps = (
        db.query(TaskDependency)
        .join(Task, Task.id == TaskDependency.task_id)
        .filter(Task.status == "blocked")
        .all()
    )

    blocker_dept_counts: Dict[str, int] = {}
    for dep in blocked_deps:
        blocker_task = db.query(Task).filter(Task.id == dep.blocked_by_task_id).first()
        if blocker_task and blocker_task.status not in ["resolved", "rejected"]:
            dept_code = blocker_task.department.code if blocker_task.department else "Unknown"
            blocker_dept_counts[dept_code] = blocker_dept_counts.get(dept_code, 0) + 1

    bottlenecks = [
        {"department_code": code, "blocking_count": cnt}
        for code, cnt in sorted(blocker_dept_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    # 5. Urgency distribution
    urgency_rows = (
        db.query(Issue.urgency, func.count(Issue.id))
        .group_by(Issue.urgency)
        .all()
    )
    urgency_map = {1: 0, 2: 0, 3: 0, 4: 0}
    for u, cnt in urgency_rows:
        urgency_map[u] = cnt
    urgency_dist = [
        {"urgency": 1, "label": "Low (1)", "count": urgency_map[1]},
        {"urgency": 2, "label": "Medium (2)", "count": urgency_map[2]},
        {"urgency": 3, "label": "High (3)", "count": urgency_map[3]},
        {"urgency": 4, "label": "Critical (4)", "count": urgency_map[4]},
    ]

    # 6. Classification source ratio
    source_rows = (
        db.query(Issue.classification_source, func.count(Issue.id))
        .group_by(Issue.classification_source)
        .all()
    )
    source_ratio = {"llm": 0, "fallback": 0}
    for src, cnt in source_rows:
        if src in source_ratio:
            source_ratio[src] = cnt

    return AdminAnalyticsResponse(
        total_issues=total_issues,
        open_issues_count=open_issues_count,
        resolved_issues_count=resolved_issues_count,
        open_issues_by_dept=open_by_dept,
        median_resolution_time_hours_by_dept=resolution_times,
        currently_blocked_tasks_count=blocked_count,
        bottleneck_departments=bottlenecks,
        urgency_distribution=urgency_dist,
        classification_source_ratio=source_ratio,
    )


@router.post("/recompute-priorities")
def recompute_priorities(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    count = recompute_all_open_priorities(db)
    return {"message": f"Recomputed priorities for {count} open issues", "issues_updated": count}
