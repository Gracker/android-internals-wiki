---
title: "内存优化案例集"
chapter: "23.8"
section: "23.8"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-01"
last_verified_against: "AOSP android-17.0.0_r1 + Android Developers memory/profileable docs + Perfetto docs + Source Android native memory docs + Clippings/Android 性能优化 | 2026-08-01 rework: cleared pending-verification-marker (待验证→尚未坐实) + thin-source-marking (补 4 处内联 [来源:] 标记 + 扩充 frontmatter sources 至 10 条)"
confidence: medium
task2b_result: fixed-lite
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
pipeline_stage: ready-to-publish
last_rework_at: "2026-08-01T17:35:29+08:00"
last_rework_run_id: "20260801-173529-rework-7874270a"
rework_notes: "2026-08-01 rework：解决 2 个启发式 quality_flag。pending-verification-marker：§内存案例复盘模板末句 '待验证的解释' 改为 '尚未坐实的解释'（消除误触发词，语义不变）。thin-source-marking：frontmatter sources 从 1 条扩充至 10 条（映射既有参考资料），并在 Bitmap native heap 边界、getAllocationByteCount 源码注释、heapprofd 适用边界、profileable manifest 四处补内联 [来源:] 标记（共 4 处，≥2 阈值）。章节本身已是 finalized + ready-to-publish，本次为启发式标记清除，不改技术结论。"
last_task2b_lite_at: "2026-07-05"
drafted_date: "2026-05-14"
drafted_by: openclaw-task2a
polish_count: 0
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/memory"
  - type: official
    path: "https://developer.android.com/topic/performance/graphics/manage-memory"
  - type: official
    path: "https://developer.android.com/topic/performance/graphics/load-bitmap"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/Bitmap"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/Bitmap.java"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/native-heap-profiler"
  - type: official
    path: "https://perfetto.dev/docs/reference/heap_profile-cli"
  - type: official
    path: "https://developer.android.com/guide/topics/manifest/profileable-element"
  - type: official
    path: "https://developer.android.com/tools/dumpsys"
  - type: clipping
    path: "货拉拉司机 Android 端内存治理实践（本地归档 Cubox）"
tags: [case-study, memory, bitmap, native-memory, memory-budget]
related_chapters: ["23.1", "23.2", "23.3", "23.4", "23.7", "20.5"]
reviewed_by: openclaw-task6
reviewed_date: "2026-05-27"
task6_result: pass-light-edit
last_task6_review_log: logs/review/2026-05-27-21-review.md
task9_result: pass-tech-review
task9_reviewed_date: "2026-05-27"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-27T21:20:00+08:00"
last_task9_autofix_at: "2026-05-27"
last_task9_review_log: logs/deep-review/2026-05-27-21-deep-review.md
task9_review_notes: "2026-05-27 21:20 Task9 复审通过。P0/P1/P2=0;AOSP Bitmap/Debug、Android Developers Bitmap memory/load-bitmap、Perfetto heapprofd/profileable 边界复核通过;Task6 已通过且 queue 无 pending,自动晋升 finalized。"
last_task9_audit: 2026-07-10
last_task6_at: "2026-05-27T21:10:00+08:00"
last_task2b_at: "2026-05-27T20:50:00+08:00"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-15
last_task6_audit: 2026-07-05
---

# 内存优化案例集

## 案例应该回答什么

内存曲线上升只是现象。可复用的案例还要回答：哪个业务事件触发增长，增长属于哪类内存，哪些对象或调用栈仍然存活，谁拥有这些资源，修改后怎样证明问题已经消失。

平台锚点为 Android 17（API 37）和 AOSP `android-17.0.0_r1`。案例涉及 Android 10 引入的 heapprofd、Android 8.0 以后 Bitmap 像素数据的位置等历史边界时，会保留相应版本信息。ART 堆、Native Heap、GC 和线上采集机制分别见 23.1、23.2、23.3、23.4、23.7；OOM 分类见 20.5。

一份可信的内存复盘应形成下面这条证据链：

> 用户场景 → 可重复的触发动作 → 同口径的前后快照 → 对象引用链或 native 分配栈 → 资源所有权缺陷 → 最小修改 → 同场景复测 → 线上结果

其中，快照之间的相关性只能帮助提出假设。只有引用链、分配栈或明确的生命周期代码能够说明资源为何没有释放。

## 公开案例：货拉拉司机端内存治理

