#!/usr/bin/env python3
"""Apply the 2026-08-24 second-pass article consolidation.

The YAML plan is the reviewable source of truth.  This script validates that
every canonical article is accounted for, builds merged documents without
dropping member bodies or source metadata, renumbers each chapter, and updates
the active navigation and routing files.

The default mode is read-only.  Pass ``--apply`` only after the dry run passes.
All removed chapter files remain recoverable from Git.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import posixpath
import re
import shutil
import subprocess
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from urllib.parse import unquote

import yaml

from frontmatter_schema import ALLOWED_FIELDS, REQUIRED_FIELDS


ROOT = Path(__file__).resolve().parent.parent
PLAN_PATH = ROOT / "metadata/2026-08-24-content-consolidation-v2.yaml"
CONSOLIDATED_AT = "2026-08-24"
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)
TOP_LEVEL_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*:\s*")
MARKDOWN_LINK_RE = re.compile(
    r"(?P<image>!?)\[(?P<label>[^\]]*)\]\((?P<inside>[^)]+)\)"
)
WIKILINK_RE = re.compile(r"\[\[(?P<target>[^\]|]+)(?:\|(?P<label>[^\]]+))?\]\]")
HEADING_RE = re.compile(r"^(#{1,6})(\s+)(.*)$")
CHAPTER_DIR_RE = re.compile(r"^ch(\d+)-")
NUMBERED_FILE_RE = re.compile(r"^(\d+)-(.*)\.md$")
TITLE_NUMBER_RE = re.compile(r"^\s*\d+(?:\.\d+)+\s+")
EXTERNAL_SCHEMES = ("http://", "https://", "mailto:", "data:", "javascript:")


@dataclass(frozen=True)
class Document:
    rel_path: PurePosixPath
    text: str
    frontmatter_raw: str
    meta: dict[str, Any]
    body: str

    @property
    def name(self) -> str:
        return self.rel_path.name

    @property
    def title(self) -> str:
        value = str(self.meta.get("title") or self.rel_path.stem)
        return TITLE_NUMBER_RE.sub("", value).strip()

    @property
    def chapter_id(self) -> str:
        value = str(self.meta.get("chapter") or "").strip()
        if re.fullmatch(r"\d+\.\d+", value):
            return value
        directory_match = CHAPTER_DIR_RE.match(self.rel_path.parent.name)
        file_match = NUMBERED_FILE_RE.match(self.rel_path.name)
        if directory_match and file_match:
            return f"{int(directory_match.group(1))}.{int(file_match.group(1))}"
        return value


@dataclass
class Unit:
    chapter_dir: PurePosixPath
    chapter_number: str
    title: str
    slug: str
    members: list[Document]
    primary: Document
    original_position: int
    target_index: int = 0
    target_id: str = ""
    target_rel_path: PurePosixPath | None = None
    output_text: str = ""

    @property
    def merged(self) -> bool:
        return len(self.members) > 1


def load_plan() -> dict[str, Any]:
    data = yaml.safe_load(PLAN_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("chapters"), dict):
        raise ValueError(f"Invalid plan: {PLAN_PATH}")
    return data


def split_document(path: Path) -> Document:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"Missing or malformed frontmatter: {path.relative_to(ROOT)}")
    raw = match.group(1).strip("\n")
    meta = yaml.safe_load(raw)
    if not isinstance(meta, dict):
        raise ValueError(f"Frontmatter is not a mapping: {path.relative_to(ROOT)}")
    return Document(
        rel_path=PurePosixPath(path.relative_to(ROOT).as_posix()),
        text=text,
        frontmatter_raw=raw,
        meta=meta,
        body=text[match.end() :],
    )


def file_position(name: str) -> int:
    match = NUMBERED_FILE_RE.match(name)
    if not match:
        raise ValueError(f"Article filename is not continuously numberable: {name}")
    return int(match.group(1))


def flatten_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            try:
                parsed = yaml.safe_load(stripped)
            except yaml.YAMLError:
                parsed = value
            if isinstance(parsed, list):
                return flatten_list(parsed)
    if not isinstance(value, list):
        return [value]
    result: list[Any] = []
    for item in value:
        result.extend(flatten_list(item))
    return result


def unique_values(values: Iterable[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[str] = set()
    for value in values:
        marker = yaml.safe_dump(
            value, allow_unicode=True, sort_keys=True, default_flow_style=True
        ).strip()
        if marker in seen:
            continue
        seen.add(marker)
        result.append(value)
    return result


def normalized_tags(value: Any) -> list[str]:
    """Return scalar tag values, expanding encoded and comma-joined lists."""
    tags: list[str] = []
    for raw in flatten_list(value):
        text = str(raw).strip()
        if not text:
            continue
        parts = [part.strip() for part in text.split(",")]
        tags.extend(part for part in parts if part)
    return unique_values(tags)


def normalized_related_chapters(
    value: Any,
    old_id_to_new: dict[str, str],
) -> list[str]:
    """Normalize relation values to current numeric IDs where possible."""
    related: list[str] = []
    for raw in flatten_list(value):
        text = str(raw).strip()
        if not text:
            continue
        comma_parts = [part.strip() for part in text.split(",")]
        candidates = (
            comma_parts
            if len(comma_parts) > 1
            and all(re.fullmatch(r"\d+\.\d+", part) for part in comma_parts)
            else [text]
        )
        for candidate in candidates:
            match = re.match(r"^(\d+\.\d+)(?:\s+.*)?$", candidate)
            reference = match.group(1) if match else candidate
            related.append(old_id_to_new.get(reference, reference))
    return unique_values(related)


def build_units(plan: dict[str, Any]) -> tuple[list[Unit], dict[str, list[Unit]]]:
    units: list[Unit] = []
    by_chapter: dict[str, list[Unit]] = {}
    seen_global: set[PurePosixPath] = set()

    for directory_value, chapter_plan in plan["chapters"].items():
        chapter_dir = PurePosixPath(directory_value)
        directory = ROOT / chapter_dir
        chapter_match = CHAPTER_DIR_RE.match(directory.name)
        if not chapter_match:
            raise ValueError(f"Cannot derive chapter number from {directory}")
        chapter_number = str(int(chapter_match.group(1)))

        paths = sorted(
            (path for path in directory.glob("*.md") if path.name != "README.md"),
            key=lambda item: file_position(item.name),
        )
        documents = {path.name: split_document(path) for path in paths}
        member_to_group: dict[str, dict[str, Any]] = {}

        for group in chapter_plan.get("merges", []):
            members = group.get("members") or []
            if len(members) < 2:
                raise ValueError(f"Merge group must contain at least two members: {group}")
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(group.get("slug") or "")):
                raise ValueError(f"Invalid output slug: {group.get('slug')!r}")
            for name in members:
                if name not in documents:
                    raise ValueError(f"Planned member does not exist: {chapter_dir / name}")
                if name in member_to_group:
                    raise ValueError(f"Article appears in two groups: {chapter_dir / name}")
                member_to_group[name] = group
            primary_name = group.get("primary", members[0])
            if primary_name not in members:
                raise ValueError(f"Primary is not a group member: {chapter_dir / primary_name}")

        chapter_units: list[Unit] = []
        emitted_groups: set[int] = set()
        for path in paths:
            group = member_to_group.get(path.name)
            if group is None:
                match = NUMBERED_FILE_RE.match(path.name)
                assert match
                doc = documents[path.name]
                chapter_units.append(
                    Unit(
                        chapter_dir=chapter_dir,
                        chapter_number=chapter_number,
                        title=doc.title,
                        slug=match.group(2),
                        members=[doc],
                        primary=doc,
                        original_position=file_position(path.name),
                    )
                )
                continue

            marker = id(group)
            if marker in emitted_groups:
                continue
            member_names = group["members"]
            earliest = min(file_position(name) for name in member_names)
            if file_position(path.name) != earliest:
                continue
            emitted_groups.add(marker)
            member_docs = [documents[name] for name in member_names]
            primary = documents[group.get("primary", member_names[0])]
            chapter_units.append(
                Unit(
                    chapter_dir=chapter_dir,
                    chapter_number=chapter_number,
                    title=str(group["title"]).strip(),
                    slug=str(group["slug"]).strip(),
                    members=member_docs,
                    primary=primary,
                    original_position=earliest,
                )
            )

        chapter_units.sort(key=lambda unit: unit.original_position)
        expected_target = int(chapter_plan["target_count"])
        if len(chapter_units) != expected_target:
            raise ValueError(
                f"{chapter_dir}: calculated {len(chapter_units)} outputs, "
                f"plan requires {expected_target}"
            )

        for index, unit in enumerate(chapter_units, start=1):
            unit.target_index = index
            unit.target_id = f"{chapter_number}.{index}"
            unit.target_rel_path = chapter_dir / f"{index:02d}-{unit.slug}.md"
            if unit.target_rel_path in seen_global:
                raise ValueError(f"Duplicate target path: {unit.target_rel_path}")
            seen_global.add(unit.target_rel_path)

        units.extend(chapter_units)
        by_chapter[str(chapter_dir)] = chapter_units

    expected_current = int(plan["current_chapter_articles"])
    source_count = sum(len(unit.members) for unit in units)
    if source_count != expected_current:
        raise ValueError(f"Plan accounts for {source_count} sources, expected {expected_current}")
    expected_target = int(plan["target_chapter_articles"])
    if len(units) != expected_target:
        raise ValueError(f"Plan builds {len(units)} outputs, expected {expected_target}")
    return units, by_chapter


def assert_modified_sources_are_preserved(units: list[Unit]) -> None:
    commands = [
        ["git", "diff", "--name-only", "--", "src"],
        ["git", "diff", "--cached", "--name-only", "--", "src"],
    ]
    modified: set[str] = set()
    for command in commands:
        result = subprocess.run(
            command, cwd=ROOT, check=True, capture_output=True, text=True
        )
        modified.update(line.strip() for line in result.stdout.splitlines() if line.strip())

    member_to_unit = {
        str(member.rel_path): unit for unit in units for member in unit.members
    }
    for rel in sorted(modified):
        unit = member_to_unit.get(rel)
        if unit is None or not unit.merged:
            continue
        if str(unit.primary.rel_path) != rel:
            raise ValueError(
                f"Modified source {rel} would be absorbed using another frontmatter base. "
                f"Declare it as primary in the plan first."
            )


def dump_field(key: str, value: Any) -> list[str]:
    dumped = yaml.safe_dump(
        {key: value},
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=100000,
    ).rstrip()
    return dumped.splitlines()


def replace_frontmatter_field(raw: str, key: str, value: Any) -> str:
    lines = raw.splitlines()
    start = None
    key_re = re.compile(rf"^{re.escape(key)}:\s*")
    for index, line in enumerate(lines):
        if key_re.match(line):
            start = index
            break
    replacement = dump_field(key, value)
    if start is None:
        if lines and lines[-1].strip():
            lines.extend(replacement)
        else:
            lines[-1:] = replacement
        return "\n".join(lines)

    end = start + 1
    while end < len(lines) and not TOP_LEVEL_KEY_RE.match(lines[end]):
        end += 1
    lines[start:end] = replacement
    return "\n".join(lines)


def remove_frontmatter_field(raw: str, key: str) -> str:
    lines = raw.splitlines()
    start = None
    key_re = re.compile(rf"^{re.escape(key)}:\s*")
    for index, line in enumerate(lines):
        if key_re.match(line):
            start = index
            break
    if start is None:
        return raw

    end = start + 1
    while end < len(lines) and not TOP_LEVEL_KEY_RE.match(lines[end]):
        end += 1
    del lines[start:end]
    return "\n".join(lines).strip("\n")


def set_frontmatter_fields(raw: str, fields: dict[str, Any]) -> str:
    result = raw
    for key, value in fields.items():
        result = replace_frontmatter_field(result, key, value)
    return result


def normalized_sources(members: list[Document]) -> list[dict[str, Any]]:
    current = [
        source
        for member in members
        for source in flatten_list(member.meta.get("sources"))
        if isinstance(source, dict)
    ]
    legacy = [
        {
            "type": "legacy",
            "path": str(source).strip(),
            "availability": (
                "preserved from previous_sources during the 2026-08-24 "
                "frontmatter migration; not treated as current evidence"
            ),
        }
        for member in members
        for source in flatten_list(member.meta.get("previous_sources"))
        if str(source).strip()
    ]
    return unique_values([*current, *legacy])


def migrate_obsolete_frontmatter(
    raw: str,
    members: list[Document],
    primary: Document,
) -> str:
    availability_notes = unique_values(
        str(member.meta.get("consolidated_from_availability") or "").strip()
        for member in members
        if str(member.meta.get("consolidated_from_availability") or "").strip()
    )
    if availability_notes:
        current_note = str(primary.meta.get("note") or "").strip()
        migration_note = "Consolidated-source availability: " + "; ".join(
            availability_notes
        )
        raw = replace_frontmatter_field(
            raw,
            "note",
            f"{current_note}; {migration_note}" if current_note else migration_note,
        )
    for key in ("previous_sources", "consolidated_from_availability"):
        raw = remove_frontmatter_field(raw, key)
    return raw


def select_merged_status(members: list[Document]) -> str:
    statuses = {str(member.meta.get("status") or "").strip() for member in members}
    if "draft" in statuses:
        return "draft"
    if statuses and statuses <= {"finalized", "verified"}:
        return "finalized"
    return "ready-for-review"


def select_merged_pipeline(members: list[Document], status: str) -> str:
    stages = {
        str(member.meta.get("pipeline_stage") or "").strip() for member in members
    }
    if status == "finalized" and stages and stages <= {"ready-to-publish", "publish_ready"}:
        return "ready-to-publish"
    if status == "finalized":
        return "finalized"
    if status == "draft":
        return "task6_pending"
    return "ready-for-review"


def latest_date(members: list[Document], field: str) -> str | None:
    values = [str(member.meta.get(field) or "").strip() for member in members]
    values = [value for value in values if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)]
    return max(values) if values else None


def weakest_confidence(members: list[Document]) -> str | None:
    rank = {"low": 0, "medium-low": 1, "medium": 2, "medium-high": 3, "high": 4}
    values = [str(member.meta.get("confidence") or "").strip() for member in members]
    values = [value for value in values if value in rank]
    return min(values, key=rank.__getitem__) if values else None


def strip_leading_h1(body: str) -> str:
    lines = body.splitlines()
    fenced = False
    for index, line in enumerate(lines):
        if re.match(r"^\s*(```|~~~)", line):
            fenced = not fenced
            continue
        if not fenced and re.match(r"^#\s+", line):
            del lines[index]
            break
        if not fenced and line.strip() and index > 40:
            break
    return "\n".join(lines).strip()


def namespace_notes_and_references(text: str, prefix: str) -> str:
    lines = text.splitlines()
    fenced = False
    labels: list[str] = []
    for line in lines:
        if re.match(r"^\s*(```|~~~)", line):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = re.match(r"^\[([^\]^][^\]]*)\]:\s+", line)
        if match:
            labels.append(match.group(1))

    labels = sorted(set(labels), key=len, reverse=True)

    def transform_plain(segment: str) -> str:
        segment = re.sub(
            r"\[\^([^\]]+)\]",
            lambda match: f"[^{prefix}-{match.group(1)}]",
            segment,
        )
        for label in labels:
            escaped = re.escape(label)
            replacement = f"{prefix}-{label}"
            segment = re.sub(
                rf"(?i)(\]\[){escaped}(\])",
                rf"\1{replacement}\2",
                segment,
            )
            segment = re.sub(
                rf"(?i)\[{escaped}\]\[\]",
                f"[{replacement}][]",
                segment,
            )
        return segment

    result: list[str] = []
    fenced = False
    for line in lines:
        if re.match(r"^\s*(```|~~~)", line):
            fenced = not fenced
            result.append(line)
            continue
        if fenced:
            result.append(line)
            continue
        parts = re.split(r"(`+[^`]*`+)", line)
        line = "".join(
            part if index % 2 else transform_plain(part)
            for index, part in enumerate(parts)
        )
        for label in labels:
            escaped = re.escape(label)
            replacement = f"{prefix}-{label}"
            line = re.sub(
                rf"(?i)^\[{escaped}\](?=:\s+)",
                f"[{replacement}]",
                line,
            )
        result.append(line)
    return "\n".join(result)


def rewrite_headings(
    text: str,
    old_id: str,
    new_id: str,
    *,
    demote: bool,
    strip_old_number: bool,
) -> str:
    lines = text.splitlines()
    fenced = False
    result: list[str] = []
    old_prefix_re = re.compile(
        rf"^(?:§\s*)?{re.escape(old_id)}(?:\.\d+)*(?:[.、]\s*|\s+)"
    ) if old_id else None
    for line in lines:
        if re.match(r"^\s*(```|~~~)", line):
            fenced = not fenced
            result.append(line)
            continue
        match = HEADING_RE.match(line) if not fenced else None
        if not match:
            result.append(line)
            continue
        hashes, spacing, heading = match.groups()
        if old_prefix_re and old_prefix_re.match(heading):
            if strip_old_number:
                heading = old_prefix_re.sub("", heading, count=1)
            else:
                heading = re.sub(
                    rf"^(?:§\s*)?{re.escape(old_id)}",
                    new_id,
                    heading,
                    count=1,
                )
        if demote and len(hashes) < 6:
            hashes += "#"
        result.append(f"{hashes}{spacing}{heading}")
    return "\n".join(result).strip()


def merged_frontmatter(
    unit: Unit,
    old_id_to_new: dict[str, str],
) -> str:
    members = unit.members
    primary = unit.primary
    sources = normalized_sources(members)
    tags = normalized_tags([member.meta.get("tags") for member in members])
    if not tags:
        tags = [unit.slug]
    related = normalized_related_chapters(
        [member.meta.get("related_chapters") for member in members],
        old_id_to_new,
    )
    related = [value for value in related if value != unit.target_id]
    consolidated = unique_values(
        [
            str(value).strip()
            for member in members
            for value in flatten_list(member.meta.get("consolidated_from"))
            if str(value).strip()
        ]
        + [str(member.rel_path) for member in members]
    )
    status = select_merged_status(members)
    fields: dict[str, Any] = {
        "title": unit.title,
        "chapter": unit.target_id,
        "status": status,
        "pipeline_stage": select_merged_pipeline(members, status),
        "tags": tags,
        "related_chapters": related,
        "sources": sources,
        "last_consolidated_at": CONSOLIDATED_AT,
        "consolidated_from": consolidated,
    }
    if "section" in primary.meta:
        fields["section"] = unit.target_id
    date = latest_date(members, "last_verified")
    if date:
        fields["last_verified"] = date
    confidence = weakest_confidence(members)
    if confidence:
        fields["confidence"] = confidence
    raw = set_frontmatter_fields(primary.frontmatter_raw, fields)
    return migrate_obsolete_frontmatter(raw, members, primary)


def singleton_frontmatter(
    unit: Unit,
    old_id_to_new: dict[str, str],
) -> str:
    member = unit.members[0]
    fields: dict[str, Any] = {
        "title": unit.title,
        "chapter": unit.target_id,
    }
    if "section" in member.meta:
        fields["section"] = unit.target_id
    tags = normalized_tags(member.meta.get("tags"))
    fields["tags"] = tags or [unit.slug]
    if "related_chapters" in member.meta:
        related = normalized_related_chapters(
            member.meta.get("related_chapters"), old_id_to_new
        )
        fields["related_chapters"] = [
            value for value in related if value != unit.target_id
        ]
    if "previous_sources" in member.meta:
        fields["sources"] = normalized_sources([member])
    raw = set_frontmatter_fields(member.frontmatter_raw, fields)
    return migrate_obsolete_frontmatter(raw, [member], member)


def build_unit_output(unit: Unit, old_id_to_new: dict[str, str]) -> str:
    if unit.merged:
        frontmatter = merged_frontmatter(unit, old_id_to_new)
        sections: list[str] = []
        for member in unit.members:
            body = strip_leading_h1(member.body)
            prefix = "s" + re.sub(r"[^0-9A-Za-z]+", "-", member.chapter_id).strip("-")
            body = namespace_notes_and_references(body, prefix or member.rel_path.stem)
            body = rewrite_headings(
                body,
                member.chapter_id,
                unit.target_id,
                demote=True,
                strip_old_number=True,
            )
            sections.append(f"## {member.title}\n\n{body}".rstrip())
        body = f"# {unit.title}\n\n" + "\n\n".join(sections) + "\n"
    else:
        member = unit.members[0]
        frontmatter = singleton_frontmatter(unit, old_id_to_new)
        body_without_h1 = strip_leading_h1(member.body)
        body_without_h1 = rewrite_headings(
            body_without_h1,
            member.chapter_id,
            unit.target_id,
            demote=False,
            strip_old_number=False,
        )
        body = f"# {unit.title}\n\n{body_without_h1}\n"
    return f"---\n{frontmatter}\n---\n\n{body}"


def build_maps(
    units: list[Unit],
) -> tuple[
    dict[str, str],
    dict[str, str],
    dict[str, Unit],
    dict[str, tuple[str, str, str]],
]:
    path_map: dict[str, str] = {}
    old_id_to_new: dict[str, str] = {}
    target_to_unit: dict[str, Unit] = {}
    stem_candidates: defaultdict[str, list[tuple[str, str, str]]] = defaultdict(list)

    old_ids: set[str] = set()
    for unit in units:
        assert unit.target_rel_path is not None
        target = str(unit.target_rel_path)
        target_to_unit[target] = unit
        for member in unit.members:
            old = str(member.rel_path)
            path_map[old] = target
            if member.chapter_id:
                if member.chapter_id in old_ids:
                    raise ValueError(f"Duplicate current chapter id: {member.chapter_id}")
                old_ids.add(member.chapter_id)
                old_id_to_new[member.chapter_id] = unit.target_id
            stem_candidates[member.rel_path.stem].append(
                (unit.target_rel_path.stem, unit.target_id, unit.title)
            )

    stem_map = {
        stem: values[0]
        for stem, values in stem_candidates.items()
        if len({value[0] for value in values}) == 1
    }
    return path_map, old_id_to_new, target_to_unit, stem_map


def parse_link_inside(inside: str) -> tuple[str, str]:
    stripped = inside.strip()
    if stripped.startswith("<"):
        close = stripped.find(">")
        if close >= 0:
            return stripped[1:close], stripped[close + 1 :]
    parts = stripped.split(maxsplit=1)
    return parts[0], (" " + parts[1]) if len(parts) == 2 else ""


def resolve_repo_link(doc_rel: PurePosixPath, href: str) -> str | None:
    if not href or href.startswith("#") or href.startswith(EXTERNAL_SCHEMES):
        return None
    clean = href
    if clean.startswith("/"):
        absolute = Path(unquote(clean))
        try:
            return absolute.relative_to(ROOT).as_posix()
        except ValueError:
            return None
    path_part = clean.split("#", 1)[0].split("?", 1)[0]
    if not path_part:
        return None
    return posixpath.normpath(str(doc_rel.parent / unquote(path_part)))


def mapped_href(doc_rel: PurePosixPath, href: str, target_rel: str) -> str:
    suffix = ""
    base = href
    for separator in ("#", "?"):
        if separator in base:
            index = base.find(separator)
            suffix = base[index:] + suffix
            base = base[:index]
    relative = posixpath.relpath(target_rel, start=str(doc_rel.parent))
    return relative + suffix


def rewrite_links(
    text: str,
    doc_rel: PurePosixPath,
    path_map: dict[str, str],
    target_to_unit: dict[str, Unit],
    source_id_by_path: dict[str, str],
    stem_map: dict[str, tuple[str, str, str]],
) -> str:
    def markdown_callback(match: re.Match[str]) -> str:
        label = match.group("label")
        href, title_suffix = parse_link_inside(match.group("inside"))
        resolved = resolve_repo_link(doc_rel, href)
        if resolved not in path_map:
            return match.group(0)
        target = path_map[resolved]
        unit = target_to_unit[target]
        new_href = mapped_href(doc_rel, href, target)
        old_id = source_id_by_path.get(resolved, "")
        stripped_label = label.strip()
        if old_id and (
            stripped_label == old_id
            or stripped_label.startswith(old_id + " ")
            or stripped_label.startswith("§" + old_id)
        ):
            label = f"{unit.target_id} {unit.title}"
        return f"{match.group('image')}[{label}]({new_href}{title_suffix})"

    text = MARKDOWN_LINK_RE.sub(markdown_callback, text)

    def wiki_callback(match: re.Match[str]) -> str:
        target = match.group("target")
        label = match.group("label")
        mapped = stem_map.get(target)
        if not mapped:
            return match.group(0)
        new_stem, new_id, new_title = mapped
        if label and re.match(r"^(?:§)?\d+\.\d+(?:\s|$)", label.strip()):
            label = f"{new_id} {new_title}"
        return f"[[{new_stem}{'|' + label if label else ''}]]"

    return WIKILINK_RE.sub(wiki_callback, text)


def replace_readme_index(text: str, units: list[Unit]) -> str:
    lines = text.splitlines()
    heading_index = None
    for index, line in enumerate(lines):
        if re.match(
            r"^##\s+(?:\d+\.\s*)?(?:内容索引|连续阅读目录|章节目录|章节地图)\s*$",
            line,
        ):
            heading_index = index
            break

    index_lines = [
        f"- [{unit.target_id} {unit.title}]({unit.target_rel_path.name})"
        for unit in units
    ]
    if heading_index is None:
        insert_at = next(
            (index for index, line in enumerate(lines) if line.startswith("## ")),
            len(lines),
        )
        block = ["## 内容索引", "", *index_lines, ""]
        lines[insert_at:insert_at] = block
        return "\n".join(lines).rstrip() + "\n"

    end = heading_index + 1
    while end < len(lines) and not lines[end].startswith("## "):
        end += 1
    replacement = [lines[heading_index], "", *index_lines, ""]
    lines[heading_index:end] = replacement
    return "\n".join(lines).rstrip() + "\n"


def rewrite_chapter_references(text: str, old_id_to_new: dict[str, str]) -> str:
    frontmatter = FRONTMATTER_RE.match(text)
    prefix = text[: frontmatter.end()] if frontmatter else ""
    content = text[frontmatter.end() :] if frontmatter else text
    token_re = re.compile(r"(?<![\w.])(\d{1,2}\.\d{1,2})(?!\d)")
    lines: list[str] = []
    fenced = False
    for line in content.splitlines():
        if re.match(r"^\s*(```|~~~)", line):
            fenced = not fenced
            lines.append(line)
            continue
        if fenced:
            lines.append(line)
            continue
        should_rewrite = bool(
            re.search(
                r"阅读|参阅|另见|详见|章节|小节|相关(?:章节|内容)|§|→|"
                r"见\s*\*{0,2}\s*\d{1,2}\.\d{1,2}|"
                r"\d{1,2}\.\d{1,2}\s*(?:节|章|《|说明|负责|讨论)|"
                r"^\s*-\s*\d{1,2}\.\d{1,2}\s+|"
                r"\*\*\d{1,2}\.\d{1,2}\s+[^*]",
                line,
            )
        )
        if not should_rewrite:
            lines.append(line)
            continue

        protected: list[tuple[int, int]] = []
        for match in re.finditer(r"`+([^`]*)`+", line):
            inline = match.group(1).strip()
            is_chapter_reference = bool(
                re.fullmatch(
                    r"§?\d{1,2}\.\d{1,2}(?:\s*(?:→|、|，|/|～|-|与|和)\s*"
                    r"§?\d{1,2}\.\d{1,2})*",
                    inline,
                )
            )
            if not is_chapter_reference:
                protected.append(match.span())
        for match in MARKDOWN_LINK_RE.finditer(line):
            protected.append(match.span("inside"))
        protected.extend(
            match.span() for match in re.finditer(r"https?://[^\s)>]+", line)
        )

        def callback(match: re.Match[str]) -> str:
            if any(start <= match.start() < end for start, end in protected):
                return match.group(0)
            start = match.start()
            local_prefix = line[max(0, start - 24) : start]
            if re.search(
                r"(?:Android|API|v|Compose|Kotlin|Java|JDK|AGP|Gradle|"
                r"OpenGL|Vulkan|Flutter|Linux|Kernel|HTTP|TLS|SQLite)"
                r"(?:\s+|\s*\*{1,2})$",
                local_prefix,
                re.IGNORECASE,
            ):
                return match.group(0)
            return old_id_to_new.get(match.group(1), match.group(1))

        lines.append(token_re.sub(callback, line))
    return prefix + "\n".join(lines).rstrip() + "\n"


def update_readme_frontmatter(
    text: str,
    chapter_number: str,
    target_count: int,
    old_id_to_new: dict[str, str],
) -> str:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return text
    raw = match.group(1)
    fields: dict[str, Any] = {
        "last_consolidated_at": CONSOLIDATED_AT,
        "consolidation_note": (
            f"第二轮逐篇审阅后收敛为 {target_count} 篇，"
            "合并同一责任链中的总览、机制、版本增量、观测与案例，"
            "并统一连续编号。"
        ),
    }
    meta = yaml.safe_load(raw)
    if isinstance(meta, dict) and "related_chapters" in meta:
        fields["related_chapters"] = normalized_related_chapters(
            meta.get("related_chapters"), old_id_to_new
        )
    raw = set_frontmatter_fields(raw, fields)
    body = text[match.end() :]
    return f"---\n{raw}\n---\n{body}"


def build_summary(original: str, by_chapter: dict[str, list[Unit]]) -> str:
    lines = original.splitlines()
    result: list[str] = []
    index = 0
    chapter_by_readme = {
        posixpath.relpath(f"{chapter_dir}/README.md", start="src"): units
        for chapter_dir, units in by_chapter.items()
    }
    chapter_line_re = re.compile(r"^- \[[^\]]+\]\(([^)]+/README\.md)\)\s*$")
    while index < len(lines):
        line = lines[index]
        match = chapter_line_re.match(line)
        units = chapter_by_readme.get(match.group(1)) if match else None
        if units is None:
            result.append(line)
            index += 1
            continue
        result.append(line)
        for unit in units:
            assert unit.target_rel_path is not None
            href = posixpath.relpath(str(unit.target_rel_path), start="src")
            result.append(f"  - [{unit.target_id} {unit.title}]({href})")
        index += 1
        while index < len(lines) and lines[index].startswith("  - "):
            index += 1
    return "\n".join(result).rstrip() + "\n"


def update_active_json(
    path_map: dict[str, str],
    old_id_to_new: dict[str, str],
    target_to_unit: dict[str, Unit],
) -> dict[Path, str]:
    updates: dict[Path, str] = {}

    queue_path = ROOT / "metadata/queue.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    for entry in queue:
        old_target = entry.get("target_path")
        if old_target in path_map:
            new_target = path_map[old_target]
            unit = target_to_unit[new_target]
            entry["target_path"] = new_target
            if entry.get("section") in old_id_to_new:
                entry["section"] = old_id_to_new[entry["section"]]
            if entry.get("chapter") in old_id_to_new:
                entry["chapter"] = old_id_to_new[entry["chapter"]]
            if entry.get("status") in {"body-applied", "review-finalized"}:
                entry["title"] = unit.title
        if entry.get("mapped_to") in path_map:
            entry["mapped_to"] = path_map[entry["mapped_to"]]
    updates[queue_path] = json.dumps(queue, ensure_ascii=False, indent=2) + "\n"

    source_path = ROOT / "metadata/source-index.json"
    source_index = json.loads(source_path.read_text(encoding="utf-8"))
    for entry in source_index.get("files", []):
        old_target = entry.get("target_path")
        if old_target not in path_map:
            continue
        new_target = path_map[old_target]
        unit = target_to_unit[new_target]
        entry["target_path"] = new_target
        if entry.get("section") in old_id_to_new:
            entry["section"] = old_id_to_new[entry["section"]]
        entry["canonical_target_chapter"] = f"ch{int(unit.chapter_number):02d}"
    updates[source_path] = json.dumps(source_index, ensure_ascii=False, indent=2) + "\n"

    findings_path = ROOT / "metadata/review-findings.json"
    findings = json.loads(findings_path.read_text(encoding="utf-8"))
    for finding in findings.get("findings", []):
        if finding.get("status") != "open":
            continue
        chapter = finding.get("chapter")
        if chapter in path_map:
            finding["chapter"] = path_map[chapter]
        elif chapter in old_id_to_new:
            finding["chapter"] = old_id_to_new[chapter]
    updates[findings_path] = json.dumps(findings, ensure_ascii=False, indent=2) + "\n"
    return updates


def build_progress(
    units: list[Unit],
    summary: str,
    output_by_path: dict[str, str],
    queue_text: str,
) -> str:
    status_counts: Counter[str] = Counter()
    pipeline_counts: Counter[str] = Counter()
    chapter_counts: Counter[str] = Counter()
    for unit in units:
        assert unit.target_rel_path is not None
        document_text = output_by_path[str(unit.target_rel_path)]
        match = FRONTMATTER_RE.match(document_text)
        assert match
        meta = yaml.safe_load(match.group(1))
        status_counts[str(meta.get("status") or "unspecified")] += 1
        pipeline_counts[str(meta.get("pipeline_stage") or "unspecified")] += 1
        chapter_counts[unit.chapter_number] += 1

    queue = json.loads(queue_text)
    queue_counts = Counter(str(entry.get("status") or "unspecified") for entry in queue)
    local_links = 0
    for match in MARKDOWN_LINK_RE.finditer(summary):
        href, _ = parse_link_inside(match.group("inside"))
        if not href.startswith(EXTERNAL_SCHEMES) and not href.startswith("#"):
            local_links += 1

    progress = {
        "schema_version": 3,
        "scope": (
            "Canonical chapter bodies under the 26 directories defined by "
            "metadata/v1.0-definition.md; README, SUMMARY, preface and appendix are excluded."
        ),
        "total": len(units),
        "draft": status_counts.get("draft", 0),
        "ready-for-review": status_counts.get("ready-for-review", 0),
        "finalized": status_counts.get("finalized", 0),
        "needs-review": status_counts.get("needs-review", 0),
        "verified": status_counts.get("verified", 0),
        "outdated": status_counts.get("outdated", 0),
        "ready_to_publish": pipeline_counts.get("ready-to-publish", 0),
        "status_counts": dict(sorted(status_counts.items())),
        "pipeline_stage_counts": dict(sorted(pipeline_counts.items())),
        "chapter_article_counts": {
            str(number): chapter_counts[str(number)]
            for number in sorted(map(int, chapter_counts))
        },
        "summary_local_links": local_links,
        "queue_snapshot": {
            "total": len(queue),
            **dict(sorted(queue_counts.items())),
        },
        "last_updated": datetime.now().astimezone().isoformat(timespec="seconds"),
        "last_action": (
            "second-pass content consolidation: 454 canonical chapter bodies reduced "
            "to 285 after a complete article-level review; merged overview, mechanism, "
            "version delta, observability and case fragments within shared responsibility chains"
        ),
        "generated_from": "chapter frontmatter and src/SUMMARY.md",
    }
    return json.dumps(progress, ensure_ascii=False, indent=2) + "\n"


def validate_outputs(
    units: list[Unit],
    outputs: dict[str, str],
    by_chapter: dict[str, list[Unit]],
) -> None:
    if len(outputs) != len(units):
        raise ValueError(f"Built {len(outputs)} outputs for {len(units)} units")
    for target, text in outputs.items():
        match = FRONTMATTER_RE.match(text)
        if not match:
            raise ValueError(f"Generated frontmatter is malformed: {target}")
        meta = yaml.safe_load(match.group(1))
        if not isinstance(meta, dict):
            raise ValueError(f"Generated frontmatter is not a mapping: {target}")
        for field in REQUIRED_FIELDS:
            if field not in meta:
                raise ValueError(f"Generated article {target} is missing {field}")
        obsolete = sorted(str(field) for field in meta if field not in ALLOWED_FIELDS)
        if obsolete:
            raise ValueError(
                f"Generated article {target} has obsolete frontmatter fields: "
                + ", ".join(obsolete)
            )
        tags = meta.get("tags")
        if (
            not isinstance(tags, list)
            or not tags
            or any(not isinstance(tag, str) or not tag.strip() for tag in tags)
        ):
            raise ValueError(
                f"Generated article {target} tags must be a non-empty string list"
            )
        related = meta.get("related_chapters")
        if related is not None and (
            not isinstance(related, list)
            or any(
                not isinstance(reference, str) or not reference.strip()
                for reference in related
            )
        ):
            raise ValueError(
                f"Generated article {target} related_chapters must be a string list"
            )
        sources = meta.get("sources")
        if sources is not None:
            if not isinstance(sources, list):
                raise ValueError(f"Generated article {target} sources is not a list")
            for index, source in enumerate(sources):
                if not isinstance(source, dict):
                    raise ValueError(
                        f"Generated article {target} sources[{index}] is not a mapping"
                    )
                if not str(source.get("type") or "").strip():
                    raise ValueError(
                        f"Generated article {target} sources[{index}] has no type"
                    )
                if not str(source.get("path") or "").strip():
                    raise ValueError(
                        f"Generated article {target} sources[{index}] has no path"
                    )
        h1_count = 0
        fenced = False
        for line in text.splitlines():
            if re.match(r"^\s*(```|~~~)", line):
                fenced = not fenced
            elif not fenced and line.startswith("# "):
                h1_count += 1
        if h1_count != 1:
            raise ValueError(f"Generated article must contain exactly one H1: {target}")

    for chapter_dir, chapter_units in by_chapter.items():
        actual = [
            target for target in outputs if str(PurePosixPath(target).parent) == chapter_dir
        ]
        if len(actual) != len(chapter_units):
            raise ValueError(f"Generated chapter count mismatch: {chapter_dir}")


def build_all(
    plan: dict[str, Any],
) -> tuple[
    list[Unit],
    dict[str, list[Unit]],
    dict[str, str],
    dict[Path, str],
    str,
]:
    units, by_chapter = build_units(plan)
    assert_modified_sources_are_preserved(units)
    path_map, old_id_to_new, target_to_unit, stem_map = build_maps(units)
    source_id_by_path = {
        str(member.rel_path): member.chapter_id for unit in units for member in unit.members
    }

    outputs: dict[str, str] = {}
    for unit in units:
        assert unit.target_rel_path is not None
        output = build_unit_output(unit, old_id_to_new)
        output = rewrite_chapter_references(output, old_id_to_new)
        output = rewrite_links(
            output,
            unit.target_rel_path,
            path_map,
            target_to_unit,
            source_id_by_path,
            stem_map,
        )
        unit.output_text = output
        outputs[str(unit.target_rel_path)] = output
    validate_outputs(units, outputs, by_chapter)

    auxiliary_updates: dict[Path, str] = {}
    for chapter_dir, chapter_units in by_chapter.items():
        readme_path = ROOT / chapter_dir / "README.md"
        readme_rel = PurePosixPath(readme_path.relative_to(ROOT).as_posix())
        text = readme_path.read_text(encoding="utf-8")
        text = rewrite_chapter_references(text, old_id_to_new)
        text = rewrite_links(
            text,
            readme_rel,
            path_map,
            target_to_unit,
            source_id_by_path,
            stem_map,
        )
        text = replace_readme_index(text, chapter_units)
        text = update_readme_frontmatter(
            text,
            chapter_units[0].chapter_number,
            len(chapter_units),
            old_id_to_new,
        )
        auxiliary_updates[readme_path] = text

    for path in sorted((ROOT / "src").rglob("*.md")):
        rel = PurePosixPath(path.relative_to(ROOT).as_posix())
        if str(rel) in path_map or path in auxiliary_updates or path.name == "SUMMARY.md":
            continue
        text = path.read_text(encoding="utf-8")
        text = rewrite_chapter_references(text, old_id_to_new)
        rewritten = rewrite_links(
            text,
            rel,
            path_map,
            target_to_unit,
            source_id_by_path,
            stem_map,
        )
        if rewritten != text:
            auxiliary_updates[path] = rewritten

    summary_path = ROOT / "src/SUMMARY.md"
    summary = build_summary(summary_path.read_text(encoding="utf-8"), by_chapter)
    auxiliary_updates[summary_path] = summary

    json_updates = update_active_json(path_map, old_id_to_new, target_to_unit)
    auxiliary_updates.update(json_updates)
    path_records = []
    for old_path, target_path in sorted(path_map.items()):
        unit = target_to_unit[target_path]
        path_records.append(
            {
                "source_path": old_path,
                "source_chapter": source_id_by_path[old_path],
                "target_path": target_path,
                "target_chapter": unit.target_id,
                "target_title": unit.title,
                "disposition": (
                    "merged"
                    if unit.merged
                    else "retained"
                    if old_path == target_path
                    else "renumbered"
                ),
            }
        )
    map_report = {
        "schema_version": 1,
        "reviewed_at": CONSOLIDATED_AT,
        "plan": str(PLAN_PATH.relative_to(ROOT)),
        "source_count": len(path_records),
        "target_count": len(units),
        "paths": path_records,
    }
    auxiliary_updates[
        ROOT / "metadata/2026-08-24-content-consolidation-v2-map.json"
    ] = json.dumps(map_report, ensure_ascii=False, indent=2) + "\n"
    progress = build_progress(
        units,
        summary,
        outputs,
        json_updates[ROOT / "metadata/queue.json"],
    )
    auxiliary_updates[ROOT / "metadata/progress.json"] = progress
    return units, by_chapter, outputs, auxiliary_updates, summary


def apply_outputs(
    units: list[Unit],
    outputs: dict[str, str],
    auxiliary_updates: dict[Path, str],
) -> None:
    with tempfile.TemporaryDirectory(prefix="aiw-consolidation-v2-") as temp_value:
        temp_root = Path(temp_value)
        for rel, text in outputs.items():
            target = temp_root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8", newline="\n")

        chapter_dirs = sorted({unit.chapter_dir for unit in units}, key=str)
        for chapter_dir in chapter_dirs:
            directory = ROOT / chapter_dir
            for path in directory.glob("*.md"):
                if path.name != "README.md":
                    path.unlink()
        for rel in sorted(outputs):
            source = temp_root / rel
            target = ROOT / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)

    for path, text in auxiliary_updates.items():
        path.write_text(text, encoding="utf-8", newline="\n")


def print_report(
    plan: dict[str, Any],
    units: list[Unit],
    by_chapter: dict[str, list[Unit]],
    outputs: dict[str, str],
    auxiliary_updates: dict[Path, str],
    summary: str,
    apply: bool,
) -> None:
    source_count = sum(len(unit.members) for unit in units)
    merged_groups = sum(1 for unit in units if unit.merged)
    output_chars = sum(len(text) for text in outputs.values())
    source_chars = sum(len(member.text) for unit in units for member in unit.members)
    largest = sorted(
        ((len(text), rel) for rel, text in outputs.items()), reverse=True
    )[:5]
    print(f"mode: {'APPLY' if apply else 'DRY RUN'}")
    print(f"sources: {source_count}")
    print(f"outputs: {len(units)}")
    print(f"merged groups: {merged_groups}")
    print(f"book articles including preface/appendix: {len(units) + 13}")
    print(f"source chars: {source_chars}")
    print(f"output chars: {output_chars}")
    print(f"auxiliary files to update: {len(auxiliary_updates)}")
    print(f"SUMMARY local links: {len(MARKDOWN_LINK_RE.findall(summary))}")
    print("chapter counts:")
    for chapter_dir, chapter_units in by_chapter.items():
        planned = plan["chapters"][chapter_dir]["target_count"]
        print(f"  {PurePosixPath(chapter_dir).name}: {len(chapter_units)}/{planned}")
    print("largest outputs:")
    for size, rel in largest:
        print(f"  {size:7d} {rel}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the validated consolidation; default is read-only dry run.",
    )
    args = parser.parse_args()
    plan = load_plan()
    units, by_chapter, outputs, auxiliary_updates, summary = build_all(plan)
    print_report(
        plan, units, by_chapter, outputs, auxiliary_updates, summary, args.apply
    )
    if args.apply:
        apply_outputs(units, outputs, auxiliary_updates)
        print("consolidation applied")
    else:
        print("dry run passed; no files changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
