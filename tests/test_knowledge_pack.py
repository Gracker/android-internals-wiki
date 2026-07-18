"""Focused tests for deterministic Knowledge Pack construction."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest

import yaml

from scripts.knowledge_pack.eligibility import (
    public_content_fingerprint,
    scan_corpus_articles,
)
from scripts.knowledge_pack.frontmatter import (
    DuplicateKeyError,
    parse_article,
)
from scripts.knowledge_pack.markdown_chunks import (
    build_sections_and_chunks,
    stable_article_id,
    tokenize_search_text,
)
from scripts.knowledge_pack.manifest import build_audit_summary
from scripts.knowledge_pack.security_scan import (
    redact_private_context_lines,
    scan_public_text,
)
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


class CorpusInclusionTest(unittest.TestCase):
    def test_workflow_state_and_queue_do_not_gate_body_inclusion(self) -> None:
        result = scan_corpus_articles(FIXTURE_ROOT, load_policy())
        self.assertEqual(
            [article.relative_path for article in result.accepted],
            [
                "src/blocked.md",
                "src/draft.md",
                "src/duplicate.md",
                "src/good.md",
            ],
        )
        qualities = {
            article.relative_path: article.metadata_quality
            for article in result.accepted
        }
        self.assertEqual(qualities["src/draft.md"], "strict")
        self.assertEqual(qualities["src/duplicate.md"], "invalid")
        audit = build_audit_summary(
            result,
            "2026-07-18T00:00:00Z",
            "0" * 40,
        )
        self.assertEqual(
            audit["acceptedWorkflowMetadataCounts"]["status"],
            {"(missing)": 1, "draft": 1, "finalized": 2},
        )
        self.assertEqual(
            audit["acceptedMetadataErrorCounts"],
            {"DuplicateKeyError": 1},
        )

    def test_content_fingerprint_is_stable(self) -> None:
        first = scan_corpus_articles(FIXTURE_ROOT, load_policy())
        second = scan_corpus_articles(FIXTURE_ROOT, load_policy())
        self.assertEqual(
            public_content_fingerprint(first.accepted),
            public_content_fingerprint(second.accepted),
        )

    def test_queue_changes_do_not_change_public_corpus(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aiw-pack-queue-") as temp_dir:
            fixture = Path(temp_dir)
            shutil.copytree(FIXTURE_ROOT, fixture, dirs_exist_ok=True)
            before = scan_corpus_articles(fixture, load_policy())
            queue_path = fixture / "metadata" / "queue.json"
            queue_path.write_text(
                json.dumps([{"status": "blocked", "file": "src/good.md"}]),
                encoding="utf-8",
            )
            after = scan_corpus_articles(fixture, load_policy())

        self.assertEqual(
            public_content_fingerprint(before.accepted),
            public_content_fingerprint(after.accepted),
        )

    def test_closed_malformed_frontmatter_includes_body_with_fallback(self) -> None:
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

            result = scan_corpus_articles(fixture, load_policy())

        malformed_article = next(
            article
            for article in result.accepted
            if article.relative_path == "src/malformed.md"
        )
        self.assertEqual(malformed_article.metadata_quality, "invalid")
        self.assertEqual(malformed_article.title, "malformed")

    def test_unclosed_frontmatter_with_h1_includes_body_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aiw-pack-unclosed-") as temp_dir:
            fixture = Path(temp_dir)
            shutil.copytree(FIXTURE_ROOT, fixture, dirs_exist_ok=True)
            (fixture / "src" / "unclosed.md").write_text(
                "---\ntitle: Unclosed\n# Body that must not include metadata\n\nArticle text.\n",
                encoding="utf-8",
            )
            result = scan_corpus_articles(fixture, load_policy())

        article = next(
            item for item in result.accepted if item.relative_path == "src/unclosed.md"
        )
        self.assertEqual(article.metadata_quality, "invalid")
        self.assertNotIn("title: Unclosed", article.chunks[0].body)
        self.assertEqual(article.chunks[0].heading, "Body that must not include metadata")
        self.assertIn("Article text.", article.chunks[0].body)

    def test_unclosed_frontmatter_without_h1_is_excluded(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aiw-pack-unclosed-empty-") as temp_dir:
            fixture = Path(temp_dir)
            shutil.copytree(FIXTURE_ROOT, fixture, dirs_exist_ok=True)
            (fixture / "src" / "unclosed.md").write_text(
                "---\ntitle: Unclosed\nmetadata only\n",
                encoding="utf-8",
            )
            result = scan_corpus_articles(fixture, load_policy())

        reasons = {entry.relative_path: entry.reason for entry in result.excluded}
        self.assertTrue(reasons["src/unclosed.md"].startswith("body_parse_failed"))

    def test_private_path_redaction_is_public_projection_stable(self) -> None:
        fingerprints: list[str] = []
        for username in ("alice", "bob"):
            with tempfile.TemporaryDirectory(prefix="aiw-pack-redaction-") as temp_dir:
                fixture = Path(temp_dir)
                shutil.copytree(FIXTURE_ROOT, fixture, dirs_exist_ok=True)
                draft_path = fixture / "src" / "draft.md"
                draft_path.write_text(
                    draft_path.read_text(encoding="utf-8")
                    + f"\nPrivate note: /Users/{username}/private/source.md\n",
                    encoding="utf-8",
                )
                result = scan_corpus_articles(fixture, load_policy())
                article = next(
                    item for item in result.accepted if item.relative_path == "src/draft.md"
                )
                self.assertIn("macos_user_path", article.redaction_codes)
                self.assertIn("[REDACTED_PRIVATE_CONTEXT:macos_user_path]", article.chunks[-1].body)
                self.assertFalse(scan_public_text(article.chunks[-1].body))
                fingerprints.append(public_content_fingerprint(result.accepted))
        self.assertEqual(fingerprints[0], fingerprints[1])

    def test_fatal_secret_in_body_aborts_public_build(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aiw-pack-secret-") as temp_dir:
            fixture = Path(temp_dir)
            shutil.copytree(FIXTURE_ROOT, fixture, dirs_exist_ok=True)
            draft_path = fixture / "src" / "draft.md"
            draft_path.write_text(
                draft_path.read_text(encoding="utf-8")
                + "\n-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "fatal secret finding"):
                scan_corpus_articles(fixture, load_policy())

    def test_repository_corpus_includes_every_body_markdown(self) -> None:
        result = scan_corpus_articles(REPO_ROOT, load_policy())
        expected_paths = {
            path.relative_to(REPO_ROOT).as_posix()
            for path in (REPO_ROOT / "src").rglob("*.md")
            if path.name.lower() not in {"readme.md", "summary.md"}
            and "src/graphify-out/" not in path.relative_to(REPO_ROOT).as_posix()
        }
        self.assertEqual(
            {article.relative_path for article in result.accepted},
            expected_paths,
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

    def test_private_context_redaction_preserves_line_count(self) -> None:
        original = "before\n/Users/alice/private/source.cc\nafter\n"
        redacted, codes = redact_private_context_lines(original)
        self.assertEqual(redacted.count("\n"), original.count("\n"))
        self.assertEqual(codes, ("macos_user_path",))
        self.assertFalse(scan_public_text(redacted))


class SqlitePackTest(unittest.TestCase):
    def test_pack_database_is_searchable(self) -> None:
        scan = scan_corpus_articles(FIXTURE_ROOT, load_policy())
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
                article_columns = {
                    row[1]
                    for row in connection.execute("PRAGMA table_info(articles)")
                }
                self.assertNotIn("status", article_columns)
                self.assertNotIn("pipeline_stage", article_columns)
                self.assertEqual(
                    connection.execute(
                        """
                        SELECT COUNT(*)
                        FROM chunks_fts f
                        JOIN chunks c ON c.chunk_rowid = f.rowid
                        """
                    ).fetchone()[0],
                    connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0],
                )
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
