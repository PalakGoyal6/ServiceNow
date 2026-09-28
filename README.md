# Student Support Triage & Joined-Up Case Management

A modern, multi-department triage and case management platform for universities. It enables students to describe complex academic, financial, wellbeing, or administrative problems **once in their own words**, automatically coordinates across **12 university support departments**, establishes prerequisite workflow dependencies, and prevents cross-department deadlocks using **priority inheritance**.

---

## 🌟 Key Features

1. **One-Stop Intake & Multi-Department Triage:**
   - Single natural language submission without requiring students to know university bureaucracy.
   - LLM classifier with keyword fallback splits problems into discrete departmental tasks and establishes sequential execution stages.
2. **Privacy-Preserving Summaries (Data Minimization):**
   - Each department sees only the details necessary to act (e.g. Finance sees fee arrears without mental-health notes).
   - Unredacted student text is shielded behind an explicit, audited view endpoint.
3. **Dynamic Priority Inheritance:**
   - Tasks waiting on prerequisite departments inherit higher urgency and impending deadlines from downstream tasks (e.g. Finance processing fee clearance for an exam occurring in 2 days becomes **Critical**).
4. **Automated Unblocking & Cycle Prevention:**
   - Blocked tasks automatically transition to pending as soon as prerequisite departments resolve their tasks.
   - Dependency graph enforces acyclic graphs (DFS cycle detection).
5. **Real-Time Synchronized Dashboards:**
   - Live 5-second polling (SWR) across student and staff dashboards without WebSocket dropouts.
6. **Executive Bottleneck Analytics:**
   - Recharts visual metrics identifying friction points, median SLA resolution times, and departments most often blocking others.
7. **One-Click Demo Persona Switcher:**
   - Instant switching between students (Priya, Rohan, Ananya), staff from 12 departments (FIN, EXAM, SCHOL, COUNS, ACAD, IT, HOSTEL, DSW), and Administrator.

---

## 🛠 Tech Stack

- **Frontend:** Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, SWR, Recharts, Lucide Icons.
- **Backend:** FastAPI, Python 3.11+, Pydantic v2, SQLAlchemy 2.0 ORM.
- **Database:** SQLite with WAL mode (`PRAGMA journal_mode = WAL`) and foreign key enforcement (`PRAGMA foreign_keys = ON`).
- **Authentication:** JWT with bcrypt password hashing and seeded demo credentials.

---

## 🚀 Quick Start Guide

### 1. Backend Setup
```bash
# Navigate to backend and install dependencies
pip install -r backend/requirements.txt

# Seed departments, demo users, and realistic sample issues
python -m backend.app.seed

# Run the FastAPI server (port 8000)
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Setup
```bash
# Navigate to frontend and install dependencies
cd frontend
npm install

# Start the Next.js development server (port 3000)
npm run dev
```
Open **[http://localhost:3000](http://localhost:3000)** in your browser.

---

## 🎬 3-Minute Demo Script

Follow these steps to demonstrate the end-to-end multi-department workflow during a live presentation:

1. **Sign in as Student Priya:**
   - Navigate to `/login` and click **Priya Sharma** (one-click login).
   - Click **Submit Issue** (`/student/new`) and click the quick demo preset or type:
     > *"My scholarship hasn't been credited so I couldn't pay my fees, and now my name isn't on the exam list. My exam is in two days."*
   - Click **Submit Request**. Notice the AI triage animation.
2. **Review Student Case Tracker:**
   - View the generated issue page: Three departments are identified in sequential stages:
     - **Step 1:** Scholarships & Financial Aid (SCHOL)
     - **Step 2:** Finance & Fees (FIN)
     - **Step 3:** Examinations (EXAM)
3. **Switch to Examinations Staff:**
   - Click **Switch Persona** in the top navbar and choose **Examinations (EXAM)**.
   - Notice the task appears in the queue as **Blocked** (`Waiting on Finance`).
4. **Switch to Finance Staff:**
   - Switch persona to **Finance (FIN)**.
   - Notice the task priority is elevated to **Critical** with the note: *"Priority raised because Examinations is waiting on this (deadline in 2 days)"*.
   - Point out that Finance sees only the financial details in its summary, preserving student privacy.
   - Click **Mark Resolved (Done)**.
5. **Observe Automatic Unblocking:**
   - Switch back to **Examinations (EXAM)**.
   - Notice the task has automatically unblocked to **Pending / In Action** with a **"Newly Unblocked"** badge.
   - Click **Start Work** and then **Mark Resolved (Done)**.
6. **Confirm Student Resolution:**
   - Switch back to **Priya Sharma**.
   - Notice all stages are now completed with green checkmarks and the overall case is marked **Resolved**.
7. **View Admin Bottleneck Intelligence:**
   - Switch persona to **Administrator** (`/admin`).
   - Highlight the **Department Bottlenecks** chart, **Median Resolution SLA** chart, and **Caseload Distribution**.

---

## 🧪 Running Automated Tests

Run the complete test suite (17 comprehensive unit & integration tests covering permissions, cycle detection, priority inheritance, lifecycle state machine, and fallback classifier):

```bash
pytest backend/tests
```
