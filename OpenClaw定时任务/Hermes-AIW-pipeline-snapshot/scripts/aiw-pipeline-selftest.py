#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only/temporary regression tests for the active AIW automation."""
from __future__ import annotations

import importlib.util
import hashlib
import json
import subprocess
import tempfile
from datetime import date, datetime
from pathlib import Path

import aiw_pipeline_common as common

SCRIPTS = Path("/Users/gracker/.hermes/scripts")
JOBS = Path("/Users/gracker/.hermes/cron/jobs.json")


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), SCRIPTS / name)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []

    normalized = common.json_safe({
        "date": date(2026, 8, 9),
        "nested": [{"datetime": datetime(2026, 8, 9, 1, 2, 3)}],
        "path": Path("src/example.md"),
    })
    check(normalized["date"] == "2026-08-09", "json_safe did not normalize date", errors)
    check(
        normalized["nested"][0]["datetime"] == "2026-08-09T01:02:03",
        "json_safe did not normalize nested datetime",
        errors,
    )
    check(normalized["path"] == "src/example.md", "json_safe did not normalize Path", errors)
    check(
        common.is_canonical_chapter_path("src/part1-fundamentals/ch01-architecture/example.md"),
        "canonical chapter path was rejected",
        errors,
    )
    check(
        not common.is_canonical_chapter_path("src/preface/how-to-use.md"),
        "preface leaked into canonical chapter scope",
        errors,
    )

    watchdog = load_script("aiw-throughput-watchdog.py")
    changed = '{"status":"changed","changed_paths":["src/a.md"],"blocked_reason":""}'
    no_change = '{"status":"completed-no-change","changed_paths":[],"blocked_reason":""}'
    check(watchdog.parse_response_json(changed).get("status") == "changed", "watchdog failed to parse changed JSON", errors)
    check(watchdog.parse_response_json(no_change).get("status") == "completed-no-change", "watchdog failed to parse no-change JSON", errors)
    with tempfile.TemporaryDirectory(prefix="aiw-watchdog-selftest-") as tmp:
        changed_output = Path(tmp) / "changed.md"
        changed_output.write_text(
            "## Response\n```json\n"
            + json.dumps({"status": "changed", "blocked_reason": ""})
            + "\n```\n",
            encoding="utf-8",
        )
        no_change_output = Path(tmp) / "no-change.md"
        no_change_output.write_text(
            "## Response\n```json\n"
            + json.dumps({"status": "completed-no-change", "blocked_reason": ""})
            + "\n```\n",
            encoding="utf-8",
        )
        parse_error_output = Path(tmp) / "parse-error.md"
        parse_error_output.write_text(
            "## Response\n任务说明里出现 blocked_reason，但没有结果 JSON。\n",
            encoding="utf-8",
        )
        check(watchdog.classify_cron_output(changed_output) == "productive_or_completed", "watchdog misclassified changed response", errors)
        check(watchdog.classify_cron_output(no_change_output) == "completed-no-change", "watchdog misclassified no-change response", errors)
        check(watchdog.classify_cron_output(parse_error_output) == "response-parse-error", "watchdog treated blocked_reason prose as blocked", errors)

    freshness = load_script("aiw-weekly-source-audit.py")
    high = f"Android {17 + 1}"
    high_api = f"API level {37 + 1}"
    high_api_short = f"API {37 + 1}"
    check(list(common.affirmative_higher_android_mentions(f"{high} 不再允许旧接口。")), "higher-version negative predicate was incorrectly filtered", errors)
    check(not list(common.affirmative_higher_android_mentions(f"本文不把 Android 17 结论外推到 {high}。")), "scope exclusion was incorrectly treated as a claim", errors)
    check(not list(common.affirmative_higher_android_mentions(f"正文中的线程模型结论均不外推到 {high} 或更新版本。")), "long scope exclusion was incorrectly treated as a claim", errors)
    check(not list(common.affirmative_higher_android_mentions(f"不把 {high} 以后可能出现的行为写成正文结论。")), "post-version scope exclusion was incorrectly treated as a claim", errors)
    check(not list(common.affirmative_higher_android_mentions(f"无 {high}/{high_api_short}+ 主线结论。")), "zero-claim audit statement was incorrectly treated as a claim", errors)
    check(
        not list(common.affirmative_higher_android_mentions(f"本文未使用 {high}/{high_api_short} 之后的主线实现反推 Android 17 行为。")),
        "explicit non-use of higher-version sources was incorrectly treated as a claim",
        errors,
    )
    check(
        len(list(common.affirmative_higher_android_mentions(f"{high}/{high_api_short} introduces a policy."))) == 1,
        "one source line produced duplicate higher-version findings",
        errors,
    )
    check(list(common.affirmative_higher_android_mentions(f"{high_api} introduces a policy.")), "API level form was not detected", errors)

    fm_fixture = """---
title: test
status: ready-for-review
last_verified: 2026-08-09
sources:
  - type: aosp
    path: frameworks/base/example.java
---
body
"""
    review_context = load_script("aiw-review-finalize-context.py")
    parsed_review_fm, _ = review_context.parse_fm(fm_fixture)
    check(
        isinstance(parsed_review_fm.get("sources"), list) and len(parsed_review_fm["sources"]) == 1,
        "review-finalize context flattened YAML sources",
        errors,
    )
    check(parsed_review_fm.get("last_verified") == "2026-08-09", "review-finalize context leaked YAML date objects", errors)
    body_context = load_script("aiw-body-apply-context.py")
    with tempfile.TemporaryDirectory(prefix="aiw-frontmatter-selftest-") as tmp:
        fm_path = Path(tmp) / "chapter.md"
        fm_path.write_text(fm_fixture, encoding="utf-8")
        parsed_body_fm = body_context.frontmatter(fm_path)
        check(
            isinstance(parsed_body_fm.get("sources"), list) and len(parsed_body_fm["sources"]) == 1,
            "body-apply context flattened YAML sources",
            errors,
        )
        check(parsed_body_fm.get("last_verified") == "2026-08-09", "body-apply context leaked YAML date objects", errors)

    completion = load_script("aiw-run-complete.py")
    try:
        completion.yaml.load("title: one\ntitle: two\n", Loader=completion.StrictSafeLoader)
        errors.append("strict YAML loader accepted a duplicate key")
    except completion.DuplicateKeyError:
        pass
    with tempfile.TemporaryDirectory(prefix="aiw-markdown-selftest-") as tmp:
        escaped = Path(tmp) / "escaped.md"
        escaped.write_text("# Report\\n\\n- one\\n- two\\n", encoding="utf-8")
        normal = Path(tmp) / "normal.md"
        normal.write_text("# Report\n\n- one\n- two\n", encoding="utf-8")
        check(
            completion.verify_external_artifact(str(escaped), "selftest", json_required=False) is not None,
            "escaped-newline Markdown artifact was accepted",
            errors,
        )
        check(
            completion.verify_external_artifact(str(normal), "selftest", json_required=False) is None,
            "valid multiline Markdown artifact was rejected",
            errors,
        )

    original_completion_aiw = completion.AIW
    original_completion_canonical = completion.is_canonical_chapter_path
    try:
        with tempfile.TemporaryDirectory(prefix="aiw-reader-prose-selftest-") as tmp:
            completion.AIW = Path(tmp)
            completion.is_canonical_chapter_path = lambda _: True
            target = completion.AIW / "src/chapter.md"
            target.parent.mkdir(parents=True)
            target.write_text(
                "---\ntitle: test\n---\n\n本次 rework 只采纳一方来源。\n",
                encoding="utf-8",
            )
            check(
                completion.invalid_pipeline_prose(["src/chapter.md"]) is not None,
                "pipeline narration in reader-facing body was accepted",
                errors,
            )
            target.write_text(
                "---\ntitle: test\n---\n\n本章区分平台证据与端到端实测边界。\n",
                encoding="utf-8",
            )
            check(
                completion.invalid_pipeline_prose(["src/chapter.md"]) is None,
                "reader-facing evidence boundary was rejected as pipeline narration",
                errors,
            )
            target.write_text(
                "---\ntitle: test\n---\n\nFrontEnd 处理的是客户端请求怎样变成本轮可消费状态，不是完整的显示流水线。\n",
                encoding="utf-8",
            )
            check(
                completion.invalid_pipeline_prose(["src/chapter.md"]) is None,
                "technical use of 本轮 and 流水线 was rejected as pipeline narration",
                errors,
            )
            target.write_text(
                "---\ntitle: test\n---\n\n补齐源码前，本章保持 `ready-for-review`。\n",
                encoding="utf-8",
            )
            check(
                completion.invalid_pipeline_prose(["src/chapter.md"]) is not None,
                "reader prose exposed an internal metadata state",
                errors,
            )
            target.write_text(
                "---\ntitle: test\nchapter: '1.1'\nstatus: finalized\napplicable_versions: Android 17\n"
                "tags: [test]\nlast_verified: 2026-08-09\nconfidence: high\n"
                "sources:\n  - type: aosp\n    path: frameworks/base/example.java\n---\n\n"
                "> 历史错误提纲不作为技术结论。\n",
                encoding="utf-8",
            )
            check(
                completion.invalid_publication_body(["src/chapter.md"]) is not None,
                "historical wrong-content disclaimer passed the publication gate",
                errors,
            )
            target.write_text(
                "---\ntitle: test\nchapter: '1.1'\nstatus: finalized\napplicable_versions: Android 17\n"
                "tags: [test]\nlast_verified: 2026-08-09\nconfidence: high\n"
                "sources:\n  - type: aosp\n    path: frameworks/base/example.java\n---\n\n"
                "上游源码 TODO 表示实现边界，不能外推为已交付能力。\n",
                encoding="utf-8",
            )
            check(
                completion.invalid_publication_body(["src/chapter.md"]) is None,
                "honest upstream TODO boundary failed the publication gate",
                errors,
            )
            check(
                completion.metadata_schema_error(["src/chapter.md"]) is None,
                "valid strict source schema was rejected",
                errors,
            )
            target.write_text(
                target.read_text(encoding="utf-8").replace(
                    "sources:\n  - type: aosp\n    path: frameworks/base/example.java",
                    "sources:\n  - frameworks/base/example.java",
                ),
                encoding="utf-8",
            )
            check(
                completion.metadata_schema_error(["src/chapter.md"]) is not None,
                "legacy string-only sources passed the strict source schema",
                errors,
            )
    finally:
        completion.AIW = original_completion_aiw
        completion.is_canonical_chapter_path = original_completion_canonical

    quality = load_script("aiw-quality-baseline.py")
    original_quality_aiw = quality.AIW
    try:
        with tempfile.TemporaryDirectory(prefix="aiw-marker-selftest-") as tmp:
            quality.AIW = Path(tmp)
            marker_path = quality.AIW / "chapter.md"
            marker_path.write_text(
                "---\ntitle: marker\nchapter: '1.1'\nstatus: finalized\n---\n\n"
                "上游源码 TODO(dev) 表示此分支尚未实现。\n\n"
                "当前公开证据仍待验证，不能外推为设备保证。\n\n"
                "[待验证] 作者需要补齐这个结论。\n",
                encoding="utf-8",
            )
            marker = quality.parse_chapter(marker_path)
            check(marker["upstream_source_todos"] == 1, "upstream TODO marker classification failed", errors)
            check(marker["declared_evidence_boundaries"] == 1, "evidence-boundary marker classification failed", errors)
            check(marker["editorial_placeholders"] == 1, "editorial placeholder classification failed", errors)
    finally:
        quality.AIW = original_quality_aiw

    original_manifest_dir = common.MANIFEST_DIR
    original_result_dir = common.RESULT_DIR
    original_current_head = common.current_head
    try:
        with tempfile.TemporaryDirectory(prefix="aiw-selftest-") as tmp:
            common.MANIFEST_DIR = Path(tmp) / "manifests"
            common.RESULT_DIR = Path(tmp) / "results"
            common.current_head = lambda: "a" * 40
            manifest = common.create_manifest(
                lane="selftest",
                run_id="selftest-1",
                target_path="src/a.md",
                expected_changed_paths=["src/a.md"],
                target_sha_before="deadbeef",
            )
            check(manifest.get("status") == "leased", "new manifest was not leased", errors)
            check(not common.load_manifests(), "leased manifest leaked into git-sync ready set", errors)
            common.mark_manifest("selftest-1", "agent-completed")
            check(len(common.load_manifests()) == 1, "agent-completed manifest was not loadable", errors)
            common.mark_manifest(
                "selftest-1",
                "needs-human-review",
                result_validation_error="transient conflict",
            )
            common.mark_manifest(
                "selftest-1",
                "agent-completed",
                clear_fields=("result_validation_error",),
            )
            refreshed = json.loads((common.MANIFEST_DIR / "selftest-1.json").read_text(encoding="utf-8"))
            check(
                "result_validation_error" not in refreshed,
                "successful manifest release retained a stale validation error",
                errors,
            )
            try:
                common.create_manifest(
                    lane="selftest",
                    run_id="selftest-2",
                    target_path="src/a.md",
                    expected_changed_paths=["src/a.md"],
                )
                errors.append("duplicate active target lease was accepted")
            except RuntimeError:
                pass
    finally:
        common.MANIFEST_DIR = original_manifest_dir
        common.RESULT_DIR = original_result_dir
        common.current_head = original_current_head

    before = len(list(original_manifest_dir.glob("*.json")))
    for script in [
        "aiw-body-apply-context.py",
        "aiw-review-finalize-context.py",
        "aiw-polish-deep-review-context.py",
        "aiw-polish-rework-context.py",
        "aiw-polish-idle-audit-context.py",
        "aiw-polish-draft-polish-context.py",
        "aiw-chinese-review-context.py",
    ]:
        preview = subprocess.run(
            ["python3", str(SCRIPTS / script), "--dry-run"],
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
        check(preview.returncode == 0, f"{script} dry-run failed: {preview.stderr[-300:]}", errors)
        try:
            preview_json = json.loads(preview.stdout)
        except json.JSONDecodeError:
            preview_json = {}
        if preview_json.get("target"):
            target = preview_json["target"]
            check(
                target.get("sha256_utf8_16") == target.get("sha16")
                and "not a Git blob hash" in str(target.get("hash_contract") or ""),
                f"{script} omitted the unambiguous target content-hash contract",
                errors,
            )
            relative = target.get("relative_path") or target.get("path") or preview_json.get("target_path")
            if relative:
                check(
                    common.is_canonical_chapter_path(str(relative)),
                    f"{script} selected a non-canonical target: {relative}",
                    errors,
                )
    after = len(list(original_manifest_dir.glob("*.json")))
    check(before == after, "one or more pre-run dry-runs created a manifest", errors)

    freshness_paths = [
        common.AIW / "metadata/freshness-cursor.json",
        common.AIW / "metadata/freshness-log.json",
        common.AIW / "metadata/review-findings.json",
        common.AIW / "metadata/queue.json",
    ]
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "<missing>"
    freshness_before = {str(path): digest(path) for path in freshness_paths}
    status_before = subprocess.run(
        ["git", "status", "--porcelain"], cwd=str(common.AIW), text=True, capture_output=True, check=False
    ).stdout
    wrapper = subprocess.run(
        ["python3", str(SCRIPTS / "aiw-weekly-source-audit-freshness-check.py"), "--dry-run", "--scan-limit", "0"],
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    check(wrapper.returncode == 0, f"freshness wrapper dry-run failed: {wrapper.stderr[-300:]}", errors)
    check("scanned=0" in wrapper.stdout, "freshness wrapper dropped --scan-limit", errors)
    freshness_after = {str(path): digest(path) for path in freshness_paths}
    status_after = subprocess.run(
        ["git", "status", "--porcelain"], cwd=str(common.AIW), text=True, capture_output=True, check=False
    ).stdout
    check(freshness_before == freshness_after, "freshness wrapper dry-run mutated repo state files", errors)
    check(status_before == status_after, "freshness wrapper dry-run changed Git status", errors)

    jobs = json.loads(JOBS.read_text(encoding="utf-8")).get("jobs", [])
    by_name = {row.get("name"): row for row in jobs}
    sync = by_name.get("aiw-git-sync", {})
    schedule = sync.get("schedule") or {}
    schedule_expr = schedule.get("expr") if isinstance(schedule, dict) else schedule
    check(schedule_expr == "25,55 7-23 * * *", "mid-hour git-sync schedule missing", errors)
    expected_jobs = {
        "aiw-git-sync-morning-intake": ("55 5,6 * * *", True, "aiw-git-sync.py"),
        "aiw-pipeline-selftest": ("50 6 * * *", True, "aiw-pipeline-selftest.py"),
        "aiw-quality-baseline": ("5 7 * * *", True, "aiw-quality-baseline.py"),
        "aiw-chinese-quality-deepseek": ("0 9,13,17,21 * * *", False, "aiw-chinese-review-context.py"),
    }
    for name, (expr, no_agent, script) in expected_jobs.items():
        job = by_name.get(name, {})
        schedule = job.get("schedule") or {}
        actual_expr = schedule.get("expr") if isinstance(schedule, dict) else schedule
        check(job.get("state") == "scheduled", f"{name} is not scheduled", errors)
        check(actual_expr == expr, f"{name} schedule mismatch", errors)
        check(bool(job.get("no_agent")) == no_agent, f"{name} execution mode mismatch", errors)
        check(job.get("script") == script, f"{name} script mismatch", errors)
    deepseek_job = by_name.get("aiw-chinese-quality-deepseek", {})
    check(deepseek_job.get("model") == "deepseek-v4-pro", "DeepSeek Chinese job model mismatch", errors)
    check(deepseek_job.get("provider") == "deepseek", "DeepSeek Chinese job provider mismatch", errors)
    check("aiw-run-complete.py" in str(deepseek_job.get("prompt") or ""), "DeepSeek Chinese job lacks result release contract", errors)
    for name in [
        "aiw-body-apply",
        "aiw-review-finalize-apply",
        "aiw-polish-deep-review-apply",
        "aiw-polish-rework-apply",
        "aiw-polish-idle-audit-apply",
        "aiw-polish-draft-polish-apply",
    ]:
        prompt = str(by_name.get(name, {}).get("prompt") or "")
        check("aiw-run-complete.py" in prompt and "result_path" in prompt, f"{name} lacks result release contract", errors)
        check(
            "target.hash_contract" in prompt and "git hash-object" in prompt,
            f"{name} lacks the explicit UTF-8 SHA-256 target hash contract",
            errors,
        )
        check(
            prompt.count("发布正文验收优先级：") == 1
            and "事实正确性 > 证据可追溯" in prompt
            and "上游源码中的 TODO" in prompt,
            f"{name} lacks the publication-priority prompt contract",
            errors,
        )
    check(
        "target.hash_contract" in str(deepseek_job.get("prompt") or "")
        and "git hash-object" in str(deepseek_job.get("prompt") or ""),
        "DeepSeek Chinese job lacks the explicit UTF-8 SHA-256 target hash contract",
        errors,
    )
    check(
        "上游源码 TODO、未完成实现" in str(deepseek_job.get("prompt") or "")
        and "只报告 needs-human-review" in str(deepseek_job.get("prompt") or ""),
        "DeepSeek Chinese job lacks technical-boundary escalation rules",
        errors,
    )

    feishu_source = (SCRIPTS / "feishu-daily-sync.py").read_text(encoding="utf-8")
    check('"-e", "OpenClaw定时任务/"' in feishu_source, "Feishu work-copy clean exclusion missing", errors)

    active_manifests = []
    for path in original_manifest_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("status") in {"created", "leased", "agent-completed", "committed-local"}:
            active_manifests.append(f"{data.get('run_id')}:{data.get('status')}")
    check(not active_manifests, "unexpected active manifests: " + ", ".join(active_manifests), errors)

    if errors:
        print("# AIW Pipeline Selftest\n- status: failed\n" + "\n".join(f"- {error}" for error in errors))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
