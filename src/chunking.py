from __future__ import annotations

import math
import re
import unicodedata


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])(?:\s+|\n+)", text.strip())
            if sentence.strip()
        ]
        if not sentences:
            return []

        chunks: list[str] = []
        for index in range(0, len(sentences), self.max_sentences_per_chunk):
            group = sentences[index : index + self.max_sentences_per_chunk]
            chunks.append(" ".join(group).strip())
        return chunks


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        return self._split(text.strip(), list(self.separators))

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        current_text = current_text.strip()
        if not current_text:
            return []

        if len(current_text) <= self.chunk_size:
            return [current_text]

        if not remaining_separators:
            return [
                current_text[index : index + self.chunk_size].strip()
                for index in range(0, len(current_text), self.chunk_size)
                if current_text[index : index + self.chunk_size].strip()
            ]

        separator = remaining_separators[0]
        next_separators = remaining_separators[1:]

        if separator == "":
            return [
                current_text[index : index + self.chunk_size].strip()
                for index in range(0, len(current_text), self.chunk_size)
                if current_text[index : index + self.chunk_size].strip()
            ]

        if separator not in current_text:
            return self._split(current_text, next_separators)

        pieces = current_text.split(separator)
        chunks: list[str] = []
        buffer = ""

        for piece in pieces:
            piece = piece.strip()
            if not piece:
                continue

            candidate = piece if not buffer else f"{buffer}{separator}{piece}"
            if len(candidate) <= self.chunk_size:
                buffer = candidate
                continue

            if buffer:
                chunks.append(buffer.strip())
                buffer = ""

            if len(piece) <= self.chunk_size:
                buffer = piece
            else:
                chunks.extend(self._split(piece, next_separators))

        if buffer:
            chunks.append(buffer.strip())

        normalized_chunks: list[str] = []
        for chunk in chunks:
            if len(chunk) <= self.chunk_size:
                normalized_chunks.append(chunk)
            else:
                normalized_chunks.extend(self._split(chunk, next_separators))
        return normalized_chunks


