"""Focused TUF repository tests for immutable Knowledge Pack publication."""

from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import unittest

from tuf.api.metadata import Metadata
from tuf.api.exceptions import (
    DownloadLengthMismatchError,
    LengthOrHashMismatchError,
)
from tuf.ngclient import Updater


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from bootstrap_knowledge_pack_repository import (
    _validate_private_key_location,
    bootstrap,
)
from publish_knowledge_pack import (
    next_version,
    publish,
)
from knowledge_pack.tuf_repository import (
    latest_metadata_path,
    target_path,
)


def write_fake_pack(pack_dir: Path, version: str, fingerprint: str) -> None:
    (pack_dir / "licenses").mkdir(parents=True, exist_ok=True)
    (pack_dir / "content.sqlite.gz").write_bytes(b"fake sqlite")
    (pack_dir / "audit-summary.json").write_text("{}\n", encoding="utf-8")
    license_hashes: dict[str, str] = {}
    for filename in ("LICENSE", "COMMERCIAL-LICENSE.md", "KNOWLEDGE-PACK-LICENSE.md"):
        (pack_dir / "licenses" / filename).write_text(
            f"{filename}\n",
            encoding="utf-8",
        )
        license_hashes[filename] = "unit-test"
    manifest = {
        "packId": "android-internals",
        "contentVersion": version,
        "contentFingerprint": fingerprint,
        "sourceRevision": "0" * 40,
        "generatedAt": "2026-07-18T00:00:00Z",
        "database": {"file": "content.sqlite.gz"},
        "audit": {"file": "audit-summary.json"},
        "licenses": {"files": license_hashes},
    }
    (pack_dir / "manifest.json").write_text(
        json.dumps(manifest) + "\n",
        encoding="utf-8",
    )


class TufRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="aiw-tuf-test-")
        root = Path(self.temporary.name)
        self.repository = root / "repository"
        self.repository.mkdir()
        self.keys = root / "keys"
        bootstrap(REPO_ROOT, self.repository, self.keys)
        self.pack = root / "pack"
        write_fake_pack(self.pack, "2026.07.18.0", "fingerprint-a")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_bootstrap_delegates_all_pack_target_depths(self) -> None:
        targets = Metadata.from_file(
            str(latest_metadata_path(self.repository, "targets"))
        )
        role = targets.signed.delegations.roles["nightly"]
        self.assertTrue(role.is_delegated_path("channels/stable.json"))
        self.assertTrue(
            role.is_delegated_path(
                "packs/android-internals/2026.07.18.0/manifest.json"
            )
        )
        self.assertTrue(
            role.is_delegated_path(
                "packs/android-internals/2026.07.18.0/licenses/LICENSE"
            )
        )

    def test_private_keys_are_rejected_inside_either_repository(self) -> None:
        with self.assertRaisesRegex(ValueError, "outside source"):
            _validate_private_key_location(
                REPO_ROOT,
                self.repository,
                REPO_ROOT / "knowledge-pack" / "keys",
            )
        with self.assertRaisesRegex(ValueError, "outside source"):
            _validate_private_key_location(
                REPO_ROOT,
                self.repository,
                self.repository / "keys",
            )

    def test_publish_is_no_op_for_same_content_and_never_overwrites_version(self) -> None:
        first = publish(
            REPO_ROOT,
            self.repository,
            self.pack,
            self.keys,
            None,
            None,
            None,
        )
        self.assertTrue(first["published"])
        second = publish(
            REPO_ROOT,
            self.repository,
            self.pack,
            self.keys,
            None,
            None,
            None,
        )
        self.assertEqual(second["reason"], "content_fingerprint_unchanged")
        self.assertEqual(next_version(self.repository, "2026.07.18"), "2026.07.18.1")

        write_fake_pack(self.pack, "2026.07.18.0", "fingerprint-b")
        with self.assertRaisesRegex(ValueError, "already exists"):
            publish(
                REPO_ROOT,
                self.repository,
                self.pack,
                self.keys,
                None,
                None,
                None,
            )

    def test_revoking_current_stable_requires_an_existing_safe_version(self) -> None:
        publish(
            REPO_ROOT,
            self.repository,
            self.pack,
            self.keys,
            None,
            None,
            None,
        )
        write_fake_pack(self.pack, "2026.07.18.1", "fingerprint-b")
        publish(
            REPO_ROOT,
            self.repository,
            self.pack,
            self.keys,
            None,
            None,
            None,
        )
        with self.assertRaisesRegex(ValueError, "requires --minimum-safe-version"):
            publish(
                REPO_ROOT,
                self.repository,
                None,
                self.keys,
                "2026.07.18.1",
                None,
                "content-safety",
            )
        with self.assertRaisesRegex(ValueError, "is revoked"):
            publish(
                REPO_ROOT,
                self.repository,
                None,
                self.keys,
                "2026.07.18.1",
                "2026.07.18.1",
                "content-safety",
            )
        result = publish(
            REPO_ROOT,
            self.repository,
            None,
            self.keys,
            "2026.07.18.1",
            "2026.07.18.0",
            "content-safety",
        )
        self.assertEqual(result["revokedVersions"], ["2026.07.18.1"])

    def test_clean_client_rejects_tampered_consistent_target(self) -> None:
        publish(
            REPO_ROOT,
            self.repository,
            self.pack,
            self.keys,
            None,
            None,
            None,
        )
        handler = partial(
            SimpleHTTPRequestHandler,
            directory=str(self.repository),
        )
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client_root = Path(self.temporary.name) / "client"
            metadata_dir = client_root / "metadata"
            targets_dir = client_root / "targets"
            metadata_dir.mkdir(parents=True)
            targets_dir.mkdir()
            shutil.copyfile(
                self.repository / "metadata" / "1.root.json",
                metadata_dir / "root.json",
            )
            base_url = f"http://127.0.0.1:{server.server_port}"
            updater = Updater(
                str(metadata_dir),
                f"{base_url}/metadata/",
                str(targets_dir),
                f"{base_url}/targets/",
            )
            updater.refresh()
            target = updater.get_targetinfo("channels/stable.json")
            self.assertIsNotNone(target)
            physical = target_path(
                self.repository,
                "channels/stable.json",
                target,
            )
            physical.write_bytes(physical.read_bytes() + b"tampered")
            with self.assertRaises(
                (DownloadLengthMismatchError, LengthOrHashMismatchError)
            ):
                updater.download_target(target)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
