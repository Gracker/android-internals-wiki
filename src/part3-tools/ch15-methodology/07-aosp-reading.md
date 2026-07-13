---
title: 07-aosp-reading
chapter: 15.07
status: "ready-for-review"
applicable_versions: Android 5 (API 21) - Android 17 (API 37)
tags: [methodology, metrics]
updated_by: openclaw-task2b
updated_date: 2026-05-23
---
title: "AOSP 代码阅读"
chapter: "15.7"
section: "15.7"
status: "ready-for-review"
drafted_date: "2026-04-04"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-14"
last_verified_against: "AOSP android-17.0.0_r1（frameworks/base/core/java/android/app、frameworks/base/services/core/java/com/android/server/am、frameworks/base/services/core/java/com/android/server/wm、system/core/libutils/include/utils/Trace.h、system/core/libcutils/include/cutils/trace.h、frameworks/native/services/surfaceflinger）"
confidence: medium
sources:
  - type: official
    path: "https://cs.android.com"
  - type: official
    path: "https://source.android.com/setup/contribute/code-search"
  - type: blog
    path: "https://mp.weixin.qq.com/s?__biz=MzI4NTk1NzYwNg==&mid=2247483668"
tags: ['aosp', 'code-reading', 'cs.android.com', 'methodology']
related_chapters: ["1.1", "2.4", "2.5", "13.1"]
pipeline_stage: "task2b_pending"
task6_state: "revisiting"
task9_state: "pending"
task9_result: "needs-rework"
task9_reviewed_date: "2026-05-23"
task2b_state: "fixed"
task2b_result: "fixed"
repaired_date: "2026-05-23"
repaired_by: "openclaw-task2b"
last_task2b_at: "2026-04-25T19:43:07+08:00"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-05-23"
task6_result: pass-light-edit
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-05-23T15:20:00+08:00"
last_task6_audit: "2026-05-22"
last_task6_at: "2026-05-23T16:13:21+08:00"
last_task6_review_log: "logs/review/2026-05-23-16-review.md"
review_round: 5
task9_review_notes: "2026-05-23 Task9 深度复审：needs-rework。P0 1 / P1 1 / P2 0；SurfaceFlinger Android 13-16 trace 宏版本边界与 Android 16 slice 名仍需修正。详见 logs/deep-review/2026-05-23-15-deep-review.md。"
last_task9_audit: "2026-05-23"
last_task9_review_log: "logs/deep-review/2026-05-23-15-deep-review.md"
last_task9_audit_log: "logs/deep-review/2026-05-23-11-audit.md"
---
---

# AOSP 代码阅读

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 AOSP 源码在线阅读工具：cs.android.com（Android Code Search）
- 🔹 关键目录结构：frameworks/base、frameworks/native、system/core、art
- 🔹 阅读技巧：从 Logcat 日志反查代码、从 Systrace tag 定位代码
- 🔹 性能相关的核心源码入口：ActivityThread、ViewRootImpl、Choreographer、SurfaceFlinger
- 🔹 如何高效追踪一个调用链（IDE 搜索 vs grep vs codesearch）

### 扩展（可选深入）

- 🔸 本地 AOSP 全量代码的下载与 IDE 配置
- 🔸 利用 git log/blame 追踪功能变更历史

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么需要学会读 AOSP 源码

当我们在 Perfetto 中看到一帧渲染耗时 32ms，或者从 Logcat 中发现一行陌生的 warning 日志时，最直接的问题往往是：这行日志从哪里打出来的？调用链是什么？系统能不能不这么做？

博客、文档、Stack Overflow 能帮我们回答"是什么"，但只有源码能回答"为什么"和"怎么改"。对于做性能优化的工程师来说，AOSP 源码阅读不是锦上添花的技能，而是定位根因的基本功。

AOSP 由几百个 Git 仓库通过 `repo` 工具拼接而成。传统的 GitHub 浏览方式在这里几乎不可用——我们无法像浏览一个普通开源项目那样在仓库之间跳转。面对几百万行代码，没有专门的工具和方法，很容易迷失。

本节的目标很实际：读完之后，我们拿到一行日志、一个 Trace 中的 tag，或者一个类名，能快速定位到对应的 AOSP 源码，理解它的上下文，追踪它的调用链。

## 在线代码浏览：cs.android.com

[已验证: 官方文档, source.android.com/setup/contribute/code-search]

Android Code Search（cs.android.com）是 Google 为 AOSP 专门构建的代码搜索和浏览工具，2019 年底正式上线。它解决了一个核心问题：AOSP 由数百个 Git 仓库组成，在 android.googlesource.com 上逐个仓库翻看效率极低，而且无法跨仓库搜索和跳转。

