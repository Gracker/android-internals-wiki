---
title: "Android 11 以下进程退出归因方案"
chapter: "26.10"
section: "26.10"
drafted_date: "2026-05-16"
applicable_versions: "Android 5.0 (API 21) - Android 10 (API 29)"
last_verified: "2026-05-16"
last_verified_against: "Android Developers 2026-03 docs; AOSP master paths; KOOM master README"
confidence: medium
polish_count: 1
task6_state: reviewed
reviewed_by: "openclaw-task6"
reviewed_date: "2026-05-16"
task6_result: pass-light-edit
last_task6_at: "2026-05-16T03:16:00+08:00"
last_task6_review_log: "logs/review/2026-05-16-03-review.md"
last_task6_audit: "2026-06-07"
sources:
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationExitInfo"
  - type: official
    path: "https://developer.android.com/reference/android/app/ActivityManager#getHistoricalProcessExitReasons"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/anr"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ApplicationExitInfo.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/AppExitInfoTracker.java"
  - type: aosp
    path: "system/core/lmkd/"
  - type: material
    path: "DeepResearch/2026-05-08-applicationexitinfo-android11-below-alternatives.md"
  - type: material
    path: "DeepResearch/2026-05-09-application-exit-info-android11-alternatives.md"
  - type: open-source
    path: "github.com/KwaiAppTeam/KOOM/koom-java-leak/README.md"
  - type: structure
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 2.md"
  - type: structure
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 3.md"
  - type: structure
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 35.md"
  - type: structure
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 45.md"
  - type: structure
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 50.md"
tags: ["applicationexitinfo", "process-exit", "apm", "legacy-android", "stability"]
related_chapters: ["9.3", "19.24", "20.8", "23.7", "26.2", "26.9"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-15"
gap_source: "素材驱动/官方文档/章节深挖"
task9_state: reviewed
task9_reviewed_date: "2026-05-17"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-17T00:32:12+08:00"
last_task9_review_log: logs/deep-review/2026-05-17-00-deep-review.md
status: finalized
pipeline_stage: ready-to-publish
task9_result: pass-tech-review
task2b_state: fixed
task2b_result: fixed
p0: 0
p1: 0
p2: 3
task9_review_notes: "2026-05-17 Task9 00: pass-tech-review。Task2B 已修复 P0/P1；本轮仅保留既有 P2 来源路径/JVMTI 权限边界建议。Task6 已通过且 queue 无 pending，自动晋升 finalized / ready-to-publish。已写入 logs/deep-review/2026-05-17-00-deep-review.md。"
---

# 26.10 Android 11 以下进程退出归因方案

Android 11 以前，应用侧没有 `ApplicationExitInfo` 这类系统级退出记录。APM SDK 需要在下一次启动时把崩溃文件、ANR 线索、内存压力、上次心跳、进程状态快照放到同一个证据模型里，给出带置信度的退出原因。

这里的范围限定在 Android 5.0 到 Android 10。Android 11 及以上的系统能力详见 26.9 节；Crash 上报的 envelope 和去重详见 26.2 节；ANR 触发机制详见 9.3 节；低内存治理详见 23.7 节。

## 要点

### 🔹 API 30 以下缺少系统退出记录带来的观测缺口

`ApplicationExitInfo` 从 API 30 开始提供，应用可以通过 `ActivityManager.getHistoricalProcessExitReasons(packageName, pid, maxNum)` 读取历史退出记录，并拿到 `reason`、`timestamp`、`pid`、`processName`、`description` 等字段。系统侧由 `AppExitInfoTracker` 维护近期进程退出信息，相关容器类位于 `frameworks/base/core/java/android/app/ApplicationExitInfo.java`。低版本没有这层系统记录，进程退出时也不会自动给应用留下一条标准化事件。[已验证: 官方文档, developer.android.com/reference/android/app/ApplicationExitInfo] [已验证: AOSP master, frameworks/base/core/java/android/app/ApplicationExitInfo.java]

低版本的缺口集中在三类场景：

- 进程被系统或用户直接杀掉：`SIGKILL` 不能被应用捕获，LMKD、任务管理器清理、系统回收都可能表现为“上次没有正常退出”。
- ANR 之后进程被结束：系统会写 ANR trace，但普通应用不能稳定读取 `/data/anr/`，只能通过下次启动时的本地痕迹、日志平台、Play Vitals 或用户 bugreport 补证据。[已验证: 官方文档, developer.android.com/topic/performance/vitals/anr]
- OOM 前后现场丢失：Java heap OOM、虚拟内存耗尽、线程/fd 逼近上限都可能让写文件、分配对象、启动上报线程失败，进程内补救路径必须尽量短。

参考书的崩溃分析章节把“现场信息”拆成崩溃类型、线程、Logcat、机型、系统、内存、fd、线程数、业务路径等维度；这里沿用这种组织方式，但不复用原文表述。低版本退出归因也要按“证据”拆，而不是只给一个 reason。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 2.md] [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 3.md]

