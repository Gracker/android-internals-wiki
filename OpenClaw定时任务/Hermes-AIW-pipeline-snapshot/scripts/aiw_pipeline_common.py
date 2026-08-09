#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared contracts for AIW Hermes cron lanes.

This module centralizes the eligibility/status and per-run manifest contract so
selector, watchdog, and git-sync use the same definitions instead of drifting.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")
AIW = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki")
SRC = AIW / "src"
STATE_ROOT = Path("/Users/gracker/.hermes/state")
MANIFEST_DIR = STATE_ROOT / "aiw-run-manifests"
RESULT_DIR = STATE_ROOT / "aiw-run-results"
FORMAL_ROOT = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AIW自动化流水线")
CANONICAL_PARTS = {
    "part1-fundamentals": {
        "ch01-architecture", "ch02-rendering", "ch03-input",
        "ch04-memory", "ch05-cpu-power", "ch06-storage",
    },
    "part2-performance": {
        "ch07-smoothness", "ch08-responsiveness", "ch09-anr",
        "ch10-memory-perf", "ch11-power", "ch12-apk-network",
        "ch18-rendering-pipelines",
    },
    "part3-tools": {
        "ch13-perfetto", "ch14-other-tools", "ch15-methodology", "ch19-apm",
    },
    "part4-system": {"ch16-aosp", "ch17-oem"},
    "part5-app": {
        "ch20-stability", "ch21-startup", "ch22-rendering-practice",
        "ch23-memory-practice", "ch24-io-network", "ch25-power-size",
        "ch26-observability",
    },
}
LEASE_TTL_MINUTES = 90
GIT_SYNC_READY_STATUSES = {"agent-completed"}
LEASE_STATUSES = {"created", "leased"}
TERMINAL_MANIFEST_STATUSES = {
    "blocked",
    "committed-local",
    "completed-no-change",
    "expired",
    "needs-human-review",
    "pushed",
    "rejected",
    "superseded",
    "superseded-test",
}

TERMINAL_ACTIONS = {"body-applied", "applied", "rejected", "duplicate", "superseded"}
INELIGIBLE_ROUTE_PREFIXES = ("quarantined",)
MIN_ROUTE_CONFIDENCE = 30
HIGHER_ANDROID_VERSION = re.compile(
    r'(?:Android\s*(?:1[89]|[2-9][0-9])|'
    r'API(?:\s+level|[_\s]*LEVEL)?[_\s]*(?:3[8-9]|[4-9][0-9])|'
    r'(?:Build\.)?VERSION_CODES\.[A-Z0-9_]*(?:3[8-9]|[4-9][0-9])|'
    r'targetSdk(?:Version)?\s*[=:]?\s*(?:3[8-9]|[4-9][0-9])|'
    r'SDK_INT\s*(?:>=|>|==)\s*(?:3[8-9]|[4-9][0-9]))',
    re.I,
)
SOURCE_TODO_RE = re.compile(r"(?<![A-Za-z])(TODO|TBD|FIXME)(?![A-Za-z])", re.I)
EDITORIAL_PLACEHOLDER_RE = re.compile(
    r"\[\s*待验证(?:\s*[:：\]]|\s*$)|"
    r"(?:加工说明|后续(?:加工|补写|补充|完善|再核对))|"
    r"(?:(?:本节|本章|本文|作者)\s*)?(?:需要|待)(?:补写|补充)"
    r"(?:正文|内容|材料|来源|章节|示例|官方示例|工程边界)|"
    r"补充.{0,80}待验证项",
    re.I,
)
EVIDENCE_BOUNDARY_RE = re.compile(r"待验证|需要进一步验证|待进一步验证")