cs.android.com 将所有 AOSP 代码呈现在一个统一的视图中，与我们本地 checkout 出来的目录结构完全一致。搜索一个类名时，我们能直接看到它在整个 Android 系统中的定义、引用和调用者，不需要关心这个文件属于哪个底层 Git 仓库。

### 核心能力

**全文搜索**是入口。在搜索框中输入类名、函数名、变量名或任意关键字，即可获得全代码库的匹配结果。搜索支持正则表达式和文件类型过滤。

**交叉引用跳转**是最有价值的功能。当我们打开一个源文件时，每个标识符（类名、方法名、变量）都可以点击跳转到它的定义处或所有使用处。这就像在一个 IDE 中阅读代码——我们可以从 `Choreographer.doFrame()` 一路点击跳到 `ViewRootImpl.doTraversal()`，再到 `View.performDraw()`，沿着调用链一路深入，而不需要手动在仓库之间寻找文件。

**分支切换**允许我们在不同 Android 版本之间对比。左上角可以选择目标分支，比如 `android-17.0.0_r1` 或 `master`。如果某个类在不同版本中的行为不同，我们可以切到对应分支对比源码。并非所有分支都有完整的交叉引用信息，通常较新的稳定版本支持最好。

### 实操建议

几个让 cs.android.com 更好用的习惯：

第一，直接用 URL 导航。`cs.android.com/platform/frameworks/base/+/android-17.0.0_r1:core/java/android/view/Choreographer.java` 这样的链接可以直接打开指定文件。我们可以把这个 URL 模板保存为书签，只需要替换路径和分支即可。

第二，善用搜索语法。`Choreographer$` 匹配文件名以 Choreographer 结尾的文件；`f:Choreographer doFrame` 限定只在文件名包含 Choreographer 的文件中搜索 doFrame。这些高级语法能显著缩小搜索范围。

第三，当搜索结果太多时，优先选择 `frameworks/base` 和 `frameworks/native` 下的结果——这两个目录包含了绝大多数我们关心的 Framework 和系统服务代码。

[图：cs.android.com 搜索 Choreographer.doFrame 的截图，标注搜索框、结果列表和交叉引用跳转]

## AOSP 关键目录结构

[已验证: 官方文档, source.android.com/setup/contribute/code-search]

面对几百万行代码，知道该去哪个目录找，比知道怎么搜索更重要。AOSP 的顶层目录很多，但性能优化相关的工作主要集中在以下四个目录。

### frameworks/base — Java Framework 的核心

这是 Android Java Framework 的主目录，也是我们日常接触最多的目录。它包含了 App 开发者和系统开发者都频繁打交道的那些类。

性能分析中最常访问的几个子路径：

- `core/java/android/app/` — ActivityThread、Instrumentation、LoadedApk 等应用进程侧入口
- `core/java/android/view/` — ViewRootImpl、Choreographer、View、ViewGroup
- `core/java/android/os/` — Handler、Looper、Trace、Binder 相关
- `services/core/java/com/android/server/` — 系统服务总目录：ActivityManagerService、WindowManagerService、PowerManagerService 等
- `services/core/java/com/android/server/am/` — 进程、广播、服务、ANR 等 ActivityManager 相关实现
- `services/core/java/com/android/server/wm/` — ActivityTaskManager、WindowManager、Task/DisplayArea、窗口布局与转场动画
- `packages/SystemUI/` — 状态栏、通知面板、锁屏、快捷设置和系统 UI 动画
- `graphics/java/android/graphics/` — 渲染相关：Canvas、Bitmap、Paint、HardwareRenderer

分析应用进程内的启动、生命周期与渲染问题时，`core/java/android/view/` 和 `core/java/android/app/` 是最常进入的两个目录；涉及系统服务时，AMS / PMS / WMS 的公共入口在 `services/core/java/com/android/server/`，Activity 栈、Task、DisplayArea、窗口排版和转场动画要继续进入 `wm/` 包。

### frameworks/native — C++ 系统服务

这个目录包含用 C++ 实现的系统服务和底层库。对性能优化来说，最重要的子目录：

- `services/surfaceflinger/` — SurfaceFlinger 的完整实现，包括合成逻辑、HWC 交互、VSync 管理
- `libs/gui/` — BufferQueue、Surface、GraphicBuffer 等 GUI 底层组件
- `libs/ui/` — Display 相关的抽象
- `cmds/atrace/` — atrace 工具的实现，Systrace/Perfetto 的数据采集端

