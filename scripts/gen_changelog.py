#!/usr/bin/env python3
"""Generate daily changelogs for Android-Internal-Wiki from git history."""
import subprocess, re
from pathlib import Path

AIW = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki")
CHANGELOG_DIR = AIW / "changelog"
REPO_URL = "https://github.com/gracker/Android-Internal-Wiki"

# chapter -> file mapping (built from actual src/ structure)
CHAPTER_FILES = {
    "1.1": "src/part1-fundamentals/ch01-architecture/01-layered-architecture.md",
    "1.2": "src/part1-fundamentals/ch01-architecture/02-boot-process.md",
    "1.3": "src/part1-fundamentals/ch01-architecture/03-process-model.md",
    "1.4": "src/part1-fundamentals/ch01-architecture/04-binder.md",
    "1.5": "src/part1-fundamentals/ch01-architecture/05-threading-model.md",
    "1.6": "src/part1-fundamentals/ch01-architecture/06-version-evolution.md",
    "2.1": "src/part1-fundamentals/ch02-rendering/01-rendering-overview.md",
    "2.2": "src/part1-fundamentals/ch02-rendering/02-framerate.md",
    "2.3": "src/part1-fundamentals/ch02-rendering/03-vsync.md",
    "2.4": "src/part1-fundamentals/ch02-rendering/04-choreographer.md",
    "2.5": "src/part1-fundamentals/ch02-rendering/05-main-render-thread.md",
    "2.6": "src/part1-fundamentals/ch02-rendering/06-surfaceflinger.md",
    "2.7": "src/part1-fundamentals/ch02-rendering/07-hardware-layer.md",
    "2.8": "src/part1-fundamentals/ch02-rendering/08-overdraw.md",
    "2.9": "src/part1-fundamentals/ch02-rendering/09-rendering-evolution.md",
    "2.10": "src/part1-fundamentals/ch02-rendering/10-gpu-rendering.md",
    "2.11": "src/part1-fundamentals/ch02-rendering/11-flutter-rendering.md",
    "3.1": "src/part1-fundamentals/ch03-input/01-input-dispatch.md",
    "3.2": "src/part1-fundamentals/ch03-input/02-touch-performance.md",
    "3.3": "src/part1-fundamentals/ch03-input/03-gesture-navigation.md",
    "3.4": "src/part1-fundamentals/ch03-input/04-input-interception-security.md",
    "3.5": "src/part1-fundamentals/ch03-input/05-gesture-recognition-performance.md",
    "3.6": "src/part1-fundamentals/ch03-input/06-input-method-manager-performance.md",
    "3.7": "src/part1-fundamentals/ch03-input/07-predictive-back-system-architecture.md",
    "3.8": "src/part1-fundamentals/ch03-input/08-keyboard-mouse-pointer-input-performance.md",
    "4.1": "src/part1-fundamentals/ch04-memory/01-memory-overview.md",
    "4.2": "src/part1-fundamentals/ch04-memory/02-linux-memory.md",
    "4.3": "src/part1-fundamentals/ch04-memory/03-art-memory.md",
    "4.4": "src/part1-fundamentals/ch04-memory/04-lmk.md",
    "4.5": "src/part1-fundamentals/ch04-memory/05-app-memory-optimization.md",
    "4.6": "src/part1-fundamentals/ch04-memory/06-16kb-page-size.md",
    "4.7": "src/part1-fundamentals/ch04-memory/07-art-generational-gc.md",
    "4.8": "src/part1-fundamentals/ch04-memory/08-finalizer-referencequeue.md",
    "4.9": "src/part1-fundamentals/ch04-memory/09-art-heaptask-scheduling-pipeline.md",
    "4.10": "src/part1-fundamentals/ch04-memory/10-memory-compaction-direct-reclaim.md",
    "4.11": "src/part1-fundamentals/ch04-memory/11-cached-app-freezer-gc-boundary.md",
    "4.12": "src/part1-fundamentals/ch04-memory/12-zram-compressed-swap-relaunch.md",
    "4.13": "src/part1-fundamentals/ch04-memory/13-android17-memorylimiter.md",
    "4.14": "src/part1-fundamentals/ch04-memory/14-ontrimmemory-art-heap-trim.md",
    "4.15": "src/part1-fundamentals/ch04-memory/15-android17-memory-tagging-extension-mte.md",
    "4.16": "src/part1-fundamentals/ch04-memory/16-cross-process-memory-ai-inference.md",
    "4.17": "src/part1-fundamentals/ch04-memory/17-product-prefetch-lmkd-boundary.md",
    "5.1": "src/part1-fundamentals/ch05-cpu-power/01-linux-scheduling.md",
    "5.2": "src/part1-fundamentals/ch05-cpu-power/02-eas.md",
    "5.3": "src/part1-fundamentals/ch05-cpu-power/03-big-little.md",
    "5.4": "src/part1-fundamentals/ch05-cpu-power/04-dvfs.md",
    "5.5": "src/part1-fundamentals/ch05-cpu-power/05-thermal.md",
    "5.6": "src/part1-fundamentals/ch05-cpu-power/06-android-power.md",
    "5.7": "src/part1-fundamentals/ch05-cpu-power/07-background-execution.md",
    "5.8": "src/part1-fundamentals/ch05-cpu-power/08-jobscheduler-workmanager-performance.md",
    "5.9": "src/part1-fundamentals/ch05-cpu-power/09-adpf.md",
    "5.10": "src/part1-fundamentals/ch05-cpu-power/10-ondevice-ml-inference-performance.md",
    "5.11": "src/part1-fundamentals/ch05-cpu-power/11-mobile-llm-dvfs-energy.md",
    "5.12": "src/part1-fundamentals/ch05-cpu-power/12-android17-ml-runtime-npu-boundary.md",
    "5.13": "src/part1-fundamentals/ch05-cpu-power/13-sensorservice-batching-power.md",
    "5.14": "src/part1-fundamentals/ch05-cpu-power/14-cpu-cache-friendly-code-data-layout.md",
    "5.15": "src/part1-fundamentals/ch05-cpu-power/15-genai-app-integration-performance.md",
    "5.16": "src/part1-fundamentals/ch05-cpu-power/16-bluetooth-le-audio-performance.md",
    "5.17": "src/part1-fundamentals/ch05-cpu-power/17-android17-app-hibernation-performance.md",
    "6.1": "src/part1-fundamentals/ch06-storage/01-storage-architecture.md",
    "6.2": "src/part1-fundamentals/ch06-storage/02-filesystem.md",
    "6.3": "src/part1-fundamentals/ch06-storage/03-io-scheduling.md",
    "6.4": "src/part1-fundamentals/ch06-storage/04-sharedpreferences-datastore.md",
    "6.5": "src/part1-fundamentals/ch06-storage/05-vold-mediaprovider-fuse.md",
    "7.1": "src/part2-performance/ch07-smoothness/01-jank-definition.md",
    "7.2": "src/part2-performance/ch07-smoothness/02-jank-causes.md",
    "7.3": "src/part2-performance/ch07-smoothness/03-jank-methodology.md",
    "7.4": "src/part2-performance/ch07-smoothness/04-typical-scenarios.md",
    "7.5": "src/part2-performance/ch07-smoothness/05-optimization.md",
    "7.6": "src/part2-performance/ch07-smoothness/06-case-studies.md",
    "7.7": "src/part2-performance/ch07-smoothness/07-compose-performance.md",
    "8.1": "src/part2-performance/ch08-responsiveness/01-responsiveness-principles.md",
    "8.2": "src/part2-performance/ch08-responsiveness/02-app-launch.md",
    "8.3": "src/part2-performance/ch08-responsiveness/03-launch-optimization.md",
    "8.4": "src/part2-performance/ch08-responsiveness/04-other-scenarios.md",
    "8.5": "src/part2-performance/ch08-responsiveness/05-case-studies.md",
    "8.6": "src/part2-performance/ch08-responsiveness/06-coroutine-performance.md",
    "9.1": "src/part2-performance/ch09-anr/01-anr-design.md",
    "9.2": "src/part2-performance/ch09-anr/02-anr-types.md",
    "9.3": "src/part2-performance/ch09-anr/03-anr-analysis.md",
    "9.4": "src/part2-performance/ch09-anr/04-special-anr.md",
    "9.5": "src/part2-performance/ch09-anr/05-case-studies.md",
    "10.1": "src/part2-performance/ch10-memory-perf/01-app-memory-analysis.md",
    "10.2": "src/part2-performance/ch10-memory-perf/02-memory-leak.md",
    "10.3": "src/part2-performance/ch10-memory-perf/03-memory-growth.md",
    "10.4": "src/part2-performance/ch10-memory-perf/04-low-memory-impact.md",
    "10.5": "src/part2-performance/ch10-memory-perf/05-case-studies.md",
    "10.6": "src/part2-performance/ch10-memory-perf/06-memory-churn.md",
    "11.1": "src/part2-performance/ch11-power/01-power-model.md",
    "11.2": "src/part2-performance/ch11-power/02-app-power-optimization.md",
    "11.3": "src/part2-performance/ch11-power/03-system-power-optimization.md",
    "11.4": "src/part2-performance/ch11-power/04-case-studies.md",
    "12.1": "src/part2-performance/ch12-apk-network/01-apk-size.md",
    "12.2": "src/part2-performance/ch12-apk-network/02-network-performance.md",
    "13.1": "src/part3-tools/ch13-perfetto/01-perfetto-intro.md",
    "13.2": "src/part3-tools/ch13-perfetto/02-trace-capture.md",
    "13.3": "src/part3-tools/ch13-perfetto/03-perfetto-view.md",
    "13.4": "src/part3-tools/ch13-perfetto/04-large-traces.md",
    "13.5": "src/part3-tools/ch13-perfetto/05-thread-cpu-states.md",
    "13.6": "src/part3-tools/ch13-perfetto/06-advanced-usage.md",
    "13.7": "src/part3-tools/ch13-perfetto/07-input-latency-sql.md",
    "14.1": "src/part3-tools/ch14-other-tools/01-as-profiler.md",
    "14.2": "src/part3-tools/ch14-other-tools/02-simpleperf.md",
    "14.3": "src/part3-tools/ch14-other-tools/03-android17-simpleperf-microarch-profiling.md",
    "14.4": "src/part3-tools/ch14-other-tools/04-arm-topdown-microarch-performance-analysis.md",
    "14.5": "src/part3-tools/ch14-other-tools/05-memory-tools.md",
    "14.6": "src/part3-tools/ch14-other-tools/06-hprof-heapdump-javahprof-datasource.md",
    "14.7": "src/part3-tools/ch14-other-tools/07-dumpsys.md",
    "14.8": "src/part3-tools/ch14-other-tools/08-battery-historian.md",
    "14.9": "src/part3-tools/ch14-other-tools/09-automation-tools.md",
    "14.10": "src/part3-tools/ch14-other-tools/10-third-party-libs-observability.md",
    "14.11": "src/part3-tools/ch14-other-tools/11-profiling-manager.md",
    "14.12": "src/part3-tools/ch14-other-tools/12-statsd-system-metrics.md",
    "14.13": "src/part3-tools/ch14-other-tools/13-strictmode-performance-diagnostics.md",
    "14.14": "src/part3-tools/ch14-other-tools/14-android-cli-agent-performance-workflow.md",
    "14.15": "src/part3-tools/ch14-other-tools/15-gpu-debug-tools.md",
    "14.16": "src/part3-tools/ch14-other-tools/16-gpu-performance-profiling-advanced.md",
    "14.17": "src/part3-tools/ch14-other-tools/17-android-performance-analyzer.md",
    "14.18": "src/part3-tools/ch14-other-tools/18-android17-agi-frame-profiler-gapii-spy.md",
    "14.19": "src/part3-tools/ch14-other-tools/19-android17-gpuservice-gpu-memory-observability.md",
    "14.20": "src/part3-tools/ch14-other-tools/20-camera-performance-analysis.md",
    "14.21": "src/part3-tools/ch14-other-tools/21-winscope-window-composition-debugging.md",
    "14.22": "src/part3-tools/ch14-other-tools/22-layout-inspector-viewdebug.md",
    "14.23": "src/part3-tools/ch14-other-tools/23-ebpf-performance-analysis.md",
    "14.24": "src/part3-tools/ch14-other-tools/24-ebpf-bpfloader-architecture.md",
    "14.25": "src/part3-tools/ch14-other-tools/25-android17-ebpf-observability-matrix.md",
    "14.26": "src/part3-tools/ch14-other-tools/26-hook-infrastructure.md",
    "14.27": "src/part3-tools/ch14-other-tools/27-r8-configuration-analyzer.md",
    "14.28": "src/part3-tools/ch14-other-tools/28-gaps-dynamic-analysis.md",
    "15.1": "src/part3-tools/ch15-methodology/01-philosophy.md",
    "15.2": "src/part3-tools/ch15-methodology/02-system-vs-app.md",
    "15.3": "src/part3-tools/ch15-methodology/03-metrics.md",
    "15.4": "src/part3-tools/ch15-methodology/04-competitive-analysis.md",
    "15.5": "src/part3-tools/ch15-methodology/05-online-monitoring.md",
    "15.6": "src/part3-tools/ch15-methodology/06-testing-best-practices.md",
    "15.7": "src/part3-tools/ch15-methodology/07-aosp-reading.md",
    "15.8": "src/part3-tools/ch15-methodology/08-empirical-performance-issues.md",
    "15.9": "src/part3-tools/ch15-methodology/09-performance-governance.md",
    "15.10": "src/part3-tools/ch15-methodology/10-google-android-bench-ai-coding-evaluation-methodology.md",
    "16.1": "src/part4-system/ch16-aosp/01-google-optimization.md",
    "16.2": "src/part4-system/ch16-aosp/02-version-changes.md",
    "16.3": "src/part4-system/ch16-aosp/03-aosp-build.md",
    "16.4": "src/part4-system/ch16-aosp/04-android17-kernel618-performance.md",
    "16.5": "src/part4-system/ch16-aosp/05-android17-api37-performance-changes.md",
    "16.6": "src/part4-system/ch16-aosp/06-profile-dm-sdm-install-compilation.md",
    "16.7": "src/part4-system/ch16-aosp/07-system-boot-time-optimization.md",
    "16.8": "src/part4-system/ch16-aosp/08-appflow-large-app-cold-launch-memory-scheduling.md",
    "16.9": "src/part4-system/ch16-aosp/09-rust-system-services-performance.md",
    "16.10": "src/part4-system/ch16-aosp/10-arm64-kernel-security-mitigation-performance.md",
    "16.11": "src/part4-system/ch16-aosp/11-agent-native-os.md",
    "17.1": "src/part4-system/ch17-oem/01-oem-overview.md",
    "17.2": "src/part4-system/ch17-oem/02-soc-differences.md",
    "17.3": "src/part4-system/ch17-oem/03-industry-cases.md",
    "17.4": "src/part4-system/ch17-oem/04-sched-ext-oem-bpf-scheduler.md",
    "17.5": "src/part4-system/ch17-oem/05-oem-game-mode-input-priority.md",
    "17.6": "src/part4-system/ch17-oem/06-media-performance-class-device-capability.md",
    "17.7": "src/part4-system/ch17-oem/07-private-space-app-lock-boundary.md",
    "17.8": "src/part4-system/ch17-oem/08-power-hal-schedutil-soc-power.md",
    "17.9": "src/part4-system/ch17-oem/09-power-stats-hal-oem-implementation.md",
    "17.10": "src/part4-system/ch17-oem/10-android-auto-car-os-performance.md",
    "18.1": "src/part2-performance/ch18-rendering-pipelines/01-pipeline-overview.md",
    "18.2": "src/part2-performance/ch18-rendering-pipelines/02-android-view-standard.md",
    "18.3": "src/part2-performance/ch18-rendering-pipelines/03-android-view-software.md",
    "18.4": "src/part2-performance/ch18-rendering-pipelines/04-android-view-mixed.md",
    "18.5": "src/part2-performance/ch18-rendering-pipelines/05-android-view-multi-window.md",
    "18.6": "src/part2-performance/ch18-rendering-pipelines/06-surfaceview.md",
    "18.7": "src/part2-performance/ch18-rendering-pipelines/07-textureview.md",
    "18.8": "src/part2-performance/ch18-rendering-pipelines/08-opengl-es.md",
    "18.9": "src/part2-performance/ch18-rendering-pipelines/09-vulkan-native.md",
    "18.10": "src/part2-performance/ch18-rendering-pipelines/10-surface-control-api.md",
    "18.11": "src/part2-performance/ch18-rendering-pipelines/11-angle-gles-vulkan.md",
    "18.12": "src/part2-performance/ch18-rendering-pipelines/12-flutter-rendering.md",
    "18.13": "src/part2-performance/ch18-rendering-pipelines/13-webview-rendering.md",
    "18.14": "src/part2-performance/ch18-rendering-pipelines/14-camera-pipeline.md",
    "18.15": "src/part2-performance/ch18-rendering-pipelines/15-video-overlay-hwc.md",
    "18.16": "src/part2-performance/ch18-rendering-pipelines/16-game-engine.md",
    "18.17": "src/part2-performance/ch18-rendering-pipelines/17-hardware-buffer-renderer.md",
    "18.18": "src/part2-performance/ch18-rendering-pipelines/18-variable-refresh-rate.md",
    "18.19": "src/part2-performance/ch18-rendering-pipelines/19-eyedropper-crossdevice.md",
    "18.20": "src/part2-performance/ch18-rendering-pipelines/20-android-xr-spatial-ui-rendering.md",
    "18.21": "src/part2-performance/ch18-rendering-pipelines/21-media-codec2-tunneled-media3-abr.md",
    "18.22": "src/part2-performance/ch18-rendering-pipelines/22-advanced-professional-video-apv.md",
    "18.23": "src/part2-performance/ch18-rendering-pipelines/23-compose-rendering-pipeline.md",
    "18.24": "src/part2-performance/ch18-rendering-pipelines/24-android17-hwui-vulkan-multi-queue.md",
    "18.25": "src/part2-performance/ch18-rendering-pipelines/25-webgpu-android-pipeline.md",
}

