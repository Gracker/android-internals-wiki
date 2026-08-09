#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Daily AIW closed-loop throughput watchdog."""
from __future__ import annotations

import json
import os
import re
import subprocess
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from aiw_pipeline_common import (
    AIW as AIW_CANONICAL,
    MANIFEST_DIR,
    classify_changed_markdown,
    material_applied_in_body,
    source_index_eligibility,
    split_frontmatter_body,
)

TZ = ZoneInfo("Asia/Shanghai")
AIW = AIW_CANONICAL
FORMAL = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AIW自动化流水线/health")
STATE = Path("/Users/gracker/.hermes/state/aiw-throughput-watchdog")
CRON_OUT = Path("/Users/gracker/.hermes/cron/output")
AIW_JOB_IDS = {
    "body_apply": "2aa21bb1eb45",
    "review_finalize": "464ba760c0e3",
    "git_sync": "5fa9d7fe9e87",
    "deep_review": "a2fb41f345c8",
    "rework": "410de74688cd",
    "idle_audit": "fb934850da95",
    "draft_polish": "ef444f87d299",
    "daily_intake_deepresearch": "db79021b32a0",
    "daily_intake_tech_articles": "f50a04d870c3",
    "daily_intake_incremental": "2364b7bf9a07",
    "daily_intake_classify": "51d73c474658",
    "git_sync_morning": "d6f28d5a2e78",
    "pipeline_selftest": "2837b3bb3243",
    "quality_baseline": "a57d1850625a",
    "chinese_quality_deepseek": "ea4c4334aa21",
}


def run(cmd: list[str], cwd: Path = AIW, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, timeout=timeout)


