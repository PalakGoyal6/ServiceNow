# Build prompt: Student Support Triage & Joined-Up Case Management

You are building a hackathon project end to end. Read this whole document before writing any code. Work in the phases listed at the bottom, and after each phase make sure the app runs and the acceptance checks pass before moving on. If anything here is ambiguous, pick the simplest reasonable option, note the decision in `DECISIONS.md`, and keep going.

---

## 1. What we're building (context)

A university has 12 separate support departments. Today a student with a problem has to figure out which department to go to, fill in separate forms for each, and repeat their story every time. Departments can't see what the others are doing, so problems that touch several departments stall.

Our system fixes this with one flow:

1. A student describes their issue **once**, in their own words.
2. An AI model reads it and decides **which departments** are involved, **how urgent** it is, and **in what order** the departments must act (e.g. Finance must clear unpaid fees before Examinations can add the student to the exam list).
3. The system creates **one task per department** for that issue.
4. Each department sees only its own tasks on a live dashboard, sorted by priority. Tasks that are waiting on another department appear as **blocked** and unblock automatically when the blocking task is resolved.
5. Everyone working on the issue sees the **status of every department** on it ("Finance: resolved, Examinations: in progress").
6. The student sees the same per-department progress on their own dashboard and can exchange messages with departments.
7. When every task is resolved, the issue is marked **resolved** (never deleted) and shows as resolved to the student.

**Out of scope for now:** crisis/self-harm detection and emergency escalation. Do not build it. But structure the intake pipeline so a "safety screen" step can later be inserted before classification (see §6.1).

---

## 2. Tech stack (fixed)

- **Frontend:** Next.js 14+ (App Router), TypeScript, Tailwind CSS. Use `fetch` + SWR for data fetching with polling for live updates.
- **Backend:** FastAPI (Python 3.11+), Pydantic v2, SQLAlchemy 2.0 ORM, Alembic for migrations.
- **Database:** SQLite (file `backend/app.db`). On every connection enable `PRAGMA foreign_keys = ON` and `PRAGMA journal_mode = WAL`.
- **Auth:** simple JWT (python-jose or PyJWT) with bcrypt-hashed passwords. Seeded demo users. Add a **demo login switcher** on the login page (one-click buttons: "Login as student Priya", "Login as Finance staff", etc.) so we can switch personas fast during the demo.
- **AI:** provider-agnostic LLM client behind an interface (see §6). Configured via environment variables. Must also work with **no API key** by falling back to a rule-based classifier, so the demo never breaks.
- **Live updates:** polling every 5 seconds via SWR `refreshInterval`. Do not add websockets.

---

## 3. Repository layout

```
/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI app, CORS, router registration
│   │   ├── config.py              # settings from env (pydantic-settings)
│   │   ├── db.py                  # engine, session, SQLite pragmas
│   │   ├── models.py              # SQLAlchemy models
│   │   ├── schemas.py             # Pydantic request/response models
│   │   ├── auth.py                # JWT, password hashing, current-user deps
│   │   ├── permissions.py         # ALL access-control checks live here
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── student.py         # student-facing endpoints
│   │   │   ├── staff.py           # department-facing endpoints
│   │   │   └── admin.py           # analytics, departments, routing config
│   │   ├── services/
│   │   │   ├── intake.py          # orchestrates the whole intake pipeline
│   │   │   ├── classifier.py      # LLM + fallback classification
│   │   │   ├── llm_client.py      # provider-agnostic LLM wrapper
│   │   │   ├── priority.py        # priority calculation + inheritance
│   │   │   ├── dependencies.py    # blocked_by graph, cycle checks, unblocking
│   │   │   ├── tasks.py           # task state transitions
│   │   │   └── events.py          # append-only event log helper
│   │   ├── prompts/
│   │   │   └── classify.md        # the classification prompt template
│   │   └── seed.py                # departments, users, sample issues
│   ├── alembic/
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── login/page.tsx
│   │   ├── student/page.tsx               # student dashboard (list of my issues)
│   │   ├── student/new/page.tsx           # submit an issue
│   │   ├── student/issues/[id]/page.tsx   # issue detail + progress + messages
│   │   ├── staff/page.tsx                 # department dashboard (task queue)
│   │   ├── staff/tasks/[id]/page.tsx      # task detail
│   │   └── admin/page.tsx                 # analytics
│   ├── components/
│   ├── lib/api.ts                          # typed API client, attaches JWT
│   └── .env.example
├── DECISIONS.md
└── README.md                               # setup + demo script
```

