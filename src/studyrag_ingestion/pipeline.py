from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import Engine

from studyrag_core import HashingEmbeddingModel
from studyrag_core.embeddings import EmbeddingModel
from studyrag_core.text_extraction import extract_pages
from studyrag_persistence.database import create_session_factory
from studyrag_persistence.models import DocumentRecord
from studyrag_persistence.services import persist_document_chunks


class IngestionError(RuntimeError):
    pass


@dataclass(frozen=True)
class IngestionResult:
    document_id: uuid.UUID
    status: str
    success: bool
    error: str | None = None


def ingest_document_file(
    session,
    *,
    document_id: uuid.UUID | str,
    source_path: str | Path,
    embedding_model: EmbeddingModel | None = None,
) -> IngestionResult:
    """Extract, chunk, embed, and persist one uploaded document.

    This function deliberately writes through `persist_document_chunks()` so the
    ingestion path reuses the Phase 2 persistence code already tested against
    real Postgres/pgvector.
    """

    document_uuid = uuid.UUID(str(document_id))
    embedding_model = embedding_model or HashingEmbeddingModel()

    try:
        document = session.get(DocumentRecord, document_uuid)
        if document is None:
            raise IngestionError(f"document not found: {document_uuid}")

        pages = extract_pages(source_path)
        if not any(page.text.strip() for page in pages):
            raise IngestionError("no extractable text found in document")

        persist_document_chunks(
            session,
            document=document,
            pages=pages,
            embedding_model=embedding_model,
        )
        session.commit()
        return IngestionResult(document_id=document_uuid, status="embedded", success=True)
    except Exception as exc:
        session.rollback()
        failed_document = session.get(DocumentRecord, document_uuid)
        if failed_document is not None:
            failed_document.status = "failed"
            session.commit()
        return IngestionResult(
            document_id=document_uuid,
            status="failed",
            success=False,
            error=str(exc),
        )


def run_document_ingestion(
    engine: Engine,
    document_id: uuid.UUID | str,
    source_path: str | Path,
    embedding_model: EmbeddingModel | None = None,
    *,
    cleanup_source: bool = True,
) -> IngestionResult:
    session_factory = create_session_factory(engine)
    source = Path(source_path)

    try:
        with session_factory() as session:
            return ingest_document_file(
                session,
                document_id=document_id,
                source_path=source,
                embedding_model=embedding_model,
            )
    finally:
        if cleanup_source:
            source.unlink(missing_ok=True)
