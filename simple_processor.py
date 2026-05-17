#!/usr/bin/env python3
import subprocess
import json
import re
from pathlib import Path
from datetime import datetime

def check_file_indexed(file_path):
    """Check if file is already indexed by calling helper script"""
    try:
        file_name = Path(file_path).stem.lower()
        cmd = [
            'python3', 'scripts/source_index_helper.py', 'search', 
            '--query', file_name
        ]
        
        # Change to the AIW directory
        aiw_dir = Path('/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki')
        
        result = subprocess.run(cmd, cwd=aiw_dir, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            search_result = json.loads(result.stdout)
            return search_result.get('matches', 0) > 0
        else:
            print(f"Search error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error checking index: {e}")
        return False

def score_file_simple(file_path):
    """Simple scoring function without importing complex dependencies"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return {'total': 0, 'error': f"Read error: {e}"}
    
    # Extract title from first line
    first_line = content.split('\n')[0].strip()
    if first_line.startswith('# '):
        title = first_line[2:]
    else:
        title = Path(file_path).stem
    
    title_lower = title.lower()
    content_lower = content.lower()
    
    # Simple scoring based on keywords
    score = 0
    
    # Android/Linux keywords
    android_keywords = ['android', 'linux', 'framework', 'perfetto', 'surfaceflinger', 'choreographer',
                       '内存', '功耗', '渲染', 'anr', '启动', 'binder', 'zygote', 'ams', 'wms', 'surface']
    
    if any(keyword in title_lower or keyword in content_lower for keyword in android_keywords):
        score += 5
    
    # Technical indicators
    technical_words = ['code', 'api', '性能', '内存', 'cpu', 'rendering', 'profiler', 'trace', 'benchmark']
    if any(word in content_lower for word in technical_words):
        score += 3
    
    # Recent content
    if any(year in content_lower for year in ['2024', '2025', '2026']):
        score += 2
    
    return {
        'total': min(score, 20),
        'title': title,
        'content_preview': content[:200].strip()
    }

def append_to_daily_funnel(file_path, score_result):
    """Append Android-related file to daily funnel"""
    try:
        aiw_root = Path('/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki')
        funnel_file = aiw_root / 'intake/daily-info' / f'{datetime.now().strftime("%Y-%m-%d")}.md'
        
        # Create directory if it doesn't exist
        funnel_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_name = Path(file_path).stem
        absolute_path = str(file_path)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # Determine chapter mapping
        title = score_result['title'].lower()
        if any(keyword in title for keyword in ['渲染', 'surfaceflinger', 'vsync', 'choreographer']):
            chapter = 'ch02'
        elif any(keyword in title for keyword in ['内存', 'lmk', 'zram']):
            chapter = 'ch04'
        elif any(keyword in title for keyword in ['cpu', 'eas', '调度']):
            chapter = 'ch05'
        elif any(keyword in title for keyword in ['启动', '响应']):
            chapter = 'ch08'
        elif any(keyword in title for keyword in ['anr', 'watchdog']):
            chapter = 'ch09'
        elif any(keyword in title for keyword in ['perfetto', 'trace']):
            chapter = 'ch13'
        else:
            chapter = 'ch16'
        
        funnel_entry = f"""
## [增量扫描] {file_name}
- **来源**：Task 11 增量扫描
- **时间**：{timestamp}
- **链接**：{absolute_path}
- **摘要**：{score_result['content_preview']}
- **推荐映射章节**：{chapter}
- **内容类型**：素材扫描
- **相关标签**：{{#Android #系统开发}}

"""
        
        # Append to funnel file
        with open(funnel_file, 'a', encoding='utf-8') as f:
            f.write(funnel_entry)
            
        return True
        
    except Exception as e:
        print(f"Error appending to daily funnel: {e}")
        return False

def add_to_index(file_path, score_result):
    """Add file to source index using helper script"""
    try:
        aiw_dir = Path('/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki')
        
        entry = {
            'path': str(file_path),
            'title': score_result['title'],
            'score': score_result['total'],
            'relevance': 5,  # Default since we're checking Android keywords
            'technical_depth': 3,
            'timeliness': 2,
            'verifiability': 2,
            'scored_at': datetime.now().isoformat(),
            'quality': 'high' if score_result['total'] >= 15 else 'medium'
        }
        
        entries_json = json.dumps([entry], ensure_ascii=False)
        cmd = ['python3', 'scripts/source_index_helper.py', 'append', '--entries', entries_json]
        
        result = subprocess.run(cmd, cwd=aiw_dir, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            append_result = json.loads(result.stdout)
            print(f"Successfully added {append_result.get('added', 0)} entries to index")
            return True
        else:
            print(f"Index add error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error adding to index: {e}")
        return False

def main():
    # List of Android-related files from the incremental scan
    android_files = [
        "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Cubox/深入 Android Bitmap 内存模型：从 Java 堆分配到 Hardware Bitmap 的演进与优化-2026-05-16.md",
        "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-16-android-17-deliqueue-recyclerview-scroll-performance.md",
        "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-16-android-art-gc-compose-recomposition.md",
        "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-16-android-generational-cmc-userefaultfd.md",
        "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-16-android-jobscheduler-workmanager-api-version-verification.md",
        "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-16-android-native-crash-applicationexitinfo.md",
        "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-16-android-selinux-isenforced-mechanism.md",
        "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-16-android-view-standard-pipeline-blast-source-verification.md",
        "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-17-android-17-deli-queue-source-analysis.md",
        "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/android-skills-profilers/2026-05-16-android-skills-profilers-深度调研.md"
    ]
    
    print(f"Processing {len(android_files)} Android-related incremental files...")
    
    results = {
        'total_found': len(android_files),
        'processed': 0,
        'added_to_index': 0,
        'added_to_funnel': 0,
        'skipped': 0
    }
    
    for file_path in android_files:
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                print(f"File not found: {file_path}")
                continue
                
            results['processed'] += 1
            
            # Check if already indexed
            if check_file_indexed(file_path):
                results['skipped'] += 1
                continue
            
            # Score the file
            score_result = score_file_simple(file_path)
            total_score = score_result['total']
            
            print(f"\nProcessing: {Path(file_path).stem}")
            print(f"Score: {total_score}/20")
            
            if total_score >= 10:
                # Add to index
                if add_to_index(file_path, score_result):
                    results['added_to_index'] += 1
                    
                    # Check if Android-related and add to daily funnel
                    title = score_result['title'].lower()
                    android_keywords = ['android', 'linux', 'framework', 'perfetto', 'surfaceflinger', 'choreographer',
                                       '内存', '功耗', '渲染', 'anr', '启动', 'binder', 'zygote', 'ams', 'wms', 'surface']
                    
                    if any(keyword in title or keyword in score_result['content_preview'].lower() 
                           for keyword in android_keywords):
                        if append_to_daily_funnel(file_path, score_result):
                            results['added_to_funnel'] += 1
            else:
                results['skipped'] += 1
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    # Print results
    print("\n=== AIW 增量扫描结果 ===")
    print(f"发现文件：{results['total_found']} 个")
    print(f"处理完成：{results['processed']} 个")
    print(f"新增索引：{results['added_to_index']} 个")
    print(f"追加漏斗：{results['added_to_funnel']} 个")
    print(f"跳过：{results['skipped']} 个")

if __name__ == "__main__":
    main()