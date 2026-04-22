# 一般建议清单

## [External Review Integration] 2026-04-21

本批次整合了 22 个外部 review 文件，共提取 41 条一般修正建议。主要涉及工具使用说明、案例补充、权限说明等方面。

### GPU 调试工具相关 (14.8)
- **类型**: 数据支撑
- **位置**: 工具使用说明段
- **问题**: 缺少真实案例分析
- **建议**: 补充 GPU 性能问题的实际调试案例
- **来源**: 外部 AI Review

### 内存工具相关 (03)
- **类型**: 原理修正
- **位置**: Perfetto Java 堆分析段
- **问题**: 严重低估了 Perfetto 的 Java 堆分析能力
- **建议**: 明确区分 Perfetto 的 Java Heap Dumps (Android 11+) 和 Java Heap Sampling (Android 12+) 两种能力
- **来源**: 外部 AI Review

- **类型**: 权限说明
- **位置**: 底层工具使用段
- **问题**: 缺少工具执行权限要求说明
- **建议**: 明确指出  和  强依赖  或 userdebug/eng 系统镜像
- **来源**: 外部 AI Review

### 性能管理器相关 (14.7)
- **类型**: 方法改进
- **位置**: 性能分析段
- **问题**: 缺少机器学习模型的调优建议
- **建议**: 补充 AML 模型训练和部署的最佳实践
- **来源**: 外部 AI Review

### 自动化测试工具相关 (14.6)
- **类型**: 工具增强
- **位置**: 自动化脚本段
- **问题**: 缺少自动化脚本示例
- **建议**: 提供性能测试自动化脚本模板
- **来源**: 外部 AI Review

### Battery Historian 相关 (14.11)
- **类型**: 数据支撑
- **位置**: 功耗分析方法段
- **问题**: 缺少实际功耗分析案例
- **建议**: 补充 Battery Historian 在实际项目中的应用案例
- **来源**: 外部 AI Review

### Simpleperf 相关 (14.2)
- **类型**: 功能补充
- **位置**: 性能分析工具段
- **问题**: 缺少特定场景的使用指南
- **建议**: 补充 Simpleperf 在特定性能场景下的使用技巧
- **来源**: 外部 AI Review

### 三方性能库相关 (14.5)
- **类型**: 版本兼容性
- **位置**: 性能库使用段
- **问题**: 缺少版本兼容性说明
- **建议**: 补充各版本 Android 下的三方库兼容性注意事项
- **来源**: 外部 AI Review

## 涉及章节总结
- 14.8: GPU 调试工具
- 03: 内存工具
- 14.7: 性能管理器
- 14.6: 自动化测试工具
- 14.11: Battery Historian 与功耗分析
- 14.2: Simpleperf
- 14.5: 三方性能库
- 14.4: Dumpsys
- 14.1: AS Profiler
- 14.01: 自动化脚本
- 其他章节...

## 建议
1. 优先处理涉及 P1 级别问题的章节（如内存工具章节的 Perfetto 能力修正）
2. 补充工具权限要求的详细说明，提升实战指导价值
3. 增加真实案例分析，提升内容的实用性

## [Task6 Review] 13.1 Perfetto 简介与演进 — 2026-04-21
- **类型**：需修正 + 需补充
- **位置**：参考资料 / Perfetto 的架构
- **问题**：(P0) AOSP源码路径 system/tracing/ 不存在，正确路径为 external/perfetto/src/traced/；(P1) 架构章节遗漏 heapprofd 和 traced_perf 两个核心组件
- **建议**：修正源码路径；在 traced_probes 之后补充 heapprofd/traced_perf 的角色说明
- **来源**：external-review/2026-04-21-22-13.1-external-review.md
- **review 日志**：logs/review/2026-04-21-18-review.md

## [Task6 Review] 14.4 dumpsys 系列命令 — 2026-04-21
- **类型**：需修正 + 需补充 + 需确认
- **位置**：meminfo USS段落 / window焦点段落 / activity进程优先级
- **问题**：(P0) LMKD不使用USS，使用RSS+oom_score_adj；(P1) 遗漏dumpsys input联动；(P2) VISIBLE_APP_ADJ值在Android 10前后不同
- **建议**：修正USS描述；补充dumpsys input建议；说明ADJ版本变化
- **来源**：external-review/2026-04-21-14-04-dumpsys-external-review.md
- **review 日志**：logs/review/2026-04-21-18-review.md

## [Task9 Deep Review] 14.7 ProfilingManager — 2026-04-21
- **类型**：交叉引用
- **位置**：结果分发 / trigger 版本对照表 / 相关章节
- **问题**：文中多次写“详见 §8.8 ProfilingManager 系统触发式性能追踪”，但当前 `8.8` 实际是“Android 多媒体管线性能”，引用目标不存在。
- **建议**：把交叉引用改成真实存在的章节编号或文件路径，再同步正文里的“§8.8”描述。

## [Task9 Deep Review] 14.9 Android Camera 性能与 Perfetto 分析 — 2026-04-21
- **类型**：数据缺失/案例泛化
- **位置**：SQL 查询：量化帧率和帧间隔
- **问题**：示例把 `thread.name like '%PreviewSpacer%'` 写成默认筛选条件，但没有说明它不是稳定的公开 AOSP 命名，也没有给通用 fallback。
- **建议**：补充“该筛选依赖具体 trace/实现”的边界，并给出按 `cameraserver` + `queueBuffer`/stream track 做通用筛选的替代写法。

## [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-04-21
- **类型**：交叉工具链
- **位置**：ODPM 的工作原理 / Power Profiler vs Energy Profiler
- **问题**：章节把 ODPM 基本限定在 Android Studio Profiler 视角，缺少 Perfetto `android.power_rails` trace 与 SQL 分析链路。
- **建议**：补一段 Perfetto 抓取 power rails、和 CPU 调度/线程事件联查的入口，避免工具链割裂。

## [External Review] 15.6 Testing Best Practices — 2026-04-21
- **类型**：最佳实践补充
- **位置**：固定 CPU 频率（进阶）
- **问题**：未提及 Jetpack Benchmark 自带的 LockClocks 自动化锁频能力
- **建议**：补充 `androidx.benchmark` 内部 `LockClocks` 机制可自动锁定 CPU 频率，无需手动编写 Shell 脚本
- **来源**：外部 AI Review（06-15.6）

## [External Review] 15.8 实证性能问题研究 — 2026-04-21
- **类型**：原理描述优化
- **位置**：模式一：API 误用 -> GlobalScope 协程
- **问题**：GlobalScope 导致泄漏的根本条件描述不够严谨，需补充闭包捕获外部引用的前提
- **建议**：补充说明 GlobalScope 导致泄漏的根本条件是"闭包捕获了外部生命周期组件的引用"，而非必然泄漏
- **来源**：外部 AI Review（08-15.8）

## [External Review] 14.1 Android Studio Profiler — 2026-04-21
- **类型**：描述模糊
- **位置**：Callstack Sample 小节
- **问题**："Android Studio 2025" 命名不够专业确切
- **建议**：定位到具体动物代号（如 Koala, Ladybug, Meerkat），避免模糊版本描述
- **来源**：外部 AI Review（14-01）

## [External Review] 14.2 Simpleperf — 2026-04-21
- **类型**：原理链补充
- **位置**：软件事件：cpu-clock 和 task-clock
- **问题**：`--trace-offcpu` 机制解释不够透彻，未点出 off-CPU 时间如何被可视化
- **建议**：补充基于 `sched_switch` 计算时间差加权的原理：监听调度切换事件，计算线程被换出和下一次被换入之间的时间差，伪造 off-CPU 样本
- **来源**：外部 AI Review（14-02）