渲染管线深入分析时，`services/surfaceflinger/` 是必经之地。SurfaceFlinger 的合成策略、帧提交流程、VSync 分发逻辑都在这里。

### system/core — 系统启动和基础工具

这是 Android 系统最底层的组件目录：

- `init/` — init 进程，Android 系统启动后的第一个用户空间进程
- `adb/` — ADB daemon 和 client
- `logd/` — 系统日志守护进程
- `toolbox/` — 基础命令行工具

现代 AOSP 的部分基础组件已经出现 Rust 代码。遇到 `.rs` 文件时，先看同目录 `Android.bp` 里的 `rust_binary` / `rust_library`，再沿 JNI、Binder 或命令入口追调用关系。`system/core` 不能再按纯 C/C++ 目录处理。

做启动性能分析时，`init/` 目录尤其重要——它负责 early userspace 启动、解析 `init.rc`、拉起 zygote 和关键守护进程。进入 Framework 阶段后，zygote fork 出 `system_server`，再由 AMS/PMS/WMS 等系统服务继续推进开机流程；`BOOT_COMPLETED` / `LOCKED_BOOT_COMPLETED` 广播也发生在这个阶段。

### art — Android Runtime

ART 虚拟机的完整实现。这个目录结构比较独立和完整：

- `runtime/` — ART 运行时核心：GC、JIT、AOT 编译器、线程管理
- `compiler/` — dex2oat 编译器
- `libartbase/` — ART 基础数据结构
- `dex2oat/` — DEX 到 OAT 的编译入口

内存分析（GC 暂停、内存分配）和启动优化（dex2oat 编译策略）时需要深入这个目录。

### 速查表：性能问题对应的源码目录

| 性能场景 | 主要源码目录 |
|---------|------------|
| UI 卡顿 / 掉帧 | frameworks/base/core/java/android/view/ |
| VSync / 帧调度 | frameworks/base/core/java/android/view/Choreographer.java |
| SurfaceFlinger 合成 | frameworks/native/services/surfaceflinger/ |
| Activity / Window / 转场 | frameworks/base/services/core/java/com/android/server/wm/ |
| SystemUI 动画 / 通知 / 锁屏 | frameworks/base/packages/SystemUI/ |
| 应用启动 | frameworks/base/core/java/android/app/ActivityThread.java |
| 系统启动 | system/core/init/ |
| 内存管理 / GC | art/runtime/ |
| 输入事件分发 | frameworks/native/services/inputflinger/dispatcher/（C++ 分发核心） + frameworks/base/core/java/android/view/InputEventReceiver.java（Java 接收端） |
| Binder 通信 | frameworks/native/libs/binder/ |
| 功耗 / WakeLock | frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java |

[图：AOSP 目录结构树状图，标注性能相关的核心路径]

## 从日志反查代码：两条实用路径

拿到一行日志或一个 Trace tag，怎么找到对应的源码？这听起来简单，但如果没有系统的方法，很容易在海量代码中迷失。这里介绍两条最常用的定位路径。

### 路径一：从 Logcat 日志定位源码

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/view/Choreographer.java — Log tag 与日志文本源码位置]

Logcat 日志有一个经常被忽略的特性：每条日志都带着 tag。这个 tag 通常就是源码中 `Log.x()` 调用的第一个参数，而源码中的 tag 定义往往是类名或模块名的常量。

比如我们在 Logcat 中看到：

```
D/Choreographer: Skipping 2 frames!  The application may be doing too much work on its main thread.
```

`Choreographer` 就是 Log tag。我们在 cs.android.com 中搜索 `"Choreographer"` 并限定为字符串常量，就能直接定位到 `frameworks/base/core/java/android/view/Choreographer.java` 中打出这行日志的代码位置。

更系统的方法是关注日志中的关键字符串。比如 `"Skipping"` 和 `"too much work on its main thread"` 这段文字是硬编码的，直接在 cs.android.com 中搜索这段文字，就能精确命中。这种方法比搜索 tag 更精准，因为 tag 可能在多处定义，但具体的日志文本通常是唯一的。

实操中，我们总结出这样的工作流：

1. 从 Logcat 复制有疑问的日志行
2. 提取其中的特征字符串（越特殊越好，避免通用词）
3. 在 cs.android.com 中搜索这个字符串（用双引号包裹以精确匹配）
4. 找到对应的源码位置，分析上下文

