

## [Task9 Deep Review] 15. Android 性能优化研究方法论 — 2026-07-17
- **类型**：数据支撑
- **位置**：§4.3 trace_processor SQL 实战部分
- **问题**：缺乏实际 trace_processor SQL 执行案例展示，仅有 SQL 查询模板
- **建议**：补充一个完整 trace_processor SQL 执行的实操案例，包括：
  1. 完整的 perfetto trace 采集命令（10秒内包含一次卡顿场景）
  2. trace_processor 启动和 SQL 执行的具体命令
  3. 执行结果的数据输出格式展示
  4. 结果如何与 Perfetto UI 中的 slice 数据对应

# 现有内容保持不变：
## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-07-17
- **类型**：版本差异覆盖
- **位置**：启动流程的版本差异（Android 12-16 关键变更）部分
- **问题**：提及 "首次启动时编译产物可能依赖云端下发的 profile" 但未详细说明在 SystemServer 启动流程中的具体机制
- **建议**：补充 Cloud Profiles 对 SystemServer 启动的影响机制，包括服务启动顺序、编译产物选择路径、首次启动与后续启动的性能差异

## [Task9 Deep Review] 14.19 Android CLI 与 Agent 化性能调试工作流 — 2026-07-17
- **类型**：工作流完整性
- **位置**：CI 工作流模板
- **问题**：提供的模板缺少关键前置条件，如 AVD 创建前的系统镜像下载确认、启动超时设置、权限初始化等
- **建议**：在 CI 模板中添加：
  ```bash
  # 确保系统镜像已下载
  android emulator list > "$OUT/emulator-list.txt" 2>&1 || echo "No emulators available"
  
  # 启动前检查
  android emulator start medium_phone --timeout 300 &
  
  # 等待设备就绪
  adb -s emulator-5554 wait-for-device
  adb -s emulator-5554 shell getprop sys.boot_completed
  ```

## [Task2A Gap Mining] 知识缺口挖掘记录 — 2026-07-17 23:25
- 已检查方向：ch01-ch26 全部章节覆盖范围、AOSP 核心服务、官方文档、研究素材、每日信息
- 合格缺口（≥14 分）：4 个，均已录入
  - 22.44 Compose 状态订阅与重组控制实战 (18 分)
  - 22.45 Compose LazyGrid 性能优化实战 (17 分)
  - 20.29 Crash 报告 SDK 架构选型与 tombstone 解析实战 (15 分)
  - 24.22 OkHttp 5.0 / Cronet / Ktor 网络引擎选型 (14 分)
- 不合格候选（<14 分）：SensorManager 性能（素材不足）、Backup API（冷门）、Companion Device Manager（已有覆盖）


## [Task14 参考书扫描] 6.1 存储性能 — 2026-07-18
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 48.md]
- **建议补充**：Linux readahead（预读）机制对 Android 文件 I/O 性能的影响。顺序文件读取时系统读取超出请求范围的数据并缓存至 Page Cache，加速后续读取。文件排列顺序直接影响预读命中率。对应 Android 资源加载场景（Resources/Assets）以及 Flutter 资源加载。
- **参考书覆盖深度**：概述

## [Task14 参考书扫描] 26.21 ASM 字节码插桩 — 2026-07-18
- **类型**：内容补充（开发工具提示）
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 48.md, 49.md]
- **建议补充**：ASM Bytecode Outline 插件的两种实用模式：(1) ASMified 模式可直接生成目标类的 ASM 构建代码；(2) Diff 模式展示相邻两次修改的字节码差异，帮助开发者快速定位插桩需要添加的 ASM 代码。AdviceAdapter 的 onMethodEnter()/onMethodExit() 方法级插桩模式，含 timeLocalIndex 局部变量槽位管理实践。
- **参考书覆盖深度**：中等

## [Task14 参考书扫描] 26.27 Facebook Profilo PLT Hook — 2026-07-18
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 51.md]
- **建议补充**：PLT Hook 实战模式集合：(1) Hook libc.so 的 write/__write_chk 方法捕获 ATrace 日志输出；(2) Hook Socket 相关函数（connect/sendto/recvfrom）实现网络请求监控；(3) Hook pthread_create 获取线程创建堆栈。这些是 Matrix/Profilo 框架的核心技术路线在实践中的具体落地方式。
- **参考书覆盖深度**：中等

## [Task14 参考书扫描] 8.3 启动优化 — 2026-07-18
- **类型**：版本更新
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 51.md]
- **过时内容**：通过 -Xverify:none 关闭 ART class verify 以提升启动速度（参考书所述实践）
- **建议更新至**：Android 17 中 ART 已采用 Boot Image 预验证 + Cloud Profiles 体系，class verify bypass 技巧的历史适用性和现代替代方案应明确标注。该技巧在 Android 12+ 已逐步失效，仅作为历史演进参考。

