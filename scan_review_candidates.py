#!/usr/bin/env python3
import os
import json
import re
import yaml
from pathlib import Path
from datetime import datetime, timedelta

def extract_frontmatter(file_path):
    """Extract YAML frontmatter from markdown file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Match frontmatter between --- delimiters
        frontmatter_match = re.search(r'^---\s*\n(.*?)\n---\s*$', content, re.MULTILINE | re.DOTALL)
        if frontmatter_match:
            frontmatter_content = frontmatter_match.group(1)
            try:
                return yaml.safe_load(frontmatter_content)
            except yaml.YAMLError:
                return {}
        return {}
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return {}

def get_review_candidates(src_dir):
    """Find chapters that need review"""
    candidates = {
        're-review-mode': [],  # Has re-review-materials field
        'first-review-priority': [],  # ready-for-review + task6_state: pending (no re-review-materials)
        'revisiting': [],  # ready-for-review + task6_state: revisiting
        'finalized-sample': [],  # finalized chapters (for quality sampling)
        'excluded': []  # ready-to-publish or other excluded statuses
    }
    
    # Get all markdown files (excluding README.md)
    md_files = []
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith('.md') and file != 'README.md':
                md_files.append(os.path.join(root, file))
    
    today = datetime.now()
    
    for file_path in md_files:
        frontmatter = extract_frontmatter(file_path)
        
        # Skip if no frontmatter
        if not frontmatter:
            continue
            
        # Determine chapter path relative to src
        rel_path = os.path.relpath(file_path, src_dir)
        
        # Check status and task6_state
        status = frontmatter.get('status', '')
        task6_state = frontmatter.get('task6_state', '')
        has_re_review_materials = 're-review-materials' in frontmatter
        
        # Rule 1: Highest priority - re-review mode
        if (status == 'ready-for-review' and 
            task6_state == 'pending' and 
            has_re_review_materials):
            candidates['re-review-mode'].append({
                'path': rel_path,
                'file_path': file_path,
                'frontmatter': frontmatter
            })
        
        # Rule 2: Second priority - first review (no re-review-materials)
        elif (status == 'ready-for-review' and 
              task6_state == 'pending' and 
              not has_re_review_materials):
            candidates['first-review-priority'].append({
                'path': rel_path,
                'file_path': file_path,
                'frontmatter': frontmatter
            })
        
        # Rule 3: Third priority - revisiting
        elif (status == 'ready-for-review' and 
              task6_state == 'revisiting'):
            candidates['revisiting'].append({
                'path': rel_path,
                'file_path': file_path,
                'frontmatter': frontmatter
            })
        
        # Rule 4: Optional sampling - finalized chapters
        elif status == 'finalized':
            # For sampling, check if reviewed more than 7 days ago or never reviewed
            last_review = frontmatter.get('reviewed_date', '')
            should_sample = False
            
            if last_review:
                try:
                    review_date = datetime.fromisoformat(last_review.replace('Z', '+00:00'))
                    if (today - review_date).days > 7:
                        should_sample = True
                except:
                    should_sample = True  # If date parsing fails, sample it
            else:
                should_sample = True  # Never reviewed, sample it
            
            if should_sample:
                candidates['finalized-sample'].append({
                    'path': rel_path,
                    'file_path': file_path,
                    'frontmatter': frontmatter
                })
        
        # Rule 5: Never select - ready-to-publish
        elif status == 'ready-to-publish':
            candidates['excluded'].append({
                'path': rel_path,
                'file_path': file_path,
                'reason': 'ready-to-publish (excluded)'
            })
    
    return candidates

def check_content_sufficiency(file_path):
    """Check if chapter has sufficient content for review"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find outline-end marker
        outline_end_match = re.search(r'<!-- outline-end -->', content)
        if not outline_end_match:
            return False, 0, 0  # No outline-end found
        
        # Count lines after outline-end
        after_outline = content[outline_end_match.end():]
        lines = after_outline.strip().split('\n')
        
        # Count total lines and valid content lines
        total_lines = len(lines)
        valid_lines = 0
        
        for line in lines:
            line = line.strip()
            # Skip empty lines, pure comments, and title-only lines
            if (line and 
                not line.startswith('//') and 
                not line.startswith('#') and 
                not line.startswith('<!--') and 
                not line.startswith('-->') and
                not line.startswith('TODO') and
                not line.startswith('待补充') and
                not line.startswith('TBD') and
                not line.startswith('此处填写内容') and
                not line.startswith('...')):
                valid_lines += 1
        
        return True, total_lines, valid_lines
    except Exception as e:
        print(f"Error checking content sufficiency for {file_path}: {e}")
        return False, 0, 0

