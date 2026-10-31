from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_current_user, verify_password
from app.database.session import get_db
from app.models import User
from app.schemas.api import LoginRequest, LoginResponse, UserOut
from app.services import audit_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


def user_out(u: User) -> UserOut:
    return UserOut(id=u.id, email=u.email, full_name=u.full_name, role=u.role, department=u.department,
                   organization=u.organization.name)


@router.post("/login", response_model=LoginResponse, responses={401: {"description": "Invalid credentials"}})
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(func.lower(User.email) == body.email.strip().lower())).scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash) or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    audit_service.append_event(db, event_type="USER_LOGIN", description=f"{user.full_name} signed in.",
                               actor=user.full_name, user_id=user.id)
    return LoginResponse(access_token=create_access_token(user), user=user_out(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user_out(user)
