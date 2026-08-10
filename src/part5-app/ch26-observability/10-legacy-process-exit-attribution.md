---
title: Android 11 以下进程退出归因方案
chapter: '26.10'
section: '26.10'
status: finalized
applicable_versions: Android 5.0 (API 21) - Android 10 (API 29)
last_verified: '2026-07-01'
last_verified_against: AOSP android-17.0.0_r1 (ApplicationExitInfo/ActivityManager/AppExitInfoTracker/lmkd);
  AOSP android-10.0.0_r47 system/core/lmkd historical path; Android Developers docs;
  KOOM README
confidence: medium
sources:
- type: official
  path: https://developer.android.com/reference/android/app/ApplicationExitInfo
- type: official
  path: https://developer.android.com/reference/android/app/ActivityManager#getHistoricalProcessExitReasons
- type: official
  path: https://developer.android.com/topic/performance/vitals/anr
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityManager.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/AppExitInfoTracker.java
- type: aosp
  path: https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/
- type: aosp-historical
  path: https://android.googlesource.com/platform/system/core/+/refs/tags/android-10.0.0_r47/lmkd/
- type: material
  path: DeepResearch/2026-05-08-applicationexitinfo-android11-below-alternatives.md
- type: material
  path: DeepResearch/2026-05-09-application-exit-info-android11-alternatives.md
- type: open-source
  path: github.com/KwaiAppTeam/KOOM/koom-java-leak/README.md
- type: structure
  path: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 2.md
- type: structure
  path: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 3.md
- type: structure
  path: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 35.md
- type: structure
  path: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 45.md
- type: structure
  path: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 50.md
tags:
- applicationexitinfo
- process-exit
- apm
- legacy-android
- stability
related_chapters:
- '9.3'
- '19.24'
- '20.8'
- '23.7'
- '26.2'
- '26.9'
drafted_date: '2026-05-16'
polish_count: '1'
task6_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: '2026-07-04'
task6_result: pass-light-edit
last_task6_at: 2026-07-04T12:08:00+08:00
last_task6_review_log: logs/review/2026-07-04-12-review.md
last_task6_audit: '2026-06-07'
created_by: task2a-knowledge-gap
created_date: '2026-05-15'
gap_source: 素材驱动/官方文档/章节深挖
task9_state: reviewed
task9_reviewed_date: '2026-05-17'
task9_reviewed_by: openclaw-task9
last_task9_at: '2026-05-17T00:32:12+08:00'
last_task9_audit: '2026-07-01'
last_task9_autofix_at: '2026-07-01'
last_task9_review_log: logs/deep-review/2026-05-17-00-deep-review.md
pipeline_stage: ready-to-publish
task9_result: pass-tech-review
task2b_state: fixed
task2b_result: fixed
p0: '0'
p1: '0'
p2: '3'
task9_review_notes: '2026-05-17 Task9 00: pass-tech-review。Task2B 已修复 P0/P1；本轮仅保留既有
  P2 来源路径/JVMTI 权限边界建议。Task6 已通过且 queue 无 pending，自动晋升 finalized / ready-to-publish。已写入
  logs/deep-review/2026-05-17-00-deep-review.md。 | 2026-07-01 Task9 idle-audit AUTO-FIX:
  将 AOSP source 锚点从 master/裸路径改为 android-17.0.0_r1 tagged URLs；保留 Android 10 lmkd
  历史路径为 android-10.0.0_r47 参照；版本上限遵守 Android 17/API 37。回到 Task6 复审。详见 logs/deep-review/2026-07-01-09-audit.md。'
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-16
---

# 26.10 Android 11 以下进程退出归因方案

Android 11 以前，应用侧没有 `ApplicationExitInfo` 这类系统退出记录。进程结束后，SDK 只能在下次启动时读取崩溃文件、卡顿现场、内存快照、会话标记等应用自有证据，推测上一个进程发生了什么。

运行版本范围是 Android 5.0（API 21）到 Android 10（API 29）。平台侧以 `android-17.0.0_r1` 作为当前模型的校准上限，内核侧以 `android17-6.18-2026-06_r6` 作为当前参考。后两个锚点用于说明今天的系统怎样记录退出、LMKD 与内核怎样协作，并不表示 Android 5～10 设备运行 Linux 6.18。分析旧设备时，还要回到对应 ROM 的 framework、Android 10 AOSP `lmkd` 和厂商内核实现。

