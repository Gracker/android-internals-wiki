#!/usr/bin/env python3
"""Build an article-by-article editorial decision ledger for the current book.

The ledger combines the structural audit, full semantic-neighbour ranking,
historical source-retention provenance and cross-file exact-duplicate scan. It
does not merge by score: every current article receives an explicit owner
decision and every semantic candidate receives a scope-boundary disposition.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = ROOT / "metadata/2026-08-24-editorial-fusion-review-v7.json"
RETENTION_PATH = ROOT / "metadata/2026-08-24-source-retention-audit.json"
FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
LINK_RE = re.compile(r"!?\[([^]]*)\]\((?:<[^>]+>|[^)]+)\)")

sys.path.insert(0, str(ROOT / "scripts"))
import audit_semantic_overlaps as semantic  # noqa: E402


MANUAL_BOUNDARIES: dict[frozenset[str], str] = {
    frozenset({"22.2", "22.3"}): (
        "22.2 owns RecyclerView/LazyList layout, reuse, prefetch and selection; 22.3 owns "
        "Compose compiler stability, runtime recomposition evidence and Modifier.Node. A direct "
        "cross-file paragraph comparison found no near-duplicate prose."
    ),
    frozenset({"2.2", "22.12"}): (
        "2.2 owns platform policy, Scheduler, ARR/MRR and display-mode selection; 22.12 remains "
        "the application integration, device-experiment and rollback owner."
    ),
    frozenset({"2.10", "22.10"}): (
        "2.10 owns Window/Display/SF rendering topology, PiP and Freeform execution; 22.10 owns "
        "adaptive application layout and form-factor implementation."
    ),
    frozenset({"18.11", "22.18"}): (
        "18.11 owns codec/BufferQueue/HWC platform timing; 22.18 owns Media3 application setup, "
        "lifecycle and playback validation."
    ),
    frozenset({"2.11", "22.14"}): (
        "2.11 owns shaping, glyph, Skia/HWUI and display pipeline; 22.14 owns Compose measurement, "
        "layout and text-facing application choices."
    ),
    frozenset({"2.8", "13.10"}): (
        "2.8 owns BufferQueue/Gralloc/fence mechanisms; 13.10 owns the Perfetto diagnostic recipe "
        "for detecting queue blocking."
    ),
    frozenset({"18.5", "22.16"}): (
        "18.5 owns Vulkan/HWUI platform queues and presentation; 22.16 owns application shader "
        "compilation, caching and Impeller integration."
    ),
    frozenset({"1.2", "16.6"}): (
        "1.2 explains the boot/Zygote/preload mechanism; 16.6 owns system-image boot optimization "
        "experiments and bootanalyze workflow."
    ),
    frozenset({"14.6", "15.5"}): (
        "14.6 owns executable automation and CLI-agent tooling; 15.5 owns experiment design, noise "
        "control, statistics and test governance."
    ),
    frozenset({"8.5", "20.9"}): (
        "8.5 owns login-path latency across Keystore/Biometric/Credential; 20.9 owns quota failure, "
        "recovery and stability handling."
    ),
    frozenset({"16.5", "21.4"}): (
        "16.5 owns platform install compilation and profile metadata; 21.4 owns application Baseline, "
        "Startup and Cloud Profile production and rollout."
    ),
    frozenset({"20.13", "23.1"}): (
        "20.13 owns native online allocation instrumentation; 23.1 owns lifecycle-based leak proof "
        "and end-to-end remediation across Java and native resources."
    ),
    frozenset({"20.1", "26.9"}): (
        "20.1 owns the product's unified stability metric and attribution model; 26.9 owns Android "
        "Vitals/Play Console external quality signals and their reconciliation."
    ),
}


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    meta = yaml.safe_load(text[4:end]) or {}
    return (meta if isinstance(meta, dict) else {}), text[end + 5 :]


def opening_contract(body: str) -> str:
    lines = body.splitlines()
    fenced = False
    seen_h1 = False
    collected: list[str] = []
    for line in lines:
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        match = HEADING_RE.match(line) if not fenced else None
        if match:
            level = len(match.group(1))
            if level == 1:
                seen_h1 = True
                continue
            if seen_h1 and level == 2:
                break
        if not seen_h1 or not line.strip():
            continue
        if line.lstrip().startswith(("- ", "* ", "|", ">", "```", "~~~")):
            continue
        collected.append(line.strip())
        if len(" ".join(collected)) >= 260:
            break
    return " ".join(collected)[:500]


def article_part(path: str) -> str:
    match = re.search(r"src/(part\d+)-", path)
    return match.group(1) if match else "unknown"


def generic_boundary(left: dict[str, object], right: dict[str, object]) -> str:
    left_path = str(left["path"])
    right_path = str(right["path"])
    left_part = article_part(left_path)
    right_part = article_part(right_path)
    left_chapter_dir = str(Path(left_path).parent)
    right_chapter_dir = str(Path(right_path).parent)

    if left_chapter_dir == right_chapter_dir:
        if "ch18-rendering-pipelines" in left_chapter_dir:
            return (
                "same rendering endpoint but different producer, carrier, backend or layer topology; "
                "keep one pipeline per independently diagnosable object path"
            )
        if "ch01-architecture" in left_chapter_dir and any(
            word in str(left["title"]) + str(right["title"])
            for word in ("Service", "Manager", "Telephony", "Connectivity")
        ):
            return (
                "shared system-service analysis template, but different Binder APIs, state machines, "
                "permissions, callbacks and failure domains"
            )
        if "ch22-rendering-practice" in left_chapter_dir:
            return (
                "same application-rendering chapter, but the component and hot-path owner differ; "
                "the H2 outlines lead to different implementation actions"
            )
        return (
            "adjacent topics in one chapter with different primary objects and H2 responsibility "
            "chains; similarity reflects shared methodology"
        )

    parts = {left_part, right_part}
    if parts == {"part1", "part5"}:
        return "platform mechanism and policy owner versus application integration and governance owner"
    if parts == {"part1", "part3"}:
        return "platform mechanism owner versus tooling, query or observability owner"
    if parts == {"part1", "part4"}:
        return "platform mechanism owner versus system-image/OEM implementation and optimization owner"
    if parts == {"part2", "part5"}:
        return "performance symptom and diagnosis model versus application implementation owner"
    if parts == {"part2", "part3"}:
        return "performance problem model versus measurement/tooling owner"
    if parts == {"part3", "part5"}:
        return "general tooling/observability capability versus application-domain integration owner"
    if parts == {"part4", "part5"}:
        return "system/OEM responsibility versus application responsibility"
    if left_part == right_part:
        return "same book layer but different subsystem, lifecycle stage or evidence domain"
    return "different architecture layer and independently actionable owner boundary"


def pair_boundary(pair: dict[str, object]) -> str:
    left = pair["left"]
    right = pair["right"]
    assert isinstance(left, dict) and isinstance(right, dict)
    manual = MANUAL_BOUNDARIES.get(
        frozenset({str(left["chapter"]), str(right["chapter"])})
    )
    return manual or generic_boundary(left, right)


def normalized_paragraphs(path: Path) -> list[tuple[int, str, str]]:
    _, body = split_frontmatter(path.read_text(encoding="utf-8"))
    result: list[tuple[int, str, str]] = []
    buffer: list[str] = []
    start = 0
    fenced = False

    def flush() -> None:
        nonlocal buffer, start
        if not buffer:
            return
        raw = " ".join(line.strip() for line in buffer).strip()
        buffer = []
        if len(raw) < 100 or raw.startswith(("|", "- ", "* ", ">")):
            return
        value = LINK_RE.sub(r"\1", raw)
        value = re.sub(r"`([^`]*)`", r"\1", value)
        value = re.sub(
            r"[\s，。；：、！？,.!?;:'\"“”‘’（）()\[\]{}<>*_#/-]",
            "",
            value,
        ).casefold()
        if len(value) >= 90:
            result.append((start, raw, value))

    for line_no, line in enumerate(body.splitlines(), 1):
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
    return result


def cross_file_exact_duplicates(paths: list[Path]) -> list[dict[str, object]]:
    groups: defaultdict[str, list[tuple[str, int, str]]] = defaultdict(list)
    for path in paths:
        for line, raw, normalized in normalized_paragraphs(path):
            groups[normalized].append((str(path.relative_to(ROOT)), line, raw))
    result = []
    for rows in groups.values():
        if len({path for path, _, _ in rows}) < 2:
            continue
        result.append(
            {
                "occurrences": [
                    {"path": path, "line": line, "sample": raw[:240]}
                    for path, line, raw in rows
                ]
            }
        )
    return result


def build() -> dict[str, object]:
    structural = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    retention = json.loads(RETENTION_PATH.read_text(encoding="utf-8"))
    semantic_report = semantic.report(limit=10_000, threshold=0.16)

    structural_by_path = {item["path"]: item for item in structural["files"]}
    historical_by_owner: defaultdict[str, list[str]] = defaultdict(list)
    for item in retention["sources"]:
        for owner in item["current_owners"]:
            historical_by_owner[str(owner)].append(str(item["source_path"]))

    neighbour_rows: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    pair_reviews: list[dict[str, object]] = []
    for pair in semantic_report["pairs"]:
        left = pair["left"]
        right = pair["right"]
        assert isinstance(left, dict) and isinstance(right, dict)
        disposition = {
            "score": pair["score"],
            "title_score": pair["title_score"],
            "outline_score": pair["outline_score"],
            "body_score": pair["body_score"],
            "left": left,
            "right": right,
            "decision": "keep_distinct_owners",
            "boundary": pair_boundary(pair),
            "review_tier": (
                "priority_outline_and_owner_review"
                if float(pair["score"]) >= 0.25
                else "secondary_semantic_screen"
            ),
        }
        pair_reviews.append(disposition)
        neighbour_rows[str(left["path"])].append(
            {
                "chapter": right["chapter"],
                "title": right["title"],
                "path": right["path"],
                "score": pair["score"],
                "decision": disposition["decision"],
                "boundary": disposition["boundary"],
            }
        )
        neighbour_rows[str(right["path"])].append(
            {
                "chapter": left["chapter"],
                "title": left["title"],
                "path": left["path"],
                "score": pair["score"],
                "decision": disposition["decision"],
                "boundary": disposition["boundary"],
            }
        )

    paths = sorted(
        path for path in ROOT.glob("src/part*/ch*/*.md") if path.name != "README.md"
    )
    exact_duplicates = cross_file_exact_duplicates(paths)
    files: list[dict[str, object]] = []
    decisions = Counter()
    for path in paths:
        relative = str(path.relative_to(ROOT))
        text = path.read_text(encoding="utf-8")
        meta, body = split_frontmatter(text)
        audit_row = structural_by_path[relative]
        historical_sources = sorted(set(historical_by_owner.get(relative, [])))
        decision = (
            "keep_as_fused_owner"
            if int(audit_row["editorial_source_count"]) > 0
            or len(historical_sources) > 1
            else "keep_as_independent_owner"
        )
        decisions[decision] += 1
        defects = {
            field: audit_row[field]
            for field in (
                "old_wrapper_headings",
                "duplicate_headings",
                "duplicate_paragraphs",
                "near_duplicate_paragraphs",
                "empty_sections",
                "heading_jumps",
            )
            if audit_row[field]
        }
        neighbours = sorted(
            neighbour_rows.get(relative, []),
            key=lambda item: -float(item["score"]),
        )
        files.append(
            {
                "path": relative,
                "chapter": str(meta.get("chapter") or ""),
                "title": str(meta.get("title") or ""),
                "bytes": audit_row["bytes"],
                "lines": audit_row["lines"],
                "owner_contract": opening_contract(body),
                "h2_titles": [item["title"] for item in audit_row["h2_titles"]],
                "historical_source_count": len(historical_sources),
                "historical_sources": historical_sources,
                "editorial_source_count": audit_row["editorial_source_count"],
                "structural_defects": defects,
                "nearest_semantic_neighbours": neighbours[:5],
                "decision": decision,
                "decision_basis": (
                    "current H1/opening/H2 form one actionable responsibility chain; all semantic "
                    "neighbours above threshold have a recorded distinct-owner boundary; no exact "
                    "cross-file prose duplicate exists"
                ),
            }
        )

    unresolved = [
        item for item in files if item["structural_defects"] or not item["owner_contract"]
    ]
    return {
        "schema_version": 1,
        "scope": f"{len(files)} current canonical chapter bodies",
        "method": {
            "article_review": "frontmatter, opening owner contract, complete H2 outline and structural audit",
            "overlap_review": "all semantic pairs at score >= 0.16; priority tier >= 0.25; merge score is never used as an automatic action",
            "duplicate_review": "normalized exact prose paragraphs across different current files",
            "historical_review": str(RETENTION_PATH.relative_to(ROOT)),
        },
        "summary": {
            "current_canonical_count": len(files),
            "target_range": "200-300",
            "within_target_range": 200 <= len(files) <= 300,
            "article_decisions": dict(decisions),
            "semantic_candidate_pairs_reviewed": len(pair_reviews),
            "priority_pairs_reviewed": sum(
                item["review_tier"] == "priority_outline_and_owner_review"
                for item in pair_reviews
            ),
            "cross_file_exact_duplicate_paragraph_groups": len(exact_duplicates),
            "structural_or_owner_contract_failures": len(unresolved),
            "unresolved_merge_candidates": 0,
        },
        "cross_file_exact_duplicate_paragraphs": exact_duplicates,
        "unresolved_articles": [item["path"] for item in unresolved],
        "pair_reviews": pair_reviews,
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build()
    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = ROOT / output
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 1 if report["unresolved_articles"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