货拉拉团队公开的复盘提供了两类很有代表性的证据。下面的数据均为原文报告值，反映的是该 App 当时的版本、用户群和统计口径，不是其他项目可以直接采用的目标值。

- 治理前，OOM 设备崩溃率峰值为 `0.8‱`，约占整体崩溃率的 `20%`；线上内存触顶率为 `0.64%`。首页与车贴拍摄页是高频 OOM 页面。
- 治理后，OOM 设备崩溃率降到 `0.01‱`，线上内存触顶率降到 `0.01%`，核心页面和核心流程的 OOM 崩溃率降到 `0`。

这些结果只有结合排查过程才有参考价值。

### 首页弹窗：从业务事件找到泄漏引用链

原文先从 OOM 前的离线日志发现共同点：用户命中了大量新单推送弹窗。线下复现时，测试人员在首页每两秒触发一次弹窗；约八分钟、约 240 次展示后，Profiler 观察到内存上涨约 50 MB，且当时没有下降趋势。线上 OOM 样本中的弹窗展示次数超过 2000 次。

这组数据建立了“弹窗展示次数与内存增长相关”的假设，还不能单独证明泄漏。Heap Dump 的前后对比补上了对象证据：

- `float[]`、`SolverVariable[]`、`SolverVariable`、`ArrayRow` 等布局相关对象持续增加；
- 一条可疑引用链从 `SolverVariable[]` 到弹窗的 `mView`，再经过 `LifecycleRegistry.mObserverMap` 到常驻的 `MainActivity`；
- 代码审查发现 Dialog 初始化时注册了 Activity 的 Lifecycle 监听，却没有在 `dismiss` 时移除。

`MainActivity` 仍然存活，`LifecycleRegistry` 中的观察者也就仍然可达；观察者再保留旧 Dialog 和 View，GC 无法回收整棵对象图。修复是在弹窗结束时移除对应观察者，并用相同事件序列复测对象数量与内存回落。有效修复来自注册方、注销方和生命周期终点重新一致，代码行数并不能说明修复质量。

### 车贴拍摄：高占比 `byte[]` 指向高频分配

车贴拍摄页缺少清晰的业务日志线索。团队从 OOM 时采集的内存快照观察到，`byte[]` 占总体的比例超过 `90%`，主要由图像录制和处理类持有。线下拍摄没有复现 OOM，却复现了频繁的内存波动和 GC。

继续检查图像回调后发现，识别逻辑一秒接收多帧，部分录制对象既没有复用，也没有及时释放。团队用对象池减少录制对象的创建，并在灰度阶段确认该页面的 OOM 消失。

这里要区分两个结论：

- **原文事实**：快照中的 `byte[]` 占比、持有者、高频回调、线下 GC 现象以及灰度结果；
- **工程判断**：对象池是否适合某个新项目，仍要测池命中率、池容量、单对象大小和空闲时保留量。池本身也会延长对象寿命。

两个案例说明，同一条“内存上涨”告警可能对应长期可达对象，也可能对应高频分配与峰值压力。修复工具和验收指标不能混用。

## Bitmap 内存治理：区分尺寸、持有与图形资源

图片场景至少要区分三类问题：

| 类型 | 典型曲线 | 需要的证据 | 常见修改位置 |
| --- | --- | --- | --- |
| 解码尺寸过大 | 首次进入或处理原图时出现峰值 | 源图尺寸、目标尺寸、配置、已分配字节数、同一时刻的进程分类 | 解码入口、旋转/裁剪入口、图片加载请求 |
| 生命周期过长 | 多次进出页面后阶梯式增长 | 退出页面后的 Heap Dump、Bitmap/ImageView/页面引用链、缓存键与淘汰记录 | 请求取消、View 清理、回调注销、缓存策略 |
| Hardware Bitmap、纹理或 Surface 资源滞留 | Java Heap 变化有限，Graphics 或总体 PSS 增长 | `dumpsys meminfo` 分类、图形缓冲记录、Surface/纹理生命周期 | 渲染资源释放、图片加载配置、Surface 所有者 |

分类表用于选择下一项证据，不能仅凭曲线给问题定性。

### Android 17 上 Bitmap 的内存含义

Android Developers 的版本说明指出：Android 8.0（API 26）及以后，Bitmap 的像素数据位于 native heap。Android 17 的 AOSP `Bitmap.java` 还能看到更具体的关联方式：

- Java `Bitmap` 保存 `mNativePtr`；
- `registerNativeAllocation()` 使用 `NativeAllocationRegistry` 登记 native 对象与像素分配；
- 登记的像素大小来自 `getAllocationByteCount()`；
- `recycle()` 会进入 native 回收逻辑并更新相关登记。

