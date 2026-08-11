import os
import sys
import subprocess
import time

files = [
    "src/part2-performance/ch18-rendering-pipelines/05-android-view-multi-window.md",
    "src/part2-performance/ch18-rendering-pipelines/06-surfaceview.md",
    "src/part2-performance/ch18-rendering-pipelines/07-textureview.md",
    "src/part2-performance/ch18-rendering-pipelines/08-opengl-es.md",
    "src/part2-performance/ch18-rendering-pipelines/09-vulkan-native.md",
    "src/part2-performance/ch18-rendering-pipelines/10-surface-control-api.md",
    "src/part2-performance/ch18-rendering-pipelines/11-angle-gles-vulkan.md",
    "src/part2-performance/ch18-rendering-pipelines/12-flutter-rendering.md",
    "src/part2-performance/ch18-rendering-pipelines/13-webview-rendering.md",
    "src/part2-performance/ch18-rendering-pipelines/14-camera-pipeline.md",
    "src/part2-performance/ch18-rendering-pipelines/15-video-overlay-hwc.md",
    "src/part2-performance/ch18-rendering-pipelines/16-game-engine.md",
    "src/part2-performance/ch18-rendering-pipelines/17-hardware-buffer-renderer.md",
    "src/part2-performance/ch18-rendering-pipelines/18-variable-refresh-rate.md",
    "src/part2-performance/ch18-rendering-pipelines/19-eyedropper-crossdevice.md",
    "src/part2-performance/ch18-rendering-pipelines/20-android-xr-spatial-ui-rendering.md",
    "src/part2-performance/ch18-rendering-pipelines/21-media-codec2-tunneled-media3-abr.md",
    "src/part2-performance/ch18-rendering-pipelines/22-advanced-professional-video-apv.md",
    "src/part2-performance/ch18-rendering-pipelines/23-compose-rendering-pipeline.md",
    "src/part2-performance/ch18-rendering-pipelines/24-android17-hwui-vulkan-multi-queue.md",
    "src/part2-performance/ch18-rendering-pipelines/25-webgpu-android-pipeline.md",
    "src/part2-performance/ch18-rendering-pipelines/README.md"
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
    
    out_filename = "logs/external-review/15.18-" + os.path.basename(filepath)
    if os.path.basename(filepath) == "README.md":
        out_filename = "logs/external-review/15.README-ch18.md"
        
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
