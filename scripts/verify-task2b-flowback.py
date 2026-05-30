#!/usr/bin/env python3
"""
Task2B Verifier - Verify chapters after Task2B/Task2B Lite/Task9 auto-fix
Check if they correctly flow back to Task6 standards.

Requirements for Task6 flowback:
1. queue.json has no pending Task6/Task9/External Review entries for that section
2. frontmatter must have:
   - status: ready-for-review
   - task2b_state: fixed
   - task6_state: revisiting
   - task9_state: pending (if Task9 not yet reviewed) or reviewed (if Task9 reviewed)
   - pipeline_stage: task6_pending
3. Main text content must have ≥30 effective lines (not empty shell)
"""

import json
import re
from pathlib import Path
from datetime import datetime, timedelta
import sys

def parse_frontmatter(file_path):
    """Parse frontmatter from markdown file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not content.startswith('---'):
            return {}
        
        # Extract frontmatter section
        end_idx = content.find('\n---', 3)
        if end_idx < 0:
            return {}
        
        frontmatter_text = content[3:end_idx]
        frontmatter = {}
        
        for line in frontmatter_text.split('\n'):
            line = line.strip()
            if line and ':' in line and not line.startswith(' '):
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip().strip('"\'')
                frontmatter[key] = value
        
        return frontmatter
    except Exception as e:
        print(f"Error parsing frontmatter from {file_path}: {e}")
        return {}

def check_queue_status(section, queue_data):
    """Check if section has any pending items in queue"""
    for item in queue_data:
        if item.get('section') == section and item.get('status') == 'pending':
            return False  # Has pending items
    return True  # No pending items

def count_effective_lines(file_path):
    """Count effective lines in main text (excluding frontmatter and outline)"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove frontmatter
        if content.startswith('---'):
            end_idx = content.find('\n---', 3)
            if end_idx >= 0:
                content = content[end_idx + 4:]  # Remove frontmatter
        
        # Remove outline section
        outline_start = content.find('<!-- outline-start -->')
        outline_end = content.find('<!-- outline-end -->')
        if outline_start >= 0 and outline_end >= outline_start:
            content = content[:outline_start] + content[outline_end + 18:]
        
        # Count non-empty, non-comment lines
        lines = content.split('\n')
        effective_lines = 0
        for line in lines:
            line = line.strip()
            if line and not line.startswith('<!--') and not line.startswith('[['):
                effective_lines += 1
        
        return effective_lines
    except Exception as e:
        print(f"Error counting lines in {file_path}: {e}")
        return 0

def verify_chapter(chapter_path, section, queue_data):
    """Verify a single chapter for Task6 flowback"""
    print(f"\n📋 Verifying {section} ({chapter_path})")
    
    # Parse frontmatter
    frontmatter = parse_frontmatter(chapter_path)
    
    # Check required frontmatter fields
    checks = {
        'status': frontmatter.get('status') == 'ready-for-review',
        'task2b_state': frontmatter.get('task2b_state') == 'fixed',
        'task6_state': frontmatter.get('task6_state') == 'revisiting',
        'pipeline_stage': frontmatter.get('pipeline_stage') == 'task6_pending',
        'queue_clean': check_queue_status(section, queue_data),
        'content_sufficient': count_effective_lines(chapter_path) >= 30
    }
    
    # Handle task9_state - can be either "pending" or "reviewed"
    task9_state = frontmatter.get('task9_state', 'unknown')
    task9_result = frontmatter.get('task9_result', 'unknown')
    checks['task9_state_ok'] = task9_state in ['pending', 'reviewed']
    
    print(f"   Frontmatter checks:")
    print(f"   - status == ready-for-review: {checks['status']}")
    print(f"   - task2b_state == fixed: {checks['task2b_state']}")
    print(f"   - task6_state == revisiting: {checks['task6_state']}")
    print(f"   - pipeline_stage == task6_pending: {checks['pipeline_stage']}")
    print(f"   - queue clean (no pending): {checks['queue_clean']}")
    print(f"   - content sufficient (≥30 lines): {checks['content_sufficient']}")
    print(f"   - task9_state ok (pending/reviewed): {checks['task9_state_ok']}")
    
    # Overall verification result
    all_passed = all(checks.values())
    
    return {
        'section': section,
        'chapter_path': chapter_path,
        'frontmatter': frontmatter,
        'checks': checks,
        'passed': all_passed,
        'effective_lines': count_effective_lines(chapter_path)
    }

def main():
    # Paths
    aiw_root = Path('/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki')
    queue_file = aiw_root / 'metadata' / 'queue.json'
    src_dir = aiw_root / 'src'
    
    # Load queue data
    try:
        with open(queue_file, 'r') as f:
            queue_data = json.load(f)
    except Exception as e:
        print(f"Error loading queue.json: {e}")
        return
    
    # Chapters to verify (based on progress.json analysis)
    chapters_to_verify = [
        {
            'section': '2.19',
            'chapter_path': src_dir / 'part1-fundamentals' / 'ch02-rendering' / '19-refresh-rate-switching.md',
            'expected_result': 'ready-for-task6'
        },
        {
            'section': '2.10', 
            'chapter_path': src_dir / 'part1-fundamentals' / 'ch02-rendering' / '10-gpu-rendering.md',
            'expected_result': 'blocked'
        }
    ]
    
    # Verify chapters
    results = []
    status_corrections = 0
    blocked_count = 0
    
    for chapter_info in chapters_to_verify:
        section = chapter_info['section']
        chapter_path = chapter_info['chapter_path']
        expected_result = chapter_info['expected_result']
        
        if not chapter_path.exists():
            print(f"❌ Chapter not found: {chapter_path}")
            results.append({
                'section': section,
                'result': 'blocked',
                'reason': 'file_not_found'
            })
            blocked_count += 1
            continue
        
        verification = verify_chapter(chapter_path, section, queue_data)
        results.append(verification)
        
        if verification['passed']:
            print(f"✅ {section} - Ready for Task6")
            status_corrections += 1
        else:
            print(f"❌ {section} - Blocked")
            blocked_count += 1
            print("   Failed checks:")
            for check_name, passed in verification['checks'].items():
                if not passed:
                    print(f"   - {check_name}: False")
    
    # Generate report
    print(f"\n🧪 Task2B Verifier · 回流复查")
    print(f"本轮复查：{', '.join([r['section'] for r in results])}")
    print(f"状态修正：{status_corrections}")
    print(f"阻塞：{blocked_count}")
    
    # Determine overall result
    if all(r['passed'] for r in results):
        print(f"结果：ready-for-task6")
    elif any(r['passed'] for r in results):
        print(f"结果：mixed")
    else:
        print(f"结果：blocked")
    
    return {
        'results': results,
        'status_corrections': status_corrections,
        'blocked_count': blocked_count
    }

if __name__ == "__main__":
    main()