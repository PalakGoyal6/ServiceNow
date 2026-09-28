import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.app.db import Base, get_db
from backend.app.main import app
from backend.app.models import User, StudentProfile, Department, Issue, Task, TaskDependency
from backend.app.auth import get_password_hash, create_access_token

from sqlalchemy.pool import StaticPool

# In-memory SQLite with StaticPool for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_db(db_session):
    pwd = get_password_hash("demo1234")

    # Departments
    dept_fin = Department(code="FIN", name="Finance & Fees", description="fees and payments")
    dept_exam = Department(code="EXAM", name="Examinations", description="exams and admit cards")
    dept_schol = Department(code="SCHOL", name="Scholarships", description="scholarships")
    dept_couns = Department(code="COUNS", name="Counselling", description="wellbeing")
    dept_dsw = Department(code="DSW", name="Dean of Student Welfare", description="disputes")
    db_session.add_all([dept_fin, dept_exam, dept_schol, dept_couns, dept_dsw])
    db_session.flush()

    # Users
    admin = User(email="admin@test.edu", password_hash=pwd, full_name="Admin User", role="admin")
    student1 = User(email="priya@test.edu", password_hash=pwd, full_name="Priya Sharma", role="student")
    student2 = User(email="rohan@test.edu", password_hash=pwd, full_name="Rohan Verma", role="student")
    staff_fin = User(email="fin@test.edu", password_hash=pwd, full_name="Fin Staff", role="staff", department_id=dept_fin.id)
    staff_exam = User(email="exam@test.edu", password_hash=pwd, full_name="Exam Staff", role="staff", department_id=dept_exam.id)
    staff_schol = User(email="schol@test.edu", password_hash=pwd, full_name="Schol Staff", role="staff", department_id=dept_schol.id)
    staff_couns = User(email="couns@test.edu", password_hash=pwd, full_name="Couns Staff", role="staff", department_id=dept_couns.id)

    db_session.add_all([admin, student1, student2, staff_fin, staff_exam, staff_schol, staff_couns])
    db_session.flush()

    # Student profiles
    p1 = StudentProfile(user_id=student1.id, roll_no="2023BCSE042", programme="B.Tech CSE", year_of_study=3)
    p2 = StudentProfile(user_id=student2.id, roll_no="2024BAIML019", programme="B.Tech AI", year_of_study=2)
    db_session.add_all([p1, p2])
    db_session.commit()

    return {
        "admin": admin,
        "student1": student1,
        "student2": student2,
        "staff_fin": staff_fin,
        "staff_exam": staff_exam,
        "staff_schol": staff_schol,
        "staff_couns": staff_couns,
        "dept_fin": dept_fin,
        "dept_exam": dept_exam,
        "dept_schol": dept_schol,
        "dept_couns": dept_couns,
        "dept_dsw": dept_dsw,
    }


def auth_header_for(user: User) -> dict:
    token = create_access_token(data={"sub": user.id, "email": user.email, "role": user.role})
    return {"Authorization": f"Bearer {token}"}