工程上可以先把退出分成四档：

| 档位 | 代表场景 | 可采证据 | 置信度 |
|------|----------|----------|--------|
| 已知崩溃 | Java 未捕获异常、Native signal | crash 文件、minidump、信号号、崩溃线程、符号化栈 | 高 |
| 已知卡死 | 前台 ANR、Service ANR、Broadcast timeout | 主线程 watchdog 栈、`am_anr` 事件、Play Vitals、bugreport trace | 中到高 |
| 疑似低内存退出 | LMKD、Java heap OOM 前置预警、线程/fd/虚拟内存耗尽 | 上次心跳、内存快照、`/proc/self/status`、KOOM dump、系统内存桶 | 中 |
| 未知退出 | 用户划掉、系统回收、升级、设备重启、ROM 策略 | session marker、boot id、版本号、启动耗时、前后台状态 | 低 |

这一层分档决定后面的产品口径：低版本不要把“疑似 LMKD”写成“系统确认 LMK kill”。更稳妥的做法是输出 `reason_guess + confidence + evidence[]`，把判断和证据一起上报。

### 🔹 Signal Handler、ANR traces、LMKD、dumpsys 的能力对照

低版本没有单一入口，只能把多种工具放到同一张对照表里。每个工具要明确能证明什么、不能证明什么、能不能在线上大规模使用。

| 手段 | 能覆盖的退出 | 线上可用性 | 主要限制 | 建议用途 |
|------|--------------|------------|----------|----------|
| `Thread.setDefaultUncaughtExceptionHandler` | Java crash | 高 | 进程状态已异常；不能覆盖 native crash、ANR、kill | 生成 Java crash envelope |
| Native signal handler / Breakpad / Crashpad | `SIGSEGV`、`SIGABRT` 等 native crash | 高，但实现成本高 | handler 中只能做 async-signal-safe 操作；要防二次崩溃 | 写 minidump、寄存器、maps、线程栈 |
| 主线程 watchdog | 疑似 ANR 前兆 | 高 | 不是系统 ANR 判定；会受采样间隔和误报影响 | 保存主线程栈、消息队列等待时间、业务路径 |
| `/data/anr/` traces | 系统 ANR | 低 | 普通 App 权限不足；新版文件名从单个 `traces.txt` 变成多个 `anr_*` | 实验室、bugreport、厂商合作 |
| Logcat event | `am_anr`、`am_crash`、`am_low_memory` 等 | 低到中 | Android 4.1 后第三方只能读自身日志；厂商和权限差异大 | 调试包、企业版、用户授权诊断 |
| LMKD / lowmemorykiller 线索 | 低内存杀进程 | 低 | `SIGKILL` 不可捕获；普通 App 无法直接监听系统 LMKD kill 事件 | 用内存压力和上次心跳做间接归因 |
| `dumpsys activity processes` / `meminfo` / `procstats` | 进程状态、adj、内存 | 低 | 多数命令需要 shell、dump 权限或调试环境 | 实验室复现、售后诊断、灰度白名单 |
| `/proc/self/*` | 当前进程内存、线程、fd、maps | 高 | 只能在进程还活着时采集；字段随内核版本有差异 | 崩溃前快照、周期性轻量采样 |

Native crash 的处理要把“捕获信号”和“可靠写文件”分开。信号到来时堆、锁、线程状态都可能不可用，handler 里应只做最小记录，并尽量交给独立 handler 进程或 fork 出的子进程处理。参考书在 Breakpad 章节强调了文件句柄泄漏、栈溢出、堆破坏、二次崩溃这些失败路径；低版本退出归因可以复用这个风险清单，但实现要以当前 SDK 的 crash 组件为准。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 2.md] [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 45.md]

ANR traces 不能按“线上 SDK 可直接读文件”设计。Android 官方文档说明，旧版本会有单个 `/data/anr/traces.txt`，新版本会有多个 `/data/anr/anr_*` 文件；这描述的是设备上的系统 trace 文件形态，不等于普通应用有读取权限。SDK 更稳妥的路径是在主线程长时间无响应时先保存本进程可拿到的栈、队列等待时间、前后台状态和最近业务事件，再把 Play Vitals、用户 bugreport、厂商诊断结果作为后补证据。[已验证: 官方文档, developer.android.com/topic/performance/vitals/anr]