def jload(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def git_lines(*args: str) -> list[str]:
    # Disable Git's C-style path quoting so Chinese chapter paths still count
    # as src/**/*.md changes in throughput metrics.
    r = run(["git", "-c", "core.quotepath=false", *args])
    return [x for x in r.stdout.splitlines() if x]


def since_iso(day: str) -> str:
    return f"{day}T00:00:00+08:00"


def commit_stats(day: str) -> dict:
    lines = git_lines("log", f"--since={since_iso(day)}", "--pretty=format:%h%x09%s", "--name-only")
    commits = []
    current = None
    touched = set()
    actions = Counter()
    change_types = Counter()
    committed_change_types = Counter()
    for line in lines:
        if "\t" in line and re.match(r"^[0-9a-f]{7,}\t", line):
            sha, subject = line.split("\t", 1)
            if not subject.startswith("[hermes-aiw]"):
                current = None
                continue
            current = {"sha": sha, "subject": subject, "files": []}
            commits.append(current)
            m = re.search(r"\] ([^:]+):", subject)
            if m: actions[m.group(1)] += 1
        elif current is not None and line.strip():
            path = line.strip()
            current["files"].append(path)
            if path.startswith("src/") and path.endswith(".md"):
                touched.add(path)
                committed_change_types[classify_committed_markdown(current["sha"], path)] += 1
    # Uncommitted classification is useful because git-sync is now separated from LLM lanes.
    for p in git_lines("status", "--porcelain"):
        path = p[3:]
        if path.startswith("src/") and path.endswith(".md"):
            change_types[classify_changed_markdown(path)] += 1
    return {
        "count": len(commits),
        "actions": dict(actions),
        "touched_chapters": len(touched),
        "committed_change_types": dict(committed_change_types),
        "uncommitted_change_types": dict(change_types),
        "recent": commits[:10],
    }


def classify_committed_markdown(sha: str, path: str) -> str:
    before = run(["git", "show", f"{sha}^:{path}"], timeout=60)
    after = run(["git", "show", f"{sha}:{path}"], timeout=60)
    before_fm, before_body = split_frontmatter_body(before.stdout if before.returncode == 0 else "")
    after_fm, after_body = split_frontmatter_body(after.stdout if after.returncode == 0 else "")
    if before_body != after_body:
        return "body-change"
    if before_fm != after_fm:
        return "frontmatter-only"
    return "no-content-change"


def source_stats() -> dict:
    idx = jload(AIW / "metadata/source-index.json", {"files": []})
    files = [x for x in idx.get("files", []) if isinstance(x, dict)] if isinstance(idx, dict) else []
    route = Counter(x.get("route_status") or "missing" for x in files)
    action = Counter(x.get("action") or x.get("status") or "missing" for x in files)
    eligibility = Counter()
    candidate_keys: set[tuple[str, str]] = set()
    for x in files:
        target = str(x.get("target_path") or "")
        chapter = AIW / target if target else None
        chapter_text = chapter.read_text(encoding="utf-8", errors="ignore") if chapter and chapter.exists() else None
        ok, reason = source_index_eligibility(x, chapter_text=chapter_text)
        eligibility[reason] += 1
        if ok:
            candidate_keys.add((target, str(x.get("path") or "")))
    queue = jload(AIW / "metadata/queue.json", [])
    queue_rows = queue if isinstance(queue, list) else queue.get("pending", queue.get("items", []))
    queue_reasons = Counter()
    for item in queue_rows if isinstance(queue_rows, list) else []:
        if not isinstance(item, dict) or item.get("status", "pending") != "pending":
            continue
        target = str(item.get("target_path") or "")
        if not target or target.endswith("README.md"):
            queue_reasons["missing-or-ineligible-target"] += 1
            continue
        chapter = AIW / target
        if not chapter.exists():
            queue_reasons["missing-target-file"] += 1
            continue
        chapter_text = chapter.read_text(encoding="utf-8", errors="ignore")
        materials = [str(x) for x in item.get("material_paths") or [] if x]
        if not materials:
            queue_reasons["missing-material"] += 1
            continue
        for material in materials:
            if material_applied_in_body(material, chapter_text):
                queue_reasons["material-already-applied-in-body"] += 1
            else:
                candidate_keys.add((target, material))
                queue_reasons["eligible"] += 1
    return {
        "total": len(files),
        "route_status": dict(route),
        "action": dict(action),
        "eligibility": dict(eligibility),
        "queue_eligibility": dict(queue_reasons),
        "apply_pending": len(candidate_keys),
        "apply_pending_unique": len(candidate_keys),
    }


def chapter_status() -> dict:
    c = Counter()
    for p in (AIW / "src").rglob("*.md"):
        if p.name in {"README.md", "SUMMARY.md"}: continue
        txt = p.read_text(encoding="utf-8", errors="ignore")[:2000]
        m = re.search(r"(?m)^status:\s*[\"']?([^\"'\n]+)", txt)
        c[m.group(1).strip() if m else "missing"] += 1
    return dict(c)


def log_counts(day: str) -> dict:
    out = {}
    for lane in ["deep-review", "rework", "audit", "review"]:
        root = AIW / "logs" / lane
        out[lane] = len(list(root.glob(f"{day}*.md"))) if root.exists() else 0
    return out


def parse_response_json(text: str) -> dict | None:
    if "## Response" in text:
        text = text.rsplit("## Response", 1)[-1]
    text = text.strip()
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S | re.I)
    candidates = fenced + [text]
    decoder = json.JSONDecoder()
    for candidate in candidates:
        for match in re.finditer(r"\{", candidate):
            try:
                value, _ = decoder.raw_decode(candidate[match.start():])
            except Exception:
                continue
            if isinstance(value, dict) and value.get("status"):
                return value
    return None


def classify_cron_output(path: Path) -> str:
    if path.stat().st_size == 0:
        return "empty-output"
    txt = path.read_text(encoding="utf-8", errors="ignore")
    response = parse_response_json(txt)
    if response:
        status = str(response.get("status") or "").strip().lower()
        if status in {"blocked", "needs-human-review"}:
            return status
        if status in {"no-candidate", "no-new-input", "completed-no-change", "empty-output"}:
            return status
        if status in {"changed", "metadata-only", "agent-completed", "pushed", "completed", "finalized", "ready-for-review"}:
            return "productive_or_completed"
        return "response-status:" + status
    tail = txt.rsplit("## Response", 1)[-1][-8000:]
    status_line = re.search(r"(?mi)^-?\s*status\s*:\s*([\w-]+)", tail)
    if status_line:
        status = status_line.group(1).lower()
        if status in {"blocked", "needs-human-review", "no-candidate", "no-new-input", "completed-no-change"}:
            return status
        if status in {"ok", "pushed", "completed"}:
            return "productive_or_completed"
        return "script-status:" + status
    if "[SILENT]" in tail:
        return "no-new-input"
    return "response-parse-error"


def cron_output_stats(day: str) -> dict:
    out = {}
    for name, jid in AIW_JOB_IDS.items():
        root = CRON_OUT / jid
        counts = Counter()
        if root.exists():
            for p in root.glob(f"{day}_*.md"):
                counts[classify_cron_output(p)] += 1
        out[name] = dict(counts)
    return out