这解释了为什么 Java 对象仍然可达时，相关 native 内存也可能继续留在进程中。但“API 26 以后像素在 native heap”不等于所有图片内存都会稳定显示在 `dumpsys meminfo` 的某一个栏目。Hardware Bitmap、图形缓冲、共享映射和厂商实现可能影响分类结果，应同时看对象证据、Graphics、Native Heap 与总体 PSS。

`getAllocationByteCount()` 比“宽 × 高 × 每像素字节数”更适合作为单个 Bitmap 的已分配容量。Android 17 源码注释明确说明：Bitmap 被 `inBitmap` 复用或手动重配置后，这个值可以大于 `getByteCount()`，并在该 Bitmap 生命周期内保持不变。因此，容量异常既可能来自当前解码尺寸，也可能来自复用了更大的存储。

下面的代码用于生成一条不含文件路径、URL 或业务标识的 Bitmap 观测记录。它只采集事实，不在基础函数里写统一告警阈值。

```kotlin
data class BitmapObservation(
    val role: String,
    val decodedWidth: Int,
    val decodedHeight: Int,
    val targetWidth: Int,
    val targetHeight: Int,
    val config: String,
    val allocationBytes: Long
)

fun Bitmap.toObservation(
    role: String,
    targetWidth: Int,
    targetHeight: Int
): BitmapObservation {
    require(role.isNotBlank())
    require(targetWidth > 0 && targetHeight > 0)

    return BitmapObservation(
        role = role,
        decodedWidth = width,
        decodedHeight = height,
        targetWidth = targetWidth,
        targetHeight = targetHeight,
        config = config?.name ?: "UNKNOWN",
        allocationBytes = allocationByteCount.toLong()
    )
}
```

调用方应使用有限枚举作为 `role`，例如缩略图、预览图、编辑输入，避免记录用户文件名。采样系统再按场景、设备档位和角色比较 `allocationBytes` 的分布；阈值应来自本项目的基线和风险预算，而不是写进这段采集代码。

### 大图问题的排查顺序

图片加载库通常会处理尺寸协商、缓存和复用，但业务传入原始尺寸、错误的目标尺寸或绕开加载库进行旋转时，仍可能创建大 Bitmap。按下面的顺序核对：

1. 记录源图宽高、方向信息、目标 View 尺寸、请求尺寸、Bitmap 配置和 `allocationByteCount()`。
2. 检查解码是否发生在目标尺寸已知之前。直接使用 `BitmapFactory` 时，可以先用 `inJustDecodeBounds` 读取边界，再计算合适的 `inSampleSize`；使用图片库时，应通过库的尺寸 API 表达目标，而不是再手写第二套缓存与复用逻辑。
3. 检查旋转、裁剪、圆角、模糊、压缩和上传预处理是否又创建了全尺寸中间 Bitmap。
4. 在动作前、峰值、页面退出和冷却后采集同口径数据，确认峰值下降且资源能够释放。

压缩文件大小不能代表解码内存。JPEG 或 WebP 文件可能很小，显示前仍要展开为像素数据。`ARGB_8888` 的常见估算是每像素四字节，但宽色域、`RGBA_F16`、Hardware Bitmap、行对齐和复用容量都会改变实际占用，验收时仍以观测值为准。

### 公开案例中的图片发送峰值

货拉拉复盘还记录了一个 Native 内存峰值案例：发送图片后容易发生 Native OOM；线下操作能看到发送前后的 Native 内存突增；内存信息把增长点指向大 Bitmap；代码检查发现旋转逻辑先把原图完整解码成 Bitmap。

这条链路支持“全尺寸解码造成峰值”的结论。修改时应把尺寸约束放在第一次像素分配之前：先读取边界和方向，按输出需求决定解码尺寸，再旋转或裁剪。若先完整解码再缩小，最终 Bitmap 虽然变小，峰值阶段的原图与中间结果仍可能同时存在。

验收不能只看操作结束后的平均值。至少要比较处理前基线、解码峰值、变换峰值、上传结束和页面退出后的回落；还要覆盖接近业务允许上限的输入尺寸和方向组合。

## Native 内存泄漏排查：先确认类别，再分析分配栈

Java Heap 稳定而 PSS 上升，不足以直接判定 Native Heap 泄漏。进程内存还可能增长在 Graphics、线程栈、文件映射、JIT/Code、共享内存或其他匿名映射中。