---

## 4. Departments (seed data, editable config)

Seed these 12 departments from a single config file (`backend/app/departments.yaml` or a Python list in `seed.py`) so the team can rename them without touching code. Each has an `id`, `code`, `name`, and a one-line `description` of what it handles; the descriptions are fed to the classifier, so write them carefully.

| code | name | handles |
|---|---|---|
| ACAD | Academic Affairs | course registration, attendance shortfall, academic appeals, credits |
| EXAM | Examinations | exam eligibility lists, admit cards, re-evaluation, results |
| FIN | Finance & Fees | fee payment, dues, refunds, fines, payment receipts |
| SCHOL | Scholarships & Financial Aid | scholarships, fee waivers, emergency financial support |
| HOSTEL | Hostel & Accommodation | room allocation, hostel issues, mess, accommodation |
| COUNS | Counselling & Wellbeing | stress, anxiety, emotional wellbeing, personal difficulties |
| HEALTH | Health Centre | illness, medical certificates, medical leave |
| DISAB | Disability Support | accommodations, accessibility, extra exam time |
| LIB | Library | library access, fines, resources |
| IT | IT Services | portal login, email, Wi-Fi, LMS access |
| PLACE | Training & Placement | internships, placement eligibility, company process issues |
| DSW | Dean of Student Welfare | harassment complaints, disputes, anything cross-cutting or unclear |

---

## 5. Data model (SQLite via SQLAlchemy)

Use UUID strings as primary keys for issues/tasks/messages (store as `TEXT`), integer keys for departments. All timestamps UTC, ISO format. **Nothing is ever hard-deleted.** Resolution is a status change.

### users
`id, email (unique), password_hash, full_name, role ('student' | 'staff' | 'admin'), department_id (nullable, required when role='staff'), created_at`

### student_profiles
`user_id (PK, FK users), roll_no, programme, year_of_study`

### departments
`id, code (unique), name, description`

