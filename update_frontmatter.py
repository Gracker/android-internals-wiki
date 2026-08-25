#!/usr/bin/env python3
import re
import yaml
from datetime import datetime
from pathlib import Path

def update_chapter_frontmatter(file_path):
    """Update the frontmatter of a chapter with Task 6 review results."""
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False
    
    # Extract current frontmatter
    frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*$'
    match = re.search(frontmatter_pattern, content, re.MULTILINE | re.DOTALL)
    
    if not match:
        print(f"No frontmatter found in {file_path}")
        return False
    
    try:
        current_frontmatter = yaml.safe_load(match.group(1))
    except Exception as e:
        print(f"Error parsing YAML frontmatter in {file_path}: {e}")
        return False
    
    # Update Task 6 metadata
    current_frontmatter['task6_state'] = 'reviewed'
    current_frontmatter['task6_result'] = 'pass-light-edit'
    current_frontmatter['task6_reviewed_at'] = datetime.now().isoformat()
    current_frontmatter['task6_reviewed_by'] = 'openclaw-task6'
    
    # Check auto-promotion conditions
    should_promote = check_auto_promotion(current_frontmatter)
    
    if should_promote:
        current_frontmatter['status'] = 'finalized'
        current_frontmatter['pipeline_stage'] = 'ready-to-publish'
        print(f"✅ Auto-promoting {file_path} to finalized")
    else:
        print(f"✅ Reviewed but not auto-promoting {file_path}")
    
    # Convert updated frontmatter back to YAML
    try:
        new_frontmatter_yaml = yaml.dump(current_frontmatter, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        print(f"Error dumping YAML for {file_path}: {e}")
        return False
    
    # Rebuild the content
    new_content = f"---\n{new_frontmatter_yaml}---\n{content[match.end():]}"
    
    # Write back the updated content
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    except Exception as e:
        print(f"Error writing to {file_path}: {e}")
        return False

def check_auto_promotion(frontmatter):
    """Check if chapter should be auto-promoted to finalized."""
    # Check if task6_result is pass-light-edit
    task6_pass = frontmatter.get('task6_result') == 'pass-light-edit'
    
    # Check if task9_result is pass-tech-review  
    task9_pass = frontmatter.get('task9_result') == 'pass-tech-review'
    
    # Check if there are pending queue items for this section
    section = frontmatter.get('section', 'unknown')
    has_pending_queue = check_queue_pending(section)
    
    return task6_pass and task9_pass and not has_pending_queue

def check_queue_pending(section):
    """Check if there are pending items in queue.json for this section."""
    try:
        with open("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki/metadata/queue.json", 'r', encoding='utf-8') as f:
            queue_data = json.load(f)
        
        for item in queue_data.get('pending', []):
            if item.get('section') == section:
                return True
        return False
    except Exception as e:
        print(f"Error checking queue for section {section}: {e}")
        return True  # Assume there are pending items if we can't check

def main():
    chapters = [
        'src/part3-tools/ch17-apm/08-network-apm-internals.md',
        'src/part3-tools/ch17-apm/11-hybrid-apm.md',
        'src/part2-performance/ch13-rendering-pipelines/11-video-overlay-media3-codec-pipeline.md'
    ]
    
    print("=== Updating Chapter Frontmatter ===\n")
    
    total_updated = 0
    for chapter in chapters:
        full_path = f"/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki/{chapter}"
        if update_chapter_frontmatter(full_path):
            total_updated += 1
    
    print(f"\n📊 Summary:")
    print(f"   Chapters processed: {len(chapters)}")
    print(f"   Frontmatter updated: {total_updated}")
    
    return total_updated == len(chapters)

if __name__ == "__main__":
    import json
    main()
