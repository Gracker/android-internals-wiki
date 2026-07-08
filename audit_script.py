#!/usr/bin/env python3
from pathlib import Path
import re
from datetime import datetime

def extract_frontmatter(content):
    """Extract frontmatter from markdown content"""
    if not content.startswith('---'):
        return {}
    
    end_idx = content.find('\n---', 3)
    if end_idx < 0:
        return {}
    
    frontmatter_text = content[3:end_idx]
    frontmatter = {}
    
    for line in frontmatter_text.splitlines():
        line = line.strip()
        if line and ':' in line:
            key, value = line.split(':', 1)
            frontmatter[key.strip()] = value.strip().strip('"\'')
    
    return frontmatter

def check_frontmatter_completeness(frontmatter):
    """Check if required frontmatter fields are present"""
    required_fields = ['title', 'chapter', 'status', 'applicable_versions', 'tags']
    issues = []
    
    for field in required_fields:
        if field not in frontmatter:
            issues.append(f"Missing required field: {field}")
    
    # Check status is 'finalized' for idle audit
    if frontmatter.get('status') != 'finalized':
        issues.append("Status should be 'finalized' for idle audit")
    
    # Check task6_state is 'reviewed'
    if frontmatter.get('task6_state') != 'reviewed':
        issues.append("task6_state should be 'reviewed' for idle audit")
    
    return issues

def check_outline_anchors(content):
    """Check if all outline anchors have content"""
    # Extract outline section
    outline_start = content.find('<!-- outline-start -->')
    outline_end = content.find('<!-- outline-end -->')
    
    if outline_start == -1 or outline_end == -1:
        return ["Missing outline markers"]
    
    outline_section = content[outline_start:outline_end]
    
    # Find all anchor points (🔹 markers)
    anchors = re.findall(r'🔹\s*([^#]+)', outline_section)
    issues = []
    
    # Check if each anchor has corresponding content
    for anchor in anchors:
        # Simple check - look for content after this anchor
        anchor_pattern = r'🔹\s*' + re.escape(anchor)
        anchor_pos = outline_section.find(anchor_pattern)
        
        if anchor_pos != -1:
            # Look for content after this anchor (next anchor or end of outline)
            next_content = outline_section[anchor_pos + len(anchor_pattern):anchor_pos + 200]
            if len(next_content.strip()) < 10:  # Very minimal content check
                issues.append(f"Anchor '{anchor}' appears to have minimal content")
    
    return issues

def perform_idle_audit(file_path):
    """Perform idle audit on a chapter"""
    print(f"Auditing: {file_path}")
    
    # Read the file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return {"error": f"Failed to read file: {e}"}
    
    # Parse frontmatter
    frontmatter = extract_frontmatter(content)
    frontmatter_issues = check_frontmatter_completeness(frontmatter)
    
    # Check outline anchors
    outline_issues = check_outline_anchors(content)
    
    # L1 forbidden words scan (simplified check)
    forbidden_patterns = [
        r'总之', r'综上所述', r'由此可见', r'总的来说', r'总体而言',
        r'事实上', r'实际上', r'理论上', r'一般来说', r'值得一提的是',
        r'值得注意的是', r'简单来说', r'简单而言'
    ]
    
    forbidden_found = []
    for pattern in forbidden_patterns:
        matches = re.findall(pattern, content)
        if matches:
            forbidden_found.extend(matches)
    
    # High frequency words check
    high_freq_words = {
        '其实': content.count('其实'),
        '真正': content.count('真正'),
        '彻底': content.count('彻底')
    }
    
    results = {
        'file': str(file_path),
        'frontmatter_issues': frontmatter_issues,
        'outline_issues': outline_issues,
        'forbidden_words_found': forbidden_found,
        'high_frequency_words': {k: v for k, v in high_freq_words.items() if v > 0},
        'overall_status': 'PASS' if not (frontmatter_issues or outline_issues or forbidden_found) else 'ISSUES_FOUND'
    }
    
    return results

if __name__ == "__main__":
    # Path to the target chapter
    file_path = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki/src/ch15-methodology.md")
    
    if file_path.exists():
        results = perform_idle_audit(file_path)
        print("\n=== AUDIT RESULTS ===")
        print(f"File: {results['file']}")
        print(f"Overall Status: {results['overall_status']}")
        
        if results['frontmatter_issues']:
            print("\nFrontmatter Issues:")
            for issue in results['frontmatter_issues']:
                print(f"  - {issue}")
        
        if results['outline_issues']:
            print("\nOutline Issues:")
            for issue in results['outline_issues']:
                print(f"  - {issue}")
        
        if results['forbidden_words_found']:
            print("\nForbidden Words Found:")
            for word in results['forbidden_words_found']:
                print(f"  - {word}")
        
        if results['high_frequency_words']:
            print("\nHigh Frequency Words:")
            for word, count in results['high_frequency_words'].items():
                print(f"  - {word}: {count}")
    else:
        print(f"File not found: {file_path}")