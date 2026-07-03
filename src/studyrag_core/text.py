from __future__ import annotations

import re
from collections.abc import Iterable

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?")
SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+")

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "using",
    "was",
    "what",
    "when",
    "where",
    "with",
}


def tokenize(text: str, *, keep_stop_words: bool = True) -> list[str]:
    tokens = [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]
    if keep_stop_words:
        return tokens
    return [token for token in tokens if token not in STOP_WORDS]


def token_count(text: str) -> int:
    return len(tokenize(text))


def normalize_whitespace(text: str) -> str:
    lines = [" ".join(line.split()) for line in text.splitlines()]
    compacted = "\n".join(line for line in lines if line)
    return re.sub(r"\n{3,}", "\n\n", compacted).strip()


def split_sentences(text: str) -> list[str]:
    text = normalize_whitespace(text)
    if not text:
        return []
    return [part.strip() for part in SENTENCE_PATTERN.split(text) if part.strip()]


def tail_tokens(text: str, limit: int) -> str:
    if limit <= 0:
        return ""
    tokens = TOKEN_PATTERN.findall(text)
    return " ".join(tokens[-limit:])


def first_sentences(text: str, limit: int = 2) -> str:
    sentences = split_sentences(text)
    if not sentences:
        return normalize_whitespace(text)
    return " ".join(sentences[:limit])


def unique_preserving_order(values: Iterable[int]) -> list[int]:
    seen: set[int] = set()
    ordered: list[int] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered
