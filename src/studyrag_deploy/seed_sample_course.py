from __future__ import annotations

import os

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from eval.course_material import COURSE_NAME, DOCUMENT_FILENAME, sample_course_pages
from studyrag_core import HashingEmbeddingModel, SemanticChunker
from studyrag_persistence import persist_document_chunks
from studyrag_persistence.database import create_engine_from_url, create_session_factory
from studyrag_persistence.models import ChunkRecord, CourseRecord, DocumentRecord, UserRecord


DEFAULT_DEMO_EMAIL = "demo@studyrag.local"


def seed_sample_course(
    engine: Engine | None = None,
    *,
    demo_email: str | None = None,
    course_name: str | None = None,
    storage_url: str | None = None,
) -> str:
    owns_engine = engine is None
    engine = engine or create_engine_from_url()
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as session:
            course = _seed(session, demo_email=demo_email, course_name=course_name, storage_url=storage_url)
            return str(course.id)
    finally:
        if owns_engine:
            engine.dispose()


def _seed(
    session: Session,
    *,
    demo_email: str | None,
    course_name: str | None,
    storage_url: str | None,
) -> CourseRecord:
    email = (demo_email or os.getenv("STUDYRAG_DEMO_USER_EMAIL") or DEFAULT_DEMO_EMAIL).lower()
    user = session.scalar(select(UserRecord).where(UserRecord.email == email))
    if user is None:
        user = UserRecord(email=email, hashed_password="demo-login-only")
        session.add(user)
        session.flush()
    return seed_sample_course_for_user(session, user, course_name=course_name, storage_url=storage_url)


def seed_sample_course_for_user(
    session: Session,
    user: UserRecord,
    *,
    course_name: str | None = None,
    storage_url: str | None = None,
) -> CourseRecord:
    name = course_name or os.getenv("STUDYRAG_SAMPLE_COURSE_NAME") or COURSE_NAME
    document_url = (
        storage_url
        or os.getenv("STUDYRAG_SAMPLE_COURSE_STORAGE_URL")
        or "local://eval/study-rag-sample-course-notes.txt"
    )

    course = session.scalar(select(CourseRecord).where(CourseRecord.user_id == user.id, CourseRecord.name == name))
    if course is None:
        course = CourseRecord(user_id=user.id, name=name)
        session.add(course)
        session.flush()

    document = session.scalar(
        select(DocumentRecord).where(
            DocumentRecord.course_id == course.id,
            DocumentRecord.filename == DOCUMENT_FILENAME,
        )
    )
    if document is None:
        document = DocumentRecord(
            course_id=course.id,
            filename=DOCUMENT_FILENAME,
            source_type="txt",
            storage_url=document_url,
            status="pending",
        )
        session.add(document)
        session.flush()

    chunk_count = session.scalar(select(func.count()).select_from(ChunkRecord).where(ChunkRecord.document_id == document.id))
    if chunk_count == 0:
        persist_document_chunks(
            session,
            document=document,
            pages=sample_course_pages(),
            chunker=SemanticChunker(max_tokens=80, overlap_tokens=8),
            embedding_model=HashingEmbeddingModel(),
        )
    elif document.status != "embedded":
        document.status = "embedded"

    session.commit()
    return course


def main() -> None:
    course_id = seed_sample_course()
    print(f"sample_course_id={course_id}")


if __name__ == "__main__":
    main()