## [External Review] 14.3 Memory Tools — 2026-04-21
- **类型**：版本差异
- **位置**：HWASAN 与 MTE -> MTE
- **问题**：关于应用如何主动启用 MTE 检查，缺少 Android 15 的 Manifest 配置方法
- **建议**：补充 Android 15 引入的 `android:memtagMode="async"` Manifest 属性说明
- **来源**：外部 AI Review（14-03）

## [External Review] 14.5 三方性能库 — 2026-04-21
- **类型**：内容补充
- **位置**：KOOM 线程泄漏检测
- **问题**：未提及线上实际使用中可能遇到的误报和性能开销问题
- **建议**：补充 KOOM 如何通过白名单或业务线程标记来过滤正常常驻线程，降低误报率
- **来源**：外部 AI Review（14-05）

## [External Review] 14.6 自动化测试工具 — 2026-04-21
- **类型**：代码示例准确性
- **位置**：CompilationMode：量化编译优化效果
- **问题**：`CompilationMode.Partial(CompilationMode.Partial.Mode.DEFAULT)` 代码偏老且冗余
- **建议**：简化为 `CompilationMode.Partial()`
- **来源**：外部 AI Review（14-06）

## [External Review] 14.7 ProfilingManager — 2026-04-21
- **类型**：API 签名准确性
- **位置**：显式请求的公共骨架
- **问题**：CancellationSignal 的传递方式未在代码中体现，且可能是通过方法参数传递而非 Builder
- **建议**：核实 AndroidX 最终 API，更新代码示例并补充 `adb shell device_config put profiling_manager rate_limiter.disabled true` 绕过限流的调试指令
- **来源**：外部 AI Review（14-07）

## [External Review] 14.8 GPU 调试工具 — 2026-04-21
- **类型**：版本差异
- **位置**：Snapdragon Profiler 状态
- **问题**：称 Snapdragon Profiler 仍在活跃维护，但高通正逐渐向 Qualcomm Profiler 整合
- **建议**：提及 Qualcomm Profiler 的出现及其作为系统级工具的地位
- **来源**：外部 AI Review（14-08）

## [External Review] 14.9 Android Camera 性能与 Perfetto 分析 — 2026-04-21
- **类型**：版本标注
- **位置**：requestStreamBuffers
- **问题**：未标注 requestStreamBuffers 是 Camera HAL 3.5 的核心特性
- **建议**：明确标注为 Camera HAL 3.5 引入的"按需分配（Buffer Management）"特性
- **来源**：外部 AI Review（14-09）

## [External Review] 14.10 eBPF/BPF 性能分析 — 2026-04-21
- **类型**：原理补充
- **位置**：BPF CO-RE：一次编译，到处运行
- **问题**：对 CO-RE 的跨设备兼容性描述过于乐观，未指出厂商驱动层可能面临的 BTF 缺失问题
- **建议**：补充说明 CO-RE 绝对稳定性仅限标准 Linux/GKI 数据结构，追踪厂商驱动层结构仍面临 BTF 信息缺失
- **来源**：外部 AI Review（14-10）

## [External Review] 14.11 Battery Historian 与功耗分析工具 — 2026-04-21
- **类型**：内容补充
- **位置**：bugreport 抓取
- **问题**：现代 Android 14+ 上部分受限 OEM 手机 dumpsys batterystats 可能受权限/后台策略影响
- **建议**：简单提示某些受限 OEM 手机可能需要显式赋予开发者选项相关安全权限
- **来源**：外部 AI Review（14-11）



## [Task9 Deep Review] 14.3 内存分析工具 — 2026-04-21
- **类型**：版本差异
- **位置**：HWASAN 与 MTE -> MTE
- **问题**：正文只写“通过开发者选项启用异步 MTE 模式”，遗漏 Android 15+ 可通过 `android:memtagMode="async"` / `sync` 在 Manifest 侧显式 opt-in 的新入口。
- **建议**：补一段版本化说明，区分开发者选项、系统镜像限制与 Android 15+ Manifest opt-in 三条启用路径。