def git(*args):
    r = subprocess.run(["git"] + list(args), cwd=AIW, capture_output=True, text=True)
    return r.stdout.strip()

def git_log(day):
    out = git("log", "--oneline", f"--since={day}T00:00:00+08:00", f"--until={day}T23:59:59+08:00")
    return [l.strip() for l in out.split("\n") if l.strip()]

def git_diff_stat(day):
    return git("diff", "--shortstat", f"--since={day}T00:00:00+08:00", f"--until={day}T23:59:59+08:00")

def classify(commits):
    cats = {"draft": [], "review": [], "rework": [], "feat": [], "freshness": [], "daily": [], "meta": [], "other": []}
    patterns = {
        "draft": [r"\[openclaw\] draft:", r"task2:", r"\bfeat\(ch"],
        "review": [r"\[openclaw\] review:", r"review-r2:", r"review-rework:"],
        "rework": [r"\[openclaw\] rework:", r"\[openclaw\] revision:"],
        "feat": [r"\[openclaw\] feat:", r"\[openclaw\] fix:"],
        "freshness": [r"\[openclaw\] freshness:"],
        "daily": [r"\[openclaw\] daily:"],
        "meta": [r"\[openclaw\] metadata:", r"\[openclaw\] meta:", r"\[openclaw\] progress:", r"chore:"],
    }
    for c in commits:
        m = re.match(r"^[a-f0-9]+\s+(.*)", c)
        if not m: continue
        msg = m.group(1)
        done = False
        for cat, pats in patterns.items():
            if any(re.search(p, msg, re.IGNORECASE) for p in pats):
                cats[cat].append(msg)
                done = True
                break
        if not done:
            cats["other"].append(msg)
    return cats

