#!/usr/bin/env python3
import os
import json
import re
from datetime import datetime

# Read current scan progress
with open('scan-progress.json', 'r') as f:
    progress = json.load(f)

# Read source index
with open('source-index.json', 'r') as f:
    source_index = json.load(f)

# Read skipped files
with open('skipped-files.json', 'r') as f:
    skipped = json.load(f)

# Get current directory
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Get all markdown files in current directory
md_files = []
for root, dirs, files in os.walk(current_dir):
    for f in files:
        if f.endswith('.md'):
            md_files.append(os.path.join(root, f))

# Sort by filename (priority order)
md_files.sort(key=lambda x: x.split('/')[-1])

print(f"Found {len(md_files)} markdown files to process")
print(f"Current progress: {len(progress)} files scanned")
print(f"Source index: {len(source_index)} entries")
print(f"Skipped files: {len(skipped)} entries")

# Process each file
for md_file in md_files:
    filename = os.path.basename(md_file)
    title = None
    content = None
    
    # Read file content
    with open(md_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Extract title (first line)
    title_match = re.match(r'^\s*(.+?)\s*\n', content, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
    
    # Extract first 200 characters
    first_200 = content[:200].strip()
    
    # Score the file
    scores = {
        'relevance': 0,
        'technical_depth': 0,
        'timeliness': 0,
        'verifiability': 0,
        'total': 0
    }
    
    # Determine score based on content
    if 'Android' in title or 'android' in title.lower():
        scores['relevance'] = 3
    elif 'Android' in content or 'android' in content.lower():
        scores['relevance'] = 2
    elif 'Android' in filename or 'android' in filename.lower():
        scores['relevance'] = 1
    
    if '调度' in title or 'schedule' in title.lower() or '调度' in content or 'schedule' in content.lower():
        scores['technical_depth'] = 2
    elif '调度' in filename or 'schedule' in filename.lower():
        scores['technical_depth'] = 1
    
    if '负载' in title or 'load' in title.lower() or '负载' in content or 'load' in content.lower():
        scores['technical_depth'] = 2
    elif '负载' in filename or 'load' in filename.lower():
        scores['technical_depth'] = 1
    
    if '调度' in title or 'schedule' in title.lower() or '调度' in content or 'schedule' in content.lower():
        scores['timeliness'] = 3
    elif '调度' in filename or 'schedule' in filename.lower():
        scores['timeliness'] = 2
    
    if '调度' in title or 'schedule' in title.lower() or '调度' in content or 'schedule' in content.lower():
        scores['verifiability'] = 2
    elif '调度' in filename or 'schedule' in filename.lower():
        scores['verifiability'] = 1
    
    if '调度' in title or 'schedule' in title.lower() or '调度' in content or 'schedule' in content.lower():
        scores['total'] = scores['relevance'] + scores['technical_depth'] + scores['timeliness'] + scores['verifiability']
    else:
        scores['total'] = 0
    
    # Check if should be skipped
    if scores['total'] < 10:
        skipped_file = skipped + [filename]
        skipped_file.append(f"总分{scores['total']}<10，详细：相关性{scores['relevance']}+技术{scores['technical_depth']}+时效{scores['timeliness']}+可验证{scores['verifiability']}")
    else:
        # Add to source index
        source_entry = {
            'path': md_file,
            'title': title,
            'first_200': first_200,
            'scores': scores,
            'chapters': [],
            'metadata': {
                'modified_time': datetime.now().isoformat(),
                'size': os.path.getsize(md_file)
            }
        }
        source_index.append(source_entry)
        skipped_file.append(f"总分{scores['total']}>=10，已添加到索引")
    
    # Update skipped files
    with open('skipped-files.json', 'w') as f:
        json.dump(skipped_file, f, indent=2)
    
    # Update scan progress
    progress['scanned'] = progress['scanned'] + 1
    with open('scan-progress.json', 'w') as f:
        json.dump(progress, f, indent=2)
    
    print(f"Processed: {filename} - Score: {scores['total']}/10")

print(f"\nScan complete!")
print(f"Files scanned: {progress['scanned']}")
print(f"Source index entries: {len(source_index)}")
print(f"Skipped files: {len(skipped)}")