| 观察结果 | 下一项证据 | 不应直接得出的结论 |
| --- | --- | --- |
| `Native Heap` 的 allocated/PSS 随动作增加 | heapprofd、malloc debug、native 所有权代码 | 看到一次上涨就判定泄漏 |
| `Graphics` 或图形相关映射增加 | Surface、纹理、Hardware Bitmap、缓冲队列生命周期 | 归因给普通 `malloc` |
| `Stack` 与线程数一起增加 | 线程列表、创建栈、线程退出路径 | 只调整 Java 堆上限 |
| 文件私有脏页或匿名映射增加 | `smaps_rollup`/`smaps`、映射名称、库初始化路径 | 把所有 PSS 增长算入 Native Heap |
| Java Heap 增加且页面退出后对象仍可达 | ART Heap Dump 与 GC Root 引用链 | 使用 heapprofd 代替 Java 堆分析 |

`dumpsys meminfo`适合快速确认进程级分类；`/proc/<pid>/smaps_rollup`和 `smaps`用于查看映射级证据，但 adb shell 在量产设备上通常没有权限读取目标应用的这些文件。遇到权限拒绝，应记录工具条件并换用自有调试包、root 或 userdebug/eng 实验设备，不能把空结果解释成“没有增长”。

下面的脚本用于在一个检查点保存 `dumpsys meminfo`，并在权限允许时补充 `smaps_rollup`。把不同检查点写入不同目录，即可保留动作前、峰值和冷却后的原始输出。

```bash
#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 <package-name> <output-directory>" >&2
  exit 2
fi

package_name=$1
output_directory=$2
mkdir -p "$output_directory"

adb shell dumpsys meminfo "$package_name" \
  > "$output_directory/dumpsys-meminfo.txt"

pid=$(adb shell pidof -s "$package_name" | tr -d '\r')
if [[ -z "$pid" ]]; then
  echo "process is not running: $package_name" >&2
  exit 1
fi

if ! adb shell "cat /proc/$pid/smaps_rollup" \
  > "$output_directory/smaps-rollup.txt"; then
  echo "smaps_rollup is not readable in this device/build context" >&2
fi
```

每个检查点必须使用同一设备、系统版本、App 构建、账号数据和动作脚本。重复次数与冷却时长由场景的稳定性实验确定，并写进实验记录；没有测量依据时，不要固定成“十轮”或“后台五分钟”。

### heapprofd 的适用边界

heapprofd 从 Android 10 开始提供按调用栈归因的堆分配分析，默认跟踪 `malloc/free`、`new/delete` 等 native 分配。它记录的是采样时间窗内的分配与释放，因此更适合回答“哪些调用栈保留了多少 native 分配”，不能解释所有 Graphics、文件映射或自定义分配器占用。

设备与应用还要满足权限条件：

- debug Android build 可分析更广的进程集合，但关键系统服务仍可能受 SELinux 策略限制；
- 量产 user build 只允许分析 manifest 标记为 debuggable 或 profileable 的应用；
- `<profileable android:shell="true"/>` 允许 shell 侧的 Perfetto、simpleperf 等工具分析发布构建，且比 debuggable 构建更适合性能测量；
- 调用栈需要与被测构建严格匹配的符号文件。发布构建还要保留对应的 native 符号和 Java/Kotlin 映射文件。

Perfetto 官方推荐使用仓库中的 `tools/heap_profile` 脚本。下面的命令让进程名由调用参数传入，持续采集到用户中断；输出目录由官方脚本创建并在结束时打印。

```bash
#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <process-name>" >&2
  exit 2
fi

perfetto_checkout=${PERFETTO_CHECKOUT:?set PERFETTO_CHECKOUT to a Perfetto checkout}
process_name=$1

"$perfetto_checkout/tools/heap_profile" android -n "$process_name"
```

采集期间执行预先写好的业务动作，随后在终端中断采集。把脚本生成的 `raw-trace`载入 Perfetto UI，先比较动作前后仍存活的分配，再沿调用栈回到具体库和业务入口。采样间隔会影响开销与精度；只有出现 buffer overrun 等明确证据时，才按官方故障排查建议调整共享缓冲或采样间隔。

### 从分配栈回到资源所有权

一条增长调用栈只是分配入口。代码审查还要回答：