def main():
    src_dir = "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki/src"
    
    print(f"Scanning for review candidates in {src_dir}...")
    candidates = get_review_candidates(src_dir)
    
    print("\n=== Review Candidates Summary ===")
    print(f"Re-review mode (highest priority): {len(candidates['re-review-mode'])}")
    print(f"First review priority: {len(candidates['first-review-priority'])}")
    print(f"Revisiting: {len(candidates['revisiting'])}")
    print(f"Finalized sampling candidates: {len(candidates['finalized-sample'])}")
    print(f"Excluded: {len(candidates['excluded'])}")
    
    # Display detailed candidate info
    print("\n=== Detailed Candidates ===")
    
    # Re-review mode (highest priority)
    if candidates['re-review-mode']:
        print("\n🔄 Re-review mode candidates:")
        for candidate in candidates['re-review-mode']:
            print(f"  - {candidate['path']}")
            print(f"    re-review-materials: {len(candidate['frontmatter'].get('re-review-materials', []))} items")
    
    # First review priority
    if candidates['first-review-priority']:
        print("\n📝 First review priority candidates:")
        for candidate in candidates['first-review-priority']:
            print(f"  - {candidate['path']}")
    
    # Revisiting
    if candidates['revisiting']:
        print("\n🔄 Revisiting candidates:")
        for candidate in candidates['revisiting']:
            print(f"  - {candidate['path']}")
    
    # Finalized sampling
    if candidates['finalized-sample']:
        print("\n✅ Finalized sampling candidates:")
        for candidate in candidates['finalized-sample']:
            print(f"  - {candidate['path']}")
    
    # Check content sufficiency for top candidates
    print("\n=== Content Sufficiency Check ===")
    
    # Check re-review candidates first (highest priority)
    if candidates['re-review-mode']:
        print("\n🔄 Re-review mode content check:")
        for candidate in candidates['re-review-mode'][:3]:  # Check first 3
            sufficient, total_lines, valid_lines = check_content_sufficiency(candidate['file_path'])
            print(f"  {candidate['path']}: {sufficient} (total: {total_lines}, valid: {valid_lines})")
    
    # Check first review candidates
    if candidates['first-review-priority']:
        print("\n📝 First review content check:")
        for candidate in candidates['first-review-priority'][:3]:  # Check first 3
            sufficient, total_lines, valid_lines = check_content_sufficiency(candidate['file_path'])
            print(f"  {candidate['path']}: {sufficient} (total: {total_lines}, valid: {valid_lines})")
    
    # Return top candidates for this round
    selected_candidates = []
    
    # First select re-review candidates (highest priority)
    for candidate in candidates['re-review-mode']:
        sufficient, _, _ = check_content_sufficiency(candidate['file_path'])
        if sufficient:
            selected_candidates.append(('re-review-mode', candidate))
    
    # Then select first review candidates
    if len(selected_candidates) < 3:  # Aim for 3-4 chapters per round
        available_slots = 3 - len(selected_candidates)
        for candidate in candidates['first-review-priority']:
            if len(selected_candidates) >= 3:
                break
            sufficient, _, _ = check_content_sufficiency(candidate['file_path'])
            if sufficient:
                selected_candidates.append(('first-review-priority', candidate))
    
    # Then add revisiting if still needed
    if len(selected_candidates) < 3:
        available_slots = 3 - len(selected_candidates)
        for candidate in candidates['revisiting']:
            if len(selected_candidates) >= 3:
                break
            sufficient, _, _ = check_content_sufficiency(candidate['file_path'])
            if sufficient:
                selected_candidates.append(('revisiting', candidate))
    
    print(f"\n=== Selected Candidates for This Round ({len(selected_candidates)}) ===")
    for mode, candidate in selected_candidates:
        print(f"  {mode}: {candidate['path']}")
    
    return selected_candidates

if __name__ == "__main__":
    main()