## [Task2A Gap Mining] 知识缺口挖掘记录 — 2026-07-18 11:04
- 已检查方向：ch01-ch26 全部章节覆盖范围、AOSP 核心服务、官方文档、研究素材、每日信息、Clippings 三本参考书知识点对照
- 候选缺口评估：5 个
  - ✅ 25.32 插件化包体积优化（14 分）— Clippings 参考书 2 篇专题 + AIW 零覆盖 + 中国市场高频需求 → 已录入
  - ❌ F2FS 文件系统性能与 SQLite I/O 交互（11 分）— 24.2/24.17/6.6/6.7 已充分覆盖，独立成节素材不足
  - ❌ CompOS On-device Compilation Server（12 分）— 1.7/21.11/21.12 已覆盖 ART 编译体系，外部素材有限
  - ❌ Compose Foundation 1.10 API 迁移性能（12 分）— 22.31/22.33/22.39/22.40 已覆盖核心迁移点，大部分是正确性非性能
  - ❌ Project Mainline / APEX 模块更新性能影响（12 分）— 性能影响对 app 开发者不直接可见，素材中等但缺乏深度
- 合格缺口（≥14 分）：1 个，已录入

## [Task14 参考书扫描] ch20 — 2026-07-18
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - ANR 治理实践.md]
- **建议补充**：title: "Android 应用稳定性剖析与优化 - ANR 治理实践"；ANR（Application Not Responding，应用无响应）是 Android 应用中最常见的稳定性问题之一。当应用在规定时间内无法响应用户输入或系统事件时，系统会弹出 ANR 对话框，严重影响用户体验和应用留存。；1. **用户体验下降**：应用卡顿、无响应，用户流失；Android 17 中的 ANR 机制
- **参考书覆盖深度**：结构索引，不搬运原文

## [Task14 参考书扫描] ch20 — 2026-07-18
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - ART 堆内存分布与黑科技扩量：拯救 OOM 的利器.md]
- **建议补充**：title: "Android 应用稳定性剖析与优化 - Pika - 掘金小册"；ART 堆内存分布与黑科技扩量：拯救 OOM 的利器
- **参考书覆盖深度**：结构索引，不搬运原文

## [Task14 参考书扫描] ch20 — 2026-07-18
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - ASM 与字节码插桩：改写字节码的“神器”.md]
- **建议补充**：title: "Android 应用稳定性剖析与优化 - Pika - 掘金小册"；我们日常 Android 开发接触的 **.java 或.kt** 文件，在经过编译之后，都会生成 **.class** 文件，这个也是我们常说的字节码文件，虽然在 Android 构建过程中，会把.class 文件进行进一步聚合，形成.dex 文件。；针对 Class 文件本身的处理技术有很多，比如 ASM、Javassist 等，本篇会以当前最热门的、性能较高的 ASM 工具作为讲解。通过学习本篇，你将了解到 ASM tree API 的简单使用以及通过 ASM 完成一些较为复杂的任务。
- **参考书覆盖深度**：结构索引，不搬运原文

## [Task14 参考书扫描] ch20 — 2026-07-18
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - Android.bp 文件与符号表：如何才能找到函数符号？.md]
- **建议补充**：title: "Android 应用稳定性剖析与优化 - Pika - 掘金小册"；我们 Android 应用开发，日常可能跟 Android 系统打交道的机会并不多，但是我们也会经常接触到 Android 系统源码，此时我们也会发现，Android 系统中有着大部分 C/C++ 代码，同时 Android 系统内部的子模块众多，一个 and；在我们用 Ninja 构建一个大型项目的时候，一般需要先编写 Ninja Build 文件（通常是以.ninja 为后缀的文件），指定构建规则，然后在命令行中启动 Ninja 程序，Ninja 程序会根据配置文件中的构建规则生成指定的目标文件。；但是，这个 Ninja 构建的配置文件有点过于复杂了，同时上手成本也很高，也不太适合直接构建多模块场景，此时 `Android.bp` 文件出现了，通过编写 Android.bp 文件包含了源文件和依赖关系的信息，以及如何编译成目标文件的信息，最终通过 Nin
- **参考书覆盖深度**：结构索引，不搬运原文

## [Task14 参考书扫描] ch20 — 2026-07-19
- **类型**：现有章节参考/案例候选（章节冻结：不新增章节）
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - Binder 通信监控：如何监控每一次 Binder 传输？.md]
- **建议补充**：title: "Android 应用稳定性剖析与优化 - Pika - 掘金小册"；Binder 通信监控：如何监控每一次 Binder 传输？
- **参考书覆盖深度**：结构索引，不搬运原文

## [Task14 参考书扫描] ch20 — 2026-07-19
- **类型**：现有章节参考/案例候选（章节冻结：不新增章节）
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - Binder 通信过程：客户端视角领略 Binder.md]
- **建议补充**：title: "Android 应用稳定性剖析与优化 - Pika - 掘金小册"；Binder 通信过程：客户端视角领略 Binder
- **参考书覆盖深度**：结构索引，不搬运原文

