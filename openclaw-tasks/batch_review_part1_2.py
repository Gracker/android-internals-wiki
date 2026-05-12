import os
import re
import subprocess
import time
from datetime import datetime
import glob

TODO_FILE = "logs/external-review/TODO-part1-2.md"
REVIEW_DIR = "logs/external-review"
LOG_FILE = "logs/external-review/batch_review_log.txt"

def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {msg}"
    print(log_msg)
    with open(LOG_FILE, "a") as f:
        f.write(log_msg + "\n")

def get_chapter_number(filepath):
    m = re.search(r'ch(\d+)[^/]*/(\d+)-.*\.md', filepath)
    if m:
        return f"{int(m.group(1))}.{int(m.group(2))}"
    m2 = re.search(r'ch(\d+)[^/]*/README\.md', filepath)
    if m2:
        return f"{int(m2.group(1))}.0"
    return os.path.splitext(os.path.basename(filepath))[0]

def init_todolist():
    os.makedirs(REVIEW_DIR, exist_ok=True)
    if os.path.exists(TODO_FILE):
        return
    
    files = glob.glob("src/part1-fundamentals/**/*.md", recursive=True) + \
            glob.glob("src/part2-performance/**/*.md", recursive=True)
    
    # Sort files for deterministic order
    files.sort()
    
    with open(TODO_FILE, "w") as f:
        f.write("# 批量 Review Todo List\n\n")
        for file in files:
            f.write(f"- [ ] {file}\n")

def get_next_task():
    if not os.path.exists(TODO_FILE):
        return None, []
    
    with open(TODO_FILE, 'r') as f:
        lines = f.readlines()
        
    for i, line in enumerate(lines):
        if line.startswith("- [ ] "):
            filepath = line.replace("- [ ] ", "").strip()
            return filepath, i, lines
    return None, None, lines

def mark_task_done(index, lines):
    lines[index] = lines[index].replace("- [ ] ", "- [x] ", 1)
    with open(TODO_FILE, 'w') as f:
        f.writelines(lines)

def run_review(filepath):
    chapter_str = get_chapter_number(filepath)
    timestamp = datetime.now().strftime("%Y-%m-%d-%H")
    
    # 按照用户的要求，以章节号命名，类似于 15.x 的形式
    out_file = os.path.join(REVIEW_DIR, f"{timestamp}-{chapter_str}-external-review.md")
    
    prompt = f"""
你正在执行后台批量审查任务。
请严格按照 @aiw-gemini-review-pack.md 规范，对 {filepath} 进行单篇深度技术 review。
必须把 review 结果落盘写入 {out_file}，这是强制要求。章节编号请使用 {chapter_str}。
你的回答只用告诉我落盘成功与否即可，所有核心报告内容都应直接写入文件！
不要停留在表面，要优先使用联网搜索、cs.android.com 寻找源码依据。
"""
    
    log(f"Starting review for {filepath}...")
    
    try:
        # Try up to 3 times to mitigate random errors
        for attempt in range(3):
            result = subprocess.run(["gemini", "-y", "-p", prompt], capture_output=True, text=True)
            if result.returncode == 0:
                log(f"Review completed for {filepath}. Output excerpt: {result.stdout[:100].strip()}")
                return True
            else:
                log(f"Attempt {attempt + 1} failed for {filepath}: {result.stderr[:200].strip()}")
                time.sleep(10)
        return False
    except Exception as e:
        log(f"Error executing gemini: {e}")
        return False

def main():
    init_todolist()
    log("Todo list initialized. Starting batch review...")
    
    while True:
        filepath, index, lines = get_next_task()
        if not filepath:
            log("All tasks completed or no tasks found!")
            break
            
        success = run_review(filepath)
        if success:
            mark_task_done(index, lines)
            log(f"Marked {filepath} as done in TODO list.")
            time.sleep(5)
        else:
            log(f"Failed to process {filepath}. Pausing for 60 seconds before retry...")
            time.sleep(60)

if __name__ == "__main__":
    main()