## 要点

### 🔹 先区分系统事实与应用推断

`ApplicationExitInfo` 从 API 30 开始提供。应用可通过 `ActivityManager.getHistoricalProcessExitReasons(packageName, pid, maxNum)` 查询系统保留的历史记录。`ApplicationExitInfo.java` 定义的是跨 Binder 返回给客户端的值对象；在 Android 17 源码中，服务端历史由 `AppExitInfoTracker` 管理，其内部 `AppExitInfoContainer` 按包和 UID 保存记录。Android 5～10 没有这套公开查询接口，不能把一次“会话标记未关闭”写成系统确认的退出原因。

低版本最难处理的是进程来不及执行任何清理逻辑的场景：

- `SIGKILL` 不能注册 handler。LMKD、用户停止、系统回收等路径在应用侧都可能只留下未结束的会话。
- 系统判定 ANR 后会生成系统 trace，但普通发布包不能依赖读取 `/data/anr/`。应用内 watchdog 只能证明主线程在采样期间没有响应，不能证明系统已经判定 ANR。
- Java 堆 OOM、地址空间耗尽、线程或文件描述符耗尽会同时削弱采集能力。此时分配对象、创建线程和写大文件都可能失败。
- 设备重启会中断进程，也会重置 `elapsedRealtime`。如果没有同一启动周期内的时间边界，下一次启动时间不能当作上次退出时间。

数据模型应同时保存 `legacy_reason`、`confidence` 和 `evidence[]`。其中 reason 是应用规则的结论，confidence 描述证据强度，evidence 保留可复核的原始事实。三者不能合成一个看似确定的枚举。

可以按证据强度组织事件：

| 结论 | 代表证据 | 推荐口径 |
|------|----------|----------|
| 已确认 Java 崩溃 | 本进程写出的完整未捕获异常记录，包含会话、线程和栈 | `JAVA_CRASH_CONFIRMED` |
| 已确认 Native 崩溃 | 完整 minidump 或经过校验的 signal report | `NATIVE_CRASH_CONFIRMED` |
| 外部平台确认 ANR | Play Vitals、bugreport 或厂商系统 trace 可与会话对应 | `ANR_CONFIRMED_EXTERNAL` |
| 应用观测到卡死 | watchdog 连续留存主线程与调度现场，但没有系统记录 | `ANR_SUSPECTED` |
| 疑似内存压力退出 | 会话未闭合，并且退出前有内存、线程、fd 或堆报告异常 | `LOW_MEMORY_SUSPECTED` |
| 原因未知 | 只有会话未闭合，或多类证据互相冲突 | `ABNORMAL_END_UNKNOWN` |

`LOW_MEMORY_SUSPECTED` 不能在报表中显示成“LMKD 已杀进程”。同理，应用 watchdog 的样本也不能直接计入 Android Vitals 的 ANR 指标。

### 🔹 Signal Handler、ANR traces、LMKD、dumpsys 的能力对照

低版本没有统一入口，每种手段都要同时标出证明范围和访问边界。

| 手段 | 能证明什么 | 普通发布包边界 | 合适用途 |
|------|------------|----------------|----------|
| `Thread.setDefaultUncaughtExceptionHandler` | Java 未捕获异常到达 handler | 不能覆盖 Native crash、ANR、`SIGKILL`；已有 handler 还要按约定传递 | 写小型 Java crash 记录 |
| 经过验证的 Native crash 组件 | 收集到的 signal、寄存器、minidump 与映射信息 | handler 只能调用 async-signal-safe 操作；堆和锁可能已损坏 | Native 崩溃诊断 |
| 主线程 watchdog | 采样时主线程未在期限内响应 | 不等于系统 ANR；暂停、调试器、设备负载也可能触发 | 保存主线程栈、消息调度和前后台状态 |
| `/data/anr/` | 系统生成的 ANR trace | 普通应用通常不可读，官方取证流程依赖 adb/bugreport | 实验室复现、用户授权诊断、厂商协作 |
| 系统 event log | `am_anr`、`am_crash` 等系统事件 | 第三方应用不能把读取系统事件当作稳定能力 | 调试、系统应用或受管设备 |
| LMKD / lowmemorykiller 线索 | 系统处于内存压力，或外部日志显示发生 kill | 应用不能捕获 `SIGKILL`，也不能可靠订阅 LMKD 的系统 kill 记录 | 外部补证或应用侧间接推断 |
| `dumpsys` / bugreport | 系统进程状态、adj、内存与事件上下文 | 通常需要 shell、`DUMP` 或系统权限，输出也不是 SDK 稳定协议 | 复现、售后和受管设备诊断 |
| `/proc/self/*` | 当前进程在采样时的部分状态 | 只能观察自己且受内核、SELinux 与厂商修改影响 | 低频快照 |