另一个技巧是利用 Logcat 中的进程和线程信息。如果日志来自 `system_server` 进程，对应的代码通常在 `frameworks/base/services/` 目录下；如果来自 App 进程，通常在 `frameworks/base/core/` 下。

### 路径二：从 Systrace / Perfetto tag 定位源码

[已验证: AOSP android-17.0.0_r1, system/core/libutils/include/utils/Trace.h；system/core/libcutils/include/cutils/trace.h；frameworks/native/include/android/trace.h]

在 Perfetto 中，我们看到的每一个 slice 都有一个名字，比如 `Choreographer#doFrame`、`measure`、`layout`、`draw`、`queueBuffer` 等。这些名字不是 Perfetto 自动生成的，而是开发者在源码中主动埋点的结果。

Android 系统中有两种埋点方式：

**Java 层**使用 `android.os.Trace` 类：

```java
// frameworks/base/core/java/android/os/Trace.java
// @ AOSP android-17.0.0_r1
Trace.traceBegin(Trace.TRACE_TAG_VIEW, "measure");
// measure 相关代码省略。
Trace.traceEnd(Trace.TRACE_TAG_VIEW);
```

`traceBegin` 的第二个参数 `"measure"` 就是在 Perfetto 中显示的 slice 名字。当我们在 Perfetto 中看到 `measure` 这个 slice，就可以在 cs.android.com 中搜索 `"measure"` 并结合 `TRACE_TAG_VIEW` 上下文，找到对应的源码位置。

**Native 层**使用 `ATRACE_CALL()` 或 `ATRACE_NAME()` 宏。内部宏位于 `system/core/libutils/include/utils/Trace.h`，tag 常量在 `system/core/libcutils/include/cutils/trace.h`，NDK 公开入口则是 `frameworks/native/include/android/trace.h`。部分系统服务（如 SurfaceFlinger）在此基础上封装了专用宏族（`SFTRACE_NAME`、`SFTRACE_ASYNC_FOR_TRACK_BEGIN` 等），生成更丰富的 slice 信息。反查时需注意区分通用宏和服务专用宏。

```cpp
// frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp
// @ AOSP android-17.0.0_r1
// SurfaceFlinger 在 Android 16 使用自定义 SFTRACE_* 宏族
// SFTRACE_* 定义在 services/surfaceflinger/common/include/common/trace.h
void SurfaceFlinger::composite(const CompositeArgs& args) {
    // SFTRACE_NAME 把传入的 name 交给 ScopedTrace
    // Perfetto 中看到的 slice 是 "composite <vsyncId>"，不含类名
    SFTRACE_NAME(ftl::Concat(__func__, ' ', ftl::to_underlying(args.vsyncId)).c_str());
    // 异步 trace 用 SFTRACE_ASYNC_FOR_TRACK_BEGIN / END
    SFTRACE_ASYNC_FOR_TRACK_BEGIN("vsync", /* 其他参数省略 */);
    // 合成逻辑省略。
}
```

> **注意**：`ATRACE_CALL()` 展开为 `ATRACE_NAME(__FUNCTION__)`，只能拿到函数名（如 `composite`），不包含类名。SurfaceFlinger 在 Android 16 起使用自己的 `SFTRACE_*` 宏族（定义在 `services/surfaceflinger/common/include/common/trace.h`）。但 `SFTRACE_NAME` 本身只是把传入的 name 交给 `ScopedTrace`，不会自动补类名。`SurfaceFlinger::composite()` 传入的是 `ftl::Concat(__func__, ' ', ftl::to_underlying(vsyncId))`，`__func__` 为 `composite`，所以 Perfetto 中看到的 slice 名是 `composite <vsyncId>`，不是 `SurfaceFlinger::composite`。如需类名，调用点字符串必须显式提供。
>
> SurfaceFlinger trace 入口按版本拆开看：Android 12 的 `onMessageRefresh()` 使用 `ATRACE_CALL()`；Android 13/14 的 `composite()` 使用 `ATRACE_FORMAT("%s ...", __func__, vsyncId)`；Android 15 使用 `ATRACE_NAME(ftl::Concat(__func__, ' ', vsyncId).c_str())`；Android 16 才切到 `SFTRACE_*` 封装。不要把 Android 16 的宏族泛化到 Android 12+。

反查规则需要区分宏族。Perfetto 中看到的 slice 名来源取决于模块使用的宏：

