#!/usr/bin/env python3
"""Bootstrap an offline-root TUF repository for AIW Knowledge Packs."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from securesystemslib.signer import CryptoSigner
from tuf.api.metadata import (
    DelegatedRole,
    Delegations,
    Metadata,
    Root,
    Snapshot,
    Targets,
    Timestamp,
)

from knowledge_pack.frontmatter import load_strict_yaml
from knowledge_pack.tuf_repository import (
    copy_public_license,
    expires_after,
    meta_file,
    write_immutable,
    write_timestamp,
    write_versioned_metadata,
)


ROLES = ("root", "targets", "nightly", "snapshot", "timestamp")


def _git_worktree_ancestor(path: Path) -> Path | None:
    candidate = path.resolve()
    for ancestor in (candidate, *candidate.parents):
        if (ancestor / ".git").exists():
            return ancestor
    return None


def _validate_private_key_location(
    repo_root: Path,
    repository_root: Path,
    keys_dir: Path,
) -> None:
    resolved_keys = keys_dir.resolve()
    for prohibited in (repo_root.resolve(), repository_root.resolve()):
        if resolved_keys == prohibited or resolved_keys.is_relative_to(prohibited):
            raise ValueError(
                "private TUF keys must be stored outside source and distribution repositories"
            )
    worktree = _git_worktree_ancestor(resolved_keys)
    if worktree is not None:
        raise ValueError(
            f"private TUF keys must be stored outside every Git worktree: {worktree}"
        )


def _load_policy(repo_root: Path) -> dict:
    value = load_strict_yaml(
        (repo_root / "knowledge-pack" / "channel-policy.yaml").read_text(
            encoding="utf-8"
        )
    )
    if not isinstance(value, dict):
        raise ValueError("channel policy must be a mapping")
    return value


def _write_private_keys(keys_dir: Path, signers: dict[str, CryptoSigner]) -> None:
    keys_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(keys_dir, 0o700)
    existing = [path for path in keys_dir.iterdir() if path.name != ".DS_Store"]
    if existing:
        raise ValueError(f"refusing to overwrite non-empty key directory: {keys_dir}")
    keyids: dict[str, str] = {}
    for role, signer in signers.items():
        path = keys_dir / f"{role}.pem"
        path.write_bytes(signer.private_bytes)
        os.chmod(path, 0o600)
        keyids[role] = signer.public_key.keyid
    (keys_dir / "keyids.json").write_text(
        json.dumps(keyids, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.chmod(keys_dir / "keyids.json", 0o600)


def bootstrap(
    repo_root: Path,
    repository_root: Path,
    keys_dir: Path,
) -> dict[str, str]:
    metadata_dir = repository_root / "metadata"
    if metadata_dir.exists() and any(metadata_dir.iterdir()):
        raise ValueError("refusing to overwrite existing TUF metadata")
    _validate_private_key_location(repo_root, repository_root, keys_dir)
    policy = _load_policy(repo_root)
    expiry = policy["metadata_expiry"]
    signers = {role: CryptoSigner.generate_ed25519() for role in ROLES}
    _write_private_keys(keys_dir, signers)

    root = Metadata(
        Root(
            version=1,
            expires=expires_after(days=int(expiry["root_days"])),
            consistent_snapshot=True,
        )
    )
    for role in ("root", "targets", "snapshot", "timestamp"):
        root.signed.add_key(signers[role].public_key, role)
    root.sign(signers["root"])

    targets = Metadata(
        Targets(
            version=1,
            expires=expires_after(days=int(expiry["targets_days"])),
            delegations=Delegations(
                keys={
                    signers["nightly"].public_key.keyid: signers[
                        "nightly"
                    ].public_key
                },
                roles={
                    "nightly": DelegatedRole(
                        "nightly",
                        [signers["nightly"].public_key.keyid],
                        1,
                        True,
                        paths=[
                            "channels/*",
                            "packs/*/*/*",
                            "packs/*/*/*/*",
                        ],
                    )
                },
            ),
        )
    )
    targets.sign(signers["targets"])

    nightly = Metadata(
        Targets(
            version=1,
            expires=expires_after(days=int(expiry["nightly_days"])),
        )
    )
    nightly.sign(signers["nightly"])

    _, targets_content = write_versioned_metadata(
        repository_root, "targets", targets
    )
    _, nightly_content = write_versioned_metadata(
        repository_root, "nightly", nightly
    )
    snapshot = Metadata(
        Snapshot(
            version=1,
            expires=expires_after(days=int(expiry["snapshot_days"])),
            meta={
                "targets.json": meta_file(targets.signed.version, targets_content),
                "nightly.json": meta_file(nightly.signed.version, nightly_content),
            },
        )
    )
    snapshot.sign(signers["snapshot"])
    _, snapshot_content = write_versioned_metadata(
        repository_root, "snapshot", snapshot
    )

    timestamp = Metadata(
        Timestamp(
            version=1,
            expires=expires_after(hours=int(expiry["timestamp_hours"])),
            snapshot_meta=meta_file(snapshot.signed.version, snapshot_content),
        )
    )
    timestamp.sign(signers["timestamp"])
    write_timestamp(repository_root, timestamp)
    write_versioned_metadata(repository_root, "root", root)

    public_templates = repo_root / "knowledge-pack" / "public-repository"
    write_immutable(
        repository_root / "README.md",
        (public_templates / "README.md").read_bytes(),
    )
    write_immutable(
        repository_root / "TRUST.md",
        (public_templates / "TRUST.md").read_bytes(),
    )
    copy_public_license(repo_root / "LICENSE", repository_root / "LICENSE")
    copy_public_license(
        repo_root / "LICENSE",
        repository_root / "LICENSES" / "CC-BY-NC-SA-4.0.txt",
    )
    copy_public_license(
        repo_root / "COMMERCIAL-LICENSE.md",
        repository_root / "LICENSES" / "AIW-COMMERCIAL-LICENSE.md",
    )
    copy_public_license(
        repo_root / "KNOWLEDGE-PACK-LICENSE.md",
        repository_root / "LICENSES" / "KNOWLEDGE-PACK-REDISTRIBUTION.md",
    )
    return {role: signer.public_key.keyid for role, signer in signers.items()}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        default=str(Path(__file__).resolve().parents[1]),
        help="AIW source repository",
    )
    parser.add_argument("--repository", required=True, help="public repository path")
    parser.add_argument("--keys-dir", required=True, help="private offline key directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        keyids = bootstrap(
            Path(args.repo).resolve(),
            Path(args.repository).resolve(),
            Path(args.keys_dir).resolve(),
        )
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"bootstrapped": True, "keyids": keyids}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
