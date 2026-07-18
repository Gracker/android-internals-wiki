"""Strict YAML frontmatter parsing with duplicate-key rejection."""

from __future__ import annotations

from datetime import date, datetime
import re
from typing import Any

import yaml

from .models import ParsedArticle


FRONTMATTER_PATTERN = re.compile(
    r"\A---[ \t]*\r?\n(?P<yaml>.*?)\r?\n---[ \t]*(?:\r?\n|\Z)",
    re.DOTALL,
)
BODY_H1_PATTERN = re.compile(r"(?m)^#[ \t]+.+$")


class DuplicateKeyError(ValueError):
    """Raised when a YAML mapping contains the same key more than once."""


class StrictSafeLoader(yaml.SafeLoader):
    """PyYAML safe loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: StrictSafeLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise DuplicateKeyError(f"duplicate YAML key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def load_strict_yaml(text: str) -> Any:
    return yaml.load(text, Loader=StrictSafeLoader)


def scalar_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (str, int, float)):
        normalized = str(value).strip()
        return normalized or None
    return None


def parse_article(relative_path: str, raw: str) -> ParsedArticle:
    match = FRONTMATTER_PATTERN.match(raw)
    if not match:
        raise ValueError("missing_or_malformed_frontmatter")
    loaded = load_strict_yaml(match.group("yaml"))
    if not isinstance(loaded, dict):
        raise ValueError("frontmatter_must_be_mapping")
    metadata = {str(key): value for key, value in loaded.items()}
    body = raw[match.end() :]
    body_start_line = raw[: match.end()].count("\n") + 1
    return ParsedArticle(
        relative_path=relative_path,
        metadata=metadata,
        body=body,
        body_start_line=body_start_line,
    )


def parse_corpus_article(relative_path: str, raw: str) -> ParsedArticle:
    """Extract a body even when optional source metadata needs a safe fallback."""

    match = FRONTMATTER_PATTERN.match(raw)
    if match is None:
        if raw.startswith("---\n") or raw.startswith("---\r\n"):
            body_match = BODY_H1_PATTERN.search(raw)
            if body_match is None:
                raise ValueError("unclosed_frontmatter_without_body_heading")
            body = raw[body_match.start() :]
            return ParsedArticle(
                relative_path=relative_path,
                metadata={},
                body=body,
                body_start_line=raw[: body_match.start()].count("\n") + 1,
                metadata_quality="invalid",
                metadata_error="UnclosedFrontmatterFence",
            )
        return ParsedArticle(
            relative_path=relative_path,
            metadata={},
            body=raw,
            body_start_line=1,
            metadata_quality="missing",
        )

    body = raw[match.end() :]
    body_start_line = raw[: match.end()].count("\n") + 1
    try:
        loaded = load_strict_yaml(match.group("yaml"))
        if not isinstance(loaded, dict):
            raise ValueError("frontmatter_must_be_mapping")
        metadata = {str(key): value for key, value in loaded.items()}
    except (ValueError, yaml.YAMLError) as error:
        return ParsedArticle(
            relative_path=relative_path,
            metadata={},
            body=body,
            body_start_line=body_start_line,
            metadata_quality="invalid",
            metadata_error=type(error).__name__,
        )
    return ParsedArticle(
        relative_path=relative_path,
        metadata=metadata,
        body=body,
        body_start_line=body_start_line,
    )