def is_higher_version_scope_exclusion(sentence: str) -> bool:
    high = HIGHER_ANDROID_VERSION.pattern
    patterns = [
        rf'(?:本文|本章|本节|正文|这里|本书|结论).{{0,120}}(?:不讨论|不涉及|不纳入|不采用|不依赖|不适用|不外推).{{0,48}}{high}',
        rf'(?:本文|本章|本节|正文|本书)?.{{0,12}}不(?:要)?把.{{0,60}}外推到.{{0,12}}{high}',
        rf'(?:不要|不得|不能|不应|不可).{{0,60}}(?:外推|纳入|采用|依赖|写入|作为结论).{{0,24}}{high}',
        rf'{high}.{{0,24}}(?:不进入|不纳入|不属于|超出).{{0,24}}(?:本文|本章|正文|本书|结论|范围|基线)',
        rf'(?:不|未)(?:把|将)?.{{0,12}}{high}.{{0,80}}(?:外推|写成|作为|纳入|进入).{{0,24}}(?:正文|结论|范围|基线)',
        rf'{high}.{{0,80}}(?:不|未)(?:应|会|能|可)?(?:被)?(?:外推|写成|作为|纳入|进入).{{0,24}}(?:正文|结论|范围|基线)',
        rf'(?:无|没有|不存在).{{0,12}}{high}.{{0,32}}(?:结论|内容|断言|主线)',
        rf'{high}.{{0,32}}(?:结论|内容|断言|主线).{{0,16}}(?:为零|没有|不存在|已移除|已删除)',
        rf'(?:未|不)(?:使用|引入|采用|依赖).{{0,48}}{high}',
        rf'(?:本文|本章|本节|正文|本书).{{0,120}}{high}.{{0,80}}(?:不|未)(?:会|能|可)?(?:被)?(?:反推|外推|纳入|写入|作为)',
    ]
    return any(re.search(pattern, sentence, re.I) for pattern in patterns)


def affirmative_higher_android_mentions(body: str):
    """Yield higher-than-Android-17 claims, excluding explicit scope disclaimers."""
    for raw_line in body.splitlines():
        line = re.sub(r'\s+', ' ', raw_line).strip()
        if not line or not HIGHER_ANDROID_VERSION.search(line):
            continue
        if is_higher_version_scope_exclusion(line):
            continue
        # One finding per source line is enough even when the same boundary is
        # written as both Android N and API M. Duplicate findings only consume
        # review/rework capacity without representing a second claim.
        match = HIGHER_ANDROID_VERSION.search(line)
        assert match is not None
        start = max(0, match.start() - 80)
        end = min(len(line), match.end() + 100)
        yield line[start:end]


def marker_kind(line: str) -> str | None:
    """Classify TODO-like prose without turning honest source limits into debt."""
    if SOURCE_TODO_RE.search(line):
        return "upstream-source-todo"
    if EDITORIAL_PLACEHOLDER_RE.search(line):
        return "editorial-placeholder"
    if EVIDENCE_BOUNDARY_RE.search(line):
        return "declared-evidence-boundary"
    return None


def run_git(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=str(AIW), text=True, capture_output=True, timeout=timeout, check=False)


def current_head() -> str:
    r = run_git(["rev-parse", "HEAD"])
    return r.stdout.strip() if r.returncode == 0 else ""


def sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def json_safe(value):
    """Recursively normalize PyYAML/path values before writing JSON contexts."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, set):
        return sorted((json_safe(item) for item in value), key=str)
    return str(value)


def is_canonical_chapter_path(path: Path | str) -> bool:
    p = Path(path)
    if p.is_absolute():
        try:
            p = p.relative_to(SRC)
        except ValueError:
            return False
    elif p.parts and p.parts[0] == "src":
        p = Path(*p.parts[1:])
    parts = p.parts
    return (
        len(parts) >= 3
        and parts[0] in CANONICAL_PARTS
        and parts[1] in CANONICAL_PARTS[parts[0]]
        and p.suffix == ".md"
        and p.name not in {"README.md", "SUMMARY.md"}
    )


def iter_canonical_chapters():
    for part, chapters in CANONICAL_PARTS.items():
        for chapter in sorted(chapters):
            root = SRC / part / chapter
            if not root.exists():
                continue
            yield from (
                path for path in root.rglob("*.md")
                if path.name not in {"README.md", "SUMMARY.md"}
            )


def finding_matches_target(row: dict, target_path: str, fm: dict | None = None) -> bool:
    fm = fm or {}
    aliases = {
        target_path,
        Path(target_path).stem,
        str(fm.get("chapter") or ""),
        str(fm.get("title") or ""),
    }
    source_paths = {str(path) for path in row.get("source_paths", []) if path}
    return (
        str(row.get("target_path") or "") == target_path
        or target_path in source_paths
        or str(row.get("chapter") or "") in aliases
    )


def matching_findings(
    rows: list[dict],
    target_path: str,
    fm: dict | None = None,
    *,
    status: str | None = "open",
    severities: set[str] | None = None,
) -> list[dict]:
    return [
        row for row in rows
        if isinstance(row, dict)
        and (status is None or row.get("status") == status)
        and (severities is None or row.get("severity") in severities)
        and finding_matches_target(row, target_path, fm)
    ]


def rel_to_aiw(path: Path | str) -> str:
    p = Path(path)
    if not p.is_absolute():
        norm = os.path.normpath(str(p))
        if norm == ".." or norm.startswith("../"):
            raise ValueError(f"path escapes AIW repo: {path}")
        return norm
    return str(p.resolve().relative_to(AIW.resolve()))


def porcelain_paths() -> list[str]:
    """Return changed paths from porcelain -z, handling rename/copy records."""
    r = run_git(["status", "--porcelain", "-z"])
    entries = [x for x in r.stdout.split("\0") if x]
    paths: list[str] = []
    i = 0
    while i < len(entries):
        entry = entries[i]
        status = entry[:2]
        path = entry[3:]
        if status and status[0] in {"R", "C"}:
            i += 1
            if i < len(entries):
                path = entries[i]
        if path:
            paths.append(path)
        i += 1
    return sorted(set(paths))


def dirty_paths_excluding(paths: list[str]) -> list[str]:
    allowed = {str(p) for p in paths}
    return [p for p in porcelain_paths() if p not in allowed]


def atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(json_safe(data), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(path)


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value))
        return dt if dt.tzinfo else dt.replace(tzinfo=TZ)
    except (TypeError, ValueError):
        return None


def expire_stale_manifests(now: datetime | None = None) -> int:
    """Expire abandoned pre-run leases so validation/no-op runs cannot block later work."""
    now = now or datetime.now(TZ)
    changed = 0
    if not MANIFEST_DIR.exists():
        return changed
    for p in MANIFEST_DIR.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("status") not in LEASE_STATUSES:
            continue
        expires_at = parse_iso(data.get("lease_expires_at"))
        if expires_at is None:
            created_at = parse_iso(data.get("created_at")) or now
            expires_at = created_at + timedelta(minutes=LEASE_TTL_MINUTES)
        if expires_at <= now:
            data["status"] = "expired"
            data["expired_at"] = now.isoformat()
            data["updated_at"] = now.isoformat()
            atomic_write_json(p, data)
            changed += 1
    return changed


def active_target_lease(target_path: str | None) -> dict | None:
    if not target_path:
        return None
    expire_stale_manifests()
    for p in MANIFEST_DIR.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("target_path") != target_path:
            continue
        if data.get("status") in LEASE_STATUSES | GIT_SYNC_READY_STATUSES | {"committed-local"}:
            data["manifest_path"] = str(p)
            return data
    return None


def unique_report_path(lane: str, run_id: str, now: datetime | None = None) -> Path:
    now = now or datetime.now(TZ)
    return FORMAL_ROOT / f"{now:%Y-%m-%d-%H%M%S}-{run_id}-{lane}.md"


def evidence_path(lane: str, run_id: str) -> Path:
    return STATE_ROOT / lane / f"{run_id}.json"


def create_manifest(
    *,
    lane: str,
    run_id: str,
    target_path: str | None,
    expected_changed_paths: list[str],
    finding_ids: list[str] | None = None,
    metadata: dict | None = None,
    formal_report_path: str | None = None,
    evidence_path: str | None = None,
    target_sha_before: str | None = None,
    lease_ttl_minutes: int = LEASE_TTL_MINUTES,
) -> dict:
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(MANIFEST_DIR, 0o700)
    os.chmod(RESULT_DIR, 0o700)
    existing = active_target_lease(target_path)
    if existing:
        raise RuntimeError(
            f"active-target-lease:{existing.get('run_id')}:{existing.get('status')}:{target_path}"
        )
    norm = []
    for p in expected_changed_paths:
        if not p:
            continue
        try:
            norm.append(rel_to_aiw(p))
        except Exception:
            # Formal reports/evidence outside the AIW repo are not staged by git,
            # but remain in the manifest as external artifacts for traceability.
            norm.append(str(p))
    now = datetime.now(TZ)
    result_path = RESULT_DIR / f"{run_id}.json"
    manifest_path = MANIFEST_DIR / f"{run_id}.json"
    if manifest_path.exists() or result_path.exists():
        raise RuntimeError(f"run-id-already-exists:{run_id}")
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "lane": lane,
        "base_sha": current_head(),
        "target_path": target_path,
        "target_sha_before": target_sha_before or "",
        "expected_changed_paths": sorted(set(norm)),
        "formal_report_path": formal_report_path or "",
        "evidence_path": evidence_path or "",
        "result_path": str(result_path),
        "finding_ids": finding_ids or [],
        "metadata": metadata or {},
        "status": "leased",
        "created_at": now.isoformat(),
        "lease_expires_at": (now + timedelta(minutes=max(5, lease_ttl_minutes))).isoformat(),
    }
    atomic_write_json(manifest_path, manifest)
    return manifest


def load_manifests(statuses: set[str] | None = None) -> list[dict]:
    """Load only manifests explicitly released by an agent result by default."""
    expire_stale_manifests()
    statuses = statuses or GIT_SYNC_READY_STATUSES
    out = []
    for p in sorted(MANIFEST_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and data.get("status") in statuses:
            data["manifest_path"] = str(p)
            out.append(data)
    return out


def mark_manifest(run_id: str, status: str, *, clear_fields: tuple[str, ...] = (), **fields) -> None:
    p = MANIFEST_DIR / f"{run_id}.json"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return
    for field in clear_fields:
        data.pop(field, None)
    data.update(fields)
    data["status"] = status
    data["updated_at"] = datetime.now(TZ).isoformat()
    atomic_write_json(p, data)


def strip_frontmatter_and_code(text: str) -> str:
    text = re.sub(r"^---\n.*?\n---\n?", "", text, flags=re.S)
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return text


def split_frontmatter_body(text: str) -> tuple[str, str]:
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    if not m:
        return "", text
    return m.group(1), text[m.end():]


def material_markers_for(path: str) -> set[str]:
    raw = str(path or "").strip().strip("`")
    if not raw:
        return set()
    p = Path(raw)
    base = p.name
    stem = p.stem
    return {raw, base, stem, f"[来源: {base}]", f"[source: {base}]", f"material_id:{stem}", f"material_id: {stem}"}


def material_applied_in_body(material_path: str, chapter_text: str) -> bool:
    body = strip_frontmatter_and_code(chapter_text)
    return any(marker and marker in body for marker in material_markers_for(material_path))


def source_index_eligibility(item: dict, *, chapter_text: str | None = None) -> tuple[bool, str]:
    action = str(item.get("action") or item.get("status") or "")
    if action in TERMINAL_ACTIONS:
        return False, f"terminal-action:{action}"
    if action.startswith(INELIGIBLE_ROUTE_PREFIXES):
        return False, f"terminal-action:{action}"
    route_status = str(item.get("route_status") or "")
    if route_status.startswith(INELIGIBLE_ROUTE_PREFIXES):
        return False, f"route-status:{route_status}"
    if route_status and route_status != "existing-chapter-routed":
        return False, f"route-status:{route_status}"
    try:
        rc = int(item.get("route_confidence")) if item.get("route_confidence") is not None else None
    except (TypeError, ValueError):
        rc = None
    if rc is not None and rc < MIN_ROUTE_CONFIDENCE:
        return False, f"low-route-confidence:{rc}"
    if not item.get("target_path"):
        return False, "missing-target_path"
    mat = str(item.get("path") or "").strip().strip("`")
    if not mat:
        return False, "missing-material_path"
    if chapter_text is not None and material_applied_in_body(mat, chapter_text):
        return False, "material-already-applied-in-body"
    return True, "eligible"


def classify_changed_markdown(path: str) -> str:
    """body-change/frontmatter-only/no-content-change for a staged or unstaged md path."""
    before_run = run_git(["show", f"HEAD:{path}"])
    before = before_run.stdout if before_run.returncode == 0 else ""
    current = AIW / path
    try:
        after = current.read_text(encoding="utf-8", errors="ignore") if current.exists() else ""
    except Exception:
        after = ""
    before_fm, before_body = split_frontmatter_body(before)
    after_fm, after_body = split_frontmatter_body(after)
    if before_body != after_body:
        return "body-change"
    if before_fm != after_fm:
        return "frontmatter-only"
    return "no-content-change"


def deletion_count(path: str) -> int:
    d = run_git(["diff", "--cached", "--", path]).stdout or run_git(["diff", "--", path]).stdout
    return sum(1 for line in d.splitlines() if line.startswith("-") and not line.startswith("---"))
