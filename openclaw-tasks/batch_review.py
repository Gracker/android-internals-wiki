import os
import re
import subprocess
import time
from datetime import datetime

TODO_FILE = "logs/external-review/TODO-part3-tools.md"
REVIEW_DIR = "logs/external-review"

def get_next_task():
    if not os.path.exists(TODO_FILE):
        return None, []
    
    with open(TODO_FILE, 'r') as f:
        lines = f.readlines()
        
    for i, line in enumerate(lines):
        if line.startswith("- [ ] "):
            filepath = line[6:].strip()
            return filepath, i, lines
    return None, None, lines

def mark_task_done(index, lines):
    lines[index] = lines[index].replace("- [ ] ", "- [x] ", 1)
    with open(TODO_FILE, 'w') as f:
        f.writelines(lines)

def get_chapter_number(filepath):
    m = re.search(r'ch(\d+)[^/]*/(\d+)-.*\.md', filepath)
    if m:
        return f"{int(m.group(1))}.{int(m.group(2))}"
    m2 = re.search(r'ch(\d+)[^/]*/README\.md', filepath)
    if m2:
        return f"{int(m2.group(1))}.0"
    return os.path.splitext(os.path.basename(filepath))[0]

def run_review(filepath):
    chapter_str = get_chapter_number(filepath)
    timestamp = datetime.now().strftime("%Y-%m-%d-%H")
    
    # We will try to make the prompt enforce writing to the file
    out_file = os.path.join(REVIEW_DIR, f"{timestamp}-{chapter_str}-external-review.md")
    
    prompt = f"""
按照 @aiw-gemini-review-pack.md 规范，对 {filepath} 进行单篇深度技术 review。
必须把 review 结果落盘写入 {out_file}，这是强制要求。
你的回答只用告诉我落盘成功与否即可，所有核心报告内容都应直接写入文件！
不要停留在表面，要优先使用联网搜索、cs.android.com 寻找源码依据。
"""
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting review for {filepath}...")
    
    # Call gemini cli with non-interactive flag -p
    try:
        result = subprocess.run(["gemini", "-m", "gemini-3.1-flash-lite-preview", "-y", "-p", prompt], capture_output=True, text=True, check=True)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Review completed for {filepath}.")
        print(f"Output excerpt: {result.stdout[:200]}...")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Review failed for {filepath}: {e.stderr}")
        return False

def main():
    os.makedirs(REVIEW_DIR, exist_ok=True)
    
    while True:
        filepath, index, lines = get_next_task()
        if not filepath:
            print("All tasks completed or no tasks found!")
            break
            
        success = run_review(filepath)
        if success:
            mark_task_done(index, lines)
            print(f"Marked {filepath} as done in TODO list.")
            time.sleep(10) # Prevent rate limits
        else:
            print(f"Failed to process {filepath}. Pausing for 60 seconds before retry...")
            time.sleep(60)

if __name__ == "__main__":
    main()