Native crash 处理必须把“进入 signal handler”和“完成持久化”看成两个阶段。崩溃线程可能持有 libc、分配器或应用锁，从 handler 里调用普通日志、分配内存或执行复杂 C++ 代码都可能再次故障。生产实现宜采用经过机型验证的 Crashpad/Breakpad 类组件，或预先启动的独立 handler 进程。不要把“收到信号后临时 fork，再在子进程调用任意库函数”当成通用安全方案；多线程进程 fork 后，子进程会继承其他线程持有的锁。

ANR trace 也不能按“线上 SDK 直接读文件”设计。Android 官方文档说明，旧版本使用单个 `/data/anr/traces.txt`，较新版本使用多个 `/data/anr/anr_*` 文件；同一文档给出的取证方式依赖 adb 访问设备。SDK 能稳定保留的是本进程 watchdog 现场，再由 Play Vitals、bugreport 或厂商诊断提供系统侧证据。

LMKD 归因还要区分年代。Android 10 AOSP 已有 userspace `lmkd`，可向目标发送 `SIGKILL`；更老设备或厂商内核仍可能使用内核 lowmemorykiller 驱动。Android 17 的 `lmkd` 与 6.18 内核锚点用于理解当前 PSI、进程优先级和 kill 上报路径，不能反推某台 Android 8 设备的实现。普通应用只能在进程存活时记录内存压力与自身状态，下次启动再把这些记录作为推断证据。

内存字段也要按来源命名。`/proc/self/status` 可提供 `VmRSS`、`VmSize`、线程数等字段，但不提供 PSS；PSS 可由 `Debug.getPss()`、`Debug.MemoryInfo` 或在允许访问时解析 `smaps`/`smaps_rollup` 获得。RSS、PSS、Java heap 和虚拟地址空间代表不同问题，不能互相代替。任何 `/proc/self/*` 样本都只描述采样瞬间，不能单独证明后来由谁结束了进程。

### 🔹 KOOM fork dump 在低版本 OOM 现场保留中的位置

KOOM 的 Java Leak 模块用于在进程仍存活时监测 Java heap、线程、fd 和虚拟内存等信号，并在满足其配置条件后生成 HPROF。其 fork dump 方案会暂停 ART、fork 子进程、恢复父进程，再由子进程写出 HPROF。项目 README 声明支持 Android 5.0 及以上；这是 KOOM 项目的兼容范围，不是 Android SDK 对所有 ROM 的保证。

它对退出归因的价值是补充“退出前堆现场”：

- Java heap 持续增长时，可以在进程尚能工作时保存对象引用关系。
- HPROF 能解释 Java 对象占用，却不能解释所有 Native 分配、图形缓冲、文件映射和内核内存。
- 已经收到 `SIGKILL` 的进程没有机会再触发 dump。

fork dump 依赖 ART 私有实现、动态链接和不同 Android 版本的兼容处理，还会增加 copy-on-write、RSS、文件 I/O、存储与隐私成本。即使某个版本在实验室可用，也要经过目标 ROM 灰度验证、资源预算和失败保护。Android 17 的默认发布方案不应依赖未验证的 ART 私有符号。