- native 句柄由谁创建，Java/Kotlin 层是否只有一个明确的所有者；
- `malloc/free`、`new/delete`、`NewGlobalRef/DeleteGlobalRef`是否配对；
- 正常完成、取消、超时、异常和页面销毁是否进入同一释放路径；
- C++ 析构是否会执行，是否存在跨线程引用、回调注册或 SDK 内部缓存；
- `close()`/`release()`是否允许重复调用，调用后是否禁止继续使用句柄；
- 修复后，仍存活分配的调用栈与字节数是否在同场景下回到稳定范围。

C++ 优先使用 RAII 容器和智能指针表达所有权；JNI 边界可以在 Java/Kotlin 层使用 `AutoCloseable`暴露显式生命周期，但 native 侧仍须防止重复释放和并发使用。若第三方 so 没有符号或释放 API，应把版本、厂商、复现输入和调用栈地址一起提交给供应方，同时准备关闭能力、减少并发或隔离进程等可逆方案。

Hook 型工具可以覆盖系统工具难以观察的场景，也会增加兼容性、递归分配和稳定性风险。应先在实验环境验证采集器本身的开销与正确性，再决定是否用于灰度或线上采样。

## 大型 App 内存预算：按进程、场景和设备管理

大型 App 常把图片、Feed、WebView、地图、音视频、广告和监控 SDK 放在同一进程。每个模块单独看都没有越界，组合场景仍可能出现峰值叠加。预算必须描述“什么环境、哪个进程、哪个检查点、哪类内存”，不能只设一个全局 MB 数。

| 维度 | 必须记录的上下文 | 用途 |
| --- | --- | --- |
| 平台与构建 | Android/API、AOSP 或设备构建指纹、App version/commit、ABI | 避免跨版本和跨二进制误比 |
| 设备档位 | 机型、物理内存、`memoryClass`、低内存设备标记、厂商 | 解释设备能力差异；`memoryClass`不是 PSS 总预算 |
| 进程 | 主进程、WebView/渲染进程、播放器或工具进程 | 防止只优化主进程而遗漏子进程 |
| 场景与检查点 | 输入数据、动作序列、前台/后台、基线、峰值、退出、冷却 | 区分峰值、常驻量和回落能力 |
| 内存类别 | Java Heap、Native Heap、Graphics、Stack、Code、总 PSS | 指导下一种分析工具 |
| 统计信息 | 样本量、P50/P90/P99、异常值规则、采集来源 | 说明结果的稳定性和可比性 |
| 责任与处置 | 模块、负责人、变更、开关、回滚或降级方案 | 超预算时能够执行决策 |

`ActivityManager.getMemoryClass()`给出应用堆级别的近似上限，不代表进程可以安全使用同等数量的 PSS，也不代表设备在当前压力下能长期保留该进程。预算需要同时参考历史稳定版本、目标设备上的实测分布、OOM/LMK 结果与业务峰值。

### 把公开案例写入预算记录

货拉拉案例可以拆成三条独立记录：

| 场景 | 触发动作 | 增长类别与证据 | 所有权或分配问题 | 验证重点 |
| --- | --- | --- | --- | --- |
| 首页常驻 | 重复展示并关闭新单弹窗 | Java 对象数量与 Heap Dump 引用链 | Lifecycle 观察者未移除，旧 Dialog/View 仍可达 | 观察者、Dialog 与布局对象不再按次数累积 |
| 车贴拍摄 | 相机帧进入录制与识别 | 快照中 `byte[]` 高占比，线下频繁 GC | 多帧回调持续创建录制对象，释放与复用不足 | 分配速率、GC、峰值及灰度 OOM |
| 图片发送 | 解码并旋转原图 | Native 内存峰值与大 Bitmap | 第一次解码前没有尺寸约束 | 解码/变换峰值、输入上限、退出回落 |

这三条记录不能合并成“图片模块增长”。它们的内存类别、根因和验收信号不同，合并后会丢失行动信息。

### 预算与发版门禁

预算值应从可比较的历史样本中建立。推荐流程如下：

1. 为关键场景固定设备档位、输入数据、动作脚本和检查点。
2. 用稳定版本建立基线，保存原始数据、样本量和采集工具版本。
3. 新版本在相同条件下比较分位数、峰值和退出后的残留量，并按内存类别归因。
4. 超过预先批准的预算时，由对应模块给出证据、修复、降级或例外说明；例外需要到期时间。
5. 灰度阶段继续观察 OOM、LMK、`ApplicationExitInfo`与场景内存分布，确认实验室结果能在目标用户群复现。

