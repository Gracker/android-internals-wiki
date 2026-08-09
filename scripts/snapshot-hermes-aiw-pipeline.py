#!/usr/bin/env python3
"""Create a reviewable, secret-minimized snapshot of the live Hermes AIW pipeline."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("/Users/gracker/.hermes/scripts")
JOBS = Path("/Users/gracker/.hermes/cron/jobs.json")
DEST = ROOT / "OpenClaw定时任务/Hermes-AIW-pipeline-snapshot"
SCRIPT_DEST = DEST / "scripts"
TZ = ZoneInfo("Asia/Shanghai")

JOB_FIELDS = (
    "id", "job_id", "name", "state", "schedule", "script", "no_agent",
    "model", "provider", "workdir", "prompt", "toolsets", "skills",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    SCRIPT_DEST.mkdir(parents=True, exist_ok=True)
    sources = sorted({*SOURCE.glob("aiw-*.py"), *SOURCE.glob("aiw_*.py")})
    manifest = []
    for source in sources:
        target = SCRIPT_DEST / source.name
        shutil.copy2(source, target)
        manifest.append({
            "path": f"scripts/{source.name}",
            "source": str(source),
            "sha256": sha256(target),
            "bytes": target.stat().st_size,
        })

    raw = json.loads(JOBS.read_text(encoding="utf-8"))
    jobs = raw if isinstance(raw, list) else raw.get("jobs", [])
    selected = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        haystack = json.dumps(job, ensure_ascii=False)
        if "aiw" not in str(job.get("name") or "").lower() and "Android-Internal-Wiki" not in haystack:
            continue
        # Delivery endpoints and unrelated provider metadata are deliberately
        # excluded. The remaining object is sufficient for prompt/schedule review.
        selected.append({key: job[key] for key in JOB_FIELDS if key in job})
    selected.sort(key=lambda row: str(row.get("name") or ""))
    jobs_snapshot = DEST / "jobs.aiw.redacted.json"
    jobs_snapshot.write_text(
        json.dumps({"schema_version": 1, "jobs": selected}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest.append({
        "path": jobs_snapshot.name,
        "source": str(JOBS),
        "sha256": sha256(jobs_snapshot),
        "bytes": jobs_snapshot.stat().st_size,
        "redacted": True,
    })
    snapshot_manifest = DEST / "manifest.json"
    snapshot_manifest.write_text(
        json.dumps({
            "schema_version": 1,
            "generated_at": datetime.now(TZ).isoformat(),
            "android_platform_ceiling": "Android 17 / API 37",
            "files": manifest,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"snapshot_files={len(manifest)} destination={DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
