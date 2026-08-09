#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Measure AIW publication readiness without editing the repository."""
from __future__ import annotations

import hashlib
import json
import os
import re
import statistics
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from aiw_pipeline_common import (
    AIW,
    FORMAL_ROOT,
    iter_canonical_chapters,
    marker_kind,
    matching_findings,
    split_frontmatter_body,
)

TZ = ZoneInfo("Asia/Shanghai")
SRC = AIW / "src"
STATE = Path("/Users/gracker/.hermes/state/aiw-quality-baseline")
REPORT_ROOT = FORMAL_ROOT / "quality-baseline"
FINDINGS = AIW / "metadata/review-findings.json"

CONTRAST_CORRECTION_RE = re.compile(
    r"不是[^。\n]{0,25}而是|不只是[^。\n]{0,25}还|并非[^。\n]{0,25}而是|"
    r"不仅仅是[^。\n]{0,25}更是|与其说"
)
FILLER_ADVERB_RE = re.compile(r"真正|实际上|其实|根本|彻底|确实")
EVALUATIVE_OPENER_RE = re.compile(r"最值得看|最值得|值得一看")
STRUCTURAL_META_RE = re.compile(
    r"接下来我将|下面我们来看|让我们来探讨|让我们来看看|接下来让我们|"
    r"首先|其次|最后"
)
MEANING_INFLATION_RE = re.compile(
    r"标志着|反映了(?:更大的)?趋势|奠定了?基础|体现了?价值|展现了?潜力|"
    r"这说明|这体现|这反映|这凸显|进一步说明|从侧面反映"
)
AI_STYLE_RE = re.compile(
    r"综上所述|总而言之|不难发现|显而易见|值得注意的是|需要指出的是|"
    r"核心在于|归根结底|赋能|抓手|底座|方法论输出|"
    r"不是[^。\n]{0,25}而是|不只是[^。\n]{0,25}还|并非[^。\n]{0,25}而是|"
    r"不仅仅是[^。\n]{0,25}更是|与其说|真正|实际上|其实|根本|彻底|确实|"
    r"最值得看|最值得|值得一看|接下来我将|下面我们来看|让我们来探讨|"
    r"让我们来看看|接下来让我们|首先|其次|最后|标志着|反映了(?:更大的)?趋势|"
    r"奠定了?基础|体现了?价值|展现了?潜力|这说明|这体现|这反映|这凸显|"
    r"进一步说明|从侧面反映"
)
OBSERVE_RE = re.compile(r"Perfetto|trace_processor|adb\s|dumpsys|命令|日志|指标|观测|排查|验证", re.I)
MECHANISM_RE = re.compile(r"机制|调用|流程|状态|线程|源码|数据结构|时序|边界")


