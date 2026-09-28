import os
import yaml
from datetime import datetime, date, timedelta, timezone
from sqlalchemy.orm import Session
from backend.app.db import engine, Base, SessionLocal
from backend.app.models import (
    User,
    StudentProfile,
    Department,
    Issue,
    Task,
    TaskDependency,
    Message,
    Event,
)
from backend.app.auth import get_password_hash
from backend.app.services.priority import recompute_issue_priorities
from backend.app.services.dependencies import recompute_block_states


def seed_database():
    print("Resetting database schema...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    default_password_hash = get_password_hash("demo1234")
    now = datetime.now(timezone.utc)

    # 1. Seed Departments from YAML
    yaml_path = os.path.join(os.path.dirname(__file__), "departments.yaml")
    if os.path.exists(yaml_path):
        with open(yaml_path, "r", encoding="utf-8") as f:
            dept_data = yaml.safe_load(f).get("departments", [])
    else:
        dept_data = [
            {"code": "ACAD", "name": "Academic Affairs", "description": "course registration, attendance shortfall, academic appeals, credits"},
            {"code": "EXAM", "name": "Examinations", "description": "exam eligibility lists, admit cards, re-evaluation, results"},
            {"code": "FIN", "name": "Finance & Fees", "description": "fee payment, dues, refunds, fines, payment receipts"},
            {"code": "SCHOL", "name": "Scholarships & Financial Aid", "description": "scholarships, fee waivers, emergency financial support"},
            {"code": "HOSTEL", "name": "Hostel & Accommodation", "description": "room allocation, hostel issues, mess, accommodation"},
            {"code": "COUNS", "name": "Counselling & Wellbeing", "description": "stress, anxiety, emotional wellbeing, personal difficulties"},
            {"code": "HEALTH", "name": "Health Centre", "description": "illness, medical certificates, medical leave"},
            {"code": "DISAB", "name": "Disability Support", "description": "accommodations, accessibility, extra exam time"},
            {"code": "LIB", "name": "Library", "description": "library access, fines, resources"},
            {"code": "IT", "name": "IT Services", "description": "portal login, email, Wi-Fi, LMS access"},
            {"code": "PLACE", "name": "Training & Placement", "description": "internships, placement eligibility, company process issues"},
            {"code": "DSW", "name": "Dean of Student Welfare", "description": "harassment complaints, disputes, anything cross-cutting or unclear"}
        ]

    dept_map = {}
    for d in dept_data:
        dept = Department(code=d["code"], name=d["name"], description=d["description"])
        db.add(dept)
        db.flush()
        dept_map[d["code"]] = dept

    print(f"Created {len(dept_map)} departments.")

    # 2. Seed Admin
    admin_user = User(
        email="admin@university.edu",
        password_hash=default_password_hash,
        full_name="Dr. Rajesh Sharma (Dean of Admin)",
        role="admin",
        created_at=now - timedelta(days=60),
    )
    db.add(admin_user)
    db.flush()

    # 3. Seed Students
    students_info = [
        ("priya.sharma@student.edu", "Priya Sharma", "2023BCSE042", "B.Tech Computer Science", 3),
        ("rohan.verma@student.edu", "Rohan Verma", "2024BAIML019", "B.Tech AI & Data Science", 2),
        ("ananya.iyer@student.edu", "Ananya Iyer", "2022BECE088", "B.Tech Electronics & Comm", 4),
        ("kabir.patel@student.edu", "Kabir Patel", "2023BMECH014", "B.Tech Mechanical Engg", 3),
        ("sneha.rao@student.edu", "Sneha Rao", "2025BBCA005", "B.Sc Computing & IT", 1),
    ]

    student_users = []
    for email, name, roll, prog, yr in students_info:
        u = User(
            email=email,
            password_hash=default_password_hash,
            full_name=name,
            role="student",
            created_at=now - timedelta(days=90),
        )
        db.add(u)
        db.flush()
        profile = StudentProfile(user_id=u.id, roll_no=roll, programme=prog, year_of_study=yr)
        db.add(profile)
        student_users.append(u)

    print(f"Created {len(student_users)} student profiles.")

    # 4. Seed Staff Members (2 per department)
    staff_roster = [
        ("FIN", [("vikram.fin@university.edu", "Vikram Malhotra"), ("sunita.fin@university.edu", "Sunita Menon")]),
        ("EXAM", [("arvind.exam@university.edu", "Prof. Arvind Swaminathan"), ("meera.exam@university.edu", "Meera Nair")]),
        ("SCHOL", [("deepa.schol@university.edu", "Deepa Krishnan"), ("amit.schol@university.edu", "Amit Saxena")]),
        ("COUNS", [("aditi.couns@university.edu", "Dr. Aditi Sen"), ("maya.couns@university.edu", "Maya Pillai")]),
        ("ACAD", [("suresh.acad@university.edu", "Dr. Suresh Rao"), ("pooja.acad@university.edu", "Pooja Hegde")]),
        ("HOSTEL", [("sandeep.hostel@university.edu", "Col. Sandeep Kapoor"), ("anita.hostel@university.edu", "Anita Thomas")]),
        ("HEALTH", [("priya.health@university.edu", "Dr. Priya Nambiar"), ("ramesh.health@university.edu", "Ramesh Gupta")]),
        ("DISAB", [("geeta.disab@university.edu", "Geeta Bose"), ("karan.disab@university.edu", "Karan Joshi")]),
        ("LIB", [("mohan.lib@university.edu", "Mohan Das"), ("shweta.lib@university.edu", "Shweta Joshi")]),
        ("IT", [("tarun.it@university.edu", "Tarun Sethi"), ("neha.it@university.edu", "Neha Chawla")]),
        ("PLACE", [("gaurav.place@university.edu", "Gaurav Khanna"), ("ritu.place@university.edu", "Ritu Singhal")]),
        ("DSW", [("harish.dsw@university.edu", "Prof. Harish Chander"), ("shalini.dsw@university.edu", "Shalini Kaul")]),
    ]

    staff_map = {}
    for code, members in staff_roster:
        dept = dept_map[code]
        staff_map[code] = []
        for s_email, s_name in members:
            staff_u = User(
                email=s_email,
                password_hash=default_password_hash,
                full_name=s_name,
                role="staff",
                department_id=dept.id,
                created_at=now - timedelta(days=60),
            )
            db.add(staff_u)
            db.flush()
            staff_map[code].append(staff_u)

    print("Created 24 staff accounts across 12 departments.")

    # 5. Seed Sample Issues (§13)

    # Issue 1: The Scholarship -> Finance -> Exam Chain (Demo centerpiece)
    # Priya Sharma
    exam_deadline = date.today() + timedelta(days=2)
    iss1 = Issue(
        student_id=student_users[0].id,
        title="Scholarship delay causing fee arrears and exam de-listing",
        description="My scholarship hasn't been credited so I couldn't pay my semester fees, and now my name isn't on the exam list. My exam is on " + exam_deadline.strftime('%d %b %Y') + ".",
        urgency=4,
        deadline=exam_deadline,
        status="open",
        classification_source="llm",
        classification_raw='{"source": "demo_seed"}',
        created_at=now - timedelta(hours=8),
        updated_at=now - timedelta(hours=1),
    )
    db.add(iss1)
    db.flush()

    t_schol = Task(
        issue_id=iss1.id,
        department_id=dept_map["SCHOL"].id,
        status="resolved",
        dept_summary="Student merit-cum-means scholarship disbursement was pending state clearance. Grant sanctioned.",
        action_needed="Disburse pending scholarship funds to student fee account",
        base_priority=80,
        effective_priority=95,
        assigned_to=staff_map["SCHOL"][0].id,
        created_at=now - timedelta(hours=8),
        updated_at=now - timedelta(hours=2),
        resolved_at=now - timedelta(hours=2),
    )
    t_fin = Task(
        issue_id=iss1.id,
        department_id=dept_map["FIN"].id,
        status="in_progress",
        dept_summary="Fee payment pending scholarship credit. Clearance needed for examination eligibility.",
        action_needed="Verify scholarship receipt credit and clear exam financial hold",
        base_priority=80,
        effective_priority=95,
        assigned_to=staff_map["FIN"][0].id,
        created_at=now - timedelta(hours=8),
        updated_at=now - timedelta(hours=1),
        unblocked_at=now - timedelta(hours=2),
    )
    t_exam = Task(
        issue_id=iss1.id,
        department_id=dept_map["EXAM"].id,
        status="blocked",
        dept_summary="Student de-listed from upcoming exam hall ticket due to fee arrears flag.",
        action_needed="Generate admit card and add to hall seating list once fee clearance arrives",
        base_priority=95,
        effective_priority=95,
        assigned_to=staff_map["EXAM"][0].id,
        created_at=now - timedelta(hours=8),
        updated_at=now - timedelta(hours=8),
    )
    db.add_all([t_schol, t_fin, t_exam])
    db.flush()

    dep1 = TaskDependency(task_id=t_fin.id, blocked_by_task_id=t_schol.id, reason="Fee clearance requires scholarship disbursement", created_by="ai")
    dep2 = TaskDependency(task_id=t_exam.id, blocked_by_task_id=t_fin.id, reason="Exam hall ticket requires fee clearance", created_by="ai")
    db.add_all([dep1, dep2])
    db.flush()

    # Events & Messages for Issue 1
    m1 = Message(
        issue_id=iss1.id,
        task_id=t_schol.id,
        author_id=staff_map["SCHOL"][0].id,
        body="Scholarship sanction letter received. Fund transfer initiated to Finance ledger.",
        visibility="student_and_staff",
        created_at=now - timedelta(hours=2),
    )
    m2 = Message(
        issue_id=iss1.id,
        task_id=t_fin.id,
        author_id=staff_map["FIN"][0].id,
        body="We see the scholarship transfer credit. Verifying invoice balance now.",
        visibility="student_and_staff",
        created_at=now - timedelta(hours=1),
    )
    db.add_all([m1, m2])

    ev1 = Event(issue_id=iss1.id, type="issue_created", actor_id=student_users[0].id, payload='{"urgency": 4}', created_at=now - timedelta(hours=8))
    ev2 = Event(issue_id=iss1.id, type="task_unblocked", actor_id=staff_map["SCHOL"][0].id, task_id=t_fin.id, payload='{"department_code": "FIN"}', created_at=now - timedelta(hours=2))
    db.add_all([ev1, ev2])

    # Issue 2: Single-Department IT Issue (Resolved)
    # Rohan Verma
    iss2 = Issue(
        student_id=student_users[1].id,
        title="Campus Wi-Fi eduroam authentication failure in library",
        description="My campus Wi-Fi login keeps failing on eduroam in the central library since morning.",
        urgency=2,
        status="resolved",
        classification_source="fallback",
        created_at=now - timedelta(days=3),
        updated_at=now - timedelta(days=2),
        resolved_at=now - timedelta(days=2),
    )
    db.add(iss2)
    db.flush()

    t_it = Task(
        issue_id=iss2.id,
        department_id=dept_map["IT"].id,
        status="resolved",
        dept_summary="RADIUS certificate renewal required for user device MAC address. (auto-classified)",
        action_needed="Reset eduroam profile and re-register device certificate",
        base_priority=40,
        effective_priority=40,
        assigned_to=staff_map["IT"][0].id,
        created_at=now - timedelta(days=3),
        updated_at=now - timedelta(days=2),
        resolved_at=now - timedelta(days=2),
    )
    db.add(t_it)
    db.flush()

    # Issue 3: COUNS + ACAD with Internal Note & Waiting_on_student
    # Ananya Iyer
    iss3 = Issue(
        student_id=student_users[2].id,
        title="Attendance shortfall due to severe anxiety and missed labs",
        description="I've been feeling extremely overwhelmed and missed multiple lab sessions, attendance dropped below 70%.",
        urgency=3,
        status="open",
        classification_source="llm",
        created_at=now - timedelta(days=4),
        updated_at=now - timedelta(days=1),
    )
    db.add(iss3)
    db.flush()

    t_couns = Task(
        issue_id=iss3.id,
        department_id=dept_map["COUNS"].id,
        status="in_progress",
        dept_summary="Student reports overwhelming academic stress and panic attacks causing class absence.",
        action_needed="Conduct weekly counseling session and establish wellness plan",
        base_priority=60,
        effective_priority=60,
        assigned_to=staff_map["COUNS"][0].id,
        created_at=now - timedelta(days=4),
        updated_at=now - timedelta(days=2),
    )
    t_acad = Task(
        issue_id=iss3.id,
        department_id=dept_map["ACAD"].id,
        status="waiting_on_student",
        dept_summary="Attendance condonation requested for 4 missed laboratory sessions.",
        action_needed="Review medical leave application and counseling recommendation for condonation",
        base_priority=60,
        effective_priority=60,
        assigned_to=staff_map["ACAD"][0].id,
        created_at=now - timedelta(days=4),
        updated_at=now - timedelta(days=1),
    )
    db.add_all([t_couns, t_acad])
    db.flush()

    # Internal note in COUNS
    m_int = Message(
        issue_id=iss3.id,
        task_id=t_couns.id,
        author_id=staff_map["COUNS"][0].id,
        body="Internal Note: Student attended first intake session. Receptive to mindfulness exercises. Recommended formal condonation note to Academic Affairs.",
        visibility="department_only",
        created_at=now - timedelta(days=2),
    )
    m_acad = Message(
        issue_id=iss3.id,
        task_id=t_acad.id,
        author_id=staff_map["ACAD"][0].id,
        body="Dear Ananya, please upload your leave application form and medical prescription to process the attendance condonation.",
        visibility="student_and_staff",
        created_at=now - timedelta(days=1),
    )
    db.add_all([m_int, m_acad])

    # Issue 4: Rejected Task Rerouted to DSW
    # Kabir Patel
    iss4 = Issue(
        student_id=student_users[3].id,
        title="Dispute over unauthorized canteen fine deduction",
        description="Dispute with hostel canteen vendor over unauthorized fee deduction and aggressive behavior by vendor staff.",
        urgency=2,
        status="open",
        classification_source="llm",
        created_at=now - timedelta(days=5),
        updated_at=now - timedelta(days=3),
    )
    db.add(iss4)
    db.flush()

    t_hostel_rej = Task(
        issue_id=iss4.id,
        department_id=dept_map["HOSTEL"].id,
        status="rejected",
        dept_summary="Hostel maintenance does not oversee private catering vendor disciplinary contracts.",
        action_needed="Inspect hostel mess facilities",
        base_priority=40,
        effective_priority=40,
        created_at=now - timedelta(days=5),
        updated_at=now - timedelta(days=3),
    )
    t_dsw = Task(
        issue_id=iss4.id,
        department_id=dept_map["DSW"].id,
        status="pending",
        dept_summary="Re-routed to DSW because previous department marked not relevant. Vendor dispute resolution required.",
        action_needed="Re-route: previous department marked not relevant",
        base_priority=40,
        effective_priority=40,
        assigned_to=staff_map["DSW"][0].id,
        created_at=now - timedelta(days=3),
        updated_at=now - timedelta(days=3),
    )
    db.add_all([t_hostel_rej, t_dsw])
    db.flush()

    # Issue 5: Deadline Tomorrow Showing Critical Inherited Priority
    # Sneha Rao
    tomorrow = date.today() + timedelta(days=1)
    iss5 = Issue(
        student_id=student_users[4].id,
        title="Urgent transcript verification for internship joining tomorrow",
        description="Urgent: Grade card and official transcript missing for final internship background check tomorrow morning.",
        urgency=4,
        deadline=tomorrow,
        status="open",
        classification_source="llm",
        created_at=now - timedelta(hours=6),
        updated_at=now - timedelta(hours=6),
    )
    db.add(iss5)
    db.flush()

    t5_fin = Task(
        issue_id=iss5.id,
        department_id=dept_map["FIN"].id,
        status="in_progress",
        dept_summary="Clear transcript fee invoice of Rs. 250.",
        action_needed="Process transcript processing receipt",
        base_priority=80,
        effective_priority=95,
        assigned_to=staff_map["FIN"][1].id,
        created_at=now - timedelta(hours=6),
        updated_at=now - timedelta(hours=6),
    )
    t5_exam = Task(
        issue_id=iss5.id,
        department_id=dept_map["EXAM"].id,
        status="blocked",
        dept_summary="Issue digitally signed official transcript for placement onboarding.",
        action_needed="Generate and stamp official academic transcript",
        base_priority=95,
        effective_priority=95,
        assigned_to=staff_map["EXAM"][1].id,
        created_at=now - timedelta(hours=6),
        updated_at=now - timedelta(hours=6),
    )
    db.add_all([t5_fin, t5_exam])
    db.flush()

    dep5 = TaskDependency(task_id=t5_exam.id, blocked_by_task_id=t5_fin.id, reason="Official transcript release requires payment verification", created_by="ai")
    db.add(dep5)

    # Issues 6 to 12: Additional historical and varied issues for analytics charts
    sample_issues_data = [
        ("Disability wheelchair ramp access request at Block C", "DISAB", student_users[0], 2, "resolved", timedelta(days=12), timedelta(days=10)),
        ("Library overdue fine appeal due to medical hospitalization", "LIB", student_users[1], 2, "resolved", timedelta(days=10), timedelta(days=9)),
        ("Placement cell NOC requirement for off-campus summer research", "PLACE", student_users[2], 3, "resolved", timedelta(days=8), timedelta(days=7)),
        ("Health centre medical certificate approval for missed mid-term", "HEALTH", student_users[3], 3, "resolved", timedelta(days=6), timedelta(days=5)),
        ("Hostel room water seepage and geyser malfunction", "HOSTEL", student_users[4], 2, "in_progress", timedelta(days=4), None),
        ("Academic backlog credit registration conflict in elective course", "ACAD", student_users[0], 3, "pending", timedelta(days=2), None),
        ("Degree certificate name spelling correction appeal", "EXAM", student_users[1], 1, "pending", timedelta(days=1), None),
    ]

    for title, dept_code, student_user, urgency_val, task_stat, created_delta, resolved_delta in sample_issues_data:
        iss_stat = "resolved" if task_stat == "resolved" else "open"
        res_date = now - resolved_delta if resolved_delta else None
        
        hist_iss = Issue(
            student_id=student_user.id,
            title=title,
            description=f"Detailed request: {title}. Submitted via student portal.",
            urgency=urgency_val,
            status=iss_stat,
            classification_source="llm" if urgency_val > 1 else "fallback",
            created_at=now - created_delta,
            updated_at=res_date or (now - created_delta),
            resolved_at=res_date,
        )
        db.add(hist_iss)
        db.flush()

        hist_task = Task(
            issue_id=hist_iss.id,
            department_id=dept_map[dept_code].id,
            status=task_stat,
            dept_summary=f"Handled by {dept_map[dept_code].name}: {title}",
            action_needed=f"Process {title}",
            base_priority=urgency_val * 20,
            effective_priority=urgency_val * 20,
            assigned_to=staff_map[dept_code][0].id,
            created_at=now - created_delta,
            updated_at=res_date or (now - created_delta),
            resolved_at=res_date,
        )
        db.add(hist_task)

    db.commit()

    # Recompute priorities and block states on all issues
    all_issues = db.query(Issue).all()
    for iss in all_issues:
        recompute_block_states(db, iss.id)
        recompute_issue_priorities(db, iss.id)
    db.commit()

    print(f"Database successfully seeded with {len(all_issues)} issues, tasks, dependencies, messages, and events.")
    db.close()


if __name__ == "__main__":
    seed_database()
