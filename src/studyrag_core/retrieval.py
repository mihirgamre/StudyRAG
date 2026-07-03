from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence

from .embeddings import EmbeddingModel, cosine_similarity
from .models import Chunk, EmbeddedChunk, RetrievalHit
from .text import tokenize


class InMemoryHybridRetriever:
    def __init__(self, embedding_model: EmbeddingModel, *, rrf_k: int = 60) -> None:
        if rrf_k <= 0:
            raise ValueError("rrf_k must be positive")
        self.embedding_model = embedding_model
        self.rrf_k = rrf_k
        self._records: list[EmbeddedChunk] = []

    def index_chunks(self, chunks: Sequence[Chunk]) -> None:
        self._records = []
        self.add_chunks(chunks)

    def add_chunks(self, chunks: Sequence[Chunk]) -> None:
        embeddings = self.embedding_model.embed([chunk.content for chunk in chunks])
        for chunk, embedding in zip(chunks, embeddings):
            self._records.append(
                EmbeddedChunk(
                    chunk=chunk,
                    embedding=embedding,
                    embedding_model=self.embedding_model.name,
                )
            )

    def retrieve(self, course_id: str, query: str, *, top_k: int = 5) -> list[RetrievalHit]:
        if top_k <= 0:
            raise ValueError("top_k must be positive")

        candidates = [
            record
            for record in self._records
            if record.chunk.course_id == course_id
            and record.embedding_model == self.embedding_model.name
        ]
        if not candidates:
            return []

        query_embedding = self.embedding_model.embed([query])[0]
        vector_scores = {
            record.chunk.id: cosine_similarity(query_embedding, record.embedding)
            for record in candidates
        }
        keyword_scores = self._bm25_scores(candidates, query)
        vector_ranks = self._rank_scores(vector_scores)
        keyword_ranks = self._rank_scores(keyword_scores, positive_only=True)

        hits: list[RetrievalHit] = []
        for record in candidates:
            chunk_id = record.chunk.id
            vector_rank = vector_ranks[chunk_id]
            keyword_rank = keyword_ranks.get(chunk_id)
            fused_score = 1.0 / (self.rrf_k + vector_rank)
            if keyword_rank is not None:
                fused_score += 1.0 / (self.rrf_k + keyword_rank)

            hits.append(
                RetrievalHit(
                    chunk=record.chunk,
                    rank=0,
                    vector_score=vector_scores[chunk_id],
                    keyword_score=keyword_scores.get(chunk_id, 0.0),
                    fused_score=fused_score,
                )
            )

        hits.sort(key=lambda hit: hit.fused_score, reverse=True)
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

    def _bm25_scores(self, records: Sequence[EmbeddedChunk], query: str) -> dict[str, float]:
        query_terms = tokenize(query, keep_stop_words=False)
        if not query_terms:
            return {record.chunk.id: 0.0 for record in records}

        doc_terms = {
            record.chunk.id: tokenize(record.chunk.content, keep_stop_words=False)
            for record in records
        }
        doc_lengths = {chunk_id: len(terms) for chunk_id, terms in doc_terms.items()}
        average_length = sum(doc_lengths.values()) / max(len(doc_lengths), 1)
        average_length = max(average_length, 1.0)

        document_frequency: Counter[str] = Counter()
        for terms in doc_terms.values():
            document_frequency.update(set(terms))

        total_docs = len(records)
        k1 = 1.5
        b = 0.75
        scores: dict[str, float] = {}

        for record in records:
            chunk_id = record.chunk.id
            term_counts = Counter(doc_terms[chunk_id])
            doc_length = max(doc_lengths[chunk_id], 1)
            score = 0.0

            for term in set(query_terms):
                frequency = term_counts.get(term, 0)
                if frequency == 0:
                    continue
                df = document_frequency[term]
                idf = math.log(1 + (total_docs - df + 0.5) / (df + 0.5))
                denominator = frequency + k1 * (1 - b + b * doc_length / average_length)
                score += idf * (frequency * (k1 + 1)) / denominator

            scores[chunk_id] = score

        return scores

    def _rank_scores(
        self,
        scores: dict[str, float],
        *,
        positive_only: bool = False,
    ) -> dict[str, int]:
        items = scores.items()
        if positive_only:
            items = [(key, value) for key, value in items if value > 0.0]
        ranked = sorted(items, key=lambda item: item[1], reverse=True)
        return {chunk_id: index for index, (chunk_id, _) in enumerate(ranked, start=1)}
