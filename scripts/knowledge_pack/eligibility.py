"""Strict article eligibility and public-safe metadata projection."""

from __future__ import annotations

from fnmatch import fnmatch
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from .frontmatter import parse_article, scalar_text
from .markdown_chunks import build_sections_and_chunks, stable_article_id
from .models import AuditEntry, PackArticle, ScanResult
from .security_scan import scan_public_text


SKIPPED_FILENAMES = {"readme.md", "summary.md"}
VALID_CONFIDENCE = {
    "high": "high",
    "medium-high": "high",
    "medium": "medium",
    "medium-low": "low",
    "low": "low",
}


def _normalize_path(value: str) -> str:
    return value.replace("\\", "/").removeprefix("./")


def load_blocked_queue_paths(
    repo_root: Path,
    blocking_statuses: set[str],
) -> set[str]:
    queue_path = repo_root / "metadata" / "queue.json"
    loaded = json.loads(queue_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        raise ValueError("metadata/queue.json must contain a list")
    blocked: set[str] = set()
    for item in loaded:
        if not isinstance(item, dict):
            raise ValueError("metadata/queue.json entries must be objects")
        status = scalar_text(item.get("status"))
        if not status or status.lower() not in blocking_statuses:
            continue
        path_value = scalar_text(item.get("path")) or scalar_text(item.get("file"))
        if path_value:
            blocked.add(_normalize_path(path_value))
    return blocked


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


def _safe_tags(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError("tags_must_be_list")
    tags: list[str] = []
    for item in value:
        text = scalar_text(item)
        if not text or len(text) > 80 or "\n" in text:
            raise ValueError("tags_invalid")
        tags.append(text)
    if not tags or len(tags) > 32:
        raise ValueError("tags_invalid")
    return tuple(tags)


def _safe_sources(value: Any) -> tuple[dict[str, str], ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError("sources_must_be_list")
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
        if len(url) > 2_048 or any(char in url for char in "\r\n\0"):
            raise ValueError("source_url_invalid")
        sources.append({"type": source_type[:80], "url": url})
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


def _required_metadata_reason(
    metadata: dict[str, Any],
    eligibility: dict[str, Any],
) -> str | None:
    for key in (
        "status",
        "pipeline_stage",
        "task6_state",
        "task6_result",
        "task9_state",
        "task9_result",
    ):
        actual = scalar_text(metadata.get(key))
        expected = scalar_text(eligibility.get(key))
        if actual != expected:
            return f"{key}_not_eligible"
    for key in ("title", "chapter", "applicable_versions", "tags"):
        if key not in metadata:
            return f"missing_{key}"
    return None


def scan_eligible_articles(repo_root: Path, policy: dict[str, Any]) -> ScanResult:
    src_root = repo_root / "src"
    if not src_root.is_dir():
        raise ValueError("src directory not found")
    eligibility = policy["eligibility"]
    blocking_statuses = {
        str(value).strip().lower()
        for value in eligibility["blocking_queue_statuses"]
    }
    blocked_queue_paths = load_blocked_queue_paths(repo_root, blocking_statuses)
    excluded_patterns, policy_blocklist, excluded_tags = _policy_patterns(policy)
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
            parsed = parse_article(relative_path, raw)
        except (OSError, UnicodeError, ValueError, yaml.YAMLError) as error:
            excluded.append(
                AuditEntry(
                    f"strict_parse_failed:{type(error).__name__}",
                    relative_path,
                )
            )
            continue
        reason = _required_metadata_reason(parsed.metadata, eligibility)
        if reason:
            excluded.append(AuditEntry(reason, relative_path))
            continue
        if relative_path in blocked_queue_paths:
            excluded.append(AuditEntry("blocking_queue_entry", relative_path))
            continue
        if relative_path in policy_blocklist:
            excluded.append(AuditEntry("policy_blocklist", relative_path))
            continue
        if _metadata_distribution_excluded(parsed.metadata):
            excluded.append(AuditEntry("article_distribution_excluded", relative_path))
            continue
        try:
            title = scalar_text(parsed.metadata.get("title"))
            chapter = scalar_text(parsed.metadata.get("chapter"))
            applicable_versions = scalar_text(parsed.metadata.get("applicable_versions"))
            if not title or len(title) > 240:
                raise ValueError("title_invalid")
            if not chapter or len(chapter) > 80:
                raise ValueError("chapter_invalid")
            if not applicable_versions or len(applicable_versions) > 240:
                raise ValueError("applicable_versions_invalid")
            tags = _safe_tags(parsed.metadata.get("tags"))
            if excluded_tags.intersection(tag.lower() for tag in tags):
                excluded.append(AuditEntry("policy_tag_excluded", relative_path))
                continue
            sources = _safe_sources(parsed.metadata.get("sources"))
            confidence_raw = scalar_text(parsed.metadata.get("confidence"))
            confidence = (
                VALID_CONFIDENCE.get(confidence_raw.lower())
                if confidence_raw
                else None
            )
            if confidence_raw and confidence is None:
                raise ValueError("confidence_invalid")
            last_verified = scalar_text(parsed.metadata.get("last_verified"))
            last_verified_against = scalar_text(
                parsed.metadata.get("last_verified_against")
            )
            if last_verified_against and len(last_verified_against) > 240:
                raise ValueError("last_verified_against_invalid")
        except ValueError as error:
            excluded.append(AuditEntry(str(error), relative_path))
            continue

        findings = scan_public_text(raw)
        fatal = [finding.code for finding in findings if finding.severity == "fatal"]
        if fatal:
            raise ValueError(
                f"fatal secret finding in eligible article {relative_path}: {','.join(fatal)}"
            )
        exclude_findings = [
            finding.code for finding in findings if finding.severity == "exclude"
        ]
        if exclude_findings:
            excluded.append(
                AuditEntry(f"security_excluded:{exclude_findings[0]}", relative_path)
            )
            continue

        article_id = stable_article_id(relative_path)
        sections, chunks = build_sections_and_chunks(
            article_id=article_id,
            article_title=title,
            tags=tags,
            body=parsed.body,
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
                file_hash=parsed.file_hash,
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
        digest.update(article.file_hash.encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()
