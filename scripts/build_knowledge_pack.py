#!/usr/bin/env python3
"""Build a deterministic, public-safe Android Internals Knowledge Pack."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any

from knowledge_pack import BUILDER_VERSION, PACK_FORMAT_VERSION
from knowledge_pack.eligibility import (
    public_content_fingerprint,
    scan_eligible_articles,
)
from knowledge_pack.frontmatter import load_strict_yaml
from knowledge_pack.manifest import (
    build_audit_summary,
    build_manifest,
    gzip_deterministic,
    normalize_utc_timestamp,
    write_json,
)
from knowledge_pack.sqlite_pack import create_pack_database


VERSION_PATTERN = re.compile(r"^(?:\d{4}\.\d{2}\.\d{2}\.\d+|0\.0\.0-dev)$")
OUTPUT_FILES = (
    "manifest.json",
    "content.sqlite",
    "content.sqlite.gz",
    "audit-summary.json",
)


def _git(repo_root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo_root), *args],
        text=True,
        stderr=subprocess.PIPE,
    ).strip()


def _source_identity(repo_root: Path) -> tuple[str, str, bool]:
    revision = _git(repo_root, "rev-parse", "HEAD")
    commit_time = _git(repo_root, "show", "-s", "--format=%cI", "HEAD")
    dirty = bool(
        _git(
            repo_root,
            "status",
            "--porcelain=v1",
            "--",
            "src",
            "metadata/queue.json",
            "knowledge-pack",
            "scripts/build_knowledge_pack.py",
            "scripts/knowledge_pack",
            "LICENSE",
            "COMMERCIAL-LICENSE.md",
            "KNOWLEDGE-PACK-LICENSE.md",
        )
    )
    return revision, normalize_utc_timestamp(commit_time), dirty


def _load_policy(path: Path) -> dict[str, Any]:
    loaded = load_strict_yaml(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("knowledge-pack policy must be a mapping")
    required_paths = (
        ("schema_version",),
        ("pack_id",),
        ("distribution", "smartperfetto", "default"),
        ("eligibility", "task9_result"),
        ("license", "expression"),
        ("compatibility", "smartperfetto_min_version"),
    )
    for segments in required_paths:
        value: Any = loaded
        for segment in segments:
            if not isinstance(value, dict) or segment not in value:
                raise ValueError(f"policy missing {'.'.join(segments)}")
            value = value[segment]
    if loaded["distribution"]["smartperfetto"]["default"] != "include-if-eligible":
        raise ValueError("unsupported distribution default")
    return loaded


def _prepare_output(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename in OUTPUT_FILES:
        path = output_dir / filename
        if path.exists():
            path.unlink()
    licenses_dir = output_dir / "licenses"
    if licenses_dir.exists():
        for path in licenses_dir.iterdir():
            if path.is_file():
                path.unlink()
    licenses_dir.mkdir(exist_ok=True)


def _public_content_fingerprint(
    repo_root: Path,
    policy: dict[str, Any],
    article_fingerprint: str,
) -> str:
    digest = hashlib.sha256()
    digest.update(f"articles:{article_fingerprint}\n".encode("ascii"))
    digest.update(
        json.dumps(
            policy,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    digest.update(b"\n")
    inputs = [
        repo_root / "LICENSE",
        repo_root / "COMMERCIAL-LICENSE.md",
        repo_root / "KNOWLEDGE-PACK-LICENSE.md",
        repo_root / "scripts" / "build_knowledge_pack.py",
        *sorted((repo_root / "scripts" / "knowledge_pack").glob("*.py")),
    ]
    for path in inputs:
        digest.update(str(path.relative_to(repo_root)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def build(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo).resolve()
    output_dir = Path(args.output).resolve()
    if not VERSION_PATTERN.fullmatch(args.version):
        raise ValueError("version must be CalVer YYYY.MM.DD.N or 0.0.0-dev")
    policy_path = repo_root / "knowledge-pack" / "policy.yaml"
    policy = _load_policy(policy_path)
    revision, commit_time, dirty = _source_identity(repo_root)
    if dirty and not args.allow_dirty:
        raise ValueError(
            "eligible source inputs are dirty; commit them or pass --allow-dirty for a development build"
        )
    generated_at = (
        normalize_utc_timestamp(args.built_at) if args.built_at else commit_time
    )
    _prepare_output(output_dir)
    scan = scan_eligible_articles(repo_root, policy)
    if not scan.accepted:
        raise ValueError("source_generation_empty")
    fingerprint = _public_content_fingerprint(
        repo_root,
        policy,
        public_content_fingerprint(scan.accepted),
    )
    database_path = output_dir / "content.sqlite"
    compressed_path = output_dir / "content.sqlite.gz"
    audit_path = output_dir / "audit-summary.json"
    identity = {
        "packId": policy["pack_id"],
        "packFormatVersion": PACK_FORMAT_VERSION,
        "contentVersion": args.version,
        "sourceRevision": revision,
        "contentFingerprint": fingerprint,
        "builderVersion": BUILDER_VERSION,
        "generatedAt": generated_at,
        "licenseExpression": policy["license"]["expression"],
    }
    create_pack_database(database_path, scan.accepted, identity)
    gzip_deterministic(database_path, compressed_path)
    audit = build_audit_summary(scan, generated_at, revision)
    write_json(audit_path, audit)
    license_sources = [
        repo_root / "LICENSE",
        repo_root / "COMMERCIAL-LICENSE.md",
        repo_root / "KNOWLEDGE-PACK-LICENSE.md",
    ]
    license_outputs: list[Path] = []
    for source in license_sources:
        destination = output_dir / "licenses" / source.name
        shutil.copyfile(source, destination)
        license_outputs.append(destination)
    manifest = build_manifest(
        policy=policy,
        content_version=args.version,
        source_revision=revision,
        content_fingerprint=fingerprint,
        generated_at=generated_at,
        scan=scan,
        database_path=database_path,
        compressed_path=compressed_path,
        audit_path=audit_path,
        license_paths=license_outputs,
    )
    write_json(output_dir / "manifest.json", manifest)
    database_path.unlink()
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        default=str(Path(__file__).resolve().parents[1]),
        help="AIW repository root",
    )
    parser.add_argument("--output", required=True, help="output directory")
    parser.add_argument("--version", required=True, help="CalVer content version")
    parser.add_argument("--built-at", help="reproducible ISO-8601 build timestamp")
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="allow dirty eligible source inputs for local development only",
    )
    return parser.parse_args()


def main() -> int:
    try:
        manifest = build(parse_args())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "packId": manifest["packId"],
                "contentVersion": manifest["contentVersion"],
                "sourceRevision": manifest["sourceRevision"],
                "contentFingerprint": manifest["contentFingerprint"],
                "articleCount": manifest["articleCount"],
                "chunkCount": manifest["chunkCount"],
                "databaseSha256": manifest["database"]["sha256"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
