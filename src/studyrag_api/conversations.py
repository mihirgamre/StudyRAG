from __future__ import annotations

import json
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from studyrag_core import Message, StudyRAGCore
from studyrag_persistence import PostgresHybridRetriever
from studyrag_persistence.models import (
    ConversationRecord,
    DocumentRecord,
    MessageCitationRecord,
    MessageRecord,
    UserRecord,
)

from .dependencies import get_current_user, get_owned_conversation, get_owned_course, get_session
from .rate_limit import limiter

router = APIRouter(tags=["conversations"])


class ConversationResponse(BaseModel):
    id: str
    course_id: str


class MessageCreateRequest(BaseModel):
    content: str = Field(min_length=1)


class CitationResponse(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page_number: int | None
    section_heading: str | None
    snippet: str
    relevance_score: float
    storage_url: str | None = None


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    citations: list[CitationResponse] = []


@router.post(
    "/courses/{course_id}/conversations",
    status_code=status.HTTP_201_CREATED,
    response_model=ConversationResponse,
)
def create_conversation(
    course_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: UserRecord = Depends(get_current_user),
) -> ConversationResponse:
    get_owned_course(session, current_user, course_id)
    conversation = ConversationRecord(course_id=course_id, user_id=current_user.id)
    session.add(conversation)
    session.commit()
    return ConversationResponse(id=str(conversation.id), course_id=str(course_id))


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
def list_messages(
    conversation_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: UserRecord = Depends(get_current_user),
) -> list[MessageResponse]:
    conversation = get_owned_conversation(session, current_user, conversation_id)
    records = session.scalars(
        select(MessageRecord)
        .where(MessageRecord.conversation_id == conversation.id)
        .order_by(MessageRecord.created_at, MessageRecord.id)
    ).all()
    return [_message_response(record) for record in records]


@router.post("/conversations/{conversation_id}/messages")
@limiter.limit(os.getenv("STUDYRAG_MESSAGE_RATE_LIMIT", "30/minute"))
def create_message(
    request: Request,
    conversation_id: uuid.UUID,
    payload: MessageCreateRequest,
    session: Session = Depends(get_session),
    current_user: UserRecord = Depends(get_current_user),
) -> StreamingResponse:
    conversation = get_owned_conversation(session, current_user, conversation_id)

    history_records = session.scalars(
        select(MessageRecord)
        .where(MessageRecord.conversation_id == conversation.id)
        .order_by(MessageRecord.created_at, MessageRecord.id)
    ).all()
    history = [Message(role=record.role, content=record.content) for record in history_records]

    user_message = MessageRecord(
        conversation_id=conversation.id,
        role="user",
        content=payload.content,
    )
    session.add(user_message)
    session.flush()

    retriever = PostgresHybridRetriever(session, request.app.state.embedding_model)
    core = StudyRAGCore(
        retriever,
        confidence_gate=request.app.state.confidence_gate,
        response_generator=request.app.state.response_generator,
    )
    tutor_response = core.prepare_generation(
        course_id=str(conversation.course_id),
        question=payload.content,
        history=history,
        top_k=request.app.state.retrieval_top_k,
    )

    assistant_message = MessageRecord(
        conversation_id=conversation.id,
        role="assistant",
        content=tutor_response.answer,
    )
    session.add(assistant_message)
    session.flush()

    citation_documents = {
        citation.document_id: session.get(DocumentRecord, uuid.UUID(citation.document_id))
        for citation in tutor_response.citations
    }

    for citation in tutor_response.citations:
        session.add(
            MessageCitationRecord(
                message_id=assistant_message.id,
                chunk_id=uuid.UUID(citation.chunk_id),
                relevance_score=citation.relevance_score,
            )
        )

    session.commit()
    final_payload = {
        "message_id": str(assistant_message.id),
        "answer": tutor_response.answer,
        "citations": [
            {
                "chunk_id": citation.chunk_id,
                "document_id": citation.document_id,
                "filename": citation.filename,
                "page_number": citation.page_number,
                "section_heading": citation.section_heading,
                "snippet": citation.snippet,
                "relevance_score": citation.relevance_score,
                "storage_url": citation_documents[citation.document_id].storage_url
                if citation_documents[citation.document_id] is not None
                else None,
            }
            for citation in tutor_response.citations
        ],
        "confidence": tutor_response.confidence,
        "refused": tutor_response.refused,
    }

    return StreamingResponse(
        _sse_stream(tutor_response.answer, final_payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _sse_stream(answer: str, final_payload: dict) -> list[str]:
    events: list[str] = []
    for token in _token_chunks(answer):
        events.append(_sse_event("token", {"text": token}))
    events.append(_sse_event("final", final_payload))
    return events


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _token_chunks(answer: str) -> list[str]:
    if not answer:
        return []
    parts = answer.split(" ")
    chunks: list[str] = []
    current: list[str] = []
    for index, part in enumerate(parts):
        suffix = " " if index < len(parts) - 1 else ""
        current.append(part + suffix)
        if len(current) >= 4 or sum(len(piece) for piece in current) >= 96:
            chunks.append("".join(current))
            current = []
    if current:
        chunks.append("".join(current))
    return chunks


def _message_response(record: MessageRecord) -> MessageResponse:
    citations: list[CitationResponse] = []
    for citation in record.citations:
        chunk = citation.chunk
        document = chunk.document
        citations.append(
            CitationResponse(
                chunk_id=str(chunk.id),
                document_id=str(document.id),
                filename=document.filename,
                page_number=chunk.page_number,
                section_heading=chunk.section_heading,
                snippet=chunk.content[:240],
                relevance_score=citation.relevance_score,
                storage_url=document.storage_url,
            )
        )

    return MessageResponse(
        id=str(record.id),
        role=record.role,
        content=record.content,
        citations=citations,
    )
