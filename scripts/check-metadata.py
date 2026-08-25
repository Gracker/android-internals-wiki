#!/usr/bin/env python3
"""检查所有章节文件是否包含完整的 YAML 元数据头。"""

import argparse
import os
import re
import sys
import yaml

from frontmatter_schema import ALLOWED_FIELDS, REQUIRED_FIELDS

OPTIONAL_FIELDS = ["confidence", "sources"]
SOURCE_GATED_STATUS = {"ready-for-review", "finalized", "verified"}
PUBLICATION_STATUS = {"finalized", "verified"}

VALID_STATUS = [
    "verified", "draft", "needs-review", "outdated",
    "reviewed", "ready-to-publish", "ready-for-review", "finalized",
]
VALID_CONFIDENCE = ["high", "medium", "low", "medium-high", "medium-low"]

CANONICAL_PARTS = {
    "part1-fundamentals": {
        "ch01-architecture", "ch02-rendering", "ch03-input",
        "ch04-memory", "ch05-cpu-power", "ch06-storage",
    },
    "part2-performance": {
        "ch07-smoothness", "ch08-responsiveness", "ch09-anr",
        "ch10-memory-perf", "ch11-power", "ch12-apk-network",
        "ch13-rendering-pipelines",
    },
    "part3-tools": {
        "ch14-perfetto", "ch15-other-tools", "ch16-methodology", "ch17-apm",
    },
    "part4-system": {"ch18-aosp", "ch19-oem"},
    "part5-app": {
        "ch20-stability", "ch21-startup", "ch22-rendering-practice",
        "ch23-memory-practice", "ch24-io-network", "ch25-power-size",
        "ch26-observability",
    },
}
AUXILIARY_SRC_DIRS = {"preface", "appendix"}


class DuplicateKeyError(yaml.YAMLError):
    """Raised for duplicate mapping keys, including keys in nested mappings."""


class StrictSafeLoader(yaml.SafeLoader):
    pass


def construct_unique_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise DuplicateKeyError(
                f"重复 YAML key {key!r}（frontmatter 第 {key_node.start_mark.line + 1} 行）"
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_unique_mapping,
)


def canonical_chapter_roots(src_dir):
    for part, chapters in CANONICAL_PARTS.items():
        for chapter in sorted(chapters):
            yield os.path.join(src_dir, part, chapter)


def is_canonical_chapter_file(filepath, src_dir):
    rel = os.path.relpath(filepath, src_dir)
    parts = rel.split(os.sep)
    return (
        len(parts) >= 3
        and parts[0] in CANONICAL_PARTS
        and parts[1] in CANONICAL_PARTS[parts[0]]
    )


def check_layout(src_dir):
    """Reject obsolete/duplicate top-level and chapter directories."""
    issues = []
    allowed_top = set(CANONICAL_PARTS) | AUXILIARY_SRC_DIRS
    for name in sorted(os.listdir(src_dir)):
        path = os.path.join(src_dir, name)
        if os.path.isdir(path) and name not in allowed_top:
            issues.append(f"异常 src 顶层目录: {name}")

    for part, expected_chapters in CANONICAL_PARTS.items():
        part_dir = os.path.join(src_dir, part)
        if not os.path.isdir(part_dir):
            issues.append(f"缺少规范 Part 目录: {part}")
            continue
        actual_chapters = {
            name for name in os.listdir(part_dir)
            if os.path.isdir(os.path.join(part_dir, name))
        }
        for name in sorted(actual_chapters - expected_chapters):
            issues.append(f"异常章节目录: {part}/{name}")
        for name in sorted(expected_chapters - actual_chapters):
            issues.append(f"缺少规范章节目录: {part}/{name}")
        for name in sorted(os.listdir(part_dir)):
            if os.path.isfile(os.path.join(part_dir, name)):
                issues.append(f"Part 根目录存在异常文件: {part}/{name}")
    return issues

