#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate one AIW agent result and release its manifest to git-sync.

The LLM writes a machine-readable result and evidence first. This helper derives
the real dirty paths from Git, runs local gates, and only then changes a leased
manifest to agent-completed. Chat output alone can never authorize a commit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

from aiw_pipeline_common import (
    AIW,
    MANIFEST_DIR,
    RESULT_DIR,
    atomic_write_json,
    current_head,
    is_canonical_chapter_path,
    mark_manifest,
    matching_findings,
    porcelain_paths,
    rel_to_aiw,
    split_frontmatter_body,
)

CHANGE_STATUSES = {"changed", "metadata-only"}
NO_CHANGE_STATUSES = {"completed-no-change", "no-change"}
STOP_STATUSES = {"blocked", "needs-human-review"}
ALLOWED_RESULT_STATUSES = CHANGE_STATUSES | NO_CHANGE_STATUSES | STOP_STATUSES
SOURCE_GATED_STATUSES = {"ready-for-review", "finalized", "verified"}
PUBLICATION_STATUSES = {"finalized", "verified"}


class DuplicateKeyError(yaml.YAMLError):
    """Raised when frontmatter repeats a mapping key at any nesting level."""


class StrictSafeLoader(yaml.SafeLoader):
    pass


def construct_unique_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise DuplicateKeyError(
                f"duplicate YAML key {key!r} at line {key_node.start_mark.line + 1}"
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_unique_mapping,
)


def fail(manifest: dict, reason: str, *, result: dict | None = None) -> int:
    run_id = str(manifest.get("run_id") or "")
    if run_id:
        mark_manifest(run_id, "needs-human-review", result_validation_error=reason)
    print(json.dumps({
        "status": "needs-human-review",
        "run_id": run_id,
        "reason": reason,
        "result_status": (result or {}).get("status"),
    }, ensure_ascii=False))
    return 2


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON object required: {path}")
    return data


def normalize_result_paths(paths: list) -> list[str]:
    out: list[str] = []
    for raw in paths:
        if not raw:
            continue
        try:
            out.append(rel_to_aiw(str(raw)))
        except Exception:
            # Formal reports and private evidence live outside the Git repo.
            continue
    return sorted(set(out))


def run(cmd: list[str], timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(AIW), text=True, capture_output=True, timeout=timeout, check=False)


def sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def file_sha256(path: Path) -> str:
    if not path.exists():
        return "<deleted>"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def target_at_base(manifest: dict) -> str:
    target = str(manifest.get("target_path") or "")
    base = str(manifest.get("base_sha") or "")
    if not target or not base:
        return ""
    r = run(["git", "show", f"{base}:{target}"], timeout=60)
    return r.stdout if r.returncode == 0 else ""


def parse_target_frontmatter(target: str) -> dict:
    path = AIW / target
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8", errors="ignore")
    fm_text, _ = split_frontmatter_body(text)
    if not fm_text:
        return {}
    try:
        data = yaml.load(fm_text, Loader=StrictSafeLoader) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def open_blocking_findings(target: str, fm: dict) -> list[str]:
    path = AIW / "metadata/review-findings.json"
    try:
        rows = load_json(path).get("findings", [])
    except Exception:
        return []
    matched = matching_findings(
        rows if isinstance(rows, list) else [],
        target,
        fm,
        severities={"P0", "P1"},
    )
    return [str(row.get("id") or "unknown-finding") for row in matched]


def strict_frontmatter(relative: str) -> tuple[dict, str]:
    path = AIW / relative
    text = path.read_text(encoding="utf-8", errors="ignore")
    fm_text, body = split_frontmatter_body(text)
    if not fm_text:
        raise ValueError("missing YAML frontmatter")
    meta = yaml.load(fm_text, Loader=StrictSafeLoader)
    if not isinstance(meta, dict):
        raise ValueError("frontmatter must be a mapping")
    return meta, body


def metadata_schema_error(paths: list[str]) -> str | None:
    """Apply the publication schema before an agent result can be accepted."""
    for relative in paths:
        if not is_canonical_chapter_path(relative):
            continue
        try:
            meta, _ = strict_frontmatter(relative)
        except Exception as exc:
            return f"strict YAML validation failed: {relative}: {exc}"
        status = str(meta.get("status") or "")
        sources = meta.get("sources")
        if sources is not None:
            if not isinstance(sources, list):
                return f"sources must be a list: {relative}"
            for index, source in enumerate(sources):
                if not isinstance(source, dict):
                    return f"sources[{index}] must be a mapping: {relative}"
                if not str(source.get("type") or "").strip() or not str(source.get("path") or "").strip():
                    return f"sources[{index}] requires non-empty type/path: {relative}"
        if status in SOURCE_GATED_STATUSES and not sources:
            return f"status={status} requires a non-empty sources list: {relative}"
        if status in PUBLICATION_STATUSES:
            for key in ("pipeline_stage", "task6_state", "task9_state", "task2b_state"):
                value = str(meta.get(key) or "").lower()
                if re.search(r"(?:pending|needs[-_ ]?rework|revisiting)", value):
                    return f"status={status} conflicts with {key}={meta.get(key)!r}: {relative}"
    return None


