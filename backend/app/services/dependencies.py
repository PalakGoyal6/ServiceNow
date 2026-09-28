from typing import List, Dict, Set, Tuple
from collections import defaultdict, deque
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.app.models import Task, TaskDependency, Event
from backend.app.services.events import log_event


def get_issue_dependencies(db: Session, issue_id: str) -> List[TaskDependency]:
    tasks = db.query(Task.id).filter(Task.issue_id == issue_id).all()
    task_ids = [t[0] for t in tasks]
    if not task_ids:
        return []
    return (
        db.query(TaskDependency)
        .filter(TaskDependency.task_id.in_(task_ids))
        .all()
    )


def would_create_cycle(db: Session, issue_id: str, task_id: str, blocked_by_task_id: str) -> bool:
    """
    Checks if adding edge: task_id is blocked by blocked_by_task_id
    (i.e. blocked_by_task_id -> task_id execution order) would form a cycle.
    """
    if task_id == blocked_by_task_id:
        return True

    deps = get_issue_dependencies(db, issue_id)
    
    # Graph where edge A -> B means A blocks B (A must complete before B)
    # New edge would be: blocked_by_task_id -> task_id
    adj = defaultdict(list)
    for dep in deps:
        adj[dep.blocked_by_task_id].append(dep.task_id)
    adj[blocked_by_task_id].append(task_id)

    # Check if we can reach blocked_by_task_id from task_id (which means a cycle)
    visited = set()
    queue = deque([task_id])
    while queue:
        curr = queue.popleft()
        if curr == blocked_by_task_id:
            return True
        if curr not in visited:
            visited.add(curr)
            for neighbor in adj[curr]:
                queue.append(neighbor)
    return False


def get_blockers(db: Session, task_id: str) -> List[Task]:
    """
    Returns tasks that must resolve before this task can start.
    """
    deps = db.query(TaskDependency).filter(TaskDependency.task_id == task_id).all()
    blocker_ids = [d.blocked_by_task_id for d in deps]
    if not blocker_ids:
        return []
    return db.query(Task).filter(Task.id.in_(blocker_ids)).all()


def get_dependents(db: Session, task_id: str) -> List[Task]:
    """
    Returns tasks that are waiting on this task.
    """
    deps = db.query(TaskDependency).filter(TaskDependency.blocked_by_task_id == task_id).all()
    dependent_ids = [d.task_id for d in deps]
    if not dependent_ids:
        return []
    return db.query(Task).filter(Task.id.in_(dependent_ids)).all()


def recompute_block_states(db: Session, issue_id: str, actor_id: str = None) -> List[Task]:
    """
    Updates task statuses for the issue based on blocker resolution.
    Unblocks tasks when all their blockers are resolved/rejected.
    """
    tasks = db.query(Task).filter(Task.issue_id == issue_id).all()
    task_map = {t.id: t for t in tasks}
    deps = get_issue_dependencies(db, issue_id)
    
    # Map: task_id -> list of blocker task_ids
    blockers_map = defaultdict(list)
    for dep in deps:
        blockers_map[dep.task_id].append(dep.blocked_by_task_id)

    unblocked_tasks = []
    now = datetime.now(timezone.utc)

    for task in tasks:
        # Ignore already terminal tasks or in-progress tasks
        if task.status in ["resolved", "rejected"]:
            continue

        blocker_ids = blockers_map.get(task.id, [])
        all_resolved = True
        for b_id in blocker_ids:
            b_task = task_map.get(b_id)
            if b_task and b_task.status not in ["resolved", "rejected"]:
                all_resolved = False
                break

        if not all_resolved:
            if task.status != "blocked":
                task.status = "blocked"
                task.updated_at = now
        else:
            if task.status == "blocked":
                task.status = "pending"
                task.unblocked_at = now
                task.updated_at = now
                unblocked_tasks.append(task)
                log_event(
                    db=db,
                    issue_id=issue_id,
                    event_type="task_unblocked",
                    actor_id=actor_id,
                    task_id=task.id,
                    payload={"department_id": task.department_id, "department_code": task.department.code if task.department else ""},
                )

    db.flush()
    return unblocked_tasks


def get_execution_order(db: Session, issue_id: str) -> List[Dict]:
    """
    Calculates execution stages (topological sort partitioned by dependency levels).
    Returns list of stage dicts: [{"stage_number": 1, "tasks": [...]}, ...]
    """
    tasks = db.query(Task).filter(Task.issue_id == issue_id).all()
    if not tasks:
        return []

    deps = get_issue_dependencies(db, issue_id)
    # blocker_map: task_id -> set of blocker_ids
    blockers = {t.id: set() for t in tasks}
    for dep in deps:
        if dep.task_id in blockers:
            blockers[dep.task_id].add(dep.blocked_by_task_id)

    # Compute level/depth for each task
    # Level 0 = tasks with no blockers
    # Level k = 1 + max(level of all blockers)
    levels: Dict[str, int] = {}
    
    def get_level(task_id: str, visiting: Set[str]) -> int:
        if task_id in levels:
            return levels[task_id]
        if task_id in visiting:
            return 0  # Cycle safeguard
        visiting.add(task_id)
        
        b_ids = blockers.get(task_id, set())
        if not b_ids:
            lvl = 0
        else:
            lvl = 1 + max(get_level(b, visiting) for b in b_ids)
            
        visiting.remove(task_id)
        levels[task_id] = lvl
        return lvl

    for t in tasks:
        get_level(t.id, set())

    # Group tasks by stage
    stages_dict = defaultdict(list)
    task_map = {t.id: t for t in tasks}

    for task in tasks:
        lvl = levels.get(task.id, 0)
        # Find department names of blockers for this task
        blocker_dept_names = []
        for b_id in blockers.get(task.id, set()):
            b_task = task_map.get(b_id)
            if b_task and b_task.department:
                blocker_dept_names.append(b_task.department.name)

        stages_dict[lvl].append({
            "task_id": task.id,
            "department_id": task.department_id,
            "department_code": task.department.code if task.department else "",
            "department_name": task.department.name if task.department else "",
            "status": task.status,
            "action_needed": task.action_needed,
            "effective_priority": task.effective_priority,
            "resolved_at": task.resolved_at,
            "blocked_by_dept_names": blocker_dept_names,
        })

    stages = []
    for stage_num in sorted(stages_dict.keys()):
        stages.append({
            "stage_number": stage_num + 1,
            "tasks": stages_dict[stage_num]
        })

    return stages
