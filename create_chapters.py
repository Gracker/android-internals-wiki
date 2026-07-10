import json
import re
from pathlib import Path
from datetime import datetime
import zoneinfo

AIW_ROOT = Path('/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki')
SRC = AIW_ROOT / 'src'
METADATA = AIW_ROOT / 'metadata'

def get_next_section_number(chapter_path):
    """Get the next section number for a chapter"""
    if not chapter_path.exists():
        return "1"
    
    # Find all existing section files
    section_files = list(chapter_path.glob("*.md"))
    existing_numbers = []
    
    for file in section_files:
        # Extract section number from filename (e.g., 1.1, 1.2, etc.)
        match = re.match(r'(\d+)\.(\d+)', file.stem)
        if match:
            existing_numbers.append(int(match.group(2)))
    
    if existing_numbers:
        return str(max(existing_numbers) + 1)
    else:
        return "1"

def create_chapter(candidate, rank):
    """Create a new chapter file based on candidate"""
    title = candidate['title']
    score = candidate['score']
    section = candidate.get('section', '')
    chapter = candidate.get('chapter', '')
    url_path = candidate['url'] or candidate['path']
    
    # Determine part and chapter path
    if chapter.startswith('ch') and len(chapter) > 2:
        # Format: ch01, ch02, etc.
        chapter_num = chapter[2:]
        # Find which part this chapter belongs to
        summary_path = SRC / 'SUMMARY.md'
        summary_content = summary_path.read_text()
        
        # Parse SUMMARY.md to find part mapping
        part_map = {}
        current_part = None
        
        for line in summary_content.split('\n'):
            line = line.strip()
            if line.startswith('# '):
                if '第' in line and '章' in line:
                    current_part = 'part1'  # Default to part1
                elif 'Part' in line:
                    current_part = f'part{line.split()[1]}'
            elif line.startswith('- [') and '.md)' in line:
                match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', line)
                if match:
                    chapter_ref = match.group(2)
                    if f'ch{chapter_num}' in chapter_ref:
                        part = current_part or 'part1'
                        break
        
        # If we can't find the part, default to part1
        part_dir = f'part1-fundamentals'
    else:
        # Default to part1
        part_dir = 'part1-fundamentals'
    
    # Create chapter directory structure
    if chapter.startswith('ch'):
        chapter_dir_name = f'ch{chapter_num}'
        chapter_path = SRC / part_dir / chapter_dir_name
    else:
        # For chapters without specific ch prefix, find appropriate location
        if 'memory' in section.lower():
            chapter_path = SRC / 'part1-fundamentals' / 'ch04-memory'
        elif 'startup' in section.lower():
            chapter_path = SRC / 'part1-fundamentals' / 'ch08-startup'
        elif 'rendering' in section.lower() or 'gpu' in section.lower():
            chapter_path = SRC / 'part2-performance' / 'ch02-rendering'
        else:
            chapter_path = SRC / 'part1-fundamentals' / 'ch01-architecture'
    
    # Ensure chapter directory exists
    chapter_path.mkdir(parents=True, exist_ok=True)
    
    # Get next section number
    section_num = get_next_section_number(chapter_path)
    
    # Create filename
    safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-')
    filename = f"{chapter_num}.{section_num}-{safe_title}.md"
    filepath = chapter_path / filename
    
    # Generate applicable versions
    applicable_versions = "Android 14 (API 34) - Android 17 (API 37)"
    
    # Create frontmatter and content
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    frontmatter = f"""---
title: "{title}"
chapter: "{chapter_num}.{section_num}"
status: draft
applicable_versions: "{applicable_versions}"
tags: [Android, {section.replace('-', ' ')}, optimization]
related_chapters: []
created_by: "task2a-knowledge-gap"
created_date: "{now:%Y-%m-%d}"
gap_source: "素材驱动/AOSP结构/官方文档/章节深挖/研究素材"
---

# {chapter_num}.{section_num} {title}

<!-- outline-start -->
## 要点

### 🔹 Android 17 新特性概览
Android 17 引入了 {title.split(' ')[1] if len(title.split(' ')) > 1 else title} 相关的重大改进，通过源码级优化和机制重构，为开发者提供了更强大的调试和优化能力。

### 🔹 核心机制解析
深入分析 Android 17 中 {title.split(' ')[1] if len(title.split(' ')) > 1 else title} 的底层实现原理，包括关键组件交互和数据流路径。

### 🔹 性能优化策略
基于源码分析，总结 {title.split(' ')[1] if len(title.split(' ')) > 1 else title} 领域的最佳实践和优化方案。

### 🔹 实战应用案例
通过真实场景案例，展示 {title.split(' ')[1] if len(title.split(' ')) > 1 else title} 技术在实际开发中的应用效果。

### 🔹 工具链与调试方法
介绍 Android 17 中针对 {title.split(' ')[1] if len(title.split(' ')) > 1 else title} 的专用调试工具和分析方法。

## 扩展

### 🔸 深度源码分析
[待补充: 源码关键函数和数据结构分析]

### 🔸 OEM厂商定制化实现
[待补充: 不同厂商的实现差异和优化策略]

### 🔸 性能基准测试
[待补充: 标准化性能测试方法和基准数据]

<!-- outline-end -->

> 本节内容待加工。

[来源: {url_path}]
"""
    
    # Write the file
    filepath.write_text(frontmatter)
    
    return {
        'title': title,
        'filepath': str(filepath.relative_to(AIW_ROOT)),
        'chapter': f"{chapter_num}.{section_num}",
        'score': score,
        'part': part_dir
    }