## [Task9 Deep Review] 14.4 dumpsys 系列命令 — 2026-04-21
- **类型**：版本差异
- **位置**：dumpsys activity：进程优先级与 ANR
- **问题**：正文直接给出 `VISIBLE_APP_ADJ=100`，没有说明 Android 10 前常见资料里是 `1`。读者对照旧文或老设备时容易误判。
- **建议**：加一句版本差异提示，说明 Android 10+ 把 ADJ 数值整体放大，但优先级顺序没变。

## [Task9 Deep Review] 14.6 自动化测试工具 — 2026-04-21
- **类型**：源码准确性
- **位置**：CompilationMode：量化编译优化效果
- **问题**：示例仍写 `CompilationMode.Partial(CompilationMode.Partial.Mode.DEFAULT)`，偏旧，容易和当前 `CompilationMode.Partial()` 的默认写法混淆。
- **建议**：把示例收敛到当前默认写法，并补一句默认模式与 Baseline Profile 关系。

## [Task9 Deep Review] 5.2 EAS 能量感知调度 — 2026-04-22
- **类型**：版本差异 / 观测边界
- **位置**：`## EAS 在 Perfetto 中的观察 > CPU Frequency Track`
- **问题**：正文写成“同簇 CPU 通常以簇为单位调频”，缺少硬件边界。新平台存在按 policy / per-core DVFS 的实现，读者如果只按“同簇同频”判断，容易误读频率轨。
- **建议**：改成“很多移动 SoC 仍按 policy / 簇调频，但要以 `/sys/devices/system/cpu/cpufreq/policy*` 为准”，并补一句不要只凭同簇同频下结论。

## [Task9 Deep Review] 11.5 Wakelock 机制与功耗分析 — 2026-04-22
- **类型**：数据缺失
- **位置**：`## Wakelock 的本质：为什么 Android 需要“阻止睡眠”`
- **问题**：正文写“整机功耗可以降到 1mA 以下”，但没有给机型、温度、调制解调器状态、Always-on 组件条件，这个数值跨设备不可直接复用。
- **建议**：改成“可降到极低待机电流”或补测试条件，避免把单机观测写成通用基线。

## [Task9 Deep Review] 5.2 EAS 能量感知调度 — 2026-04-22
- **类型**：源码准确性
- **位置**：`## 参考资料`
- **问题**：`kernel/sched/fair.c`、`kernel/power/energy_model.c` 被标成 “AOSP 源码”，但路径缺少内核仓库根和分支信息，读者无法在 AOSP / GKI 树直接定位。
- **建议**：改成 Linux kernel / Android common kernel 锚点，并给出可检索入口，例如对应分支下的 `kernel/common` 路径或直接引用内核文档。

## [Task9 Deep Review] 11.5 Wakelock 机制与功耗分析 — 2026-04-22
- **类型**：知识盲区
- **位置**：`Android 提供了四种 wakelock 类型，但后三种已经废弃`
- **问题**：这里把 wake lock level 简化成四种，漏掉 `PROXIMITY_SCREEN_OFF_WAKE_LOCK` 这一类特殊屏幕相关 level，读者会以为 PowerManager 里只剩四种枚举。
- **建议**：补一句“本文聚焦功耗分析常见的 partial / screen 类 wakelock，`PROXIMITY_SCREEN_OFF_WAKE_LOCK` 等特殊 level 不展开”，避免把范围写成全集。

## [Task9 Deep Review] 15.9 从采集到治理的闭环 — 2026-04-22
- **类型**：版本差异
- **位置**：第三步“采集”中的信号源列表 / `稳定性：ApplicationExitInfo`
- **问题**：章节适用版本覆盖 Android 8-16，但把 `ApplicationExitInfo` 与通用信号源并列，没有标出它是 Android 11（API 30）起才可直接使用的能力。低版本读者容易误判线上稳定性采集入口。
- **建议**：在该 bullet 补 `Android 11+/API 30+` 版本标识，并给 Android 8-10 的替代入口提示，例如 Play vitals、自建退出原因日志或 tombstone / signal 侧证据。

