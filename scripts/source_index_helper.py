#!/usr/bin/env python3
"""
source-index.json 操作助手

提供对 source-index.json 和 skipped-files.json 的安全读写操作，
避免 LLM 直接加载全量文件导致上下文爆炸。

用法：
  python3 source_index_helper.py <command> [args...]

Commands:
  stats                          打印当前索引统计
  append --entries <json>        追加索引条目（JSON 数组，自动去重）
  append-skipped --entries <json> 追加跳过记录
  search --query <text>          按关键词搜索已有索引
  get-progress                   获取扫描进度
  update-progress --json <json>  更新扫描进度（完整替换）
  get-recent --limit N           获取最近 N 条索引记录
"""

import json
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parents[1]
METADATA_DIR = Path(os.environ.get(
    "AIW_METADATA_DIR",
    REPO_ROOT / "metadata",
))

SOURCE_INDEX = METADATA_DIR / "source-index.json"
SKIPPED_FILES = METADATA_DIR / "skipped-files.json"
SCAN_PROGRESS = METADATA_DIR / "scan-progress.json"


def load_json(path, default=None):
    """加载 JSON 文件"""
    if not path.exists():
        return default if default is not None else {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    """保存 JSON 文件"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_entries(data):
    """统一获取 entries 列表"""
    if isinstance(data, dict):
        return data.get("files", [])
    if isinstance(data, list):
        return data
    return []


def compute_fingerprint(entry):
    """计算条目指纹（用于去重）"""
    path = entry.get("path", entry.get("source_path", entry.get("file_path", "")))
    title = entry.get("title", "")
    return f"{path}::{title}"


def cmd_stats(args):
    """打印索引统计"""
    idx = load_json(SOURCE_INDEX, {"files": []})
    skip = load_json(SKIPPED_FILES, [])

    entries = get_entries(idx)
    skipped = skip if isinstance(skip, list) else skip.get("files", [])

    # 按目录统计
    from collections import Counter
    idx_dirs = Counter()
    for e in entries:
        p = e.get("path", "")
        d = p.split("/")[0] if "/" in p else "(root)"
        idx_dirs[d] += 1

    high_quality = sum(1 for e in entries if e.get("quality") == "high")
    medium_quality = sum(1 for e in entries if e.get("quality") == "medium")

    result = {
        "total_indexed": len(entries),
        "high_quality": high_quality,
        "medium_quality": medium_quality,
        "total_skipped": len(skipped),
        "by_directory": dict(idx_dirs.most_common()),
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_append(args):
    """追加索引条目"""
    entries_raw = json.loads(args.entries)
    idx = load_json(SOURCE_INDEX, {"files": []})
    existing = get_entries(idx)

    # 构建已有指纹集合
    existing_fps = set()
    for e in existing:
        existing_fps.add(compute_fingerprint(e))

    # 去重追加
    added = []
    duplicates = 0
    for entry in entries_raw:
        fp = compute_fingerprint(entry)
        if fp not in existing_fps:
            # 确保有 scored_at 时间戳
            if "scored_at" not in entry:
                entry["scored_at"] = datetime.now().isoformat()
            existing.append(entry)
            existing_fps.add(fp)
            added.append(entry.get("title", entry.get("path", "unknown")))
        else:
            duplicates += 1

    # Preserve top-level schema/mapping metadata added by architecture migrations.
    if isinstance(idx, dict):
        idx["files"] = existing
        save_json(SOURCE_INDEX, idx)
    else:
        save_json(SOURCE_INDEX, {"files": existing})

    result = {
        "added": len(added),
        "duplicates": duplicates,
        "total_indexed": len(existing),
        "added_titles": added[:10],  # 最多返回 10 条
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_append_skipped(args):
    """追加跳过记录"""
    entries_raw = json.loads(args.entries)
    skip = load_json(SKIPPED_FILES, [])

    if not isinstance(skip, list):
        skip = skip.get("files", [])

    # 构建已有指纹集合
    existing_fps = set()
    for e in skip:
        if isinstance(e, str):
            existing_fps.add(e)
        else:
            existing_fps.add(compute_fingerprint(e))

    added = 0
    for entry in entries_raw:
        if isinstance(entry, str):
            if entry not in existing_fps:
                skip.append(entry)
                existing_fps.add(entry)
                added += 1
        else:
            fp = compute_fingerprint(entry)
            if fp not in existing_fps:
                skip.append(entry)
                existing_fps.add(fp)
                added += 1

    save_json(SKIPPED_FILES, skip)

    result = {
        "added": added,
        "total_skipped": len(skip),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_search(args):
    """按关键词搜索索引"""
    idx = load_json(SOURCE_INDEX, {"files": []})
    entries = get_entries(idx)

    query = args.query.lower()
    matches = []
    for e in entries:
        searchable = json.dumps(e, ensure_ascii=False).lower()
        if query in searchable:
            matches.append({
                "title": e.get("title", ""),
                "path": e.get("path", ""),
                "quality": e.get("quality", ""),
                "score": e.get("score", 0),
            })

    result = {
        "query": query,
        "matches": len(matches),
        "results": matches[:20],  # 最多 20 条
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_get_progress(args):
    """获取扫描进度"""
    progress = load_json(SCAN_PROGRESS)
    print(json.dumps(progress, ensure_ascii=False, indent=2))


def cmd_update_progress(args):
    """更新扫描进度"""
    data = json.loads(args.json)
    save_json(SCAN_PROGRESS, data)
    print(json.dumps({"status": "ok", "updated": True}, ensure_ascii=False))


def cmd_get_recent(args):
    """获取最近 N 条索引"""
    idx = load_json(SOURCE_INDEX, {"files": []})
    entries = get_entries(idx)

    limit = args.limit or 20
    recent = entries[-limit:]

    # 精简输出
    output = []
    for e in recent:
        output.append({
            "title": e.get("title", ""),
            "path": e.get("path", ""),
            "score": e.get("score", 0),
            "quality": e.get("quality", ""),
        })

    result = {
        "total_indexed": len(entries),
        "returned": len(output),
        "recent": output,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="source-index.json 操作助手")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("stats", help="打印索引统计")
    subparsers.add_parser("get-progress", help="获取扫描进度")
    subparsers.add_parser("get-recent", help="获取最近索引").add_argument("--limit", type=int, default=20)

    # append
    p_append = subparsers.add_parser("append", help="追加索引条目")
    p_append.add_argument("--entries", required=True, help="JSON 数组")

    # append-skipped
    p_skip = subparsers.add_parser("append-skipped", help="追加跳过记录")
    p_skip.add_argument("--entries", required=True, help="JSON 数组")

    # search
    p_search = subparsers.add_parser("search", help="搜索索引")
    p_search.add_argument("--query", required=True, help="搜索关键词")

    # update-progress
    p_prog = subparsers.add_parser("update-progress", help="更新扫描进度")
    p_prog.add_argument("--json", required=True, help="完整 JSON")

    args = parser.parse_args()

    if args.command == "stats":
        cmd_stats(args)
    elif args.command == "append":
        cmd_append(args)
    elif args.command == "append-skipped":
        cmd_append_skipped(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "get-progress":
        cmd_get_progress(args)
    elif args.command == "update-progress":
        cmd_update_progress(args)
    elif args.command == "get-recent":
        cmd_get_recent(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