### issues
One row per thing a student submits.
- `id`
- `student_id` (FK users)
- `title` (short, AI-generated, max ~80 chars)
- `description` (the student's raw text; **sensitive**, see §7)
- `urgency` (int 1–4, from classifier; 4 = most urgent)
- `deadline` (nullable date; extracted by classifier if the student mentions one, e.g. "exam on Friday")
- `status` ('open' | 'resolved')
- `classification_source` ('llm' | 'fallback')
- `classification_raw` (JSON text of the full classifier output, for debugging)
- `created_at, updated_at, resolved_at`

### tasks
One row per department involved in an issue. This is the heart of the system.
- `id`
- `issue_id` (FK issues)
- `department_id` (FK departments)
- `status` ('blocked' | 'pending' | 'in_progress' | 'waiting_on_student' | 'resolved' | 'rejected')
  - `rejected` = the department says "not ours"; see §8.4
- `dept_summary` (AI-written summary of the issue **tailored to this department**, containing only what this department needs to know; see §7)
- `action_needed` (one line: what this department is expected to do)
- `base_priority` (int, computed, see §9)
- `effective_priority` (int, computed, includes inheritance, see §9)
- `assigned_to` (nullable FK users, a staff member in that department)
- `created_at, updated_at, resolved_at`
- Unique constraint on `(issue_id, department_id)`.

### task_dependencies
Represents "task A cannot start until task B is resolved".
- `task_id` (FK tasks) — the blocked task
- `blocked_by_task_id` (FK tasks) — the task it waits for
- `reason` (short text from classifier, e.g. "Exam eligibility requires fee clearance")
- `created_by` ('ai' | user id)
- PK `(task_id, blocked_by_task_id)`
- Both tasks must belong to the same issue. The graph must stay acyclic (§10).

### messages
Two-way communication on an issue.
- `id, issue_id, task_id (nullable), author_id (FK users), body, created_at`
- `visibility` ('student_and_staff' | 'department_only')
  - `student_and_staff`: visible to the student and all departments on the issue
  - `department_only`: internal note, visible only to staff of the author's department

### events
Append-only audit/timeline log. Never updated or deleted. Every state change in the system writes one row here via `services/events.py`.
- `id (autoincrement), issue_id, task_id (nullable), actor_id (nullable; null = system/AI), type, payload (JSON text), created_at`
- Event types: `issue_created, classified, task_created, dependency_added, dependency_removed, task_status_changed, task_unblocked, task_rejected, task_reassigned, department_added, message_posted, priority_changed, issue_resolved, issue_reopened`

Create indexes on: `tasks(department_id, status)`, `tasks(issue_id)`, `events(issue_id, created_at)`, `messages(issue_id, created_at)`.

---

## 6. Intake pipeline

Implement in `services/intake.py` as a sequence of small functions so steps can be inserted later:

```
submit_issue(student, text, optional_deadline)
  → [future: safety_screen(text)]   # leave a clearly commented no-op hook here
  → classify(text, departments)     # LLM, fallback on failure
  → validate_and_normalize(result)
  → create issue + tasks + dependencies in ONE transaction
  → compute priorities
  → write events
  → return issue with tasks
```

### 6.1 Safety hook
Add a function `safety_screen(text) -> None` that currently does nothing, with a docstring saying it's reserved for a future crisis-detection step that runs before classification. Do not implement detection logic.

### 6.2 LLM client (`llm_client.py`)
- Interface: `complete_json(system: str, user: str, schema: type[BaseModel]) -> BaseModel`.
- Env vars: `LLM_PROVIDER` (`anthropic` | `openai` | `gemini` | `none`), `LLM_API_KEY`, `LLM_MODEL`.
- Instruct the model to return **only JSON**. Strip markdown fences before parsing. Validate with Pydantic. On validation failure, retry once with the validation error appended to the prompt. On second failure or any network error or `LLM_PROVIDER=none`, raise so the caller uses the fallback.
- Timeout 20s.

### 6.3 Classifier output schema

```python
class DeptAssignment(BaseModel):
    department_code: str              # must be one of the 12 codes
    dept_summary: str                 # 1-3 sentences, ONLY info this dept needs
    action_needed: str                # one line
    confidence: float                 # 0-1

class Dependency(BaseModel):
    blocked_department_code: str
    blocked_by_department_code: str
    reason: str

class Classification(BaseModel):
    title: str                        # <= 80 chars, neutral
    urgency: int                      # 1-4
    urgency_reason: str
    deadline: date | None             # only if explicitly stated or clearly implied
    departments: list[DeptAssignment] # 1-4 items
    dependencies: list[Dependency]    # may be empty
```

### 6.4 Classification prompt (`prompts/classify.md`)
Write a careful prompt that:
- Includes today's date (for resolving "next Friday" into a real date).
- Lists all 12 departments with their descriptions.
- Tells the model to pick the **minimum** set of departments actually needed (1–4), not everything tangentially related.
- Defines urgency: 1 = routine, no time pressure; 2 = should be handled this week; 3 = time-sensitive, a deadline within ~7 days or significant impact on studies; 4 = deadline within 48 hours or serious ongoing harm to the student's studies/wellbeing.
- Explains dependencies: add one only when a department **literally cannot complete its action** until another department finishes (e.g. EXAM blocked by FIN when the student is off the exam list due to unpaid fees). Parallel work is the default. Never create circular dependencies.
- **Privacy rule for dept_summary:** each department's summary must contain only what that department needs to act. Example: if the student mentions both fee arrears and anxiety, the FIN summary mentions the fee issue and may say "student is also receiving wellbeing support" but must not describe mental-health details; the COUNS summary covers the wellbeing side and only briefly notes the financial stressor.
- Includes 3 worked examples (input → JSON), one of which has a dependency chain:
  - "I couldn't pay my semester fees because my scholarship money hasn't come yet, and now my name isn't on the exam list for the exam on 3rd Oct." → SCHOL, FIN, EXAM; FIN blocked by SCHOL; EXAM blocked by FIN; urgency 4 (if within 48h) or 3.
  - "My hostel Wi-Fi hasn't worked for a week and I can't submit assignments on the LMS." → IT only, urgency 2.
  - "I've been feeling really overwhelmed and I've missed a lot of classes, now I'm short on attendance." → COUNS + ACAD, no dependency, urgency 3.

### 6.5 Validation & normalization
After parsing: drop unknown department codes; deduplicate; clamp urgency to 1–4; drop dependencies that reference departments not in the list; drop any dependency that would create a cycle (log it); if zero departments remain, assign DSW with `action_needed = "Review and route manually"`.

### 6.6 Fallback classifier
Keyword-based, used when the LLM is unavailable. Map keyword lists to department codes (fees/payment/due → FIN; exam/admit card/hall ticket → EXAM; scholarship → SCHOL; hostel/room/mess → HOSTEL; wifi/portal/login/email → IT; stressed/anxious/overwhelmed → COUNS; etc.). Urgency from keywords ("tomorrow", "today", "urgent" → 4; "this week", a date within 7 days → 3; else 2). Hard-coded dependency rules: if both FIN and EXAM are present, EXAM blocked by FIN; if both SCHOL and FIN present, FIN blocked by SCHOL. `dept_summary` = first 200 chars of the text with a note "auto-classified". Set `classification_source = 'fallback'`. The UI should show a small "auto-classified" badge on these.

---

## 7. Access control (the most important non-functional requirement)

All checks live in `permissions.py` and every endpoint must go through them. Write tests for each rule.

- **Students** can see only their own issues, all tasks on them (department name, status, `action_needed`, resolved time), and `student_and_staff` messages. Students **cannot** see `dept_summary`, internal notes, priorities, or assignee names.
- **Staff** can see an issue **only if their department has a task on it** (any status, including rejected, so they keep context of what they touched).
- For an issue they can see, staff get:
  - their own task in full, including their department's `dept_summary`
  - for other departments' tasks: department name, status, and `action_needed` only (**not** the other departments' summaries)
  - `student_and_staff` messages, plus `department_only` notes from their own department
  - the student's name, roll number, programme, year