KOOM 报告只能成为 `evidence[]` 的一项。比如，上一会话未结束，而且此前出现连续 Java heap 压力并成功保存 HPROF，规则可以给出 `LOW_MEMORY_SUSPECTED`。在 Android 5～10 上没有系统退出记录可供确认，不能因为有一份 HPROF 就把置信度提高到“系统确认”，也不能把 Java heap 泄漏等同于 LMKD kill。

### 🔹 权限、ART TI 与厂商 ROM 边界

低版本退出归因的主要误差来自访问权限、系统版本和厂商修改。能力清单应区分“应用自有数据”“调试环境数据”和“系统或厂商数据”。

| 线索 | 稳定性 | 风险 |
|------|--------|------|
| SDK 自己写的 crash/minidump/session marker | 高 | 写文件失败、进程二次崩溃、磁盘满 |
| 公开 API 与应用私有目录 | 高 | 仍需处理版本差异、I/O 失败和数据过期 |
| `/proc/self/status`、`/proc/self/fd`、`/proc/self/maps` | 中 | 节点和字段受内核、SELinux 与 ROM 影响；高频采集会增加开销 |
| 应用自身 Logcat | 中 | 不能据此获得完整系统事件；日志可能被覆盖 |
| `/data/anr/`、系统 event log、LMKD 记录 | 低 | 普通应用不能稳定访问 |
| `dumpsys` / bugreport | 低 | 需要 shell、系统授权或用户参与；格式不是 SDK 契约 |
| ROM 私有诊断接口 | 取决于合作协议 | 升级后可能改变，还要单独处理授权和数据治理 |

Android 8.0 引入 ART TI/JVMTI，但官方文档明确限制 agent 只能附加到 `android:debuggable="true"` 的应用，文件权限和 SELinux 还会限制 agent 库的加载。普通应用商店发布包不能依赖 JVMTI 构建通用的线上退出 SDK。它适合调试包、实验室复现或受控环境，用于观察对象分配、线程、类加载和 GC 等过程，不负责提供进程结束后的系统归因。

厂商 ROM 还会影响三类判断：

- 后台限制策略：同样是 marker 未闭合，不同设备上的可能原因分布不同，但单个事件仍不能由机型先验直接定因。
- 日志保留策略：部分 ROM 会扩展系统日志或诊断接口，也可能限制 `/proc`、Logcat、ANR 文件访问。
- 进程优先级策略：前后台切换、保活策略、厂商电池管理会改变 OOM adj 和进程被回收的概率。

厂商能力写入分析平台时，应带 `source=oem`、`build_fingerprint_hash`、`api_level`、`collector_version` 和授权版本，并与 AOSP 公开接口来源分开统计。

### 🔹 低版本归因结果如何并入 ApplicationExitInfo 模型

Android 11+ 的系统记录与 Android 5～10 的应用推断可以进入同一分析域，但不能共用一个无来源的 `reason` 字段。系统原因、旧版推断和展示分类应分别存储。

建议最小字段如下：

| 字段 | 含义 | 注意事项 |
|------|------|----------|
| `event_id` / `session_id` | 归因事件和上一个进程会话 | 由应用生成并持久化 |
| `package_name` / `process_name` / `pid` | 进程身份 | PID 会复用，不能单独作为关联键 |
| `boot_session_id` | 采样所属的设备启动周期 | 不可用时显式留空，不要编造 |
| `process_start_elapsed_ms` | 上一进程启动时的单调时钟值 | 仅可在同一设备启动周期比较 |
| `next_start_wall_time_ms` / `next_start_elapsed_ms` | 发现旧会话未闭合的时间 | 这是检测时间，不是退出时间 |
| `system_reason_code` / `system_timestamp_ms` | API 30+ 系统事实 | 来源固定为 `ApplicationExitInfo` |
| `legacy_reason` / `confidence` | API 21～29 的规则结论 | 不写入系统 reason 字段 |
| `evidence[]` / `attachment_ref[]` | 可复核事实和附件引用 | 附件引用需带保留期、加密和访问级别 |
| `last_foreground_state` | 最近一次成功写入的前后台状态 | 不代表退出瞬间状态 |
| `memory_snapshot` | Java heap、PSS、RSS、VmSize、fd、线程数 | 每个值记录采样 API 与时间 |
| `collector_version` / `rule_version` | 采集器和规则版本 | 支持复算和误判追踪 |

