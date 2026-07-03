from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from typing import Protocol

from .text import tokenize


class EmbeddingModel(Protocol):
    name: str
    dimensions: int

    def embed(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        ...


class HashingEmbeddingModel:
    """Small deterministic embedding model for local tests and zero-cost dev.

    This is not a semantic model. It exists so retrieval, thresholding, and
    citation plumbing can be tested without network calls or model downloads.
    Swap to SentenceTransformerEmbeddingModel when validating real materials.
    """

    def __init__(self, *, dimensions: int = 384, name: str = "hashing-dev-384") -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self.dimensions = dimensions
        self.name = name

    def embed(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> tuple[float, ...]:
        vector = [0.0] * self.dimensions
        tokens = tokenize(text, keep_stop_words=False)
        features = list(tokens)
        features.extend(f"{left}_{right}" for left, right in zip(tokens, tokens[1:]))

        for feature in features:
            index = self._hash_to_index(feature)
            vector[index] += 1.0

        return _l2_normalize(vector)

    def _hash_to_index(self, value: str) -> int:
        digest = hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(digest, "big") % self.dimensions


class SentenceTransformerEmbeddingModel:
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed. Install the optional "
                "dependency with: pip install 'studyrag-core[local-models]'"
            ) from exc

        self.model_name = model_name
        self.name = model_name
        self._model = SentenceTransformer(model_name)
        dimensions = self._model.get_sentence_embedding_dimension()
        if dimensions is None:
            raise RuntimeError(f"Could not determine dimensions for {model_name}")
        self.dimensions = int(dimensions)

    def embed(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        vectors = self._model.encode(list(texts), normalize_embeddings=True)
        return [tuple(float(value) for value in vector) for vector in vectors]


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("vectors must have the same dimensions")

    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _l2_normalize(vector: Sequence[float]) -> tuple[float, ...]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return tuple(0.0 for _ in vector)
    return tuple(value / norm for value in vector)
