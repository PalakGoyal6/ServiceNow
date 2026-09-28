import pytest
from backend.app.schemas import Classification, DeptAssignment, DependencySchema
from backend.app.services.classifier import validate_and_normalize, fallback_classify


def test_validation_drops_unknown_codes_and_cycles():
    available = {"FIN", "EXAM", "SCHOL", "DSW"}
    raw = Classification(
        title="Valid title that is quite normal and fits the length constraint perfectly",
        urgency=10,  # Needs clamping to 4
        urgency_reason="Testing",
        departments=[
            DeptAssignment(department_code="FIN", dept_summary="Fin text", action_needed="Fin act"),
            DeptAssignment(department_code="UNKNOWN_DEPT", dept_summary="Bad dept", action_needed="Bad act"),
            DeptAssignment(department_code="EXAM", dept_summary="Exam text", action_needed="Exam act"),
        ],
        dependencies=[
            DependencySchema(blocked_department_code="EXAM", blocked_by_department_code="FIN", reason="Dep 1"),
            DependencySchema(blocked_department_code="FIN", blocked_by_department_code="EXAM", reason="Creates cycle"),
            DependencySchema(blocked_department_code="EXAM", blocked_by_department_code="UNKNOWN_DEPT", reason="Nonexistent"),
        ]
    )

    normalized = validate_and_normalize(raw, available)
    codes = [d.department_code for d in normalized.departments]
    assert "FIN" in codes
    assert "EXAM" in codes
    assert "UNKNOWN_DEPT" not in codes
    assert normalized.urgency == 4
    # Only the first valid non-cyclic dependency should be kept
    assert len(normalized.dependencies) == 1
    assert normalized.dependencies[0].blocked_department_code == "EXAM"
    assert normalized.dependencies[0].blocked_by_department_code == "FIN"


def test_fallback_classifier_keyword_mapping(seeded_db, db_session):
    departments = db_session.query(seeded_db["dept_fin"].__class__).all()
    text = "I have fee dues and cannot download my exam admit card."
    result = fallback_classify(text, departments)

    codes = [d.department_code for d in result.departments]
    assert "FIN" in codes
    assert "EXAM" in codes
    assert len(result.dependencies) == 1
    assert result.dependencies[0].blocked_department_code == "EXAM"
    assert result.dependencies[0].blocked_by_department_code == "FIN"
