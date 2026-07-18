"""Manifest, hashing, deterministic gzip, and audit helpers."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

from . import BUILDER_VERSION, PACK_FORMAT_VERSION
from .models import ScanResult


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    path.write_text(f"{content}\n", encoding="utf-8")


def gzip_deterministic(source: Path, destination: Path) -> None:
    with source.open("rb") as input_handle:
        with destination.open("wb") as output_handle:
            with gzip.GzipFile(
                filename="",
                mode="wb",
                fileobj=output_handle,
                mtime=0,
                compresslevel=9,
            ) as gzip_handle:
                shutil.copyfileobj(input_handle, gzip_handle)


def build_audit_summary(
    scan: ScanResult,
    generated_at: str,
    source_revision: str,
) -> dict[str, Any]:
    reasons = Counter(entry.reason for entry in scan.excluded)
    return {
        "schemaVersion": 1,
        "generatedAt": generated_at,
        "sourceRevision": source_revision,
        "totalMarkdownFiles": scan.total_markdown_files,
        "acceptedArticleCount": len(scan.accepted),
        "excludedArticleCount": len(scan.excluded),
        "excludedReasonCounts": dict(sorted(reasons.items())),
        "acceptedArticleIds": [article.article_id for article in scan.accepted],
    }


def build_manifest(
    *,
    policy: dict[str, Any],
    content_version: str,
    source_revision: str,
    content_fingerprint: str,
    generated_at: str,
    scan: ScanResult,
    database_path: Path,
    compressed_path: Path,
    audit_path: Path,
    license_paths: list[Path],
) -> dict[str, Any]:
    chunk_count = sum(len(article.chunks) for article in scan.accepted)
    section_count = sum(len(article.sections) for article in scan.accepted)
    license_hashes = {
        path.name: sha256_file(path)
        for path in sorted(license_paths, key=lambda item: item.name)
    }
    return {
        "schemaVersion": 1,
        "packId": policy["pack_id"],
        "packFormatVersion": PACK_FORMAT_VERSION,
        "contentVersion": content_version,
        "sourceRevision": source_revision,
        "contentFingerprint": content_fingerprint,
        "builder": {
            "name": "android-internals-knowledge-pack",
            "version": BUILDER_VERSION,
        },
        "generatedAt": generated_at,
        "articleCount": len(scan.accepted),
        "sectionCount": section_count,
        "chunkCount": chunk_count,
        "database": {
            "file": compressed_path.name,
            "compression": "gzip",
            "uncompressedBytes": database_path.stat().st_size,
            "compressedBytes": compressed_path.stat().st_size,
            "uncompressedSha256": sha256_file(database_path),
            "sha256": sha256_file(compressed_path),
        },
        "audit": {
            "file": audit_path.name,
            "sha256": sha256_file(audit_path),
        },
        "licenses": {
            "expression": policy["license"]["expression"],
            "copyrightHolder": policy["license"]["copyright_holder"],
            "attribution": policy["license"]["attribution"],
            "files": license_hashes,
        },
        "compatibility": {
            "smartPerfettoMinVersion": policy["compatibility"][
                "smartperfetto_min_version"
            ],
            "smartPerfettoMaxVersion": policy["compatibility"][
                "smartperfetto_max_version"
            ],
        },
        "revocation": {
            "revoked": False,
            "minimumSafeVersion": content_version,
        },
    }


def normalize_utc_timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    normalized = parsed.astimezone(timezone.utc).replace(microsecond=0)
    return normalized.isoformat().replace("+00:00", "Z")
