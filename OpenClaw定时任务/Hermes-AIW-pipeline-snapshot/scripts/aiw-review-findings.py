#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manage AIW review findings as a machine-readable issue pool.

Examples:
  aiw-review-findings.py add --chapter src/...md --lane deep-review --severity P1 --type missing-source --summary "..."
  aiw-review-findings.py close --id finding-... --status fixed --run-id 20260725-...
  aiw-review-findings.py list --status open --chapter src/...md
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")
AIW = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki")
FINDINGS = AIW / "metadata/review-findings.json"
VALID_STATUS = {"open", "fixed", "verified", "wontfix"}
VALID_SEVERITY = {"P0", "P1", "P2", "P3"}


def load() -> dict:
    if not FINDINGS.exists():
        return {"schema_version": 1, "findings": []}
    try:
        data = json.loads(FINDINGS.read_text(encoding="utf-8"))
    except Exception:
        data = {"schema_version": 1, "findings": []}
    data.setdefault("schema_version", 1)
    data.setdefault("findings", [])
    return data


def save(data: dict) -> None:
    FINDINGS.parent.mkdir(parents=True, exist_ok=True)
    tmp = FINDINGS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(FINDINGS)


def make_id(chapter: str, summary: str, ftype: str) -> str:
    seed = f"{chapter}\n{ftype}\n{summary}".encode("utf-8", errors="ignore")
    return "finding-" + hashlib.sha1(seed).hexdigest()[:12]


def add(args: argparse.Namespace) -> int:
    if args.severity not in VALID_SEVERITY:
        raise SystemExit(f"invalid severity: {args.severity}")
    data = load()
    fid = args.id or make_id(args.chapter, args.summary, args.type)
    now = datetime.now(TZ).isoformat()
    existing = next((f for f in data["findings"] if f.get("id") == fid), None)
    payload = {
        "id": fid,
        "chapter": args.chapter,
        "severity": args.severity,
        "type": args.type,
        "summary": args.summary,
        "details": args.details or "",
        "status": "open",
        "created_by": args.lane,
        "created_run_id": args.run_id,
        "created_at": now,
        "source_paths": [x for x in (args.source or []) if x],
        "log_path": args.log_path or "",
        "updated_at": now,
    }
    if existing:
        existing.update({k: v for k, v in payload.items() if v not in (None, "", [])})
        existing.setdefault("status", "open")
        existing["updated_at"] = now
    else:
        data["findings"].append(payload)
    save(data)
    print(json.dumps({"status": "ok", "id": fid, "path": str(FINDINGS)}, ensure_ascii=False, indent=2))
    return 0


def close(args: argparse.Namespace) -> int:
    if args.status not in VALID_STATUS - {"open"}:
        raise SystemExit(f"invalid closing status: {args.status}")
    data = load()
    found = False
    now = datetime.now(TZ).isoformat()
    for f in data["findings"]:
        if f.get("id") == args.id:
            found = True
            f["status"] = args.status
            f["closed_by"] = args.lane
            f["closed_run_id"] = args.run_id
            f["close_note"] = args.note or ""
            f["updated_at"] = now
            if args.commit:
                f["closed_commit"] = args.commit
            break
    if not found:
        raise SystemExit(f"finding not found: {args.id}")
    save(data)
    print(json.dumps({"status": "ok", "id": args.id, "new_status": args.status}, ensure_ascii=False, indent=2))
    return 0


def list_findings(args: argparse.Namespace) -> int:
    data = load()
    rows = [f for f in data.get("findings", []) if isinstance(f, dict)]
    if args.status:
        rows = [f for f in rows if f.get("status") == args.status]
    if args.chapter:
        rows = [f for f in rows if f.get("chapter") == args.chapter]
    sev_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    rows.sort(key=lambda f: (sev_order.get(f.get("severity", "P3"), 9), f.get("updated_at", "")), reverse=False)
    print(json.dumps({"status": "ok", "count": len(rows), "findings": rows[: args.limit]}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--id")
    a.add_argument("--chapter", required=True)
    a.add_argument("--lane", required=True)
    a.add_argument("--run-id", default="")
    a.add_argument("--severity", default="P2")
    a.add_argument("--type", required=True)
    a.add_argument("--summary", required=True)
    a.add_argument("--details", default="")
    a.add_argument("--source", action="append")
    a.add_argument("--log-path", default="")
    c = sub.add_parser("close")
    c.add_argument("--id", required=True)
    c.add_argument("--status", required=True, choices=sorted(VALID_STATUS - {"open"}))
    c.add_argument("--lane", required=True)
    c.add_argument("--run-id", default="")
    c.add_argument("--commit", default="")
    c.add_argument("--note", default="")
    l = sub.add_parser("list")
    l.add_argument("--status")
    l.add_argument("--chapter")
    l.add_argument("--limit", type=int, default=50)
    args = ap.parse_args()
    return {"add": add, "close": close, "list": list_findings}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
