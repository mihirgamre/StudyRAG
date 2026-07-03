from __future__ import annotations

import uuid
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from passlib.hash import pbkdf2_sha256
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from studyrag_persistence.models import UserRecord

from .dependencies import get_session

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def hash_password(password: str) -> str:
    return pbkdf2_sha256.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pbkdf2_sha256.verify(password, hashed_password)


def create_access_token(request: Request, user_id: uuid.UUID) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=8)
    payload = {"sub": str(user_id), "exp": expires_at}
    return jwt.encode(payload, request.app.state.jwt_secret, algorithm="HS256")


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=AuthResponse)
def register(payload: AuthRequest, request: Request, session: Session = Depends(get_session)) -> AuthResponse:
    existing_user = session.scalar(select(UserRecord).where(UserRecord.email == payload.email.lower()))
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already registered")

    user = UserRecord(email=payload.email.lower(), hashed_password=hash_password(payload.password))
    session.add(user)
    session.flush()
    if os.getenv("STUDYRAG_ATTACH_SAMPLE_COURSE_ON_REGISTER", "false").lower() in {"1", "true", "yes"}:
        from studyrag_deploy.seed_sample_course import seed_sample_course_for_user

        seed_sample_course_for_user(session, user)
    session.commit()
    return AuthResponse(access_token=create_access_token(request, user.id))


@router.post("/login", response_model=AuthResponse)
def login(payload: AuthRequest, request: Request, session: Session = Depends(get_session)) -> AuthResponse:
    user = session.scalar(select(UserRecord).where(UserRecord.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid email or password")

    return AuthResponse(access_token=create_access_token(request, user.id))


@router.post("/demo", response_model=AuthResponse)
def demo_login(request: Request, session: Session = Depends(get_session)) -> AuthResponse:
    if os.getenv("STUDYRAG_DEMO_ENABLED", "false").lower() not in {"1", "true", "yes"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="demo login is not enabled")

    email = os.getenv("STUDYRAG_DEMO_USER_EMAIL", "demo@studyrag.local").lower()
    user = session.scalar(select(UserRecord).where(UserRecord.email == email))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="sample course has not been seeded",
        )
    return AuthResponse(access_token=create_access_token(request, user.id))