def check_file(filepath):
    issues = []
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if not content.startswith('---'):
        return ["缺少 YAML frontmatter"]

    # 按行首的 --- 分割，避免误匹配内容中的 ---
    m = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if not m:
        return ["YAML frontmatter 格式错误"]

    try:
        meta = yaml.load(m.group(1), Loader=StrictSafeLoader)
    except yaml.YAMLError as e:
        return [f"YAML 解析错误: {e}"]

    if meta is None:
        return [f"YAML frontmatter 为空"]
    if not isinstance(meta, dict):
        return ["YAML frontmatter 必须是 mapping"]

    for field in REQUIRED_FIELDS:
        if field not in meta:
            issues.append(f"缺少字段: {field}")

    obsolete_fields = sorted(
        str(field) for field in meta if str(field) not in ALLOWED_FIELDS
    )
    if obsolete_fields:
        issues.append(
            "包含过时或未登记的 frontmatter 字段: " + ", ".join(obsolete_fields)
        )

    if meta.get("status") and meta["status"] not in VALID_STATUS:
        issues.append(f"status 值无效: {meta['status']}")

    if meta.get("confidence") and meta["confidence"] not in VALID_CONFIDENCE:
        issues.append(f"confidence 值无效: {meta['confidence']}")

    status = meta.get("status")
    sources = meta.get("sources")
    if sources is not None:
        if not isinstance(sources, list):
            issues.append("sources 必须是 list")
        else:
            for index, source in enumerate(sources):
                if not isinstance(source, dict):
                    issues.append(f"sources[{index}] 必须是 mapping")
                    continue
                if not str(source.get("type") or "").strip():
                    issues.append(f"sources[{index}] 缺少非空 type")
                if not str(source.get("path") or "").strip():
                    issues.append(f"sources[{index}] 缺少非空 path")
    if status in SOURCE_GATED_STATUS:
        if not (meta.get("last_source_verified_at") or meta.get("last_verified")):
            issues.append(f"status={status} 需要 last_source_verified_at 或兼容字段 last_verified")
        if not meta.get("confidence"):
            issues.append(f"status={status} 需要 confidence")
        if not meta.get("sources"):
            issues.append(f"status={status} 需要非空 sources")

    if status in PUBLICATION_STATUS:
        for field in ("pipeline_stage", "task6_state", "task9_state", "task2b_state"):
            value = str(meta.get(field) or "").lower()
            if re.search(r"(?:pending|needs[-_ ]?rework|revisiting)", value):
                issues.append(f"status={status} 与 {field}={meta.get(field)!r} 冲突")

    if "last_source_verified_at" not in meta and "last_verified" not in meta:
        issues.append("[warn] 缺少来源核验时间: last_source_verified_at / last_verified")

    for field in OPTIONAL_FIELDS:
        if field not in meta:
            issues.append(f"[warn] 缺少可选字段: {field} (建议补充)")

    return issues


def iter_files(src_dir, explicit_files=None):
    if explicit_files:
        repo_root = os.path.dirname(os.path.dirname(__file__))
        for item in explicit_files:
            filepath = item if os.path.isabs(item) else os.path.join(repo_root, item)
            if not filepath.endswith('.md') or not os.path.exists(filepath):
                continue
            if os.path.basename(filepath) in ('README.md', 'SUMMARY.md'):
                continue
            if filepath.startswith(src_dir + os.sep) and is_canonical_chapter_file(filepath, src_dir):
                yield filepath
        return

    # Full scan mode is deliberately restricted to the canonical 26 chapter roots.
    for chapter_root in canonical_chapter_roots(src_dir):
        for root, dirs, files in os.walk(chapter_root):
            for f in files:
                if f.endswith('.md') and f != 'README.md' and f != 'SUMMARY.md':
                    yield os.path.join(root, f)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Check chapter YAML metadata.')
    ap.add_argument('--files', nargs='*', help='Only check these repo-relative files. Default: full src scan.')
    args = ap.parse_args(argv)
    src_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")

    layout_issues = check_layout(src_dir)
    all_files = list(iter_files(src_dir, args.files))

    total = len(all_files)
    issues_count = len(layout_issues)
    warn_count = 0

    scope = '指定变更文件' if args.files else '全量 canonical 章节'
    print(f"检查 {total} 个章节文件的元数据（scope={scope}）...\n")

    for issue in layout_issues:
        print(f"❌ {issue}")
    if layout_issues:
        print()

    for filepath in sorted(all_files):
        rel = os.path.relpath(filepath, src_dir)
        issues = check_file(filepath)
        if issues and not all(i.startswith('[warn]') for i in issues):
            issues_count += 1
            print(f"❌ {rel}")
            for issue in issues:
                print(f"   - {issue}")
        elif any(i.startswith('[warn]') for i in issues):
            warn_count += 1
            print(f"⚠️  {rel}")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print(f"✅ {rel}")

    passed = total - (issues_count - len(layout_issues))
    print(f"\n总计: {total} 个文件, {passed} 个通过, {issues_count} 个失败（含 {len(layout_issues)} 个目录结构问题）, {warn_count} 个警告")
    return 1 if issues_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