def run_git(args: list[str], timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        cwd=str(AIW),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def parse_chapter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="ignore")
    fm_text, body = split_frontmatter_body(text)
    try:
        fm = yaml.safe_load(fm_text) or {}
    except Exception:
        fm = {}
    clean_body = re.sub(r"```.*?```", "", body, flags=re.S)
    clean_body = re.sub(r"<!--.*?-->", "", clean_body, flags=re.S)
    paragraphs = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", clean_body) if p.strip()]
    long_paragraphs = sum(len(p) > 650 for p in paragraphs)
    sources = fm.get("sources")
    source_count = len(sources) if isinstance(sources, list) else (1 if sources else 0)
    marker_counts = Counter()
    marker_samples = {
        "editorial-placeholder": [],
        "declared-evidence-boundary": [],
        "upstream-source-todo": [],
    }
    for raw_line in clean_body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        kind = marker_kind(line)
        if kind is None:
            continue
        marker_counts[kind] += 1
        if len(marker_samples[kind]) < 5:
            marker_samples[kind].append(line[:240])
    ai_style = len(AI_STYLE_RE.findall(clean_body))
    contrast_correction = len(CONTRAST_CORRECTION_RE.findall(clean_body))
    filler_adverbs = len(FILLER_ADVERB_RE.findall(clean_body))
    evaluative_openers = len(EVALUATIVE_OPENER_RE.findall(clean_body))
    structural_meta = len(STRUCTURAL_META_RE.findall(clean_body))
    meaning_inflation = len(MEANING_INFLATION_RE.findall(clean_body))
    observations = len(OBSERVE_RE.findall(clean_body))
    mechanisms = len(MECHANISM_RE.findall(clean_body))
    return {
        "path": str(path.relative_to(AIW)),
        "title": str(fm.get("title") or path.stem),
        "chapter": str(fm.get("chapter") or ""),
        "status": str(fm.get("status") or "missing"),
        "confidence": str(fm.get("confidence") or ""),
        "verification_date": str(fm.get("last_source_verified_at") or fm.get("last_verified") or ""),
        "source_count": source_count,
        "body_chars": len(body),
        "pending_markers": marker_counts["editorial-placeholder"],
        "editorial_placeholders": marker_counts["editorial-placeholder"],
        "declared_evidence_boundaries": marker_counts["declared-evidence-boundary"],
        "upstream_source_todos": marker_counts["upstream-source-todo"],
        "marker_samples": marker_samples,
        "ai_style_hits": ai_style,
        "contrast_correction_hits": contrast_correction,
        "filler_adverb_hits": filler_adverbs,
        "evaluative_opener_hits": evaluative_openers,
        "structural_meta_hits": structural_meta,
        "meaning_inflation_hits": meaning_inflation,
        "long_paragraphs": long_paragraphs,
        "observation_hits": observations,
        "mechanism_hits": mechanisms,
    }


def aliases(row: dict) -> set[str]:
    return {row["path"], Path(row["path"]).stem, row["chapter"], row["title"]}


def open_findings() -> list[dict]:
    data = load_json(FINDINGS, {"findings": []})
    rows = data.get("findings", []) if isinstance(data, dict) else []
    return [x for x in rows if isinstance(x, dict) and x.get("status") == "open"]


def risk_flags(row: dict, linked: list[dict]) -> list[str]:
    flags = []
    if row["status"] in {"ready-for-review", "finalized", "verified"}:
        if not row["verification_date"]: flags.append("missing-source-verification-date")
        if not row["source_count"]: flags.append("missing-sources")
        if not row["confidence"]: flags.append("missing-confidence")
    if row["editorial_placeholders"]: flags.append("editorial-placeholders")
    if row["body_chars"] < 3500: flags.append("thin-body")
    if row["mechanism_hits"] < 3: flags.append("thin-mechanism-explanation")
    if row["observation_hits"] < 2: flags.append("thin-observation-guidance")
    if row["ai_style_hits"]: flags.append("ai-style-language")
    if row["contrast_correction_hits"]: flags.append("contrast-correction-language")
    if row["filler_adverb_hits"] >= 5: flags.append("filler-adverb-overuse")
    if row["evaluative_opener_hits"]: flags.append("evaluative-opener")
    if row["structural_meta_hits"]: flags.append("structural-meta-language")
    if row["meaning_inflation_hits"]: flags.append("meaning-inflation-language")
    if row["long_paragraphs"] >= 3: flags.append("dense-long-paragraphs")
    if any(x.get("severity") == "P0" for x in linked): flags.append("open-P0")
    if any(x.get("severity") == "P1" for x in linked): flags.append("open-P1")
    return flags


