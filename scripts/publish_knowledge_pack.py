#!/usr/bin/env python3
"""Inspect or publish an immutable AIW Knowledge Pack through TUF."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any

from tuf.api.metadata import Metadata, Snapshot, Timestamp

from knowledge_pack.frontmatter import load_strict_yaml
from knowledge_pack.tuf_repository import (
    add_json_target,
    add_target,
    expires_after,
    latest_metadata_path,
    load_latest_metadata,
    meta_file,
    read_json_target,
    signer_for_role,
    write_timestamp,
    write_versioned_metadata,
)


CHANNEL_TARGET = "channels/stable.json"
CALVER_PATTERN = re.compile(r"^(?P<date>\d{4}\.\d{2}\.\d{2})\.(?P<serial>\d+)$")


def _load_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must contain an object")
    return loaded


def _load_policy(repo_root: Path) -> dict[str, Any]:
    loaded = load_strict_yaml(
        (repo_root / "knowledge-pack" / "channel-policy.yaml").read_text(
            encoding="utf-8"
        )
    )
    if not isinstance(loaded, dict):
        raise ValueError("channel policy must be a mapping")
    return loaded


def _load_repository(repository_root: Path) -> dict[str, Metadata]:
    metadata = {
        "root": load_latest_metadata(repository_root, "root"),
        "targets": load_latest_metadata(repository_root, "targets"),
        "nightly": load_latest_metadata(repository_root, "nightly"),
        "snapshot": load_latest_metadata(repository_root, "snapshot"),
        "timestamp": Metadata.from_file(
            str(repository_root / "metadata" / "timestamp.json")
        ),
    }
    metadata["root"].verify_delegate("targets", metadata["targets"])
    metadata["root"].verify_delegate("snapshot", metadata["snapshot"])
    metadata["root"].verify_delegate("timestamp", metadata["timestamp"])
    metadata["targets"].verify_delegate("nightly", metadata["nightly"])
    return metadata


def inspect_repository(repository_root: Path) -> dict[str, Any]:
    metadata = _load_repository(repository_root)
    channel = read_json_target(
        repository_root,
        metadata["nightly"],
        CHANNEL_TARGET,
    )
    versions: list[str] = []
    for logical_path in metadata["nightly"].signed.targets:
        parts = logical_path.split("/")
        if len(parts) >= 4 and parts[:2] == ["packs", "android-internals"]:
            version = parts[2]
            if CALVER_PATTERN.fullmatch(version):
                versions.append(version)
    return {
        "channel": channel,
        "publishedVersions": sorted(set(versions)),
        "metadataVersions": {
            role: value.signed.version
            for role, value in metadata.items()
        },
    }


def _published_versions(nightly: Metadata) -> set[str]:
    versions: set[str] = set()
    for logical_path in nightly.signed.targets:
        parts = logical_path.split("/")
        if len(parts) >= 4 and parts[:2] == ["packs", "android-internals"]:
            version = parts[2]
            if CALVER_PATTERN.fullmatch(version):
                versions.add(version)
    return versions


def next_version(repository_root: Path, date_value: str | None = None) -> str:
    prefix = date_value or datetime.now(timezone.utc).strftime("%Y.%m.%d")
    if not re.fullmatch(r"\d{4}\.\d{2}\.\d{2}", prefix):
        raise ValueError("version date must be YYYY.MM.DD")
    state = inspect_repository(repository_root)
    serials = [
        int(match.group("serial"))
        for version in state["publishedVersions"]
        if (match := CALVER_PATTERN.fullmatch(version))
        and match.group("date") == prefix
    ]
    return f"{prefix}.{max(serials, default=-1) + 1}"


def _role_signer(
    role_name: str,
    key_path: Path,
    metadata: dict[str, Metadata],
):
    if role_name == "nightly":
        delegations = metadata["targets"].signed.delegations
        if delegations is None or delegations.roles is None:
            raise ValueError("nightly delegation is missing")
        keyid = delegations.roles["nightly"].keyids[0]
        public_key = delegations.keys[keyid]
    else:
        keyid = metadata["root"].signed.roles[role_name].keyids[0]
        public_key = metadata["root"].signed.keys[keyid]
    return signer_for_role(key_path, public_key)


def _pack_channel(
    pack_dir: Path,
    manifest: dict[str, Any],
    previous: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Path]]:
    version = str(manifest["contentVersion"])
    prefix = f"packs/android-internals/{version}"
    files = {
        "manifest": pack_dir / "manifest.json",
        "database": pack_dir / str(manifest["database"]["file"]),
        "audit": pack_dir / str(manifest["audit"]["file"]),
    }
    license_targets: dict[str, str] = {}
    for filename in sorted(manifest["licenses"]["files"]):
        semantic_name = f"license:{filename}"
        files[semantic_name] = pack_dir / "licenses" / filename
        license_targets[filename] = f"{prefix}/licenses/{filename}"
    logical_targets = {
        "manifest": f"{prefix}/manifest.json",
        "database": f"{prefix}/content.sqlite.gz",
        "audit": f"{prefix}/audit-summary.json",
        "licenses": license_targets,
    }
    channel = {
        "schemaVersion": 1,
        "packId": manifest["packId"],
        "contentVersion": version,
        "contentFingerprint": manifest["contentFingerprint"],
        "sourceRevision": manifest["sourceRevision"],
        "generatedAt": manifest["generatedAt"],
        "targets": logical_targets,
        "revokedVersions": list((previous or {}).get("revokedVersions", [])),
        "minimumSafeVersion": (
            (previous or {}).get("minimumSafeVersion") or version
        ),
        "reasonCode": (previous or {}).get("reasonCode"),
    }
    return channel, files


def _apply_revocation(
    nightly: Metadata,
    channel: dict[str, Any] | None,
    revoke_version: str,
    minimum_safe_version: str | None,
    reason_code: str | None,
) -> dict[str, Any]:
    if channel is None:
        raise ValueError("cannot revoke before a stable channel exists")
    if not CALVER_PATTERN.fullmatch(revoke_version):
        raise ValueError("revoked version must be CalVer YYYY.MM.DD.N")
    published_versions = _published_versions(nightly)
    if revoke_version not in published_versions:
        raise ValueError(f"cannot revoke unpublished version: {revoke_version}")
    revoked = set(str(value) for value in channel.get("revokedVersions", []))
    revoked.add(revoke_version)
    if (
        revoke_version == channel["contentVersion"]
        and minimum_safe_version is None
    ):
        raise ValueError("revoking current stable requires --minimum-safe-version")
    safe_version = (
        minimum_safe_version
        or channel.get("minimumSafeVersion")
        or channel["contentVersion"]
    )
    if not CALVER_PATTERN.fullmatch(str(safe_version)):
        raise ValueError("minimum safe version must be CalVer YYYY.MM.DD.N")
    if safe_version not in published_versions:
        raise ValueError(f"minimum safe version is not published: {safe_version}")
    if safe_version in revoked:
        raise ValueError(f"minimum safe version is revoked: {safe_version}")
    updated = dict(channel)
    updated["revokedVersions"] = sorted(revoked)
    updated["minimumSafeVersion"] = safe_version
    updated["reasonCode"] = reason_code or "operator-revoked"
    return updated


def validate_revocation(
    repository_root: Path,
    revoke_version: str,
    minimum_safe_version: str | None,
    reason_code: str | None,
) -> dict[str, Any]:
    metadata = _load_repository(repository_root)
    channel = read_json_target(
        repository_root,
        metadata["nightly"],
        CHANNEL_TARGET,
    )
    updated = _apply_revocation(
        metadata["nightly"],
        channel,
        revoke_version,
        minimum_safe_version,
        reason_code,
    )
    return {
        "valid": True,
        "revokedVersion": revoke_version,
        "minimumSafeVersion": updated["minimumSafeVersion"],
        "reasonCode": updated["reasonCode"],
    }


def publish(
    repo_root: Path,
    repository_root: Path,
    pack_dir: Path | None,
    keys_dir: Path,
    revoke_version: str | None,
    minimum_safe_version: str | None,
    reason_code: str | None,
    refresh_metadata: bool = False,
) -> dict[str, Any]:
    if refresh_metadata and (pack_dir is not None or revoke_version is not None):
        raise ValueError(
            "metadata refresh cannot be combined with a Pack or revocation"
        )
    metadata = _load_repository(repository_root)
    policy = _load_policy(repo_root)
    expiry = policy["metadata_expiry"]
    nightly = metadata["nightly"]
    previous_channel = read_json_target(repository_root, nightly, CHANNEL_TARGET)
    channel = previous_channel
    published = False

    if pack_dir is not None:
        manifest = _load_json(pack_dir / "manifest.json")
        if manifest["contentVersion"] == "0.0.0-dev":
            raise ValueError("development Pack cannot be published")
        if (
            previous_channel
            and previous_channel.get("contentFingerprint")
            == manifest.get("contentFingerprint")
            and revoke_version is None
        ):
            return {
                "published": False,
                "reason": "content_fingerprint_unchanged",
                "contentVersion": previous_channel["contentVersion"],
            }
        channel, files = _pack_channel(pack_dir, manifest, previous_channel)
        version_prefix = (
            f"packs/android-internals/{manifest['contentVersion']}/"
        )
        if any(
            logical_path.startswith(version_prefix)
            for logical_path in nightly.signed.targets
        ):
            raise ValueError(
                f"immutable Pack version already exists: {manifest['contentVersion']}"
            )
        logical_targets = channel["targets"]
        add_target(
            nightly,
            repository_root,
            logical_targets["manifest"],
            files["manifest"],
        )
        add_target(
            nightly,
            repository_root,
            logical_targets["database"],
            files["database"],
        )
        add_target(
            nightly,
            repository_root,
            logical_targets["audit"],
            files["audit"],
        )
        for filename, logical_path in logical_targets["licenses"].items():
            add_target(
                nightly,
                repository_root,
                logical_path,
                files[f"license:{filename}"],
            )
        published = True

    if revoke_version is not None:
        channel = _apply_revocation(
            nightly,
            channel,
            revoke_version,
            minimum_safe_version,
            reason_code,
        )
        published = True

    if channel is None:
        raise ValueError("publish requires an existing stable channel")
    if not published and not refresh_metadata:
        raise ValueError("publish requires a Pack or --revoke-version")

    add_json_target(nightly, repository_root, CHANNEL_TARGET, channel)
    nightly.signed.version += 1
    nightly.signed.expires = expires_after(days=int(expiry["nightly_days"]))
    nightly.sign(
        _role_signer("nightly", keys_dir / "nightly.pem", metadata)
    )
    _, nightly_content = write_versioned_metadata(
        repository_root,
        "nightly",
        nightly,
    )

    targets_path = latest_metadata_path(repository_root, "targets")
    targets_content = targets_path.read_bytes()
    snapshot = Metadata(
        Snapshot(
            version=metadata["snapshot"].signed.version + 1,
            expires=expires_after(days=int(expiry["snapshot_days"])),
            meta={
                "targets.json": meta_file(
                    metadata["targets"].signed.version,
                    targets_content,
                ),
                "nightly.json": meta_file(
                    nightly.signed.version,
                    nightly_content,
                ),
            },
        )
    )
    snapshot.sign(
        _role_signer("snapshot", keys_dir / "snapshot.pem", metadata)
    )
    _, snapshot_content = write_versioned_metadata(
        repository_root,
        "snapshot",
        snapshot,
    )

    timestamp = Metadata(
        Timestamp(
            version=metadata["timestamp"].signed.version + 1,
            expires=expires_after(hours=int(expiry["timestamp_hours"])),
            snapshot_meta=meta_file(snapshot.signed.version, snapshot_content),
        )
    )
    timestamp.sign(
        _role_signer("timestamp", keys_dir / "timestamp.pem", metadata)
    )
    write_timestamp(repository_root, timestamp)
    return {
        "published": True,
        "contentPublished": published,
        "reason": "content_published" if published else "metadata_refreshed",
        "contentVersion": channel["contentVersion"],
        "contentFingerprint": channel["contentFingerprint"],
        "nightlyMetadataVersion": nightly.signed.version,
        "snapshotMetadataVersion": snapshot.signed.version,
        "timestampMetadataVersion": timestamp.signed.version,
        "revokedVersions": channel["revokedVersions"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        default=str(Path(__file__).resolve().parents[1]),
        help="AIW source repository",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("--repository", required=True)

    version_parser = subparsers.add_parser("next-version")
    version_parser.add_argument("--repository", required=True)
    version_parser.add_argument("--date")

    revoke_parser = subparsers.add_parser("validate-revocation")
    revoke_parser.add_argument("--repository", required=True)
    revoke_parser.add_argument("--revoke-version", required=True)
    revoke_parser.add_argument("--minimum-safe-version")
    revoke_parser.add_argument("--reason-code")

    publish_parser = subparsers.add_parser("publish")
    publish_parser.add_argument("--repository", required=True)
    publish_parser.add_argument("--pack-dir")
    publish_parser.add_argument("--keys-dir", required=True)
    publish_parser.add_argument("--revoke-version")
    publish_parser.add_argument("--minimum-safe-version")
    publish_parser.add_argument("--reason-code")
    publish_parser.add_argument("--refresh-metadata", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "inspect":
            result: Any = inspect_repository(Path(args.repository).resolve())
        elif args.command == "next-version":
            result = {
                "nextVersion": next_version(
                    Path(args.repository).resolve(),
                    args.date,
                )
            }
        elif args.command == "validate-revocation":
            result = validate_revocation(
                Path(args.repository).resolve(),
                args.revoke_version,
                args.minimum_safe_version,
                args.reason_code,
                args.refresh_metadata,
            )
        else:
            result = publish(
                Path(args.repo).resolve(),
                Path(args.repository).resolve(),
                Path(args.pack_dir).resolve() if args.pack_dir else None,
                Path(args.keys_dir).resolve(),
                args.revoke_version,
                args.minimum_safe_version,
                args.reason_code,
            )
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
