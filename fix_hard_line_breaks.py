#!/usr/bin/env python3
import re
from pathlib import Path

def fix_hard_line_breaks_in_file(file_path):
    """Fix hard line breaks in the middle of sentences."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False
    
    lines = content.split('\n')
    fixed_lines = []
    changes_made = []
    
    for i, line in enumerate(lines):
        # Check if this is a hard break in the middle of a sentence
        is_hard_break = (
            len(line.strip()) > 0 and 
            len(line.strip()) < 50 and 
            i < len(lines) - 1 and 
            not line.strip().endswith(('。', '！', '？', '.', '!', '?')) and
            not line.strip().startswith('#') and
            not line.strip().startswith('-') and
            not line.strip().startswith('*') and
            not line.strip().startswith('```') and
            not line.strip().startswith('<!--') and
            not line.strip().startswith('[//]:') and
            not line.strip().startswith('[') and line.strip().endswith(']')
        )
        
        if is_hard_break:
            # Join with the next line
            if i + 1 < len(lines):
                combined_line = line.strip() + ' ' + lines[i + 1].strip()
                fixed_lines.append(combined_line)
                changes_made.append({
                    'line_num': i + 1,
                    'original': line.strip(),
                    'fixed': combined_line,
                    'next_line': lines[i + 1].strip()
                })
                # Skip the next line since we've combined it
                continue
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    # Write back the fixed content
    if changes_made:
        fixed_content = '\n'.join(fixed_lines)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"✅ Fixed {len(changes_made)} hard line breaks in {file_path}")
            return True
        except Exception as e:
            print(f"Error writing to {file_path}: {e}")
            return False
    else:
        print(f"✅ No hard line breaks found in {file_path}")
        return False

def main():
    chapters = [
        'src/part3-tools/ch19-apm/18-network-apm-internals.md',
        'src/part3-tools/ch19-apm/21-hybrid-apm.md',
        'src/part2-performance/ch08-responsiveness/08-media-pipeline.md'
    ]
    
    print("=== Fixing Hard Line Breaks ===\n")
    
    total_fixed = 0
    for chapter in chapters:
        full_path = f"/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki/{chapter}"
        if fix_hard_line_breaks_in_file(full_path):
            total_fixed += 1
    
    print(f"\n📊 Summary:")
    print(f"   Files processed: {len(chapters)}")
    print(f"   Files with fixes: {total_fixed}")
    print(f"   All chapters ready for review")

if __name__ == "__main__":
    main()