## [Task9 Deep Review] 6.1 Android 存储架构 — 2026-04-22
- **类型**：数据缺失
- **位置**：`性能差距有多大？` 表格（eMMC 5.1 / UFS 3.1 / UFS 4.0）
- **问题**：顺序吞吐和随机 IOPS 对比没有标出 queue depth、块大小、测试端或厂商口径，容易把 JEDEC / 器件公开值、样片测试和整机实测混成同一层结论。
- **建议**：在表下注明“为协议/器件公开口径，非统一整机 benchmark”，并补测试条件或来源链接，避免读者把表中的数值直接当成 Perfetto 分析基线。

## [Task9 Deep Review] 6.4 存储相关的版本演进 — 2026-04-22
- **类型**：源码准确性
- **位置**：参考资料 / EROFS 段（约 L221, L386）
- **问题**：`source.android.com/docs/core/storage/erofs` 当前 404，读者按文中锚点无法打开官方页面。
- **建议**：把官方链接改到 `source.android.com/docs/core/architecture/kernel/erofs`，并区分 AOSP 存储总览页与 EROFS 专页。

## [Task9 Deep Review] 6.4 存储相关的版本演进 — 2026-04-22
- **类型**：数据缺失
- **位置**：EROFS 的核心技术优势（L205-L211）
- **问题**：“24%-45% 空间收益”和“最高 22.9% 启动提升”缺少机型、镜像大小、压缩级别和 workload 条件，容易被读者误当成统一 benchmark。
- **建议**：在表述里加“LPC 2019 / 厂商测试口径”与测试条件，或降级成“公开案例显示可获得 XX 量级收益”。

## [Task9 Deep Review] 7.4 典型场景分析 — 2026-04-22
- **类型**：源码准确性
- **位置**：桌面滑动（L311）
- **问题**：Launcher 桌面容器写成 `Workspace/BrowseLayout`，与 AOSP Launcher3 主线类名不一致。
- **建议**：改成 `Workspace / CellLayout`，或直接写“Launcher 自定义页面容器”，避免给出查不到的类名。

## [Task9 Deep Review] 10.4 低内存对系统性能的影响 — 2026-04-22
- **类型**：交叉引用
- **位置**：`与 [4.5 App 内存优化](../ch04-memory/05-app-memory-optimization.md)`
- **问题**：当前相对路径从 `part2-performance/ch10-memory-perf/` 解析后会落到不存在的 `src/part2-performance/ch04-memory/05-app-memory-optimization.md`，读者无法跳到真正的 §4.5。
- **建议**：把链接改成指向 `src/part1-fundamentals/ch04-memory/05-app-memory-optimization.md` 的正确相对路径，或统一改用章节号引用避免跨 part 相对路径漂移。

## [Task9 Deep Review] 4.7 16KB Page Size 与 Android 性能 — 2026-04-22
- **类型**：版本边界/工具链条件
- **位置**：L124-L127
- **问题**：AGP 8.5.1 段只写“自动处理对齐”，漏掉 uncompressed shared libraries、bundletool zip alignment，以及 AGP 8.3-8.5 默认对齐但 Play 打包仍可能失配的条件。
- **建议**：把 AGP 8.5.1+、bundletool `PAGE_ALIGNMENT_16K`、以及 AGP 8.3-8.5 的 caveat 放到同一段，避免读者误判“升级 AGP 即自动合规”。

## [Task9 Deep Review] 5.3 大小核架构 — 2026-04-22
- **类型**：调度提示边界
- **位置**：L411-L414
- **问题**：`Process.setThreadPriority()` 被直接写成“会更积极地把高优先级线程放到大核上”，容易把 CFS 权重和异构选核混为一谈。
- **建议**：把这段改成“priority 主要影响调度竞争；真正更直接的放核路径通常是 uclamp / task profile / cpuset / affinity”，并补版本与权限边界。

