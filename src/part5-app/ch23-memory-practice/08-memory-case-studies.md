---
title: "内存优化案例集"
chapter: "23.8"
section: "23.8"
status: ready-for-review
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-14"
last_verified_against: "AOSP android-16.0.0_r1 + Android Developers + Perfetto docs + Source Android native memory docs + Clippings/Android 性能优化"
confidence: medium
drafted_date: "2026-05-14"
drafted_by: openclaw-task2a
polish_count: 0
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/graphics/load-bitmap"
  - type: official
    path: "https://developer.android.com/topic/performance/graphics/manage-memory"
  - type: official
    path: "https://developer.android.com/topic/performance/memory"
  - type: official
    path: "https://developer.android.com/studio/profile/memory-profiler"
  - type: official
    path: "https://developer.android.com/studio/profile/capture-heap-dump"
  - type: official
    path: "https://source.android.com/docs/core/tests/debug/native-memory"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/native-heap-profiler"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/Bitmap.java @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Debug.java @ android-16.0.0_r1"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]"
tags: [case-study, memory, bitmap, native-memory, memory-budget]
related_chapters: ["23.1", "23.2", "23.3", "23.4", "23.7", "20.5"]
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: pending
task2b_result: fixed-lite
task2b_state: fixed
last_task2b_lite_at: "2026-05-27"
reviewed_by: openclaw-task6
reviewed_date: "2026-05-14"
task6_result: needs-rework
last_task6_review_log: "logs/review/2026-05-14-06-review.md"
task9_result: needs-rework
task9_reviewed_date: "2026-05-14"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-14T06:32:15+08:00"
last_task9_review_log: logs/deep-review/2026-05-14-06-deep-review.md
task9_review_notes: "2026-05-14 Task9 06: needs-rework。P1 1：heapprofd / smaps 运行条件缺少 user/userdebug、profileable/debuggable 与权限边界；P2 1：26.3 仍为 draft 引用。 已写入 logs/deep-review/2026-05-14-06-deep-review.md。"
---

# 内存优化案例集

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Bitmap 内存治理实战
- 🔹 Native 内存泄漏排查案例
- 🔹 大型 App 内存预算管理

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要看内存优化案例

前面几节已经把内存泄漏、Bitmap、Native Heap、Java Heap、GC 抖动和线上监控拆开讲过。案例集换一个视角：把线上现象、排查路径、验证材料和修复动作放在同一张表里，避免只得到“内存涨了”这种不可执行的结论。

本节不重复展开 ART 堆结构、Bitmap 解码 API、heapprofd 配置和线上指标采集。相关机制详见 23.1、23.2、23.3、23.4、23.7 节；OOM 分类与稳定性口径详见 20.5 节。

[需补充素材: 本节目前主要是排查模板和治理口径，缺少 1-2 个可脱敏真实案例的修复前后数据、Heap Dump / heapprofd 观察点或线上 PSS 趋势。建议 Task 2B 补齐案例证据后再进入终审。]

[结构参考: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md]
[结构参考: Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md]
[结构参考: Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md]

## Bitmap 内存治理实战：先拆成“大图”和“泄漏”两类

[已验证: 官方文档, developer.android.com/topic/performance/graphics/load-bitmap]
[已验证: 官方文档, developer.android.com/topic/performance/graphics/manage-memory]
[已验证: AOSP android-16.0.0_r1, frameworks/base/graphics/java/android/graphics/Bitmap.java]
[结构参考: Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md]

图片问题常见于信息流、相册、商品详情和富文本页面。症状看起来相似：Native Heap、Graphics 或 PSS 在滑动后上升，页面退出后回落慢，低端机更容易触发 OOM。排查时先把问题拆成两类：解码出来的 Bitmap 本身太大，或者 Bitmap 所属页面已经失效但对象还被引用。

两类问题要用不同证据确认。

- **大图问题**：同一张图片在屏幕上只显示成缩略图，解码后却保留原始像素尺寸。Android Developers 的大图加载文档给出的路径是先用 `inJustDecodeBounds` 读取边界，再按目标显示尺寸计算 `inSampleSize`，第二次 decode 才分配像素内存。
- **泄漏问题**：页面退出、列表 item 回收或弹窗关闭后，Bitmap 仍被 Activity、Adapter、ImageView、缓存集合或异步回调持有。AOSP `Bitmap` Java 对象持有 native 指针，并通过 `NativeAllocationRegistry` 关联 Native 释放；Java 对象活着时，像素内存也可能继续留在进程里。

一个可复用的排查表如下。

| 观察项 | 大图问题 | 泄漏问题 |
| --- | --- | --- |
| 触发方式 | 首次进入页面或快速滑动时峰值过高 | 多次进出页面后阶梯式增长 |
| 主要证据 | 宽高、`config`、`allocationByteCount` 超出显示需求 | Heap Dump 中退出页面仍有 Bitmap / ImageView / Activity 引用链 |
| 优先工具 | 图片加载入口日志、Memory Profiler、`dumpsys meminfo` | LeakCanary、Heap Dump、页面生命周期回放 |
| 修复动作 | 采样解码、尺寸上限、低端机降规格、分块加载 | 取消请求、清理 View 引用、缩短缓存生命周期、校验复用池回收 |

