#!/usr/bin/env python3
import os
import re
import yaml
from pathlib import Path

def extract_frontmatter(file_path):
    """Extract YAML frontmatter from markdown file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Match frontmatter between --- delimiters
        frontmatter_match = re.search(r'^---\s*\n(.*?)\n---\s*$', content, re.MULTILINE | re.DOTALL)
        if frontmatter_match:
            frontmatter_content = frontmatter_match.group(1)
            try:
                return yaml.safe_load(frontmatter_content)
            except yaml.YAMLError:
                return {}
        return {}
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return {}

def count_outline_anchors(content):
    """Count 🔹 anchors in outline section"""
    # Find outline section
    outline_match = re.search(r'<!-- outline-start -->(.*?)<!-- outline-end -->', content, re.DOTALL)
    if not outline_match:
        return 0, 0
    
    outline_content = outline_match.group(1)
    anchors = re.findall(r'🔹\s*(.+)', outline_content)
    return len(anchors), len(re.findall(r'🔸\s*(.+)', outline_content))

def analyze_writing_guide_compliance(content, file_path):
    """Analyze content against technical writing guide"""
    issues = {
        'forbidden_words': [],
        'ai_filler_words': [],
        'metaphor_issues': [],
        'structure_issues': [],
        'formatting_issues': [],
        'technical_accuracy_issues': []
    }
    
    # Check for forbidden words and phrases
    forbidden_patterns = [
        r'赋能|闭环|底座|抓手|下钻|落地|对齐|沉淀|打通|串联|链路|心智|颗粒度|组合拳|护城河|矩阵|生态位|赛道|痛点|蓝海|红海|方法论输出|形成共识|统一认知|价值闭环|全链路|全局最优|打法',
        r'综上所述|一言以蔽之|直奔主题|值得重点关注|不难看出|显然|众所周知|总而言之|需要注意的是|可以看到|某种程度上|从某种意义上说|核心在于|归根结底|简而言之|总的来说',
        r'YYDS|绝绝子|破防|拿捏|上分|炸裂|封神|降维打击|赢麻了',
        r'说实话|老实说|坦白说|不得不承认|事实上|实际上|关键是|重要的是|有趣的是|值得注意的是|问题是|真正的问题是|这让我想到|这启发了我|不得不说|需要指出的是|不得不提的是',
        r'这一点很重要|这很关键|这至关重要|毋庸置疑|毫无疑问|显而易见|不言而喻|由此可见|这就意味着|值得深思|发人深省',
        r'在当今社会|在现在这个时代|在当前环境下|在当今|随着技术的不断发展|随着 AI 的快速发展|从根本上说|总而言之|综上所述|总的来说|简而言之|归根结底',
        r'接下来我将|下面我们来看|让我们来探讨|我想说的是|我要强调的是|让我们来看看|接下来让我们|首先|其次|最后',
        r'具有深远意义|影响巨大|意义重大|至关重要|不可或缺|举足轻重|意味着什么|这意味着|本质上|换句话说|不可否认',
        r'不是\s+[^,，]+，\s*而是|不只是\s+[^,，]+，\s*还|并非\s+[^,，]+，\s*而是|不仅仅是\s+[^,，]+，\s*更是|与其说是\s+[^,，]+，\s*不如说是'
    ]
    
    for pattern in forbidden_patterns:
        matches = re.findall(pattern, content)
        if matches:
            issues['forbidden_words'].extend(matches)
    
    # Check for AI filler phrases
    ai_filler_patterns = [
        r'其实|更准确地说|更贴近现代 Android 的理解是',
        r'误以为|很多人会以为|读者可能',
        r'你可以把\s+[^，。！？]+，\s+理解成|你可以把\s+[^，。！？]+，\s+先记成',
        r'先别急着|先记住一点|这里有一个关键点要讲清楚'
    ]
    
    for pattern in ai_filler_patterns:
        matches = re.findall(pattern, content)
        if matches:
            issues['ai_filler_words'].extend(matches)
    
    # Check for metaphor issues
    metaphor_patterns = [
        r'立住|扛住|打透|站稳|雪崩|炸裂|魔法般|一招封神|彻底颠覆',
        r'这场仗|立得住|扛住|打透|站稳|核弹级|雪崩式|魔法般|一招封神|彻底颠覆'
    ]
    
    for pattern in metaphor_patterns:
        matches = re.findall(pattern, content)
        if matches:
            issues['metaphor_issues'].extend(matches)
    
    # Check for structure issues
    # Check if content starts with too much background
    first_sentence = re.search(r'^[^。！？]*。[^\n]*', content)
    if first_sentence:
        first_text = first_sentence.group(0)
        # Check if first sentence starts with background phrases
        if re.search(r'在这个时代|随着技术|在现在这个时代|在当前环境', first_text):
            issues['structure_issues'].append(f"首句以背景短语开头：{first_text}")
    
    # Check for formatting issues
    # Check for inconsistent spacing around punctuation
    spacing_issues = re.findall(r'[^\s][，。！？；：][^\s]', content)
    if spacing_issues:
        issues['formatting_issues'].append(f"发现 {len(spacing_issues)} 处标点符号缺少空格")
    
    # Check for technical accuracy issues (basic checks)
    # Look for potential version inconsistencies
    version_matches = re.findall(r'Android\s+\d+', content)
    if len(set(version_matches)) > 1:
        # Check if versions are mentioned inconsistently
        issues['technical_accuracy_issues'].append("发现多个 Android 版本引用，需检查一致性")
    
    return issues

def review_chapter(chapter_path):
    """Review a single chapter"""
    with open(chapter_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    frontmatter = extract_frontmatter(chapter_path)
    required_anchors, optional_anchors = count_outline_anchors(content)
    
    # Analyze compliance
    compliance_issues = analyze_writing_guide_compliance(content, chapter_path)
    
    # Extract table of contents/outline
    outline_match = re.search(r'<!-- outline-start -->(.*?)<!-- outline-end -->', content, re.DOTALL)
    outline_content = outline_match.group(1) if outline_match else "No outline found"
    
    # Count lines of content after outline
    outline_end_match = re.search(r'<!-- outline-end -->', content)
    if outline_end_match:
        after_outline = content[outline_end_match.end():]
        content_lines = len(after_outline.strip().split('\n'))
    else:
        content_lines = len(content.split('\n'))
    
    review_result = {
        'file_path': chapter_path,
        'chapter_title': frontmatter.get('title', 'Unknown'),
        'status': frontmatter.get('status', 'unknown'),
        'required_anchors_found': required_anchors,
        'optional_anchors_found': optional_anchors,
        'content_lines': content_lines,
        'compliance_issues': compliance_issues,
        'has_sufficient_content': content_lines >= 50,
        'outline': outline_content
    }
    
    return review_result

def main():
    # Review the three selected chapters
    chapters = [
        "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki/src/part4-system/ch16-aosp/03-aosp-build.md",
        "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki/src/part1-fundamentals/ch02-rendering/03-vsync.md",
        "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki/src/part1-fundamentals/ch06-storage/04-sharedpreferences-datastore.md"
    ]
    
    reviews = []
    for chapter in chapters:
        review = review_chapter(chapter)
        reviews.append(review)
        print(f"\n=== Review: {review['chapter_title']} ===")
        print(f"Content lines: {review['content_lines']}")
        print(f"Required anchors: {review['required_anchors_found']}")
        print(f"Compliance issues found: {sum(len(v) for v in review['compliance_issues'].values())}")
    
    return reviews

if __name__ == "__main__":
    reviews = main()
