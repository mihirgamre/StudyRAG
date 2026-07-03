from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from studyrag_core import HashingEmbeddingModel, PageText, SemanticChunker, SourceDocument
from studyrag_core.embeddings import EmbeddingModel

from .models import ChunkRecord, DocumentRecord


CHUNK_ID_NAMESPACE = uuid.UUID("b4f10ab1-c334-49ed-9e7c-97895242e76b")


def persist_document_chunks(
    session: Session,
    *,
    document: DocumentRecord,
    pages: Sequence[PageText],
    chunker: SemanticChunker | None = None,
    embedding_model: EmbeddingModel | None = None,
) -> list[ChunkRecord]:
    """Chunk, embed, and persist pages for one document.

    The chunking and embedding work delegates to `studyrag_core`; this service
    only maps the core dataclasses into SQLAlchemy records.
    """

    chunker = chunker or SemanticChunker()
    embedding_model = embedding_model or HashingEmbeddingModel()
    source_document = SourceDocument(
        id=str(document.id),
        course_id=str(document.course_id),
        filename=document.filename,
        source_type=document.source_type,  # type: ignore[arg-type]
        storage_url=document.storage_url,
    )

    core_chunks = chunker.chunk_document(source_document, pages)
    document.status = "chunked"
    session.flush()

    embeddings = embedding_model.embed([chunk.content for chunk in core_chunks])
    records: list[ChunkRecord] = []
    for core_chunk, embedding in zip(core_chunks, embeddings):
        record = ChunkRecord(
            id=stable_chunk_uuid(core_chunk.id),
            document_id=document.id,
            content=core_chunk.content,
            embedding=list(embedding),
            embedding_model=embedding_model.name,
            page_number=core_chunk.page_number,
            section_heading=core_chunk.section_heading,
            chunk_index=core_chunk.chunk_index,
            token_count=core_chunk.token_count,
        )
        session.add(record)
        records.append(record)

    document.status = "embedded"
    session.flush()
    return records


def stable_chunk_uuid(core_chunk_id: str) -> uuid.UUID:
    return uuid.uuid5(CHUNK_ID_NAMESPACE, core_chunk_id)