- Staff **cannot** see the student's raw `description` by default. Provide an explicit "View original message" button that calls a separate endpoint, which returns it only if the staff member's department has a task on the issue, and writes an `events` row of type `raw_description_viewed` so access is audited. (Add this event type.)
- Staff can modify only tasks belonging to their own department (except "add department", §8.5, which any involved department can do).
- **Admin** sees analytics and aggregate data, plus department/routing config. For the demo admin may see everything; mark this in `DECISIONS.md` as something to restrict later.

---

## 8. Task lifecycle & rules

Implement all transitions in `services/tasks.py` with a single `change_status(task, new_status, actor)` function that validates the transition, writes an event, and triggers the side effects below.

### 8.1 Allowed transitions
- `blocked → pending` (system only, when all blockers resolve)
- `pending → in_progress | waiting_on_student | resolved | rejected`
- `in_progress → waiting_on_student | resolved | rejected`
- `waiting_on_student → in_progress | resolved` (also auto-moves to `in_progress` when the student posts a message)
- `resolved → in_progress` (reopen by that department)
- A `blocked` task cannot be moved by staff except via rejecting it or removing its dependency.

### 8.2 Initial status
When tasks are created, any task with at least one unresolved blocker starts as `blocked`; all others start as `pending`.

### 8.3 Unblocking
When a task becomes `resolved` (or `rejected`), find every task that depends on it. For each, if **all** of its blockers are now resolved/rejected, move it to `pending`, write a `task_unblocked` event, and flag it as "newly unblocked" so the department dashboard highlights it (e.g. a badge for 24h).