def extract_ch(msg):
    m = re.search(r"(\d+\.\d+)\s+(.+?)(?:\s*[\-\u2014]|\s*\(|\s*$)", msg)
    return (m.group(1), m.group(2).strip()) if m else (None, None)

def ch_link(ch):
    f = CHAPTER_FILES.get(ch)
    if f and (AIW / f).exists():
        return f"[📄 {ch}]({REPO_URL}/blob/master/{f})"
    return None

def format_day(day, cats, diff_stat):
    lines = [
        f"# Android-Internal-Wiki 更新日志 · {day}",
        "",
        f"> 仓库：[Android-Internal-Wiki]({REPO_URL})",
        f"> 提交记录：[{day} commits]({REPO_URL}/commits/master)",
        "",
    ]
    
    total = sum(len(v) for v in cats.values())
    d, r, w = len(cats["draft"]), len(cats["review"]), len(cats["rework"])
    
    lines.append("## 今日概览")
    lines.append(f"- 提交数：{total}")
    lines.append(f"- 新增章节：{d} | Review：{r} | 回炉修复：{w}")
    if diff_stat:
        lines.append(f"- 变更：{diff_stat}")
    lines.append("")
    
    if cats["draft"]:
        lines.append("## 📝 新增章节")
        for msg in cats["draft"]:
            ch, title = extract_ch(msg)
            if ch:
                link = ch_link(ch)
                entry = f"- **{ch}** {title}"
                if link:
                    entry += f"  {link}"
                lines.append(entry)
            else:
                clean = re.sub(r"\[openclaw\]\s*", "", msg)
                lines.append(f"- {clean}")
        lines.append("")
    
    if cats["review"]:
        lines.append("## 🔍 Review 完成")
        for msg in cats["review"]:
            ch, title = extract_ch(msg)
            if ch:
                if "finalized" in msg.lower() or "定稿" in msg:
                    status = "✅ 定稿"
                elif "回炉" in msg or "B类" in msg or "B-class" in msg:
                    status = "🔄 回炉"
                else:
                    status = "📋 Reviewed"
                link = ch_link(ch)
                entry = f"- **{ch}** {title} — {status}"
                if link:
                    entry += f"  {link}"
                lines.append(entry)
            else:
                lines.append(f"- {msg}")
        lines.append("")
    
    if cats["rework"]:
        lines.append("## 🔧 回炉修复")
        for msg in cats["rework"]:
            ch, title = extract_ch(msg)
            if ch:
                link = ch_link(ch)
                entry = f"- **{ch}** {title}"
                if link:
                    entry += f"  {link}"
                lines.append(entry)
            else:
                clean = re.sub(r"\[openclaw\]\s*", "", msg)
                lines.append(f"- {clean}")
        lines.append("")
    
    other = cats["feat"] + cats["freshness"] + cats["meta"]
    if other:
        lines.append("## ⚙️ 工程与配置")
        for msg in other:
            clean = re.sub(r"\[openclaw\]\s*", "", msg)
            lines.append(f"- {clean}")
        lines.append("")
    
    if cats["other"]:
        lines.append("## 📦 其他")
        for msg in cats["other"]:
            lines.append(f"- {msg}")
        lines.append("")
    
    return "\n".join(lines)

