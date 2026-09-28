import os
import re
from datetime import date, datetime, timedelta
from typing import List, Tuple, Optional, Set
from backend.app.models import Department
from backend.app.schemas import Classification, DeptAssignment, DependencySchema
from backend.app.services.llm_client import complete_json, LLMClientError

VALID_DEPT_CODES = {
    "ACAD", "EXAM", "FIN", "SCHOL", "HOSTEL", "COUNS",
    "HEALTH", "DISAB", "LIB", "IT", "PLACE", "DSW"
}

KEYWORDS = {
    "FIN": ["fee", "fees", "payment", "due", "dues", "refund", "refunds", "fine", "fines", "receipt", "challan", "tuition"],
    "EXAM": ["exam", "exams", "admit card", "hall ticket", "eligibility list", "re-evaluation", "grade", "marksheet", "test"],
    "SCHOL": ["scholarship", "scholarships", "fee waiver", "stipend", "financial aid", "grant", "fellowship"],
    "HOSTEL": ["hostel", "room", "mess", "accommodation", "warden", "block", "hostel fee"],
    "COUNS": ["stress", "anxious", "anxiety", "overwhelmed", "depressed", "depression", "mental", "emotional", "counseling", "counselling", "wellbeing"],
    "HEALTH": ["medical", "health", "doctor", "hospital", "prescription", "sick", "illness", "medical leave", "medical certificate"],
    "DISAB": ["disability", "accommodations", "extra time", "accessible", "wheelchair", "scribe", "special needs"],
    "LIB": ["library", "books", "book fine", "journal", "borrowing", "catalogue", "borrow"],
    "IT": ["wifi", "wi-fi", "portal", "lms", "login", "password", "email", "internet", "moodle", "canvas", "erp"],
    "PLACE": ["placement", "internship", "interview", "recruiter", "company", "offer", "job", "career"],
    "ACAD": ["attendance", "course registration", "credits", "backlog", "academic appeal", "syllabus", "shortfall", "classes"],
    "DSW": ["harassment", "ragging", "dispute", "complaint", "welfare", "unfair", "discipline"]
}

DEPT_DEFAULT_ACTIONS = {
    "FIN": "Review student fee account and process clearance",
    "EXAM": "Verify exam eligibility and issue hall ticket/admit card",
    "SCHOL": "Check status of scholarship disbursement and disburse funds",
    "HOSTEL": "Inspect hostel issue and allocate/fix accommodation",
    "COUNS": "Schedule wellbeing support and guidance session",
    "HEALTH": "Review medical records and issue medical certificate clearance",
    "DISAB": "Configure requested accessibility accommodations",
    "LIB": "Clear library record and resolve resource access",
    "IT": "Resolve IT/portal login/network connectivity issue",
    "PLACE": "Update placement eligibility and coordinate with recruitment cell",
    "ACAD": "Review academic/attendance records and process appeal",
    "DSW": "Review cross-cutting student grievance and coordinate support",
}


def load_prompt_template() -> str:
    prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "classify.md")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Classify student support issues into departments."


def validate_and_normalize(classification: Classification, available_codes: Set[str]) -> Classification:
    """
    Normalizes classifier output per §6.5:
    - Drops unknown department codes
    - Deduplicates departments
    - Clamps urgency 1-4
    - Drops dependencies referencing absent departments or creating cycles
    - Falls back to DSW if no departments remain
    - Clamps title <= 80 chars
    """
    # 1. Deduplicate and filter unknown codes
    seen_codes = set()
    valid_depts: List[DeptAssignment] = []
    for d in classification.departments:
        code = d.department_code.strip().upper()
        if code in available_codes and code not in seen_codes:
            seen_codes.add(code)
            valid_depts.append(DeptAssignment(
                department_code=code,
                dept_summary=d.dept_summary.strip(),
                action_needed=d.action_needed.strip(),
                confidence=d.confidence
            ))

    # If zero departments, assign DSW
    if not valid_depts:
        valid_depts.append(DeptAssignment(
            department_code="DSW",
            dept_summary="Issue requires review and routing by student welfare.",
            action_needed="Review and route manually",
            confidence=0.5
        ))
        seen_codes.add("DSW")

    # 2. Filter dependencies
    valid_deps: List[DependencySchema] = []
    # Build simple graph for cycle check
    adj = {code: [] for code in seen_codes}

    for dep in classification.dependencies:
        b_code = dep.blocked_department_code.strip().upper()
        by_code = dep.blocked_by_department_code.strip().upper()
        
        # Must be in assigned departments and not self-dependency
        if b_code in seen_codes and by_code in seen_codes and b_code != by_code:
            # Check cycle in graph: does by_code reach b_code?
            # Edge by_code -> b_code
            visited = set()
            queue = [b_code]
            has_cycle = False
            while queue:
                curr = queue.pop(0)
                if curr == by_code:
                    has_cycle = True
                    break
                if curr not in visited:
                    visited.add(curr)
                    queue.extend(adj.get(curr, []))

            if not has_cycle:
                adj[by_code].append(b_code)
                valid_deps.append(DependencySchema(
                    blocked_department_code=b_code,
                    blocked_by_department_code=by_code,
                    reason=dep.reason.strip()
                ))

    # 3. Clamp urgency
    urgency = max(1, min(4, classification.urgency))

    # 4. Clamp title
    title = classification.title.strip()
    if len(title) > 80:
        title = title[:77] + "..."

    return Classification(
        title=title or "Student Support Request",
        urgency=urgency,
        urgency_reason=classification.urgency_reason or "Classified based on request urgency",
        deadline=classification.deadline,
        departments=valid_depts,
        dependencies=valid_deps
    )