def verify_external_artifact(path_value: str, run_id: str, *, json_required: bool) -> str | None:
    if not path_value:
        return "required artifact path missing from manifest"
    path = Path(path_value)
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return f"required artifact missing or empty: {path}"
    if json_required:
        try:
            data = load_json(path)
        except Exception as exc:
            return f"invalid evidence JSON {path}: {exc}"
        if str(data.get("run_id") or "") != run_id:
            return f"evidence run_id mismatch: {path}"
    elif path.suffix.lower() == ".md":
        text = path.read_text(encoding="utf-8", errors="ignore")
        if text.count("\n") < 3 and text.count("\\n") >= 3:
            return f"markdown artifact contains escaped newlines instead of real lines: {path}"
    return None


def invalid_repo_markdown(paths: list[str]) -> str | None:
    for relative in paths:
        if not relative.endswith(".md"):
            continue
        path = AIW / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if text.count("\n") < 3 and text.count("\\n") >= 3:
            return f"repo markdown contains escaped newlines instead of real lines: {relative}"
    return None


def invalid_pipeline_prose(paths: list[str]) -> str | None:
    """Keep internal workflow narration out of reader-facing chapter bodies."""
    patterns = [
        re.compile(
            r"(?:本次|本轮)\s*(?:的|AIW\s*)?(?:rework|deep[- ]?review|review lane|lane|prompt|pipeline|agent|流水线|定时任务|任务产物)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:由|交给).{0,24}(?:lane|agent|流水线|定时任务).{0,24}(?:处理|修改|审查|生成)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:ready-for-review|needs-rework|pipeline_stage|last_review_finalize)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:Review[- ]?finalize|Draft[- ]?polish|deep[- ]?review).{0,40}(?:本轮|任务|lane|阶段|复核|处理|修改|产物)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:OpenClaw\s*加工指引|流水线加工要求|加工说明|为了兼容\s*(?:Hermes|OpenClaw|流水线))",
            re.IGNORECASE,
        ),
    ]
    for relative in paths:
        if not relative.startswith("src/") or not relative.endswith(".md"):
            continue
        path = AIW / relative
        if not path.exists():
            continue
        _, body = split_frontmatter_body(path.read_text(encoding="utf-8", errors="ignore"))
        body = re.sub(r"```.*?```", "", body, flags=re.S)
        body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
        for pattern in patterns:
            match = pattern.search(body)
            if match:
                excerpt = " ".join(match.group(0).split())[:160]
                return f"reader-facing chapter contains pipeline narration: {relative}: {excerpt}"
    return None


def invalid_publication_body(paths: list[str]) -> str | None:
    """Reject known historical-outline/process disclaimers in published chapters."""
    patterns = [
        re.compile(r"受保护大纲|历史(?:错误|原文|遗留)(?:提纲|大纲|标记)"),
        re.compile(r"不作为(?:当前|本文)?技术结论|可引用正文从"),
        re.compile(r"为了兼容\s*(?:Hermes|OpenClaw|流水线)", re.I),
        re.compile(r"^#{2,4}\s*(?:OpenClaw\s*加工指引|流水线加工要求|加工说明)\s*$", re.I | re.M),
    ]
    for relative in paths:
        if not is_canonical_chapter_path(relative):
            continue
        try:
            meta, body = strict_frontmatter(relative)
        except Exception:
            continue
        if str(meta.get("status") or "") not in PUBLICATION_STATUSES:
            continue
        body = re.sub(r"```.*?```", "", body, flags=re.S)
        body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
        for pattern in patterns:
            match = pattern.search(body)
            if match:
                excerpt = " ".join(match.group(0).split())[:160]
                return f"published chapter contains historical/process prose: {relative}: {excerpt}"
    return None


