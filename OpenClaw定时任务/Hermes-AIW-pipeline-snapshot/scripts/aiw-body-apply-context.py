#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Select one AIW body-apply candidate for a Hermes agent run.

This script is intentionally non-mutating for chapter bodies. It creates only
private lease/evidence state under ~/.hermes/state. The agent cron consumes the
JSON context, edits exactly one existing AIW chapter, then updates queue/index.
"""
from __future__ import annotations

import hashlib
import argparse
import json
import os
import re
import sys
import yaml
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from aiw_pipeline_common import (
    create_manifest,
    current_head,
    is_canonical_chapter_path,
    iter_canonical_chapters,
    json_safe,
    material_applied_in_body,
    porcelain_paths,
    source_index_eligibility,
    unique_report_path,
)

TZ = ZoneInfo("Asia/Shanghai")
AIW = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki")
SRC = AIW / "src"
META = AIW / "metadata"
QUEUE = META / "queue.json"
SOURCE_INDEX = META / "source-index.json"
STATE = Path("/Users/gracker/.hermes/state/aiw-body-apply")
REPORT_DIR = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AIW自动化流水线")

ANDROID_BASELINE = "android-17.0.0_r1"


def jload(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def read(path: Path, limit: int | None = None) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    if limit and len(text) > limit:
        return text[: limit // 2] + "\n\n[...truncated...]\n\n" + text[-limit // 2 :]
    return text


def frontmatter(path: Path) -> dict:
    text = read(path, 12000)
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    try:
        loaded = yaml.safe_load(text[3:end]) or {}
        return json_safe(loaded) if isinstance(loaded, dict) else {}
    except Exception:
        return {}


def chapter_files() -> list[tuple[Path, dict]]:
    out = []
    if not SRC.exists():
        return out
    for path in iter_canonical_chapters():
        fm = frontmatter(path)
        out.append((path, fm))
    return out


def resolve_target(item: dict, chapters: list[tuple[Path, dict]]) -> Path | None:
    raw = item.get("target_path") or item.get("path")
    if raw:
        p = AIW / raw if not str(raw).startswith("/") else Path(raw)
        try:
            p.resolve().relative_to(SRC.resolve())
        except Exception:
            return None
        if p.exists() and p.is_file() and is_canonical_chapter_path(p):
            return p
        # Freeze means no new chapters; do not return missing path.
        return None

    section = str(item.get("section") or item.get("chapter") or "").strip()
    section = section.replace("§", "").strip()
    if section:
        hay_terms = re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]{2,}", str(item.get("title") or item.get("section_title") or "").lower())
        # Exact chapter frontmatter match first. Historical AIW has a few duplicate
        # chapter numbers; when multiple files match, choose the one whose title/path
        # overlaps the queue/source title instead of the first filesystem hit.
        exact: list[tuple[int, Path]] = []
        for p, fm in chapters:
            if str(fm.get("chapter", "")).strip() == section:
                hay = (str(p).lower() + " " + json.dumps(fm, ensure_ascii=False).lower())
                score = sum(1 for t in hay_terms if t.lower() in hay)
                exact.append((score, p))
        if exact:
            exact.sort(reverse=True, key=lambda x: x[0])
            return exact[0][1]
        # Some historical items store ch02 / 2.31; allow prefix chapter-family match.
        sec_prefix = section.split(".", 1)[0].lstrip("ch0").lstrip("ch")
        scored: list[tuple[int, Path]] = []
        for p, fm in chapters:
            chap = str(fm.get("chapter", ""))
            if sec_prefix and chap.split(".", 1)[0].lstrip("0") != sec_prefix:
                continue
            hay = (str(p).lower() + " " + json.dumps(fm, ensure_ascii=False).lower())
            score = sum(1 for t in hay_terms if t.lower() in hay)
            scored.append((score, p))
        scored.sort(reverse=True, key=lambda x: x[0])
        if scored and scored[0][0] > 0:
            return scored[0][1]
    return None


def queue_candidates(chapters: list[tuple[Path, dict]]) -> list[dict]:
    raw = jload(QUEUE, [])
    items = raw if isinstance(raw, list) else raw.get("pending", raw.get("items", []))
    out = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        if item.get("status", "pending") != "pending":
            continue
        target = resolve_target(item, chapters)
        if not target:
            continue
        mats = item.get("material_paths") or ([item.get("link")] if item.get("link") else [])
        target_text = read(target, 40000)
        # Only a stable source marker / material id in the chapter body proves
        # material application. A filename in frontmatter such as gap_source or
        # review_notes must not make the selector skip the item.
        if any(str(m) and material_applied_in_body(str(m), target_text) for m in mats):
            continue
        out.append({
            "source": "queue",
            "queue_index": idx,
            "priority": int(item.get("priority") or 50),
            "title": item.get("title") or item.get("section_title") or target.stem,
            "target_path": str(target.relative_to(AIW)),
            "material_paths": mats,
            "item": item,
        })
    return out


def source_index_candidates(chapters: list[tuple[Path, dict]]) -> list[dict]:
    data = jload(SOURCE_INDEX, {"files": []})
    files = data.get("files", []) if isinstance(data, dict) else []
    out = []
    draft_chapters = [(p, fm) for p, fm in chapters if str(fm.get("status", "")).strip().strip('"\'') == "draft"]
    for idx, item in enumerate(files):
        if not isinstance(item, dict):
            continue
        mat = str(item.get("path") or "").strip().strip('`')
        if not mat:
            continue
        target = None
        match_reason = "explicit-target"
        # Freeze-safe rule: source-index material may only be applied when the
        # collector/classifier already routed it to a concrete existing chapter.
        # Do not guess from broad chapter labels (ch16) or generic title overlap;
        # that previously allowed AI/agent/RSS noise to leak into AIW chapters.
        if item.get("target_path") or item.get("applied_target_path"):
            target = resolve_target({"target_path": item.get("target_path") or item.get("applied_target_path")}, chapters)
        if not target:
            continue
        target_text = read(target, 40000)
        eligible, reason = source_index_eligibility(item, chapter_text=target_text)
        if not eligible:
            continue
        out.append({
            "source": "source-index",
            "source_index": idx,
            "priority": int(item.get("score") or (85 if item.get("section") else 70)),
            "title": item.get("title") or target.stem,
            "target_path": str(target.relative_to(AIW)),
            "material_paths": [mat],
            "match_reason": match_reason,
            "eligibility_reason": reason,
            "item": item,
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Preview selection without creating a manifest/lease")
    args = ap.parse_args()
    STATE.mkdir(parents=True, exist_ok=True)
    os.chmod(STATE, 0o700)
    if not AIW.exists() or not SRC.exists():
        print(json.dumps(json_safe({"status": "blocked", "reason": "AIW repo/src missing", "aiw": str(AIW)}), ensure_ascii=False))
        return 0

    dirty = porcelain_paths()
    if dirty and not args.dry_run:
        payload = {
            "schema_version": 1,
            "profile": "aiw-body-apply",
            "status": "blocked",
            "reason": "dirty-worktree-before-run",
            "dirty_paths": dirty[:50],
            "aiw_repo": str(AIW),
            "generated_at": datetime.now(TZ).isoformat(),
        }
        (STATE / "latest-context.json").write_text(json.dumps(json_safe(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(json_safe(payload), ensure_ascii=False, indent=2))
        return 0

    chapters = chapter_files()
    raw_candidates = queue_candidates(chapters) + source_index_candidates(chapters)
    deduped: dict[tuple[str, tuple[str, ...]], dict] = {}
    for candidate in raw_candidates:
        key = (
            str(candidate.get("target_path") or ""),
            tuple(sorted(str(x) for x in candidate.get("material_paths") or [])),
        )
        previous = deduped.get(key)
        if previous is None or int(candidate.get("priority") or 0) > int(previous.get("priority") or 0):
            deduped[key] = candidate
    candidates = list(deduped.values())
    candidates.sort(key=lambda x: (x.get("priority", 0), 1 if x.get("source") == "queue" else 0), reverse=True)
    if not candidates:
        payload = {
            "schema_version": 1,
            "profile": "aiw-body-apply",
            "status": "no-candidate",
            "generated_at": datetime.now(TZ).isoformat(),
            "scanned": {"chapters": len(chapters), "eligible": 0, "candidates": 0},
        }
        (STATE / "latest-context.json").write_text(json.dumps(json_safe(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(json_safe(payload), ensure_ascii=False, indent=2))
        return 0

    cand = candidates[0]
    target = AIW / cand["target_path"]
    materials = []
    for m in cand.get("material_paths") or []:
        p = Path(m)
        if p.exists() and p.is_file():
            materials.append({"path": str(p), "sha16": sha_text(read(p)), "excerpt": read(p, 9000)})
        else:
            materials.append({"path": str(m), "sha16": "", "excerpt": ""})

    now = datetime.now(TZ)
    run_id = now.strftime("%Y%m%d-%H%M%S") + "-" + sha_text(json.dumps(cand, ensure_ascii=False))[:8]
    formal_report_path = str(unique_report_path("aiw-body-apply", run_id, now))
    evidence_path = str(STATE / f"{run_id}.evidence.json")
    expected_paths = [cand["target_path"], "metadata/queue.json", "metadata/source-index.json"]
    if args.dry_run:
        manifest = {
            "base_sha": current_head(),
            "expected_changed_paths": expected_paths + [formal_report_path, evidence_path],
            "result_path": "",
        }
    else:
        try:
            manifest = create_manifest(
                lane="aiw-body-apply",
                run_id=run_id,
                target_path=cand["target_path"],
                expected_changed_paths=expected_paths + [formal_report_path, evidence_path],
                metadata={"candidate_source": cand.get("source"), "candidate_title": cand.get("title")},
                formal_report_path=formal_report_path,
                evidence_path=evidence_path,
                target_sha_before=sha_text(read(target)),
            )
        except RuntimeError as exc:
            payload = {
                "schema_version": 1,
                "profile": "aiw-body-apply",
                "status": "blocked",
                "reason": str(exc),
                "target_path": cand["target_path"],
                "generated_at": now.isoformat(),
            }
            print(json.dumps(json_safe(payload), ensure_ascii=False, indent=2))
            return 1
    payload = {
        "schema_version": 1,
        "profile": "aiw-body-apply",
        "status": "candidate-preview" if args.dry_run else "candidate_ready",
        "run_id": run_id,
        "lane": "aiw-body-apply",
        "base_sha": manifest["base_sha"],
        "manifest_path": "" if args.dry_run else str(Path("/Users/gracker/.hermes/state/aiw-run-manifests") / f"{run_id}.json"),
        "result_path": manifest["result_path"],
        "evidence_path": evidence_path,
        "generated_at": now.isoformat(),
        "aiw_repo": str(AIW),
        "formal_report_path": formal_report_path,
        "allowed_changed_paths": manifest["expected_changed_paths"],
        "candidate": cand,
        "target": {
            "path": str(target),
            "relative_path": cand["target_path"],
            "sha16": sha_text(read(target)),
            "sha256_utf8_16": sha_text(read(target)),
            "hash_contract": "SHA-256 of the exact UTF-8 decoded file text, first 16 lowercase hex characters; this is not a Git blob hash",
            "frontmatter": frontmatter(target),
            "excerpt": read(target, 12000),
        },
        "materials": materials,
        "constraints": [
            "Before editing, recompute target.sha256_utf8_16 as hashlib.sha256(Path(target.path).read_text(encoding='utf-8').encode('utf-8')).hexdigest()[:16] and compare it with manifest target_sha_before; never use git hash-object for this check.",
            "FINAL closed-loop writer: must modify exactly one existing src/**/*.md chapter when candidate_ready",
            "No new chapter files; do not edit src/SUMMARY.md",
            f"Android baseline: {ANDROID_BASELINE}; do not introduce conclusions for any version higher than Android 17",
            "Every new technical assertion must cite source material with [来源: ...] or [已验证: ...] style",
            "Keep chapter prose reader-facing: never mention this run/round, lane, agent, prompt, pipeline, review/rework task, or execution process in the article body; put those details only in logs/reports/evidence",
            "Factual correctness outranks outline/anchor preservation: delete or rewrite known-wrong prose, fake APIs, unsupported numbers, and contradicted drafts instead of retaining them behind a disclaimer",
            "Preserve YAML frontmatter validity; update last_body_apply_at, last_body_apply_run_id, task2b_state, task6_state, task9_state/pipeline_stage as appropriate",
            "After editing, update queue/source-index item status to applied/body-applied with run_id and target_path",
            "Write the exact formal_report_path, evidence_path JSON, and result_path JSON; then run aiw-run-complete.py with this manifest/result before responding",
        ],
    }
    if not args.dry_run:
        out = STATE / "latest-context.json"
        out.write_text(json.dumps(json_safe(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.chmod(out, 0o600)
    # Emit complete valid JSON. Cron output remains modest (~30KB) and downstream
    # agents/tools must be able to parse the pre-run contract exactly; truncating
    # mid-string creates invalid JSON and breaks the transaction boundary.
    print(json.dumps(json_safe(payload), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