def classify_commit_path(sha: str, path: str) -> tuple[str, str]:
    before = run_git(["show", f"{sha}^:{path}"], timeout=60)
    after = run_git(["show", f"{sha}:{path}"], timeout=60)
    before_fm, before_body = split_frontmatter_body(before.stdout if before.returncode == 0 else "")
    after_fm, after_body = split_frontmatter_body(after.stdout if after.returncode == 0 else "")
    if before_body != after_body:
        historical = re.compile(
            r"受保护大纲|历史(?:错误|原文|遗留)(?:提纲|大纲|标记)|"
            r"不作为(?:当前|本文)?技术结论|可引用正文从|OpenClaw\s*加工指引|流水线加工要求",
            re.I,
        )
        removed_historical = len(historical.findall(before_body)) > len(historical.findall(after_body))
        if removed_historical or len(before_body) - len(after_body) >= 1200:
            outcome = "wrong-content-deletion"
        else:
            diff = run_git(["diff", f"{sha}^", sha, "--", path], timeout=60).stdout
            technical = re.search(
                r"(?:android-[0-9]|frameworks/|kernel/|AOSP|API\s*[0-9]|源码|接口|状态机|"
                r"\b(?:class|struct|enum|fun|void|int|bool)\b)",
                diff,
                re.I,
            )
            outcome = "substantive-correction" if technical else "prose-only"
        return "body-change", outcome
    if before_fm != after_fm:
        evidence_fields = re.compile(
            r"^(?:[+-])(?:sources|last_source_verified_at|last_verified|last_verified_against|"
            r"confidence|status|pipeline_stage|task[269]_state):",
            re.M,
        )
        diff = run_git(["diff", f"{sha}^", sha, "--", path], timeout=60).stdout
        outcome = "metadata-evidence-only" if evidence_fields.search(diff) else "metadata-other"
        return "frontmatter-only", outcome
    return "no-content-change", "no-change"


def recent_automation_stats() -> dict:
    raw = run_git(["log", "--since=7 days ago", "--pretty=format:@@%H%x09%s", "--name-only"]).stdout
    commits = 0
    change_types = Counter()
    outcome_types = Counter()
    current_sha = ""
    current_is_aiw = False
    seen_pairs = set()
    for line in raw.splitlines():
        if line.startswith("@@"):
            sha, subject = line[2:].split("\t", 1)
            current_sha = sha
            current_is_aiw = subject.startswith("[hermes-aiw]")
            if current_is_aiw: commits += 1
            continue
        path = line.strip()
        if not current_is_aiw or not path.startswith("src/") or not path.endswith(".md"):
            continue
        key = (current_sha, path)
        if key in seen_pairs: continue
        seen_pairs.add(key)
        change_type, outcome = classify_commit_path(current_sha, path)
        change_types[change_type] += 1
        outcome_types[outcome] += 1
    total = sum(change_types.values())
    return {
        "commits": commits,
        "chapter_change_events": total,
        "change_types": dict(change_types),
        "outcome_types": dict(outcome_types),
        "body_change_ratio": round(change_types.get("body-change", 0) / total, 3) if total else 0,
    }