- **通用模块**（`ATRACE_CALL()` / `ATRACE_NAME()`）：只含函数名（`composite`），不含类名
- **SurfaceFlinger**（`SFTRACE_NAME` / `SFTRACE_ASYNC_FOR_TRACK_BEGIN`）：可含类名 + vsyncId
- **自定义字符串**（`Trace.traceBegin()` / `ATRACE_BEGIN()`）：slice 名就是传入的字符串

查找步骤：先按 slice 名在 cs.android.com 搜索，确认对应的宏族（`ATRACE_*`、`SFTRACE_*`、`Trace.traceBegin` 等），再根据宏的展开方式找到源码位置。不要假设 slice 名的格式固定不变。

**异步 Trace** 要按 name + cookie 配对。Java 层搜索 `Trace.asyncTraceBegin()` / `Trace.asyncTraceEnd()`，公共 API 场景还会看到 `Trace.beginAsyncSection()` / `Trace.endAsyncSection()`；Native 层搜索 `ATRACE_ASYNC_BEGIN` / `ATRACE_ASYNC_END`。Perfetto 中这类 slice 可能跨线程、跨时间段出现，不能只按相邻 begin/end 读，要看同名事件和同一个 cookie。

Systrace/Perfetto 的 tag 体系中还有一个概念：tag 类别（`ATRACE_TAG`）。系统定义了几十个 tag 类别（如 `ATRACE_TAG_GRAPHICS`、`ATRACE_TAG_INPUT`、`ATRACE_TAG_VIEW`），只有在抓取时启用了对应的 tag，相关的 trace 事件才会被记录。如果我们在 Perfetto 中看不到预期的 slice，可能是因为对应的 tag 没有被启用。[已验证: AOSP android-17.0.0_r1, system/core/libcutils/include/cutils/trace.h 中 ATRACE_TAG 定义]

[图：Perfetto 中的 slice 名与 AOSP 源码中 traceBegin 调用的对应关系示意]

## 性能分析的核心源码入口

了解了目录结构和定位方法之后，我们来看看性能优化中最核心的几个源码入口。这些是几乎所有性能分析都会涉及的类和函数——知道它们在哪、做什么，能让我们在分析问题时不至于"大海捞针"。

### ActivityThread — 应用进程的起点

`frameworks/base/core/java/android/app/ActivityThread.java`

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/app/ActivityThread.java]

每一个 Android 应用进程都有一个 `ActivityThread` 实例，它是应用进程的主入口。`ActivityThread.main()` 是进程启动后执行的第一个方法，它初始化主线程的 Looper 和 Handler，然后进入消息循环。

性能分析中，我们需要关注的几个关键方法：

- `handleBindApplication()` — Application 创建和初始化，启动分析的核心
- `handleLaunchActivity()` / `performLaunchActivity()` — Activity 创建和生命周期回调
- `handleReceiver()` / `handleServiceArgs()` — 其他组件的创建和处理

应用启动耗时的根因分析，通常从 `handleBindApplication()` 和 `handleLaunchActivity()` 开始。我们可以在这两个方法中设置断点或添加 Trace tag，逐段分析哪个初始化步骤耗时最长。

### ViewRootImpl — View 系统的桥梁

`frameworks/base/core/java/android/view/ViewRootImpl.java`

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/view/ViewRootImpl.java]

`ViewRootImpl` 是 View 树与系统服务之间的桥梁。每个 Window 对应一个 `ViewRootImpl`，它负责把 View 树的绘制需求转化为实际的渲染指令，同时处理来自系统服务的输入事件分发。

性能分析中的关键入口：

- `doTraversal()` — 触发 measure/layout/draw 三步流程
- `performMeasure()` / `performLayout()` / `performDraw()` — 三步的具体执行
- `requestLayout()` — 标记需要重新布局，请求下一个 VSync

在 Perfetto 中，我们看到的 `traversal` slice 就对应 `doTraversal()` 方法。如果 traversal 耗时过长，我们可以在 `ViewRootImpl` 中看 `performMeasure()`、`performLayout()`、`performDraw()` 分别占了多少时间。

### Choreographer — 渲染时序的指挥家

`frameworks/base/core/java/android/view/Choreographer.java`

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/view/Choreographer.java]

`Choreographer` 是 Android 渲染管线的时序协调者。它接收 VSync 信号，按优先级调度回调。早期版本可按 Input → Animation → Traversal 三类理解；Android 16 当前源码还定义了 `CALLBACK_INSETS_ANIMATION` 和 `CALLBACK_COMMIT`，读者在阅读现代源码时应注意到完整的回调队列。本书第 2.4 节已经详细讲解了它的机制，这里只强调源码层面的入口。

性能分析中最常用的切入点：

