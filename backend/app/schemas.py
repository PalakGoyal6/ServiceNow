from datetime import date, datetime
from typing import List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field


# --- Auth & Users ---
class LoginRequest(BaseModel):
    email: str
    password: str


class StudentProfileSchema(BaseModel):
    roll_no: str
    programme: str
    year_of_study: int

    model_config = ConfigDict(from_attributes=True)


class UserSchema(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    department_id: Optional[int] = None
    created_at: datetime
    student_profile: Optional[StudentProfileSchema] = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSchema


class DemoUserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    department_id: Optional[int] = None
    department_code: Optional[str] = None
    department_name: Optional[str] = None
    description: Optional[str] = None


# --- Departments ---
class DepartmentSchema(BaseModel):
    id: int
    code: str
    name: str
    description: str

    model_config = ConfigDict(from_attributes=True)


# --- Classifier Schemas ---
class DeptAssignment(BaseModel):
    department_code: str
    dept_summary: str
    action_needed: str
    confidence: float = 1.0


class DependencySchema(BaseModel):
    blocked_department_code: str
    blocked_by_department_code: str
    reason: str


class Classification(BaseModel):
    title: str
    urgency: int
    urgency_reason: str
    deadline: Optional[date] = None
    departments: List[DeptAssignment]
    dependencies: List[DependencySchema] = []


# --- Messages ---
class MessageCreate(BaseModel):
    body: str
    task_id: Optional[str] = None
    visibility: str = "student_and_staff"  # or 'department_only'


class MessageResponse(BaseModel):
    id: str
    issue_id: str
    task_id: Optional[str] = None
    author_id: str
    author_name: str
    author_role: str
    department_code: Optional[str] = None
    body: str
    visibility: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Events ---
class EventResponse(BaseModel):
    id: int
    issue_id: str
    task_id: Optional[str] = None
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    type: str
    payload: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Execution Order / Stages ---
class StageTaskInfo(BaseModel):
    task_id: str
    department_id: int
    department_code: str
    department_name: str
    status: str
    action_needed: str
    effective_priority: Optional[int] = None
    priority_label: Optional[str] = None
    resolved_at: Optional[datetime] = None
    blocked_by_dept_names: List[str] = []


class ExecutionStage(BaseModel):
    stage_number: int
    tasks: List[StageTaskInfo]


# --- Tasks ---
class TaskStudentView(BaseModel):
    id: str
    department_id: int
    department_code: str
    department_name: str
    status: str
    action_needed: str
    resolved_at: Optional[datetime] = None


class TaskStaffSelfView(BaseModel):
    id: str
    issue_id: str
    department_id: int
    department_code: str
    department_name: str
    status: str
    dept_summary: str
    action_needed: str
    base_priority: int
    effective_priority: int
    priority_label: str
    priority_inherited: bool = False
    priority_inheritance_reason: Optional[str] = None
    assigned_to: Optional[str] = None
    assignee_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    unblocked_at: Optional[datetime] = None
    is_newly_unblocked: bool = False


class TaskStaffOtherView(BaseModel):
    id: str
    department_id: int
    department_code: str
    department_name: str
    status: str
    action_needed: str
    resolved_at: Optional[datetime] = None


class TaskUpdateStatusRequest(BaseModel):
    status: str  # 'pending' | 'in_progress' | 'waiting_on_student' | 'resolved' | 'rejected'
    note: Optional[str] = None


class TaskAssignRequest(BaseModel):
    user_id: Optional[str] = None


class AddDepartmentRequest(BaseModel):
    department_code: str
    note: str
    blocked_by_task_id: Optional[str] = None


class AddDependencyRequest(BaseModel):
    task_id: str
    blocked_by_task_id: str
    reason: str = "Staff configured dependency"


class DeleteDependencyRequest(BaseModel):
    task_id: str
    blocked_by_task_id: str


# --- Issues ---
class IssueCreate(BaseModel):
    text: str
    deadline: Optional[date] = None


class IssueStudentListCard(BaseModel):
    id: str
    title: str
    urgency: int
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    department_statuses: List[dict]  # [{"code": "FIN", "name": "Finance", "status": "resolved"}]


class IssueStudentDetailResponse(BaseModel):
    id: str
    title: str
    status: str
    urgency: int
    deadline: Optional[date] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    tasks: List[TaskStudentView]
    execution_order: List[ExecutionStage]
    messages: List[MessageResponse]
    waiting_banner: Optional[dict] = None  # if any dept is waiting_on_student: {department_name, latest_message}


class StaffTaskListItem(BaseModel):
    task_id: str
    issue_id: str
    title: str
    student_name: str
    student_roll_no: Optional[str] = None
    status: str
    dept_summary: str
    action_needed: str
    effective_priority: int
    priority_label: str
    priority_inherited: bool = False
    deadline: Optional[date] = None
    created_at: datetime
    unblocked_at: Optional[datetime] = None
    is_newly_unblocked: bool = False
    is_auto_classified: bool = False
    other_departments_count: int
    other_departments_preview: List[dict]  # [{"code": "EXAM", "status": "blocked"}]


class StaffTaskDetailResponse(BaseModel):
    task: TaskStaffSelfView
    issue_id: str
    issue_title: str
    issue_status: str
    issue_urgency: int
    issue_deadline: Optional[date] = None
    issue_created_at: datetime
    classification_source: str
    student_info: dict  # {name, roll_no, programme, year_of_study}
    other_tasks: List[TaskStaffOtherView]
    execution_order: List[ExecutionStage]
    messages: List[MessageResponse]
    events: List[EventResponse]
    allowed_transitions: List[str]


class ReopenIssueRequest(BaseModel):
    body: str


# --- Analytics & Stats ---
class StaffStatsResponse(BaseModel):
    active_count: int
    blocked_count: int
    resolved_this_week_count: int
    department_name: str
    department_code: str


class AdminAnalyticsResponse(BaseModel):
    total_issues: int
    open_issues_count: int
    resolved_issues_count: int
    open_issues_by_dept: List[dict]
    median_resolution_time_hours_by_dept: List[dict]
    currently_blocked_tasks_count: int
    bottleneck_departments: List[dict]  # departments most often blocking other tasks
    urgency_distribution: List[dict]
    classification_source_ratio: dict
