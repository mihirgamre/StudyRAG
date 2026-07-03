from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from studyrag_ingestion import object_key_for_document, run_document_ingestion
from studyrag_ingestion.storage import source_type_from_filename
from studyrag_persistence.models import DocumentRecord, UserRecord

from .dependencies import get_current_user, get_owned_course, get_owned_document, get_session

router = APIRouter()


class DocumentResponse(BaseModel):
    id: str
    filename: str
    source_type: str
    status: str
    storage_url: str | None


@router.post(
    "/courses/{course_id}/documents",
    status_code=status.HTTP_201_CREATED,
    response_model=DocumentResponse,
)
def upload_document(
    course_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: UserRecord = Depends(get_current_user),
) -> DocumentResponse:
    get_owned_course(session, current_user, course_id)

    try:
        source_type = source_type_from_filename(file.filename or "upload")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    document_id = uuid.uuid4()
    temp_path = _write_upload_to_temp_file(file, document_id)
    object_key = object_key_for_document(document_id, file.filename or "upload")
    storage_url = request.app.state.storage.put_file(
        temp_path,
        object_key=object_key,
        content_type=file.content_type,
    )

    document = DocumentRecord(
        id=document_id,
        course_id=course_id,
        filename=file.filename or "upload",
        source_type=source_type,
        storage_url=storage_url,
        status="pending",
    )
    session.add(document)
    session.commit()

    # Swap point: if real uploads start timing out or blocking workers, replace
    # this FastAPI BackgroundTasks call with an RQ enqueue that runs the same
    # `run_document_ingestion()` function in a worker.
    background_tasks.add_task(
        run_document_ingestion,
        request.app.state.engine,
        document_id,
        temp_path,
        request.app.state.embedding_model,
    )

    return DocumentResponse(
        id=str(document_id),
        filename=document.filename,
        source_type=document.source_type,
        status=document.status,
        storage_url=storage_url,
    )


@router.get("/courses/{course_id}/documents", response_model=list[DocumentResponse])
def list_documents(
    course_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: UserRecord = Depends(get_current_user),
) -> list[DocumentResponse]:
    course = get_owned_course(session, current_user, course_id)
    documents = session.scalars(
        select(DocumentRecord)
        .where(DocumentRecord.course_id == course.id)
        .order_by(DocumentRecord.uploaded_at.desc())
    ).all()
    return [
        DocumentResponse(
            id=str(document.id),
            filename=document.filename,
            source_type=document.source_type,
            status=document.status,
            storage_url=document.storage_url,
        )
        for document in documents
    ]


@router.get("/documents/{document_id}/status", response_model=DocumentResponse)
def get_document_status(
    document_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: UserRecord = Depends(get_current_user),
) -> DocumentResponse:
    document = get_owned_document(session, current_user, document_id)

    return DocumentResponse(
        id=str(document.id),
        filename=document.filename,
        source_type=document.source_type,
        status=document.status,
        storage_url=document.storage_url,
    )


def _write_upload_to_temp_file(file: UploadFile, document_id: uuid.UUID) -> Path:
    suffix = Path(file.filename or "").suffix
    temp_dir = Path(tempfile.mkdtemp(prefix="studyrag-upload-"))
    temp_path = temp_dir / f"{document_id}{suffix}"
    file.file.seek(0)
    with temp_path.open("wb") as destination:
        shutil.copyfileobj(file.file, destination)
    return temp_path
