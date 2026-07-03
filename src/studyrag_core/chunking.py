from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Sequence

from .models import Chunk, PageText, SourceDocument
from .text import normalize_whitespace, split_sentences, tail_tokens, token_count, tokenize


@dataclass(frozen=True)
class TextSection:
    heading: str | None
    content: str


class SemanticChunker:
    def __init__(
        self,
        *,
        max_tokens: int = 700,
        overlap_tokens: int = 105,
        min_chunk_tokens: int = 1,
    ) -> None:
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if overlap_tokens < 0:
            raise ValueError("overlap_tokens cannot be negative")
        if overlap_tokens >= max_tokens:
            raise ValueError("overlap_tokens must be smaller than max_tokens")
        if min_chunk_tokens <= 0:
            raise ValueError("min_chunk_tokens must be positive")

        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.min_chunk_tokens = min_chunk_tokens

    def chunk_document(self, document: SourceDocument, pages: Sequence[PageText]) -> list[Chunk]:
        chunks: list[Chunk] = []
        chunk_index = 0

        for page in pages:
            if not normalize_whitespace(page.text):
                continue

            for section in self._split_sections(page.text):
                for content in self._split_section_content(section.content):
                    count = token_count(content)
                    if count < self.min_chunk_tokens:
                        continue

                    chunks.append(
                        Chunk(
                            id=self._chunk_id(document.id, chunk_index, content),
                            course_id=document.course_id,
                            document_id=document.id,
                            filename=document.filename,
                            content=content,
                            page_number=page.page_number,
                            section_heading=section.heading,
                            chunk_index=chunk_index,
                            token_count=count,
                        )
                    )
                    chunk_index += 1

        return chunks

    def _split_sections(self, text: str) -> list[TextSection]:
        sections: list[TextSection] = []
        current_heading: str | None = None
        buffer: list[str] = []

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                if buffer:
                    buffer.append("")
                continue

            if self._looks_like_heading(line):
                self._append_section(sections, current_heading, buffer)
                current_heading = self._clean_heading(line)
                buffer = [line]
                continue

            buffer.append(line)

        self._append_section(sections, current_heading, buffer)
        return sections

    def _append_section(
        self,
        sections: list[TextSection],
        heading: str | None,
        buffer: list[str],
    ) -> None:
        content = normalize_whitespace("\n".join(buffer))
        if content:
            sections.append(TextSection(heading=heading, content=content))

    def _split_section_content(self, text: str) -> list[str]:
        text = normalize_whitespace(text)
        if token_count(text) <= self.max_tokens:
            return [text]

        units = self._semantic_units(text)
        chunks: list[str] = []
        current: list[str] = []
        current_count = 0

        for unit in units:
            unit_count = token_count(unit)
            if unit_count > self.max_tokens:
                if current:
                    chunks.append(normalize_whitespace("\n\n".join(current)))
                    current = []
                    current_count = 0
                chunks.extend(self._split_token_windows(unit))
                continue

            if current and current_count + unit_count > self.max_tokens:
                completed = normalize_whitespace("\n\n".join(current))
                chunks.append(completed)
                overlap = tail_tokens(completed, self.overlap_tokens)
                current = [overlap, unit] if overlap else [unit]
                current_count = token_count("\n\n".join(current))
            else:
                current.append(unit)
                current_count += unit_count

        if current:
            chunks.append(normalize_whitespace("\n\n".join(current)))

        return [chunk for chunk in chunks if chunk]

    def _semantic_units(self, text: str) -> list[str]:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
        units: list[str] = []

        for paragraph in paragraphs:
            if token_count(paragraph) <= self.max_tokens:
                units.append(paragraph)
                continue
            units.extend(split_sentences(paragraph) or [paragraph])

        return units

    def _split_token_windows(self, text: str) -> list[str]:
        words = tokenize(text)
        chunks: list[str] = []
        step = self.max_tokens - self.overlap_tokens
        start = 0

        while start < len(words):
            window = words[start : start + self.max_tokens]
            if not window:
                break
            chunks.append(" ".join(window))
            if start + self.max_tokens >= len(words):
                break
            start += step

        return chunks

    def _looks_like_heading(self, line: str) -> bool:
        if len(line) > 90:
            return False
        if line.startswith("#"):
            return True

        words = tokenize(line)
        if not words or len(words) > 10:
            return False
        if line.endswith((".", "?", "!", ";")):
            return False
        if re.match(r"^\d+(\.\d+)*\s+\S+", line):
            return True
        if line.isupper() and len(words) <= 8:
            return True
        return len(words) <= 6 and line[:1].isupper() and ":" not in line

    def _clean_heading(self, line: str) -> str:
        return line.lstrip("#").strip().rstrip(":")

    def _chunk_id(self, document_id: str, chunk_index: int, content: str) -> str:
        digest = hashlib.sha1(content.encode("utf-8")).hexdigest()[:12]
        return f"{document_id}:{chunk_index}:{digest}"
