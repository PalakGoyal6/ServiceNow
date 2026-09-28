# Architecture & Design Decisions (DECISIONS.md)

This document records the architectural decisions, trade-offs, and design rationales made during the development of the **Student Support Triage & Joined-Up Case Management** system.

---

## 1. Single Intake Pipeline & Privacy Architecture
- **Problem:** Students previously repeated their story across 12 isolated departments, often sharing sensitive personal/medical details with non-relevant administrative staff.
- **Decision:** The student submits their issue once. The AI classifier splits the issue into discrete per-department tasks and generates **isolated `dept_summary` summaries**.
- **Privacy Rule:** A department only receives information necessary to execute its specific action (e.g. Finance sees fee arrears without mental health details; Counselling sees wellbeing distress without invoice ledgers).
- **Data Minimization:** By default, staff cannot see the student's raw text. A separate "View Original Message" endpoint is protected and automatically records an append-only `raw_description_viewed` audit event.

---

## 2. Priority Inheritance Engine
- **Problem:** When a student faces an imminent exam or graduation deadline, the downstream department (Examinations) is critical, but the blocking upstream department (Finance or Scholarships) might only treat fee processing as routine priority, causing deadlocks.
- **Decision:** We implemented **transitive priority inheritance**. If task $B$ is blocked by task $A$, task $A$'s effective priority becomes $\max(\text{base\_priority}(A), \text{effective\_priority}(B))$.
- **Visual Feedback:** Staff dashboards clearly flag inherited priorities with visual badges and descriptive explanations (e.g., *"Priority raised because Examinations is waiting on this (exam in 2 days)"*).

---

## 3. Dependency Graph & Cycle Prevention
- **Problem:** Mutual blockers can cause cyclic stalemates where no department can start.
- **Decision:** Dependency graphs are strictly managed with cycle detection using depth-first search (DFS). Any attempted dependency edge that creates a cycle is rejected with an explanatory HTTP 400 error.
- **Sequential Stages:** We compute topological sorting levels, rendering parallel tasks within the same stage and sequential stages with clear "Waiting on X" indicators for students and staff.

---

## 4. Provider-Agnostic LLM with Deterministic Fallback
- **Problem:** LLM rate limits, network outages, or missing API keys during a live demo could disrupt case submission.
- **Decision:** We implemented a unified LLM interface supporting Anthropic, OpenAI, and Gemini with JSON schema validation and single-retry feedback. If `LLM_PROVIDER=none` or an error occurs, the system seamlessly uses a keyword and rule-based fallback classifier with zero disruption.

---

## 5. Live State Synchronization
- **Decision:** Implemented 5-second polling via SWR (`refreshInterval: 5000`) on both student and staff dashboards instead of WebSockets. This eliminates stateful connection dropping, proxy issues, and reconnection logic while keeping UI updates near instantaneous.

---

## 6. Admin Permissions Scope
- **Decision:** For the hackathon demo, the Administrator persona has global oversight across analytics, bottlenecks, and cross-department workloads. In a future production deployment, admin views can be partitioned by college faculty and student grievance categories.
