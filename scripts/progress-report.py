#!/usr/bin/env python3
"""生成书项目进度报告。

适配 progress.json 实际结构：
  - 顶层: metrics (按 status 统计), stats (completed/pending), sections (按章节状态)
  - 章节按 "X.Y" 编号存于 sections
"""

import json
import os
import sys
from datetime import datetime

# 章节 → 所属部分映射
CHAPTER_TITLES = {
    "1": "架构基础", "2": "渲染机制", "3": "输入系统", "4": "内存管理",
    "5": "CPU与功耗", "6": "存储系统", "7": "流畅度", "8": "响应速度",
    "9": "ANR", "10": "内存性能", "11": "功耗优化", "12": "APK与网络",
    "13": "Perfetto", "14": "其他工具", "15": "方法论", "16": "AOSP", "17": "OEM",
}

PARTS = {
    "第一部分：基础与机制": ["1", "2", "3", "4", "5", "6"],
    "第二部分：性能专题": ["7", "8", "9", "10", "11", "12"],
    "第三部分：工具与方法论": ["13", "14", "15"],
    "第四部分：系统级优化": ["16", "17"],
}

STATUS_LABELS = {
    "draft": "草稿", "ready-for-review": "待审", "reviewed": "已审",
    "finalized": "终审", "ready-to-publish": "待发", "published": "已发",
}

# 按完成度排序（低→高）
STATUS_ORDER = ["draft", "ready-for-review", "reviewed", "finalized", "ready-to-publish", "published"]


def get_chapter_num(section_id):
    """从 'X.Y' 提取章号 X。"""
    return section_id.split(".")[0]


def main():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    progress_path = os.path.join(base_dir, "metadata", "progress.json")

    with open(progress_path, 'r', encoding='utf-8') as f:
        progress = json.load(f)

    # 从 metrics 获取状态分布
    metrics = progress.get("metrics", {})
    total = metrics.get("total", progress.get("stats", {}).get("total", 0))

    print(f"📊 Android Internals & Performance 进度报告")
    print(f"{'=' * 50}")
    print(f"日期: {datetime.now().strftime('%Y-%m-%d')}")
    print()

    # 状态分布
    print("状态分布:")
    for status in STATUS_ORDER:
        count = metrics.get(status, 0)
        if count > 0:
            label = STATUS_LABELS.get(status, status)
            print(f"  {label}: {count}")
    print()

    # 从 sections 聚合章级进度
    sections = progress.get("sections", {})
    # 顶层还有部分 section 用数字 key 存的（如 "5.1", "2.6"）
    # 合并所有 section 数据
    all_sections = {}
    for key, val in sections.items():
        if isinstance(val, dict) and "status" in val:
            all_sections[key] = val

    # 也从顶层数字 key 收集
    for key, val in progress.items():
        if isinstance(key, str) and "." in key and isinstance(val, dict) and "status" in val:
            if key not in all_sections:
                all_sections[key] = val

    # 按章节聚合
    chapter_sections = {}  # ch_num -> list of section dicts
    for sec_id, sec_data in all_sections.items():
        ch_num = get_chapter_num(sec_id)
        chapter_sections.setdefault(ch_num, []).append((sec_id, sec_data))

    # 整体完成率（非 draft 即视为有进展）
    draft_count = metrics.get("draft", 0)
    active_count = total - draft_count
    active_pct = active_count / total * 100 if total > 0 else 0
    print(f"整体进度: {active_count}/{total} 已启动 ({active_pct:.0f}%)")
    print()

    # 按部分输出
    for part_name, ch_nums in PARTS.items():
        part_sections = []
        for ch in ch_nums:
            part_sections.extend(chapter_sections.get(ch, []))

        if not part_sections:
            print(f"{part_name}: 无数据")
            print()
            continue

        part_total = len(part_sections)
        part_active = sum(1 for _, s in part_sections if s.get("status") != "draft")
        pct = part_active / part_total * 100 if part_total > 0 else 0
        print(f"{part_name}: {pct:.0f}%")

        for ch in ch_nums:
            ch_secs = chapter_sections.get(ch, [])
            if not ch_secs:
                ch_title = CHAPTER_TITLES.get(ch, "")
                print(f"  Ch{ch:>2} {ch_title:<20s} [░░░░░░░░░░] 0%")
                continue

            ch_total = len(ch_secs)
            ch_active = sum(1 for _, s in ch_secs if s.get("status") != "draft")
            ch_pct = ch_active / ch_total * 100 if ch_total > 0 else 0
            ch_title = CHAPTER_TITLES.get(ch, ch_secs[0][1].get("title", "")[:20])
            filled = int(ch_pct / 10)
            status_bar = "█" * filled + "░" * (10 - filled)
            print(f"  Ch{ch:>2} {ch_title:<20s} [{status_bar}] {ch_pct:.0f}%")
        print()


if __name__ == "__main__":
    main()
