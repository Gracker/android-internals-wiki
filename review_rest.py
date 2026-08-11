import os
import sys
import subprocess
import time

files = [
    "src/part3-tools/ch19-apm/01-apm-landscape.md",
    "src/part3-tools/ch19-apm/02-tencent-matrix.md",
    "src/part3-tools/ch19-apm/03-koom.md",
    "src/part3-tools/ch19-apm/04-btrace.md",
    "src/part3-tools/ch19-apm/05-leakcanary.md",
    "src/part3-tools/ch19-apm/06-dokit.md",
    "src/part3-tools/ch19-apm/07-measure.md",
    "src/part3-tools/ch19-apm/08-open-source-apm-history.md",
    "src/part3-tools/ch19-apm/09-jankstats-framemetrics.md",
    "src/part3-tools/ch19-apm/10-tracing-sdk.md",
    "src/part3-tools/ch19-apm/11-jetpack-benchmark.md",
    "src/part3-tools/ch19-apm/12-baseline-profiles.md",
    "src/part3-tools/ch19-apm/13-profiling-manager.md",
    "src/part3-tools/ch19-apm/14-firebase-performance.md",
    "src/part3-tools/ch19-apm/15-commercial-apm.md",
    "src/part3-tools/ch19-apm/16-testing-tools.md",
    "src/part3-tools/ch19-apm/17-device-benchmarks.md",
    "src/part3-tools/ch19-apm/18-network-apm-internals.md",
    "src/part3-tools/ch19-apm/19-crash-anr-internals.md",
    "src/part3-tools/ch19-apm/20-battery-thermal-apm.md",
    "src/part3-tools/ch19-apm/21-hybrid-apm.md",
    "src/part3-tools/ch19-apm/22-apm-client-architecture.md",
    "src/part3-tools/ch19-apm/README.md"
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
    
    out_filename = "logs/external-review/19-" + os.path.basename(filepath)
    if os.path.basename(filepath) == "README.md":
        out_filename = "logs/external-review/19.README-ch19.md"
        
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
