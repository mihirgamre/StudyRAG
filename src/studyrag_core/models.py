from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Mapping, Sequence

SourceType = Literal["pdf", "docx", "txt", "slides"]
MessageRole = Literal["user", "assistant"]


@dataclass(frozen=True)
class SourceDocument:
    id: str
    course_id: str
    filename: str
    source_type: SourceType
    storage_url: str | None = None


@dataclass(frozen=True)
class PageText:
    text: str
    page_number: int | None = None


@dataclass(frozen=True)
class Chunk:
    id: str
    course_id: str
    document_id: str
    filename: str
    content: str
    page_number: int | None
    section_heading: str | None
    chunk_index: int
    token_count: int
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class EmbeddedChunk:
    chunk: Chunk
    embedding: tuple[float, ...]
    embedding_model: str


@dataclass(frozen=True)
class RetrievalHit:
    chunk: Chunk
    rank: int
    vector_score: float
    keyword_score: float
    fused_score: float


@dataclass(frozen=True)
class PromptSource:
    source_number: int
    hit: RetrievalHit

    @property
    def tag(self) -> str:
        return f"[source {self.source_number}]"


@dataclass(frozen=True)
class Message:
    role: MessageRole
    content: str


@dataclass(frozen=True)
class GenerationRequest:
    question: str
    prompt: str
    sources: Sequence[PromptSource]
    confidence: float
    included_history: Sequence[Message]


@dataclass(frozen=True)
class Citation:
    chunk_id: str
    document_id: str
    filename: str
    page_number: int | None
    section_heading: str | None
    snippet: str
    relevance_score: float


@dataclass(frozen=True)
class TutorResponse:
    answer: str
    citations: Sequence[Citation]
    confidence: float
    refused: bool
    generation_request: GenerationRequest | None = None
