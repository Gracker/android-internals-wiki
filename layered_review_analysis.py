#!/usr/bin/env python3
import re
import yaml
from pathlib import Path

class LayeredReview:
    def __init__(self, file_path):
        self.file_path = file_path
        self.content = self.read_file()
        self.frontmatter = self.extract_frontmatter()
        self.review_results = {
            'L1_issues': [],
            'L2_issues': [],
            'L3_issues': [],
            'L4_issues': [],
            'direct_fixes': []
        }
        
    def read_file(self):
        """Read the file content."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {self.file_path}: {e}")
            return ""
    
    def extract_frontmatter(self):
        """Extract YAML frontmatter from markdown content."""
        try:
            # Match YAML frontmatter between --- markers
            pattern = r'^---\s*\n(.*?)\n---\s*$'
            match = re.search(pattern, self.content, re.MULTILINE | re.DOTALL)
            
            if match:
                frontmatter_text = match.group(1)
                try:
                    return yaml.safe_load(frontmatter_text)
                except yaml.YAMLError as e:
                    print(f"Error parsing YAML in {self.file_path}: {e}")
                    return {}
            return {}
        except Exception as e:
            print(f"Error extracting frontmatter from {self.file_path}: {e}")
            return {}
    
    def L1_hard_rules_check(self):
        """L1: Hard rules (zero tolerance)."""
        issues = []
        
        # Check for forbidden words
        forbidden_words = [
            '赋能', '闭环', '底座', '抓手', '下钻', '落地', '对齐', '沉淀', '打通', '串联', 
            '心智', '颗粒度', '组合拳', '护城河', '矩阵', '生态位', '赛道', '痛点', '蓝海', '红海',
            '赛道', '赋能', '降本增效', '价值主张', '用户心智', '心智模型'
        ]
        
        for word in forbidden_words:
            count = self.content.count(word)
            if count > 0:
                issues.append(f"Forbidden word '{word}' appears {count} times")
        
        # Check for汇报腔 phrases
        reporting_phrases = [
            "先说判断", "先给结论", "综上所述", "总而言之", "一言以蔽之",
            "直奔主题", "值得重点关注", "值得深思", "不难看出", "显然",
            "众所周知", "不言而喻", "以上可以看出", "由此可见"
        ]
        
        for phrase in reporting_phrases:
            count = self.content.count(phrase)
            if count > 0:
                issues.append(f"Reporting phrase '{phrase}' appears {count} times")
        
        # Check for network slang
        slang_words = ['YYDS', '绝绝子', '破防', '拿捏', '上分', '躺平', '内卷']
        for word in slang_words:
            count = self.content.count(word)
            if count > 0:
                issues.append(f"Network slang '{word}' appears {count} times")
        
        # Check for high-frequency filler words
        high_freq_words = ['真正', '本质上', '恰恰', '其实', '显然', '众所周知', '不言而喻',
                          '说实话', '事实上', '实际上', '关键是', '重要的是',
                          '值得注意', '不得不说', '需要指出']
        
        for word in high_freq_words:
            count = self.content.count(word)
            if count >= 5:
                issues.append(f"High-frequency word '{word}' appears {count} times (threshold: 5)")
        
        # Check for structural meta-narrative
        meta_patterns = [
            r"本节只讲.*?放到下一节",
            r"这一节先把.*?摆出来.*?下一节再展开细节",
            r"S\d+X采用.*?结构",
            r"下面先讲.*?再讲.*?最后讲.*?",
            r"只想先看结论.*?看完这一节就够.*?要追.*?再看下一节"
        ]
        
        for pattern in meta_patterns:
            matches = re.findall(pattern, self.content)
            if matches:
                issues.append(f"Structural meta-narrative found: {len(matches)} instances")
        
        return issues
    
    def L2_readability_check(self):
        """L2: Readability and structure."""
        issues = []
        
        # Check opening (first 3 sentences should enter topic)
        sentences = re.split(r'[。！？]', self.content[:1000])
        if len(sentences) >= 3:
            first_three = sentences[:3]
            # Simple check: if they are too generic or not technical
            generic_openings = ['在当今社会', '在现在这个时代', '在当前环境下', '随着技术的不断发展']
            opening_generic = any(phrase in first_three[0] for phrase in generic_openings)
            
            if opening_generic:
                issues.append("Opening seems too generic; should directly enter topic")
        
        # Check paragraph length (should not be too long)
        content_section = self.content.split('<!-- outline-end -->', 1)[1] if '<!-- outline-end -->' in self.content else self.content
        paragraphs = content_section.split('\n\n')
        for i, para in enumerate(paragraphs):
            if len(para.split('\n')) > 8:  # More than 8 lines per paragraph
                issues.append(f"Paragraph {i+1} is too long (>{len(para.split('\n'))} lines)")
        
        # Check for structural issues
        outline_section = re.search(r'<!-- outline-start -->(.*?)<!-- outline-end -->', self.content, re.DOTALL)
        if outline_section:
            outline_content = outline_section.group(1)
            # Check if all anchor points have content
            anchor_pattern = r'🔹 \[(.*?)\]'
            anchors = re.findall(anchor_pattern, outline_content)
            content_has_anchor = {}
            
            for anchor in anchors:
                # Check if anchor appears in content
                if anchor in self.content.split('<!-- outline-end -->')[0]:
                    content_has_anchor[anchor] = True
                else:
                    content_has_anchor[anchor] = False
            
            missing_anchors = [anchor for anchor, has_content in content_has_anchor.items() if not has_content]
            if missing_anchors:
                issues.append(f"Missing content for anchors: {', '.join(missing_anchors)}")
        
        return issues
    
    def L3_content_depth_check(self):
        """L3: Content depth and technical accuracy."""
        issues = []
        
        # Check for technical accuracy placeholders
        vague_phrases = ['[待验证]', '[待补充]', 'TODO', 'TBD', '此处填写内容']
        vague_count = 0
        for phrase in vague_phrases:
            count = self.content.count(phrase)
            vague_count += count
        
        if vague_count > 0:
            issues.append(f"Found {vague_count} vague/unverified placeholders")
        
        # Check if technical claims are supported
        # This is a simplified check - in real implementation would need more sophisticated analysis
        technical_claims = re.findall(r'[，。]([^，。]{20,}[^，。]*[^，。技术验证支持事实]{20,})', self.content)
        
        # Check for code example quality
        code_blocks = re.findall(r'```[a-zA-Z]*\n(.*?)```', self.content, re.DOTALL)
        for i, code in enumerate(code_blocks):
            if len(code.strip()) < 50:  # Code block too small
                issues.append(f"Code block {i+1} appears too small/placeholder-like")
        
        return issues
    
    def L4_liveness_check(self):
        """L4: Liveness and authentic writing style."""
        issues = []
        
        # Check for AI-like patterns (translation symptoms)
        # Pattern 1: Adjective + colon
        adj_colon = re.findall(r'[\u4e00-\u9fff]+\s*[很更加特别]\s*[:：]', self.content)
        if adj_colon:
            issues.append(f"Found {len(adj_colon)} 'adjective + colon' patterns (AI-like)")
        
        # Pattern 2: Abstract noun + adjective conclusion
        abstract_pattern = re.findall(r'[\u4e00-\u9fff]+的[\u4e00-\u9fff]+[\u4e00-\u9fff]*[\u4e00-\u9fff]*比[^，。]*[^，。]{10,}[更]{1,2}[\u4e00-\u9fff]{2,}', self.content)
        if abstract_pattern:
            issues.append(f"Found {len(abstract_pattern)} abstract noun + adjective patterns (AI-like)")
        
        # Check for verb patterns (physical action verbs)
        action_verbs = ['接住', '击穿', '拆解', '收口', '不崩', '不爆', '打穿', '打透', '收紧', '推开', '扛住', '立住', '站稳', '锋利']
        for verb in action_verbs:
            count = self.content.count(verb)
            if count > 0:
                issues.append(f"Found action verb '{verb}' (translation symptom)")
        
        return issues
    
    def identify_direct_fixes(self):
        """Identify issues that can be directly fixed (light edits)."""
        fixes = []
        
        # Fix Chinese-English spacing
        # Find English words/identifiers and add spaces around them
        # This is a simplified fix - in real implementation would need more sophisticated pattern matching
        content_lines = self.content.split('\n')
        for i, line in enumerate(content_lines):
            # Simple pattern: Chinese characters next to English words
            fixed_line = re.sub(r'([a-zA-Z])([\u4e00-\u9fff])', r' \2', line)  # EN -> CN
            fixed_line = re.sub(r'([\u4e00-\u9fff])([a-zA-Z])', r' \1 ', fixed_line)  # CN -> EN
            
            if fixed_line != line:
                fixes.append({
                    'line': i+1,
                    'type': 'Chinese-English spacing',
                    'before': line,
                    'after': fixed_line
                })
        
        # Fix hard line breaks in the middle of sentences
        for i, line in enumerate(content_lines):
            if (len(line) > 0 and len(line) < 50 and 
                i < len(content_lines) - 1 and 
                not line.strip().endswith(('。', '！', '？', '.', '!', '?'))):
                # This might be a hard break in the middle of a sentence
                fixes.append({
                    'line': i+1,
                    'type': 'Hard line break in sentence',
                    'before': line,
                    'after': line + ' '  # Simple fix
                })
        
        return fixes
    
    def perform_review(self):
        """Perform complete layered review."""
        print(f"🔍 Performing layered review for: {self.file_path}")
        
        # L1: Hard rules
        self.review_results['L1_issues'] = self.L1_hard_rules_check()
        print(f"L1: Found {len(self.review_results['L1_issues'])} hard rule violations")
        
        # L2: Readability
        self.review_results['L2_issues'] = self.L2_readability_check()
        print(f"L2: Found {len(self.review_results['L2_issues'])} readability issues")
        
        # L3: Content depth
        self.review_results['L3_issues'] = self.L3_content_depth_check()
        print(f"L3: Found {len(self.review_results['L3_issues'])} content depth issues")
        
        # L4: Liveness
        self.review_results['L4_issues'] = self.L4_liveness_check()
        print(f"L4: Found {len(self.review_results['L4_issues'])} liveness issues")
        
        # Direct fixes
        self.review_results['direct_fixes'] = self.identify_direct_fixes()
        print(f"Direct fixes: Found {len(self.review_results['direct_fixes'])} fixable issues")
        
        return self.review_results
    
    def generate_summary(self):
        """Generate a summary of the review."""
        total_issues = (len(self.review_results['L1_issues']) + 
                       len(self.review_results['L2_issues']) + 
                       len(self.review_results['L3_issues']) + 
                       len(self.review_results['L4_issues']))
        
        has_major_issues = total_issues > 10 or len(self.review_results['L1_issues']) > 0
        
        return {
            'total_issues': total_issues,
            'has_major_issues': has_major_issues,
            'L1_count': len(self.review_results['L1_issues']),
            'L2_count': len(self.review_results['L2_issues']),
            'L3_count': len(self.review_results['L3_issues']),
            'L4_count': len(self.review_results['L4_issues']),
            'fixes_count': len(self.review_results['direct_fixes'])
        }

def main():
    # Chapters to review
    chapters = [
        'src/part3-tools/ch19-apm/18-network-apm-internals.md',
        'src/part3-tools/ch19-apm/21-hybrid-apm.md',
        'src/part2-performance/ch08-responsiveness/08-media-pipeline.md'
    ]
    
    print("=== Layered Review Analysis ===\n")
    
    review_results = {}
    
    for chapter in chapters:
        full_path = f"/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki/{chapter}"
        reviewer = LayeredReview(full_path)
        result = reviewer.perform_review()
        summary = reviewer.generate_summary()
        
        review_results[chapter] = {
            'review': result,
            'summary': summary
        }
        
        print(f"\n📊 Summary for {chapter}:")
        print(f"   Total issues: {summary['total_issues']}")
        print(f"   Major issues: {'YES' if summary['has_major_issues'] else 'NO'}")
        print(f"   L1: {summary['L1_count']}, L2: {summary['L2_count']}, L3: {summary['L3_count']}, L4: {summary['L4_count']}")
        print(f"   Direct fixes: {summary['fixes_count']}")
        print("-" * 50)
    
    return review_results

if __name__ == "__main__":
    main()