## [Task14 参考书扫描] ch20 — 2026-07-19
- **类型**：现有章节参考/案例候选（章节冻结：不新增章节）
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - ELF 文件与 readelf & objdump ：了解 ELF 格式与解析工具.md]
- **建议补充**：title: "Android 应用稳定性剖析与优化 - Pika - 掘金小册"；因为 Android 系统是基于 Linux 内核的，作为 Linux 主要的文件格式的 ELF，它被运用在很多地方，比如与我们稳定性相关的.so 文件，它本质就是一个 ELF 文件格式。ELF 解析被广泛运用在很多方面，比如 so 动态加载、dlsym 绕过；通常，在我们 Android 开发中，readelf 工具随着 ndk 的下载，就集成在 ndk 工具包了。我们可以通过以下路径，去找到不同架构里面的 readelf 工具，比如我电脑中的路径如下：；/AndroidSdk/ndk/21.0.6113669/toolchains/aarch64-linux-android-4.9/prebuilt/darwin-x86_64/bin/aarch64-linux-android-readelf
- **参考书覆盖深度**：结构索引，不搬运原文

## [Task14 参考书扫描] ch20 — 2026-07-19
- **类型**：现有章节参考/案例候选（章节冻结：不新增章节）
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - Java Crash 分析与监控原理.md]
- **建议补充**：title: "Android 应用稳定性剖析与优化 - Java Crash 分析与监控原理"；source: "综合自Java Crash监控章节"；在 Android Java 层，异常分为两大类别：；特殊处理**：在 Android 17 中，可通过"堆扩量"技术部分恢复
- **参考书覆盖深度**：结构索引，不搬运原文

## [Task14 参考书扫描] ch20 — 2026-07-20
- **类型**：现有章节参考/案例候选（章节冻结：不新增章节）
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - Java Crash 监控：实现自定义 Crash 处理器.md]
- **建议补充**：title: "Android 应用稳定性剖析与优化 - Pika - 掘金小册"；但是随着技术发展，我们也衍生了各种各样的黑科技，能够让虚拟机错误变成一个可逆的过程，比如我们在发生 OutOfMemoryError 的时候，可以通过堆增量技术，把虚拟机的堆内存扩大，从而延长应用的在线时间并保持稳定。下文我们会讲到这个黑科技， **OOM 时；当我们 Android Java 层发生异常/错误的时候，如果不进行处理，会发生闪退，而这个行为是系统定义的，下面我们详细看一下 Android 的异常/错误处理过程。；当我们虚拟机运行时发生了异常，可以通过 `Thread::SetException` 在 Native 层的 Thread 设置一个异常标志。
- **参考书覆盖深度**：结构索引，不搬运原文

## [Task14 参考书扫描] ch20 — 2026-07-20
- **类型**：现有章节参考/案例候选（章节冻结：不新增章节）
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - Java 内存泄漏监控与 OOM：Java 内存泄漏如何定义？.md]
- **建议补充**：title: "Android 应用稳定性剖析与优化 - Pika - 掘金小册"；作为应用层开发者，我们日常最能接触到的，其实就是堆内存分配时发生的 OOM。比如当前堆内存不足时，我们再去分配一个较大的内存，就很有可能超过虚拟机设立的限制（256M/512M），此时就会走到 Heap 里面的 ThrowOutOfMemoryError。；在本篇中，我们将聚焦于引起 OOM 的因素之一—— `内存泄漏` ，学习内存泄漏监控原理与实战。；通常来说，Android 应用应当规范自己的虚拟机堆使用内存在 256M/512M 内，其他运行时过于频繁且消耗较大的内存，应当放到 Native 层里面，比如 Android 系统的 Bitmap。在 Android 7 后，就把 Bitmap 存储的 by
- **参考书覆盖深度**：结构索引，不搬运原文

## [Task14 参考书扫描] ch20 — 2026-07-20
- **类型**：现有章节参考/案例候选（章节冻结：不新增章节）
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - Java 堆栈：深入了解 Throwable.md]
- **建议补充**：title: "Android 应用稳定性剖析与优化 - Pika - 掘金小册"；ArtMethod 是 Java 中可执行类（Executable）在 Native 层的具体表现。；if (android_get_device_api_level() >= 30) {；当我们构建一个 Throwable 对象的时候，会在构造函数调用 fillInStackTrace 方法，通过 Native 层抓取堆栈。
- **参考书覆盖深度**：结构索引，不搬运原文

## [Task14 参考书扫描] ch20 — 2026-07-20
- **类型**：现有章节参考/案例候选（章节冻结：不新增章节）
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Backtrace：Native 堆栈信息获取.md]
- **建议补充**：title: "Android 应用稳定性剖析与优化 - Pika - 掘金小册"；前面我们已经讲完 APM 中 Native 稳定性中最重要的一环——信号监控，那么我们监控后，还需要做一件不可或缺的事情，就是 **记录当前的堆栈** 。；记录好稳定的堆栈，提供给业务同学排查，才是 APM 建设的本质工作。；在本篇中，我们将介绍几个 Native 堆栈获取的概念，同时也会学习到如何运用 unwind 的方式去实现 Native 堆栈的回溯。
- **参考书覆盖深度**：结构索引，不搬运原文