LMKD 也不能写成“应用监听到系统杀进程”。LMKD 结束进程时使用的是不可捕获的 kill 路径，应用侧只能在进程还活着时采样 `PSS/RSS/VSS`、Java heap、线程数、fd 数、前后台状态、最近心跳；下次启动发现 marker 未闭合，再结合设备内存桶、上次前后台、OOM 前置预警判断。详见 23.7 节。

`dumpsys` 适合做验证工具，不适合作为普通线上采集入口。调试环境可以用 `dumpsys activity processes` 看 adj 和进程状态，用 `dumpsys meminfo <package>` 看内存分布，用 bugreport 关联 `am_anr`、`am_crash`、`lowmemorykiller` 线索；发布包里应把这类能力放在用户授权诊断或企业设备管理场景，不能默认调用。

### 🔹 KOOM fork dump 在低版本 OOM 现场保留中的位置

KOOM 的价值在于“进程死掉前保存 Java heap 现场”，不是替代 `ApplicationExitInfo`。它通过轮询 Java heap、线程数、fd、虚拟内存等阈值，在连续超过阈值后触发 HPROF dump；dump 过程使用 `Suspend ART VM -> fork VM process -> Resume ART VM -> Dump Hprof`，把传统 dump 对主进程的长时间冻结压到 20ms 以内。KOOM 官方 README 标注兼容 Android L 及以上，也就是 API 21+。[已验证: 开源项目, github.com/KwaiAppTeam/KOOM/koom-java-leak/README.md]

这套策略解决的是两个低版本问题：

- Java heap 泄漏或大对象堆积时，进程还没被系统杀掉，SDK 可以提前把 heap 现场保存下来。
- 传统 `Debug.dumpHprofData()` 容易让主进程冻结太久，用户可感知；fork 后由子进程写 HPROF，主进程更快恢复。

它不能解决的边界也要写清楚：

- 已经被 LMKD `SIGKILL` 的进程没有机会再 dump。
- Native 内存、图形缓冲、ashmem、mmap 文件导致的 RSS/PSS 压力，不一定能从 Java HPROF 中解释。
- fork dump 本身会带来 copy-on-write、文件 I/O、磁盘空间和隐私成本，必须受采样、频控和网络条件约束。
- ROM 对 hidden API、动态链接、ART 内部符号的限制会影响实现稳定性，接入前要做机型灰度。

在退出归因模型里，KOOM 产物适合放进 `evidence[]`，而不是直接改写 reason。例子：上次 session 未正常关闭，进程重启前 2 分钟内出现 Java heap 阈值连续超限，同时保存了 HPROF 报告，这时可以给 `LOW_MEMORY_SUSPECTED`，置信度为 medium；如果同时有系统侧 `ApplicationExitInfo.REASON_LOW_MEMORY`，才把它升为系统确认。低版本没有系统侧记录，所以不要升到 high。

参考书的内存现场章节把 `/proc/meminfo`、`/proc/self/status`、`/proc/self/maps`、fd、线程数作为崩溃分析素材；KOOM 补上的只是 heap dump 这一块。退出归因要把这些轻量快照和 HPROF 组合起来，避免只看 Java heap 就把所有退出都归成 OOM。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 3.md] [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 50.md]

### 🔹 权限、兼容性与厂商 ROM 差异

低版本退出归因的主要误差来自权限和 ROM 差异。能力表在设计阶段就要按“稳定可用、调试可用、厂商合作可用、不可依赖”四档标注。

| 线索 | 稳定性 | 风险 |
|------|--------|------|
| SDK 自己写的 crash/minidump/session marker | 高 | 写文件失败、进程二次崩溃、磁盘满 |
| `/proc/self/status`、`/proc/self/fd`、`/proc/self/maps` | 中到高 | 字段随内核版本变化；采样太频繁会有开销 |
| Logcat 自身日志 | 中 | 只能读到自身日志；系统事件依权限和版本变化 |
| `/data/anr/` | 低 | 普通应用不可读；文件名和保留策略随版本变化 |
| LMKD 事件 | 低 | 普通应用不能可靠监听；厂商实现差异大 |
| `dumpsys` | 低 | shell/调试权限；输出格式无稳定协议 |
| ROM 私有诊断接口 | 低到中 | 需要厂商合作；版本升级易断 |

Android 8.0 以后 JVMTI 可用于调试和监控类工具，但这不等同于低版本都能无成本拿到所有退出证据。JVMTI 更适合收集对象分配、线程创建、类加载、GC 事件等过程数据；退出归因只把它当作“进程活着时的补充证据”。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 53.md]

