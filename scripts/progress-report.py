#!/usr/bin/env python3
"""生成书项目进度报告。"""

import json
import os
import sys
from datetime import datetime

def main():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    progress_path = os.path.join(base_dir, "metadata", "progress.json")

    with open(progress_path, 'r', encoding='utf-8') as f:
        progress = json.load(f)

    total = progress["total_sections"]
    drafted = progress["total_drafted"]
    reviewed = progress["total_reviewed"]
    published = progress["total_published"]

    print(f"📊 Android Internals & Performance 进度报告")
    print(f"{'=' * 50}")
    print(f"日期: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"")
    print(f"整体进度: {published}/{total} 已发布 ({published/total*100:.1f}%)")
    print(f"  - 已起草: {drafted}")
    print(f"  - 已审核: {reviewed}")
    print(f"  - 已发布: {published}")
    print(f"  - 待开始: {total - drafted - reviewed - published}")
    print()

    parts = {
        "第一部分：基础与机制": ["1","2","3","4","5","6"],
        "第二部分：性能专题": ["7","8","9","10","11","12"],
        "第三部分：工具与方法论": ["13","14","15"],
        "第四部分：系统级优化": ["16","17"],
    }

    for part_name, ch_nums in parts.items():
        part_total = sum(progress["chapters"][c]["total_sections"] for c in ch_nums)
        part_drafted = sum(progress["chapters"][c]["drafted"] for c in ch_nums)
        part_reviewed = sum(progress["chapters"][c]["reviewed"] for c in ch_nums)
        part_published = sum(progress["chapters"][c]["published"] for c in ch_nums)
        pct = (part_drafted + part_reviewed + part_published) / part_total * 100 if part_total > 0 else 0
        print(f"{part_name}: {pct:.0f}%")
        for c in ch_nums:
            ch = progress["chapters"][c]
            ch_pct = (ch["drafted"] + ch["reviewed"] + ch["published"]) / ch["total_sections"] * 100 if ch["total_sections"] > 0 else 0
            status_bar = "█" * int(ch_pct / 10) + "░" * (10 - int(ch_pct / 10))
            print(f"  Ch{c:>2} {ch['title']:<20s} [{status_bar}] {ch_pct:.0f}%")
        print()


if __name__ == "__main__":
    main()
