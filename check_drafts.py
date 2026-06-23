import json
from pathlib import Path
import re

def extract_frontmatter(text):
    """Extract YAML frontmatter from markdown file"""
    if not text.startswith('---'):
        return {}
    
    end = text.find('\n---', 3)
    if end < 0:
        return {}
    
    fm_text = text[3:end]
    frontmatter = {}
    for line in fm_text.splitlines():
        line = line.strip()
        if line and ':' in line and not line.startswith('-'):
            key, value = line.split(':', 1)
            frontmatter[key.strip()] = value.strip().strip('"\'')
    return frontmatter

def count_content_lines(text):
    """Count actual content lines (excluding frontmatter, comments, and empty lines)"""
    # Remove frontmatter
    if text.startswith('---'):
        end = text.find('\n---', 3)
        if end > 0:
            content = text[end + 4:]  # Skip closing ---
        else:
            content = text
    else:
        content = text
    
    # Remove outline markers and comments
    lines = []
    for line in content.splitlines():
        line = line.strip()
        # Skip empty lines, outline markers, and comments
        if (line and 
            not line.startswith('<!-- outline-start -->') and
            not line.startswith('<!-- outline-end -->') and
            not line.startswith('<!--') and
            not line.startswith('> ') and
            not line.startswith('# ') and
            not line.startswith('## ')):
            lines.append(line)
    
    return len(lines)

# Scan for draft chapters
src_dir = Path('src')
empty_drafts = []

for md_file in src_dir.rglob('*.md'):
    if md_file.name.lower() in ('readme.md', 'summary.md', '参考资料.md'):
        continue
    
    try:
        content = md_file.read_text('utf-8', errors='ignore')
        fm = extract_frontmatter(content)
        
        if fm.get('status') == 'draft':
            content_lines = count_content_lines(content)
            if content_lines < 15:
                empty_drafts.append({
                    'path': str(md_file.relative_to(src_dir)),
                    'content_lines': content_lines,
                    'title': fm.get('title', 'Unknown')
                })
    except Exception as e:
        print(f"Error reading {md_file}: {e}")

print(f"Found {len(empty_drafts)} empty draft chapters:")
for draft in empty_drafts:
    print(f"  - {draft['path']} ({draft['content_lines']} lines, {draft['title']})")
