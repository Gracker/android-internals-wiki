# AIW 自动 Review 任务报告

## 一、目标发现结果
- 扫描范围：`src/part3-tools/ch14-other-tools/`
- 候选章节：
  1. `03-memory-tools.md` | 指定 review 章节
- 最终选择：`03-memory-tools.md`
- 选择理由：用户明确指定了此章节进行 review。
- 排除的高频原因：N/A

## 二、总体结论
- 总体技术评分：3.5/5
- 是否建议回炉：是（需要结构化修正）
- 主要风险：Perfetto Java 堆分析能力描述存在严重事实错误（误导读者以为 Perfetto 不能做 Java 引用链分析），部分底层工具（procrank、malloc debug）的使用权限前提未说清，容易导致读者在 User 版本生产设备上实战受挫。
- 评分理由：文章整体脉络清晰，工具定位准确。但存在 2 个 P1 级别的问题（Perfetto 能力描述错误，底层工具执行权限/环境限制未说明），按照规范，存在 1 条以上 P1，最高不超过 4.0 分；存在 2 条以上 P1，最高不超过 3.5 分。
- 闭环建议：强烈建议进入回炉队列，修正 Perfetto 部分的能力描述，并补充各个底层命令行工具的权限要求（Root / Userdebug）。
- 本轮 review 覆盖范围：LeakCanary、MAT、heapprofd、dumpsys meminfo、showmap/procrank/libmeminfo、malloc debug/hooks、HWASAN/MTE。
- 本轮未完成部分：无。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 4/5 | 0 |
| 原理链完整性 | 3.5/5 | 2 |
| 版本差异覆盖 | 3.5/5 | 2 |
| 知识盲区 | 4/5 | 1 |
| 数据/案例支撑 | 4/5 | 0 |
| 交叉引用一致性 | 5/5 | 0 |

## 四、P0 问题（事实错误）
（无 P0 问题）

