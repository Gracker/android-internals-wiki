#!/usr/bin/env python3
"""检查所有章节文件是否包含完整的 YAML 元数据头。"""

import argparse
import os
import re
import sys
import yaml

REQUIRED_FIELDS = [
    "title", "chapter", "status", "applicable_versions", "tags"
]

OPTIONAL_FIELDS = ["last_verified", "confidence", "sources"]

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
AUXILIARY_SRC_DIRS = {"preface", "appendix"}


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
        meta = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        return [f"YAML 解析错误: {e}"]

    if meta is None:
        return [f"YAML frontmatter 为空"]

    for field in REQUIRED_FIELDS:
        if field not in meta:
            issues.append(f"缺少字段: {field}")

    if meta.get("status") and meta["status"] not in VALID_STATUS:
        issues.append(f"status 值无效: {meta['status']}")

    if meta.get("confidence") and meta["confidence"] not in VALID_CONFIDENCE:
        issues.append(f"confidence 值无效: {meta['confidence']}")

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
