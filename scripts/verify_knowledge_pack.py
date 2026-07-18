#!/usr/bin/env python3
"""Verify hashes, schema, retrieval quality, and public safety of a Pack."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from typing import Any

from knowledge_pack.frontmatter import load_strict_yaml
from knowledge_pack.security_scan import scan_public_text
from knowledge_pack.sqlite_pack import (
    REQUIRED_TABLES,
    count_rows,
    database_identity,
    database_tables,
    search_database,
)


MAX_COMPRESSED_BYTES = 64 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 128 * 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def _decompress_checked(source: Path, destination: Path) -> None:
    if source.stat().st_size > MAX_COMPRESSED_BYTES:
        raise ValueError("compressed Pack exceeds budget")
    written = 0
    with gzip.open(source, "rb") as input_handle:
        with destination.open("wb") as output_handle:
            while True:
                block = input_handle.read(1024 * 1024)
                if not block:
                    break
                written += len(block)
                if written > MAX_UNCOMPRESSED_BYTES:
                    raise ValueError("uncompressed Pack exceeds budget")
                output_handle.write(block)


def _verify_golden_queries(
    connection: sqlite3.Connection,
    golden_path: Path,
) -> dict[str, Any]:
    loaded = load_strict_yaml(golden_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict) or not isinstance(loaded.get("queries"), list):
        raise ValueError("golden queries must contain a queries list")
    recall_at = int(loaded.get("recall_at", 5))
    passed = 0
    positive = 0
    outcomes: list[dict[str, Any]] = []
    for item in loaded["queries"]:
        if not isinstance(item, dict):
            raise ValueError("golden query entry must be an object")
        query_id = str(item["id"])
        query = str(item["query"])
        rows = search_database(connection, query, recall_at)
        paths = [str(row["relative_path"]) for row in rows]
        if item.get("expect_no_results") is True:
            ok = not rows
        else:
            positive += 1
            expected_path = str(item["expected_path"])
            ok = expected_path in paths
        if ok:
            passed += 1
        outcomes.append({"id": query_id, "ok": ok, "paths": paths})
    recall = passed / len(outcomes) if outcomes else 0.0
    minimum_recall = float(loaded.get("minimum_recall", 1.0))
    if recall < minimum_recall:
        failures = [outcome for outcome in outcomes if not outcome["ok"]]
        raise ValueError(f"golden query recall {recall:.3f} below {minimum_recall}: {failures}")
    return {
        "queryCount": len(outcomes),
        "positiveQueryCount": positive,
        "recall": recall,
    }


def verify(pack_dir: Path, golden_path: Path | None) -> dict[str, Any]:
    manifest = _load_json(pack_dir / "manifest.json")
    audit = _load_json(pack_dir / "audit-summary.json")
    database = pack_dir / str(manifest["database"]["file"])
    if database.stat().st_size != int(manifest["database"]["compressedBytes"]):
        raise ValueError("compressed database length mismatch")
    if sha256_file(database) != manifest["database"]["sha256"]:
        raise ValueError("compressed database hash mismatch")
    if sha256_file(pack_dir / manifest["audit"]["file"]) != manifest["audit"]["sha256"]:
        raise ValueError("audit hash mismatch")
    for filename, expected_hash in manifest["licenses"]["files"].items():
        if sha256_file(pack_dir / "licenses" / filename) != expected_hash:
            raise ValueError(f"license hash mismatch: {filename}")

    with tempfile.TemporaryDirectory(prefix="aiw-pack-verify-") as temp_dir:
        sqlite_path = Path(temp_dir) / "content.sqlite"
        _decompress_checked(database, sqlite_path)
        if sqlite_path.stat().st_size != int(
            manifest["database"]["uncompressedBytes"]
        ):
            raise ValueError("uncompressed database length mismatch")
        if sha256_file(sqlite_path) != manifest["database"]["uncompressedSha256"]:
            raise ValueError("uncompressed database hash mismatch")
        connection = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
        try:
            quick_check = connection.execute("PRAGMA quick_check").fetchone()
            if not quick_check or quick_check[0] != "ok":
                raise ValueError(f"SQLite quick_check failed: {quick_check}")
            missing_tables = REQUIRED_TABLES - database_tables(connection)
            if missing_tables:
                raise ValueError(f"missing Pack tables: {sorted(missing_tables)}")
            identity = database_identity(connection)
            for key in (
                "packId",
                "packFormatVersion",
                "contentVersion",
                "sourceRevision",
                "contentFingerprint",
                "generatedAt",
            ):
                if identity.get(key) != manifest.get(key):
                    raise ValueError(f"internal manifest mismatch: {key}")
            counts = count_rows(
                connection,
                ("articles", "sections", "chunks", "sources"),
            )
            if counts["articles"] != int(manifest["articleCount"]):
                raise ValueError("article count mismatch")
            if counts["sections"] != int(manifest["sectionCount"]):
                raise ValueError("section count mismatch")
            if counts["chunks"] != int(manifest["chunkCount"]):
                raise ValueError("chunk count mismatch")
            if int(audit["acceptedArticleCount"]) != counts["articles"]:
                raise ValueError("audit accepted count mismatch")
            for (body,) in connection.execute("SELECT body FROM chunks"):
                findings = scan_public_text(str(body))
                if findings:
                    raise ValueError(
                        f"public safety finding in Pack body: {findings[0].code}"
                    )
            golden = (
                _verify_golden_queries(connection, golden_path)
                if golden_path is not None
                else None
            )
        finally:
            connection.close()
    return {
        "packId": manifest["packId"],
        "contentVersion": manifest["contentVersion"],
        "articleCount": manifest["articleCount"],
        "chunkCount": manifest["chunkCount"],
        "databaseSha256": manifest["database"]["sha256"],
        "goldenQueries": golden,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack-dir", required=True)
    parser.add_argument("--golden-queries")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = verify(
            Path(args.pack_dir).resolve(),
            Path(args.golden_queries).resolve() if args.golden_queries else None,
        )
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