图片入口建议记录四个字段：原始尺寸、目标显示尺寸、Bitmap 配置和 `allocationByteCount`。只记录文件大小没有用，JPEG / WebP 压缩文件很小，解码后的像素内存仍可能很大。

下面这段代码用于给图片解码入口补充预算日志。重点看 `allocationByteCount` 和目标尺寸的对比，不把日志当成修复手段。

```kotlin
fun Bitmap.reportBitmapBudget(
    scene: String,
    targetWidth: Int,
    targetHeight: Int,
    warnBytes: Long
) {
    val bytes = allocationByteCount.toLong()
    if (bytes >= warnBytes) {
        Log.w(
            "BitmapBudget",
            "scene=$scene bitmap=${width}x$height config=$config " +
                "target=${targetWidth}x$targetHeight bytes=$bytes"
        )
    }
}
```

这段日志只适合开发包、灰度包或采样用户。线上全量记录会增加 I/O 和隐私风险，栈信息也要脱敏。进入治理阶段后，阈值不要写成一个全局常量，要按页面类型、设备内存档位和图片角色拆开：头像、缩略图、长图预览、高清查看器不应该共用同一条线。

修复顺序建议按收益和风险排序：先修明显超出显示尺寸的大图，再修页面退出后仍存活的 Bitmap，后处理复用池策略。`inBitmap` 复用能降低反复分配，但复用池本身也会保留内存；没有命中率数据时扩大复用池，可能把峰值问题改成常驻占用问题。

## Native 内存泄漏排查案例：Java Heap 稳定时看 Native Heap 和匿名映射

[已验证: 官方文档, source.android.com/docs/core/tests/debug/native-memory]
[已验证: 官方文档, perfetto.dev/docs/data-sources/native-heap-profiler]
[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/Debug.java]
[结构参考: Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md]

Native 内存泄漏常见于音视频 SDK、地图 SDK、图片库、加密库和自研 JNI 模块。典型现象是 Java Heap 曲线稳定，PSS 或 Native Heap 随场景次数增长；重启进程后恢复，清理 Java 缓存没有效果。

排查时先确认增长口径，再抓分配栈。`dumpsys meminfo <pid>` 可以看 Native Heap、Dalvik Heap、Graphics、Stack、Code 等分类；`/proc/<pid>/smaps` 可以进一步确认增长区域是 `[anon:libc_malloc]`、`[anon:scudo:*]`、so 私有脏页，还是图形缓冲。分类对了，工具才选得对。

常用排查路径分成四步：

1. **复现场景**：固定一次业务路径，例如“进入预览 → 拍照 → 退出”重复 10 轮，每轮记录 PSS、Native Heap、Graphics 和线程数。
2. **区分来源**：Native Heap 增长优先采 heapprofd；Graphics / dma-buf 增长回到图片、Surface、纹理释放；so 私有脏页异常看库装载和初始化写入。
3. **抓调用栈**：Android 10 及以上优先用 heapprofd。Perfetto 文档说明 heapprofd 会跟踪指定时间窗口内的堆分配和释放，并把内存归因到调用栈。
4. **回到所有权**：找到调用栈后检查 JNI handle、`malloc/free` 配对、C++ 对象析构、SDK `release()` 时机，以及 Java 层对象是否还持有 native 句柄。

Native 泄漏修复不建议一开始就使用 Hook。参考书里把 Native Hook、PLT Hook、Inline Hook 放在排查方案中，适合做专项工具或内部平台；日常业务排查优先用系统工具。Hook 会引入兼容性和稳定性成本，尤其是线上环境。

下面这组命令用于把“哪类内存在涨”先确认下来。重点看趋势，不用单次快照下结论。

```bash
# 记录进程级分类，适合对比每轮操作后的 Native Heap / Graphics / PSS
adb shell dumpsys meminfo <package_or_pid>

# 保存 VMA 明细，适合确认增长来自 libc malloc、scudo、mmap、so 映射还是图形缓冲
adb shell cat /proc/<pid>/smaps > smaps-after-round-10.txt

# 采集 Native Heap 分配画像，具体配置按 Perfetto heapprofd 文档生成
adb shell perfetto -c heapprofd-config.pbtxt -o /data/misc/perfetto-traces/native.pb
```

这些命令只能确认方向。定位到某条 native 分配栈以后，还要回到业务生命周期：对象在哪个 Java API 创建、谁负责释放、异常路径是否跳过释放、页面退出和进程后台时是否都能走到清理逻辑。只补一个 `free()` 往往不够，资源所有权不清楚时，同一类泄漏会换一个入口再出现。

