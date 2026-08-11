import os
import sys
import subprocess
import time

files = [
    "src/part5-app/ch20-stability/01-stability-overview.md",
    "src/part5-app/ch20-stability/02-java-crash-governance.md",
    "src/part5-app/ch20-stability/03-native-crash-governance.md",
    "src/part5-app/ch20-stability/04-anr-governance.md",
    "src/part5-app/ch20-stability/05-oom-governance.md",
    "src/part5-app/ch20-stability/06-stability-metrics.md",
    "src/part5-app/ch20-stability/07-exception-architecture.md",
    "src/part5-app/ch20-stability/08-crash-aggregation.md",
    "src/part5-app/ch20-stability/09-webview-renderer-oom-recovery.md",
    "src/part5-app/ch20-stability/10-mte-gwp-asan-native-memory-safety.md",
    "src/part5-app/ch20-stability/11-16kb-page-size-native-compatibility.md",
    "src/part5-app/ch20-stability/12-fd-resource-monitoring.md",
    "src/part5-app/ch20-stability/13-android17-native-dcl-stability.md",
    "src/part5-app/ch20-stability/14-keystore-quota-login-stability.md",
    "src/part5-app/ch20-stability/15-binder-ipc-fault-monitoring.md",
    "src/part5-app/ch20-stability/16-native-stack-unwinding-symbolication.md",
    "src/part5-app/ch20-stability/17-native-hook-technology-selection-implementation.md",
    "src/part5-app/ch20-stability/18-crash-java-stack-lock-wait-analysis.md",
    "src/part5-app/ch20-stability/19-thread-leak-anonymous-thread-monitoring.md",
    "src/part5-app/ch20-stability/20-native-memory-leak-online-monitoring.md",
    "src/part5-app/ch20-stability/21-coroutine-leak-diagnosis-structured-concurrency-performance.md",
    "src/part5-app/ch20-stability/22-sdk-performance-governance.md",
    "src/part5-app/ch20-stability/README.md"
]

prompt_template = """按照 logs/external-review/aiw-gemini-review-pack.md 规范，review 下面这个文章。不要偷懒，不要代写正文，必须给出完整的 markdown 报告。目标文件：{filepath}

文章内容：
{content}
"""

for filepath in files:
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        continue
    
    with open(filepath, "r") as f:
        content = f.read()
    
    prompt = prompt_template.format(filepath=filepath, content=content)
    
    out_filename = "logs/external-review/20-" + os.path.basename(filepath)
    if os.path.basename(filepath) == "README.md":
        out_filename = "logs/external-review/20.README-ch20.md"
        
    print(f"Reviewing {filepath} -> {out_filename}")
    
    # Run gemini ask
    process = subprocess.run(
        ["gemini", "ask", prompt],
        capture_output=True,
        text=True
    )
    
    if process.returncode == 0:
        with open(out_filename, "w") as f:
            f.write(process.stdout)
        
        # update TODO
        with open("logs/external-review/TODO-part1-2.md", "r") as f:
            todo = f.read()
        
        todo = todo.replace("- [ ] " + filepath, "- [x] " + filepath)
        
        with open("logs/external-review/TODO-part1-2.md", "w") as f:
            f.write(todo)
            
        print("Success")
    else:
        print(f"Failed: {process.stderr}")

print("Batch processing complete.")
