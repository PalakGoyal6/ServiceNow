from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.db import get_db
from backend.app.models import User, Department
from backend.app.schemas import LoginRequest, TokenResponse, UserSchema, DemoUserResponse
from backend.app.auth import verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(login_req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_req.email.strip().lower()).first()
    if not user or not verify_password(login_req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.id, "email": user.email, "role": user.role})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }


@router.get("/me", response_model=UserSchema)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/demo-users", response_model=List[DemoUserResponse])
def get_demo_users(db: Session = Depends(get_db)):
    if not settings.DEMO_MODE:
        return []

    users = db.query(User).all()
    demo_list = []
    
    # Sort order: Students first, then staff by dept code, then admin
    def sort_key(u: User):
        if u.role == "student":
            return (0, u.full_name)
        elif u.role == "staff":
            code = u.department.code if u.department else "ZZ"
            return (1, code, u.full_name)
        else:
            return (2, u.full_name)

    sorted_users = sorted(users, key=sort_key)

    for u in sorted_users:
        dept_code = u.department.code if u.department else None
        dept_name = u.department.name if u.department else None
        desc = ""
        if u.role == "student" and u.student_profile:
            desc = f"{u.student_profile.roll_no} • {u.student_profile.programme} (Yr {u.student_profile.year_of_study})"
        elif u.role == "staff" and u.department:
            desc = f"Staff • {u.department.name} ({u.department.code})"
        elif u.role == "admin":
            desc = "System Administrator"

        demo_list.append(DemoUserResponse(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            department_id=u.department_id,
            department_code=dept_code,
            department_name=dept_name,
            description=desc,
        ))
    return demo_list
