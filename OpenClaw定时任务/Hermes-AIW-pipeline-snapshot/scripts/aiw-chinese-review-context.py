#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Select one AIW chapter for a DeepSeek Chinese-quality pass."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from aiw_pipeline_common import AIW, create_manifest, current_head, porcelain_paths, unique_report_path

TZ = ZoneInfo("Asia/Shanghai")
STATE = Path("/Users/gracker/.hermes/state/aiw-chinese-quality-deepseek")
BASELINE = Path("/Users/gracker/.hermes/state/aiw-quality-baseline/latest.json")


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def selection_history() -> dict[str, datetime]:
    out: dict[str, datetime] = {}
    for path in STATE.glob("*.context.json"):
        try:
            data = load_json(path, {})
            target = (data.get("target") or {}).get("relative_path")
            if target:
                when = datetime.fromtimestamp(path.stat().st_mtime, TZ)
                previous = out.get(str(target))
                if previous is None or when > previous:
                    out[str(target)] = when
        except Exception:
            continue
    return out


def select_candidate() -> dict | None:
    baseline = load_json(BASELINE, {})
    history = selection_history()
    candidates = []
    for row in baseline.get("chinese_review_candidates", []) if isinstance(baseline, dict) else []:
        if not isinstance(row, dict):
            continue
        target = str(row.get("path") or "")
        if not target:
            continue
        path = AIW / target
        if path.exists() and path.is_file():
            candidates.append(row)
    if not candidates:
        return None
    # Baseline order is the quality priority.  Within it, review every unseen
    # chapter before cycling, then revisit the least recently selected one.
    never_selected = [row for row in candidates if str(row.get("path")) not in history]
    if never_selected:
        return never_selected[0]
    return min(candidates, key=lambda row: history[str(row.get("path"))])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    now = datetime.now(TZ)
    STATE.mkdir(parents=True, exist_ok=True)
    os.chmod(STATE, 0o700)

    if not BASELINE.exists():
        print(json.dumps({"status": "blocked", "reason": "quality baseline missing"}, ensure_ascii=False))
        return 1
    dirty = porcelain_paths()
    if dirty and not args.dry_run:
        print(json.dumps({"status": "blocked", "reason": "dirty-worktree-before-run", "dirty_paths": dirty[:50]}, ensure_ascii=False))
        return 1
    candidate = select_candidate()
    if not candidate:
        print(json.dumps({"status": "no-candidate", "reason": "no unrepeated Chinese-quality candidate"}, ensure_ascii=False))
        return 0

    rel = str(candidate["path"])
    target = AIW / rel
    text = target.read_text(encoding="utf-8", errors="ignore")
    run_id = now.strftime("%Y%m%d-%H%M%S") + "-deepseek-cn-" + sha16(rel)
    formal_report_path = str(unique_report_path("aiw-chinese-quality-deepseek", run_id, now))
    evidence_path = str(STATE / f"{run_id}.evidence.json")
    expected = [rel, formal_report_path, evidence_path]
    if args.dry_run:
        manifest = {"base_sha": current_head(), "expected_changed_paths": expected, "result_path": ""}
    else:
        try:
            manifest = create_manifest(
                lane="aiw-chinese-quality-deepseek",
                run_id=run_id,
                target_path=rel,
                expected_changed_paths=expected,
                metadata={"risk_flags": candidate.get("risk_flags", []), "risk_score": candidate.get("risk_score")},
                formal_report_path=formal_report_path,
                evidence_path=evidence_path,
                target_sha_before=sha16(text),
            )
        except RuntimeError as exc:
            print(json.dumps({"status": "blocked", "reason": str(exc), "target_path": rel}, ensure_ascii=False))
            return 1

    payload = {
        "schema_version": 1,
        "profile": "aiw-chinese-quality-deepseek",
        "status": "candidate-preview" if args.dry_run else "candidate_ready",
        "run_id": run_id,
        "lane": "aiw-chinese-quality-deepseek",
        "base_sha": manifest["base_sha"],
        "manifest_path": "" if args.dry_run else f"/Users/gracker/.hermes/state/aiw-run-manifests/{run_id}.json",
        "result_path": manifest["result_path"],
        "evidence_path": evidence_path,
        "formal_report_path": formal_report_path,
        "allowed_changed_paths": manifest["expected_changed_paths"],
        "generated_at": now.isoformat(),
        "aiw_repo": str(AIW),
        "target": {
            "path": str(target),
            "relative_path": rel,
            "sha16": sha16(text),
            "sha256_utf8_16": sha16(text),
            "hash_contract": "SHA-256 of the exact UTF-8 decoded file text, first 16 lowercase hex characters; this is not a Git blob hash",
            "quality_metrics": candidate,
            "excerpt": text[:18000],
        },
        "constraints": [
            "Before editing, recompute target.sha256_utf8_16 as hashlib.sha256(Path(target.path).read_text(encoding='utf-8').encode('utf-8')).hexdigest()[:16] and compare it with manifest target_sha_before; never use git hash-object for this check.",
            "Chinese readability and teaching-value pass only; do not alter technical facts, APIs, paths, numbers, code, citations, version boundaries, status, confidence, or verification dates.",
            "Prefer a real small edit only when it reduces ambiguity, AI-style filler, translation syntax, or dense paragraphs without changing meaning.",
            "Run the Gracker Writing hard gate on the final target body: do not add contrast-correction patterns (`不是...而是`, `不只是...还`, `并非...而是`, `不仅仅是...更是`, `与其说`), filler adverbs (`真正/实际上/其实/根本/彻底/确实`), evaluative openers (`最值得看/最值得/值得一看`), structural meta narration, meaning inflation, or `这说明/这体现/这反映/这凸显` style analysis tails. If the original already has hits, this lane should reduce them where safe; it must never increase them.",
            "Keep chapter prose reader-facing: never add this run/round, lane, agent, prompt, pipeline, review/rework task, or execution-process language to the article body.",
            "If a technical claim looks wrong, return needs-human-review without editing and identify the exact sentence.",
            "Write formal_report_path, evidence_path JSON, result_path JSON, then run aiw-run-complete.py before responding.",
        ],
    }
    if not args.dry_run:
        context_path = STATE / f"{run_id}.context.json"
        context_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.chmod(context_path, 0o600)
        latest = STATE / "latest-context.json"
        latest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.chmod(latest, 0o600)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
