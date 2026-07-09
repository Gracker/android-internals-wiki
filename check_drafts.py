import json
from pathlib import Path
import re

def extract_frontmatter(file_path):
    """Extract frontmatter from a markdown file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not content.startswith('---'):
            return {}
        
        end_idx = content.find('\n---', 3)
        if end_idx < 0:
            return {}
        
        frontmatter_content = content[3:end_idx]
        frontmatter = {}
        
        for line in frontmatter_content.splitlines():
            line = line.strip()
            if line and ':' in line and not line.startswith('-'):
                key, value = line.split(':', 1)
                frontmatter[key.strip()] = value.strip().strip('"\'')
        
        return frontmatter
    except:
        return {}

def count_content_lines(file_path):
    """Count substantive content lines in a markdown file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Count lines after frontmatter and outline markers
        lines = content.split('\n')
        content_lines = 0
        
        # Skip frontmatter
        in_frontmatter = False
        frontmatter_end = False
        for line in lines:
            if line.strip() == '---' and not in_frontmatter:
                in_frontmatter = True
                continue
            elif line.strip() == '---' and in_frontmatter:
                in_frontmatter = False
                frontmatter_end = True
                continue
            elif in_frontmatter:
                continue
            elif frontmatter_end:
                # Count substantive content lines
                if line.strip() and not line.startswith('#') and not line.startswith('>') and not line.startswith('<!--'):
                    content_lines += 1
        
        return content_lines
    except:
        return 0

# Find all markdown files
src_dir = Path('src')
draft_files = []

for md_file in src_dir.rglob('*.md'):
    if md_file.name.lower() in ['readme.md', 'summary.md']:
        continue
    
    frontmatter = extract_frontmatter(md_file)
    content_lines = count_content_lines(md_file)
    
    if frontmatter.get('status') == 'draft' and content_lines < 15:
        draft_files.append({
            'path': str(md_file),
            'content_lines': content_lines,
            'title': frontmatter.get('title', 'Unknown')
        })

print(f"Found {len(draft_files)} empty draft files (< 15 lines)")
for i, draft_file in enumerate(draft_files[:10], 1):  # Show first 10
    print(f"{i}. {draft_file['path']} - {draft_file['content_lines']} lines - {draft_file['title']}")

if len(draft_files) > 10:
    print(f"... and {len(draft_files) - 10} more")
    
if draft_files:
    print("\n📝 Empty draft files found - proceeding to Phase 2 (content processing)")
else:
    print("\n❌ No empty draft files found - proceeding to Phase 0.5 (backlog check)")