- `doFrame()` — 每一帧的入口，按顺序执行 Input → Animation → Traversal 回调
- `scheduleFrameLocked()` — 请求 VSync 信号
- `postCallback()` / `postFrameCallback()` — 注册各类回调

当我们在 Perfetto 中看到 `Choreographer#doFrame` 的 slice 特别宽时，可以对照 `doFrame()` 方法中的回调执行顺序，判断是 Input 处理慢、动画计算慢、还是 Traversal（measure/layout/draw）慢。

### SurfaceFlinger — 系统级合成器

`frameworks/native/services/surfaceflinger/`

[已验证: AOSP android-17.0.0_r1, frameworks/native/services/surfaceflinger/]

SurfaceFlinger 是 Android 图形系统的核心服务，负责将各个 Layer 合成后提交给显示器。它是 C++ 实现的独立进程，代码结构与 Java Framework 有很大差异。

Android 16 上更稳的阅读入口是这条调用链：

- `SurfaceFlinger::composite()` — 一帧合成的主要入口，负责组织本轮 composition
- `CompositionEngine::present()` — 进入 CompositionEngine，按 display / output 准备提交
- `Output::prepareFrame()` / `Output::present()` — 为每个输出准备合成方式并提交
- `HWComposer::getDeviceCompositionChanges()` — 向 HWC 查询哪些 layer 可走 device composition，哪些要回退 client composition
- `HWComposer::presentAndGetReleaseFences()` — present 后取回 release fence，用于后续 buffer 生命周期管理

老版本资料里常见的 `composeSurfaces()`、`onMessageRefresh()`、`Layer::onDraw()` 不能直接当作 Android 16 的主入口。阅读旧文章时，把它们放进版本差异里看；查 android-17.0.0_r1 时，要从 `SurfaceFlinger::composite()` 往 `CompositionEngine` / `Output` / `HWComposer` 走。

| 资料里的入口 | Android 16 阅读方式 |
|---|---|
| `SurfaceFlinger::onMessageRefresh()` | 改看 `SurfaceFlinger::composite()` 及其调度上下文 |
| `SurfaceFlinger::composeSurfaces()` | 改看 `CompositionEngine::present()` 与 `Output` 相关实现 |
| `Layer::onDraw()` | 不作为 Android 16 合成入口；优先看 layer state 如何进入 Output composition |
| `HWComposer::validateDisplay()` / `presentDisplay()` | 改看 wrapper 方法 `getDeviceCompositionChanges()` / `presentAndGetReleaseFences()` |

本书第 2.6 节有更详细的 SurfaceFlinger 机制分析。

## 追踪调用链的四种方法

找到了入口函数之后，我们通常需要追踪一个完整的调用链——从用户操作到最终效果，中间经过了哪些函数，在哪个环节出了问题。这里介绍四种方法，各有适用场景。

### 方法一：cs.android.com 交叉引用

适合场景：快速了解一个函数的调用者和被调用者。

操作方式：在 cs.android.com 中打开目标函数的定义，点击函数名即可看到所有调用这个函数的位置（callers）和这个函数内部调用了哪些函数（callees）。

优势是不需要任何本地环境，打开浏览器就能用。缺点是对于多层调用链，需要逐层手动点击跳转，当调用层次深时效率较低。

### 方法二：本地 grep + ctags

适合场景：需要快速搜索某个字符串在整个代码库中的出现位置。

在本地 AOSP 源码目录下，`grep -rn "scheduleFrameLocked" frameworks/base/` 这样的命令可以列出所有包含目标字符串的文件和行号。配合 `ctags` 或 `cscope`（C/C++ 代码），可以在终端中实现类似 IDE 的跳转功能。

对于 Java 代码，`grep` 的效率已经很高了，因为 AOSP 的 Java 代码组织比较规范，类名和文件路径一一对应。

### 方法三：Android Studio / IDE 跳转

适合场景：需要深入追踪多层调用链。

在本地导入 AOSP 的 `frameworks/base` 目录到 Android Studio 后，可以使用 IDE 的 "Go to Definition"、"Find Usages"、"Call Hierarchy" 等功能。这是追踪深层调用链最高效的方式。

[自动发现] Android Studio 导入 AOSP 的一个实用技巧：不需要导入整个 AOSP，只需要导入 `frameworks/base` 和 `frameworks/native` 就能覆盖大多数性能分析需求。完整导入所有目录会导致 IDE 索引时间过长（可能数小时），而选择性导入可以把索引时间控制在可接受范围内。

三种方法的对比：