### 8.4 Rejecting ("Not ours")
A department can reject its task with a required reason. The task becomes `rejected`, its blockers/dependents are handled as in 8.3, and the issue remains open. If rejecting leaves the issue with **no** non-rejected tasks, automatically create a task for DSW with `action_needed = "Re-route: previous department marked not relevant"`.

### 8.5 Adding a department
Any staff member whose department is on the issue can add another department with a short note. This creates a new task (status `pending` unless they also specify it's blocked by an existing task). The new department's `dept_summary` is generated by a small LLM call using the issue title, existing summaries, and the note (fallback: use the note).

### 8.6 Editing dependencies
Staff on the issue can add or remove a dependency between two tasks on that issue. Adding must pass the cycle check (§10). Recompute statuses (a task may become blocked or unblocked) and priorities afterwards.

### 8.7 Issue resolution
After any task status change: if every task on the issue is `resolved` or `rejected` and at least one is `resolved`, set the issue to `resolved`, set `resolved_at`, write `issue_resolved`. If a task on a resolved issue is reopened, set the issue back to `open` and write `issue_reopened`. The student can also reopen a resolved issue within 7 days with a message ("This isn't actually fixed"); this reopens the most recently resolved task.

---

## 9. Priority

In `services/priority.py`:

- **base_priority** (0–100) for each task:
  - urgency contributes `urgency * 20` (20–80)
  - deadline proximity: +15 if deadline within 2 days, +8 if within 7 days, +0 otherwise
  - aging: +1 per full day the task has been open (not blocked), capped at +10
  - clamp to 100
- **effective_priority** = max(own base_priority, effective_priority of every task this task blocks, transitively). This is **priority inheritance**: if EXAM is urgent because the exam is in two days, FIN (which blocks EXAM) becomes just as urgent even though fees alone wouldn't be.
- Recompute priorities for an issue whenever its tasks, dependencies, or deadline change. Also expose `POST /admin/recompute-priorities` and run a recompute of all open issues on backend startup (to apply aging).
- Map effective_priority to a label for the UI: ≥85 Critical, ≥65 High, ≥45 Medium, else Low.
- On the task detail page, if priority was inherited, show why: "Priority raised because Examinations is waiting on this (exam in 2 days)."

---

## 10. Dependency graph rules (`services/dependencies.py`)

- `would_create_cycle(issue_id, task_id, blocked_by_id) -> bool` via DFS over the issue's dependency edges.
- `get_blockers(task)`, `get_dependents(task)`, `recompute_block_states(issue_id)`.
- Provide `get_execution_order(issue_id)`: a topological sort grouped into stages (tasks in the same stage can run in parallel). The UI uses this to show the sequence as "Step 1: Scholarships → Step 2: Finance → Step 3: Examinations".

---

## 11. API endpoints

All endpoints except login require a JWT. Return 403 (not 404) when a user lacks access to an existing resource, except for students probing other students' issues, where return 404.

**Auth**
- `POST /auth/login` → `{access_token, user}`
- `GET /auth/me`
- `GET /auth/demo-users` → list of seeded users for the login switcher (only when `DEMO_MODE=true`)

**Student**
- `POST /student/issues` `{text, deadline?}` → created issue with tasks (this call runs the classifier; show a loading state on the frontend)
- `GET /student/issues` → my issues, newest first, with per-department status
- `GET /student/issues/{id}` → issue, tasks (student view), execution order, messages
- `POST /student/issues/{id}/messages` `{body, task_id?}`
- `POST /student/issues/{id}/reopen` `{body}`

**Staff**
- `GET /staff/tasks?status=active|blocked|resolved|all&sort=priority|created` → my department's tasks. `active` = pending + in_progress + waiting_on_student. Default: active, sorted by effective_priority desc.
- `GET /staff/tasks/{id}` → full task view per §7: my task, other depts' status + action_needed, execution order, messages, timeline events
- `GET /staff/tasks/{id}/original-message` → raw description (audited)
- `PATCH /staff/tasks/{id}/status` `{status, note?}` (note required for `rejected`)
- `PATCH /staff/tasks/{id}/assign` `{user_id}` (must be in same dept)
- `POST /staff/tasks/{id}/messages` `{body, visibility}`
- `POST /staff/issues/{issue_id}/departments` `{department_code, note, blocked_by_task_id?}`
- `POST /staff/issues/{issue_id}/dependencies` `{task_id, blocked_by_task_id, reason}`
- `DELETE /staff/issues/{issue_id}/dependencies` `{task_id, blocked_by_task_id}`
- `GET /staff/departments` → list for the "add department" picker
- `GET /staff/stats` → counts for my department (active, blocked, resolved this week)

**Admin**
- `GET /admin/analytics` → see §12.5
- `POST /admin/recompute-priorities`

---

## 12. Frontend pages

Clean, calm, accessible UI. Neutral palette with one accent colour. Status colours: blocked = grey, pending = amber, in_progress = blue, waiting_on_student = purple, resolved = green, rejected = muted red. Always pair colour with a text label. Mobile-friendly (students will use phones).

### 12.1 Login (`/login`)
Email/password form plus, when demo mode is on, a grid of one-click persona buttons: 3 students, one staff member each from FIN, EXAM, SCHOL, COUNS, ACAD, IT, HOSTEL, DSW, and an admin.

### 12.2 Student: submit issue (`/student/new`)
- Single large textarea: "Tell us what's going on, in your own words. You don't need to know which department handles it."
- Optional deadline date picker ("Is there a date this needs sorting by?").
- Submit → loading state ("Working out who can help…") → redirect to the issue page.

### 12.3 Student: dashboard & issue page
- Dashboard: cards for each issue with title, overall status, and a compact row of department chips with status ("Finance ✓ · Examinations ⏳").
- Issue page:
  - Title, submitted date, overall status.
  - **Progress tracker** showing the execution order as steps: each step lists its departments with status and `action_needed`. Blocked steps show "Waiting on Finance".
  - Message thread (student_and_staff only) with a reply box. If any task is `waiting_on_student`, show a prominent banner: "Finance needs something from you" with the latest message from that department.
  - Reopen button for resolved issues (within 7 days).

### 12.4 Staff: dashboard (`/staff`)
- Header: department name, counts (active / blocked / resolved this week).
- Tabs: Active (default), Blocked, Resolved.
- Task list rows: priority label, issue title, student name, status, "+N depts" indicator, deadline if any, age, "Newly unblocked" badge where applicable, "auto-classified" badge where applicable.
- Sorted by effective_priority desc. Polls every 5s.

### 12.5 Staff: task detail (`/staff/tasks/[id]`)
- Left/main column:
  - Issue title, priority label (with inheritance explanation if any), deadline.
  - **Our task**: dept_summary, action_needed, status controls (buttons for allowed transitions only), assign dropdown.
  - "View original message" button (with a small note that access is logged).
  - Message thread with a toggle between "Reply to student" and "Internal note (our department only)".
- Right column:
  - **All departments on this issue**: execution order with each department's status and action_needed, blocked-by relationships shown clearly ("Examinations → waiting on Finance").
  - Buttons: "Add department", "Edit dependencies", "Not ours".
  - Student info: name, roll no, programme, year.
  - Timeline: events list (human-readable).

### 12.6 Admin analytics (`/admin`)
Simple charts (use recharts): open issues by department; median time from task creation to resolution per department; count of tasks currently blocked and the departments most often blocking others (this surfaces bottlenecks); issues by urgency; fallback vs LLM classification ratio.

---

## 13. Seed data (`seed.py`)

Create a `make seed` / `python -m app.seed` command that resets the DB and inserts:
- the 12 departments
- 1 admin, 2 staff per department, 5 students (Indian names, realistic roll numbers and programmes, e.g. B.Tech CSE / AI&ML / ECE)
- all passwords `demo1234`
- ~12 sample issues in varied states, created directly (bypass the LLM so seeding is deterministic), including:
  - the scholarship → fees → exam chain with SCHOL resolved, FIN in progress, EXAM blocked
  - a single-department IT issue, resolved
  - a COUNS + ACAD issue with an internal note and a waiting_on_student task
  - a rejected task that was re-routed to DSW
  - an issue with a deadline tomorrow showing inherited priority
- backdated timestamps so analytics charts look realistic

---

## 14. Testing

Use pytest with an in-memory SQLite DB. Minimum tests:
- permissions: staff from an uninvolved dept gets 403; staff can't read other depts' summaries; students never receive dept_summary or internal notes; raw description endpoint writes an audit event
- dependencies: cycle detection rejects a cycle; unblocking fires only when all blockers resolve; execution order grouping is correct
- priority: inheritance propagates transitively up a chain
- lifecycle: issue auto-resolves when all tasks resolved/rejected; reopening a task reopens the issue; rejecting the last task creates a DSW task
- classifier: validation drops unknown codes and cyclic dependencies; fallback produces the FIN→EXAM dependency
- intake: whole pipeline with the LLM mocked

---

## 15. Build phases

Do these in order. At the end of each phase, run the app and the tests.

1. **Skeleton.** Backend + frontend scaffolding, DB models, Alembic migration, SQLite pragmas, auth with demo login switcher, seed script (departments + users only). ✅ Can log in as any persona and see an empty dashboard.
2. **Intake with fallback classifier.** Submit issue → fallback classification → issue + tasks + dependencies + events. Student dashboard and issue page (read-only). ✅ Submitting the scholarship/fees/exam example creates three tasks with the right blocking.
3. **Staff dashboard and lifecycle.** Task list, task detail, status transitions, unblocking, issue auto-resolution, permissions per §7. ✅ Resolving FIN unblocks EXAM and it appears on the EXAM dashboard within 5s; resolving everything shows "Resolved" to the student.
4. **LLM classifier.** llm_client, prompt, validation, per-department summaries, fallback on failure. ✅ With a key set, a mixed fees + anxiety message produces separate summaries with no mental-health detail in the FIN summary. With `LLM_PROVIDER=none`, everything still works.
5. **Priority.** Base + inheritance + aging, labels, explanation text. ✅ Seeded deadline-tomorrow issue shows the blocking FIN task as Critical with an explanation.
6. **Collaboration features.** Messages and internal notes, waiting_on_student flow, add department, edit dependencies, "Not ours", reopen, audited original-message view.
7. **Admin analytics + full seed data.**
8. **Polish.** Empty states, loading and error states, mobile layout, README with setup steps and a 3-minute demo script.

---

## 16. Demo script (put in README)

1. Log in as student Priya. Submit: "My scholarship hasn't been credited so I couldn't pay my fees, and now my name isn't on the exam list. My exam is on [2 days from today]."
2. Show the issue page: three departments, shown as a sequence Scholarships → Finance → Examinations, urgency high.
3. Switch to Examinations staff: the task is visible but blocked, "Waiting on Finance".
4. Switch to Finance staff: task shows Critical priority with "raised because Examinations is waiting on this". Show that Finance can see the task but not the other departments' private summaries.
5. Switch to Scholarships: resolve. Switch to Finance: now actionable; resolve.
6. Switch to Examinations: "Newly unblocked"; resolve.
7. Back to Priya: every department ticked, issue resolved.
8. Show admin analytics: bottleneck chart.

---

## 17. Conventions

- Type everything (Python type hints, TypeScript strict mode).
- Keep business logic in `services/`, never in routers or React components.
- Every state change goes through a service function that writes an event.
- No hard deletes anywhere.
- Read env from `.env`; provide `.env.example` for both apps. Never commit secrets.
- Keep dependencies minimal; don't add a library for something a few lines can do.
- Commit after each phase with a clear message.