def main():
    CHANGELOG_DIR.mkdir(exist_ok=True)
    
    days = sorted(set(git("log", "--format=%ad", "--date=short").split("\n")))
    print(f"Days: {days}")
    
    for day in days:
        commits = git_log(day)
        diff = git_diff_stat(day)
        cats = classify(commits)
        content = format_day(day, cats, diff)
        out = CHANGELOG_DIR / f"{day}.md"
        out.write_text(content, encoding="utf-8")
        print(f"  {day}: {len(commits)} commits -> {out.name}")
    
    # Index
    idx = [
        "# Android-Internal-Wiki 更新日志索引",
        "",
        "> 每日自动生成，记录新增章节、Review、回炉修复、工程变更。",
        "",
        "| 日期 | 新增 | Review | 回炉 | 提交数 |",
        "|------|------|--------|------|--------|",
    ]
    for day in reversed(days):
        cats = classify(git_log(day))
        d, r, w = len(cats["draft"]), len(cats["review"]), len(cats["rework"])
        t = sum(len(v) for v in cats.values())
        idx.append(f"| [{day}]({day}.md) | {d} | {r} | {w} | {t} |")
    idx.append("")
    (CHANGELOG_DIR / "README.md").write_text("\n".join(idx), encoding="utf-8")
    print(f"Index -> README.md")

if __name__ == "__main__":
    main()
