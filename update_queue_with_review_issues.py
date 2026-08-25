#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path

def add_review_issues_to_queue():
    """Add L3/L4 issues from the current review to the queue.json."""
    
    # Check current queue
    queue_path = "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki/metadata/queue.json"
    
    try:
        with open(queue_path, 'r', encoding='utf-8') as f:
            queue_data = json.load(f)
    except Exception as e:
        print(f"Error reading queue.json: {e}")
        return False
    
    # Review issues found for each chapter
    review_issues = {
        "src/part3-tools/ch17-apm/08-network-apm-internals.md": [
            {
                "type": "L4",
                "location": "活人感",
                "detail": "发现多处形容词+冒号模式（AI-like），影响表达生动性",
                "suggestion": "建议重写相关段落，使用更自然的表达方式"
            }
        ],
        "src/part3-tools/ch17-apm/11-hybrid-apm.md": [
            {
                "type": "L3", 
                "location": "内容深度",
                "detail": "Flutter FrameTiming 时间戳归一化需要更精确的实现方案",
                "suggestion": "建议补充具体的算法实现和边界条件处理"
            }
        ],
        "src/part2-performance/ch13-rendering-pipelines/11-video-overlay-media3-codec-pipeline.md": [
            {
                "type": "L3",
                "location": "内容深度", 
                "detail": "MediaCodec 与 Surface 协同机制缺乏实际案例分析",
                "suggestion": "建议增加典型场景下的配置参数和性能对比数据"
            },
            {
                "type": "L4",
                "location": "活人感",
                "detail": "多处抽象名词+形容词结构，表达过于学术化",
                "suggestion": "使用更具体的动词和实例说明技术概念"
            }
        ]
    }
    
    # Add new issues to queue
    added_issues = []
    for chapter_path, issues in review_issues.items():
        section = extract_section_from_path(chapter_path)
        section_title = extract_section_title(chapter_path)
        
        for issue in issues:
            queue_entry = {
                "section": section,
                "section_title": section_title,
                "priority": 75,  # Medium priority for Task 6 issues
                "reason": "[Task 6 Review] L3/L4 写作质量问题",
                "review_issues": [issue],
                "added_by": "openclaw-task6",
                "added_at": datetime.now().isoformat(),
                "status": "pending",
                "task6_reviewed_at": datetime.now().isoformat(),
                "task6_reviewed_by": "openclaw-task6"
            }
            queue_data["pending"].append(queue_entry)
            added_issues.append({
                "section": section,
                "issue_type": issue["type"],
                "location": issue["location"]
            })
    
    # Write updated queue
    try:
        with open(queue_path, 'w', encoding='utf-8') as f:
            json.dump(queue_data, f, ensure_ascii=False, indent=2)
        print(f"✅ Added {len(added_issues)} issues to queue.json")
        return True
    except Exception as e:
        print(f"Error writing queue.json: {e}")
        return False

def extract_section_from_path(chapter_path):
    """Extract section identifier from file path."""
    # Extract chapter and section from path
    parts = chapter_path.split('/')
    chapter_part = parts[-2]  # e.g., "ch17-apm"
    file_part = parts[-1]  # e.g., "08-network-apm-internals.md"
    
    # Extract section number from filename
    section_match = file_part.split('-')[0]
    if section_match.isdigit():
        section_num = section_match
    else:
        # Handle cases like "08-media-pipeline.md"
        section_num = file_part.split('-')[0]
    
    # Combine chapter and section
    if chapter_part.startswith('ch'):
        chapter_num = chapter_part[2:]  # Remove "ch"
        return f"{chapter_num}.{section_num}"
    else:
        return section_num

def extract_section_title(chapter_path):
    """Extract section title for display."""
    # Read the file and extract title from frontmatter
    full_path = f"/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki/{chapter_path}"
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract title from frontmatter
        title_pattern = r'title:\s*"([^"]+)"'
        match = re.search(title_pattern, content)
        if match:
            return match.group(1)
        
        # Fallback to filename without extension
        filename = Path(chapter_path).stem
        return filename.replace('-', ' ').title()
        
    except Exception as e:
        print(f"Error extracting title from {chapter_path}: {e}")
        return "Unknown"

def main():
    print("=== Adding Task 6 Review Issues to Queue ===\n")
    
    success = add_review_issues_to_queue()
    
    if success:
        print("📋 Summary:")
        print("   L3/L4 issues successfully added to queue.json")
        print("   Task 2B will process these issues")
        print("   Queue updated with Task 6 review metadata")
    else:
        print("❌ Failed to update queue.json")
    
    return success

if __name__ == "__main__":
    import re
    main()
