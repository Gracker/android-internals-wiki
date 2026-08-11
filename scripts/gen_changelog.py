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
    "5.7": "src/part1-fundamentals/ch05-cpu-power/07-cpu-evolution.md",
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
    "13.5": "src/part3-tools/ch13-perfetto/05-topic-analysis.md",
    "13.6": "src/part3-tools/ch13-perfetto/06-thread-cpu-states.md",
    "13.7": "src/part3-tools/ch13-perfetto/07-advanced-usage.md",
    "14.1": "src/part3-tools/ch14-other-tools/01-as-profiler.md",
    "14.2": "src/part3-tools/ch14-other-tools/02-simpleperf.md",
    "14.3": "src/part3-tools/ch14-other-tools/03-memory-tools.md",
    "14.4": "src/part3-tools/ch14-other-tools/04-dumpsys.md",
    "14.5": "src/part3-tools/ch14-other-tools/05-third-party-libs.md",
    "14.6": "src/part3-tools/ch14-other-tools/06-automation-tools.md",
    "14.7": "src/part3-tools/ch14-other-tools/07-profiling-manager.md",
    "15.1": "src/part3-tools/ch15-methodology/01-philosophy.md",
    "15.2": "src/part3-tools/ch15-methodology/02-system-vs-app.md",
    "15.3": "src/part3-tools/ch15-methodology/03-metrics.md",
    "15.4": "src/part3-tools/ch15-methodology/04-competitive-analysis.md",
    "15.5": "src/part3-tools/ch15-methodology/05-online-monitoring.md",
    "15.6": "src/part3-tools/ch15-methodology/06-testing-best-practices.md",
    "15.7": "src/part3-tools/ch15-methodology/07-aosp-reading.md",
    "16.1": "src/part4-system/ch16-aosp/01-google-optimization.md",
    "16.2": "src/part4-system/ch16-aosp/02-version-changes.md",
    "16.3": "src/part4-system/ch16-aosp/03-aosp-build.md",
    "17.1": "src/part4-system/ch17-oem/01-oem-overview.md",
    "17.2": "src/part4-system/ch17-oem/02-soc-differences.md",
    "17.3": "src/part4-system/ch17-oem/03-industry-cases.md",
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
