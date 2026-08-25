#!/usr/bin/env python3
"""生成书项目进度报告（AIW 精修状态机 v2）。"""

import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

CHAPTER_TITLES = {
    "1": "架构基础", "2": "渲染机制", "3": "输入系统", "4": "内存管理",
    "5": "CPU与功耗", "6": "存储系统", "7": "流畅度", "8": "响应速度",
    "9": "ANR", "10": "内存性能", "11": "功耗优化", "12": "APK与网络",
    "13": "渲染管线", "14": "Perfetto", "15": "其他工具", "16": "方法论", "17": "APM生态",
    "18": "AOSP", "19": "OEM", "20": "稳定性治理", "21": "启动优化",
    "22": "渲染实战", "23": "内存实战", "24": "I/O与网络", "25": "功耗与包体积",
    "26": "可观测性",
}

PARTS = {
    "第一部分：基础与机制": ["1", "2", "3", "4", "5", "6"],
    "第二部分：性能专题": ["7", "8", "9", "10", "11", "12", "13"],
    "第三部分：工具与方法论": ["14", "15", "16", "17"],
    "第四部分：系统级优化": ["18", "19"],
    "第五部分：应用层优化": ["20", "21", "22", "23", "24", "25", "26"],
}

CANONICAL_CHAPTER_ROOTS = [
    "part1-fundamentals/ch01-architecture",
    "part1-fundamentals/ch02-rendering",
    "part1-fundamentals/ch03-input",
    "part1-fundamentals/ch04-memory",
    "part1-fundamentals/ch05-cpu-power",
    "part1-fundamentals/ch06-storage",
    "part2-performance/ch07-smoothness",
    "part2-performance/ch08-responsiveness",
    "part2-performance/ch09-anr",
    "part2-performance/ch10-memory-perf",
    "part2-performance/ch11-power",
    "part2-performance/ch12-apk-network",
    "part2-performance/ch13-rendering-pipelines",
    "part3-tools/ch14-perfetto",
    "part3-tools/ch15-other-tools",
    "part3-tools/ch16-methodology",
    "part3-tools/ch17-apm",
    "part4-system/ch18-aosp",
    "part4-system/ch19-oem",
    "part5-app/ch20-stability",
    "part5-app/ch21-startup",
    "part5-app/ch22-rendering-practice",
    "part5-app/ch23-memory-practice",
    "part5-app/ch24-io-network",
    "part5-app/ch25-power-size",
    "part5-app/ch26-observability",
]


def parse_frontmatter(path: Path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    fm = m.group(1)
    out = {"path": str(path)}
    for key in [
        "title", "chapter", "status", "pipeline_stage",
        "task6_state", "task9_state", "task2b_state",
    ]:
        km = re.search(rf"^{re.escape(key)}:\s*(.+)$", fm, re.M)
        if km:
            out[key] = km.group(1).strip().strip("\"'")
    return out


def chapter_num(section_id: str):
    if not section_id:
        return "unknown"
    return section_id.split(".")[0]


def main():
    base_dir = Path(__file__).resolve().parent.parent
    src_dir = base_dir / "src"
    items = []

    for relative_root in CANONICAL_CHAPTER_ROOTS:
        for path in (src_dir / relative_root).rglob("*.md"):
            if path.name == "README.md":
                continue
            meta = parse_frontmatter(path)
            if meta:
                items.append(meta)

    total = len(items)
    status_counter = Counter(v.get("status", "unknown") for v in items)
    pipeline_counter = Counter(v.get("pipeline_stage", "unknown") for v in items)
    task6_counter = Counter(v.get("task6_state", "unknown") for v in items)
    task9_counter = Counter(v.get("task9_state", "unknown") for v in items)
    task2b_counter = Counter(v.get("task2b_state", "unknown") for v in items)

    print("📊 Android-Internal-Wiki 进度报告（v2）")
    print("=" * 56)
    print(f"日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    print(f"总小节: {total}")
    print()

    print("基础状态:")
    for k, v in sorted(status_counter.items()):
        print(f"  {k}: {v}")
    print()

    print("流水线阶段:")
    for k, v in sorted(pipeline_counter.items()):
        print(f"  {k}: {v}")
    print()

    print("Task 状态:")
    print("  task6_state:")
    for k, v in sorted(task6_counter.items()):
        print(f"    {k}: {v}")
    print("  task9_state:")
    for k, v in sorted(task9_counter.items()):
        print(f"    {k}: {v}")
    print("  task2b_state:")
    for k, v in sorted(task2b_counter.items()):
        print(f"    {k}: {v}")
    print()

    chapter_sections = defaultdict(list)
    for meta in items:
        chapter_sections[chapter_num(meta.get("chapter"))].append(meta)

    # Keep the legacy name for compatibility, but count the stage actually used
    # by the repository metadata today.
    ready_to_publish_like = {"ready-to-publish", "publish_ready"}
    for part_name, ch_nums in PARTS.items():
        part_items = []
        for ch in ch_nums:
            part_items.extend(chapter_sections.get(ch, []))
        if not part_items:
            print(f"{part_name}: 无数据")
            print()
            continue
        part_total = len(part_items)
        part_done = sum(
            1 for m in part_items if m.get("pipeline_stage") in ready_to_publish_like
        )
        pct = (part_done / part_total * 100) if part_total else 0
        print(f"{part_name}: {pct:.0f}% ready-to-publish")
        for ch in ch_nums:
            ch_items = chapter_sections.get(ch, [])
            ch_total = len(ch_items)
            if ch_total == 0:
                print(f"  Ch{ch:>2} {CHAPTER_TITLES.get(ch, ''):<20s} [░░░░░░░░░░] 0%")
                continue
            ch_done = sum(
                1 for m in ch_items if m.get("pipeline_stage") in ready_to_publish_like
            )
            ch_pct = ch_done / ch_total * 100
            filled = int(ch_pct / 10)
            bar = "█" * filled + "░" * (10 - filled)
            print(f"  Ch{ch:>2} {CHAPTER_TITLES.get(ch, ''):<20s} [{bar}] {ch_pct:.0f}%")
        print()


if __name__ == "__main__":
    main()
