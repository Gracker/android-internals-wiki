#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Select one AIW ready-for-review chapter for a real review/finalize agent run.

Non-mutating pre-run context script. It intentionally selects exactly one existing
chapter and lets the Hermes agent decide finalized vs needs-rework after reading
chapter/source evidence.
"""
from __future__ import annotations

import hashlib
import argparse
import json
import os
import re
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from aiw_pipeline_common import (
    MANIFEST_DIR,
    create_manifest,
    current_head,
    iter_canonical_chapters,
    json_safe,
    matching_findings,
    porcelain_paths,
    unique_report_path,
)

TZ = ZoneInfo("Asia/Shanghai")
AIW = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki")
STATE = Path("/Users/gracker/.hermes/state/aiw-review-finalize-apply")
FORMAL_ROOT = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AIW自动化流水线")
SRC = AIW / "src"


def sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def parse_fm(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}, text[:6000]
    try:
        loaded = yaml.safe_load(m.group(1)) or {}
        fm = json_safe(loaded) if isinstance(loaded, dict) else {}
    except Exception:
        fm = {}
    return fm, text[m.end():]


def jload(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def recent_paths(hours: int = 36) -> set[str]:
    """Avoid repeatedly finalizing the same chapter while alternatives exist."""
    cutoff = datetime.now(TZ) - timedelta(hours=hours)
    terminal = {
        "agent-completed",
        "committed-local",
        "pushed",
        "completed-no-change",
        "no-change",
        "needs-human-review",
    }
    out: set[str] = set()
    for path in MANIFEST_DIR.glob("*.json"):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
            if row.get("lane") != "aiw-review-finalize-apply" or row.get("status") not in terminal:
                continue
            stamp = row.get("updated_at") or row.get("created_at")
            when = datetime.fromisoformat(str(stamp)) if stamp else datetime.fromtimestamp(path.stat().st_mtime, TZ)
            if when.tzinfo is None:
                when = when.replace(tzinfo=TZ)
            if when >= cutoff and row.get("target_path"):
                out.add(str(row["target_path"]))
        except Exception:
            continue
    return out


def frontmatter_recent(fm: dict, hours: int = 36) -> bool:
    cutoff = datetime.now(TZ) - timedelta(hours=hours)
    for key in ("last_review_finalize_at", "last_task9_at", "last_task9_audit_at"):
        raw = fm.get(key)
        if not raw:
            continue
        try:
            when = datetime.fromisoformat(str(raw))
            if when.tzinfo is None:
                when = when.replace(tzinfo=TZ)
            if when >= cutoff:
                return True
        except (TypeError, ValueError):
            continue
    return False


def material_candidates(fm: dict, body: str) -> list[str]:
    out: list[str] = []
    for key in ("last_body_apply_source", "source", "material", "gap_source"):
        v = fm.get(key)
        if v and v.endswith(".md"):
            out.append(v)
    for m in re.findall(r"DeepResearch/[\w\-./\u4e00-\u9fff]+\.md|[0-9]{4}-[0-9]{2}-[0-9]{2}-[\w\-.\u4e00-\u9fff]+\.md", body):
        out.append(m)
    # source-index reverse lookup by target_path
    rel = None
    return list(dict.fromkeys(out))[:6]


def resolve_materials(names: list[str]) -> list[dict]:
    roots = [AIW.parent / "DeepResearch", AIW.parent / "技术文章", AIW.parent]
    found: list[dict] = []
    for name in names:
        p = Path(name)
        candidates = []
        if p.is_absolute():
            candidates.append(p)
        else:
            candidates += [AIW.parent / name, AIW.parent / "DeepResearch" / p.name]
            for root in roots:
                candidates.append(root / p.name)
        chosen = None
        for c in candidates:
            if c.exists() and c.is_file():
                chosen = c
                break
        if not chosen:
            # bounded basename scan only if needed
            for root in roots[:2]:
                try:
                    matches = list(root.rglob(p.name))[:1]
                except Exception:
                    matches = []
                if matches:
                    chosen = matches[0]
                    break
        if chosen:
            txt = chosen.read_text(encoding="utf-8", errors="ignore")
            found.append({"path": str(chosen), "sha16": sha16(txt), "excerpt": txt[:7000]})
    return found[:4]


def source_index_materials_for(rel: str) -> list[str]:
    idx = jload(AIW / "metadata/source-index.json", {"files": []})
    out = []
    for item in idx.get("files", []) if isinstance(idx, dict) else []:
        if item.get("target_path") == rel or item.get("applied_target_path") == rel:
            p = item.get("path")
            if p:
                out.append(str(p))
        # Also include recently body-applied entries mentioning same file path.
        if item.get("status") == "applied" and item.get("target_path") == rel and item.get("path"):
            out.append(str(item.get("path")))
    return out


def open_findings_for(rel: str, fm: dict) -> list[dict]:
    data = jload(AIW / "metadata/review-findings.json", {"findings": []})
    rows = data.get("findings", []) if isinstance(data, dict) else []
    return matching_findings(rows, rel, fm)


def priority(path: Path, fm: dict, body: str) -> tuple[int, str]:
    rel = str(path.relative_to(AIW))
    score = 0
    if fm.get("status") in {"ready-for-review", "review", "reviewing"}:
        score += 100
    if fm.get("task6_state") in {"revisiting", "pending"}:
        score += 30
    if fm.get("task9_state") in {"pending", "revisiting"}:
        score += 25
    if fm.get("last_body_apply_at"):
        score += 25
    # Publication-state claims must not outrun structured evidence. Repair or
    # explicitly downgrade these candidates before spending cycles on already
    # well-formed ready-for-review chapters.
    if not fm.get("sources"):
        score += 70
    if not (fm.get("last_source_verified_at") or fm.get("last_verified")):
        score += 40
    if not fm.get("confidence"):
        score += 30
    clean_body = re.sub(r"```.*?```|<!--.*?-->", "", body, flags=re.S)
    if re.search(
        r"\[\s*待验证(?:\s*[:：\]]|\s*$)|"
        r"(?:加工说明|需要进一步验证|待进一步验证|需要补齐|后续加工|补充.{0,60}待验证(?:项|内容|细节))",
        clean_body,
        re.I | re.M,
    ):
        score += 8
    return (-score, rel)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Preview selection without creating a manifest/lease")
    args = ap.parse_args()
    now = datetime.now(TZ)
    run_id = now.strftime("%Y%m%d-%H%M%S") + "-" + hashlib.sha1(os.urandom(16)).hexdigest()[:8]
    STATE.mkdir(parents=True, exist_ok=True)
    candidates = []
    if not AIW.exists():
        out = {"schema_version": 1, "profile": "aiw-review-finalize-apply", "status": "blocked", "reason": f"AIW repo missing: {AIW}"}
    elif porcelain_paths() and not args.dry_run:
        out = {
            "schema_version": 1,
            "profile": "aiw-review-finalize-apply",
            "status": "blocked",
            "reason": "dirty-worktree-before-run",
            "dirty_paths": porcelain_paths()[:50],
            "aiw_repo": str(AIW),
            "generated_at": now.isoformat(timespec="seconds"),
        }
    else:
        recent = recent_paths()
        for p in iter_canonical_chapters():
            txt = p.read_text(encoding="utf-8", errors="ignore")
            fm, body = parse_fm(txt)
            rel = str(p.relative_to(AIW))
            if rel in recent or frontmatter_recent(fm):
                continue
            status = fm.get("status", "").strip().strip('"\'')
            if status in {"ready-for-review", "review", "reviewing"} or fm.get("task6_state") == "revisiting" or fm.get("task9_state") == "pending":
                if status in {"finalized", "published"}:
                    continue
                candidates.append((priority(p, fm, body), p, fm, txt, body))
        candidates.sort(key=lambda x: x[0])
        if not candidates:
            out = {"schema_version": 1, "profile": "aiw-review-finalize-apply", "status": "no-candidate", "generated_at": now.isoformat(timespec="seconds"), "aiw_repo": str(AIW), "scanned": {"candidates": 0}}
        else:
            _, p, fm, txt, body = candidates[0]
            rel = str(p.relative_to(AIW))
            mats = source_index_materials_for(rel) + material_candidates(fm, body)
            findings = open_findings_for(rel, fm)
            formal_report_path = str(unique_report_path("aiw-review-finalize-apply", run_id, now))
            evidence_path = str(STATE / f"{run_id}.evidence.json")
            expected = [rel, "metadata/review-findings.json", formal_report_path, evidence_path]
            if args.dry_run:
                manifest = {"base_sha": current_head(), "expected_changed_paths": expected, "result_path": ""}
            else:
                try:
                    manifest = create_manifest(
                        lane="aiw-review-finalize-apply",
                        run_id=run_id,
                        target_path=rel,
                        expected_changed_paths=expected,
                        finding_ids=[str(x.get("id")) for x in findings if x.get("id")],
                        metadata={"frontmatter_status": fm.get("status")},
                        formal_report_path=formal_report_path,
                        evidence_path=evidence_path,
                        target_sha_before=sha16(txt),
                    )
                except RuntimeError as exc:
                    out = {
                        "schema_version": 1,
                        "profile": "aiw-review-finalize-apply",
                        "status": "blocked",
                        "reason": str(exc),
                        "target_path": rel,
                        "generated_at": now.isoformat(timespec="seconds"),
                    }
                    latest = STATE / "latest-context.json"
                    latest.write_text(json.dumps(json_safe(out), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    print(json.dumps(json_safe(out), ensure_ascii=False, indent=2))
                    return 1
            out = {
                "schema_version": 1,
                "profile": "aiw-review-finalize-apply",
                "status": "candidate-preview" if args.dry_run else "review_candidate_ready",
                "run_id": run_id,
                "lane": "aiw-review-finalize-apply",
                "base_sha": manifest["base_sha"],
                "manifest_path": "" if args.dry_run else str(Path("/Users/gracker/.hermes/state/aiw-run-manifests") / f"{run_id}.json"),
                "result_path": manifest["result_path"],
                "evidence_path": evidence_path,
                "generated_at": now.isoformat(timespec="seconds"),
                "aiw_repo": str(AIW),
                "formal_report_path": formal_report_path,
                "allowed_changed_paths": manifest["expected_changed_paths"],
                "target": {
                    "path": str(p),
                    "relative_path": rel,
                    "sha16": sha16(txt),
                    "sha256_utf8_16": sha16(txt),
                    "hash_contract": "SHA-256 of the exact UTF-8 decoded file text, first 16 lowercase hex characters; this is not a Git blob hash",
                    "frontmatter": fm,
                    "excerpt": txt[:9000],
                },
                "open_findings": findings,
                "materials": resolve_materials(mats),
                "constraints": [
                    "Before editing, recompute target.sha256_utf8_16 as hashlib.sha256(Path(target.path).read_text(encoding='utf-8').encode('utf-8')).hexdigest()[:16] and compare it with manifest target_sha_before; never use git hash-object for this check.",
                    "Real OpenClaw-style review/fix/finalize: inspect exactly one existing ready-for-review chapter",
                    "May edit the selected chapter and review-finding metadata only; no new chapter and no SUMMARY edits",
                    "Finalize only with structured source_evidence and no open P0/P1 finding; otherwise keep ready-for-review or set needs-rework",
                    "When sources/date/confidence are missing, verify existing body references against the claims before structuring them; never copy URLs into frontmatter merely to satisfy metadata. If evidence is insufficient, preserve or create a stable finding and downgrade instead of finalizing.",
                    "When an official source is used, inspect and preserve its warning, deprecated, migration, availability, API-level, and version-applicability notices; omitting such lifecycle boundaries is a substantive error.",
                    "Factual correctness outranks historical outline/anchor preservation. Delete or rewrite known-wrong prose, fake APIs, unsupported numbers, and contradicted drafts; never keep them behind a historical-outline disclaimer.",
                    "A finalized/verified article must contain one coherent current account, not an incorrect first half followed by a correction.",
                    "Keep chapter prose reader-facing: never mention this run/round, lane, agent, prompt, pipeline, review/rework task, or execution process in the article body; put those details only in logs/reports/evidence",
                    "Never expose editorial instructions or metadata states such as ready-for-review/needs-rework/finalized in article prose; express only the technical evidence boundary to readers",
                    "Write formal_report_path, evidence_path JSON, and result_path JSON; run aiw-run-complete.py before responding; do not run git sync from this lane",
                ],
            }
    latest = STATE / "latest-context.json"
    if not args.dry_run:
        latest.write_text(json.dumps(json_safe(out), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(json_safe(out), ensure_ascii=False, indent=2))
    return 0 if out.get("status") != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