def ci_stats() -> dict:
    wf_dir = AIW / ".github" / "workflows"
    workflows = list(wf_dir.glob("*.yml")) + list(wf_dir.glob("*.yaml")) if wf_dir.exists() else []
    if not workflows:
        return {"status": "disabled", "reason": "no .github/workflows/*.yml present"}
    r = run(["gh", "run", "list", "--limit", "8", "--json", "headSha,name,status,conclusion,url"], timeout=120)
    if r.returncode != 0:
        return {"status": "unavailable", "error": (r.stdout + r.stderr)[-800:]}
    try:
        runs = json.loads(r.stdout)
        head = run(["git", "rev-parse", "HEAD"], timeout=30).stdout.strip()
        if runs and all(x.get("headSha") != head for x in runs):
            return {"status": "stale", "head": head, "runs": runs}
        return {"status": "ok", "runs": runs}
    except Exception as e:
        return {"status": "parse_error", "error": str(e)}


def findings_stats() -> dict:
    data = jload(AIW / "metadata/review-findings.json", {"findings": []})
    rows = [x for x in data.get("findings", []) if isinstance(x, dict)] if isinstance(data, dict) else []
    return {"total": len(rows), "by_status": dict(Counter(x.get("status", "missing") for x in rows)), "by_severity": dict(Counter(x.get("severity", "missing") for x in rows))}


def manifest_stats() -> dict:
    rows = []
    for path in MANIFEST_DIR.glob("*.json") if MANIFEST_DIR.exists() else []:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return {
        "total": len(rows),
        "by_status": dict(Counter(str(x.get("status") or "missing") for x in rows)),
        "active": [
            {"run_id": x.get("run_id"), "lane": x.get("lane"), "target_path": x.get("target_path"), "status": x.get("status")}
            for x in rows if x.get("status") in {"leased", "agent-completed", "committed-local"}
        ][:30],
    }


def main() -> int:
    now = datetime.now(TZ)
    day = now.date().isoformat()
    STATE.mkdir(parents=True, exist_ok=True); os.chmod(STATE, 0o700)
    FORMAL.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "profile": "aiw-throughput-watchdog",
        "date": day,
        "generated_at": now.isoformat(),
        "commits": commit_stats(day),
        "source_index": source_stats(),
        "chapter_status": chapter_status(),
        "logs": log_counts(day),
        "cron_outputs": cron_output_stats(day),
        "review_findings": findings_stats(),
        "manifests": manifest_stats(),
        "ci": ci_stats(),
    }
    evidence = STATE / f"{day}.json"
    evidence.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(evidence, 0o600)
    formal = FORMAL / f"{day}-aiw-throughput-watchdog.md"
    ci_failed = [r for r in payload["ci"].get("runs", []) if r.get("conclusion") not in ("", "success", None)] if payload["ci"].get("status") == "ok" else []
    lines = [
        f"# AIW 闭环健康 · {day}",
        f"- status: {'attention-required' if ci_failed else 'completed'}",
        f"- commits_today: {payload['commits']['count']}",
        f"- chapters_touched_today: {payload['commits']['touched_chapters']}",
        f"- committed_change_types: {payload['commits']['committed_change_types']}",
        f"- logs_today: {payload['logs']}",
        f"- source-index: total={payload['source_index']['total']}, apply_pending={payload['source_index']['apply_pending']}, routes={payload['source_index']['route_status']}",
        f"- findings: {payload['review_findings']}",
        f"- manifests: {payload['manifests']}",
        f"- CI: {'failed=' + str(len(ci_failed)) if ci_failed else payload['ci'].get('status')}",
        f"- Obsidian: {formal}",
        f"- Evidence: {evidence}",
        "",
        "## Commit action mix",
        json.dumps(payload["commits"]["actions"], ensure_ascii=False, indent=2),
        "",
        "## Cron output mix",
        json.dumps(payload["cron_outputs"], ensure_ascii=False, indent=2),
        "",
        "## Recent commits",
    ]
    for c in payload["commits"]["recent"][:8]:
        lines.append(f"- `{c['sha']}` {c['subject']} ({len(c.get('files', []))} files)")
    if ci_failed:
        lines += ["", "## CI attention", *[f"- {r.get('name')}: {r.get('conclusion')} {r.get('url')}" for r in ci_failed]]
    body = "\n".join(lines) + "\n"
    formal.write_text(body, encoding="utf-8")
    print(body[:6000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
