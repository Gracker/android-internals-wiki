#!/usr/bin/env python3
"""
AIW External Review Auto-Integration Script
Processes active external-review files and writes to queue.json, research-gaps.md, suggestions.md
"""
import json
import re
import os
import glob
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict

BASE = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki")
ER_DIR = BASE / "logs" / "external-review"
QUEUE_PATH = BASE / "metadata" / "queue.json"
GAPS_PATH = BASE / "intake" / "research-gaps.md"
SUGGEST_PATH = BASE / "intake" / "suggestions.md"
INT_LOG_DIR = BASE / "logs" / "external-review-integration"

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)

# ── helpers ──────────────────────────────────────────────────────────────
def read_text(p):
    return p.read_text(encoding="utf-8") if p.exists() else ""

def write_text(p, content):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

def write_json(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# ── section mapping from filename/content ────────────────────────────────
SECTION_MAP = {
    "responsiveness-principles": ("8.1", "响应速度原理"),
    "app-launch": ("8.2", "App 启动全流程"),
    "jank-methodology": ("7.3", "卡顿分析方法论"),
    "launch-optimization": ("8.3", "启动优化"),
    "other-scenarios": ("8.4", "其他响应速度场景"),
    "optimization": ("7.5", "优化策略汇总"),
    "case-studies": None,  # ambiguous - resolve from content
    "compose-performance": ("7.7", "Jetpack Compose 性能优化"),
    "recyclerview-performance": ("7.8", "RecyclerView 滑动优化"),
    "image-bitmap-performance": ("7.10", "图片加载与 Bitmap 性能优化"),
    "webview-performance": ("7.11", "WebView 性能优化"),
    "systemui-performance": ("7.13", "SystemUI 性能优化"),
    "gaps-dynamic-analysis": ("7.14", "GAPS 动态验证分析"),
    "anr-design": ("9.1", "ANR 设计思想"),
    "anr-types": ("9.2", "ANR 类型与触发条件"),
    "anr-analysis": ("9.3", "ANR 分析方法论"),
    "notification-performance-anr": ("9.6", "通知性能与 ANR"),
    "non-technical-anr-diagnosis": ("9.7", "非技术 ANR 诊断"),
    "coroutine-performance": ("8.6", "Kotlin Coroutine 性能实践"),
    "baseline-profiles": ("8.7", "Baseline Profiles"),
    "media-pipeline": ("8.8a", "媒体管线性能优化"),
    "system-triggered-profiling": ("8.8b", "系统触发式性能追踪"),
    "game-performance": ("8.9", "游戏性能优化"),
}

def get_section_from_filename(fname):
    """Extract section number and title from filename"""
    # Pattern: 2026-04-19-38-2.7-external-review.md
    m = re.match(r'.*?-(\d+)\.(\d+)-external-review\.md$', fname)
    if m:
        return f"{m.group(1)}.{m.group(2)}", None
    
    # Pattern: 2026-04-19-10-01-responsiveness-principles-external-review.md
    m = re.match(r'.*?-\d+-(\d+)-([a-z].*?)-external-review\.md$', fname)
    if m:
        key = m.group(2)
        if key in SECTION_MAP and SECTION_MAP[key]:
            return SECTION_MAP[key]
    
    # Pattern: 2026-04-19-10-README-external-review.md or 2026-04-19-11-README-external-review.md
    m = re.match(r'.*?-(\d+)-README-external-review\.md$', fname)
    if m:
        prefix = m.group(1)
        if prefix == "10":
            return "7.0", "第 7 章 平滑度 README"
        elif prefix == "11":
            return "9.0", "第 9 章 ANR README"
    
    return None, None

def get_section_from_content(content):
    """Try to extract section from content"""
    # Look for explicit section reference in 可闭环输出
    m = re.search(r'\*\*章节\*\*：\s*(\d+\.\d+)', content)
    if m:
        return m.group(1)
    
    # Look in 一、目标发现结果
    m = re.search(r'`(\d{2})-(\w[\w-]*?)\.md`', content)
    if m:
        fname_part = m.group(2)
        for key, val in SECTION_MAP.items():
            if val and key in fname_part:
                return val[0]
    
    return None

def resolve_case_studies(fname, content):
    """Resolve ambiguous case-studies files"""
    if "ch07" in content or "平滑度" in content or "ch07-smoothness" in content:
        return "7.6", "平滑度典型案例"
    elif "ch09" in content or "ANR" in content.split("##")[0][:500] or "ch09-anr" in content:
        return "9.5", "ANR 案例分析"
    return None, None

def resolve_title_from_content(section_num, content):
    """Try to get title from review content"""
    # Search for title patterns
    m = re.search(r'目标章节[：:]\s*`?src/[^`]*?/(\d{2}-[^`]+\.md)', content)
    if m:
        # Use the filename as reference
        pass
    
    # Common title map
    TITLE_MAP = {
        "2.7": "硬件层 (Hardware Layer) 优化",
        "2.8": "过度绘制 (Overdraw) 分析",
        "2.10": "GPU 渲染性能分析",
        "2.20": "多窗口与桌面模式渲染",
        "2.21": "文本渲染性能优化",
        "5.6": "Android 功耗管理",
        "5.7": "CPU 相关的版本演进",
        "5.9": "ADPF 动态性能框架",
        "5.10": "JobScheduler 性能",
        "5.11": "端侧 AI 推理性能优化",
    }
    return TITLE_MAP.get(section_num, "")

# ── P0/P1 extraction ────────────────────────────────────────────────────
def extract_issues(content, level_tag):
    """Extract P0 or P1 issues from content"""
    issues = []
    
    # Pattern 1: ### N. [P0/P1][type][location]  followed by bullet points
    pattern = rf'###\s*\d+\.\s*\[{level_tag}\]\[([^\]]*)\]\[([^\]]*)\]'
    for m in re.finditer(pattern, content):
        issue_type = m.group(1).strip()
        location = m.group(2).strip()
        
        # Get the text until next ### or ##
        start = m.end()
        next_section = re.search(r'\n##(?=#)', content[start:])
        end = start + next_section.start() if next_section else len(content)
        block = content[start:end]
        
        # Extract key details
        detail = ""
        suggestion = ""
        
        dm = re.search(r'\*\*原文问题\*\*[：:]\s*(.+?)(?:\n-|\n\n|\n##)', block, re.DOTALL)
        if dm:
            detail = dm.group(1).strip()[:500]
        
        sm = re.search(r'\*\*建议(?:修正方向|补充方向)\*\*[：:]\s*(.+?)(?:\n-|\n\n|\n##)', block, re.DOTALL)
        if sm:
            suggestion = sm.group(1).strip()[:300]
        
        if not detail:
            # Try another pattern
            dm = re.search(r'\*\*(?:原文问题|核验结论|内容)\*\*[：:]\s*(.+?)(?:\n\*\*|\n\n|\n##)', block, re.DOTALL)
            if dm:
                detail = dm.group(1).strip()[:500]
        
        issues.append({
            "type": issue_type,
            "location": location,
            "detail": detail or f"[{level_tag} issue from external review]",
            "suggestion": suggestion or "基于外部 AI review 修正",
        })
    
    # Pattern 2: - **[P0/P1][type][location]** (single-line variant)
    if not issues:
        pattern2 = rf'-\s*\*\*\[{level_tag}\]\[([^\]]*)\]\[([^\]]*)\]\*\*'
        for m in re.finditer(pattern2, content):
            issue_type = m.group(1).strip()
            location = m.group(2).strip()
            
            start = m.end()
            next_section = re.search(r'\n- \*\*\[', content[start:])
            end = start + next_section.start() if next_section else start + 2000
            block = content[start:min(end, start+2000)]
            
            detail = ""
            dm = re.search(r'\*\*原文问题\*\*[：:]\s*(.+?)(?:\n- \*\*|\n\n)', block, re.DOTALL)
            if dm:
                detail = dm.group(1).strip()[:500]
            
            suggestion = ""
            sm = re.search(r'\*\*建议(?:修正方向|补充方向)\*\*[：:]\s*(.+?)(?:\n- \*\*|\n\n)', block, re.DOTALL)
            if sm:
                suggestion = sm.group(1).strip()[:300]
            
            issues.append({
                "type": issue_type,
                "location": location,
                "detail": detail or f"[{level_tag} issue from external review]",
                "suggestion": suggestion or "基于外部 AI review 修正",
            })
    
    # Pattern 3: - **[P1][version][topic]** style
    if not issues:
        pattern3 = rf'-\s*\*\*\[{level_tag}\]\[([^\]]*)\]'
        for m in re.finditer(pattern3, content):
            issue_type = m.group(1).strip()
            start = m.end()
            # Get next 1000 chars or until next issue
            next_issue = re.search(r'\n-\s*\*\*\[', content[start:])
            end = start + next_issue.start() if next_issue else start + 1000
            block = content[start:min(end, start+1000)]
            
            # Extract content field
            cm = re.search(r'\*\*内容\*\*[：:]\s*(.+)', block)
            if cm:
                detail = cm.group(1).strip()[:500]
                issues.append({
                    "type": issue_type,
                    "location": "全文",
                    "detail": detail,
                    "suggestion": "基于外部 AI review 补充",
                })
    
    return issues

def extract_all_issues(content):
    """Extract all P0 and P1 issues"""
    p0 = extract_issues(content, "P0")
    p1 = extract_issues(content, "P1")
    return p0, p1

# ── Knowledge gaps extraction ───────────────────────────────────────────
def extract_gaps(content):
    """Extract knowledge gaps from the review"""
    gaps = []
    
    # Find 知识盲区清单 section
    gap_section = re.search(r'##\s*(?:七|7)\s*[、.]?\s*知识盲区清单(.*?)(?=\n##|\n##\s*[八八89]|$)', content, re.DOTALL)
    if not gap_section:
        gap_section = re.search(r'知识盲区清单(.*?)(?=\n##\s*[九90]|$)', content, re.DOTALL)
    
    if gap_section:
        block = gap_section.group(1)
        
        # Table format: | 盲区 | 重要程度 | 建议研究方向 |
        for m in re.finditer(r'\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|', block):
            gap_name = m.group(1).strip()
            importance = m.group(2).strip()
            direction = m.group(3).strip()
            if gap_name and gap_name != "盲区":
                gaps.append({
                    "name": gap_name,
                    "importance": importance,
                    "direction": direction,
                })
    
    # Also check 9.2 知识盲区清单
    gap_section2 = re.search(r'###?\s*9\.2\s*(?:知识盲区|知识资产)(.*?)(?=###?\s*9\.[34567]|$)', content, re.DOTALL)
    if gap_section2:
        block = gap_section2.group(1)
        for m in re.finditer(r'\*\*(.+?)\*\*[：:]\s*(.+?)(?=\n- \*\*|\n\n|\n###)', block, re.DOTALL):
            gap_name = m.group(1).strip()
            detail = m.group(2).strip()[:300]
            if gap_name not in [g["name"] for g in gaps]:
                gaps.append({
                    "name": gap_name,
                    "importance": "高",
                    "direction": detail,
                })
    
    return gaps

# ── P2/Suggestions extraction ───────────────────────────────────────────
def extract_suggestions(content):
    """Extract P2 suggestions"""
    suggestions = []
    p2_issues = extract_issues(content, "P2")
    for issue in p2_issues:
        suggestions.append({
            "type": issue["type"],
            "location": issue["location"],
            "detail": issue["detail"][:300],
            "suggestion": issue["suggestion"][:300],
        })
    return suggestions

# ── MAIN ─────────────────────────────────────────────────────────────────
def main():
    # 1. Discover active files
    exclude = {"README.md", "TEMPLATE.md"}
    active_files = []
    for f in sorted(ER_DIR.glob("*.md")):
        if f.name in exclude:
            continue
        if "batch-review-summary" in f.name:
            continue
        if f.name.startswith("archive"):
            continue
        active_files.append(f)
    
    print(f"Active files: {len(active_files)}")
    
    # 2. Load existing data
    queue = json.loads(read_text(QUEUE_PATH)) if QUEUE_PATH.exists() else []
    existing_gaps = read_text(GAPS_PATH)
    existing_suggestions = read_text(SUGGEST_PATH)
    
    # Track existing external-ai-review sections in queue
    existing_er_sections = set()
    for item in queue:
        if item.get("added_by") == "external-ai-review":
            existing_er_sections.add(item["section"])
    
    print(f"Existing external-ai-review sections in queue: {existing_er_sections}")
    
    # 3. Process each file
    new_queue_entries = []
    merged_queue_entries = {}
    new_gaps = []
    new_suggestions = []
    sections_processed = []
    errors = []
    
    for fpath in active_files:
        fname = fpath.name
        content = read_text(fpath)
        
        # Resolve section
        sec, title = get_section_from_filename(fname)
        
        # Handle case-studies ambiguity
        if sec is None and "case-studies" in fname:
            sec, title = resolve_case_studies(fname, content)
        
        # Try from content
        if sec is None:
            sec = get_section_from_content(content)
        
        if sec is None:
            errors.append(f"{fname}: 无法确定章节号")
            continue
        
        # Resolve title
        if not title:
            # Try from content
            tm = re.search(r'目标章节[：:]\s*`?.*?(\d{2}-[^`]*?)\.md', content)
            if tm:
                raw = tm.group(1)
                # Extract title from filename pattern
                parts = raw.split("-", 1)
                if len(parts) > 1:
                    title = parts[1].replace("-", " ").title()
            
            if not title:
                title = resolve_title_from_content(sec, content)
        
        if not title:
            title = sec
        
        sections_processed.append((sec, title))
        
        # Extract issues
        p0_issues, p1_issues = extract_all_issues(content)
        gaps = extract_gaps(content)
        suggestions = extract_suggestions(content)
        
        # Determine priority
        has_p0 = len(p0_issues) > 0
        priority = 95 if has_p0 else 85
        
        # Build review_issues
        all_issues = p0_issues + p1_issues
        
        if not all_issues:
            # Some files only have P1 in the "简要" format
            # Check for P1 mentions in content
            if "P1" in content and ("建议回炉" in content):
                # Create a generic issue
                all_issues.append({
                    "type": "外部Review建议回炉",
                    "location": f"external-review {sec}",
                    "detail": f"外部 AI review 建议回炉，请查阅 {fname} 获取详细问题清单",
                    "suggestion": "基于外部 AI review 修正",
                })
        
        if sec in existing_er_sections:
            # Merge into existing entry
            merged_queue_entries[sec] = {
                "issues": all_issues,
                "has_new_p0": has_p0,
            }
        else:
            # New entry
            new_queue_entries.append({
                "section": sec,
                "section_title": title,
                "priority": priority,
                "reason": f"[External Review] 外部 AI review 发现需回炉的问题",
                "material_paths": [],
                "review_issues": all_issues,
                "added_by": "external-ai-review",
                "added_at": NOW.isoformat(),
                "status": "pending",
                "source_file": fname,
            })
        
        new_gaps.append({
            "section": sec,
            "title": title,
            "gaps": gaps,
        })
        
        new_suggestions.append({
            "section": sec,
            "title": title,
            "items": suggestions,
        })
    
    # 4. Build updated queue
    updated_queue = list(queue)
    
    # Add new entries
    for entry in new_queue_entries:
        updated_queue.append(entry)
    
    # Merge into existing entries
    for item in updated_queue:
        if item.get("added_by") == "external-ai-review" and item["section"] in merged_queue_entries:
            merge = merged_queue_entries[item["section"]]
            existing_issues = item.get("review_issues", [])
            
            # Add new issues that aren't duplicates
            for new_issue in merge["issues"]:
                is_dup = False
                new_detail_key = new_issue.get("detail", "")[:50]
                for existing in existing_issues:
                    if new_detail_key and new_detail_key in existing.get("detail", ""):
                        is_dup = True
                        break
                if not is_dup:
                    existing_issues.append(new_issue)
            
            item["review_issues"] = existing_issues
            
            # Upgrade priority if new P0 found
            if merge["has_new_p0"] and item["priority"] < 95:
                item["priority"] = 95
    
    # Fix the "unknown" section - map to 7.0
    for item in updated_queue:
        if item["section"] == "unknown" and item.get("added_by") == "external-ai-review":
            item["section"] = "7.0"
            item["section_title"] = "第 7 章 README / Jank 定义"
    
    # 5. Write queue.json
    write_json(QUEUE_PATH, updated_queue)
    print(f"Queue written: {len(updated_queue)} total items, {len(new_queue_entries)} new, {len(merged_queue_entries)} merged")
    
    # 6. Write research-gaps.md
    gaps_lines = []
    if existing_gaps:
        gaps_lines.append(existing_gaps.rstrip())
    
    for entry in new_gaps:
        sec = entry["section"]
        title = entry["title"]
        for gap in entry["gaps"]:
            gap_text = f"## [{NOW.strftime('%Y-%m-%d')}] {sec} {title} — 知识盲区\n\n"
            gap_text += f"### 盲区描述\n{gap['name']}\n\n"
            gap_text += f"### 重要程度\n{gap['importance']}\n\n"
            gap_text += f"### 建议研究方向\n{gap['direction']}\n\n"
            gap_text += f"### 外部 review 来源\nGemini 外部 review\n"
            
            # Check for dedup
            gap_key = f"{sec}-{gap['name'][:30]}"
            if gap_key not in existing_gaps:
                gaps_lines.append(gap_text)
    
    if gaps_lines:
        write_text(GAPS_PATH, "\n\n".join(gaps_lines) + "\n")
    
    print(f"Research gaps: processed {sum(len(e['gaps']) for e in new_gaps)} gaps from {len(new_gaps)} files")
    
    # 7. Write suggestions.md
    suggest_lines = []
    if existing_suggestions:
        suggest_lines.append(existing_suggestions.rstrip())
    
    for entry in new_suggestions:
        sec = entry["section"]
        title = entry["title"]
        for item in entry["items"]:
            sug_text = f"## [External Review] {sec} {title} — {NOW.strftime('%Y-%m-%d')}\n"
            sug_text += f"- **类型**：{item['type']}\n"
            sug_text += f"- **位置**：{item['location']}\n"
            sug_text += f"- **问题**：{item['detail'][:200]}\n"
            sug_text += f"- **建议**：{item['suggestion'][:200]}\n"
            sug_text += f"- **来源**：Gemini 外部 review\n"
            
            sug_key = f"{sec}-{item['detail'][:30]}"
            if sug_key not in existing_suggestions:
                suggest_lines.append(sug_text)
    
    if suggest_lines:
        write_text(SUGGEST_PATH, "\n\n".join(suggest_lines) + "\n")
    
    print(f"Suggestions: processed {sum(len(e['items']) for e in new_suggestions)} suggestions from {len(new_suggestions)} files")
    
    # 8. Write integration log
    INT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_name = f"{NOW.strftime('%Y-%m-%d-%H')}-integration.md"
    log_path = INT_LOG_DIR / log_name
    
    log_lines = [
        f"# External Review Integration Log — {NOW.strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 扫描结果",
        f"- 活跃文件：{len(active_files)}",
        f"- 成功处理：{len(sections_processed)}",
        f"- 跳过：{len(errors)}",
        f"- 错误：{len(errors)}",
        "",
        "## 写入结果",
        f"- queue.json：新增 {len(new_queue_entries)} 条，合并 {len(merged_queue_entries)} 条",
        f"- research-gaps.md：处理 {sum(len(e['gaps']) for e in new_gaps)} 条",
        f"- suggestions.md：处理 {sum(len(e['items']) for e in new_suggestions)} 条",
        "",
        "## 涉及章节",
    ]
    
    seen_sections = set()
    for sec, title in sections_processed:
        if sec not in seen_sections:
            log_lines.append(f"- {sec} {title}")
            seen_sections.add(sec)
    
    if errors:
        log_lines.append("")
        log_lines.append("## 错误/跳过")
        for err in errors:
            log_lines.append(f"- {err}")
    
    write_text(log_path, "\n".join(log_lines) + "\n")
    print(f"Integration log written: {log_path}")
    
    # 9. Summary for report
    print("\n=== INTEGRATION SUMMARY ===")
    print(f"Active files scanned: {len(active_files)}")
    print(f"Successfully processed: {len(sections_processed)}")
    print(f"Skipped/errors: {len(errors)}")
    print(f"Queue: {len(new_queue_entries)} new, {len(merged_queue_entries)} merged")
    print(f"Sections: {', '.join(sorted(seen_sections))}")

if __name__ == "__main__":
    main()
