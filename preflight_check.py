import re
from pathlib import Path

def extract_frontmatter(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content.startswith('---'):
                return {}
            
            end_pos = content.find('\n---', 3)
            if end_pos < 0:
                return {}
            
            frontmatter_text = content[3:end_pos]
            frontmatter = {}
            
            for line in frontmatter_text.splitlines():
                line = line.strip()
                if ':' in line and not line.startswith('-'):
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip().strip('"')
            
            return frontmatter
    except:
        return {}

AIW = Path('/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki')
SRC = AIW / 'src'

cands = []
idle = []
t2b = []

for md_file in SRC.rglob('*.md'):
    if md_file.name.lower() in ('readme.md', 'summary.md'):
        continue
        
    fm = extract_frontmatter(md_file)
    status = fm.get('status', '')
    task9_state = fm.get('task9_state', '')
    
    if fm.get('task2b_state') == 'pending' or fm.get('pipeline_stage') == 'task2b_pending':
        t2b.append(str(md_file.relative_to(AIW)))
    
    if status in ('ready-for-review', 'finalized', 'ready-to-publish') and task9_state == 'pending':
        cands.append(str(md_file.relative_to(AIW)))
    
    if status == 'finalized' and task9_state == 'reviewed':
        idle.append(str(md_file.relative_to(AIW)))

print(f'CANDIDATES:{len(cands)}')
print(f'IDLE_AUDIT:{len(idle)}')
print(f'TASK2B_BACKLOG:{len(t2b)}')
for c in cands[:10]:
    print(f'CAND:{c}')