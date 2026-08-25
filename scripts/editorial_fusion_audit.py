#!/usr/bin/env python3
"""Audit every current canonical article for editorial and structural defects.

The script is read-only. Editorial targets come from the current v3 fusion spec,
its deliberate split outputs, and later reviewed cross-article consolidations.
Historical v2 paths and H2-count heuristics are intentionally not used: neither
describes the current book after chapter reindexing and contextual tail moves.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "metadata/2026-08-24-editorial-fusion-v3.json"
def map_version(path: Path) -> int:
    match = re.search(r"-v(\d+)-map\.json$", path.name)
    return int(match.group(1)) if match else -1


CONSOLIDATION_MAPS = sorted(
    (ROOT / "metadata").glob("2026-08-24-editorial-fusion-v*-map.json"),
    key=map_version,
)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
LINK_RE = re.compile(r"!?\[([^\]]*)\]\((?:<[^>]+>|[^)]+)\)")


@dataclass(frozen=True)
class Heading:
    line: int
    level: int
    title: str


def canonical_bodies() -> list[Path]:
    return sorted(
        path
        for path in ROOT.glob("src/part*/ch*/*.md")
        if path.name != "README.md"
    )


def strip_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 4)
    return text[end + 5 :] if end >= 0 else text


def headings(text: str) -> list[Heading]:
    result: list[Heading] = []
    fenced = False
    for line_no, line in enumerate(strip_frontmatter(text).splitlines(), 1):
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = HEADING_RE.match(line)
        if match:
            result.append(Heading(line_no, len(match.group(1)), match.group(2)))
    return result


def normalize_title(value: str) -> str:
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = LINK_RE.sub(r"\1", value)
    value = re.sub(r"^(?:\d+(?:\.\d+)*|[一二三四五六七八九十]+)[.、：:]\s*", "", value)
    value = re.sub(r"[\s`*_—–:：,，。！？?!（）()《》/·]+", "", value)
    return value.casefold()


def prose_paragraphs(text: str) -> list[tuple[int, str]]:
    body = strip_frontmatter(text)
    lines = body.splitlines()
    paragraphs: list[tuple[int, str]] = []
    buffer: list[str] = []
    start = 0
    fenced = False

    def flush() -> None:
        nonlocal buffer, start
        if not buffer:
            return
        value = " ".join(part.strip() for part in buffer).strip()
        buffer = []
        if len(value) < 48:
            return
        if value.startswith(("#", "|", "- ", "* ", ">", "[")):
            return
        paragraphs.append((start, value))

    for line_no, line in enumerate(lines, 1):
        if FENCE_RE.match(line):
            flush()
            fenced = not fenced
            continue
        if fenced:
            continue
        if not line.strip() or HEADING_RE.match(line):
            flush()
            continue
        if not buffer:
            start = line_no
        buffer.append(line)
    flush()
    return paragraphs


def normalize_paragraph(value: str) -> str:
    value = LINK_RE.sub(r"\1", value)
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"\s+", "", value)
    value = re.sub(r"[，。；：、！？,.!?;:'\"“”‘’（）()\[\]{}<>]", "", value)
    return value.casefold()


def repeated(values: Iterable[tuple[int, str]], normalizer) -> list[dict[str, object]]:
    groups: defaultdict[str, list[tuple[int, str]]] = defaultdict(list)
    for line, value in values:
        key = normalizer(value)
        if key:
            groups[key].append((line, value))
    result = []
    for rows in groups.values():
        if len(rows) < 2:
            continue
        result.append(
            {
                "count": len(rows),
                "lines": [line for line, _ in rows],
                "sample": rows[0][1],
            }
        )
    return sorted(result, key=lambda item: (-int(item["count"]), item["lines"]))


def duplicate_sibling_headings(hs: list[Heading]) -> list[dict[str, object]]:
    """Report repeated headings only when they share one immediate parent.

    Reusing labels such as "版本边界" in two different mechanism sections is
    intentional. Repeating the same label twice under one parent is the useful
    structural defect to flag.
    """

    stack: list[Heading] = []
    groups: defaultdict[tuple[int, int, str], list[Heading]] = defaultdict(list)
    parent_titles: dict[int, str] = {}
    for heading in hs:
        while stack and stack[-1].level >= heading.level:
            stack.pop()
        parent = stack[-1] if stack else None
        parent_line = parent.line if parent else 0
        parent_titles[parent_line] = parent.title if parent else "<document>"
        groups[(parent_line, heading.level, normalize_title(heading.title))].append(heading)
        stack.append(heading)

    result: list[dict[str, object]] = []
    for (parent_line, level, normalized), rows in groups.items():
        if not normalized or len(rows) < 2:
            continue
        result.append(
            {
                "count": len(rows),
                "level": level,
                "parent_line": parent_line,
                "parent_title": parent_titles[parent_line],
                "lines": [row.line for row in rows],
                "sample": rows[0].title,
            }
        )
    return sorted(result, key=lambda item: (-int(item["count"]), item["lines"]))


def empty_sections(text: str, hs: list[Heading]) -> list[dict[str, object]]:
    lines = strip_frontmatter(text).splitlines()
    result = []
    for index, heading in enumerate(hs):
        end = len(lines)
        for candidate in hs[index + 1 :]:
            if candidate.level <= heading.level:
                end = candidate.line - 1
                break
        content = [
            line.strip()
            for line in lines[heading.line:end]
            if line.strip() and not HEADING_RE.match(line)
        ]
        if not content:
            result.append({"line": heading.line, "level": heading.level, "title": heading.title})
    return result


def heading_jumps(hs: list[Heading]) -> list[dict[str, object]]:
    result = []
    previous = 1
    for heading in hs:
        if heading.level > previous + 1:
            result.append(
                {
                    "line": heading.line,
                    "from_level": previous,
                    "to_level": heading.level,
                    "title": heading.title,
                }
            )
        previous = heading.level
    return result


def has_opening_prose(text: str, hs: list[Heading]) -> bool:
    body = strip_frontmatter(text)
    lines = body.splitlines()
    h1 = next((heading for heading in hs if heading.level == 1), None)
    h2 = next((heading for heading in hs if heading.level == 2), None)
    if not h1 or not h2:
        return False
    opening = lines[h1.line : h2.line - 1]
    return any(
        len(line.strip()) >= 24
        and not line.lstrip().startswith(("#", "- ", "* ", ">", "|", "```", "~~~"))
        for line in opening
    )


def near_duplicate_paragraphs(text: str) -> list[dict[str, object]]:
    paragraphs = [
        (line, normalize_paragraph(value), value)
        for line, value in prose_paragraphs(text)
        if len(normalize_paragraph(value)) >= 120
    ]
    result: list[dict[str, object]] = []
    for left in range(len(paragraphs)):
        line_a, norm_a, raw_a = paragraphs[left]
        for right in range(left + 1, len(paragraphs)):
            line_b, norm_b, raw_b = paragraphs[right]
            ratio = min(len(norm_a), len(norm_b)) / max(len(norm_a), len(norm_b))
            if ratio < 0.78:
                continue
            matcher = difflib.SequenceMatcher(None, norm_a, norm_b, autojunk=False)
            if matcher.quick_ratio() < 0.88:
                continue
            score = matcher.ratio()
            if score < 0.88 or norm_a == norm_b:
                continue
            result.append(
                {
                    "lines": [line_a, line_b],
                    "similarity": round(score, 3),
                    "left": raw_a,
                    "right": raw_b,
                }
            )
    return sorted(result, key=lambda item: (-float(item["similarity"]), item["lines"]))


def old_wrapper_titles() -> dict[str, set[str]]:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    result: defaultdict[str, set[str]] = defaultdict(set)
    for target, item in spec.get("targets", {}).items():
        for section in item.get("sections", []):
            result[target].add(str(section["from"]))
    split_outputs = {
        "src/part1-fundamentals/ch01-architecture/05-art-compilation-verification-deoptimization.md": {
            "ART 编译管线与 dex2oat 优化",
            "ART Verifier Quickening 与 dexopt 过滤器性能边界",
            "Android 17 ART 去优化：触发、栈重建与性能诊断",
        },
        "src/part4-system/ch16-aosp/04-autofdo-feedback-directed-optimization.md": {"AutoFDO 反馈导向编译优化"},
        "src/part1-fundamentals/ch01-architecture/24-telephony-service.md": {"Android 17 TelephonyManager 架构、状态传播与性能边界"},
        "src/part1-fundamentals/ch01-architecture/25-connectivity-service.md": {"Android 17 ConnectivityManager：架构、网络选择与性能"},
        "src/part2-performance/ch18-rendering-pipelines/08-flutter-rendering-pipeline.md": {"Android 17 Flutter 渲染管线"},
        "src/part2-performance/ch18-rendering-pipelines/09-compose-rendering-pipeline.md": {"Android 17 Jetpack Compose 渲染管线架构"},
        "src/part5-app/ch22-rendering-practice/18-media3-video-rendering.md": {"Media3 视频播放：渲染管线、帧时序与排障"},
        "src/part5-app/ch22-rendering-practice/19-camerax-rendering.md": {"CameraX：性能边界、配置与排障（Android 15–17）"},
    }
    for target, titles in split_outputs.items():
        result[target].update(titles)
    return dict(result)


OLD_WRAPPERS = old_wrapper_titles()


def editorial_target_map() -> dict[str, list[str]]:
    """Return current target paths and the source sections reviewed into them."""

    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    targets: defaultdict[str, list[str]] = defaultdict(list)
    for target, item in spec.get("targets", {}).items():
        targets[target].extend(str(section["from"]) for section in item.get("sections", []))
    for split in spec.get("splits", []):
        for output in split.get("outputs", []):
            targets[output].extend(sorted(OLD_WRAPPERS.get(output, set())))

    for map_path in CONSOLIDATION_MAPS:
        consolidation_map = json.loads(map_path.read_text(encoding="utf-8"))

        # A later fusion can retire a path that was itself an earlier editorial
        # target. Move its inherited source inventory into every declared owner
        # before chapter reindexing creates a different article at that path.
        merged_by_source: defaultdict[str, list[str]] = defaultdict(list)
        for row in consolidation_map.get("merged_paths", []):
            merged_by_source[str(row["source"])].append(str(row["target"]))
        for source, destinations in merged_by_source.items():
            inherited = targets.pop(source, [])
            for destination in destinations:
                targets[destination].extend(inherited)
                targets[destination].append(f"path:{source}")

        # Consolidation scripts apply merges first and then close numbering
        # gaps. Replaying that order prevents an old article and its successor
        # from being treated as the same canonical target.
        for row in consolidation_map.get("reindexed_paths", []):
            old = str(row["from"])
            new = str(row["to"])
            if old in targets:
                targets[new].extend(targets.pop(old))

    return {
        target: list(dict.fromkeys(editorial_sources))
        for target, editorial_sources in targets.items()
    }


def audit_file(path: Path, editorial_sources: list[str] | None) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    hs = headings(text)
    h2 = [heading for heading in hs if heading.level == 2]
    title_repeats = duplicate_sibling_headings(
        [heading for heading in hs if heading.level >= 2]
    )
    paragraph_repeats = repeated(prose_paragraphs(text), normalize_paragraph)
    body = strip_frontmatter(text)
    relative = str(path.relative_to(ROOT))
    wrapper_hits = [
        {"line": heading.line, "title": heading.title}
        for heading in h2
        if heading.title in OLD_WRAPPERS.get(relative, set())
    ]
    return {
        "path": relative,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "bytes": len(text.encode("utf-8")),
        "lines": text.count("\n") + 1,
        "paragraphs": len(prose_paragraphs(text)),
        "headings": len(hs),
        "h2_count": len(h2),
        "h2_titles": [{"line": item.line, "title": item.title} for item in h2],
        "editorial_source_count": len(editorial_sources or []),
        "editorial_sources": editorial_sources or [],
        "old_wrapper_headings": wrapper_hits,
        "duplicate_headings": title_repeats,
        "duplicate_paragraphs": paragraph_repeats,
        "near_duplicate_paragraphs": near_duplicate_paragraphs(text),
        "empty_sections": empty_sections(text, hs),
        "heading_jumps": heading_jumps(hs),
        "has_opening_prose": has_opening_prose(text, hs),
    }


def build_report() -> dict[str, object]:
    targets = editorial_target_map()
    bodies = canonical_bodies()
    body_paths = {str(path.relative_to(ROOT)) for path in bodies}
    missing_targets = sorted(set(targets) - body_paths)
    files = [audit_file(path, targets.get(str(path.relative_to(ROOT)))) for path in bodies]
    counts = Counter()
    for item in files:
        if item["editorial_source_count"]:
            counts["editorially_reviewed_targets"] += 1
        else:
            counts["independent_targets"] += 1
        if item["old_wrapper_headings"]:
            counts["files_with_old_wrapper_headings"] += 1
        if item["duplicate_headings"]:
            counts["files_with_duplicate_headings"] += 1
        if item["duplicate_paragraphs"]:
            counts["files_with_exact_duplicate_paragraphs"] += 1
        if item["near_duplicate_paragraphs"]:
            counts["files_with_near_duplicate_paragraphs"] += 1
        if item["empty_sections"]:
            counts["files_with_empty_sections"] += 1
        if item["heading_jumps"]:
            counts["files_with_heading_jumps"] += 1
        if not item["has_opening_prose"]:
            counts["files_without_opening_prose"] += 1
    return {
        "schema_version": 2,
        "scope": f"{len(bodies)} canonical chapter bodies",
        "missing_editorial_targets": missing_targets,
        "summary": dict(counts),
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="print the complete JSON report")
    parser.add_argument("--output", help="write the complete JSON report to this path")
    args = parser.parse_args()
    report = build_report()
    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = ROOT / output
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    largest = sorted(report["files"], key=lambda item: int(item["bytes"]), reverse=True)[:20]
    print("\nLargest canonical articles:")
    for item in largest:
        print(
            f'{item["bytes"]:>8} B  {item["lines"]:>5} lines  '
            f'H2={item["h2_count"]:>2}  {item["path"]}'
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