## [Task9 Deep Review] 9.2 ANR 类型与触发条件 — 2026-04-22
- **类型**：Broadcast 边界表达
- **位置**：L140-L157 / L327
- **问题**：正文把 Broadcast ANR 讨论收敛到“有序广播 + 动态注册 Receiver”，而官方 ANR 诊断文档当前更强调同步/异步 receiver、`goAsync()` 与 app startup 是否落入同一超时窗口。
- **建议**：按 modern broadcast timeout model 重写边界说明；若要保留 ordered/parallel 细分，补对应 AOSP 实现路径或标 `[待验证]`。

## [Task9 Deep Review] 2.3 VSync 机制 — 2026-04-22
- **类型**：数据缺失
- **位置**：五、VSync Phase Offset 的作用与调优 / 六、VSync 在 Perfetto 中的观察
- **问题**：阶段结论和相位配置示例没有和具体设备/刷新率/Trace 观察绑定，读者难以复核“1~2 帧”延迟收益。
- **建议**：补一组 60Hz/120Hz 实例，至少包含 `dumpsys SurfaceFlinger | grep phase` 输出、VSYNC-app/VSYNC-sf 轨道时间差，说明 phase 调优怎么落到证据链。

## [Task9 Deep Review] 5.6 Android 功耗管理 — 2026-04-22
- **类型**：数据支撑/版本差异
- **位置**：WakeLock 的种类与滥用检测 / 版本演进
- **问题**：“1 分钟 Long Wakelock / force-stop 清理”和 Android 17 DeliQueue 行没有公开证据链，容易把 Play vitals 指标、系统行为和消息队列演进混为一谈。
- **建议**：改用 Android vitals 的 excessive partial wake lock 口径（后台或 FGS 场景 24h 累计 2h+，再看会话占比）以及 Batterystats/Historian 证据链；把 DeliQueue 从功耗版本表移走或注明只是间接假设。

## [Task9 Deep Review] 13.7 Perfetto 的高级用法 — 2026-04-22
- **类型**：数据缺失
- **位置**：将 Perfetto 集成到 CI/CD / 降低误报率的几个实践
- **问题**：经验阈值（5-10% 波动、3-5 次、中位数、5%/15% 告警线）没有与设备条件、Trace 规模、Benchmark 方式绑定。
- **建议**：补一组 Macrobenchmark / 物理机样本的噪声分布，说明这些阈值适用的环境和失效边界。


## [Task9 Deep Review] 1.17 IPC 全景：Android 进程间通信机制对比与性能选型 — 2026-04-22
- **类型**：数据缺失
- **位置**：### 4.3 使用频率统计（AOSP 系统进程）
- **问题**：正文给出 Binder / Unix Socket / 共享内存 / Pipe / Signal 约 90% / 5% / 3% / 1% / 1% 的占比，但没有样本范围、统计方法、Trace/脚本来源或设备边界，当前更像经验数字而不是可复核统计。
- **建议**：补充统计口径（哪些进程、怎样计 Binder 事务/Socket/共享内存事件）和数据来源；如果暂时没有可复核样本，改成定性描述，避免伪精确百分比。

## [Task9 Deep Review] 1.17 IPC 全景：Android 进程间通信机制对比与性能选型 — 2026-04-22
- **类型**：交叉引用
- **位置**：交叉参考 §1.13
- **问题**：交叉参考写成“Pipe + epoll 在 Looper 中的应用”，但本章正文与 `1.13 MessageQueue 机制与 DeliQueue 无锁优化` 都已明确 Android 8-17 的 Looper/MessageQueue 唤醒路径应理解为 `eventfd + epoll`，pipe 只适合作为历史背景。
- **建议**：把交叉参考改成“Looper / MessageQueue 的 eventfd + epoll 唤醒路径（含 pipe 历史背景）”或同等准确表述。
