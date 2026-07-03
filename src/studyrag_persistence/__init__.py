"""Postgres persistence layer for StudyRAG."""

from .database import create_engine_from_url, session_scope
from .models import (
    Base,
    ChunkRecord,
    ConversationRecord,
    CourseRecord,
    DocumentRecord,
    MessageCitationRecord,
    MessageRecord,
    UserRecord,
)
from .retrieval import PostgresHybridRetriever
from .services import persist_document_chunks

__all__ = [
    "Base",
    "ChunkRecord",
    "ConversationRecord",
    "CourseRecord",
    "DocumentRecord",
    "MessageCitationRecord",
    "MessageRecord",
    "PostgresHybridRetriever",
    "UserRecord",
    "create_engine_from_url",
    "persist_document_chunks",
    "session_scope",
]
