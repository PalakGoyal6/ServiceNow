# Comprehensive Project File Guide: Student Support Triage & Joined-Up Case Management

This document provides a detailed, file-by-file reference explaining the architecture, responsibilities, models, functions, and components of the entire codebase.

---

## 📁 Repository Overview

```
/
├── backend/
│   ├── app/
│   │   ├── config.py              # Environment settings & configuration
│   │   ├── db.py                  # SQLAlchemy engine, session & SQLite pragmas
│   │   ├── models.py              # SQLAlchemy database ORM models
│   │   ├── schemas.py             # Pydantic v2 validation & response schemas
│   │   ├── auth.py                # Password hashing, JWT tokens, RBAC dependencies
│   │   ├── permissions.py         # All access-control & privacy-shielding checks
│   │   ├── departments.yaml       # Master catalog of the 12 support departments
│   │   ├── seed.py                # Database seeder with sample data & personas
│   │   ├── main.py                # FastAPI app instance, CORS & lifecycle hooks
│   │   ├── prompts/
│   │   │   └── classify.md        # Few-shot LLM triage classification prompt
│   │   ├── services/
│   │   │   ├── classifier.py      # AI & keyword-based classification engine
│   │   │   ├── dependencies.py    # DAG cycle checks & topological staging
│   │   │   ├── events.py          # Append-only audit logging service
│   │   │   ├── intake.py          # Orchestrator for end-to-end case intake
│   │   │   ├── llm_client.py      # Provider-agnostic LLM wrapper (Gemini/OpenAI/Anthropic)
│   │   │   ├── priority.py        # Base priority & transitive priority inheritance
│   │   │   └── tasks.py           # Task state machine, unblocking & resolution
│   │   └── routers/
│   │       ├── admin.py           # Admin analytics & SLA metrics endpoints
│   │       ├── auth.py            # Login, current user & persona switcher endpoints
│   │       ├── staff.py           # Department task queue & management endpoints
│   │       └── student.py         # Student intake, case tracking & messaging
│   ├── tests/                     # Pytest automated test suite (17 tests)
│   ├── requirements.txt           # Python dependency requirements
│   └── .env.example               # Backend environment variables template
├── frontend/
│   ├── app/
│   │   ├── layout.tsx             # Root layout with AuthProvider & Navbar
│   │   ├── page.tsx               # Root redirector based on user role
│   │   ├── globals.css            # Tailwind directives & CSS design tokens
│   │   ├── login/page.tsx         # 1-click persona switcher & login page
│   │   ├── student/
│   │   │   ├── page.tsx           # Student dashboard with department status chips
│   │   │   ├── new/page.tsx       # Natural language issue submission form
│   │   │   └── issues/[id]/page.tsx # Case tracker with workflow steps & messaging
│   │   ├── staff/
│   │   │   ├── page.tsx           # Department task queue sorted by priority
│   │   │   └── tasks/[id]/page.tsx # Task workspace with status controls & audit log
│   │   └── admin/
│   │       └── page.tsx           # Executive analytics dashboard (Recharts)
│   ├── components/
│   │   ├── Navbar.tsx             # Navigation bar with role badge & switcher
│   │   ├── StatusBadge.tsx        # Standardized color-coded status pills
│   │   ├── PriorityBadge.tsx      # Priority score badge with inheritance indicator
│   │   ├── ExecutionOrderTracker.tsx # Visual workflow stage-by-stage pipeline
│   │   ├── TimelineEvents.tsx     # Human-readable chronological audit history
│   │   └── PersonaSwitcherModal.tsx # Instant 1-click demo persona switcher modal
│   ├── lib/
│   │   ├── api.ts                 # Typed fetch client with JWT injection
│   │   └── auth-context.tsx       # React AuthContext managing user sessions
│   ├── package.json               # Node.js dependencies
│   ├── tailwind.config.js         # Tailwind theme & color configurations
│   └── tsconfig.json              # TypeScript compiler configuration
├── DECISIONS.md                   # Architectural choices & design rationale
└── README.md                      # Setup instructions & 3-minute demo script
```