## 五、P1 问题（重要缺失）
- [P1][版本差异覆盖][heapprofd：Native 堆的实时采样分析 -> 工作机制]
  - **原文问题**：“Java 分配模式从 Android 12 开始支持，监控 ART 虚拟机的对象分配。但需要注意，Java 模式展示的是分配的调用栈，而不是对象之间的引用关系——它无法替代 MAT 的引用链分析。”
  - **源码 / 一手资料锚点**：Perfetto 官方文档 (https://perfetto.dev/docs/data-sources/java-heap-profiler)
  - **缺失内容与原理说明**：原文严重低估了 Perfetto 的 Java 堆分析能力。实际上，Perfetto 针对 Java 堆有两种截然不同的模式：
    1. **Java Heap Dumps (快照)**：从 **Android 11** 开始支持。它可以捕获 ART 中对象的完整图谱，包含对象大小和**引用关系**，功能上可以直接替代 HPROF 导出和 MAT 的部分能力，并在 Perfetto UI 中展示对象支配树。
    2. **Java Heap Sampling (采样)**：从 **Android 12** 开始支持。侧重于实时追踪 Java 对象的分配调用栈。
  - **为什么这是重要缺失**：原文断言 Perfetto "无法替代 MAT 的引用链分析"，会导致读者在排查 Java 内存泄漏时，放弃使用更为现代和低开销的 Perfetto 管道，而退回到繁琐的传统手动 hprof 抓取路线。
  - **建议补充方向**：明确区分 Perfetto 的 Java Heap Dumps (Android 11+) 和 Java Heap Sampling (Android 12+) 两种能力。更正“无法查看引用关系”的错误结论。

- [P1][原理链完整性][showmap / procrank / libmeminfo -> procrank] 和 [malloc debug 与 malloc hooks]
  - **原文问题**：分别介绍了 `procrank` 和 `adb shell setprop libc.debug.malloc.program` 的用法，但没有说明在实际设备中执行所需的权限门槛。
  - **缺失内容与原理说明**：
    - `procrank` 强依赖读取 `/proc/<pid>/pagemap` 文件。在现代 Android 系统（特别是 Android 10+）中，由于严格的 SELinux 策略和 capabilities 限制，这要求 Root 权限 (`su`)。在普通的 User build 生产设备上是无法运行的。
    - `libc.debug.malloc.program` 的 `setprop` 操作同样需要 Root 权限 (`adb root`) 才能修改系统属性。对于非 Root 设备，这种开启方法会直接失效。
  - **为什么这是重要缺失**：AIW 的核心目标是指导实战。如果读者拿着书中的命令去公司的商用测试机（User Build，无 Root）上敲，会直接报错 `Permission denied` 或者静默失败，导致实战脱节、排查受阻。
  - **建议补充方向**：明确指出 `procrank` 和基于 `setprop` 的 malloc debug 强依赖 `adb root` 或 userdebug/eng 系统镜像。对于 User 版本设备，必须强调 `wrap.sh` 的替代方案。

## 六、P2 问题（建议改进）
- [P2][版本差异覆盖][HWASAN 与 MTE -> MTE]
  - **原文问题**：“对于应用开发者来说，在支持 MTE 的设备上可以通过开发者选项启用异步 MTE 模式（async mode）”
  - **问题描述**：描述不够贴近最新的开发实践。在 Android 15 中，MTE 提供了一个更面向开发者的 Manifest opt-in 开关。
  - **建议**：建议补充说明：在 Android 15+ 上，开发者可以在 `AndroidManifest.xml` 中直接配置 `android:memtagMode="async"`（或 `sync`）来显式为应用开启 MTE 内存标签检查，而无需强依赖手动去翻找系统开发者选项。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|---------|-------------|
| `libmemunreachable` 的使用 | 中 | API 24 引入了 `libmemunreachable` (通过 `dumpsys meminfo --unreachable` 触发)，这是一种零开销的 Native 内存泄漏检测方案，基于类似 GC 的标记-清除算法寻找没有任何指针引用的 Native 内存。原文未提及此 Native 泄漏检测的轻量级原生入口。 |

## 八、外部核验建议
- **Perfetto Java Heap Profiler 能力区分（Dumps vs Sampling）**：强烈建议复查 `perfetto.dev/docs/data-sources/java-heap-profiler`。
- **`pagemap` 权限收紧对 `procrank` 的影响**：查阅 Android SELinux policy 演进或 AOSP issue tracker 中关于 pagemap 权限收紧的历程。
- **Android 15 MTE Manifest 属性**：查阅 `developer.android.com` 中关于 `android:memtagMode` 的官方文档说明。

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **章节**：03-memory-tools.md
- **严重级别**：P1
- **问题类型**：事实错误 / 版本差异
- **位置**：`heapprofd：Native 堆的实时采样分析 -> 工作机制`
- **问题描述**：错误地声称 Perfetto 的 Java 模式仅展示调用栈且无法替代 MAT 的引用链分析。遗漏了 Android 11 引入的 Java Heap Dumps 功能（可提取完整引用关系）。
- **建议修正方向**：重写该段落，准确区分 Android 11+ 的 Java Heap Dumps 功能(提供引用关系，对标 MAT) 和 Android 12+ 的 Java Heap Sampling 功能(提供分配栈)。
- **建议补充的验证来源**：https://perfetto.dev/docs/data-sources/java-heap-profiler

- **章节**：03-memory-tools.md
- **严重级别**：P1
- **问题类型**：原理断裂 / 实战缺失
- **位置**：`showmap / procrank / libmeminfo` 及 `malloc debug 与 malloc hooks`
- **问题描述**：未指明 `procrank` 命令和通过 `setprop` 开启 malloc debug 的操作强依赖设备的 Root 权限（userdebug/eng 环境）。
- **建议修正方向**：在对应命令的上下文中补充权限前提。明确指出在无 Root 的生产设备上，这些方案默认不可行，并引导开发者使用 `wrap.sh` 或 profileable 等无需 root 的替代方案。

### 9.2 知识盲区清单（供后续研究）
- **章节**：03-memory-tools.md
- **盲区描述**：缺少 `libmemunreachable` 工具的介绍，这是排查 Native 确定性泄漏（没有任何指针指向的不可达内存）的轻量级系统原生方案。
- **重要程度**：中
- **建议研究方向**：研究 `dumpsys meminfo --unreachable` 命令的底层工作原理及适用场景，评估是否应作为独立小节补充到 Native 内存排查路径中。
- **可能关联章节**：10.2 内存泄漏

### 9.3 一般建议清单（非阻断）
- **章节**：03-memory-tools.md
- **问题类型**：版本差异
- **位置**：`HWASAN 与 MTE -> MTE`
- **问题描述**：关于应用如何主动启用 MTE 检查，缺少现代 Android 版本的 Manifest 配置方法。
- **建议**：补充 Android 15 引入的 `android:memtagMode="async"` Manifest 属性说明，提升技术时效性。

### 9.4 可复用知识资产（高价值新增知识）
- **章节**：03-memory-tools.md
- **一手资料链接或来源类型**：https://perfetto.dev/docs/data-sources/java-heap-profiler
- **版本差异摘要**：Perfetto 对 Java 堆的追踪支持分为两个重要演进阶段：Android 11 (R) 引入了 **Java Heap Dumps**，能够抓取完整的对象图谱和引用链（类似于传统的 HPROF 导出）；Android 12 (S) 引入了 **Java Heap Sampling**，基于 `com.android.art` 插件，主要用于持续采样对象的分配调用栈，排查内存分配热点和抖动。
- **可直接复用的技术结论**：在现代 Android 内存性能分析中，Perfetto 已经完整具备了分析 Java 对象引用链与支配树的能力（Android 11+），开发者在排查泄漏时已无需强制回退到使用 MAT 进行离线分析。

## 十、下一候选章节
- 下一章建议继续 review 的章节：`src/part3-tools/ch14-other-tools/04-systrace-perfetto.md` (鉴于本章大量提及 Perfetto 的能力边界，有必要进一步核对 Perfetto 专属章节的准确性与版本覆盖率)。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-21-14-03-memory-tools-external-review.md`