def run_local_gates(src_paths: list[str]) -> tuple[bool, list[dict]]:
    checks: list[tuple[str, list[str]]] = [
        ("diff-check", ["git", "diff", "--check"]),
        ("summary-links", [sys.executable, "scripts/check-summary-links.py"]),
    ]
    if src_paths:
        checks.append(("metadata", [sys.executable, "scripts/check-metadata.py", "--files", *src_paths]))
    results = []
    ok = True
    for name, cmd in checks:
        r = run(cmd)
        results.append({"name": name, "returncode": r.returncode, "tail": (r.stdout + r.stderr)[-1200:]})
        ok = ok and r.returncode == 0
    return ok, results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--result", required=True)
    args = ap.parse_args()

    manifest_path = Path(args.manifest).resolve()
    result_path = Path(args.result).resolve()
    try:
        manifest_path.relative_to(MANIFEST_DIR.resolve())
        result_path.relative_to(RESULT_DIR.resolve())
    except ValueError:
        print(json.dumps({"status": "rejected", "reason": "manifest/result path outside AIW state roots"}, ensure_ascii=False))
        return 2

    try:
        manifest = load_json(manifest_path)
        result = load_json(result_path)
    except Exception as exc:
        print(json.dumps({"status": "rejected", "reason": f"invalid manifest/result JSON: {exc}"}, ensure_ascii=False))
        return 2

    run_id = str(manifest.get("run_id") or "")
    if str(result.get("run_id") or "") != run_id:
        return fail(manifest, "result run_id does not match manifest", result=result)
    if str(result_path) != str(Path(manifest.get("result_path") or "").resolve()):
        return fail(manifest, "result path does not match manifest", result=result)
    if manifest.get("status") not in {"leased", "created", "needs-human-review", "agent-completed"}:
        return fail(manifest, f"manifest status cannot be completed: {manifest.get('status')}", result=result)
    status = str(result.get("status") or "")
    if status not in ALLOWED_RESULT_STATUSES:
        return fail(manifest, f"unsupported result status: {status}", result=result)
    if current_head() != manifest.get("base_sha"):
        return fail(manifest, "HEAD no longer matches manifest base_sha", result=result)

    target = str(manifest.get("target_path") or "")
    before_sha = str(manifest.get("target_sha_before") or "")
    if before_sha and sha16(target_at_base(manifest)) != before_sha:
        return fail(manifest, "target_sha_before does not match base commit", result=result)

    actual = porcelain_paths()
    expected_repo = sorted({p for p in manifest.get("expected_changed_paths", []) if p and not str(p).startswith("/")})
    unexpected = sorted(set(actual) - set(expected_repo))
    if unexpected:
        return fail(manifest, "dirty paths outside manifest: " + ", ".join(unexpected[:20]), result=result)
    reported = normalize_result_paths(result.get("changed_paths") or [])
    if reported != sorted(actual):
        return fail(manifest, f"reported changed_paths differ from Git: reported={reported}, actual={sorted(actual)}", result=result)

    if status in CHANGE_STATUSES and not actual:
        return fail(manifest, "changed result has no Git changes", result=result)
    if status in NO_CHANGE_STATUSES | STOP_STATUSES and actual:
        return fail(manifest, f"{status} result must not leave Git changes", result=result)

    if status in CHANGE_STATUSES | NO_CHANGE_STATUSES:
        for value, json_required in [
            (str(manifest.get("formal_report_path") or ""), False),
            (str(manifest.get("evidence_path") or ""), True),
        ]:
            error = verify_external_artifact(value, run_id, json_required=json_required)
            if error:
                return fail(manifest, error, result=result)

    src_paths = [p for p in actual if p.startswith("src/") and p.endswith(".md")]
    markdown_error = invalid_repo_markdown(actual)
    if markdown_error:
        return fail(manifest, markdown_error, result=result)
    schema_error = metadata_schema_error(actual)
    if schema_error:
        return fail(manifest, schema_error, result=result)
    pipeline_prose_error = invalid_pipeline_prose(actual)
    if pipeline_prose_error:
        return fail(manifest, pipeline_prose_error, result=result)
    publication_body_error = invalid_publication_body(actual)
    if publication_body_error:
        return fail(manifest, publication_body_error, result=result)
    gate_ok, gates = run_local_gates(src_paths) if actual else (True, [])
    if not gate_ok:
        return fail(manifest, "one or more local gates failed", result={**result, "local_gates": gates})

    fm = parse_target_frontmatter(target) if target else {}
    if fm.get("status") in {"finalized", "verified"} and target in actual:
        if not result.get("source_evidence"):
            return fail(manifest, "finalized/verified target requires non-empty source_evidence", result=result)
        if not (fm.get("last_source_verified_at") or fm.get("last_verified")):
            return fail(manifest, "finalized/verified target lacks source verification date", result=result)
        if not fm.get("sources"):
            return fail(manifest, "finalized/verified target lacks sources frontmatter", result=result)
        blocking = open_blocking_findings(target, fm)
        if blocking:
            return fail(manifest, "open P0/P1 findings block finalized: " + ", ".join(blocking), result=result)

    normalized = dict(result)
    repo_hashes = {path: file_sha256(AIW / path) for path in sorted(actual)}
    artifact_hashes = {
        "formal_report": file_sha256(Path(str(manifest.get("formal_report_path")))),
        "evidence": file_sha256(Path(str(manifest.get("evidence_path")))),
    }
    normalized.update({
        "schema_version": 1,
        "run_id": run_id,
        "lane": manifest.get("lane"),
        "target_path": target,
        "actual_changed_paths": sorted(actual),
        "actual_path_sha256": repo_hashes,
        "artifact_sha256": artifact_hashes,
        "local_gates": gates,
        "validated": True,
    })
    atomic_write_json(result_path, normalized)

    manifest_status = "agent-completed" if status in CHANGE_STATUSES else status
    mark_manifest(
        run_id,
        manifest_status,
        clear_fields=("result_validation_error",),
        result_path=str(result_path),
        actual_changed_paths=sorted(actual),
        actual_path_sha256=repo_hashes,
        artifact_sha256=artifact_hashes,
        result_status=status,
        local_gates=gates,
    )
    print(json.dumps({
        "status": manifest_status,
        "run_id": run_id,
        "target_path": target,
        "actual_changed_paths": sorted(actual),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