厂商 ROM 还会影响三类判断：

- 后台清理策略：同样是 marker 未闭合，有的设备更可能来自系统清理，有的设备更可能来自用户手动划掉。
- 日志保留策略：部分 ROM 会扩展系统日志或诊断接口，也可能限制 `/proc`、Logcat、ANR 文件访问。
- 进程优先级策略：前后台切换、保活策略、厂商电池管理会改变 OOM adj 和进程被回收的概率。

正文只能给通用模型，不能承诺某个厂商设备一定能拿到某类系统日志。若要把厂商能力写入线上平台，字段要带 `source=oem`、`rom_fingerprint`、`api_level`、`collector_version`，并和 AOSP/官方口径分开统计。

### 🔹 低版本归因结果如何并入 ApplicationExitInfo 模型

低版本自建模型最好贴近 `ApplicationExitInfo`，这样 Android 11+ 和 Android 10 以下可以进入同一张分析表。区别在于：API 30+ 的 `reason` 来自系统，低版本的 `reason` 来自 SDK 推断。

建议最小字段如下：

| 字段 | 说明 | 低版本来源 |
|------|------|------------|
| `event_id` | 单次退出归因事件 ID | SDK 生成 |
| `session_id` | 对应启动会话 | session marker |
| `package_name` / `process_name` | 包名和进程名 | SDK 运行时写入 |
| `pid` / `start_elapsed_ms` / `exit_detected_elapsed_ms` | 进程 ID、启动时间、发现退出时间 | marker + 下次启动扫描 |
| `reason` | 归一化原因 | SDK 推断枚举 |
| `confidence` | `high` / `medium` / `low` | 证据规则计算 |
| `evidence` | 证据列表 | crash 文件、watchdog、内存快照、KOOM、日志 |
| `trace_ref` | 本地文件或上传后对象 ID | crash/minidump/HPROF/ANR 栈 |
| `foreground_status` | 退出前前后台 | 会话标记 |
| `memory_snapshot` | Java heap、PSS/RSS、VSS、fd、线程数 | `/proc/self/*` + SDK |
| `privacy_level` | 原始、脱敏、仅摘要 | 上传策略 |

归一化 reason 可以保留和系统相近的含义，但名称要能表达推断性质：

| 低版本 reason | 映射到 Android 11+ 分析维度 | 判定条件 |
|----------------|-----------------------------|----------|
| `JAVA_CRASH_CONFIRMED` | `REASON_CRASH` | 未捕获异常文件完整，包含线程、栈、时间戳 |
| `NATIVE_CRASH_CONFIRMED` | `REASON_CRASH_NATIVE` | minidump 或 signal report 完整 |
| `ANR_SUSPECTED` | `REASON_ANR` | watchdog 主线程卡住、前台、无 crash 文件、后续重启；有 Play Vitals/bugreport 时升级 |
| `LOW_MEMORY_SUSPECTED` | `REASON_LOW_MEMORY` | 未闭合 marker + 内存/线程/fd/KOOM 证据；Java heap OOM、线程/fd 耗尽、LMKD kill 等细节作为 evidence 或 internal subReason 处理，不使用不存在的 `REASON_OOM` 公开常量 |
| `USER_OR_SYSTEM_KILL_UNKNOWN` | `REASON_USER_REQUESTED` / `REASON_OTHER` | marker 未闭合但证据不足 |
| `DEVICE_REBOOT_OR_UPDATE` | API 34+: `REASON_PACKAGE_UPDATED` / `REASON_PACKAGE_STATE_CHANGE`；API 30-33: 可能落到 `REASON_USER_REQUESTED` / `REASON_OTHER` | boot id 变化、版本升级、安装时间变化；设备重启映射到 `REASON_OTHER`，包更新/组件状态变化按 API 版本区分 |

规则引擎要允许“多证据并存”。例如进程退出前保存了 native minidump，同时下次启动发现 marker 未闭合，这种情况应归并为一个 native crash 事件，并把异常退出 marker 作为附加证据。去重键可参考 26.2 节：`process_name + pid + timestamp_bucket + top_frame/signature + session_id`。

和 26.9 的连接方式是同一张宽表分两条路径写入：API 30+ 使用系统 `ApplicationExitInfo` 填 `system_reason`，低版本使用 SDK 推断填 `legacy_reason`。查询时优先系统字段；没有系统字段再看低版本字段。这样图表可以按“确认退出原因”和“推断退出原因”分开展示。

### 🔹 灰度、采样与隐私边界

