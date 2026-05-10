#!/usr/bin/env python3
import re
import os
import json
from pathlib import Path
import yaml
from datetime import datetime, timedelta

def extract_frontmatter(file_path):
    """Extract YAML frontmatter from a markdown file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Match YAML frontmatter between --- markers
        pattern = r'^---\s*\n(.*?)\n---\s*$'
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
        
        if match:
            frontmatter_text = match.group(1)
            try:
                frontmatter = yaml.safe_load(frontmatter_text)
                return frontmatter
            except yaml.YAMLError as e:
                print(f"Error parsing YAML in {file_path}: {e}")
                return {}
        return {}
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return {}

def check_chapters_needing_review():
    """Check all chapters and determine which need review."""
    src_dir = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki/src")
    
    review_candidates = {
        "highest_priority": [],  # re-review-materials + ready-for-review + task6_state: pending
        "second_priority": [],  # ready-for-review + task6_state: pending (no re-review-materials)
        "third_priority": [],   # ready-for-review + task6_state: revisiting
        "finalized_sample": []  # finalized (for sampling)
    }
    
    excluded_files = ["README.md", "SUMMARY.md", "GRAPH_REPORT.md"]
    
    # Get all .md files except excluded ones
    md_files = []
    for file_path in src_dir.rglob("*.md"):
        if any(excluded in file_path.name for excluded in excluded_files):
            continue
        md_files.append(file_path)
    
    print(f"Found {len(md_files)} .md files to check")
    
    # Check each file
    for file_path in md_files:
        relative_path = file_path.relative_to(src_dir)
        frontmatter = extract_frontmatter(file_path)
        
        status = frontmatter.get('status', '')
        task6_state = frontmatter.get('task6_state', '')
        has_re_review_materials = 're-review-materials' in frontmatter and frontmatter['re-review-materials']
        
        # Priority 1: Highest priority - re-review-materials + ready-for-review + pending
        if (status == 'ready-for-review' and 
            task6_state == 'pending' and 
            has_re_review_materials):
            review_candidates["highest_priority"].append({
                "path": str(relative_path),
                "title": frontmatter.get('title', 'Unknown'),
                "status": status,
                "task6_state": task6_state,
                "has_re_review_materials": True,
                "frontmatter": frontmatter
            })
        
        # Priority 2: Second priority - ready-for-review + pending (no re-review-materials)
        elif (status == 'ready-for-review' and 
              task6_state == 'pending' and 
              not has_re_review_materials):
            review_candidates["second_priority"].append({
                "path": str(relative_path),
                "title": frontmatter.get('title', 'Unknown'),
                "status": status,
                "task6_state": task6_state,
                "has_re_review_materials": False,
                "frontmatter": frontmatter
            })
        
        # Priority 3: Third priority - ready-for-review + revisiting
        elif (status == 'ready-for-review' and 
              task6_state == 'revisiting'):
            review_candidates["third_priority"].append({
                "path": str(relative_path),
                "title": frontmatter.get('title', 'Unknown'),
                "status": status,
                "task6_state": task6_state,
                "has_re_review_materials": False,
                "frontmatter": frontmatter
            })
        
        # Priority 4: Finalized (for sampling)
        elif status == 'finalized':
            review_candidates["finalized_sample"].append({
                "path": str(relative_path),
                "title": frontmatter.get('title', 'Unknown'),
                "status": status,
                "task6_state": task6_state,
                "has_re_review_materials": False,
                "frontmatter": frontmatter
            })
    
    return review_candidates

def main():
    candidates = check_chapters_needing_review()
    
    print("\n=== Review Priority Analysis ===\n")
    
    print(f"Highest Priority (re-review-materials + ready-for-review + pending): {len(candidates['highest_priority'])}")
    for i, candidate in enumerate(candidates['highest_priority'][:5], 1):
        print(f"  {i}. {candidate['path']} - {candidate['title']}")
    if len(candidates['highest_priority']) > 5:
        print(f"  ... and {len(candidates['highest_priority']) - 5} more")
    
    print(f"\nSecond Priority (ready-for-review + pending): {len(candidates['second_priority'])}")
    for i, candidate in enumerate(candidates['second_priority'][:5], 1):
        print(f"  {i}. {candidate['path']} - {candidate['title']}")
    if len(candidates['second_priority']) > 5:
        print(f"  ... and {len(candidates['second_priority']) - 5} more")
    
    print(f"\nThird Priority (ready-for-review + revisiting): {len(candidates['third_priority'])}")
    for i, candidate in enumerate(candidates['third_priority'][:5], 1):
        print(f"  {i}. {candidate['path']} - {candidate['title']}")
    if len(candidates['third_priority']) > 5:
        print(f"  ... and {len(candidates['third_priority']) - 5} more")
    
    print(f"\nFinalized (for sampling): {len(candidates['finalized_sample'])}")
    for i, candidate in enumerate(candidates['finalized_sample'][:5], 1):
        print(f"  {i}. {candidate['path']} - {candidate['title']}")
    if len(candidates['finalized_sample']) > 5:
        print(f"  ... and {len(candidates['finalized_sample']) - 5} more")
    
    # Determine which chapters to review this round
    chapters_to_review = []
    
    # Always take highest priority first
    if candidates['highest_priority']:
        chapters_to_review.extend(candidates['highest_priority'][:3])  # Take up to 3
        print(f"\n🎯 Selected {len(chapters_to_review)} chapters from highest priority")
    
    # If we need more, take from second priority
    if len(chapters_to_review) < 3 and candidates['second_priority']:
        remaining = min(3 - len(chapters_to_review), len(candidates['second_priority']))
        chapters_to_review.extend(candidates['second_priority'][:remaining])
        print(f"🎯 Added {remaining} chapters from second priority")
    
    # If still need more, take from third priority
    if len(chapters_to_review) < 3 and candidates['third_priority']:
        remaining = min(3 - len(chapters_to_review), len(candidates['third_priority']))
        chapters_to_review.extend(candidates['third_priority'][:remaining])
        print(f"🎯 Added {remaining} chapters from third priority")
    
    print(f"\n📋 Total chapters to review this round: {len(chapters_to_review)}")
    
    # Output selected chapters
    if chapters_to_review:
        print("\n📝 Selected chapters for review:")
        for i, candidate in enumerate(chapters_to_review, 1):
            print(f"  {i}. {candidate['path']} - {candidate['title']}")
            print(f"     Status: {candidate['status']}, Task6 State: {candidate['task6_state']}")
            if candidate['has_re_review_materials']:
                print(f"     🔄 Re-review materials: YES")
    
    return chapters_to_review

if __name__ == "__main__":
    main()