def fallback_classify(text: str, departments: List[Department], optional_deadline: Optional[date] = None) -> Classification:
    """
    Deterministic rule/keyword-based classifier (§6.6).
    """
    text_lower = text.lower()
    matched_codes: List[str] = []

    for code, kws in KEYWORDS.items():
        for kw in kws:
            if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
                if code not in matched_codes:
                    matched_codes.append(code)
                break

    if not matched_codes:
        matched_codes = ["DSW"]

    # Limit to max 4 departments
    matched_codes = matched_codes[:4]

    # Detect urgency
    urgency = 2
    urgency_reason = "Standard priority"
    if any(w in text_lower for w in ["tomorrow", "today", "urgent", "immediately", "emergency", "within 24 hours", "asap"]):
        urgency = 4
        urgency_reason = "Keywords indicate immediate urgency"
    elif any(w in text_lower for w in ["this week", "next week", "soon", "approaching"]):
        urgency = 3
        urgency_reason = "Keywords indicate time sensitivity within the week"

    # Deadline handling
    extracted_deadline = optional_deadline
    if not extracted_deadline:
        if "tomorrow" in text_lower:
            extracted_deadline = date.today() + timedelta(days=1)
        elif "today" in text_lower:
            extracted_deadline = date.today()

    dept_assignments = []
    short_summary = text[:180].strip().replace("\n", " ") + " (auto-classified)"

    for code in matched_codes:
        action = DEPT_DEFAULT_ACTIONS.get(code, "Review and take appropriate action")
        dept_assignments.append(DeptAssignment(
            department_code=code,
            dept_summary=short_summary,
            action_needed=action,
            confidence=0.8
        ))

    # Dependencies (§6.6 rules)
    dependencies = []
    if "SCHOL" in matched_codes and "FIN" in matched_codes:
        dependencies.append(DependencySchema(
            blocked_department_code="FIN",
            blocked_by_department_code="SCHOL",
            reason="Fee payment clearance requires scholarship disbursement"
        ))
    if "FIN" in matched_codes and "EXAM" in matched_codes:
        dependencies.append(DependencySchema(
            blocked_department_code="EXAM",
            blocked_by_department_code="FIN",
            reason="Exam eligibility requires fee clearance"
        ))
    if "ACAD" in matched_codes and "EXAM" in matched_codes and "attendance" in text_lower:
        dependencies.append(DependencySchema(
            blocked_department_code="EXAM",
            blocked_by_department_code="ACAD",
            reason="Exam eligibility requires attendance clearance"
        ))

    # Short title from first few words
    words = text.strip().split()
    title = " ".join(words[:7])
    if len(title) > 60:
        title = title[:57] + "..."

    return Classification(
        title=title or "Student Support Request",
        urgency=urgency,
        urgency_reason=urgency_reason,
        deadline=extracted_deadline,
        departments=dept_assignments,
        dependencies=dependencies
    )


def classify_issue(
    text: str,
    departments: List[Department],
    optional_deadline: Optional[date] = None,
) -> Tuple[Classification, str]:
    """
    Attempts LLM classification with prompt formatting.
    Falls back to keyword classifier on any error or when LLM_PROVIDER=none.
    Returns (Classification, source: 'llm' | 'fallback').
    """
    available_codes = {d.code for d in departments} or VALID_DEPT_CODES
    prompt_template = load_prompt_template()
    system_prompt = prompt_template.replace("{today_date}", date.today().isoformat())

    user_prompt = f"Student description:\n{text}"
    if optional_deadline:
        user_prompt += f"\nStudent specified deadline: {optional_deadline.isoformat()}"

    try:
        raw_classification = complete_json(system_prompt, user_prompt, Classification)
        if optional_deadline and not raw_classification.deadline:
            raw_classification.deadline = optional_deadline
        normalized = validate_and_normalize(raw_classification, available_codes)
        return normalized, "llm"
    except Exception as e:
        fallback = fallback_classify(text, departments, optional_deadline)
        normalized = validate_and_normalize(fallback, available_codes)
        return normalized, "fallback"
