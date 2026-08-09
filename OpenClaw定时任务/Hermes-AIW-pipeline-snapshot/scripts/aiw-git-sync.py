#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Commit and push AIW automation outputs from the Android-Internal-Wiki repo.

Allowlist-based sync with descriptive OpenClaw-style commit messages. It syncs
generated AIW artifacts and metadata, but ignores suspicious/editor duplicate
files such as `.github/workflows/build 2.yml`.
"""
from __future__ import annotations

import json
import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from aiw_pipeline_common import deletion_count, load_manifests, mark_manifest, porcelain_paths

TZ = ZoneInfo("Asia/Shanghai")
REPO = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki")
STATE = Path("/Users/gracker/.hermes/state/aiw-git-sync")
LOCK = STATE / "sync.lock"
PENDING_MSG = STATE / "pending-commit-msg.txt"
FREEZE_GUARD = Path("/Users/gracker/.hermes/scripts/aiw-freeze-guard.py")
ALLOWLIST = [
    "intake/",
    "metadata/",
    "logs/",
    "src/",
    "README.md",
    "SUMMARY.md",
]


def run(cmd: list[str], check: bool = False, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(REPO), text=True, capture_output=True, timeout=timeout, check=check)


def git(*args: str, check: bool = False, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], check=check, timeout=timeout)


def acquire_lock() -> bool:
    STATE.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        try:
            if datetime.now().timestamp() - LOCK.stat().st_mtime > 7200:
                LOCK.unlink()
                fd = os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            else:
                return False
        except FileNotFoundError:
            return acquire_lock()
    with os.fdopen(fd, "w") as f:
        f.write(str(os.getpid()))
    return True


def release_lock() -> None:
    try:
        LOCK.unlink()
    except FileNotFoundError:
        pass


def allowed_changed_paths() -> list[str]:
    return sorted({
        path for path in porcelain_paths()
        if any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in ALLOWLIST)
    })


def disallowed_changed_paths() -> list[str]:
    allowed = set(allowed_changed_paths())
    return sorted(set(porcelain_paths()) - allowed)


def parse_frontmatter(path: str) -> dict[str, str]:
    p = REPO / path
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")[:12000]
    except Exception:
        return {}
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.lstrip().startswith(("#", "-")):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"\'')
    return fm


def status_delta(path: str) -> str | None:
    d = git("diff", "--cached", "-U0", "--", path).stdout
    old = new = None
    for line in d.splitlines():
        if line.startswith("-status:"):
            old = line.split(":", 1)[1].strip().strip('"\'')
        elif line.startswith("+status:"):
            new = line.split(":", 1)[1].strip().strip('"\'')
    if old and new and old != new:
        return f"{old}→{new}"
    if new:
        return new
    return None


def path_title(path: str) -> str:
    fm = parse_frontmatter(path)
    chapter = fm.get("chapter") or ""
    title = fm.get("title") or Path(path).stem.replace("-", " ")
    prefix = f"{chapter} " if chapter else ""
    s = (prefix + title).strip()
    return re.sub(r"\s+", " ", s)[:70]


def source_index_route_summary() -> str | None:
    d = git("diff", "--cached", "-U0", "--", "metadata/source-index.json").stdout
    if not d:
        return None
    routed = d.count('+      "route_status": "existing-chapter-routed"')
    quarantined = d.count('+      "route_status": "quarantined-non-aiw-or-aggregate"')
    unrouted = d.count('+      "route_status": "unrouted-existing-chapter-needed"')
    parts = []
    if routed: parts.append(f"route {routed}")
    if quarantined: parts.append(f"quarantine {quarantined}")
    if unrouted: parts.append(f"mark {unrouted} unrouted")
    return ", ".join(parts) if parts else None


def findings_summary() -> str | None:
    d = git("diff", "--cached", "-U0", "--", "metadata/review-findings.json").stdout
    if not d:
        return None
    opened = d.count('+      "status": "open"')
    fixed = d.count('+      "status": "fixed"')
    verified = d.count('+      "status": "verified"')
    parts = []
    if opened: parts.append(f"open {opened}")
    if fixed: parts.append(f"fix {fixed}")
    if verified: parts.append(f"verify {verified}")
    return ", ".join(parts) if parts else "update findings"


def infer_stage(staged: list[str]) -> str:
    joined = "\n".join(staged)
    if "metadata/review-findings.json" in staged:
        return "review-findings"
    if "metadata/source-index.json" in staged and source_index_route_summary():
        return "source-route"
    if "metadata/queue.json" in staged and not any(p.startswith("src/") for p in staged):
        return "queue-state"
    if any(p.startswith("logs/deep-review/") for p in staged):
        return "deep-review"
    if any(p.startswith("logs/audit/") for p in staged):
        return "audit"
    if any(p.startswith("logs/rework") for p in staged):
        return "rework"
    srcs = [p for p in staged if p.startswith("src/") and p.endswith(".md")]
    deltas = [status_delta(p) for p in srcs]
    if any(d and "finalized" in d for d in deltas):
        return "review-finalize"
    if any(d and "needs-rework" in d for d in deltas):
        return "rework"
    if "body-applied" in joined or "queue.json" in joined or "source-index.json" in joined:
        return "body-apply"
    if any(p.startswith("intake/") for p in staged):
        return "intake"
    if srcs:
        return "polish"
    if any(p.startswith("metadata/") for p in staged):
        return "metadata"
    return "sync"


def pending_message_if_valid(staged: list[str]) -> str | None:
    if not PENDING_MSG.exists():
        return None
    msg = PENDING_MSG.read_text(encoding="utf-8", errors="ignore").strip()
    if not msg:
        return None
    # Keep user/agent-provided messages bounded and single-commit safe.
    lines = [x.rstrip() for x in msg.splitlines()]
    subject = lines[0][:160]
    body = "\n".join(lines[1:])[:3000]
    changed = "\n".join(f"- {p}" for p in staged[:40])
    return subject + ("\n" + body if body else "") + "\n\nChanged files:\n" + changed


def build_commit_message(staged: list[str], manifest: dict | None = None) -> str:
    pending = pending_message_if_valid(staged) if manifest is None else None
    if pending:
        return pending
    day = datetime.now(TZ).strftime("%Y-%m-%d")
    srcs = [p for p in staged if p.startswith("src/") and p.endswith(".md")]
    stage = infer_stage(staged)
    if manifest:
        lane = manifest.get("lane") or stage
        run_id = manifest.get("run_id") or "unknown-run"
        target = manifest.get("target_path") or (srcs[0] if srcs else "metadata")
        title = path_title(target) if target.startswith("src/") else target
        subject = f"[hermes-aiw] {lane}: {title} ({run_id})"[:180]
        body = [
            "Generated by Hermes AIW scheduled tasks with per-run manifest.",
            f"run_id: {run_id}",
            f"lane: {lane}",
            f"base_sha: {manifest.get('base_sha')}",
            f"manifest: {manifest.get('manifest_path')}",
            "",
            "Changed files:",
            *[f"- {p}" for p in staged[:60]],
        ]
        return subject + "\n\n" + "\n".join(body)
    if srcs:
        main = srcs[0]
        title = path_title(main)
        delta = status_delta(main)
        suffix = f" — {delta}" if delta else ""
        subject = f"[hermes-aiw] {stage}: {title}{suffix}"
    elif stage == "source-route":
        subject = f"[hermes-aiw] source-route: {source_index_route_summary() or 'route source-index materials'}"
    elif stage == "review-findings":
        subject = f"[hermes-aiw] review-findings: {findings_summary() or 'update findings'}"
    elif stage == "queue-state":
        subject = f"[hermes-aiw] queue-state: update queue metadata {day}"
    else:
        subject = f"[hermes-aiw] {stage}: automation outputs {day}"
    if len(srcs) > 1:
        subject += f" (+{len(srcs)-1} chapters)"
    other_count = len([p for p in staged if p not in srcs])
    if other_count:
        subject += f" + {other_count} files"
    subject = subject[:180]
    body = [
        "Generated by Hermes AIW scheduled tasks.",
        "",
        "Changed files:",
        *[f"- {p}" for p in staged[:60]],
    ]
    if len(staged) > 60:
        body.append(f"- ... {len(staged) - 60} more")
    return subject + "\n\n" + "\n".join(body)


def select_manifest_for_paths(paths: list[str]) -> tuple[dict | None, list[str], str | None]:
    """Return manifest and exact stage paths, or reason for blocking.

    Source changes require a manifest. Metadata/intake/log-only changes may use
    legacy mode so script-only collection jobs still publish safely.
    """
    manifests = load_manifests()
    dirty = set(paths)
    src_dirty = {p for p in dirty if p.startswith("src/") and p.endswith(".md")}
    if not manifests:
        if src_dirty:
            return None, [], "src-dirty-without-manifest"
        return None, paths, None
    for m in manifests:
        repo_expected = {p for p in m.get("expected_changed_paths", []) if not p.startswith("/")}
        hit = sorted(dirty & repo_expected)
        if not hit:
            continue
        extra = sorted(dirty - repo_expected)
        if extra:
            return m, [], "dirty-paths-outside-manifest:" + ", ".join(extra[:20])
        if m.get("base_sha") and git("rev-parse", "HEAD").stdout.strip() != m.get("base_sha"):
            return m, [], "head-mismatch"
        return m, hit, None
    if src_dirty:
        return None, [], "src-dirty-not-covered-by-any-manifest"
    # There are stale manifests, but current dirty files are non-src legacy outputs.
    return None, paths, None


def validate_manifest_release(manifest: dict, paths: list[str]) -> str | None:
    if manifest.get("status") != "agent-completed":
        return f"manifest-not-agent-completed:{manifest.get('status')}"
    result_path = Path(str(manifest.get("result_path") or ""))
    evidence_path = Path(str(manifest.get("evidence_path") or ""))
    report_path = Path(str(manifest.get("formal_report_path") or ""))
    for label, path in [("result", result_path), ("evidence", evidence_path), ("formal-report", report_path)]:
        if not str(path) or not path.exists() or not path.is_file() or path.stat().st_size == 0:
            return f"missing-{label}:{path}"
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return f"invalid-result-json:{exc}"
    if result.get("run_id") != manifest.get("run_id") or not result.get("validated"):
        return "result-not-validated-for-manifest"
    actual = sorted(result.get("actual_changed_paths") or [])
    if actual != sorted(paths):
        return f"result-dirty-path-mismatch:result={actual}:git={sorted(paths)}"
    expected_hashes = result.get("actual_path_sha256")
    if not isinstance(expected_hashes, dict) or expected_hashes != manifest.get("actual_path_sha256"):
        return "validated-path-hashes-missing-or-manifest-mismatch"
    current_hashes = {
        path: (hashlib.sha256((REPO / path).read_bytes()).hexdigest() if (REPO / path).exists() else "<deleted>")
        for path in sorted(paths)
    }
    if expected_hashes != current_hashes:
        return f"dirty-content-changed-after-validation:expected={expected_hashes}:actual={current_hashes}"
    artifact_hashes = result.get("artifact_sha256")
    if not isinstance(artifact_hashes, dict) or artifact_hashes != manifest.get("artifact_sha256"):
        return "validated-artifact-hashes-missing-or-manifest-mismatch"
    current_artifact_hashes = {
        "formal_report": hashlib.sha256(report_path.read_bytes()).hexdigest(),
        "evidence": hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
    }
    if artifact_hashes != current_artifact_hashes:
        return "external-artifact-changed-after-validation"
    return None


def run_staged_gates(staged: list[str]) -> tuple[bool, str]:
    checks: list[tuple[str, list[str]]] = [
        ("diff-check", ["git", "diff", "--cached", "--check"]),
        ("summary-links", [sys.executable, "scripts/check-summary-links.py"]),
    ]
    srcs = [p for p in staged if p.startswith("src/") and p.endswith(".md")]
    if srcs:
        checks.append(("metadata", [sys.executable, "scripts/check-metadata.py", "--files", *srcs]))
    output = []
    for name, cmd in checks:
        r = run(cmd, timeout=180)
        output.append(f"[{name}] rc={r.returncode}\n{(r.stdout + r.stderr)[-1200:]}")
        if r.returncode != 0:
            return False, "\n".join(output)
    return True, "\n".join(output)


def retry_pending_push() -> tuple[bool, str]:
    upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    if upstream.returncode != 0:
        return True, "no-upstream"
    ahead = git("rev-list", "--count", "@{upstream}..HEAD")
    try:
        count = int(ahead.stdout.strip())
    except ValueError:
        count = 0
    if count <= 0:
        return True, "no-pending-commits"
    pushed = git("push", "origin", "HEAD", timeout=180)
    if pushed.returncode != 0:
        return False, (pushed.stdout + pushed.stderr)[-1800:]
    head = git("rev-parse", "--short", "HEAD").stdout.strip()
    for manifest in load_manifests({"committed-local"}):
        run_id = manifest.get("run_id")
        if run_id:
            mark_manifest(str(run_id), "pushed", push_retry=True, pushed_head=head)
    return True, f"pushed-{count}-pending-commits"


def large_diff_block_reason(staged: list[str]) -> str | None:
    srcs = [p for p in staged if p.startswith("src/") and p.endswith(".md")]
    if len(srcs) > 3:
        return f"too-many-src-files:{len(srcs)}"
    for p in srcs:
        deleted = deletion_count(p)
        if deleted > 120:
            return f"large-deletion:{p}:{deleted}"
    return None


def main() -> int:
    if not REPO.exists():
        print(f"# AIW Git Sync\n- status: error\n- reason: repo missing: {REPO}")
        return 2
    if not acquire_lock():
        return 0
    try:
        disallowed = disallowed_changed_paths()
        if disallowed:
            print(
                "# AIW Git Sync\n"
                "- status: blocked\n"
                "- reason: dirty paths outside automation allowlist\n"
                f"- dirty_paths: {', '.join(disallowed[:30])}"
            )
            return 2
        paths = allowed_changed_paths()
        if not paths:
            push_ok, push_note = retry_pending_push()
            if not push_ok:
                print("# AIW Git Sync\n- status: push_retry_failed\n```text\n" + push_note + "\n```")
                return 2
            branch = git("branch", "--show-current").stdout.strip() or "HEAD"
            pull = git("pull", "--ff-only", "origin", branch, timeout=180)
            if pull.returncode != 0:
                print("# AIW Git Sync\n- status: pull_failed\n- 修改内容: 无本地变更，但无法 ff-only 同步\n```text\n" + (pull.stdout + pull.stderr)[-1800:] + "\n```")
                return 2
            return 0

        manifest, stage_paths, block_reason = select_manifest_for_paths(paths)
        if block_reason:
            if manifest and manifest.get("run_id"):
                mark_manifest(str(manifest["run_id"]), "blocked", block_reason=block_reason, dirty_paths=paths)
            print(
                "# AIW Git Sync\n"
                "- status: blocked\n"
                f"- reason: {block_reason}\n"
                "- 修改内容: 未提交，避免把非本轮变更扫入同一提交\n"
                f"- dirty_paths: {', '.join(paths[:30])}"
            )
            return 2

        if manifest:
            release_error = validate_manifest_release(manifest, stage_paths)
            if release_error:
                mark_manifest(str(manifest.get("run_id")), "needs-human-review", block_reason=release_error, dirty_paths=paths)
                print(f"# AIW Git Sync\n- status: blocked\n- reason: {release_error}\n- 修改内容: manifest 产物未通过提交前复核")
                return 2

        if "src/SUMMARY.md" in stage_paths:
            summary_check = run([sys.executable, "scripts/check-summary-links.py"], timeout=120)
            if summary_check.returncode != 0:
                print("# AIW Git Sync\n- status: summary_check_failed\n- 修改内容: 未提交，SUMMARY.md 存在 mdBook 断链或空格路径\n```text\n" + (summary_check.stdout + summary_check.stderr)[-2000:] + "\n```")
                return 2

        git("add", "--", *stage_paths, check=True)
        staged = git("diff", "--cached", "--name-only").stdout.splitlines()
        if not staged:
            return 0

        reason = large_diff_block_reason(staged)
        if reason:
            git("reset", "--", *staged)
            if manifest and manifest.get("run_id"):
                mark_manifest(str(manifest["run_id"]), "needs-human-review", block_reason=reason, actual_changed_paths=staged)
            print(f"# AIW Git Sync\n- status: needs-human-review\n- reason: {reason}\n- 修改内容: 未提交，大 diff 需要人工 gate\n- 影响范围: {', '.join(staged[:30])}")
            return 2

        gates_ok, gates_output = run_staged_gates(staged)
        if not gates_ok:
            git("reset", "--", *staged)
            if manifest and manifest.get("run_id"):
                mark_manifest(str(manifest["run_id"]), "needs-human-review", block_reason="staged-local-gate-failed")
            print("# AIW Git Sync\n- status: local_gate_failed\n- 修改内容: 未提交\n```text\n" + gates_output[-3000:] + "\n```")
            return 2

        if FREEZE_GUARD.exists():
            guard = run([sys.executable, str(FREEZE_GUARD)], timeout=120)
            if guard.returncode != 0:
                git("reset", "--", *staged)
                print((guard.stdout + guard.stderr)[-3000:])
                return guard.returncode

        msg = build_commit_message(staged, manifest)
        c = git("commit", "-m", msg, timeout=120)
        if c.returncode != 0:
            if "nothing to commit" in (c.stdout + c.stderr).lower():
                return 0
            print("# AIW Git Sync\n- status: commit_failed\n```text\n" + (c.stdout + c.stderr)[-1800:] + "\n```")
            return 2

        sha = git("rev-parse", "--short", "HEAD").stdout.strip()
        if manifest and manifest.get("run_id"):
            mark_manifest(str(manifest["run_id"]), "committed-local", actual_changed_paths=staged, commit_sha=sha)

        if PENDING_MSG.exists():
            try:
                PENDING_MSG.unlink()
            except FileNotFoundError:
                pass

        p = git("push", "origin", "HEAD", timeout=180)
        if p.returncode != 0:
            print("# AIW Git Sync\n- status: push_failed\n- 修改内容: 已本地 commit，但 GitHub push 失败\n- 影响范围: " + ", ".join(staged[:20]) + "\n```text\n" + (p.stdout + p.stderr)[-1800:] + "\n```")
            return 2

        if manifest and manifest.get("run_id"):
            mark_manifest(str(manifest["run_id"]), "pushed", actual_changed_paths=staged, commit_sha=sha)
        print(
            f"# AIW Git Sync · {datetime.now(TZ).date().isoformat()}\n"
            f"- status: pushed\n"
            f"- 修改内容: 已提交并推送 {len(staged)} 个 AIW 落盘文件\n"
            f"- commit: {msg.splitlines()[0]}\n"
            f"- GitHub: origin HEAD @ {sha}\n"
            f"- 影响范围: {', '.join(staged[:20])}"
        )
        return 0
    finally:
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())
