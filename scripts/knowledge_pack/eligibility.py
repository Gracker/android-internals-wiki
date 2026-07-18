"""Corpus-wide body inclusion with public-safe metadata projection."""

from __future__ import annotations

from fnmatch import fnmatch
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any

import yaml

from .frontmatter import parse_corpus_article, scalar_text
from .markdown_chunks import build_sections_and_chunks, stable_article_id
from .models import AuditEntry, PackArticle, ScanResult
from .security_scan import redact_private_context_lines, scan_public_text


SKIPPED_FILENAMES = {"readme.md", "summary.md"}
VALID_CONFIDENCE = {
    "high": "high",
    "medium-high": "high",
    "medium": "medium",
    "medium-low": "low",
    "low": "low",
}
H1_PATTERN = re.compile(r"(?m)^#[ \t]+(.+?)[ \t]*#*[ \t]*$")


def _normalize_path(value: str) -> str:
    return value.replace("\\", "/").removeprefix("./")


def _metadata_distribution_excluded(metadata: dict[str, Any]) -> bool:
    distribution = metadata.get("distribution")
    if not isinstance(distribution, dict):
        return False
    value = distribution.get("smartperfetto")
    if isinstance(value, str):
        return value.strip().lower() in {"exclude", "excluded", "private", "deny"}
    if isinstance(value, dict):
        enabled = value.get("enabled")
        visibility = scalar_text(value.get("visibility"))
        return enabled is False or (
            visibility is not None
            and visibility.lower() in {"exclude", "excluded", "private", "deny"}
        )
    return False


def _safe_tags(value: Any) -> tuple[str, ...] | None:
    if not isinstance(value, list):
        return None
    tags: list[str] = []
    for item in value:
        text = scalar_text(item)
        if not text or len(text) > 80 or "\n" in text or scan_public_text(text):
            return None
        tags.append(text)
    if not tags or len(tags) > 32:
        return None
    return tuple(tags)


def _fallback_tags(relative_path: str) -> tuple[str, ...]:
    parts = PurePosixPath(relative_path).parts[1:-1]
    tags = tuple(part[:80] for part in parts[-2:] if part)
    return tags or ("android-internals",)


def _safe_sources(value: Any) -> tuple[dict[str, str], ...]:
    if not isinstance(value, list):
        return ()
    sources: list[dict[str, str]] = []
    for item in value:
        source_type = "reference"
        url: str | None = None
        if isinstance(item, str):
            url = item.strip()
        elif isinstance(item, dict):
            source_type = scalar_text(item.get("type")) or "reference"
            url = scalar_text(item.get("url")) or scalar_text(item.get("path"))
        if not url or not url.startswith("https://"):
            continue
        if (
            len(url) > 2_048
            or any(char in url for char in "\r\n\0")
            or scan_public_text(url)
        ):
            continue
        if len(source_type) > 80 or scan_public_text(source_type):
            source_type = "reference"
        sources.append({"type": source_type, "url": url})
    return tuple(sources)


def _policy_patterns(policy: dict[str, Any]) -> tuple[list[str], set[str], set[str]]:
    smartperfetto = policy["distribution"]["smartperfetto"]
    patterns = [
        _normalize_path(str(value))
        for value in smartperfetto.get("excluded_paths", [])
    ]
    blocklist = {
        _normalize_path(str(value))
        for value in smartperfetto.get("blocklist", [])
    }
    excluded_tags = {
        str(value).strip().lower()
        for value in smartperfetto.get("excluded_tags", [])
    }
    return patterns, blocklist, excluded_tags


def _path_excluded(relative_path: str, patterns: list[str]) -> bool:
    return any(fnmatch(relative_path, pattern) for pattern in patterns)


def _bounded_scalar(value: Any, maximum: int) -> str | None:
    text = scalar_text(value)
    if not text or len(text) > maximum or scan_public_text(text):
        return None
    return text


def _audit_scalar(value: Any) -> str:
    text = scalar_text(value)
    if not text or len(text) > 80 or scan_public_text(text):
        return "(missing)"
    return text


def _fallback_title(body: str, relative_path: str) -> str:
    match = H1_PATTERN.search(body)
    if match:
        title = match.group(1).strip()
        if title and len(title) <= 240 and not scan_public_text(title):
            return title
    fallback = PurePosixPath(relative_path).stem.replace("-", " ").replace("_", " ")
    return fallback[:240] or "Untitled Android Internals article"


def _fallback_chapter(relative_path: str) -> str:
    parts = PurePosixPath(relative_path).parts[1:-1]
    if not parts:
        return "root"
    candidate = "/".join(parts[-2:])
    if len(candidate) <= 80:
        return candidate
    return parts[-1][:80]