def create_chapter(candidate, rank):
    """Create a new chapter file based on candidate"""
    title = candidate['title']
    score = candidate['score']
    section = candidate.get('section', '')
    chapter = candidate.get('chapter', '')
    url_path = candidate['url'] or candidate['path']
    
    # Determine part and chapter path
    chapter_num = ""
    if chapter.startswith('ch') and len(chapter) > 2:
        # Format: ch01, ch02, etc.
        chapter_num = chapter[2:]
        
        # Map chapters to appropriate parts
        chapter_to_part = {
            'ch01': 'part1-fundamentals',
            'ch02': 'part2-performance', 
            'ch04': 'part1-fundamentals',
            'ch05': 'part1-fundamentals',
            'ch08': 'part1-fundamentals',
            'ch10': 'part3-tools',
            'ch11': 'part3-tools',
            'ch13': 'part3-tools',
            'ch14': 'part3-tools',
            'ch15': 'part3-tools',
            'ch16': 'part4-apps',
            'ch25': 'part5-app'
        }
        
        part_dir = chapter_to_part.get(chapter, 'part1-fundamentals')
        chapter_dir_name = f'ch{chapter_num}'
        chapter_path = SRC / part_dir / chapter_dir_name
    else:
        # Default mapping based on section
        if 'memory' in section.lower():
            part_dir = 'part1-fundamentals'
            chapter_path = SRC / part_dir / 'ch04-memory'
            chapter_num = "04"
        elif 'startup' in section.lower():
            part_dir = 'part1-fundamentals'
            chapter_path = SRC / part_dir / 'ch08-startup'
            chapter_num = "08"
        elif 'rendering' in section.lower() or 'gpu' in section.lower():
            part_dir = 'part2-performance'
            chapter_path = SRC / part_dir / 'ch02-rendering'
            chapter_num = "02"
        elif 'power' in section.lower():
            part_dir = 'part4-apps'
            chapter_path = SRC / part_dir / 'ch25-power'
            chapter_num = "25"
        elif 'tools' in section.lower():
            part_dir = 'part3-tools'
            chapter_path = SRC / part_dir / 'ch14-tools'
            chapter_num = "14"
        else:
            part_dir = 'part1-fundamentals'
            chapter_path = SRC / part_dir / 'ch01-architecture'
            chapter_num = "01"
    
    # Ensure chapter directory exists
    chapter_path.mkdir(parents=True, exist_ok=True)
    
    # Get next section number
    section_files = list(chapter_path.glob("*.md"))
    existing_numbers = []
    
    for file in section_files:
        match = re.match(r'(\d+)\.(\d+)', file.stem)
        if match:
            existing_numbers.append(int(match.group(2)))
    
    section_num = str(max(existing_numbers) + 1) if existing_numbers else "1"
    
    # Create filename
    safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-')
    filename = f"{chapter_num}.{section_num}-{safe_title}.md"
    filepath = chapter_path / filename
    
    # Generate applicable versions
    applicable_versions = "Android 14 (API 34) - Android 17 (API 37)"
    
    # Create frontmatter and content
    now = datetime.now(zoneinfo.ZoneInfo("Asia/Shanghai"))
    frontmatter = f"""---
title: "{title}"
chapter: "{chapter_num}.{section_num}"
status: draft
applicable_versions: "{applicable_versions}"
tags: [Android, {section.replace('-', ' ') if section else 'optimization'}, gap-mining]
related_chapters: []
created_by: "task2a-knowledge-gap"
created_date: "{now:%Y-%m-%d}"
gap_source: "素材驱动/AOSP结构/官方文档/章节深挖/研究素材"
---

# {chapter_num}.{section_num} {title}

<!-- outline-start -->
## 要点

### 🔹 Android 17 新特性概览
Android 17 引入了 {title.split(' ')[1] if len(title.split(' ')) > 1 else title} 相关的重大改进，通过源码级优化和机制重构，为开发者提供了更强大的调试和优化能力。

### 🔹 核心机制解析
深入分析 Android 17 中 {title.split(' ')[1] if len(title.split(' ')) > 1 else title} 的底层实现原理，包括关键组件交互和数据流路径。

### 🔹 性能优化策略
基于源码分析，总结 {title.split(' ')[1] if len(title.split(' ')) > 1 else title} 领域的最佳实践和优化方案。

### 🔹 实战应用案例
通过真实场景案例，展示 {title.split(' ')[1] if len(title.split(' ')) > 1 else title} 技术在实际开发中的应用效果。

### 🔹 工具链与调试方法
介绍 Android 17 中针对 {title.split(' ')[1] if len(title.split(' ')) > 1 else title} 的专用调试工具和分析方法。

## 扩展

### 🔸 深度源码分析
[待补充: 源码关键函数和数据结构分析]

### 🔸 OEM厂商定制化实现
[待补充: 不同厂商的实现差异和优化策略]

### 🔸 性能基准测试
[待补充: 标准化性能测试方法和基准数据]

<!-- outline-end -->

> 本节内容待加工。

[来源: {url_path}]
"""
    
    # Write the file
    filepath.write_text(frontmatter)
    
    return {
        'title': title,
        'filepath': str(filepath.relative_to(AIW_ROOT)),
        'chapter': f"{chapter_num}.{section_num}",
        'score': score,
        'part': part_dir
    }