---

# 🧠 Backend Files Breakdown

### 1. `backend/app/models.py`
Defines all SQLAlchemy ORM relational database models. UUID strings (`VARCHAR(36)`) are used for primary keys and integer IDs for departments. Soft status changes are used everywhere; **nothing is ever hard-deleted**.
- **`User`**: Core user record (`id`, `email`, `password_hash`, `full_name`, `role` (`student` | `staff` | `admin`), `department_id`, `created_at`).
- **`StudentProfile`**: Extended student attributes (`user_id`, `roll_no`, `programme`, `year_of_study`).
- **`Department`**: Master table for the 12 university support offices (`id`, `code`, `name`, `description`).
- **`Issue`**: Top-level case submitted by a student (`id`, `student_id`, `title`, `description`, `urgency` (1-4), `deadline`, `status` (`open` | `resolved`), `classification_source` (`llm` | `fallback`), `classification_raw`, `created_at`, `resolved_at`).
- **`Task`**: Department-specific work order (`id`, `issue_id`, `department_id`, `status` (`blocked` | `pending` | `in_progress` | `waiting_on_student` | `resolved` | `rejected`), `dept_summary`, `action_needed`, `base_priority`, `effective_priority`, `assigned_to`, `created_at`, `unblocked_at`, `resolved_at`).
- **`TaskDependency`**: Prerequisite relationship expressing that `task_id` cannot start until `blocked_by_task_id` is resolved (`task_id`, `blocked_by_task_id`, `reason`, `created_by`).
- **`Message`**: Two-way communication thread (`id`, `issue_id`, `task_id`, `author_id`, `body`, `visibility` (`student_and_staff` | `department_only`), `created_at`).
- **`Event`**: Append-only immutable audit log (`id`, `issue_id`, `task_id`, `actor_id`, `type`, `payload`, `created_at`).

---