退出归因 SDK 容易越做越重。低版本尤其要从“默认轻量、问题用户加深、强证据才上传原始文件”三层设计。

默认层只保存小对象：session marker、最近一次前后台状态、Java heap/RSS/PSS 摘要、fd/线程数、最近关键业务事件摘要、crash envelope。这个层级要覆盖全量用户，写入路径要短，文件采用原子写策略，避免为了诊断退出原因再引入新的 I/O 问题。

加深层只对灰度人群、问题版本、特定机型或服务端命令开启。可增加主线程 watchdog 栈、本进程关键线程栈、`/proc/self/maps` 摘要、最近 N 秒的 SDK 日志、KOOM dump 触发。参考书的线上疑难问题章节强调全量日志、用户拉取、主动上报和动态诊断的组合；这里采用同样的分层思路，但退出归因不应默认打开高成本采集。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 35.md]

原始文件层只在强触发下上传：minidump、HPROF、maps、线程栈、用户日志都可能包含文件路径、账号片段、URL、业务参数、设备信息。上传前要做四件事：

- 脱敏：URL query、路径用户名、token、手机号、邮箱、业务 ID 按规则替换。
- 加密：本地文件和网络传输都要加密，服务端按最小权限读。
- 频控：按用户、版本、机型、reason、文件类型设置上限，避免问题版本引发诊断流量雪崩。
- 可撤回：诊断开关支持服务端关闭，用户反馈场景要能说明采集范围。

对外指标也要区分“确认”和“推断”。Java/native crash 可以进入确认崩溃率；`ANR_SUSPECTED`、`LOW_MEMORY_SUSPECTED` 更适合做趋势和线索，不应直接和 Android Vitals 的 ANR 或系统低内存退出做一比一对账。

## 扩展

### 🔸 低版本 ANR 文件可读性变化记录

官方文档给出的文件形态是：旧版本设备上可能是单个 `/data/anr/traces.txt`，新版本设备上可能是多个 `/data/anr/anr_*` 文件。[已验证: 官方文档, developer.android.com/topic/performance/vitals/anr]

对 SDK 来说，可读性要按访问主体区分：

| 访问主体 | 可行性 | 说明 |
|----------|--------|------|
| 普通发布包 | 低 | 通常不能直接读取 `/data/anr/`；不能依赖此路径做自动上报 |
| 调试包 + adb | 中 | 本地复现可用 `adb bugreport`、`adb pull`、Logcat 辅助分析 |
| 系统签名/厂商合作包 | 中 | 取决于厂商授权和 ROM 策略，必须单独标注来源 |
| Play Console / Android Vitals | 高 | 能看到线上 ANR 聚合和部分 trace，但不一定回流到自建 APM 原始事件 |

低版本 SDK 的 ANR 归因应以“应用内 watchdog 现场 + 外部系统证据”组合为主。只要缺少系统 trace 或平台确认，reason 就保留 `ANR_SUSPECTED`。

### 🔸 自建 Process Exit Info 表结构建议

这张表用于把 Android 11+ 系统记录和低版本推断记录放到同一查询面。字段可以分阶段补齐，但要保留扩展空间。

最小表结构可以按以下方式拆：

| 表 | 主键 | 内容 |
|----|------|------|
| `process_exit_event` | `event_id` | session、process、reason、confidence、时间、版本、设备桶 |
| `process_exit_evidence` | `event_id + evidence_type` | crash 文件、watchdog、KOOM、memory snapshot、system record 的摘要 |
| `process_exit_attachment` | `attachment_id` | minidump、HPROF、trace、日志包的对象存储引用和隐私级别 |
| `process_exit_rule_result` | `event_id + rule_id` | 命中的规则、分数、排除原因，便于回溯误判 |

这段伪 SQL 只表达字段关系，真实实现要按公司数据仓库规范调整分区和索引。

```sql
CREATE TABLE process_exit_event (
  event_id STRING,
  app_version STRING,
  api_level INT64,
  device_fingerprint_hash STRING,
  session_id STRING,
  process_name STRING,
  pid INT64,
  start_elapsed_ms INT64,
  detected_elapsed_ms INT64,
  system_reason STRING,
  legacy_reason STRING,
  confidence STRING,
  foreground_status STRING,
  collector_version STRING,
  created_at TIMESTAMP
);
```

`system_reason` 和 `legacy_reason` 分开存，能避免低版本推断污染 Android 11+ 的系统事实。分析平台展示时再做一层合并字段，例如 `normalized_reason = coalesce(system_reason, legacy_reason)`，并把 `confidence` 一起展示。
