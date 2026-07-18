"""Shared immutable data structures for Knowledge Pack construction."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ParsedArticle:
    relative_path: str
    metadata: dict[str, Any]
    body: str
    body_start_line: int
    file_hash: str


@dataclass(frozen=True)
class Section:
    section_id: str
    article_id: str
    heading: str
    heading_path: str
    level: int
    start_line: int
    end_line: int


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    article_id: str
    section_id: str
    heading: str
    body: str
    start_line: int
    end_line: int
    chunk_hash: str
    token_count: int
    search_tokens: str


@dataclass(frozen=True)
class PackArticle:
    article_id: str
    relative_path: str
    title: str
    chapter: str
    applicable_versions: str
    confidence: str | None
    last_verified: str | None
    last_verified_against: str | None
    tags: tuple[str, ...]
    sources: tuple[dict[str, str], ...]
    file_hash: str
    sections: tuple[Section, ...] = field(default_factory=tuple)
    chunks: tuple[Chunk, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AuditEntry:
    reason: str
    relative_path: str


@dataclass(frozen=True)
class ScanResult:
    accepted: tuple[PackArticle, ...]
    excluded: tuple[AuditEntry, ...]
    total_markdown_files: int
