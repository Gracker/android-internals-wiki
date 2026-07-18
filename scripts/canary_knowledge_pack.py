#!/usr/bin/env python3
"""Verify a clean-client TUF download of the stable AIW Knowledge Pack."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile

from tuf.ngclient import Updater

from verify_knowledge_pack import verify


def _download(updater: Updater, logical_path: str, destination: Path) -> None:
    target = updater.get_targetinfo(logical_path)
    if target is None:
        raise ValueError(f"TUF target not found: {logical_path}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    updater.download_target(target, str(destination))


def canary(
    root_path: Path,
    metadata_base_url: str,
    target_base_url: str,
    golden_path: Path,
    expected_revoked_version: str | None,
) -> dict:
    with tempfile.TemporaryDirectory(prefix="aiw-pack-canary-") as temp_dir:
        root = Path(temp_dir)
        metadata_dir = root / "metadata"
        target_dir = root / "targets"
        pack_dir = root / "pack"
        metadata_dir.mkdir()
        target_dir.mkdir()
        shutil.copyfile(root_path, metadata_dir / "root.json")
        updater = Updater(
            str(metadata_dir),
            metadata_base_url,
            str(target_dir),
            target_base_url,
        )
        updater.refresh()
        channel_path = root / "stable.json"
        _download(updater, "channels/stable.json", channel_path)
        channel = json.loads(channel_path.read_text(encoding="utf-8"))
        version = str(channel["contentVersion"])
        revoked_versions = set(channel.get("revokedVersions", []))
        if expected_revoked_version is not None:
            if expected_revoked_version not in revoked_versions:
                raise ValueError(
                    f"expected revocation missing: {expected_revoked_version}"
                )
            minimum_safe = str(channel.get("minimumSafeVersion") or "")
            if not minimum_safe or minimum_safe in revoked_versions:
                raise ValueError("revocation channel has no usable minimum safe version")
            safe_prefix = f"packs/android-internals/{minimum_safe}/"
            safe_manifest_path = root / "minimum-safe-manifest.json"
            _download(
                updater,
                f"{safe_prefix}manifest.json",
                safe_manifest_path,
            )
            safe_manifest = json.loads(
                safe_manifest_path.read_text(encoding="utf-8")
            )
            if safe_manifest.get("contentVersion") != minimum_safe:
                raise ValueError("minimum safe manifest version mismatch")
            return {
                "canary": "revocation-ok",
                "contentVersion": version,
                "revokedVersion": expected_revoked_version,
                "minimumSafeVersion": minimum_safe,
            }
        if version in revoked_versions:
            raise ValueError(f"stable Pack is revoked: {version}")
        targets = channel["targets"]
        _download(updater, targets["manifest"], pack_dir / "manifest.json")
        _download(
            updater,
            targets["database"],
            pack_dir / "content.sqlite.gz",
        )
        _download(
            updater,
            targets["audit"],
            pack_dir / "audit-summary.json",
        )
        for filename, logical_path in targets["licenses"].items():
            _download(
                updater,
                logical_path,
                pack_dir / "licenses" / filename,
            )
        result = verify(pack_dir, golden_path)
        if result["contentVersion"] != version:
            raise ValueError("stable channel and manifest version differ")
        return {
            "canary": "ok",
            "contentVersion": version,
            "articleCount": result["articleCount"],
            "chunkCount": result["chunkCount"],
            "databaseSha256": result["databaseSha256"],
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="trusted root metadata")
    parser.add_argument("--metadata-base-url", required=True)
    parser.add_argument("--target-base-url", required=True)
    parser.add_argument("--expected-revoked-version")
    parser.add_argument(
        "--golden-queries",
        default=str(
            Path(__file__).resolve().parents[1]
            / "knowledge-pack"
            / "golden-queries.yaml"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = canary(
            Path(args.root).resolve(),
            args.metadata_base_url,
            args.target_base_url,
            Path(args.golden_queries).resolve(),
            args.expected_revoked_version,
        )
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
