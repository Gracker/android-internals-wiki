from pathlib import Path
import re

AIW = Path('/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki')
SRC = AIW / 'src'

def get_frontmatter(p):
    t = p.read_text('utf-8', errors='ignore')
    if not t.startswith('---'): return {}
    e = t.find('\n---', 3)
    if e < 0: return {}
    d = {}
    for l in t[3:e].splitlines():
        if l.strip() and not l.startswith(' ') and ':' in l and not l.lstrip().startswith('-'):
            k, v = l.split(':', 1)
            d[k.strip()] = v.strip().strip('"\'')
    return d

def get_content(p):
    t = p.read_text('utf-8', errors='ignore')
    if not t.startswith('---'):
        return t
    e = t.find('\n---', 3)
    if e < 0:
        return t
    return t[e+3:].strip()

empty_drafts = []
total_lines = 0

for p in SRC.rglob('*.md'):
    if p.name.lower() in ('readme.md', 'summary.md'): continue
    
    fm = get_frontmatter(p)
    content = get_content(p)
    content_lines = len([line for line in content.splitlines() if line.strip()])
    
    if fm.get('status') == 'draft' and content_lines < 15:
        empty_drafts.append((p, content_lines, content))
    
    total_lines += content_lines

print(f"Total files checked: {len(list(SRC.rglob('*.md')))}")
print(f"Total content lines across all files: {total_lines}")
print(f"Empty draft files found: {len(empty_drafts)}")
if empty_drafts:
    for p, lines, content in empty_drafts:
        print(f"  - {p.relative_to(SRC)}: {lines} lines")
        print(f"    Content preview: {content[:100]}...")