"""Deterministic Markdown section parsing and chunk construction."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
import unicodedata

from .models import Chunk, Section


TARGET_CHARS = 1_800
HARD_CHARS = 4_000
ATOMIC_BLOCK_MAX_CHARS = 16 * 1024
HEADING_PATTERN = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
FENCE_PATTERN = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")


@dataclass(frozen=True)
class MarkdownBlock:
    kind: str
    text: str
    start_line: int
    end_line: int


@dataclass
class SectionBuilder:
    heading: str
    heading_path: str
    level: int
    start_line: int
    blocks: list[MarkdownBlock]


def stable_article_id(relative_path: str) -> str:
    normalized = unicodedata.normalize("NFKC", relative_path).replace("\\", "/").lower()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]
    return f"aiw-{digest}"


def _stable_section_id(article_id: str, heading_path: str, ordinal: int) -> str:
    identity = f"{article_id}\0{heading_path}\0{ordinal}"
    return f"{article_id}-s-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:16]}"


def _normalized_content(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


def _chunk_hash(text: str) -> str:
    return hashlib.sha256(_normalized_content(text).encode("utf-8")).hexdigest()


def tokenize_search_text(text: str) -> list[str]:
    seen: set[str] = set()
    tokens: list[str] = []

    def add(value: str) -> None:
        normalized = unicodedata.normalize("NFKC", value).lower().strip()
        if not normalized or normalized in seen:
            return
        if len(normalized) < 2 and not _is_han(normalized):
            return
        seen.add(normalized)
        tokens.append(normalized)

    for match in re.finditer(r"[\w]+", unicodedata.normalize("NFKC", text), re.UNICODE):
        value = match.group(0)
        runs: list[tuple[bool, str]] = []
        for character in value:
            han = _is_han(character)
            if runs and runs[-1][0] == han:
                runs[-1] = (han, runs[-1][1] + character)
            else:
                runs.append((han, character))
        for han, run in runs:
            if han:
                if len(run) == 1:
                    add(run)
                for index in range(len(run) - 1):
                    add(run[index : index + 2])
                continue
            add(run)
            for underscore_part in filter(None, run.split("_")):
                expanded = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", underscore_part)
                expanded = re.sub(r"([a-z\d])([A-Z])", r"\1 \2", expanded)
                expanded = re.sub(r"([A-Za-z])(\d)", r"\1 \2", expanded)
                expanded = re.sub(r"(\d)([A-Za-z])", r"\1 \2", expanded)
                for part in expanded.split():
                    add(part)
    return tokens


def _is_han(character: str) -> bool:
    return bool(character) and (
        "\u3400" <= character <= "\u4dbf"
        or "\u4e00" <= character <= "\u9fff"
        or "\uf900" <= character <= "\ufaff"
    )


def _split_oversized_block(block: MarkdownBlock) -> list[MarkdownBlock]:
    if len(block.text) <= ATOMIC_BLOCK_MAX_CHARS:
        return [block]
    lines = block.text.splitlines(keepends=True)
    parts: list[MarkdownBlock] = []
    current: list[str] = []
    current_chars = 0
    current_start = block.start_line
    line_number = block.start_line
    for line in lines:
        if current and current_chars + len(line) > HARD_CHARS:
            parts.append(
                MarkdownBlock(
                    kind=block.kind,
                    text="".join(current).rstrip(),
                    start_line=current_start,
                    end_line=line_number - 1,
                )
            )
            current = []
            current_chars = 0
            current_start = line_number
        current.append(line)
        current_chars += len(line)
        line_number += 1
    if current:
        parts.append(
            MarkdownBlock(
                kind=block.kind,
                text="".join(current).rstrip(),
                start_line=current_start,
                end_line=max(current_start, line_number - 1),
            )
        )
    return parts


def _paragraph_blocks(lines: list[str], start_line: int) -> list[MarkdownBlock]:
    blocks: list[MarkdownBlock] = []
    index = 0
    while index < len(lines):
        if not lines[index].strip():
            index += 1
            continue
        line_number = start_line + index
        fence = FENCE_PATTERN.match(lines[index])
        if fence:
            marker = fence.group(1)
            fence_char = marker[0]
            fence_size = len(marker)
            collected = [lines[index]]
            index += 1
            while index < len(lines):
                collected.append(lines[index])
                if re.match(
                    rf"^[ \t]{{0,3}}{re.escape(fence_char)}{{{fence_size},}}[ \t]*$",
                    lines[index],
                ):
                    index += 1
                    break
                index += 1
            block = MarkdownBlock(
                kind="code",
                text="\n".join(collected).rstrip(),
                start_line=line_number,
                end_line=start_line + index - 1,
            )
            blocks.extend(_split_oversized_block(block))
            continue

        collected = [lines[index]]
        index += 1
        while index < len(lines) and lines[index].strip():
            if FENCE_PATTERN.match(lines[index]) or HEADING_PATTERN.match(lines[index]):
                break
            collected.append(lines[index])
            index += 1
        is_table = (
            len(collected) >= 2
            and "|" in collected[0]
            and re.match(
                r"^[ \t]*\|?[ \t]*:?-{3,}:?[ \t]*(?:\|[ \t]*:?-{3,}:?[ \t]*)+\|?[ \t]*$",
                collected[1],
            )
        )
        block = MarkdownBlock(
            kind="table" if is_table else "paragraph",
            text="\n".join(collected).rstrip(),
            start_line=line_number,
            end_line=start_line + index - 1,
        )
        blocks.extend(_split_oversized_block(block))
    return blocks


def _parse_sections(body: str, body_start_line: int, article_title: str) -> list[SectionBuilder]:
    lines = body.splitlines()
    heading_stack: list[str] = []
    sections: list[SectionBuilder] = [
        SectionBuilder(
            heading=article_title,
            heading_path=article_title,
            level=0,
            start_line=body_start_line,
            blocks=[],
        )
    ]
    paragraph_start = 0

    def flush_until(end_index: int) -> None:
        nonlocal paragraph_start
        if end_index > paragraph_start:
            sections[-1].blocks.extend(
                _paragraph_blocks(
                    lines[paragraph_start:end_index],
                    body_start_line + paragraph_start,
                )
            )
        paragraph_start = end_index

    in_fence = False
    fence_char = ""
    fence_size = 0
    for index, line in enumerate(lines):
        fence = FENCE_PATTERN.match(line)
        if fence:
            marker = fence.group(1)
            if not in_fence:
                in_fence = True
                fence_char = marker[0]
                fence_size = len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_size:
                in_fence = False
            continue
        if in_fence:
            continue
        heading = HEADING_PATTERN.match(line)
        if not heading:
            continue
        flush_until(index)
        level = len(heading.group(1))
        title = heading.group(2).strip()
        heading_stack[level - 1 :] = [title]
        heading_path = " > ".join(heading_stack)
        sections.append(
            SectionBuilder(
                heading=title,
                heading_path=heading_path,
                level=level,
                start_line=body_start_line + index,
                blocks=[],
            )
        )
        paragraph_start = index + 1
    flush_until(len(lines))
    return [section for section in sections if section.blocks]


def build_sections_and_chunks(
    article_id: str,
    article_title: str,
    tags: tuple[str, ...],
    body: str,
    body_start_line: int,
) -> tuple[tuple[Section, ...], tuple[Chunk, ...]]:
    builders = _parse_sections(body, body_start_line, article_title)
    sections: list[Section] = []
    chunks: list[Chunk] = []
    heading_occurrences: dict[str, int] = {}

    for builder in builders:
        ordinal = heading_occurrences.get(builder.heading_path, 0)
        heading_occurrences[builder.heading_path] = ordinal + 1
        section_id = _stable_section_id(article_id, builder.heading_path, ordinal)
        section_end = max(block.end_line for block in builder.blocks)
        sections.append(
            Section(
                section_id=section_id,
                article_id=article_id,
                heading=builder.heading,
                heading_path=builder.heading_path,
                level=builder.level,
                start_line=builder.start_line,
                end_line=section_end,
            )
        )

        current: list[MarkdownBlock] = []
        current_chars = 0

        def emit() -> None:
            nonlocal current, current_chars
            if not current:
                return
            snippet = "\n\n".join(block.text for block in current).strip()
            if not snippet:
                current = []
                current_chars = 0
                return
            content_hash = _chunk_hash(snippet)
            identity = f"{article_id}\0{section_id}\0{content_hash}"
            chunk_id = f"aiw-c-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}"
            token_source = "\n".join(
                [article_title, builder.heading, " ".join(tags), snippet]
            )
            tokens = tokenize_search_text(token_source)
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    article_id=article_id,
                    section_id=section_id,
                    heading=builder.heading,
                    body=snippet,
                    start_line=current[0].start_line,
                    end_line=current[-1].end_line,
                    chunk_hash=content_hash,
                    token_count=max(1, len(tokens)),
                    search_tokens=" ".join(tokens),
                )
            )
            overlap = (
                current[-1]
                if current[-1].kind == "paragraph" and len(current[-1].text) <= 400
                else None
            )
            current = [overlap] if overlap is not None else []
            current_chars = len(overlap.text) if overlap is not None else 0

        for block in builder.blocks:
            projected = current_chars + (2 if current else 0) + len(block.text)
            if current and projected > TARGET_CHARS:
                emit()
            if (
                block.kind == "paragraph"
                and len(block.text) > HARD_CHARS
                and "\n" not in block.text
            ):
                for offset in range(0, len(block.text), HARD_CHARS):
                    part = MarkdownBlock(
                        kind="paragraph",
                        text=block.text[offset : offset + HARD_CHARS],
                        start_line=block.start_line,
                        end_line=block.end_line,
                    )
                    if current:
                        emit()
                    current = [part]
                    current_chars = len(part.text)
                    emit()
                continue
            current.append(block)
            current_chars += (2 if len(current) > 1 else 0) + len(block.text)
        emit()

    return tuple(sections), tuple(chunks)