- **cs.android.com**：零成本，适合快速定位和轻量浏览，不适合追踪深层调用链
- **grep**：速度快，适合精确搜索，但无法自动追踪引用关系
- **IDE**：功能最强，适合深入分析，但需要本地代码和较长的初始化时间
- **AIDL / Binder 边界追踪**：适合从 App 进程跨到 system_server、SurfaceFlinger 或 vendor service 的问题

建议的策略是：先用 cs.android.com 快速定位到感兴趣的代码区域；遇到同进程深层调用链时切到本地 IDE；遇到 Binder 边界时，沿 AIDL 接口找到服务端实现，再回到 Perfetto 匹配 transaction 的 pid / tid。

### 方法四：跨 Binder 边界追踪 AIDL 实现

性能问题经常跨进程。App 里看到一次 `WindowManager`、`ActivityManager`、`PowerManager` 或 vendor service 调用时，Java 调用栈只能走到 Manager 或 Proxy，耗时可能发生在 system_server、SurfaceFlinger 或 HAL 进程。

可执行的追踪步骤：

1. 找接口定义。搜索 `IWindowSession.aidl`、`IActivityTaskManager.aidl`、`IPowerManager.aidl` 这类 `.aidl` 文件。Framework AIDL 常在 `frameworks/base/core/java/android/` 下的 `app`、`view`、`os` 等子包，模块化或 Stable AIDL 还可能在 `packages/modules/`、`hardware/interfaces/` 或 `aidl_api/` 快照目录。
2. 找服务端实现。Java 服务端通常搜索 `extends IXXX.Stub`，Native / NDK AIDL 则搜索 `BnXXX`、`BpXXX` 或 `ndk::BnCInterface`。如果找不到直接实现，再搜 `onTransact` 和 service registration。
3. 匹配运行现场。Perfetto 中看 `binder transaction` / `binder reply`，用 client pid/tid、server pid/tid 和 transaction 时间窗匹配调用链。这样可以判断时间花在客户端等待、system_server 执行、SurfaceFlinger 合成，还是 vendor service。
4. 回到源码读业务逻辑。确认服务端入口后，再用 cs.android.com 或 IDE 继续追内部调用。不要只停在生成的 Stub / Proxy；它们主要是跨进程胶水，根因通常在服务端实现类里。

这个方法能避免一个常见误判：App 主线程栈只显示“Binder 调用中”，就把问题归为 App 卡顿。很多场景里，App 主线程只是同步等待，需要看的线程在 system_server 或 SurfaceFlinger。

## 本地 AOSP 代码的获取与配置

[已验证: 官方文档, source.android.com/source/downloading]

对于需要频繁阅读和修改 AOSP 代码的工程师，搭建本地环境是值得投入的。虽然 cs.android.com 满足大部分阅读需求，但本地环境有以下不可替代的优势：

- 可以在 IDE 中使用完整的代码跳转和重构功能
- 可以编译和调试修改后的系统代码
- 可以用 `git log` 和 `git blame` 追踪代码变更历史

### 下载代码

[来源: obsidian/Personal-Knowlodge/source/build-android-12.md, 高爷原创]

国内下载 AOSP 源码推荐使用科大或清华的镜像站。基本步骤：

```bash
# 下载 repo 工具
mkdir ~/bin
PATH=~/bin:$PATH
curl -sSL 'https://gerrit-googlesource.proxy.ustclug.org/git-repo/+/master/repo?format=TEXT' | base64 -d > ~/bin/repo
chmod a+x ~/bin/repo

# 初始化仓库（以 android-17.0.0_r1 为例）
mkdir AOSP && cd AOSP
repo init -u https://mirrors.ustc.edu.cn/aosp/platform/manifest -b android-17.0.0_r1

# 同步代码（建议使用 -j 参数控制并发数）
repo sync -j8
```

完整下载需要约 100GB 磁盘空间和数小时时间。如果只是阅读而非编译，可以只同步特定目录来节省时间和空间。

### IDE 配置建议

对于 Java 代码阅读，Android Studio 是最佳选择。不需要编译整个 AOSP，只需要：

1. 用 Android Studio 打开 `frameworks/base` 目录
2. 等待索引完成（约 10-30 分钟，取决于机器配置）
3. 如果需要查看 native 代码的 Java 调用，同时导入 `frameworks/native`

对于 C++ 代码（如 SurfaceFlinger），CLion 配合 CMakeLists.txt 效果更好。但由于 AOSP 使用 Soong 构建系统，CLion 的自动补全可能不完美，需要借助 `compile_commands.json` 来辅助配置。

