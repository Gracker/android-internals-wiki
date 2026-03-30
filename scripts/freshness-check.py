#!/usr/bin/env python3
"""时效性检查辅助脚本：扫描所有章节文件，找出可能过时的内容。"""

import os
import sys
import yaml
from datetime import datetime, timedelta

STALE_DAYS = 90  # 超过 90 天未验证视为需要检查

def parse_frontmatter(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if not content.startswith('---'):
        return None

    parts = content.split('---', 2)
    if len(parts) < 3:
        return None

    try:
        return yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None


def main():
    src_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
    staging_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "staging", "drafts")

    now = datetime.now()
    stale_threshold = now - timedelta(days=STALE_DAYS)

    stale_items = []
    outdated_items = []
    never_verified = []

    for search_dir in [src_dir, staging_dir]:
        if not os.path.exists(search_dir):
            continue
        for root, dirs, files in os.walk(search_dir):
            for f in files:
                if not f.endswith('.md') or f in ('README.md', 'SUMMARY.md'):
                    continue
                filepath = os.path.join(root, f)
                rel = os.path.relpath(filepath, os.path.dirname(os.path.dirname(__file__)))

                meta = parse_frontmatter(filepath)
                if meta is None:
                    continue

                status = meta.get("status", "")
                last_verified = meta.get("last_verified", "")

                if status == "outdated":
                    outdated_items.append((rel, meta.get("title", ""), meta.get("chapter", "")))
                elif not last_verified:
                    never_verified.append((rel, meta.get("title", ""), meta.get("chapter", "")))
                else:
                    try:
                        verified_date = datetime.strptime(last_verified, "%Y-%m-%d")
                        if verified_date < stale_threshold:
                            days_ago = (now - verified_date).days
                            stale_items.append((rel, meta.get("title", ""), meta.get("chapter", ""), days_ago))
                    except ValueError:
                        pass

    print(f"🔍 时效性检查报告 | {now.strftime('%Y-%m-%d')}")
    print(f"{'=' * 50}")

    if outdated_items:
        print(f"\n🔴 已标记为过时 ({len(outdated_items)} 项):")
        for path, title, ch in outdated_items:
            print(f"  - [{ch}] {title} — {path}")

    if stale_items:
        print(f"\n🟡 超过 {STALE_DAYS} 天未验证 ({len(stale_items)} 项):")
        for path, title, ch, days in sorted(stale_items, key=lambda x: -x[3]):
            print(f"  - [{ch}] {title} — {days} 天前验证 — {path}")

    if never_verified:
        print(f"\n⚪ 从未验证 ({len(never_verified)} 项):")
        for path, title, ch in never_verified:
            print(f"  - [{ch}] {title} — {path}")

    total_issues = len(outdated_items) + len(stale_items) + len(never_verified)
    print(f"\n总计: {total_issues} 项需要关注")


if __name__ == "__main__":
    main()
