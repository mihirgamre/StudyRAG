"""Standalone RAG core for StudyRAG."""

from .chunking import SemanticChunker
from .embeddings import HashingEmbeddingModel, SentenceTransformerEmbeddingModel
from .generation import OpenAIChatResponseGenerator, ResponseGenerator
from .models import (
    Chunk,
    Citation,
    GenerationRequest,
    Message,
    PageText,
    PromptSource,
    RetrievalHit,
    SourceDocument,
    TutorResponse,
)
from .rag import CitationMapper, ConfidenceGate, PromptBuilder, Retriever, StudyRAGCore
from .retrieval import InMemoryHybridRetriever
from .text_extraction import extract_pages

__all__ = [
    "Chunk",
    "Citation",
    "CitationMapper",
    "ConfidenceGate",
    "GenerationRequest",
    "HashingEmbeddingModel",
    "InMemoryHybridRetriever",
    "Message",
    "OpenAIChatResponseGenerator",
    "PageText",
    "PromptBuilder",
    "PromptSource",
    "RetrievalHit",
    "Retriever",
    "ResponseGenerator",
    "SemanticChunker",
    "SentenceTransformerEmbeddingModel",
    "SourceDocument",
    "StudyRAGCore",
    "TutorResponse",
    "extract_pages",
]
