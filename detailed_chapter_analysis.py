#!/usr/bin/env python3
import re
import yaml
from pathlib import Path

def find_forbidden_words(content):
    """Find forbidden words from the writing guide."""
    forbidden_words = [
        '赋能', '闭环', '底座', '抓手', '下钻', '落地', '对齐', '沉淀', '打通', '串联', 
        '心智', '颗粒度', '组合拳', '护城河', '矩阵', '生态位', '赛道', '痛点', '蓝海', '红海',
        '赛道', '赋能', '降本增效', '价值主张', '用户心智', '心智模型'
    ]
    
    issues = []
    for word in forbidden_words:
        count = content.count(word)
        if count > 0:
            issues.append(f"Forbidden word '{word}' appears {count} times")
    return issues

def find_reporting_phrases(content):
    """Find reporting-style phrases."""
    reporting_phrases = [
        "先说判断", "先给结论", "综上所述", "总而言之", "一言以蔽之",
        "直奔主题", "值得重点关注", "值得深思", "不难看出", "显然",
        "众所周知", "不言而喻", "以上可以看出", "由此可见"
    ]
    
    issues = []
    for phrase in reporting_phrases:
        count = content.count(phrase)
        if count > 0:
            issues.append(f"Reporting phrase '{phrase}' appears {count} times")
    return issues

def find_translation_verbs(content):
    """Find translation-style verbs."""
    action_verbs = ['接住', '击穿', '拆解', '收口', '不崩', '不爆', '打穿', '打透', '收紧', '推开', '扛住', '立住', '站稳', '锋利']
    issues = []
    
    for verb in action_verbs:
        count = content.count(verb)
        if count > 0:
            issues.append(f"Translation verb '{verb}' appears {count} times")
    return issues

def find_adj_colon_patterns(content):
    """Find adjective + colon patterns (AI-like)."""
    # Look for Chinese characters followed by 很/更/特别 and colon
    pattern = r'[\u4e00-\u9fff]+\s*(很|更|特别)\s*[:：]'
    matches = re.findall(pattern, content)
    return [f"Adjective+colon pattern found: {match}" for match in matches]

def find_abstract_noun_patterns(content):
    """Find abstract noun + adjective patterns (AI-like)."""
    # Look for patterns like "X的Y比Z更W"
    pattern = r'[\u4e00-\u9fff]+的[\u4e00-\u9fff]+[\u4e00-\u9fff]*[\u4e00-\u9fff]*比[^，。]*[^，。]{10,}[更]{1,2}[\u4e00-\u9fff]{2,}'
    matches = re.findall(pattern, content)
    return [f"Abstract noun pattern found: {match}" for match in matches]

def fix_chinese_english_spacing(content):
    """Fix Chinese-English spacing issues."""
    # Fix Chinese followed by English without space
    fixed = re.sub(r'([\u4e00-\u9fff])([a-zA-Z])', r'\1 \2', content)
    # Fix English followed by Chinese without space  
    fixed = re.sub(r'([a-zA-Z])([\u4e00-\u9fff])', r'\1 \2', fixed)
    return fixed

def find_hard_line_breaks(content):
    """Find hard line breaks in the middle of sentences."""
    lines = content.split('\n')
    issues = []
    
    for i, line in enumerate(lines):
        if (len(line.strip()) > 0 and len(line.strip()) < 50 and 
            i < len(lines) - 1 and 
            not line.strip().endswith(('。', '！', '？', '.', '!', '?')) and
            not line.strip().startswith('#') and
            not line.strip().startswith('-') and
            not line.strip().startswith('*') and
            not line.strip().startswith('```')):
            # This might be a hard break in the middle of a sentence
            issues.append({
                'line': i+1,
                'type': 'Hard line break in sentence',
                'content': line.strip()
            })
    
    return issues