低版本枚举可以在报表层关联到相近的 Android 11+ 分析类别，但关联不改变来源：

| 低版本结论 | 可用于聚合的分析类别 | 必需证据 |
|------------|------------------------|----------|
| `JAVA_CRASH_CONFIRMED` | Java crash | 完整异常记录能对应到上一会话 |
| `NATIVE_CRASH_CONFIRMED` | Native crash | 完整 minidump 或经校验的 signal report |
| `ANR_CONFIRMED_EXTERNAL` | ANR | 外部系统证据能对应到应用、版本和时间范围 |
| `ANR_SUSPECTED` | Suspected ANR | watchdog 现场；没有系统确认时保持 suspected |
| `LOW_MEMORY_SUSPECTED` | Suspected memory pressure | 会话未闭合加一项或多项内存压力证据 |
| `PACKAGE_REPLACED_DETECTED` | Package lifecycle | 安装/更新时间或版本变化；不代表设备重启 |
| `DEVICE_REBOOT_DETECTED` | Device lifecycle | 能证明启动周期变化；不映射到某个公开退出 reason |
| `ABNORMAL_END_UNKNOWN` | Unknown | 只有未闭合标记，或证据冲突 |

不要把 `DEVICE_REBOOT_DETECTED` 映射为 `REASON_OTHER`，也不要把 `ABNORMAL_END_UNKNOWN` 映射为 `REASON_USER_REQUESTED`。`ApplicationExitInfo` 的公开 reason 是系统记录；旧版应用没有足够证据时就应保留 unknown。Java heap OOM、fd 耗尽等细节可进入自有 `evidence_type`，不要伪装成公开 API 中不存在的 `subReason`。

事件关联也不能只用 PID 和时间桶。PID 会复用，低版本又没有可靠退出时间。应用自有事件可用 `session_id + process_name + evidence fingerprint` 生成稳定标识；外部 ANR 或崩溃记录则按包、进程、版本、设备启动周期和时间边界进行候选匹配。无法唯一匹配时保留多个候选及分数，不强行合并。

### 🔹 灰度、采样与隐私边界

采集预算应由设备性能、存储、进程状态和问题严重度决定，不预设“所有设备全量采集”。

基础层只保存小对象：session marker、最近一次前后台状态、经过预算控制的内存/线程/fd 摘要、关键业务事件摘要和 crash envelope。写入应有大小上限、失败回退与原子替换策略，覆盖比例由压测结果和线上预算决定。

诊断层只对灰度人群、问题版本、特定机型或用户主动诊断开启。可增加 watchdog 栈、本进程关键线程栈、`/proc/self/maps` 摘要、按配置时长维护的环形日志和 KOOM 触发。高成本功能必须分别控制启用条件、磁盘预算、CPU/I/O 开销、上传网络和停止开关。

minidump、HPROF、maps、线程栈和日志可能包含路径、账号片段、URL、业务参数与设备信息。采集和上传至少要覆盖这些约束：

- 数据最少化：只采集当前问题需要的字段，并在客户端去除 token、账号、URL query 与业务标识。
- 明示与控制：按产品政策取得必要同意，提供诊断开关，并能停止后续采集。
- 加密与权限：本地、传输和服务端存储分别保护，原始附件仅授予必要人员和服务。
- 保留与删除：不同附件类型设置保留期，支持到期删除、用户删除请求和审计记录。
- 预算与熔断：按版本、设备、规则和文件类型限制采样与上传，异常增长时能远程停用。

对外指标必须区分系统确认、外部平台确认、应用确认和应用推断。`ANR_SUSPECTED`、`LOW_MEMORY_SUSPECTED` 适合观察趋势和筛选问题，不与 Android Vitals ANR 或 API 30+ `REASON_LOW_MEMORY` 做一比一对账。

## 扩展

### 🔸 低版本 ANR 文件可读性变化记录

官方文档记录的文件形态是：旧版本使用单个 `/data/anr/traces.txt`，较新版本使用多个 `/data/anr/anr_*` 文件。这里描述的是系统生成文件，不是应用可用的存储 API。

对 SDK 来说，可读性要按访问主体区分：

