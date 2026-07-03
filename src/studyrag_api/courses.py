from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from studyrag_persistence.models import CourseRecord, UserRecord

from .dependencies import get_current_user, get_owned_course, get_session

router = APIRouter(prefix="/courses", tags=["courses"])


class CourseCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class CourseResponse(BaseModel):
    id: str
    name: str


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CourseResponse)
def create_course(
    payload: CourseCreateRequest,
    session: Session = Depends(get_session),
    current_user: UserRecord = Depends(get_current_user),
) -> CourseResponse:
    course = CourseRecord(user_id=current_user.id, name=payload.name.strip())
    session.add(course)
    session.commit()
    return CourseResponse(id=str(course.id), name=course.name)


@router.get("", response_model=list[CourseResponse])
def list_courses(
    session: Session = Depends(get_session),
    current_user: UserRecord = Depends(get_current_user),
) -> list[CourseResponse]:
    courses = session.scalars(
        select(CourseRecord).where(CourseRecord.user_id == current_user.id).order_by(CourseRecord.created_at)
    ).all()
    return [CourseResponse(id=str(course.id), name=course.name) for course in courses]


@router.get("/{course_id}", response_model=CourseResponse)
def get_course(
    course_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: UserRecord = Depends(get_current_user),
) -> CourseResponse:
    course = get_owned_course(session, current_user, course_id)
    return CourseResponse(id=str(course.id), name=course.name)