如果只是偶尔查看，不需要完整的 IDE 配置，`vim` + `ctags` + `cscope` 的组合在终端中也能提供基本的代码跳转功能。

## 利用 Git 追踪代码变更历史

[来源: obsidian/Personal-Knowlodge/source/2026-03-06_wechat_思考_学习源码的三重境界.md, 芦半山]

阅读静态代码只能理解"现在是这样"，但很多设计决策只有看历史才能理解"为什么变成这样"。AOSP 的每个目录都是独立的 Git 仓库，我们可以用 Git 工具来追踪变更。

### git log — 了解功能的演进

在目标文件所在的 Git 仓库中，`git log --follow -p path/to/Choreographer.java` 会列出这个文件的完整修改历史，包括每次改动的 diff。通过阅读 commit message 和 diff，我们可以理解一个功能是如何一步步演变的。

### git blame — 定位特定代码的来源

当我们看到一行让人困惑的代码，想知道是谁在什么时候、因为什么原因加的，`git blame` 是最快的工具：

```bash
cd frameworks/base
git blame core/java/android/view/Choreographer.java | grep "scheduleVsync"
```

这会显示每一行代码最近一次由哪个 commit 修改，以及提交者和时间。

### Gerrit Code Review — 理解设计意图

[已验证: 官方文档, android-review.googlesource.com]

这是最容易被忽略但最有价值的工具。AOSP 的所有改动都经过 Gerrit Code Review，每个 commit 都有对应的 review 页面，上面有代码作者的 commit message，以及 Google 内部工程师的 review 讨论和意见。

从 `git log` 中获取 commit hash 后，访问 `https://android-review.googlesource.com/q/<commit-hash>` 就能看到完整的 review 记录。这里的讨论往往能揭示 commit message 中没有写明的设计动机和权衡考量。

在实际操作中，`git blame` 定位 → `git log` 查看详情 → Gerrit 阅读 review 讨论这三步组合，是理解一段代码"为什么这样设计"的最有效路径。比在博客中猜测设计意图要可靠得多。

## 常见问题与误区

**"读源码要先读完再动手"**

这是新手最常见的误区。AOSP 有几百万行代码，没有人能"读完"。正确的方式是带着问题读：遇到了一个具体问题，从日志或 Trace 出发，定位到相关代码，读通这一条调用链就够了。随着解决的问题越来越多，我们对代码的理解会自然扩展。

**"cs.android.com 够用了，不需要本地代码"**

如果只是偶尔查一两个函数，cs.android.com 基本够用。但当需要追踪深层调用链、对比多个版本的差异、或者理解一个功能的设计演进时，本地代码 + IDE + git 工具的组合效率要高得多。建议至少搭建一次本地环境，哪怕只是 `frameworks/base` 一个目录。

**"AOSP 代码太复杂，不适合应用开发者"**

这种想法会让应用开发者永远停留在"用 API"的层面。阅读 AOSP 中 `frameworks/base/core/java/android/view/` 和 `frameworks/base/core/java/android/app/` 下的代码，能帮助应用开发者理解系统在做什么，从而写出更高效的代码。比如理解了 `Choreographer` 的 VSync 申请机制，就知道为什么在一个 VSync 周期内多次 `invalidate()` 只会触发一次 `doFrame()`。

**"grep 搜索就够了，不需要专门工具"**

`grep` 能搜到内容，但它无法展示代码的引用关系和调用层次。当我们需要理解"谁调用了这个函数"或"这个函数调用了哪些函数"时，cs.android.com 的交叉引用或 IDE 的 Call Hierarchy 功能效率要高一个数量级。

## 参考资料

- AOSP Code Search: https://cs.android.com
- Code Search 官方文档: https://source.android.com/setup/contribute/code-search
- AOSP Gerrit Code Review: https://android-review.googlesource.com
- AOSP 源码下载指南: https://source.android.com/source/downloading
- 芦半山《学习源码的三重境界》: https://mp.weixin.qq.com/s?__biz=MzI4NTk1NzYwNg==&mid=2247483668
- Systrace Tag 含义参考: https://wizzie.top/Blog/2021/03/09/2021/210309_android_systraceTAG/
- AOSP Trace.java 源码: frameworks/base/core/java/android/os/Trace.java
- AOSP Trace.h (libutils 内部宏): system/core/libutils/include/utils/Trace.h
- AOSP cutils trace tag 定义: system/core/libcutils/include/cutils/trace.h
- NDK trace 公开头文件: frameworks/native/include/android/trace.h
