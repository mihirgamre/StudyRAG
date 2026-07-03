from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, joinedload

from studyrag_core.embeddings import EmbeddingModel
from studyrag_core.models import Chunk, RetrievalHit
from studyrag_core.text import tokenize

from .models import ChunkRecord, DocumentRecord


class PostgresHybridRetriever:
    """DB-backed retriever with the same public shape as the in-memory core retriever."""

    def __init__(
        self,
        session: Session,
        embedding_model: EmbeddingModel,
        *,
        rrf_k: int = 60,
        min_vector_only_score: float = 0.2,
    ) -> None:
        if rrf_k <= 0:
            raise ValueError("rrf_k must be positive")
        self.session = session
        self.embedding_model = embedding_model
        self.rrf_k = rrf_k
        self.min_vector_only_score = min_vector_only_score

    def retrieve(self, course_id: str, query: str, *, top_k: int = 5) -> list[RetrievalHit]:
        if top_k <= 0:
            raise ValueError("top_k must be positive")

        course_uuid = uuid.UUID(str(course_id))
        query_embedding = list(self.embedding_model.embed([query])[0])
        candidate_limit = max(top_k * 4, 20)

        vector_rows = self._vector_candidates(course_uuid, query_embedding, candidate_limit)
        keyword_rows = self._keyword_candidates(course_uuid, query, candidate_limit)
        if not vector_rows and not keyword_rows:
            return []

        records_by_id: dict[uuid.UUID, ChunkRecord] = {}
        vector_scores: dict[uuid.UUID, float] = {}
        keyword_scores: dict[uuid.UUID, float] = {}
        vector_ranks: dict[uuid.UUID, int] = {}
        keyword_ranks: dict[uuid.UUID, int] = {}

        for rank, (record, distance) in enumerate(vector_rows, start=1):
            records_by_id[record.id] = record
            vector_ranks[record.id] = rank
            vector_scores[record.id] = _clamp_similarity(1.0 - float(distance))

        for rank, (record, keyword_score) in enumerate(keyword_rows, start=1):
            records_by_id[record.id] = record
            keyword_ranks[record.id] = rank
            keyword_scores[record.id] = float(keyword_score or 0.0)

        hits: list[RetrievalHit] = []
        for record_id, record in records_by_id.items():
            fused_score = 0.0
            if record_id in vector_ranks:
                fused_score += 1.0 / (self.rrf_k + vector_ranks[record_id])
            if record_id in keyword_ranks:
                fused_score += 1.0 / (self.rrf_k + keyword_ranks[record_id])

            vector_score = vector_scores.get(record_id, 0.0)
            keyword_score = keyword_scores.get(record_id, 0.0)
            if keyword_score <= 0.0 and vector_score < self.min_vector_only_score:
                continue

            hits.append(
                RetrievalHit(
                    chunk=_to_core_chunk(record),
                    rank=0,
                    vector_score=vector_score,
                    keyword_score=keyword_score,
                    fused_score=fused_score,
                )
            )

        hits.sort(
            key=lambda hit: (hit.fused_score, hit.keyword_score, hit.vector_score),
            reverse=True,
        )
        return [
            RetrievalHit(
                chunk=hit.chunk,
                rank=index,
                vector_score=hit.vector_score,
                keyword_score=hit.keyword_score,
                fused_score=hit.fused_score,
            )
            for index, hit in enumerate(hits[:top_k], start=1)
        ]

    def _vector_candidates(
        self,
        course_id: uuid.UUID,
        query_embedding: Sequence[float],
        limit: int,
    ) -> list[tuple[ChunkRecord, float]]:
        distance = ChunkRecord.embedding.cosine_distance(query_embedding).label("distance")
        stmt = (
            select(ChunkRecord, distance)
            .join(ChunkRecord.document)
            .options(joinedload(ChunkRecord.document))
            .where(DocumentRecord.course_id == course_id)
            .where(ChunkRecord.embedding_model == self.embedding_model.name)
            .order_by(distance)
            .limit(limit)
        )
        return [(record, float(score)) for record, score in self.session.execute(stmt).all()]

    def _keyword_candidates(
        self,
        course_id: uuid.UUID,
        query: str,
        limit: int,
    ) -> list[tuple[ChunkRecord, float]]:
        query_terms = list(dict.fromkeys(tokenize(query, keep_stop_words=False)))
        if not query_terms:
            return []

        ts_query = func.to_tsquery("english", " | ".join(query_terms))
        rank = func.ts_rank_cd(ChunkRecord.content_tsv, ts_query).label("keyword_rank")
        stmt = (
            select(ChunkRecord, rank)
            .join(ChunkRecord.document)
            .options(joinedload(ChunkRecord.document))
            .where(DocumentRecord.course_id == course_id)
            .where(ChunkRecord.embedding_model == self.embedding_model.name)
            .where(ChunkRecord.content_tsv.op("@@")(ts_query))
            .order_by(desc(rank))
            .limit(limit)
        )
        return [(record, float(score or 0.0)) for record, score in self.session.execute(stmt).all()]


def _to_core_chunk(record: ChunkRecord) -> Chunk:
    return Chunk(
        id=str(record.id),
        course_id=str(record.document.course_id),
        document_id=str(record.document_id),
        filename=record.document.filename,
        content=record.content,
        page_number=record.page_number,
        section_heading=record.section_heading,
        chunk_index=record.chunk_index,
        token_count=record.token_count,
    )


def _clamp_similarity(value: float) -> float:
    return max(0.0, min(1.0, value))
