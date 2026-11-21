"""Authentication endpoints."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.exceptions import AuthError, ConflictError
from backend.models import User
from backend.schemas import LoginRequest, RegisterRequest, TokenOut, UserOut
from backend.security import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _token_response(request: Request, user: User) -> TokenOut:
    settings = request.app.state.settings
    token = create_access_token(user.id, settings.secret_key, settings.token_ttl_minutes)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenOut, status_code=201)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == payload.email)) is not None:
        raise ConflictError("An account with this email already exists")
    settings = request.app.state.settings
    user = User(
        name=payload.name, email=payload.email,
        password_hash=hash_password(payload.password, settings.password_iterations),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token_response(request, user)


@router.post("/login", response_model=TokenOut)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AuthError("Incorrect email or password")
    return _token_response(request, user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