| 访问主体 | 可行性 | 说明 |
|----------|--------|------|
| 普通发布包 | 低 | 通常不能直接读取 `/data/anr/`；不能依赖此路径做自动上报 |
| adb / bugreport | 可用于受控诊断 | 官方流程以 adb 访问系统 trace；是否能直接 pull 取决于设备和权限 |
| 系统应用/厂商合作包 | 取决于授权 | 由签名权限、SELinux 和 ROM 策略决定，必须标注来源 |
| Play Console / Android Vitals | 可查看平台聚合 | 平台事件不一定能与自建 APM 的每个原始会话唯一对应 |

低版本 SDK 以“应用内 watchdog 现场 + 外部系统证据”组合归因。缺少系统 trace 或平台确认时，reason 保留 `ANR_SUSPECTED`。

### 🔸 自建 Process Exit Info 表结构建议

表结构要保留来源、检测时间和证据版本，避免查询层把推断改写成系统事实。

最小表结构可以按以下方式拆：

| 表 | 主键 | 内容 |
|----|------|------|
| `process_exit_event` | `event_id` | session、process、来源、系统 reason、旧版推断、检测时间与版本 |
| `process_exit_evidence` | `event_id + evidence_type` | crash 文件、watchdog、KOOM、memory snapshot、system record 的摘要 |
| `process_exit_attachment` | `attachment_id` | minidump、HPROF、trace、日志包的对象存储引用和隐私级别 |
| `process_exit_rule_result` | `event_id + rule_id` | 命中的规则、分数、排除原因，便于回溯误判 |

下面的伪 SQL 只展示事件表的来源隔离和时间语义，分区、索引与字段类型应按实际数据仓库调整。

```sql
CREATE TABLE process_exit_event (
    event_id STRING,
    app_version STRING,
    api_level INT64,
    device_fingerprint_hash STRING,
    boot_session_id STRING,
    session_id STRING,
    process_name STRING,
    pid INT64,
    process_start_elapsed_ms INT64,
    next_start_wall_time_ms INT64,
    next_start_elapsed_ms INT64,
    system_reason_code INT64,
    system_timestamp_ms INT64,
    legacy_reason STRING,
    reason_source STRING,
    confidence STRING,
    collector_version STRING,
    rule_version STRING,
    created_at TIMESTAMP
);
```

`system_reason_code` 只接收 `ApplicationExitInfo` 的公开 reason，`legacy_reason` 只接收应用规则结论。`reason_source` 记录 `android_system`、`external_platform`、`app_confirmed` 或 `app_inferred`。展示层可以按来源生成统一分类，但不能直接用 `coalesce(system_reason, legacy_reason)` 抹去证据等级。`next_start_*` 只表示发现旧会话的时刻；低版本无法得到精确退出时间时，字段应留空或保存上下界。

## 源码与文档锚点

- [Android 17 `ApplicationExitInfo`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java)：客户端值对象、公开 reason 与 trace 接口。
- [Android 17 `AppExitInfoTracker`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/AppExitInfoTracker.java)：服务端记录、关联和持久化实现。
- [Android Developers：`ApplicationExitInfo`](https://developer.android.com/reference/android/app/ApplicationExitInfo) 与 [`getHistoricalProcessExitReasons`](https://developer.android.com/reference/android/app/ActivityManager#getHistoricalProcessExitReasons(java.lang.String,%20int,%20int))：API 30+ 的公开契约。
- [Android 17 `lmkd`](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/) 与 [Android 10 `lmkd`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-10.0.0_r47/lmkd/)：当前实现与历史范围的 AOSP 参照。
- [Android 17 common kernel 6.18 tag](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6)：当前内核语义校准点，不用于替代旧设备的实际内核。
- [Android Developers：ANR](https://developer.android.com/topic/performance/vitals/anr)：ANR trace 文件形态与 adb 取证方式。
- [AOSP：ART TI](https://source.android.com/docs/core/runtime/art-ti)：Android 8.0+ JVMTI 能力、debuggable 和 agent 加载边界。
- [KOOM Java Leak README](https://github.com/KwaiAppTeam/KOOM/blob/master/koom-java-leak/README.md)：监控项、fork dump 流程与项目声明的版本范围。
