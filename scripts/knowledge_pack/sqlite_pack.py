"""Build and query the immutable SQLite/FTS5 Knowledge Pack."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable

from .markdown_chunks import tokenize_search_text
from .models import PackArticle


SCHEMA_VERSION = 1
REQUIRED_TABLES = {
    "pack_manifest",
    "articles",
    "sections",
    "chunks",
    "sources",
    "chunks_fts",
}


def create_pack_database(
    database_path: Path,
    articles: tuple[PackArticle, ...],
    identity: dict[str, Any],
) -> None:
    if database_path.exists():
        database_path.unlink()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    try:
        connection.executescript(
            """
            PRAGMA journal_mode = OFF;
            PRAGMA synchronous = OFF;
            PRAGMA temp_store = MEMORY;
            PRAGMA page_size = 4096;
            PRAGMA auto_vacuum = NONE;
            PRAGMA user_version = 1;

            CREATE TABLE pack_manifest (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            ) WITHOUT ROWID;

            CREATE TABLE articles (
              article_id TEXT PRIMARY KEY,
              relative_path TEXT NOT NULL UNIQUE,
              title TEXT NOT NULL,
              chapter TEXT NOT NULL,
              applicable_versions TEXT NOT NULL,
              confidence TEXT,
              last_verified TEXT,
              last_verified_against TEXT,
              tags_json TEXT NOT NULL,
              file_hash TEXT NOT NULL
            ) WITHOUT ROWID;

            CREATE TABLE sections (
              section_id TEXT PRIMARY KEY,
              article_id TEXT NOT NULL,
              heading TEXT NOT NULL,
              heading_path TEXT NOT NULL,
              level INTEGER NOT NULL,
              start_line INTEGER NOT NULL,
              end_line INTEGER NOT NULL,
              FOREIGN KEY(article_id) REFERENCES articles(article_id)
            ) WITHOUT ROWID;

            CREATE TABLE chunks (
              chunk_id TEXT PRIMARY KEY,
              article_id TEXT NOT NULL,
              section_id TEXT NOT NULL,
              heading TEXT NOT NULL,
              body TEXT NOT NULL,
              start_line INTEGER NOT NULL,
              end_line INTEGER NOT NULL,
              chunk_hash TEXT NOT NULL,
              token_count INTEGER NOT NULL,
              search_tokens TEXT NOT NULL,
              FOREIGN KEY(article_id) REFERENCES articles(article_id),
              FOREIGN KEY(section_id) REFERENCES sections(section_id)
            ) WITHOUT ROWID;

            CREATE TABLE sources (
              article_id TEXT NOT NULL,
              ordinal INTEGER NOT NULL,
              source_type TEXT NOT NULL,
              url TEXT NOT NULL,
              PRIMARY KEY(article_id, ordinal),
              FOREIGN KEY(article_id) REFERENCES articles(article_id)
            ) WITHOUT ROWID;

            CREATE VIRTUAL TABLE chunks_fts USING fts5(
              chunk_id UNINDEXED,
              title,
              heading,
              tags,
              body,
              search_tokens,
              tokenize = 'unicode61 remove_diacritics 2'
            );
            """
        )
        connection.executemany(
            "INSERT INTO pack_manifest(key, value) VALUES (?, ?)",
            [
                (key, json.dumps(value, ensure_ascii=False, separators=(",", ":")))
                for key, value in sorted(identity.items())
            ],
        )
        for article in articles:
            tags_json = json.dumps(
                article.tags,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            connection.execute(
                """
                INSERT INTO articles(
                  article_id, relative_path, title, chapter,
                  applicable_versions, confidence, last_verified,
                  last_verified_against, tags_json, file_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    article.article_id,
                    article.relative_path,
                    article.title,
                    article.chapter,
                    article.applicable_versions,
                    article.confidence,
                    article.last_verified,
                    article.last_verified_against,
                    tags_json,
                    article.file_hash,
                ),
            )
            connection.executemany(
                """
                INSERT INTO sections(
                  section_id, article_id, heading, heading_path, level,
                  start_line, end_line
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        section.section_id,
                        section.article_id,
                        section.heading,
                        section.heading_path,
                        section.level,
                        section.start_line,
                        section.end_line,
                    )
                    for section in article.sections
                ],
            )
            for ordinal, source in enumerate(article.sources):
                connection.execute(
                    """
                    INSERT INTO sources(article_id, ordinal, source_type, url)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        article.article_id,
                        ordinal,
                        source["type"],
                        source["url"],
                    ),
                )
            for chunk in article.chunks:
                connection.execute(
                    """
                    INSERT INTO chunks(
                      chunk_id, article_id, section_id, heading, body,
                      start_line, end_line, chunk_hash, token_count, search_tokens
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk.chunk_id,
                        chunk.article_id,
                        chunk.section_id,
                        chunk.heading,
                        chunk.body,
                        chunk.start_line,
                        chunk.end_line,
                        chunk.chunk_hash,
                        chunk.token_count,
                        chunk.search_tokens,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO chunks_fts(
                      chunk_id, title, heading, tags, body, search_tokens
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk.chunk_id,
                        article.title,
                        chunk.heading,
                        " ".join(article.tags),
                        chunk.body,
                        chunk.search_tokens,
                    ),
                )
        connection.commit()
        connection.execute("VACUUM")
        quick_check = connection.execute("PRAGMA quick_check").fetchone()
        if not quick_check or quick_check[0] != "ok":
            raise ValueError(f"SQLite quick_check failed: {quick_check}")
    finally:
        connection.close()


def query_match_expression(query: str) -> str:
    tokens = tokenize_search_text(query)
    if not tokens:
        return ""
    return " OR ".join(f'"{token.replace(chr(34), chr(34) * 2)}"' for token in tokens)


def search_database(
    connection: sqlite3.Connection,
    query: str,
    limit: int,
) -> list[sqlite3.Row]:
    expression = query_match_expression(query)
    if not expression:
        return []
    connection.row_factory = sqlite3.Row
    return connection.execute(
        """
        SELECT
          c.chunk_id,
          c.article_id,
          a.relative_path,
          a.title,
          c.section_id,
          c.heading,
          c.body,
          c.chunk_hash,
          bm25(chunks_fts, 0.0, 8.0, 5.0, 3.0, 1.0, 2.0) AS rank
        FROM chunks_fts
        JOIN chunks c ON c.chunk_id = chunks_fts.chunk_id
        JOIN articles a ON a.article_id = c.article_id
        WHERE chunks_fts MATCH ?
        ORDER BY rank ASC, c.chunk_id ASC
        LIMIT ?
        """,
        (expression, limit),
    ).fetchall()


def database_identity(connection: sqlite3.Connection) -> dict[str, Any]:
    rows = connection.execute(
        "SELECT key, value FROM pack_manifest ORDER BY key"
    ).fetchall()
    return {str(key): json.loads(str(value)) for key, value in rows}


def database_tables(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
        )
    }


def count_rows(connection: sqlite3.Connection, table_names: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table_name in table_names:
        if table_name not in {"articles", "sections", "chunks", "sources"}:
            raise ValueError(f"unsupported table count: {table_name}")
        counts[table_name] = int(
            connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        )
    return counts
