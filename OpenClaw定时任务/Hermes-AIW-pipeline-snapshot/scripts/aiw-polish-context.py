#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Select one existing AIW chapter for high-throughput polish/review lanes.

This restores OpenClaw-like article polishing throughput without creating new
chapters. It is a non-mutating context producer: Hermes agent lanes consume the
JSON and perform the actual chapter patch + validation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import yaml
from functools import lru_cache
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from aiw_pipeline_common import (
    MANIFEST_DIR,
    affirmative_higher_android_mentions,
    create_manifest,
    current_head,
    iter_canonical_chapters,
    marker_kind,
    json_safe,
    matching_findings,
    porcelain_paths,
    unique_report_path,
)

TZ = ZoneInfo("Asia/Shanghai")
AIW = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki")
SRC = AIW / "src"
FORMAL_ROOT = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AIW自动化流水线")
STATE_ROOT = Path("/Users/gracker/.hermes/state/aiw-polish-apply")
ANDROID_BASELINE = "android-17.0.0_r1"

MODES = {"deep-review", "rework", "idle-audit", "draft-polish"}


def sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def read(path: Path, limit: int | None = None) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    if limit and len(text) > limit:
        return text[: limit // 2] + "\n\n[...truncated...]\n\n" + text[-limit // 2 :]
    return text


def jload(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def parse_fm(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    if not m:
        return {}, text
    try:
        loaded = yaml.safe_load(m.group(1)) or {}
        fm = loaded if isinstance(loaded, dict) else {}
    except Exception:
        fm = {}
    return fm, text[m.end():]


def rel(path: Path) -> str:
    return str(path.relative_to(AIW))


def recent_paths(mode: str, hours: int = 36) -> set[str]:
    out: set[str] = set()
    cutoff = datetime.now(TZ) - timedelta(hours=hours)
    terminal_statuses = {
        "agent-completed",
        "committed-local",
        "pushed",
        "completed-no-change",
        "no-change",
        "needs-human-review",
    }
    for p in MANIFEST_DIR.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if data.get("lane") != f"aiw-polish-{mode}" or data.get("status") not in terminal_statuses:
                continue
            stamp = data.get("updated_at") or data.get("created_at")
            when = datetime.fromisoformat(str(stamp)) if stamp else datetime.fromtimestamp(p.stat().st_mtime, TZ)
            if when.tzinfo is None:
                when = when.replace(tzinfo=TZ)
            if when >= cutoff and data.get("target_path"):
                out.add(str(data["target_path"]))
        except Exception:
            continue
    return out


def frontmatter_recent(fm: dict, mode: str, hours: int = 36) -> bool:
    keys = {
        "deep-review": ("last_task9_at", "last_review_finalize_at", "last_task9_audit_at"),
        "rework": ("last_rework_at", "last_task2b_at", "last_task2b_lite_at"),
        "idle-audit": ("last_idle_audit_at", "last_task9_audit_at", "last_task9_audit"),
        "draft-polish": ("last_draft_polish_at",),
    }[mode]
    cutoff = datetime.now(TZ) - timedelta(hours=hours)
    for key in keys:
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


def material_names_from_body(body: str) -> list[str]:
    pats = [
        r"DeepResearch/[\w\-./\u4e00-\u9fff]+\.md",
        r"技术文章/[\w\-./\u4e00-\u9fff]+\.md",
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}-[\w\-.\u4e00-\u9fff]+\.md",
    ]
    out: list[str] = []
    for pat in pats:
        out.extend(re.findall(pat, body))
    return list(dict.fromkeys(out))[:8]


def source_index_materials_for(relative_path: str) -> list[str]:
    idx = jload(AIW / "metadata/source-index.json", {"files": []})
    out: list[str] = []
    files = idx.get("files", []) if isinstance(idx, dict) else []
    for item in files:
        if not isinstance(item, dict):
            continue
        targets = {item.get("target_path"), item.get("applied_target_path"), item.get("path")}
        if relative_path in targets or item.get("target_path") == relative_path or item.get("applied_target_path") == relative_path:
            p = item.get("path")
            if p:
                out.append(str(p))
    return list(dict.fromkeys(out))[:8]


def resolve_materials(names: list[str]) -> list[dict]:
    roots = [AIW.parent / "DeepResearch", AIW.parent / "技术文章", AIW.parent, AIW]
    found: list[dict] = []
    for name in names:
        if not name:
            continue
        raw = Path(str(name).strip().strip('`'))
        candidates: list[Path] = []
        if raw.is_absolute():
            candidates.append(raw)
        else:
            candidates.extend([AIW.parent / raw, AIW / raw])
            for root in roots:
                candidates.append(root / raw.name)
        chosen = next((c for c in candidates if c.exists() and c.is_file()), None)
        if not chosen:
            for root in roots[:2]:
                try:
                    matches = list(root.rglob(raw.name))[:1]
                except Exception:
                    matches = []
                if matches:
                    chosen = matches[0]
                    break
        if chosen:
            txt = read(chosen, 9000)
            found.append({"path": str(chosen), "sha16": sha16(txt), "excerpt": txt})
    return found[:5]


def chapter_records() -> list[dict]:
    records: list[dict] = []
    if not SRC.exists():
        return records
    for p in iter_canonical_chapters():
        txt = read(p)
        fm, body = parse_fm(txt)
        records.append({"path": p, "rel": rel(p), "fm": fm, "body": body, "text": txt})
    return records


def quality_flags(fm: dict, body: str) -> list[str]:
    flags: list[str] = []
    if next(affirmative_higher_android_mentions(body), None):
        flags.append("above-android17-boundary-risk")
    clean_body = re.sub(r"```.*?```", "", body, flags=re.S)
    clean_body = re.sub(r"<!--.*?-->", "", clean_body, flags=re.S)
    if any(
        marker_kind(line.strip()) == "editorial-placeholder"
        for line in clean_body.splitlines()
        if line.strip()
    ):
        flags.append("editorial-placeholder")
    if len(body) < 3500:
        flags.append("thin-body")
    if not (fm.get("last_source_verified_at") or fm.get("last_verified")):
        flags.append("missing-last_verified")
    if not fm.get("confidence"):
        flags.append("missing-confidence")
    if str(fm.get("status", "")).strip().strip('"\'') in {"ready-for-review", "finalized", "verified"} and not fm.get("sources"):
        flags.append("missing-sources")
    return flags


@lru_cache(maxsize=1)
def all_open_findings() -> tuple[dict, ...]:
    data = jload(AIW / "metadata/review-findings.json", {"findings": []})
    rows = data.get("findings", []) if isinstance(data, dict) else []
    return tuple(row for row in rows if isinstance(row, dict) and row.get("status") == "open")


def open_findings_for(relative_path: str, fm: dict) -> list[dict]:
    return matching_findings(list(all_open_findings()), relative_path, fm)


def score_record(mode: str, rec: dict, recent: set[str]) -> tuple[int, str] | None:
    fm = rec["fm"]
    body = rec["body"]
    status = str(fm.get("status", "")).strip().strip('"\'')
    task6 = str(fm.get("task6_state", "")).strip()
    task9 = str(fm.get("task9_state", "")).strip()
    flags = quality_flags(fm, body)
    r = rec["rel"]
    findings = open_findings_for(r, fm)
    blocking_findings = [f for f in findings if f.get("severity") in {"P0", "P1"}]
    if r in recent or frontmatter_recent(fm, mode):
        return None

    score = 0
    if mode == "deep-review":
        # Deep-review is for reviewable chapters with enough existing body or
        # source material. Do not pick thin placeholder chapters with no
        # materials: that turns audit into unsupported drafting.
        if status not in {"ready-for-review", "review", "reviewing"}:
            return None
        if blocking_findings:
            return None
        has_material = bool(source_index_materials_for(r) or material_names_from_body(body))
        if "thin-body" in flags and not has_material:
            return None
        score += 100
        if task9 in {"pending", "revisiting"}: score += 25
        if task6 in {"revisiting", "pending"}: score += 20
        if flags: score += min(20, len(flags) * 5)
    elif mode == "rework":
        if not findings and status not in {"needs-rework", "needs-review"} and task6 != "needs-rework" and task9 != "needs-rework":
            return None
        score += 90
        if status in {"needs-rework", "needs-review"}: score += 50
        if task6 == "needs-rework" or task9 == "needs-rework": score += 40
        if any(f.get("severity") == "P0" for f in blocking_findings):
            score += 120
        elif blocking_findings:
            score += 70
        score += min(30, len(findings) * 10)
    elif mode == "idle-audit":
        if status not in {"finalized", "verified"}:
            return None
        if blocking_findings:
            return None
        score += 60
        # Prefer finalized chapters that still carry suspicious markers.
        score += min(45, len(flags) * 9)
        if not flags and fm.get("last_idle_audit_at"):
            score -= 20
    elif mode == "draft-polish":
        if status != "draft":
            return None
        score += 100
        if len(body) >= 2500: score += 20
        if flags: score += min(20, len(flags) * 5)
    else:
        return None
    # Stable spread: avoid always choosing lexicographically first chapters.
    ageish = 9999999999 - int(sha16(r), 16) % 100000
    return (-score, str(ageish), r)


def select(mode: str) -> dict | None:
    recent = recent_paths(mode)
    scored: list[tuple[tuple[int, str, str], dict]] = []
    for rec in chapter_records():
        s = score_record(mode, rec, recent)
        if s is not None:
            scored.append((s, rec))
    scored.sort(key=lambda x: x[0])
    if not scored:
        return None
    rec = scored[0][1]
    rec["open_findings"] = open_findings_for(rec["rel"], rec["fm"])
    return rec


def mode_constraints(mode: str) -> list[str]:
    base = [
        "Modify exactly one existing src/**/*.md chapter when candidate_ready; no new chapter files.",
        "Never edit src/SUMMARY.md from this lane.",
        f"Android baseline: {ANDROID_BASELINE}; do not introduce conclusions for any version higher than Android 17.",
        "Prefer real safe article patches over report-only output.",
        "Factual correctness outranks historical outline/anchor preservation. Outline markers protect topic coverage, never false prose, fake APIs, unsupported numbers, or contradicted drafts; delete or rewrite known-bad text instead of surrounding it with a disclaimer.",
        "A finalized/verified article must contain one coherent current account. Never preserve a known-wrong block and tell readers to trust a later correction.",
        "Keep chapter prose reader-facing: never mention this run/round, lane, agent, prompt, rework, audit pipeline, or task execution inside the article body; operational details belong only in logs/reports/evidence.",
        "Never expose editorial instructions or metadata states such as ready-for-review/needs-rework/finalized in article prose; express only the technical evidence boundary to readers.",
        "When an official source is used, inspect and preserve its warning, deprecated, migration, availability, API-level, and version-applicability notices; omitting such lifecycle boundaries is a substantive error.",
        "Run the Gracker Writing hard gate on the final target body: do not add contrast-correction patterns (`不是...而是`, `不只是...还`, `并非...而是`, `不仅仅是...更是`, `与其说`), filler adverbs (`真正/实际上/其实/根本/彻底/确实`), evaluative openers (`最值得看/最值得/值得一看`), structural meta narration, meaning inflation, or `这说明/这体现/这反映/这凸显` style analysis tails. If the original already has hits, reduce them when safe; at minimum never increase them in this diff.",
        "Run check-metadata.py, check-summary-links.py, and git diff --check before final response.",
        "Write a formal Obsidian report under OpenClaw定时任务/AIW自动化流水线; ~/.hermes/state is evidence only.",
        "Do not run git sync or any git add/commit/push command from this lane; a separate manifest gate owns commits.",
        "Write the exact formal_report_path, evidence_path JSON, and result_path JSON, then run aiw-run-complete.py before responding.",
    ]
    if mode == "deep-review":
        base += ["OpenClaw-style deep technical review: fix source-boundary/claim/readability issues and write a logs/deep-review/*.md audit log."]
    elif mode == "rework":
        base += ["Resolve only the open_findings supplied by context; close or preserve their stable ids and update state from evidence."]
    elif mode == "idle-audit":
        base += [
            "Idle audit finalized chapters: patch only safe issues; do not churn text if no real issue is found; write logs/audit/*.md.",
            "Treat missing structured sources, source-verification date, or confidence on finalized/verified content as a publication defect: verify existing body references claim by claim before backfilling metadata; if evidence is insufficient, create a stable finding and downgrade instead of preserving a false finalized state.",
        ]
    elif mode == "draft-polish":
        base += ["Polish an existing draft toward ready-for-review; do not create new files or expand unsupported claims."]
    return base


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=sorted(MODES))
    ap.add_argument("--dry-run", action="store_true", help="Preview selection without creating a manifest/lease")
    args = ap.parse_args()
    mode = args.mode
    now = datetime.now(TZ)
    state = STATE_ROOT / mode
    state.mkdir(parents=True, exist_ok=True)
    os.chmod(state, 0o700)
    if not AIW.exists() or not SRC.exists():
        out = {"schema_version": 1, "profile": f"aiw-polish-{mode}", "mode": mode, "status": "blocked", "reason": f"AIW repo missing: {AIW}"}
    elif porcelain_paths() and not args.dry_run:
        out = {
            "schema_version": 1,
            "profile": f"aiw-polish-{mode}",
            "mode": mode,
            "status": "blocked",
            "reason": "dirty-worktree-before-run",
            "dirty_paths": porcelain_paths()[:50],
            "aiw_repo": str(AIW),
            "generated_at": now.isoformat(timespec="seconds"),
        }
    else:
        rec = select(mode)
        if not rec:
            out = {"schema_version": 1, "profile": f"aiw-polish-{mode}", "mode": mode, "status": "no-new-input", "generated_at": now.isoformat(timespec="seconds"), "aiw_repo": str(AIW)}
        else:
            run_id = now.strftime("%Y%m%d-%H%M%S") + "-" + mode + "-" + sha16(rec["rel"])[:8]
            mats = source_index_materials_for(rec["rel"]) + material_names_from_body(rec["body"])
            formal_report_path = str(unique_report_path(f"aiw-polish-{mode}", run_id, now))
            evidence_path = str(state / f"{run_id}.evidence.json")
            log_dir = {"deep-review": "logs/deep-review", "rework": "logs/rework", "idle-audit": "logs/audit", "draft-polish": "logs/review"}[mode]
            expected = [rec["rel"], f"{log_dir}/{now:%Y-%m-%d}-{run_id}-{mode}.md", formal_report_path, evidence_path]
            if mode in {"deep-review", "rework", "idle-audit"}:
                expected.append("metadata/review-findings.json")
            if args.dry_run:
                manifest = {"base_sha": current_head(), "expected_changed_paths": expected, "result_path": ""}
            else:
                try:
                    manifest = create_manifest(
                        lane=f"aiw-polish-{mode}",
                        run_id=run_id,
                        target_path=rec["rel"],
                        expected_changed_paths=expected,
                        finding_ids=[str(x.get("id")) for x in rec.get("open_findings", []) if x.get("id")],
                        metadata={"frontmatter_status": rec["fm"].get("status"), "quality_flags": quality_flags(rec["fm"], rec["body"])},
                        formal_report_path=formal_report_path,
                        evidence_path=evidence_path,
                        target_sha_before=sha16(rec["text"]),
                    )
                except RuntimeError as exc:
                    out = {
                        "schema_version": 1,
                        "profile": f"aiw-polish-{mode}",
                        "mode": mode,
                        "status": "blocked",
                        "reason": str(exc),
                        "target_path": rec["rel"],
                        "generated_at": now.isoformat(timespec="seconds"),
                    }
                    print(json.dumps(json_safe(out), ensure_ascii=False, indent=2))
                    return 1
            out = {
                "schema_version": 1,
                "profile": f"aiw-polish-{mode}",
                "mode": mode,
                "status": "candidate-preview" if args.dry_run else "polish_candidate_ready",
                "run_id": run_id,
                "lane": f"aiw-polish-{mode}",
                "base_sha": manifest["base_sha"],
                "manifest_path": "" if args.dry_run else str(Path("/Users/gracker/.hermes/state/aiw-run-manifests") / f"{run_id}.json"),
                "result_path": manifest["result_path"],
                "evidence_path": evidence_path,
                "generated_at": now.isoformat(timespec="seconds"),
                "aiw_repo": str(AIW),
                "formal_report_path": formal_report_path,
                "allowed_changed_paths": manifest["expected_changed_paths"],
                "target": {
                    "path": str(rec["path"]),
                    "relative_path": rec["rel"],
                    "sha16": sha16(rec["text"]),
                    "sha256_utf8_16": sha16(rec["text"]),
                    "hash_contract": "SHA-256 of the exact UTF-8 decoded file text, first 16 lowercase hex characters; this is not a Git blob hash",
                    "frontmatter": rec["fm"],
                    "quality_flags": quality_flags(rec["fm"], rec["body"]),
                    "excerpt": rec["text"][:12000],
                },
                "materials": resolve_materials(mats),
                "open_findings": rec.get("open_findings", []),
                "constraints": mode_constraints(mode),
            }
            out["constraints"].insert(
                0,
                "Before editing, recompute target.sha256_utf8_16 as hashlib.sha256(Path(target.path).read_text(encoding='utf-8').encode('utf-8')).hexdigest()[:16] and compare it with manifest target_sha_before; never use git hash-object for this check.",
            )
    latest = state / "latest-context.json"
    if not args.dry_run:
        latest.write_text(json.dumps(json_safe(out), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.dry_run and out.get("status") == "polish_candidate_ready":
        (state / f"{out['run_id']}.json").write_text(json.dumps(json_safe(out), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(json_safe(out), ensure_ascii=False, indent=2))
    return 0 if out.get("status") != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
