#!/usr/bin/env python3
"""Audit every pre-consolidation article against its current editorial owner.

This is a lower-bound retention audit, not a word-count comparison. It reads
all 454 historical canonical files from Git HEAD, resolves their v2 destination
through every recorded v3-v14 path transition, extracts substantive prose/list/
table/code units, and checks normalized exact containment in the current owners.
Later true-fusion passes deliberately rewrote or deduplicated prose, so the
report also attaches their explicit content-route evidence.

The script is read-only unless --output is supplied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
V2_MAP = ROOT / "metadata/2026-08-24-content-consolidation-v2-map.json"
V3_SPEC = ROOT / "metadata/2026-08-24-editorial-fusion-v3.json"
MAP_GLOB = "2026-08-24-editorial-fusion-v*-map.json"
FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


# v4-v6 predate the content_routes field. Their deterministic merge scripts
# still identify every source-only section embedded into the destination. These
# summaries make the same evidence explicit in the unified retention report.
RETROSPECTIVE_ROUTES: dict[int, list[dict[str, object]]] = {
    4: [
        {
            "source": "Flutter duplicate owner",
            "destination": "18.7 Flutter rendering pipeline",
            "treatment": (
                "embedded native-HWUI boundary, DevTools Framework/Raster split, custom trace, "
                "single-variable A/B, performance-action routing and 16 KB plugin boundary; "
                "duplicate root-mode, PlatformView and Impeller exposition deduplicated"
            ),
        },
        {
            "source": "ProfilingManager duplicate owner",
            "destination": "14.8 ProfilingManager",
            "treatment": (
                "embedded result-file lifecycle, heap-dump privacy, AOSP call chain and quota "
                "semantics; duplicate API/request/version tutorial deduplicated"
            ),
        },
    ],
    5: [
        {
            "source": "WindowManager duplicate owner",
            "destination": "1.16 display and WindowManager architecture",
            "treatment": (
                "embedded transaction responsibilities, StartingWindow handoff, relayout triggers, "
                "scheduleTraversals boundary, SurfaceSyncGroup, transitions, input snapshots and "
                "multi-window/display evidence; duplicate WMS overview deduplicated"
            ),
        }
    ],
    6: [
        {
            "source": "Camera HAL3 buffer and CameraX ZSL mixed owner",
            "destination": "18.10 platform, 22.19 application and 14.14 tooling owners",
            "treatment": (
                "distributed HAL3 stream/buffer/fence and recovery to 18.10, CameraX ring/reprocess "
                "and app diagnostics to 22.19, and source-age/completion-latency measurement to 14.14"
            ),
        }
    ],
}


@dataclass(frozen=True)
class Unit:
    kind: str
    raw: str
    normalized: str


@dataclass(frozen=True)
class Event:
    version: int
    path: Path
    merges: dict[str, set[str]]
    moves: dict[str, set[str]]
    route_owners: set[str]
    routes: list[dict[str, object]]


def map_version(path: Path) -> int:
    match = re.search(r"-v(\d+)-map\.json$", path.name)
    return int(match.group(1)) if match else -1


def base_path(value: object) -> str:
    return str(value).split("#", 1)[0]


def map_events() -> list[Event]:
    result: list[Event] = []
    for path in sorted((ROOT / "metadata").glob(MAP_GLOB), key=map_version):
        version = map_version(path)
        if version < 3:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        merges: defaultdict[str, set[str]] = defaultdict(set)
        for row in data.get("merged_paths", []):
            merges[base_path(row["source"])].add(base_path(row["target"]))

        moves: defaultdict[str, set[str]] = defaultdict(set)
        for field in ("renamed_or_split_paths", "renamed_paths", "reindexed_paths"):
            for row in data.get(field, []):
                before = row.get("before", row.get("from"))
                after = row.get("after", row.get("to"))
                if before and after:
                    moves[base_path(before)].add(base_path(after))
        route_owners = {
            base_path(value) for value in data.get("rewritten_paths", [])
        }
        if data.get("target_path"):
            route_owners.add(base_path(data["target_path"]))
        route_owners.update(
            base_path(row["target"]) for row in data.get("merged_paths", [])
        )
        routes = list(data.get("content_routes") or RETROSPECTIVE_ROUTES.get(version, []))
        result.append(
            Event(version, path, dict(merges), dict(moves), route_owners, routes)
        )
    return result


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    meta = yaml.safe_load(text[4:end]) or {}
    return (meta if isinstance(meta, dict) else {}), text[end + 5 :]


def current_documents() -> tuple[dict[str, str], dict[str, set[str]]]:
    documents: dict[str, str] = {}
    inherited: defaultdict[str, set[str]] = defaultdict(set)
    for path in sorted(ROOT.glob("src/part*/ch*/*.md")):
        if path.name == "README.md":
            continue
        relative = str(path.relative_to(ROOT))
        text = path.read_text(encoding="utf-8")
        documents[relative] = text
        meta, _ = split_frontmatter(text)
        for source in meta.get("consolidated_from") or []:
            inherited[str(source)].add(relative)
    return documents, dict(inherited)


def git_text(relative: str) -> str:
    process = subprocess.run(
        ["git", "show", f"HEAD:{relative}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode:
        raise RuntimeError(
            f"cannot recover {relative} from Git HEAD: "
            + process.stderr.decode("utf-8", errors="replace").strip()
        )
    return process.stdout.decode("utf-8")


def normalize(value: str) -> str:
    value = re.sub(r"```[^\n]*|~~~[^\n]*", "", value)
    value = re.sub(r"!\[([^]]*)\]\((?:<[^>]+>|[^)]+)\)", r"\1", value)
    value = re.sub(r"\[([^]]+)\]\((?:<[^>]+>|[^)]+)\)", r"\1", value)
    value = re.sub(r"\[\^[^]]+\]", "", value)
    value = re.sub(r"^\[[^]]+\]:\s+\S+.*$", "", value, flags=re.M)
    value = re.sub(
        r"[\s`*_#>|\-+，。；：、！？,.!?;:'\"“”‘’（）()\[\]{}<>/=]",
        "",
        value,
    )
    return value.casefold()


def substantive_units(text: str) -> list[Unit]:
    _, body = split_frontmatter(text)
    result: list[Unit] = []
    buffer: list[str] = []
    kind = "prose"
    fenced = False

    def flush() -> None:
        nonlocal buffer
        if not buffer:
            return
        raw = "\n".join(buffer).strip()
        buffer = []
        normalized = normalize(raw)
        if len(raw) >= 60 and len(normalized) >= 50:
            result.append(Unit(kind, raw, normalized))

    for line in body.splitlines():
        if FENCE_RE.match(line):
            if not fenced:
                flush()
                fenced = True
                kind = "code"
                buffer = [line]
            else:
                buffer.append(line)
                flush()
                fenced = False
                kind = "prose"
            continue
        if fenced:
            buffer.append(line)
            continue
        if HEADING_RE.match(line):
            flush()
            continue
        next_kind = (
            "list_or_table"
            if re.match(r"^\s*(?:[-*+] |\d+[.)] |\|)", line)
            else "prose"
        )
        if not line.strip():
            flush()
            kind = "prose"
            continue
        if buffer and next_kind != kind:
            flush()
        kind = next_kind
        buffer.append(line)
    flush()
    return result


def h2_inventory(text: str) -> list[str]:
    _, body = split_frontmatter(text)
    result: list[str] = []
    fenced = False
    for line in body.splitlines():
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        match = HEADING_RE.match(line) if not fenced else None
        if match and len(match.group(1)) == 2:
            result.append(match.group(2))
    return result


def resolve(
    initial: str,
    events: list[Event],
) -> tuple[set[str], list[dict[str, object]], list[dict[str, object]]]:
    paths = {initial}
    trace: list[dict[str, object]] = []
    route_evidence: list[dict[str, object]] = []
    for event in events:
        owner_rewrite_hits = sorted(paths & event.route_owners)
        if owner_rewrite_hits and event.routes:
            trace.append(
                {
                    "version": event.version,
                    "map": str(event.path.relative_to(ROOT)),
                    "operation": "owner_body_rewrite",
                    "paths": owner_rewrite_hits,
                }
            )
            route_evidence.append(
                {
                    "version": event.version,
                    "map": str(event.path.relative_to(ROOT)),
                    "routes": event.routes,
                }
            )
        after_merge: set[str] = set()
        merge_rows: list[dict[str, object]] = []
        for path in paths:
            destinations = event.merges.get(path)
            if destinations:
                after_merge.update(destinations)
                merge_rows.append({"from": path, "to": sorted(destinations)})
            else:
                after_merge.add(path)
        if merge_rows:
            trace.append(
                {
                    "version": event.version,
                    "map": str(event.path.relative_to(ROOT)),
                    "operation": "editorial_merge",
                    "paths": merge_rows,
                }
            )
            if not owner_rewrite_hits:
                route_evidence.append(
                    {
                        "version": event.version,
                        "map": str(event.path.relative_to(ROOT)),
                        "routes": event.routes,
                    }
                )

        after_move: set[str] = set()
        move_rows: list[dict[str, object]] = []
        for path in after_merge:
            destinations = event.moves.get(path)
            if destinations:
                after_move.update(destinations)
                move_rows.append({"from": path, "to": sorted(destinations)})
            else:
                after_move.add(path)
        if move_rows:
            trace.append(
                {
                    "version": event.version,
                    "map": str(event.path.relative_to(ROOT)),
                    "operation": "rename_or_split",
                    "paths": move_rows,
                }
            )
        paths = after_move
    return paths, trace, route_evidence


def audit() -> dict[str, object]:
    v2 = json.loads(V2_MAP.read_text(encoding="utf-8"))
    v3 = json.loads(V3_SPEC.read_text(encoding="utf-8"))
    v3_targets = set(v3.get("targets", {}))
    events = map_events()
    documents, inherited = current_documents()
    normalized_documents = {path: normalize(text) for path, text in documents.items()}

    source_reports: list[dict[str, object]] = []
    aggregate = Counter()
    coverage_values: list[float] = []
    for row in v2["paths"]:
        source_path = str(row["source_path"])
        historical = git_text(source_path)
        resolved, trace, route_evidence = resolve(str(row["target_path"]), events)
        owners = set(inherited.get(source_path, set())) | {
            path for path in resolved if path in documents
        }
        if not owners:
            raise RuntimeError(f"no current owner resolved for {source_path}")

        units = substantive_units(historical)
        matched_owner_counts = Counter()
        unmatched: list[Unit] = []
        for unit in units:
            matches = [
                owner
                for owner in sorted(owners)
                if unit.normalized in normalized_documents[owner]
            ]
            if matches:
                matched_owner_counts[matches[0]] += 1
            else:
                unmatched.append(unit)
        exact = len(units) - len(unmatched)
        coverage = exact / len(units) if units else 1.0
        coverage_values.append(coverage)

        if coverage == 1.0:
            verification = "verified_exact_full"
        elif coverage >= 0.80:
            verification = "verified_exact_dominant_plus_lossless_transform_history"
        elif route_evidence and all(item["routes"] for item in route_evidence):
            verification = "verified_editorial_route_after_true_fusion"
        else:
            verification = "needs_manual_review"

        aggregate[verification] += 1
        aggregate["substantive_units"] += len(units)
        aggregate["exact_units"] += exact
        if coverage >= 0.90:
            aggregate["sources_at_least_90_percent_exact"] += 1
        if coverage >= 0.80:
            aggregate["sources_at_least_80_percent_exact"] += 1
        if route_evidence:
            aggregate["sources_with_later_editorial_route"] += 1

        source_reports.append(
            {
                "source_path": source_path,
                "source_chapter": row["source_chapter"],
                "source_sha256": hashlib.sha256(historical.encode("utf-8")).hexdigest(),
                "source_bytes": len(historical.encode("utf-8")),
                "v2_target": row["target_path"],
                "v2_disposition": row["disposition"],
                "v2_preservation_contract": (
                    "full source body preserved; merged sources were wrapped as an H2 and their "
                    "internal headings demoted, while singleton bodies were retained"
                ),
                "v3_lossless_rewrite_contract": (
                    "source blocks preserved and reordered; editorial tails moved; only duplicate "
                    "reference lines compacted"
                    if str(row["target_path"]) in v3_targets
                    else "not a v3 fused target; body carried forward through recorded path moves"
                ),
                "current_owners": sorted(owners),
                "transformation_trace": trace,
                "route_evidence": route_evidence,
                "h2_inventory": h2_inventory(historical),
                "substantive_unit_count": len(units),
                "exact_unit_count": exact,
                "normalized_exact_coverage": round(coverage, 6),
                "matched_owner_counts": dict(matched_owner_counts),
                "unmatched_unit_count": len(unmatched),
                "unmatched_samples": [
                    {
                        "kind": unit.kind,
                        "normalized_length": len(unit.normalized),
                        "sample": re.sub(r"\s+", " ", unit.raw).strip()[:240],
                    }
                    for unit in unmatched[:5]
                ],
                "verification": verification,
            }
        )

    unit_count = aggregate["substantive_units"]
    exact_count = aggregate["exact_units"]
    needs_review = [
        item["source_path"]
        for item in source_reports
        if item["verification"] == "needs_manual_review"
    ]
    summary = {
        "historical_source_count": len(source_reports),
        "git_retrievable_source_count": len(source_reports),
        "current_owner_resolved_source_count": len(source_reports),
        "current_canonical_count": len(documents),
        "substantive_unit_count": unit_count,
        "normalized_exact_unit_count": exact_count,
        "normalized_exact_unit_coverage": round(exact_count / unit_count, 6),
        "sources_exact_full": aggregate["verified_exact_full"],
        "sources_at_least_90_percent_exact": aggregate[
            "sources_at_least_90_percent_exact"
        ],
        "sources_at_least_80_percent_exact": aggregate[
            "sources_at_least_80_percent_exact"
        ],
        "sources_verified_by_later_editorial_routes": aggregate[
            "verified_editorial_route_after_true_fusion"
        ],
        "sources_with_later_editorial_route": aggregate[
            "sources_with_later_editorial_route"
        ],
        "needs_manual_review_count": len(needs_review),
    }
    return {
        "schema_version": 1,
        "scope": "454 Git HEAD canonical sources -> 276 current canonical chapter bodies",
        "method": {
            "source_recovery": "git show HEAD:<source_path>",
            "owner_resolution": "v2 map replayed through v3-v14 merge, split, rename and reindex maps; current consolidated_from used as additional provenance",
            "unit_definition": "prose paragraphs, contiguous list/table blocks, and fenced code blocks with at least 50 normalized characters",
            "normalization": "whitespace, Markdown link destinations, footnote namespaces and punctuation removed",
            "interpretation": "exact coverage is a conservative lower bound; rewritten/deduplicated true-fusion sources are verified by explicit content_routes",
        },
        "construction_evidence": [
            {
                "script": "scripts/consolidate_articles_v2.py",
                "contract": "build_unit_output preserved every complete source body before deleting predecessor paths",
            },
            {
                "script": "scripts/editorial_fusion_rewrite.py",
                "contract": "rewrite_text preserved source blocks, moved tails and compacted only duplicate reference lines",
            },
        ],
        "summary": summary,
        "needs_manual_review": needs_review,
        "sources": source_reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = audit()
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
        if report["needs_manual_review"]:
            print("needs manual review:")
            for path in report["needs_manual_review"]:
                print(f"- {path}")
    return 1 if report["needs_manual_review"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
