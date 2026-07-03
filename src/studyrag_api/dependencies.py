from __future__ import annotations

import uuid
from collections.abc import Iterator

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from studyrag_persistence.database import create_session_factory
from studyrag_persistence.models import ConversationRecord, CourseRecord, DocumentRecord, UserRecord

bearer_scheme = HTTPBearer(auto_error=False)


def get_session(request: Request) -> Iterator[Session]:
    session_factory = create_session_factory(request.app.state.engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> UserRecord:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")

    try:
        payload = jwt.decode(credentials.credentials, request.app.state.jwt_secret, algorithms=["HS256"])
        user_id = uuid.UUID(str(payload["sub"]))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid bearer token") from exc

    user = session.get(UserRecord, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")
    return user


def get_owned_course(session: Session, user: UserRecord, course_id: uuid.UUID) -> CourseRecord:
    course = session.get(CourseRecord, course_id)
    if course is None or course.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="course not found")
    return course


def get_owned_document(session: Session, user: UserRecord, document_id: uuid.UUID) -> DocumentRecord:
    document = session.get(DocumentRecord, document_id)
    if document is None or document.course.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document not found")
    return document


def get_owned_conversation(session: Session, user: UserRecord, conversation_id: uuid.UUID) -> ConversationRecord:
    conversation = session.get(ConversationRecord, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found")
    return conversation