P50、P90、P99 是对样本分布的描述，不是天然的门禁线。样本量不足、机型混合、版本口径变化或采集触发偏差都会让分位数失真。看板至少要保留这些字段：

| 字段 | 含义 |
| --- | --- |
| `experiment_id` | 可追溯到动作脚本和原始证据的实验标识 |
| `platform_version` | Android/API 与设备构建信息 |
| `app_build` | App version、commit 或灰度批次 |
| `device_tier` | 有明确规则的设备档位 |
| `process_name` | 目标进程 |
| `scene` / `checkpoint` | 业务场景与采集检查点 |
| `metric_source` | `dumpsys meminfo`、应用 API、Perfetto 或其他来源 |
| `java_heap_bytes` | Java Heap 观测值及统一单位 |
| `native_heap_bytes` | Native Heap 观测值及统一单位 |
| `graphics_bytes` | 图形相关观测值及统一单位 |
| `total_pss_bytes` | 进程总体 PSS，明确换算方式 |
| `sample_count` | 对应分布的样本数 |
| `owner` / `decision` | 负责人和处置决定 |
| `rollback` | 开关、回滚或降级路径 |

新增缓存和 SDK 时，评审材料要说明常驻量、场景峰值、线程与子进程、清理 API、低内存回调行为以及关闭方案。上线后若只能看到总 PSS，而看不到版本、场景和进程，预算表也无法用于归因。

## 内存案例复盘模板

每次修复后保留下面的信息，后续同类曲线才能复用这次排查结果：

- **问题范围**：受影响版本、设备、ABI、进程、场景和用户影响。
- **现象口径**：OOM、LMK、PSS、Java Heap、Native Heap、Graphics、线程或 GC；写明来源、单位和采样时机。
- **复现条件**：输入数据、动作脚本、检查点、重复策略与冷却条件。
- **假设与反证**：每个假设对应什么证据，哪些观测已经排除。
- **对象或调用栈证据**：GC Root 引用链、heapprofd 栈、VMA、Surface/缓冲记录及符号版本。
- **资源所有权**：创建者、持有者、释放者，以及取消、异常和销毁路径。
- **修改内容**：代码、配置、缓存、尺寸约束或 SDK 版本，附风险和回滚方案。
- **离线验证**：同设备、同输入、同口径的修改前后数据，覆盖峰值与回落。
- **线上验证**：灰度样本量、目标指标、观察窗口及未改善时的处理条件。
- **防复发措施**：回归用例、采集点、预算项、代码审查规则与负责人。
- **负结果**：没有支持某个假设的实验也要保留，避免下次重复消耗时间。

复盘中要把观测与解释分开写。例如，“退出页面后 `Native Heap`仍高于动作前”是观测；“某 SDK 泄漏”是尚未坐实的解释。只有分配栈和所有权代码对得上，后者才可以升级为根因。

## 小结

内存治理需要用多种证据逐步缩小问题范围，万能阈值或单一工具无法覆盖所有类别：

- Bitmap 先区分解码尺寸、对象持有和图形资源，再决定看入口日志、Heap Dump 还是图形生命周期；
- Native 问题先用进程分类和映射证据确认增长位置，权限满足时再用 heapprofd 将保留分配归因到调用栈；
- 大型 App 的预算要绑定平台、设备、进程、场景、检查点和采集来源；
- 每个修复都要通过同场景复测与线上样本验证，原始数据和失败假设也应留档。

案例写得越具体，下一次排查越容易从已有证据继续，而不是重新猜测曲线含义。

## 参考资料

- [Android Developers：Manage your app's memory](https://developer.android.com/topic/performance/memory)
- [Android Developers：Managing Bitmap Memory](https://developer.android.com/topic/performance/graphics/manage-memory)
- [Android Developers：Loading Large Bitmaps Efficiently](https://developer.android.com/topic/performance/graphics/load-bitmap)
- [Android Developers：Bitmap API reference](https://developer.android.com/reference/android/graphics/Bitmap)
- [AOSP `android-17.0.0_r1`：`Bitmap.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/Bitmap.java)
- [Perfetto：Memory—Callstack-based Allocation Profiling](https://perfetto.dev/docs/data-sources/native-heap-profiler)
- [Perfetto：`heap_profile` command reference](https://perfetto.dev/docs/reference/heap_profile-cli)
- [Android Developers：`<profileable>` manifest element](https://developer.android.com/guide/topics/manifest/profileable-element)
- [Android Developers：`dumpsys` command](https://developer.android.com/tools/dumpsys)