一个安全的修复模板是把 native 资源封装成显式生命周期对象：创建后只通过一个 owner 持有，页面退出、任务取消、异常失败都进入同一个 `close()` / `release()` 路径；测试用例把同一场景重复执行多轮，并断言 Native Heap 在冷却窗口后回到基线附近。

## 大型 App 内存预算管理：把预算分给场景和团队

[已验证: 官方文档, developer.android.com/topic/performance/memory]
[已验证: 官方文档, developer.android.com/studio/profile/memory-profiler]
[已验证: 官方文档, developer.android.com/studio/profile/capture-heap-dump]
[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]
[结构参考: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md]

大型 App 的内存问题很少由单个模块独立造成。首页框架、图片库、Feed、WebView、地图、直播、IM、广告 SDK、埋点 SDK 都会申请缓存和线程。每个团队只看自己的模块，单项都合理，合在一个进程里仍可能超过设备承受范围。

预算管理要按进程、设备档位和场景组合拆开，不能只设“全 App 一个阈值”。

| 维度 | 预算口径 | 失败信号 |
| --- | --- | --- |
| 设备档位 | 按 `memoryClass`、系统可用内存、低内存设备标记分组 | 低端机 OOM、后台保活下降、切回重启 |
| 进程角色 | 主进程、推送进程、WebView / 渲染进程、工具进程分开看 | 子进程异常放大、主进程被附带拖高 |
| 场景窗口 | 启动、首页首屏、Feed 连续滑动、详情页、拍摄/播放、后台 5 分钟 | 峰值过高、退出不回落、版本回归 |
| 内存类型 | Java Heap、Native Heap、Graphics、Code、Stack、PSS 分列 | 只看总量导致归因错误 |

预算表要服务排查，不是做展示。每个场景至少保留三类数据：基线版本、当前版本、变更模块。这样才能把“这个版本 PSS 多了 40 MB”变成“图片缓存多 18 MB、直播 SDK Native Heap 多 12 MB、线程栈多 6 MB”。如果没有拆分口径，评审会上只能互相猜。

[自动发现] 预算应接入发版门禁：灰度包采样记录关键场景的 P50 / P90 / P99，超过阈值时阻断发版或要求模块 owner 给出解释。阈值要保留机型维度，不能把高端机的结果拿去代表低端机。Android Studio Memory Profiler 适合单机定位；线上侧更适合采样 PSS、Java Heap、Native Heap、OOM 前兆和场景标签。完整监控设计先以 23.7 节为准，26.3 成稿后再恢复正式引用。

团队看板至少需要保留这些字段。

| 字段 | 含义 |
| --- | --- |
| `scene` | 启动、首页、Feed 滑动、详情、拍摄、播放、后台等业务场景 |
| `device_tier` | low / mid / high，规则由内存、SoC、系统版本共同决定 |
| `process` | 主进程或具体子进程名 |
| `java_heap_mb` | Java Heap 已用量，用于判断对象分配和缓存压力 |
| `native_heap_mb` | Native Heap，用于识别 JNI、SDK、图片和 allocator 压力 |
| `graphics_mb` | 图形缓冲和纹理相关占用，用于识别图片、Surface、视频问题 |
| `pss_mb` | 按比例分摊后的进程总体内存，用于线上趋势和保活风险判断 |
| `version` | 版本号、灰度批次或 commit 区间 |
| `owner` | 超预算时负责解释和修复的模块 |

预算执行有三个动作：新增大缓存必须声明场景和上限；引入 SDK 必须提供内存基线；灰度阶段发现超预算，要能回滚开关或降级能力。单纯要求“少占内存”没有操作性，给出场景、数据、owner 和回滚路径，才能把问题持续压回预算线内。

## 复盘模板：让每个内存问题变成下一次排查入口

[自动发现]
[来源: metadata/source-index.json 中 KOOM / OOM monitoring 相关素材索引]
[已验证: 官方文档, developer.android.com/topic/performance/memory]

内存问题修完后要留下结构化记录。下一次出现同类曲线时，团队应该能从旧案例里复用排查路径，而不是重新猜一遍。

每个案例至少保留这些信息：

- **现象**：用户场景、机型、系统版本、前后台状态、是否与版本发布相关。
- **指标**：PSS、Java Heap、Native Heap、Graphics、GC 频率、OOM / LMK 记录，注明采样时间和样本量。
- **证据**：Heap Dump、heapprofd trace、`dumpsys meminfo`、smaps、图片入口日志、泄漏引用链。
- **根因**：哪类对象或哪条 native 调用栈增长，为什么生命周期没有结束。
- **修复**：代码改动、配置改动、降级开关、回滚方案。
- **验证**：修复前后同场景对比，至少包含峰值、回落能力和多轮复现结果。
- **防复发**：新增监控、测试用例、预算门禁或代码评审规则。

案例的价值在证据完整度。没有复现路径、没有对比数据、没有修复后验证的记录，只能算故障流水账，下一次仍然要从头排查。