def _public_projection_hash(
    *,
    title: str,
    chapter: str,
    applicable_versions: str,
    confidence: str | None,
    last_verified: str | None,
    last_verified_against: str | None,
    tags: tuple[str, ...],
    sources: tuple[dict[str, str], ...],
    body: str,
) -> str:
    projection = {
        "applicable_versions": applicable_versions,
        "body": body,
        "chapter": chapter,
        "confidence": confidence,
        "last_verified": last_verified,
        "last_verified_against": last_verified_against,
        "sources": sources,
        "tags": tags,
        "title": title,
    }
    encoded = json.dumps(
        projection,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def scan_corpus_articles(repo_root: Path, policy: dict[str, Any]) -> ScanResult:
    src_root = repo_root / "src"
    if not src_root.is_dir():
        raise ValueError("src directory not found")
    excluded_patterns, policy_blocklist, excluded_tags = _policy_patterns(policy)
    audit_fields = tuple(policy["audit_metadata"]["workflow_fields"])
    accepted: list[PackArticle] = []
    excluded: list[AuditEntry] = []
    markdown_paths = sorted(src_root.rglob("*.md"))

    for path in markdown_paths:
        relative_path = _normalize_path(str(path.relative_to(repo_root)))
        if path.name.lower() in SKIPPED_FILENAMES:
            excluded.append(AuditEntry("reserved_markdown_file", relative_path))
            continue
        if _path_excluded(relative_path, excluded_patterns):
            excluded.append(AuditEntry("policy_path_excluded", relative_path))
            continue
        try:
            raw = path.read_text(encoding="utf-8")
            parsed = parse_corpus_article(relative_path, raw)
        except (OSError, UnicodeError, ValueError, yaml.YAMLError) as error:
            excluded.append(
                AuditEntry(
                    f"body_parse_failed:{type(error).__name__}:{error}",
                    relative_path,
                )
            )
            continue
        if relative_path in policy_blocklist:
            excluded.append(AuditEntry("policy_blocklist", relative_path))
            continue
        if _metadata_distribution_excluded(parsed.metadata):
            excluded.append(AuditEntry("article_distribution_excluded", relative_path))
            continue

        title = _bounded_scalar(parsed.metadata.get("title"), 240) or _fallback_title(
            parsed.body,
            relative_path,
        )
        chapter = _bounded_scalar(parsed.metadata.get("chapter"), 80) or _fallback_chapter(
            relative_path
        )
        applicable_versions = _bounded_scalar(
            parsed.metadata.get("applicable_versions"), 240
        ) or "unspecified in source"
        tags = _safe_tags(parsed.metadata.get("tags")) or _fallback_tags(relative_path)
        if excluded_tags.intersection(tag.lower() for tag in tags):
            excluded.append(AuditEntry("policy_tag_excluded", relative_path))
            continue
        sources = _safe_sources(parsed.metadata.get("sources"))
        confidence_raw = _bounded_scalar(parsed.metadata.get("confidence"), 40)
        confidence = (
            VALID_CONFIDENCE.get(confidence_raw.lower()) if confidence_raw else None
        )
        last_verified = _bounded_scalar(parsed.metadata.get("last_verified"), 40)
        last_verified_against = _bounded_scalar(
            parsed.metadata.get("last_verified_against"), 240
        )
        audit_metadata = tuple(
            (str(field), _audit_scalar(parsed.metadata.get(field)))
            for field in audit_fields
        )

        findings = scan_public_text(parsed.body)
        fatal = [finding.code for finding in findings if finding.severity == "fatal"]
        if fatal:
            raise ValueError(
                f"fatal secret finding in corpus article {relative_path}: {','.join(fatal)}"
            )
        public_body, redaction_codes = redact_private_context_lines(parsed.body)
        remaining_findings = scan_public_text(public_body)
        if remaining_findings:
            raise ValueError(
                f"public sanitization failed for {relative_path}: "
                f"{remaining_findings[0].code}"
            )

        article_id = stable_article_id(relative_path)
        sections, chunks = build_sections_and_chunks(
            article_id=article_id,
            article_title=title,
            tags=tags,
            body=public_body,
            body_start_line=parsed.body_start_line,
        )
        if not chunks:
            excluded.append(AuditEntry("empty_chunk_output", relative_path))
            continue
        accepted.append(
            PackArticle(
                article_id=article_id,
                relative_path=relative_path,
                title=title,
                chapter=chapter,
                applicable_versions=applicable_versions,
                confidence=confidence,
                last_verified=last_verified,
                last_verified_against=last_verified_against,
                tags=tags,
                sources=sources,
                public_hash=_public_projection_hash(
                    title=title,
                    chapter=chapter,
                    applicable_versions=applicable_versions,
                    confidence=confidence,
                    last_verified=last_verified,
                    last_verified_against=last_verified_against,
                    tags=tags,
                    sources=sources,
                    body=public_body,
                ),
                metadata_quality=parsed.metadata_quality,
                metadata_error=parsed.metadata_error,
                audit_metadata=audit_metadata,
                redaction_codes=redaction_codes,
                sections=sections,
                chunks=chunks,
            )
        )

    accepted.sort(key=lambda article: article.relative_path)
    excluded.sort(key=lambda entry: (entry.reason, entry.relative_path))
    return ScanResult(
        accepted=tuple(accepted),
        excluded=tuple(excluded),
        total_markdown_files=len(markdown_paths),
    )


def public_content_fingerprint(articles: tuple[PackArticle, ...]) -> str:
    digest = hashlib.sha256()
    for article in articles:
        digest.update(article.relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(article.public_hash.encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()