def main() -> int:
    now = datetime.now(TZ)
    chapters = [parse_chapter(path) for path in iter_canonical_chapters()]
    findings = open_findings()
    for row in chapters:
        linked = matching_findings(findings, row["path"], row, status="open")
        row["open_findings"] = [str(x.get("id") or "") for x in linked]
        row["risk_flags"] = risk_flags(row, linked)
        row["risk_score"] = sum({
            "open-P0": 100,
            "open-P1": 60,
            "missing-sources": 35,
            "missing-source-verification-date": 25,
            "missing-confidence": 25,
            "editorial-placeholders": 20,
            "thin-body": 20,
            "thin-mechanism-explanation": 15,
            "thin-observation-guidance": 12,
            "ai-style-language": 8,
            "contrast-correction-language": 10,
            "filler-adverb-overuse": 8,
            "evaluative-opener": 8,
            "structural-meta-language": 8,
            "meaning-inflation-language": 8,
            "dense-long-paragraphs": 5,
        }.get(flag, 0) for flag in row["risk_flags"])

    statuses = Counter(row["status"] for row in chapters)
    finalized = [row for row in chapters if row["status"] in {"finalized", "verified"}]
    risky_finalized = [row for row in finalized if row["risk_flags"]]
    publication_flag_counts = Counter(
        flag for row in finalized for flag in row["risk_flags"]
    )
    evidence_flags = {
        "open-P0", "open-P1", "missing-sources",
        "missing-source-verification-date", "missing-confidence",
        "editorial-placeholders",
    }
    evidence_risk_finalized = [
        row for row in finalized if evidence_flags.intersection(row["risk_flags"])
    ]
    editorial_risk_finalized = [
        row for row in finalized
        if {
            "ai-style-language", "contrast-correction-language", "filler-adverb-overuse",
            "evaluative-opener", "structural-meta-language", "meaning-inflation-language",
            "dense-long-paragraphs",
        }.intersection(row["risk_flags"])
    ]
    open_severity = Counter(str(x.get("severity") or "missing") for x in findings)
    recent = recent_automation_stats()
    saturation = "not-saturated"
    if open_severity.get("P0") or open_severity.get("P1"):
        reason = f"open findings remain: P0={open_severity.get('P0', 0)}, P1={open_severity.get('P1', 0)}"
    elif evidence_risk_finalized:
        reason = (
            f"{len(evidence_risk_finalized)} publication-state chapters still have "
            "source/date/confidence or editorial-placeholder debt"
        )
    elif len(editorial_risk_finalized) > max(3, len(finalized) // 100):
        reason = f"{len(editorial_risk_finalized)} publication-state chapters still trigger editorial-density heuristics"
    else:
        saturation = "near-saturation"
        reason = "no open P0/P1 and fewer than one percent of publication-state chapters trigger risk heuristics"

    candidates = [
        row for row in chapters
        if row["status"] in {"ready-for-review", "finalized"}
        and not any(flag in row["risk_flags"] for flag in {
            "open-P0",
            "open-P1",
            "missing-sources",
            "missing-source-verification-date",
            "missing-confidence",
            "editorial-placeholders",
        })
        and (row["ai_style_hits"] or row["long_paragraphs"] or row["observation_hits"] < 2)
    ]
    candidates.sort(key=lambda row: (
        0 if row["status"] == "ready-for-review" else 1,
        -row["long_paragraphs"],
        -row["ai_style_hits"],
        row["observation_hits"],
        row["path"],
    ))
    # Keep the complete ranked set.  The DeepSeek selector owns rotation and
    # picks never-reviewed chapters first, so truncating here would make it
    # cycle forever through the same small head of the list.
    chinese_review_candidates = candidates

    lengths = sorted(row["body_chars"] for row in chapters)
    payload = {
        "schema_version": 1,
        "profile": "aiw-quality-baseline",
        "generated_at": now.isoformat(),
        "head": run_git(["rev-parse", "HEAD"]).stdout.strip(),
        "chapter_count": len(chapters),
        "status_counts": dict(statuses),
        "body_chars": {
            "p10": lengths[len(lengths) // 10] if lengths else 0,
            "p50": int(statistics.median(lengths)) if lengths else 0,
            "p90": lengths[len(lengths) * 9 // 10] if lengths else 0,
        },
        "publication_state": {
            "count": len(finalized),
            "risk_count": len(risky_finalized),
            "risk_ratio": round(len(risky_finalized) / len(finalized), 3) if finalized else 0,
            "evidence_or_editorial_risk_count": len(evidence_risk_finalized),
            "evidence_or_pending_risk_count": len(evidence_risk_finalized),
            "editorial_risk_count": len(editorial_risk_finalized),
            "flag_counts": dict(publication_flag_counts),
            "missing_sources": sum(row["source_count"] == 0 for row in finalized),
            "pending_markers": sum(row["editorial_placeholders"] > 0 for row in finalized),
            "marker_classes": {
                "editorial_placeholders": {
                    "chapters": sum(row["editorial_placeholders"] > 0 for row in finalized),
                    "occurrences": sum(row["editorial_placeholders"] for row in finalized),
                    "paths": [row["path"] for row in finalized if row["editorial_placeholders"]],
                },
                "declared_evidence_boundaries": {
                    "chapters": sum(row["declared_evidence_boundaries"] > 0 for row in finalized),
                    "occurrences": sum(row["declared_evidence_boundaries"] for row in finalized),
                    "paths": [row["path"] for row in finalized if row["declared_evidence_boundaries"]],
                },
                "upstream_source_todos": {
                    "chapters": sum(row["upstream_source_todos"] > 0 for row in finalized),
                    "occurrences": sum(row["upstream_source_todos"] for row in finalized),
                    "paths": [row["path"] for row in finalized if row["upstream_source_todos"]],
                },
            },
            "thin_observation_guidance": sum(row["observation_hits"] < 2 for row in finalized),
        },
        "risk_categories": {
            "technical_blockers": {
                "chapters": sum(
                    bool({"open-P0", "open-P1"}.intersection(row["risk_flags"]))
                    for row in finalized
                ),
                "paths": [
                    row["path"] for row in finalized
                    if {"open-P0", "open-P1"}.intersection(row["risk_flags"])
                ],
            },
            "evidence_debt": {
                "chapters": sum(
                    bool({"missing-sources", "missing-source-verification-date", "missing-confidence"}.intersection(row["risk_flags"]))
                    for row in finalized
                ),
                "paths": [
                    row["path"] for row in finalized
                    if {"missing-sources", "missing-source-verification-date", "missing-confidence"}.intersection(row["risk_flags"])
                ],
            },
            "editorial_placeholders": {
                "chapters": sum(row["editorial_placeholders"] > 0 for row in finalized),
                "paths": [row["path"] for row in finalized if row["editorial_placeholders"]],
            },
            "stable_evidence_boundaries": {
                "chapters": sum(
                    row["declared_evidence_boundaries"] > 0 or row["upstream_source_todos"] > 0
                    for row in finalized
                ),
                "paths": [
                    row["path"] for row in finalized
                    if row["declared_evidence_boundaries"] or row["upstream_source_todos"]
                ],
            },
            "editorial_candidates": {
                "chapters": len(editorial_risk_finalized),
                "paths": [row["path"] for row in editorial_risk_finalized],
            },
        },
        "open_findings": {"count": len(findings), "by_severity": dict(open_severity)},
        "recent_automation": recent,
        "saturation": {"status": saturation, "reason": reason},
        "highest_risk_chapters": sorted(chapters, key=lambda row: (-row["risk_score"], row["path"]))[:40],
        "chinese_review_candidates": chinese_review_candidates,
    }

    STATE.mkdir(parents=True, exist_ok=True)
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    os.chmod(STATE, 0o700)
    stamp = now.strftime("%Y-%m-%d-%H%M%S")
    evidence = STATE / f"{stamp}.json"
    evidence.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(evidence, 0o600)
    latest = STATE / "latest.json"
    latest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(latest, 0o600)
    report = REPORT_ROOT / f"{stamp}-aiw-quality-baseline.md"
    lines = [
        f"# AIW 发布质量基线 · {now:%Y-%m-%d %H:%M}",
        "",
        f"- HEAD: `{payload['head']}`",
        f"- chapters: {payload['chapter_count']}",
        f"- status: {payload['status_counts']}",
        f"- publication_state: {payload['publication_state']}",
        f"- open_findings: {payload['open_findings']}",
        f"- recent_automation: {payload['recent_automation']}",
        f"- saturation: `{saturation}` — {reason}",
        f"- Evidence: {evidence}",
        "",
        "## Highest-risk chapters",
        "",
    ]
    for row in payload["highest_risk_chapters"][:25]:
        lines.append(f"- `{row['path']}` score={row['risk_score']} status={row['status']} flags={','.join(row['risk_flags'])}")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        "# AIW Quality Baseline\n"
        f"- status: {saturation}\n"
        f"- chapters: {len(chapters)}\n"
        f"- publication_state_risk: {len(risky_finalized)}/{len(finalized)}\n"
        f"- open_findings: {dict(open_severity)}\n"
        f"- recent_body_change_ratio: {recent['body_change_ratio']}\n"
        f"- report: {report}\n"
        f"- evidence: {evidence}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