### 2. `backend/app/schemas.py`
Pydantic v2 schemas that enforce strict request validation, type-safety, and privacy-shielded response serialization.
- **Auth schemas**: `LoginRequest`, `TokenResponse`, `UserSchema`, `DemoUserResponse`.
- **Intake & Classifier schemas**: `DeptAssignment`, `DependencySchema`, `Classification`.
- **Student-facing schemas**: `IssueStudentListCard`, `IssueStudentDetailResponse`, `TaskStudentView` (excludes `dept_summary`, internal notes, and staff priorities).
- **Staff-facing schemas**: `StaffTaskListItem`, `StaffTaskDetailResponse`, `TaskStaffSelfView` (includes full dept summary), `TaskStaffOtherView` (redacts other departments' summaries).
- **Admin & Analytics schemas**: `AdminAnalyticsResponse`, `StaffStatsResponse`, `ExecutionStage`.

---

### 3. `backend/app/auth.py`
Authentication and Authorization infrastructure:
- **`get_password_hash(password)`** / **`verify_password(plain, hashed)`**: Cryptographic password management using direct `bcrypt`.
- **`create_access_token(data)`**: Generates signed HS256 JWT access tokens with expiration.
- **`get_current_user`**: Validates `Authorization: Bearer <token>` header, decoding user identity.
- **`get_current_student` / `get_current_staff` / `get_current_admin`**: FastAPI role-based access control dependencies.

---

### 4. `backend/app/permissions.py`
All data-privacy and access-control checks live in this file:
- **`check_student_owns_issue`**: Asserts student access; returns HTTP 404 on probing another student's issue.
- **`check_staff_on_issue`**: Verifies a staff member's department is actively assigned to the issue; returns HTTP 403 otherwise.
- **`check_staff_can_modify_task`**: Restricts task status and assignment modifications strictly to staff in that task's department.
- **`filter_messages_for_user`**: Filters out `department_only` internal notes from students and unrelated departments.

---

### 5. `backend/app/config.py` & `backend/app/db.py`
- **`config.py`**: Manages environment variables (`DATABASE_URL`, `JWT_SECRET`, `LLM_PROVIDER`, `LLM_API_KEY`, `DEMO_MODE`, `CORS_ORIGINS`).
- **`db.py`**: Initializes SQLAlchemy engine and session factory. Attaches connection listeners to automatically enforce `PRAGMA foreign_keys = ON;` and `PRAGMA journal_mode = WAL;` on SQLite.

---

### 6. `backend/app/services/` (Core Business Logic)

- **`intake.py`**:
  - `safety_screen(text)`: Reserved pre-classification hook for future crisis/escalation handling.
  - `submit_issue(db, student, text, deadline)`: Orchestrates intake pipeline in a single database transaction (classification, task creation, dependency wiring, priority calculation, and event logging).
- **`classifier.py`**:
  - `classify_issue(...)`: Invokes LLM with prompt from `prompts/classify.md`.
  - `fallback_classify(...)`: Deterministic keyword & rule-based classifier ensuring the app always works even with `LLM_PROVIDER=none`.
  - `validate_and_normalize(...)`: Cleans output, deduplicates departments, clamps urgency (1-4), removes invalid/cyclic dependencies, and falls back to DSW if no department matches.
- **`priority.py`**:
  - `calculate_base_priority(...)`: Calculates 0-100 score based on urgency (20-80), deadline proximity (+15 for <=2d, +8 for <=7d), and aging (+1/day up to +10).
  - `recompute_issue_priorities(...)`: Executes **transitive priority inheritance** so blocker tasks inherit the urgency and deadlines of tasks waiting on them.
  - `get_priority_inheritance_info(...)`: Generates human-readable explanations (e.g. *"Priority raised because Examinations is waiting on this"*).
- **`dependencies.py`**:
  - `would_create_cycle(...)`: DFS cycle detector preventing deadlock loops in task dependencies.
  - `recompute_block_states(...)`: Automatically unblocks tasks to `pending` when all blockers resolve/reject.
  - `get_execution_order(...)`: Topological sort partitioning tasks into numbered parallel workflow stages.
- **`tasks.py`**:
  - `change_status(...)`: Validates allowed status transitions, triggers unblocking side-effects, auto-resolves issues, and reroutes rejected cases to DSW if no tasks remain.
  - `student_reopen_issue(...)`: Allows students to reopen resolved cases within 7 days.
  - `add_department_to_issue(...)` / `add_dependency(...)`: Dynamically expands department workflows.
- **`events.py`**:
  - `log_event(...)`: Appends immutable audit records for every state change.
- **`llm_client.py`**:
  - `complete_json(...)`: Provider-agnostic client supporting Anthropic, OpenAI, and Gemini with JSON extraction and automated validation retry.

---

### 7. `backend/app/routers/`

- **`auth.py`**: Endpoints for `/auth/login`, `/auth/me`, and `/auth/demo-users`.
- **`student.py`**: Endpoints for `POST /student/issues`, `GET /student/issues`, `GET /student/issues/{id}`, `POST /student/issues/{id}/messages`, and `POST /student/issues/{id}/reopen`.
- **`staff.py`**: Endpoints for `GET /staff/tasks` (filtered by active/blocked/resolved, sorted by priority), `GET /staff/tasks/{id}`, `GET /staff/tasks/{id}/original-message` (audited raw description access), `PATCH /staff/tasks/{id}/status`, `POST /staff/tasks/{id}/messages`, and dependency controls.
- **`admin.py`**: Endpoints for `GET /admin/analytics` (bottlenecks, resolution SLAs, caseloads) and `POST /admin/recompute-priorities`.

---

### 8. `backend/app/seed.py` & `departments.yaml`
- **`departments.yaml`**: Configuration declaring the 12 university departments (ACAD, EXAM, FIN, SCHOL, HOSTEL, COUNS, HEALTH, DISAB, LIB, IT, PLACE, DSW).
- **`seed.py`**: Populates database with 1 admin, 5 students, 24 staff members (all password `demo1234`), and 12 realistic historical and multi-stage test cases.

---

# 🎨 Frontend Files Breakdown

### 1. Core State & Utilities
- **`frontend/lib/api.ts`**: Centralized, typed API wrapper that attaches JWT tokens from `localStorage` and handles standardized errors.
- **`frontend/lib/auth-context.tsx`**: React Context managing user authentication, automatic login routing, and instant persona switching.

---

### 2. UI Components (`frontend/components/`)
- **`Navbar.tsx`**: Sticky top navigation bar showing current user persona, role badge, quick links, Switch Persona button, and logout.
- **`PersonaSwitcherModal.tsx`**: Modal presenting 1-click login buttons for 3 students, staff from 12 departments, and the administrator.
- **`StatusBadge.tsx`**: Color-coded status badge pairing distinct background/border tokens with icons:
  - `blocked` (slate/grey)
  - `pending` (amber)
  - `in_progress` (blue)
  - `waiting_on_student` (purple)
  - `resolved` (emerald/green)
  - `rejected` (rose/red)
- **`PriorityBadge.tsx`**: Visual badge displaying `Critical`, `High`, `Medium`, `Low` labels, flame icons for critical tasks, and an `Inherited` tag with explanatory tooltip.
- **`ExecutionOrderTracker.tsx`**: Visual workflow pipeline rendering stages (e.g. *Step 1: Scholarships → Step 2: Finance → Step 3: Examinations*) with blocker indicators (*"Waiting on Finance"*).
- **`TimelineEvents.tsx`**: Chronological audit trail showing state changes, message posts, and raw description accesses with user attribution.

---

### 3. Application Pages (`frontend/app/`)
- **`layout.tsx`**: Application layout wrapping all pages in `AuthProvider` and `Navbar` with Inter typography.
- **`page.tsx`**: Index router automatically redirecting authenticated users to `/student`, `/staff`, or `/admin`.
- **`login/page.tsx`**: Login page featuring a grid of 1-click persona buttons and credential form.
- **`student/page.tsx`**: Student dashboard listing active and resolved issues with department progress chips. Polls live every 5s.
- **`student/new/page.tsx`**: Intake page with natural language textarea, optional target date picker, demo presets, and AI triage loading animation.
- **`student/issues/[id]/page.tsx`**: Student case tracker displaying the execution order, prominent "Waiting on Student" banner, and two-way messaging thread.
- **`staff/page.tsx`**: Department staff dashboard with live metric counters (Active, Blocked, Resolved/Week), status filter tabs, and priority-sorted task queue.
- **`staff/tasks/[id]/page.tsx`**: Staff case workspace featuring AI department summary, action required, status transition buttons, audited "View Original Message" button, department internal note toggle, Add Department modal, and Dependency configuration modal.
- **`admin/page.tsx`**: Executive analytics page with interactive Recharts charts:
  - **Bottleneck Departments** (departments most frequently blocking downstream workflows)
  - **Median SLA Resolution Times** (hours per department)
  - **Open Task Caseload** by department
  - **Urgency Distribution** and **AI vs Fallback Triage Ratio**
  - **Recompute Priorities** manual trigger

---

# 🧪 Backend Test Suite (`backend/tests/`)

- **`conftest.py`**: Test setup using in-memory SQLite (`StaticPool`), FastAPI `TestClient`, and pre-seeded test database fixtures.
- **`test_permissions.py`**: Verifies 403 access control, summary shielding, student privacy, and `raw_description_viewed` audit logging.
- **`test_dependencies.py`**: Verifies cycle detection, multi-blocker unblocking, and topological sort stages.
- **`test_priority.py`**: Verifies base priority scoring, labels, and transitive priority inheritance.
- **`test_lifecycle.py`**: Verifies task state transitions, issue auto-resolution, 7-day student reopening, and DSW rejection fallback.
- **`test_classifier.py`**: Tests output normalization, unknown code filtering, and keyword-based fallback rules.
- **`test_intake.py`**: End-to-end integration test verifying the complete submission, classification, task creation, and audit logging pipeline.
