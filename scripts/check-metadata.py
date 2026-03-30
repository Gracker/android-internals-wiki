#!/usr/bin/env python3
"""检查所有章节文件是否包含完整的 YAML 元数据头。"""

import os
import sys
import yaml
import glob

REQUIRED_FIELDS = [
    "title", "chapter", "status", "applicable_versions",
    "last_verified", "confidence", "sources", "tags"
]

VALID_STATUS = ["verified", "draft", "needs-review", "outdated"]
VALID_CONFIDENCE = ["high", "medium", "low"]

def check_file(filepath):
    issues = []
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if not content.startswith('---'):
        return [f"缺少 YAML frontmatter"]

    parts = content.split('---', 2)
    if len(parts) < 3:
        return [f"YAML frontmatter 格式错误"]

    try:
        meta = yaml.safe_load(parts[1])
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

    return issues


def main():
    src_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")

    # 只检查非 README 的章节文件
    all_files = []
    for root, dirs, files in os.walk(src_dir):
        for f in files:
            if f.endswith('.md') and f != 'README.md' and f != 'SUMMARY.md':
                filepath = os.path.join(root, f)
                # 跳过 preface 和 appendix
                rel = os.path.relpath(filepath, src_dir)
                if rel.startswith('preface/') or rel.startswith('appendix/'):
                    continue
                all_files.append(filepath)

    total = len(all_files)
    issues_count = 0

    print(f"检查 {total} 个章节文件的元数据...\n")

    for filepath in sorted(all_files):
        rel = os.path.relpath(filepath, src_dir)
        issues = check_file(filepath)
        if issues:
            issues_count += 1
            print(f"❌ {rel}")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print(f"✅ {rel}")

    print(f"\n总计: {total} 个文件, {total - issues_count} 个通过, {issues_count} 个有问题")
    return 1 if issues_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
