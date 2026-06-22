---

title: "竞品分析方法"
chapter: "15.4"
section: "15.4"
status: finalized
drafted_date: "2026-04-04"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-06-16"
last_verified_against: "developer.android.com current official URLs; AOSP android-16.0.0_r1 ActivityTaskManagerService / ActivityMetricsLogger / ActivityRecord / FrameMetrics; packages/modules/adb android-16.0.0_r1 adb.1.md"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/launch-time"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/ActivityTaskManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/ActivityMetricsLogger.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/ActivityRecord.java"
  - type: official
    path: "https://developer.android.com/studio/debug/apk-analyzer"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/benchmarking-overview"
  - type: official
    path: "https://developer.android.com/reference/android/view/FrameMetrics"
  - type: aosp
    path: "frameworks/base/core/java/android/view/FrameMetrics.java"
tags: ['competitive-analysis', 'benchmark', 'startup', 'fps', 'apk-size', 'methodology']
related_chapters: ["7.3", "8.3", "12.1", "13.2", "14.1", "15.3"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
reviewed_by: openclaw-task6
reviewed_date: 2026-06-16
task6_result: pass-light-edit
last_task6_audit: "2026-06-21T06:08:32+08:00"
task9_result: auto-fixed
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-04-28"
last_task9_at: "2026-04-28T07:40:26+08:00"
task2b_result: fixed
last_task2b_at: "2026-04-27T21:44:26+08:00"
repaired_date: "2026-04-27"
repaired_by: "openclaw-task2b"
task9_review_notes: "2026-04-28 task9 deep-review: pass-tech-review。无 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。P2 3 写入 suggestions。"
last_task9_audit: "2026-06-16"
last_task9_audit_log: "logs/deep-review/2026-06-16-18-audit.md"
task9_audit_notes: '2026-05-23 Task9 idle audit: 无 P0/P1。源码路径与 Android 16 FrameMetrics/ActivityTaskManager 链路复核通过；仅记录 P2：Benchmarking overview 官方 URL 已迁移。 | 2026-06-16 Task9 idle audit auto-fixed: P0 1（Battery Historian bugreport 导出命令修正为 adb bugreport bugreport.zip）/ P1 0 / P2 1（官方文档 URL 迁移修正）；回到 Task6 复审。'
deepseek_polish_state: done
last_deepseek_polish_at: "2026-05-25"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-17
last_task9_autofix_at: "2026-06-16"
updated_by: "openclaw-task9"
updated_date: "2026-06-16"
last_task6_at: 2026-06-16T20:10:00+08:00
---

# 竞品分析方法

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 竞品性能对比的方法论：同设备、同场景、同网络、同温度
- 🔹 竞品启动速度对比：adb am start -W 的正确使用
- 🔹 竞品流畅性对比：抓 Trace 对比帧耗时分布
- 🔹 竞品包体积对比：APK Analyzer + 横向统计
- 🔹 注意事项：控制变量、多次采样、避免误导性结论

### 扩展（可选深入）

- 🔸 自动化竞品对比测试流水线
- 🔸 竞品功耗对比方法

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要认真做竞品性能分析

竞品分析最容易做成两种无效工作：一种是凭感觉说“这个快那个慢”；另一种是抓了一堆数据，但设备、温度、网络、操作路径全不一致，最后谁都说服不了谁。

这件事的难点不在工具，而在实验设计。要先保证自己看到的差异来自 App 本身，而不是设备状态、网络波动和热限频这些噪声。

如果我们能做到"同设备、同场景、同条件"，那么竞品对比的结果就不再是主观感受，而是可以拿去驱动优化决策的客观数据。一个团队如果能建立这样的对比能力，就能在每次版本迭代后量化自己与竞品的差距变化，知道优化方向对不对、优化效果够不够。

这一节的重点，就是把“怎么比”这件事讲清楚。

## 竞品性能对比的方法论

竞品性能对比的第一步是把实验框架搭好。先确保对比条件可靠，再往里面填具体的测试维度。

### 控制变量的四项基本原则

竞品对比的核心逻辑只有一个：**一次只变一个东西**。我们在测试 App A 和 App B 的性能差异时，除了 App 本身不同，其他所有条件必须一致。具体来说，有四个维度必须控制住：

**同设备**——这是最基本的条件。不同的 SoC、不同的内存容量、不同的屏幕刷新率，都会对性能数据产生量级以上的影响。在同一台设备上测试两个 App，可以消除硬件差异。如果需要在多个设备上对比（比如覆盖不同价位段），那么每组对比内部仍然必须是同一台设备，最后再把不同设备的结果做交叉验证。

**同场景**——同一个 App 的不同页面，性能表现可能天差地别。对比启动速度时，我们测试的都是从 Launcher 点击图标到首屏完全展示的完整流程；对比滑动流畅性时，选取的都是类似的 Feed 流或列表页面。场景定义要足够具体，不能只说"首页"，而要明确到"首页首次加载完成后的列表滑动"，因为首页冷启动和热启动的性能数据完全不可比。

**同网络**——对于有网络依赖的场景（大多数现代 App 都有），网络条件是必须控制的变量。理想做法是在同一 Wi-Fi 环境下测试，或者用 Charles / mitmproxy 搭建代理，用 Network Link Conditioner 模拟固定的网络带宽和延迟。如果两个 App 在不同的网络条件下测试，启动时间可能差出几百毫秒，这个差异和 App 本身的性能完全无关。

**同温度**——这是最容易被忽略的因素。现代手机在发热后会触发温控策略，降低 CPU 频率（Thermal Throttling），直接影响所有性能指标。如果我们先测了 App A 的十轮启动，设备已经发热，再测 App B，那 App B 的数据天然吃亏。正确的做法是两轮测试之间让设备冷却（可以等待几分钟或用散热背夹），或者在测试顺序上交替进行（A1 → B1 → A2 → B2），通过轮换消除顺序偏差。

### 测试前的设备准备

在每次测试之前，我们需要做一组标准化的设备准备工作，确保测试环境的一致性：

1. **关闭后台应用**：`adb shell am kill-all` 清理后台进程，或手动在最近任务中划掉所有 App。
2. **关闭系统动画**：在开发者选项中将"窗口动画缩放"、"过渡动画缩放"、"动画程序时长缩放"全部设为 0.5x 或关闭。动画会影响启动和页面切换的时间测量。
3. **固定屏幕亮度**：设为手动模式并固定在一个中间值（如 50%），避免自动亮度调节引起的功耗波动。
4. **电量保持充足**：确保设备电量在 80% 以上。低电量模式下部分厂商会限制 CPU 频率。
5. **关闭自动同步和更新**：避免后台同步在网络和 IO 上引入噪声。

这些准备工作看似琐碎，但在大量采样时能有效降低数据的方差。

### 采样策略：少量多次还是多量少次？

采样策略的选择取决于我们追求的是"精度"还是"效率"。

对于启动速度这类可重复的场景，建议每组至少采集 **20-30 次** 数据，然后取中位数（而非平均值）作为代表值。中位数比平均值更抗干扰——如果某次测试遇到了 GC 或系统服务的偶发延迟，平均值会被拉偏，但中位数基本不受影响。

对于滑动流畅性这类需要人工操作的场景，因为难以完美复现每次滑动的速度和距离，建议采用 **5-10 次** 较长距离的滑动采样，然后对比帧耗时的分布（P50、P90、P99），而不是只看单一指标。

采样次数的统计学置信区间计算方法目前还没有标准公式，这里先用经验值。

## 竞品启动速度对比

启动速度是最常被拿来对比的指标，也是最容易测错的一个。我们来讲清楚正确的测量方法和常见的坑。

### adb am start -W 的原理与正确使用

`adb shell am start -W` 是测量 App 启动时间最直接的工具。现代 Android 中，这条命令经由 `ActivityTaskManagerService#startActivityAndWait` 发起启动，并等待系统拿到启动结果。启动转场、窗口绘制和 `Displayed` 日志主要由 `com.android.server.wm` 下的 `ActivityRecord`、`ActivityMetricsLogger` 和窗口管理代码协同完成，参考路径应落到 `ActivityTaskManagerService.java` / `ActivityMetricsLogger.java`，不再指向旧的 `ActivityManagerService.java` 单点。

当目标 Activity 的窗口完成首轮绘制，WindowManager 侧会把 `windowsDrawn` 事件传给 `ActivityMetricsLogger`，本次启动 transition 的统计才结束，`am start -W` 的 `WaitResult` 才能填出 `ThisTime` / `TotalTime` / `WaitTime`。这个口径比“执行到 `onResume()`”更接近用户看到首帧的时刻。

执行命令：

```bash
# 冷启动：先强制停止再启动
adb shell am force-stop com.example.app
sleep 2  # 等待进程完全退出
adb shell am start -W com.example.app/.MainActivity
```

输出结果：

```
Starting: Intent { act=android.intent.action.MAIN cat=[android.intent.category.LAUNCHER]
                  cmp=com.example.app/.MainActivity }
Status: ok
Activity: com.example.app/.MainActivity
ThisTime: 1024
TotalTime: 1024
WaitTime: 1038
Complete.
```

这里有三个时间值需要区分清楚：

**TotalTime** 是竞品冷启动对比中优先看的值。它代表从系统接收到启动请求，到启动路径中末端 Activity 首轮窗口绘制完成的耗时。对于只有一个 Activity 的冷启动场景，TotalTime 基本反映 App 从进程创建到首帧可见的成本。

**ThisTime** 记录的是最后一个 Activity 的启动耗时。如果 App 的启动路径中有中间 Activity（比如一个透明的路由 Activity 跳转到真正的首页），ThisTime 只计最后一段，TotalTime 则包含整个路径。所以竞品对比用 TotalTime，不要用 ThisTime。

**WaitTime** 是从 `am` 命令发起时刻到系统返回结果的总时间，包含了 Pause 前一个 Activity 的开销。这个值受系统状态影响较大，不适合做精确的竞品对比。

### 自动化多次采样的脚本

手工跑一次 `am start -W` 容易，但要做 30 次重复采样并汇总统计，就需要自动化脚本。以下是一个实用的采样模板：

```bash
#!/bin/bash
# cold_start_benchmark.sh — 冷启动竞品对比采样脚本
# 用法: ./cold_start_benchmark.sh <包名> <Activity 名> <采样次数>

PACKAGE=$1
ACTIVITY=$2
COUNT=${3:-30}

echo "=== 冷启动测试: $PACKAGE ==="
echo "采样次数: $COUNT"

for i in $(seq 1 $COUNT); do
    adb shell am force-stop $PACKAGE
    sleep 2  # 冷却间隔
    RESULT=$(adb shell am start -W $PACKAGE/$ACTIVITY 2>&1)
    TOTAL=$(echo "$RESULT" | grep "TotalTime" | awk '{print $2}')
    echo "第${i}次: ${TOTAL}ms"
done
```

拿到原始数据后，我们在本地计算中位数和离散度：

```bash
# 从输出文件中提取所有 TotalTime，计算统计值
grep "TotalTime" results.txt | awk '{print $2}' | \
awk '{sum+=$1; vals[NR]=$1; if($1>max) max=$1; if(NR==1||$1<min) min=$1}
     END{n=NR; asort(vals);
     if(n%2==1) median=vals[int(n/2)+1];
     else median=(vals[n/2]+vals[n/2+1])/2;
     printf "样本数:%d  中位数:%.0fms  最小:%dms  最大:%dms  平均:%.0fms\n", n, median, min, max, sum/n}'
```

### 冷启动 vs 温启动 vs 热启动

竞品启动对比必须明确测试的是哪种启动类型，因为三者的性能瓶颈完全不同：

- **冷启动（Cold Start）**：进程不存在，系统需要 fork Zygote、加载 APK、初始化 Application 和 Activity。这是最重的启动类型，也是竞品对比中最常测试的场景。确保冷启动的方式是 `am force-stop` 而不是 `kill`，因为 force-stop 会清理进程的所有状态。
- **温启动（Warm Start）**：进程存在但 Activity 被销毁了（比如用户按了返回键）。系统只需重建 Activity，不需要重新创建进程和初始化 Application。
- **热启动（Hot Start）**：进程和 Activity 都在，只是从后台切回前台。这是最快的启动类型，通常只涉及 Window 的恢复和重绘。

竞品对比通常关注冷启动，因为它最能体现 App 的启动优化功底。但如果我们想了解竞品的保活和缓存策略，温启动和热启动的对比也很有价值。

部分 App 使用多进程架构，冷启动时主进程和子进程的启动顺序会影响 TotalTime。这种情况下，`am start -W` 的计时可能不包含子进程的完整初始化。如果需要精确分析多进程启动，建议配合 Perfetto Trace 做更深入的时间线分析。

目前还不能确认 Android 16 是否调整了 am start -W 的计时逻辑，尤其是涉及 SplashScreen 的场景。

### 启动对比的注意事项

有几个常见的坑需要特别注意：

**Android 12+ SplashScreen 的拆段**：Android 12 引入系统 SplashScreen 后，用户先看到系统起始窗口，首页内容通常在后面一段才完成。`TotalTime` 仍是系统等待启动完成的命令行口径，不能单独代表首页内容已经可交互。竞品对比时，打开 Perfetto 的 `ActivityManager` / `WindowManager` track，把启动拆成两段记录：

- `Start proc` / `activityStart` → SplashScreen starting window 显示：主要反映进程创建、`Application` 初始化和系统起始窗口准备。
- SplashScreen 退出 → 首页首帧 / `reportFullyDrawn()`：主要反映路由页、首屏数据、布局绘制和业务 ready。

报告里把 `TotalTime`、首页首帧和 `reportFullyDrawn()` 分开写。两个竞品如果 SplashScreen 策略不同，只拿一个 `TotalTime` 数字横比，会把系统起始窗口和业务首页成本混在一起。

**Multi-Window 和分屏模式**：如果设备处于分屏状态，启动时间会显著增加。确保测试时设备处于全屏模式。

**编译模式差异**：ART 的编译模式会影响启动速度。如果某个 App 刚安装未经过后台优化（`dex2oat`），启动会比已优化过的慢很多。在正式测试前，可以对所有待测包执行同一组 profile 引导步骤，再强制按 profile 编译：

```bash
adb shell cmd package compile -m speed-profile -f <package_name>
```

`speed-profile` 只把 profile 命中的热点路径 AOT 编译，接近用户使用一段时间后的稳定状态。`speed` 会全量 AOT 编译，容易把竞品和自家 App 都推到实验室上限，适合排除 JIT 噪声，不适合当默认竞品口径。

## 竞品流畅性对比

启动速度可以用一个数字概括，但流畅性不行。两个 App 可能 FPS 都是 58，但一个掉帧均匀分布（每次掉 1-2 帧），另一个集中掉帧（偶尔卡顿 100ms+），用户体验天差地别。所以流畅性对比必须看**帧耗时分布**，不能只看平均 FPS。

### 抓 Trace 对比帧耗时分布

流畅性对比的标准做法是同时抓取两个 App 的 Perfetto Trace，然后在同一个分析维度下对比帧耗时。

抓取 Trace 时需要控制的条件：

1. **固定操作路径**：提前定义好测试操作的每一步，比如"打开 App → 等待首页加载完成 → 向上滑动 3 屏 → 停止"。操作路径越精确，对比越公平。
2. **自动化的滑动操作**：用 `adb shell input swipe` 或 `adb shell getevent/sendevent` 模拟滑动，确保每次滑动的速度、距离、方向一致。手工滑动每次力度不同，会引入大量噪声。
3. **足够的采样时长**：单次 Trace 至少覆盖 10 秒以上的连续操作，才能得到有统计意义的帧耗时分布。

```bash
# 抓取竞品 A 的滑动 Trace
adb shell am start -W com.app.a/.MainActivity
sleep 3  # 等待首页加载
adb shell perfetto -c - --txt <<EOF
buffers: { size_kb: 65536 }
data_sources: { config { name: "linux.ftrace" ftrace_config {
  ftrace_events: "sched/sched_switch" ftrace_events: "power/cpu_frequency"
  atrace_categories: "view" atrace_categories: "input" atrace_categories: "wm"
  atrace_apps: "com.app.a" } } }
duration_ms: 15000
EOF &
PERFPID=$!

# 模拟滑动（600ms 内从屏幕 70% 位置滑到 30% 位置）
sleep 2
adb shell input swipe 540 1400 540 600 600
sleep 2
adb shell input swipe 540 1400 540 600 600
wait $PERFPID
```

### 帧耗时分析的关键指标

拿到 Trace 后，我们关注的是帧耗时的**分布特征**，而非单一帧的时间。在 Perfetto 中查看帧耗时的方法我们在 §13.3 和 §13.5 中已经详细介绍过，这里重点讲对比维度：

**P50（中位数帧耗时）**：反映"典型帧"的渲染速度。60Hz 设备上，P50 应该在 16.6ms 以下。120Hz 设备上，P50 应该在 8.3ms 以下。如果竞品 A 的 P50 是 12ms，竞品 B 是 9ms，说明 B 的单帧渲染效率更高。

**P90 和 P99（长尾帧耗时）**：反映"偶发卡顿"的严重程度。这是用户体验最敏感的指标。如果竞品 A 的 P99 是 32ms（偶尔掉一帧），竞品 B 的 P99 是 80ms（偶尔卡顿近 5 帧），即使 A 和 B 的 P50 接近，用户体感上 A 会更流畅。

**Jank 率和 BigJank 率**：Jank 定义为单帧耗时超过一帧的 VSync 周期（60Hz 下 > 16.6ms），BigJank 定义为超过三倍 VSync 周期（> 50ms）。这两个指标的直观含义是"用户能感知到的卡顿次数占比"。

### 使用 FrameMetrics 做线上对比

如果我们想在真实用户环境中对比流畅性（而不是实验室条件），可以使用 `FrameMetrics` API 来采集数据。相比 Perfetto Trace，FrameMetrics 的开销小得多，适合线上部署。

```java
// 注册 FrameMetrics 监听
// [已验证: 官方文档, developer.android.com/reference/android/view/FrameMetrics]
activity.getWindow().addOnFrameMetricsAvailableListener(
    (window, frameMetrics, dropCountSinceLastInvocation) -> {
        long totalDuration = frameMetrics.getMetric(FrameMetrics.TOTAL_DURATION);
        long drawDuration = frameMetrics.getMetric(FrameMetrics.DRAW_DURATION);
        long layoutDuration = frameMetrics.getMetric(FrameMetrics.LAYOUT_MEASURE_DURATION);
        // 上报到 APM 平台，按 P50/P90/P99 统计
    },
    new Handler(Looper.getMainLooper())
);
```

线上对比时，两个 App 上报的指标口径必须一致。AOSP android-16.0.0_r1 的 `FrameMetrics.java` 中，`TOTAL_DURATION` 对应 `INTENDED_VSYNC` 到 `FRAME_COMPLETED` 的完整跨度，`DEADLINE` 对应当前帧的目标完成时刻；当 `TOTAL_DURATION < DEADLINE` 时，本帧命中预期 deadline。`PERFORM_TRAVERSALS_START` 只参与 `LAYOUT_MEASURE_DURATION` 等分段指标，不能当作 `TOTAL_DURATION` 的起点。

如果分析 `performTraversals()` 之后的应用侧开销，应该拆看 `LAYOUT_MEASURE_DURATION`、`DRAW_DURATION`、`SYNC_DURATION`、`COMMAND_ISSUE_DURATION`、`SWAP_BUFFERS_DURATION`，再对应到 Perfetto 中 UI thread、RenderThread、SurfaceFlinger 的时间线。

不同 APM 平台的流畅性指标口径差异较大，目前还没有统一对比。

## 竞品包体积对比

包体积虽然不直接影响运行时性能，但影响用户的下载意愿和安装转化率。Google Play 的数据表明，APK 体积每增加 10MB，安装转化率下降约 1.5%。对于在新兴市场（网络条件差、存储空间紧张）的竞争，包体积是硬指标。

### APK Analyzer 的使用

Android Studio 自带的 APK Analyzer 是包体积分析的主力工具。它能打开任何 APK 文件（不限于自己开发的），展示内部结构和大文件分布。

使用方法：

1. 在 Android Studio 中选择 `Build → Analyze APK`，或者直接将 APK 文件拖入编辑器窗口。
2. APK Analyzer 会展示 APK 内每个文件和目录的大小，按 DEX、Resources、Assets、Native Libraries 等分类汇总。
3. 对于 DEX 文件，可以进一步展开查看类和方法的数量以及占用的字节。
4. 对于资源文件，可以按目录浏览，快速定位大图、大字体等体积消耗者。

竞品对比时，把竞品 APK 也拖进 APK Analyzer，手工记录各分类的大小，就能做出一张横向对比表。

### 命令行工具 apkanalyzer

如果要批量分析多个竞品 APK（比如自动化对比脚本中），可以使用 Android SDK Command-Line Tools 提供的 `apkanalyzer` 命令行工具：

```bash
# 查看 APK 摘要信息
apkanalyzer apk summary /path/to/app.apk

# 查看文件大小（按大小排序）
apkanalyzer files list /path/to/app.apk --size

# 查看 DEX 方法数
apkanalyzer dex list /path/to/app.apk

# 对比两个 APK 的差异
apkanalyzer apk compare /path/to/old.apk /path/to/new.apk
```

通过脚本化，我们可以快速生成竞品包体积的横向对比报告：

```bash
#!/bin/bash
# apk_size_compare.sh — 竞品包体积对比
APKS=("app-a.apk" "app-b.apk" "app-c.apk")
echo "包体积对比报告"
echo "=========================================="
printf "%-20s %12s %12s %12s %12s\n" "App" "总大小" "DEX" "Resources" "Native"
echo "------------------------------------------"
for apk in "${APKS[@]}"; do
    TOTAL=$(stat -f%z "$apk" 2>/dev/null || stat -c%s "$apk")
    # 用 unzip 列出各分类的大小
    DEX=$(unzip -l "$apk" "*.dex" | tail -1 | awk '{print $1}')
    RES=$(unzip -l "$apk" "res/*" | tail -1 | awk '{print $1}')
    NATIVE=$(unzip -l "$apk" "lib/*" | tail -1 | awk '{print $1}')
    printf "%-20s %9.1fMB %9.1fMB %9.1fMB %9.1fMB\n" \
        "$apk" $(echo "$TOTAL/1048576"|bc) $(echo "$DEX/1048576"|bc) \
        $(echo "$RES/1048576"|bc) $(echo "$NATIVE/1048576"|bc)
done
```

### 包体积对比的关键维度

在竞品包体积对比中，我们关注的不仅仅是"谁更小"，而是"大在哪里"和"大的原因"。以下是几个关键的分析维度：

**DEX 体积**：反映代码量。如果竞品的 DEX 体积明显小于我们，可能的原因包括：使用了更激进的语言（Kotlin 编译后的字节码通常比 Java 体积稍大）、更好的代码混淆（R8 的 tree-shaking 更彻底）、或者功能模块拆分更合理。

**Native 库体积**：这是很多 App 包体积差异的最大来源。支持多少个 ABI（armeabi-v7a、arm64-v8a、x86、x86_64）直接决定了 Native 库的体积倍数。如果竞品只提供 arm64-v8a 的 AAB（通过 Google Play 的 ABI 分发），而我们同时打包了多个 ABI，Native 部分的体积可能差出几倍。

**资源体积**：图片、字体、动画资源是体积大头。WebP 替换 PNG、矢量图替代位图、资源混淆（AndResGuard）都能显著压缩这部分。如果竞品的资源体积明显更小，大概率是在图片格式和资源管理策略上做了更多工作。

**Assets 体积**：有些 App 会在 assets 中打包 HTML5 页面、JS Bundle、预置数据等。这部分通常被忽略，但在某些类型的 App 中可能占比很大。

AAB（Android App Bundle）格式下，Google Play 会按设备特征（ABI、屏幕密度、语言）生成定制的 APK，实际下载体积远小于完整 APK。竞品对比时应区分"完整 APK 体积"和"实际下载体积"，后者才是用户体验的真实指标。Google Play Console 提供了下载体积的参考数据。

## 注意事项：避免误导性结论

竞品性能分析最怕得出错误结论后投入资源优化了错误的方向，这比数据不好看代价更大。以下是几个常见的误区。

### 误区一：只看单次数据就下结论

性能数据天然有波动。一次测试中 App A 的启动时间是 800ms，App B 是 850ms，不能直接得出"A 比 B 快"的结论。也许第二次测试 B 只用了 780ms。只有经过 20 次以上的重复采样，两个 App 的中位数差异在统计上显著（比如差异大于标准差的 2 倍），我们才能说"在这个场景下 A 的启动速度优于 B"。

### 误区二：不同量级的场景放在一起比

冷启动和热启动的耗时差一个数量级。如果把竞品 A 的冷启动时间和竞品 B 的温启动时间放在一起比，结论毫无意义。同样道理，首页信息流滑动和设置页面滑动的流畅性也不可同日而语。对比的前提是场景定义一致。

### 误区三：忽略版本差异和编译状态

同一个 App 在不同版本之间的性能可能差异很大。如果拿我们的最新版本去跟竞品的旧版本比，赢了也不光彩。反过来，如果竞品刚发了一个大版本做了大量优化，我们拿旧数据去比就会低估差距。竞品对比应该尽量使用各方最新发布版本。

编译状态也是一个隐蔽的变量。ART 的 JIT 和 Profile 引导编译会在 App 使用几天后逐渐优化启动路径。刚安装的 App 和已使用一周的 App，启动速度可能差 20% 以上。如果我们在 A/B 测试前重装了竞品但没有重装自己的 App，数据就会有偏差。

### 误区四：把设备差异当性能差异

即便我们用同一台设备测试，如果测试过程中系统推送了一个大版本更新、安全补丁、或者 Google Play Services 升级，都可能影响性能数据。所以竞品对比最好在短时间窗口内完成（比如同一天、同一个上午），避免设备状态在两次测试之间发生不可控的变化。

### 误区五：忽略 SoC 平台差异的影响

在不同品牌手机上测试同一个 App，性能数据可能差别很大。高通骁龙和联发科天玑的 CPU 调度策略不同，GPU 能力不同，内存带宽不同。如果我们在骁龙 8 Gen 3 上测了竞品 A，在天玑 9300 上测了竞品 B，然后得出"A 比 B 流畅"的结论，我们比较的可能是两个 SoC 而不是两个 App。

手机厂商的性能模式（如"性能模式"或"游戏模式"）会改变 CPU 调频策略和温控阈值。在竞品对比前，确保设备的性能模式设置一致，或统一使用默认模式。

## 扩展：自动化竞品对比测试流水线

如果团队需要定期（比如每周或每个版本）做竞品性能对比，手动操作效率太低，需要建设自动化流水线。

### 基本架构

一个完整的自动化竞品对比流水线包含以下环节：

1. **APK 获取**：通过 Google Play 或其他渠道定期拉取竞品最新版本。可以借助 `gplaydl` 等开源工具或手动维护 APK 存档。
2. **设备管理**：使用 adb 连接的测试设备池，每台设备在测试前执行标准化初始化脚本（清理后台、关闭动画、固定亮度）。
3. **测试执行**：使用 Python 或 Shell 脚本驱动 adb 命令，自动执行启动测试和滑动测试。
4. **数据采集**：启动时间直接从 `am start -W` 输出中提取；流畅性数据可以通过 `dumpsys gfxinfo` 或 FrameMetrics 采集。
5. **数据分析**：将原始数据汇总为统计表格（中位数、P90、P99），生成可视化图表。
6. **报告输出**：自动生成 Markdown 或 HTML 格式的对比报告，包含数据表格、趋势图和简要分析。

使用 Macrobenchmark 库实现自动化启动和滑动测试的完整示例仍在整理中。

不同 Android 版本的 dumpsys gfxinfo 输出格式可能有差异，需要做版本适配确认。

## 扩展：竞品功耗对比方法

功耗对比是竞品分析中难度最高的维度，因为功耗测量对实验条件的要求极其严格，且需要专业的硬件设备。

### 软件测量方案

最简便的方式是使用 Battery Historian 工具。它可以分析系统的电量使用情况，包括各 App 的 CPU 时间、WakeLock 持有时长、网络活动、GPS 使用等。

```bash
# 重置电池数据
adb shell dumpsys batterystats --reset

# 执行测试操作...

# 导出电池数据
adb bugreport bugreport.zip
# 使用 Battery Historian 分析
battery-historian --port 9998
```

软件方案的精度有限，只能看到"相对耗电"而非"绝对耗电"。如果两个 App 的功耗差异在 5% 以内，软件方案很难可靠地分辨。

### 硬件测量方案

高精度的功耗对比需要使用外部电流表（如 Monsoon Power Monitor），直接测量设备的电流消耗。这种方案可以精确到毫安级，但需要拆机接线或使用特殊的测试设备，成本较高。

在条件允许的情况下，硬件方案的流程是：

1. 断开设备电池，接入 Monsoon Power Monitor 供电。
2. 在固定操作路径下记录完整的电流曲线。
3. 对电流曲线积分得到总功耗（mAh），或取平均功率（mW）作为对比指标。
4. 在相同操作路径下对比不同 App 的功耗数据。

使用 Monsoon Power Monitor 进行功耗测试的详细配置步骤仍在整理中。

## 参考资料

### 官方文档
- [App startup time](https://developer.android.com/topic/performance/vitals/launch-time) — 官方启动时间测量指南
- [APK Analyzer](https://developer.android.com/studio/debug/apk-analyzer) — APK 分析工具文档
- [Benchmarking overview](https://developer.android.com/topic/performance/benchmarking/benchmarking-overview) — 性能基准测试框架
- [FrameMetrics API](https://developer.android.com/reference/android/view/FrameMetrics) — 帧性能测量 API
- [Reduce APK size](https://developer.android.com/topic/performance/reduce-apk-size) — APK 体积优化指南
- [Battery Historian](https://developer.android.com/topic/performance/power/battery-historian) — 电量分析工具

### AOSP 源码
- `frameworks/base/services/core/java/com/android/server/wm/ActivityTaskManagerService.java` — `am start -W` 等启动请求的服务端入口
- `frameworks/base/services/core/java/com/android/server/wm/ActivityMetricsLogger.java` — 启动 transition、`windowsDrawn` 与 `Displayed` 计时记录
- `frameworks/base/services/core/java/com/android/server/wm/ActivityRecord.java` — Activity 窗口绘制完成状态与启动等待结果
- `frameworks/base/core/java/android/view/FrameMetrics.java` — FrameMetrics API 定义
- `frameworks/base/core/java/android/view/Choreographer.java` — VSync 和帧回调机制

### 工具与平台
- [Perfetto](https://perfetto.dev/) — 系统级 Trace 分析平台（§13.2-§13.5 详细介绍）
- [Android Studio Profiler](https://developer.android.com/studio/profile) — 集成性能分析工具（§14.1 详细介绍）
- [Monsoon Power Monitor](https://www.msoon.com/online-store) — 硬件功耗测量设备
