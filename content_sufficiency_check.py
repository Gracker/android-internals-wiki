#!/usr/bin/env python3
import os
from pathlib import Path

def count_content_lines(file_path):
    """Count lines in content (excluding frontmatter and outline)."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split by lines
        lines = content.split('\n')
        
        # Find content start (after outline-end)
        content_start = 0
        for i, line in enumerate(lines):
            if line.strip() == '<!-- outline-end -->':
                content_start = i + 1
                break
        
        # Count content lines (skip empty lines after outline-end)
        content_lines = []
        for line in lines[content_start:]:
            stripped = line.strip()
            if stripped and not stripped.startswith('<!--') and not stripped.startswith('[//]:'):
                content_lines.append(line)
        
        return len(content_lines), len(lines)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0, 0

def check_content_sufficiency(file_path):
    """Check if content is sufficient for review."""
    content_lines, total_lines = count_content_lines(file_path)
    
    # Check if it's a empty shell chapter
    is_empty = content_lines < 30
    has_real_content = content_lines >= 15
    
    return {
        'content_lines': content_lines,
        'total_lines': total_lines,
        'is_empty_shell': is_empty,
        'has_sufficient_content': has_real_content,
        'should_skip': is_empty
    }

def main():
    # The 3 selected chapters
    chapters = [
        'src/part3-tools/ch19-apm/18-network-apm-internals.md',
        'src/part3-tools/ch19-apm/21-hybrid-apm.md',
        'src/part2-performance/ch08-responsiveness/08-media-pipeline.md'
    ]
    
    print("=== Content Sufficiency Check ===\n")
    
    chapters_to_review = []
    skipped_chapters = []
    
    for chapter_path in chapters:
        full_path = f"/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki/{chapter_path}"
        result = check_content_sufficiency(full_path)
        
        print(f"📁 {chapter_path}")
        print(f"   Content lines: {result['content_lines']}")
        print(f"   Total lines: {result['total_lines']}")
        print(f"   Empty shell: {'YES' if result['is_empty_shell'] else 'NO'}")
        print(f"   Sufficient content: {'YES' if result['has_sufficient_content'] else 'NO'}")
        
        if result['should_skip']:
            print(f"   ⏭️  SKIP: Content insufficient (only {result['content_lines']} content lines)")
            skipped_chapters.append({
                'path': chapter_path,
                'reason': f"Content insufficient (only {result['content_lines']} content lines)"
            })
        else:
            print(f"   ✅ INCLUDE: Content sufficient for review")
            chapters_to_review.append(chapter_path)
        
        print()
    
    print(f"📋 Summary:")
    print(f"   Chapters to review: {len(chapters_to_review)}")
    print(f"   Chapters skipped: {len(skipped_chapters)}")
    
    if chapters_to_review:
        print(f"\n🎯 Selected chapters for review:")
        for i, chapter in enumerate(chapters_to_review, 1):
            print(f"   {i}. {chapter}")
    
    if skipped_chapters:
        print(f"\n⏭️  Skipped chapters:")
        for chapter in skipped_chapters:
            print(f"   - {chapter['path']}: {chapter['reason']}")
    
    return chapters_to_review

if __name__ == "__main__":
    main()