def _fold_to_ascii(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    without_accents = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return without_accents


class VietnameseLegalChunker:
    """
    Custom chunker for Vietnamese legal texts and legal commentary.

    Strategy:
        - detect legal anchors such as article references, case sections,
          decision headings, and legal discourse markers.
        - split the document into paragraph/sentence-level units.
        - greedily pack neighboring units around each anchor so every chunk
          keeps a full legal point instead of stopping at arbitrary separators.
    """

    def __init__(self, chunk_size: int = 1200, min_chunk_size: int = 200) -> None:
        self.chunk_size = chunk_size
        self.min_chunk_size = min_chunk_size
        self.target_chunk_size = max(min_chunk_size, int(chunk_size * 0.85))
        self._fallback_chunker = RecursiveChunker(
            separators=["\n\n", "\n", ". ", "; ", ": ", ", ", " ", ""],
            chunk_size=chunk_size,
        )

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        normalized_text = self._prepare_text(text)
        units = self._extract_units(normalized_text)
        if not units:
            return self._fallback_chunker.chunk(normalized_text.strip())

        chunks = self._assemble_chunks(units)
        return self._merge_small_chunks(chunks)

    def _prepare_text(self, text: str) -> str:
        prepared = text.replace("\r\n", "\n").replace("\r", "\n")

        # Legal commentary often places legal anchors inline after a short title.
        prepared = re.sub(
            r"(?<=[\.\:])\s+(?=(?:Điều|Khoản|Điểm)\s+\d+|(?:Tình huống|Dẫn nhập|Kết luận|Nhận định|Quyết định)\b)",
            "\n",
            prepared,
        )
        prepared = re.sub(r"\n{3,}", "\n\n", prepared)
        return prepared

    def _extract_units(self, text: str) -> list[tuple[str, bool]]:
        units: list[tuple[str, bool]] = []
        paragraphs = [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]

        for paragraph in paragraphs:
            paragraph_anchor = self._is_anchor(paragraph)
            if len(paragraph) <= self.chunk_size:
                units.append((paragraph, paragraph_anchor))
                continue

            sentences = self._split_sentences(paragraph)
            if not sentences:
                fallback_parts = self._split_by_separators(paragraph)
                units.extend((part, self._is_anchor(part)) for part in fallback_parts if part.strip())
                continue

            buffer = ""
            buffer_anchor = paragraph_anchor
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                sentence_anchor = self._is_anchor(sentence)
                candidate = sentence if not buffer else f"{buffer} {sentence}"
                if buffer and (
                    len(candidate) > self.chunk_size
                    or (sentence_anchor and len(buffer) >= self.min_chunk_size)
                ):
                    units.append((buffer.strip(), buffer_anchor))
                    buffer = sentence
                    buffer_anchor = sentence_anchor
                    continue

                buffer = candidate
                buffer_anchor = buffer_anchor or sentence_anchor

            if buffer:
                units.append((buffer.strip(), buffer_anchor))

        return [(unit.strip(), anchor) for unit, anchor in units if unit.strip()]

    def _split_sentences(self, text: str) -> list[str]:
        parts = re.split(r"(?<=[.!?;:])\s+", text.strip())
        return [part.strip() for part in parts if part.strip()]

    def _split_by_separators(self, text: str) -> list[str]:
        return self._split_oversized_piece(text.strip(), ["; ", ": ", ", ", " ", ""])

    def _split_oversized_piece(self, text: str, separators: list[str]) -> list[str]:
        text = text.strip()
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]
        if not separators:
            return [
                text[index : index + self.chunk_size].strip()
                for index in range(0, len(text), self.chunk_size)
                if text[index : index + self.chunk_size].strip()
            ]

        separator = separators[0]
        next_separators = separators[1:]
        if separator == "":
            return [
                text[index : index + self.chunk_size].strip()
                for index in range(0, len(text), self.chunk_size)
                if text[index : index + self.chunk_size].strip()
            ]

        if separator not in text:
            return self._split_oversized_piece(text, next_separators)

        pieces = text.split(separator)
        segments: list[str] = []
        current = ""

        for piece in pieces:
            piece = piece.strip()
            if not piece:
                continue

            candidate = piece if not current else f"{current}{separator}{piece}"
            if len(candidate) <= self.chunk_size:
                current = candidate
                continue

            if current:
                segments.append(current.strip())
                current = ""

            if len(piece) <= self.chunk_size:
                current = piece
            else:
                segments.extend(self._split_oversized_piece(piece, next_separators))

        if current:
            segments.append(current.strip())

        return segments

    def _assemble_chunks(self, units: list[tuple[str, bool]]) -> list[str]:
        chunks: list[str] = []
        current_parts: list[str] = []
        current_length = 0

        for unit_text, is_anchor in units:
            unit_text = unit_text.strip()
            if not unit_text:
                continue

            separator_length = 2 if current_parts else 0
            projected_length = current_length + separator_length + len(unit_text)
            enough_context = current_length >= self.target_chunk_size or len(current_parts) >= 3

            if current_parts and (projected_length > self.chunk_size or (is_anchor and enough_context)):
                chunks.append("\n\n".join(current_parts).strip())
                current_parts = []
                current_length = 0

            if len(unit_text) > self.chunk_size:
                oversized_parts = self._split_by_separators(unit_text)
                if not oversized_parts:
                    oversized_parts = self._fallback_chunker.chunk(unit_text)
                for oversized_part in oversized_parts:
                    oversized_part = oversized_part.strip()
                    if not oversized_part:
                        continue
                    if current_parts and current_length + 2 + len(oversized_part) > self.chunk_size:
                        chunks.append("\n\n".join(current_parts).strip())
                        current_parts = []
                        current_length = 0
                    current_parts.append(oversized_part)
                    current_length = current_length + (2 if len(current_parts) > 1 else 0) + len(oversized_part)
                continue

            current_parts.append(unit_text)
            current_length = projected_length

        if current_parts:
            chunks.append("\n\n".join(current_parts).strip())

        return chunks

    def _merge_small_chunks(self, chunks: list[str]) -> list[str]:
        merged: list[str] = []
        index = 0

        while index < len(chunks):
            current = chunks[index].strip()
            if not current:
                index += 1
                continue

            next_chunk = chunks[index + 1].strip() if index + 1 < len(chunks) else ""
            if len(current) < self.min_chunk_size:
                if (
                    next_chunk
                    and len(current) + 2 + len(next_chunk) <= self.chunk_size
                    and (self._is_anchor(current) or len(current) < self.min_chunk_size // 2)
                ):
                    current = f"{current}\n\n{next_chunk}"
                    index += 1
                elif (
                    merged
                    and len(merged[-1]) + 2 + len(current) <= self.chunk_size
                    and len(merged[-1]) < self.target_chunk_size
                ):
                    merged[-1] = f"{merged[-1]}\n\n{current}"
                    index += 1
                    continue

            merged.append(current)
            index += 1

        return merged

    def _looks_like_upper_heading(self, line: str) -> bool:
        letters = [ch for ch in _fold_to_ascii(line) if ch.isalpha()]
        if len(letters) < 8:
            return False
        uppercase_count = sum(1 for ch in letters if ch.isupper())
        return uppercase_count / len(letters) >= 0.7

    def _is_anchor(self, text: str) -> bool:
        line = text.strip().splitlines()[0].strip() if text.strip() else ""
        folded = _fold_to_ascii(line).strip().lower()

        if not folded:
            return False
        if self._looks_like_upper_heading(line):
            return True
        if re.match(r"^(phan|chuong|muc|tieu muc)\b", folded):
            return True
        if re.match(r"^[ivxlcdm]+\.\s+", folded):
            return True
        if re.match(r"^(dieu|khoan|diem)\s+[0-9a-z]+", folded):
            return True
        if re.match(r"^(tinh huong|dan nhap|ket luan|nhan dinh|quyet dinh)\b", folded):
            return True
        if re.match(r"^thu\s+(nhat|hai|ba|tu|nam|sau|bay|tam|chin|muoi)\b", folded):
            return True
        if line.endswith(":") and len(line) <= 150:
            return True
        return False


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    magnitude_a = math.sqrt(sum(value * value for value in vec_a))
    magnitude_b = math.sqrt(sum(value * value for value in vec_b))
    if magnitude_a == 0.0 or magnitude_b == 0.0:
        return 0.0
    return _dot(vec_a, vec_b) / (magnitude_a * magnitude_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        overlap = min(50, max(0, chunk_size // 10))
        strategies = {
            "fixed_size": FixedSizeChunker(chunk_size=chunk_size, overlap=overlap),
            "by_sentences": SentenceChunker(max_sentences_per_chunk=3),
            "recursive": RecursiveChunker(chunk_size=chunk_size),
        }

        comparison: dict[str, dict[str, float | int | list[str]]] = {}
        for strategy_name, chunker in strategies.items():
            chunks = chunker.chunk(text)
            count = len(chunks)
            avg_length = (sum(len(chunk) for chunk in chunks) / count) if count else 0.0
            comparison[strategy_name] = {
                "count": count,
                "avg_length": avg_length,
                "chunks": chunks,
            }
        return comparison
