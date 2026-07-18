"""Small repository helpers built exclusively on python-tuf public APIs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any

from securesystemslib.signer import Signer
from tuf.api.metadata import MetaFile, Metadata, TargetFile
from tuf.api.serialization.json import JSONSerializer


SERIALIZER = JSONSerializer(compact=True)
VERSIONED_METADATA_PATTERN = re.compile(r"^(?P<version>[1-9]\d*)\.(?P<role>.+)\.json$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def expires_after(*, days: int = 0, hours: int = 0) -> datetime:
    return utc_now() + timedelta(days=days, hours=hours)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def write_immutable(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError(f"immutable repository file already differs: {path}")
        return
    path.write_bytes(content)


def metadata_bytes(metadata: Metadata) -> bytes:
    return metadata.to_bytes(SERIALIZER)


def write_versioned_metadata(
    repository_root: Path,
    role_name: str,
    metadata: Metadata,
) -> tuple[Path, bytes]:
    content = metadata_bytes(metadata)
    path = (
        repository_root
        / "metadata"
        / f"{metadata.signed.version}.{role_name}.json"
    )
    write_immutable(path, content)
    return path, content


def write_timestamp(repository_root: Path, metadata: Metadata) -> tuple[Path, bytes]:
    content = metadata_bytes(metadata)
    path = repository_root / "metadata" / "timestamp.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path, content


def latest_metadata_path(repository_root: Path, role_name: str) -> Path:
    matches: list[tuple[int, Path]] = []
    for path in (repository_root / "metadata").glob(f"*.{role_name}.json"):
        match = VERSIONED_METADATA_PATTERN.fullmatch(path.name)
        if match and match.group("role") == role_name:
            matches.append((int(match.group("version")), path))
    if not matches:
        raise ValueError(f"missing versioned TUF metadata for role {role_name}")
    return max(matches, key=lambda item: item[0])[1]


def load_latest_metadata(repository_root: Path, role_name: str) -> Metadata:
    return Metadata.from_file(str(latest_metadata_path(repository_root, role_name)))


def meta_file(version: int, content: bytes) -> MetaFile:
    return MetaFile(
        version=version,
        length=len(content),
        hashes={"sha256": sha256_bytes(content)},
    )


def signer_for_role(
    key_path: Path,
    public_key: Any,
) -> Signer:
    return Signer.from_priv_key_uri(f"file2:{key_path}", public_key)


def _target_destination(
    repository_root: Path,
    logical_path: str,
    digest: str,
) -> Path:
    pure_path = PurePosixPath(logical_path)
    if pure_path.is_absolute() or ".." in pure_path.parts:
        raise ValueError(f"unsafe target path: {logical_path}")
    return (
        repository_root
        / "targets"
        / Path(*pure_path.parent.parts)
        / f"{digest}.{pure_path.name}"
    )


def add_target(
    role_metadata: Metadata,
    repository_root: Path,
    logical_path: str,
    source_path: Path,
) -> TargetFile:
    digest = sha256_file(source_path)
    destination = _target_destination(repository_root, logical_path, digest)
    write_immutable(destination, source_path.read_bytes())
    target = TargetFile.from_file(logical_path, str(destination))
    role_metadata.signed.targets[logical_path] = target
    return target


def add_json_target(
    role_metadata: Metadata,
    repository_root: Path,
    logical_path: str,
    value: Any,
) -> TargetFile:
    content = canonical_json_bytes(value)
    digest = sha256_bytes(content)
    destination = _target_destination(repository_root, logical_path, digest)
    write_immutable(destination, content)
    target = TargetFile.from_file(logical_path, str(destination))
    role_metadata.signed.targets[logical_path] = target
    return target


def target_path(
    repository_root: Path,
    logical_path: str,
    target: TargetFile,
) -> Path:
    digest = target.hashes.get("sha256")
    if not digest:
        raise ValueError(f"target has no sha256 hash: {logical_path}")
    return _target_destination(repository_root, logical_path, digest)


def read_json_target(
    repository_root: Path,
    role_metadata: Metadata,
    logical_path: str,
) -> dict[str, Any] | None:
    target = role_metadata.signed.targets.get(logical_path)
    if target is None:
        return None
    path = target_path(repository_root, logical_path, target)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"target must be a JSON object: {logical_path}")
    return loaded


def copy_public_license(source: Path, destination: Path) -> None:
    content = source.read_bytes()
    write_immutable(destination, content)