def analyze_chapter(file_path):
    """Analyze a chapter for quality issues."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None
    
    # Extract frontmatter
    frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*$'
    frontmatter_match = re.search(frontmatter_pattern, content, re.MULTILINE | re.DOTALL)
    
    if frontmatter_match:
        try:
            frontmatter_text = frontmatter_match.group(1)
            frontmatter = yaml.safe_load(frontmatter_text)
        except:
            frontmatter = {}
    else:
        frontmatter = {}
    
    # Perform various checks
    issues = {
        'L1_forbidden_words': find_forbidden_words(content),
        'L1_reporting_phrases': find_reporting_phrases(content),
        'L1_translation_verbs': find_translation_verbs(content),
        'L4_adj_colon': find_adj_colon_patterns(content),
        'L4_abstract_noun': find_abstract_noun_patterns(content),
        'L2_hard_breaks': find_hard_line_breaks(content),
        'direct_fixes': {
            'chinese_english_spacing': fix_chinese_english_spacing(content),
            'hard_breaks_fixed': []  # Will be populated if we fix
        }
    }
    
    # Summary
    total_issues = (len(issues['L1_forbidden_words']) + 
                   len(issues['L1_reporting_phrases']) + 
                   len(issues['L1_translation_verbs']) +
                   len(issues['L4_adj_colon']) + 
                   len(issues['L4_abstract_noun']) +
                   len(issues['L2_hard_breaks']))
    
    has_major_L1 = len(issues['L1_forbidden_words']) > 0 or len(issues['L1_reporting_phrases']) > 0
    
    return {
        'file_path': file_path,
        'frontmatter': frontmatter,
        'issues': issues,
        'total_issues': total_issues,
        'has_major_L1': has_major_L1,
        'should_auto_promote': should_auto_promote(frontmatter, total_issues, has_major_L1)
    }

def should_auto_promote(frontmatter, total_issues, has_major_L1):
    """Check if chapter should be auto-promoted to finalized."""
    # Check if task6_result is pass-light-edit
    task6_pass = frontmatter.get('task6_result') == 'pass-light-edit'
    
    # Check if task9_result is pass-tech-review  
    task9_pass = frontmatter.get('task9_result') == 'pass-tech-review'
    
    # Check if there are major issues that prevent promotion
    has_minor_issues = total_issues > 0 and not has_major_L1
    
    # Auto-promote only if all conditions are met
    return task6_pass and task9_pass and not has_minor_issues

def main():
    chapters = [
        'src/part3-tools/ch19-apm/18-network-apm-internals.md',
        'src/part3-tools/ch19-apm/21-hybrid-apm.md',
        'src/part2-performance/ch08-responsiveness/08-media-pipeline.md'
    ]
    
    print("=== Detailed Chapter Analysis ===\n")
    
    results = []
    for chapter in chapters:
        full_path = f"/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki/{chapter}"
        result = analyze_chapter(full_path)
        
        if result:
            results.append(result)
            
            print(f"📁 {chapter}")
            print(f"   Frontmatter: {result['frontmatter'].get('title', 'No title')}")
            print(f"   Total issues: {result['total_issues']}")
            print(f"   Major L1 issues: {'YES' if result['has_major_L1'] else 'NO'}")
            print(f"   Auto-promote eligible: {'YES' if result['should_auto_promote'] else 'NO'}")
            
            # Show specific issues
            if result['issues']['L1_forbidden_words']:
                print(f"   L1 Forbidden words: {len(result['issues']['L1_forbidden_words'])}")
            if result['issues']['L1_reporting_phrases']:
                print(f"   L1 Reporting phrases: {len(result['issues']['L1_reporting_phrases'])}")
            if result['issues']['L1_translation_verbs']:
                print(f"   L1 Translation verbs: {len(result['issues']['L1_translation_verbs'])}")
            if result['issues']['L2_hard_breaks']:
                print(f"   L2 Hard breaks: {len(result['issues']['L2_hard_breaks'])}")
            if result['issues']['L4_adj_colon']:
                print(f"   L4 Adj+colon: {len(result['issues']['L4_adj_colon'])}")
            if result['issues']['L4_abstract_noun']:
                print(f"   L4 Abstract noun: {len(result['issues']['L4_abstract_noun'])}")
            
            print("-" * 50)
    
    # Generate final output
    print("\n📋 FINAL REVIEW SUMMARY")
    print("=" * 50)
    
    # List chapters being reviewed
    print("📋 本轮审查：")
    for i, result in enumerate(results, 1):
        print(f"   {i}. {result['file_path']}")
    
    # Check for auto-promotion
    auto_promote = [r for r in results if r['should_auto_promote']]
    if auto_promote:
        print("\n✅ 自动晋升：")
        for r in auto_promote:
            frontmatter = r['frontmatter']
            title = frontmatter.get('title', 'Unknown')
            section = frontmatter.get('section', 'Unknown')
            print(f"   {title} (section {section})")
    else:
        print("\n✅ 自动晋升：无")
    
    print("\n📊 DETAILED ISSUES:")
    for result in results:
        print(f"\n📁 {result['file_path']}")
        if result['issues']['L1_forbidden_words']:
            print("   L1 禁用词：")
            for issue in result['issues']['L1_forbidden_words']:
                print(f"      - {issue}")
        
        if result['issues']['L1_reporting_phrases']:
            print("   L1 汇报腔：")
            for issue in result['issues']['L1_reporting_phrases']:
                print(f"      - {issue}")
        
        if result['issues']['L1_translation_verbs']:
            print("   L1 翻译腔动词：")
            for issue in result['issues']['L1_translation_verbs']:
                print(f"      - {issue}")
        
        if result['issues']['L2_hard_breaks']:
            print("   L2 硬换行：")
            for issue in result['issues']['L2_hard_breaks'][:3]:  # Show first 3
                print(f"      Line {issue['line']}: {issue['content'][:50]}...")
        
        if result['issues']['L4_adj_colon']:
            print("   L4 形容词+冒号：")
            for issue in result['issues']['L4_adj_colon']:
                print(f"      - {issue}")
        
        if result['issues']['L4_abstract_noun']:
            print("   L4 抽象名词+形容词：")
            for issue in result['issues']['L4_abstract_noun']:
                print(f"      - {issue}")
    
    return results

if __name__ == "__main__":
    main()
