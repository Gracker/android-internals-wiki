"""Focused tests for deterministic Knowledge Pack construction."""

from __future__ import annotations

from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest

import yaml

from scripts.knowledge_pack.eligibility import (
    public_content_fingerprint,
    scan_eligible_articles,
)
from scripts.knowledge_pack.frontmatter import DuplicateKeyError, parse_article
from scripts.knowledge_pack.markdown_chunks import (
    build_sections_and_chunks,
    stable_article_id,
    tokenize_search_text,
)
from scripts.knowledge_pack.security_scan import scan_public_text
from scripts.knowledge_pack.sqlite_pack import (
    create_pack_database,
    search_database,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "knowledge-pack"


def load_policy() -> dict:
    return yaml.safe_load(
        (REPO_ROOT / "knowledge-pack" / "policy.yaml").read_text(encoding="utf-8")
    )


class FrontmatterTest(unittest.TestCase):
    def test_duplicate_keys_are_rejected(self) -> None:
        raw = (FIXTURE_ROOT / "src" / "duplicate.md").read_text(encoding="utf-8")
        with self.assertRaises(DuplicateKeyError):
            parse_article("src/duplicate.md", raw)


class EligibilityTest(unittest.TestCase):
    def test_only_strict_reviewed_non_blocked_article_is_accepted(self) -> None:
        result = scan_eligible_articles(FIXTURE_ROOT, load_policy())
        self.assertEqual(
            [article.relative_path for article in result.accepted],
            ["src/good.md"],
        )
        reasons = {entry.relative_path: entry.reason for entry in result.excluded}
        self.assertEqual(reasons["src/blocked.md"], "blocking_queue_entry")
        self.assertEqual(reasons["src/draft.md"], "status_not_eligible")
        self.assertTrue(reasons["src/duplicate.md"].startswith("strict_parse_failed"))

    def test_content_fingerprint_is_stable(self) -> None:
        first = scan_eligible_articles(FIXTURE_ROOT, load_policy())
        second = scan_eligible_articles(FIXTURE_ROOT, load_policy())
        self.assertEqual(
            public_content_fingerprint(first.accepted),
            public_content_fingerprint(second.accepted),
        )

    def test_malformed_yaml_is_excluded_without_aborting_scan(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aiw-pack-malformed-") as temp_dir:
            fixture = Path(temp_dir)
            shutil.copytree(FIXTURE_ROOT, fixture, dirs_exist_ok=True)
            malformed = fixture / "src" / "malformed.md"
            malformed.write_text(
                "---\n"
                "title: Malformed\n"
                "broken: | inline text\n"
                "---\n"
                "body\n",
                encoding="utf-8",
            )

            result = scan_eligible_articles(fixture, load_policy())

        reasons = {entry.relative_path: entry.reason for entry in result.excluded}
        self.assertEqual(
            reasons["src/malformed.md"],
            "strict_parse_failed:ScannerError",
        )


class MarkdownChunkTest(unittest.TestCase):
    def test_code_and_table_blocks_are_preserved(self) -> None:
        article_path = FIXTURE_ROOT / "src" / "good.md"
        parsed = parse_article(
            "src/good.md",
            article_path.read_text(encoding="utf-8"),
        )
        article_id = stable_article_id("src/good.md")
        sections, chunks = build_sections_and_chunks(
            article_id,
            "RecyclerView 性能测试",
            ("RecyclerView", "rendering"),
            parsed.body,
            parsed.body_start_line,
        )
        self.assertGreaterEqual(len(sections), 2)
        combined = "\n".join(chunk.body for chunk in chunks)
        self.assertIn("```sql", combined)
        self.assertIn("| 信号 | 含义 |", combined)
        self.assertEqual(
            [chunk.chunk_id for chunk in chunks],
            [
                chunk.chunk_id
                for chunk in build_sections_and_chunks(
                    article_id,
                    "RecyclerView 性能测试",
                    ("RecyclerView", "rendering"),
                    parsed.body,
                    parsed.body_start_line,
                )[1]
            ],
        )

    def test_search_tokens_cover_han_and_identifiers(self) -> None:
        tokens = tokenize_search_text("RecyclerView 主线程 frame_timeline")
        self.assertIn("recyclerview", tokens)
        self.assertIn("主线", tokens)
        self.assertIn("frame_timeline", tokens)
        self.assertIn("timeline", tokens)


class SecurityScanTest(unittest.TestCase):
    def test_secrets_and_local_paths_are_distinguished(self) -> None:
        fatal = scan_public_text(
            "-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----"
        )
        excluded = scan_public_text("/Users/alice/private/source.cc")
        self.assertEqual(fatal[0].severity, "fatal")
        self.assertEqual(excluded[0].severity, "exclude")


class SqlitePackTest(unittest.TestCase):
    def test_pack_database_is_searchable(self) -> None:
        scan = scan_eligible_articles(FIXTURE_ROOT, load_policy())
        with tempfile.TemporaryDirectory(prefix="aiw-pack-test-") as temp_dir:
            database_path = Path(temp_dir) / "content.sqlite"
            identity = {
                "packId": "android-internals",
                "packFormatVersion": 1,
                "contentVersion": "0.0.0-dev",
                "sourceRevision": "0" * 40,
                "contentFingerprint": public_content_fingerprint(scan.accepted),
                "builderVersion": "test",
                "generatedAt": "2026-07-18T00:00:00Z",
                "licenseExpression": "CC-BY-NC-SA-4.0 OR LicenseRef-AIW-Commercial",
            }
            create_pack_database(database_path, scan.accepted, identity)
            connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
            try:
                rows = search_database(connection, "RecyclerView 滑动", 5)
                self.assertEqual(rows[0]["relative_path"], "src/good.md")
                self.assertEqual(
                    connection.execute("PRAGMA quick_check").fetchone()[0],
                    "ok",
                )
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