def main():
    # Load qualified candidates
    with open('gap_analysis_results.json', 'r') as f:
        results = json.load(f)
    
    qualified_candidates = results['qualified_candidates']
    
    # Load current metadata
    progress_path = METADATA / 'progress.json'
    if progress_path.exists():
        with open(progress_path, 'r') as f:
            progress = json.load(f)
    else:
        progress = {'total': 0, 'draft': 0, 'ready': 0, 'final': 0}
    
    # Load queue
    queue_path = METADATA / 'queue.json'
    if queue_path.exists():
        with open(queue_path, 'r') as f:
            queue = json.load(f)
    else:
        queue = []
    
    # Create chapters for top candidates (limit to reasonable number for this demo)
    created_chapters = []
    for i, candidate in enumerate(qualified_candidates[:5], 1):  # Create top 5 for now
        chapter_info = create_chapter(candidate, i)
        created_chapters.append(chapter_info)
        
        # Update progress
        progress['total'] += 1
        progress['draft'] += 1
        
        # Add to queue
        queue.append({
            'title': chapter_info['title'],
            'path': chapter_info['filepath'],
            'priority': 80,
            'created_at': datetime.now(zoneinfo.ZoneInfo("Asia/Shanghai")).isoformat(),
            'estimated_time': 30  # minutes
        })
    
    # Save updated metadata
    with open(progress_path, 'w') as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)
    
    with open(queue_path, 'w') as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)
    
    # Return results
    return {
        'created_count': len(created_chapters),
        'chapters': created_chapters,
        'progress': progress,
        'queue_length': len(queue)
    }

if __name__ == "__main__":
    result = main()
    print(json.dumps(result, indent=2, ensure_ascii=False))