---
title: "Android logd 日志系统性能与开销"
chapter: "1.37"
section: "1.37"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-08-12"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: medium
task6_state: reviewed
task9_state: reviewed
pipeline_stage: ready-for-review
last_rework_at: "2026-07-25T17:35:42+08:00"
last_rework_run_id: "20260725-173542-rework-6030a13a"
last_deep_review_at: "2026-08-12T20:51:36+08:00"
last_deep_review_run_id: "20260812-203556-deep-review-6030a13a"
sources:
  - type: aosp
    path: "system/logging/logd/ (android-17.0.0_r1)"
  - type: aosp
    path: "system/logging/liblog/ (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/core/jni/android_util_Log.cpp"
  - type: official
    path: "developer.android.com/ndk/reference/group/logging"
  - type: official
    path: "developer.android.com/topic/performance/app-optimization/additional-rule-types"
  - type: official
    path: "developer.android.com/privacy-and-security/risks/log-info-disclosure"
tags: [logd, logging, performance, rust, kernel, logcat, buffer]
related_chapters: ["1.4", "1.5", "1.34", "26.16"]
---

# 1.37 Android logd 日志系统性能与开销

一条 `Log.d()` 会经过级别判断、JNI 字符串访问、Unix Domain Socket（同一设备上进程间通信使用的本地套接字）发送、缓冲保存和读取客户端分发。分析这条链路时，需要区分三个边界：应用写日志与 logd 保存日志、logd 的服务端筛选与 logcat 的客户端筛选、EventLog 与 StatsD 原子事件（atom，即 StatsD 定义的一类结构化指标事件）的传输。以下行为以 `android-17.0.0_r1` 为准。

## 1. Android 17 的写入链路

### 1.1 从 `Log.d()` 到 `logdw`

普通 Java 文本日志的主路径如下：

```text
android.util.Log.d(tag, message)
  -> Log.println_native(LOG_ID_MAIN, DEBUG, tag, message)
  -> frameworks/base/core/jni/android_util_Log.cpp
     GetStringUTFChars(tag / message)
  -> __android_log_buf_write()
     __android_log_is_loggable()
  -> liblog LogdWrite()
     writev(header, payload)
  -> /dev/socket/logdw (AF_UNIX, SOCK_DGRAM)
  -> logd LogListener
  -> LogBuffer::Log()
```

这张路径图有四个需要记住的细节。

JNI 层通过 `GetStringUTFChars()` 取得 tag 和 message 的 Modified UTF-8 表示，随后释放。Modified UTF-8 是 JNI 使用的一种 UTF-8 变体。虚拟机是否复制字符串由实现和字符串内容决定，因此不能把它固定描述为“一次堆分配”，但编码访问和跨越 JNI 边界都有成本。

文本日志进入 `__android_log_buf_write()` 后会再次执行 `__android_log_is_loggable()`。`Log.d()` 的参数在进入 native 方法前已经求值，所以 native 级别过滤能省去套接字写入，却省不掉调用方已经完成的字符串拼接、对象 `toString()` 或 JSON 序列化。

Android 17 的 liblog 使用 `writev()` 一次提交头部和 payload（日志消息体）。旧版内核 logger 的 `/dev/log_main` 等节点只适合解释早期版本，不能用来描述当前路径。

`/dev/socket/logdw` 是 datagram socket，也就是保留消息边界、无连接的本地数据报套接字。logd 为它启用凭据传递，`LogListener` 从内核附带的 `SCM_CREDENTIALS` 取得发送方 PID、UID、GID；客户端不能靠伪造 payload 冒充另一个进程。SELinux 和文件/socket 权限约束谁能连接与写入，但这不表示每条日志都要在 liblog 中重新执行一次 SELinux 判定。

源码锚点：

- `frameworks/base/core/java/android/util/Log.java`
- `frameworks/base/core/jni/android_util_Log.cpp`
- `system/logging/liblog/logger_write.cpp`
- `system/logging/liblog/logd_writer.cpp`
- `system/logging/liblog/README.protocol.md`
- `system/logging/logd/LogListener.cpp`

### 1.2 普通日志在过载时会丢，不会等待 logd

`LogdWrite()` 为普通日志使用 `SOCK_NONBLOCK`，也就是让写入在套接字暂时不可用时立即返回。这里的普通日志包括 `main`、`system`、`radio`、`events`、`stats`、`crash` 等合法 buffer；`security` 是受权限控制的特殊二进制 buffer，liblog 为它另设阻塞 socket。

当 logd 来不及接收、socket 返回表示“稍后再试”的 `EAGAIN` 时，liblog 记录一次丢弃（drop）并返回。后续写入恢复且 liblog 内部日志允许输出时，它会尝试写入 event tag `1006`（`liblog`），报告此前丢弃的数量。这与旧版 `chatty` 行属于不同机制。

因此，普通应用日志风暴的风险主要是：

- 调用方持续做格式化、JNI 转换和系统调用，消耗 CPU 与电量；
- socket 过载后新日志丢失，关键现场被噪声覆盖；
- logd 忙于接收、压缩、裁剪和服务读者，增加系统负载；
- 日志对象和中间字符串增加分配压力。

把普通日志描述成“socket 满后 `write()` 阻塞主线程并导致 ANR”不符合 Android 17 的 liblog 实现。若 trace 显示线程长期停在日志相关调用，应继续检查自建日志框架的锁、磁盘输出端（sink）、格式化、崩溃收集器或厂商改动，不能直接归因于 AOSP `logdw` 的反压（下游处理变慢后迫使上游等待）。

也不要对 `EAGAIN` 做无间隔重试。这样会把允许丢日志的保护机制变成 CPU 自旋。

### 1.3 payload 上限与长消息

Android 17 的 `LOGGER_ENTRY_MAX_PAYLOAD` 为 4068 字节。`LogdWrite()` 会把超出上限的直接 payload 截到可发送范围。Java `Log.printlns()` 处理长文本和堆栈时，会根据消息体的字节预算和换行位置拆成多条，再逐条调用原生写入函数。

这会带来两个结果：

- 一条很长的异常堆栈可能对应多次 JNI 和 `writev()`；
- 直接调用底层打印接口时，尾部信息可能被截断。

线上诊断信息应把稳定标识和错误类别放在前面，避免把唯一有用的字段留到长消息末尾。结构化数据也不应无上限地序列化进 logcat。

## 2. logd 如何接收和保存日志

### 2.1 `LogListener` 的两条接收实现

logd 从 init 继承 `logdw` socket。Android 17 的 `LogListener` 有两种接收方式：

- `android.logd.flags.use_iouring` 开启且内核支持时，使用 `IOUringSocketHandler` 的 multishot `recvmsg`，即一次提交接收请求后连续取得多个完成事件；
- 条件不满足时，使用传统 `recvmsg()` 循环。

两条路径都会校验包长度、读取发送方凭据，再调用 `LogBuffer::Log()`。io_uring 是 Linux 提供的异步 I/O 接口；这里是否使用它，由 aconfig 功能开关和运行时支持共同决定，不能据此断言所有 Android 17 设备都已启用。

### 2.2 buffer 名称、容量与设备差异

Android 17 定义了八个 log ID；每个 ID 对应一类独立的日志缓冲区：

| Buffer | 常见内容 |
|---|---|
| `main` | 应用与通用 native 日志 |
| `radio` | radio/telephony 相关日志 |
| `events` | EventLog 二进制事件 |
| `system` | framework/system 组件的文本日志 |
| `crash` | 崩溃相关日志 |
| `stats` | logd 协议中的 stats 二进制 buffer |
| `security` | 受权限控制的安全事件 |
| `kernel` | logd 收集的内核日志 |

`LogSize.h` 给出的通用默认值是每个 buffer 256 KiB，最小值 64 KiB，最大值 256 MiB。不可调试的低内存（low-RAM）设备会选择 64 KiB。产品配置和运行时设置可以改变结果；Android 17 能否用属性覆盖容量，还受设备类型与 `debuggable` 条件约束，不能用一张固定容量表代表所有设备。

应直接查询目标设备：

```bash
adb logcat -g
```

输出会列出各 buffer 的环形缓冲区大小（ring buffer size）、已使用量、可读量以及单条上限。`logcat -G` 可以按 `-b` 选择修改运行时大小，但通常需要相应权限；调大容量只能延长日志保留窗口，不能消除写入成本或 socket 丢包。

### 2.3 默认实现使用序列化数据块

Android 17 的 `logd.buffer_type` 默认值是 `serialized`，表示把日志编码后按数据块保存；另一个可选值为 `simple`。默认实现不是定长的 `LogBufferEntry[]` 数组。

`SerializedLogBuffer` 为每个 log ID 维护一份 `SerializedLogChunk` 列表；chunk 是一批连续保存的序列化日志。当前 chunk 保持可追加状态，写满或封存后的 chunk 使用 Zstd 1 级压缩。用于容量计算的总大小超过目标值时，logd 从较老的 chunk 开始裁剪。读取客户端需要访问压缩 chunk 时才解压，并通过引用状态避免正在读取的数据被释放。

这套设计对外仍表现为“只保留有限窗口，并淘汰旧数据”，内部管理单位则是 chunk 和序列化条目。分析裁剪成本、内存占用或慢速读取客户端行为时，需要以该实现为准。

### 2.4 `chatty` 属于历史机制

`system/logging/logd/README.compression.md` 的标题直接说明了 Android S 的变化：使用日志压缩取代 Chatty。Android 17 的 logd 源码没有当前默认路径所需的 `ChattyLogBuffer.cpp`，默认的 serialized buffer 也不会按旧说明插入 `uid=... expired ... lines` 来表示重复日志。

旧设备的日志中仍可能看到 `chatty`，AOSP 的事件 tag 表也保留了历史名称，但这不足以证明 Android 17 默认使用旧的重复行合并策略。当前版本有两个相关但不同的现象：

- buffer 超限：logd 裁剪较老 chunk；
- writer socket 过载：liblog 遇到 `EAGAIN` 丢弃新写入，并可能用 event tag `liblog` 报告数量。

## 3. logcat 的读取与过滤边界

### 3.1 reader socket 与每个客户端的线程

logcat 连接 `/dev/socket/logdr`。该 reader socket 使用 `SOCK_SEQPACKET`，这种套接字可靠、面向连接，并保留每条消息的边界。logd 接受连接和读取命令后，会为每个客户端创建独立的 `LogReaderThread`。服务端命令支持的主要筛选条件包括：

- log ID mask；
- PID；
- 起始时间或日志序号（sequence）；
- tail 条数；
- 非阻塞、等待缓冲区即将回绕后返回（wrap）等读取模式。

安全 buffer 和跨 UID 读取还受凭据与权限约束。面向应用公开的 NDK logging API 通常写入 `main`；读取全局 logcat 所需的 `READ_LOGS` 也只授予受信任的特权组件。

### 3.2 tag 与正则表达式在 logcat 客户端执行

`*:S MyApp:V` 一类 tag/priority（标签/优先级）规则由 logcat 进程的 `android_log_shouldPrintLine()` 判断。`--regex` 也由 logcat 的 `std::regex_search()` 执行。它们不会作为标签表或正则表达式交给 logd。

这个边界会直接影响性能判断：

- `--pid` 能直接交给 logd 执行，减少服务端发送的数据；
- `-b` 能缩小服务端读取的 buffer 集合；
- tag/priority 和 `--regex` 主要减少终端输出，不一定减少 logd 到 logcat 的传输；
- 复杂正则消耗的是 logcat 客户端 CPU，不能写成 logd 因正则匹配而升高 CPU。

长期采集时，可以先缩小服务端范围，再添加客户端显示过滤。例如：

```bash
adb logcat -b main --pid="$(adb shell pidof -s com.example.app)" \
  -v threadtime 'MyApp:V' '*:S'
```

这里 `-b main` 和 `--pid` 控制服务端数据范围，后面的过滤规则（filter spec）决定 logcat 打印哪些 tag。`$(...)` 命令替换应在主机 shell 中执行；多进程应用还要确认 `pidof -s` 选中的进程是否符合排查目标。

### 3.3 慢速读取客户端与多个 reader

每个 reader（读取客户端）都有独立线程和读取状态。多开 logcat 会增加线程、解压和 socket 发送工作，但 AOSP 没有给出“每个客户端固定占用多少 KB”或“超过多少个必然变慢”的通用阈值。

当 reader 的读取位置已经落到被裁剪的数据之后，serialized buffer 会让它跳过已回收的旧 chunk，并记录相应警告。读 socket 也配置了发送超时，避免一个停止读取的客户端长期占住发送线程。是否达到瓶颈取决于日志速率、buffer 容量、读取客户端数量、输出介质和设备性能，需要在目标设备上测量。

## 4. 容易混淆的两条旁路

### 4.1 EventLog 与 StatsD atom

`LOG_ID_EVENTS` 保存 `EventLog` 风格的二进制事件，其中的 tag 可由事件 tag 表解析。现代 StatsD atom 的主要传输路径不同：Android R 及以后，`packages/modules/StatsD/lib/libstatssocket` 通过独立的非阻塞 Unix datagram socket `/dev/socket/statsdw` 向 statsd 写入。

因此，不能把高频 StatsD atom 描述成“先写满 logd 的 events buffer”。StatsD 有自己的 socket、丢失报告和限流规则；logd 虽然仍定义 `LOG_ID_STATS`，但不能由名称推断所有 atom 都经 logd 保存。分析 atom 丢失应查看 `libstatssocket` 与 statsd 的指标；分析 EventLog 保留窗口才需要查看 `events` buffer。

源码锚点：

- `packages/modules/StatsD/lib/libstatssocket/Android.bp`
- `packages/modules/StatsD/lib/libstatssocket/statsd_writer.cpp`
- `system/logging/liblog/log_event_list.cpp`

### 4.2 system/logging 中的 Rust 代码

`system/logging/rust/` 包含 Rust logging API、结构化日志和 liblog 绑定等客户端代码。这个目录的存在不代表 logd 守护进程已经改写为 Rust。

在 `android-17.0.0_r1` 中，`logd/Android.bp` 构建的是 `cc_binary`，核心文件仍包括 C++ 的 `main.cpp`、`LogListener.cpp`、`SerializedLogBuffer.cpp`、`LogReader.cpp` 和 `LogReaderThread.cpp`。`logd/` 下没有负责这些核心职责的 `.rs` 实现。基于 `RwLock<VecDeque<...>>`、`mio` 或“Rust 版吞吐提升比例”的描述都得不到该版本源码支持，不应写入 Android 17 的结论。

## 5. 应用侧怎样减少日志开销

### 5.1 消除无效的参数求值

这段代码即使最终被 liblog 级别过滤，参数仍已在 Java/Kotlin 层构造：

```kotlin
Log.d(TAG, "user=${user.name}, payload=${encodeLargePayload(data)}")
```

高频路径应在格式化前判断是否需要输出，并由构建类型或应用日志组件统一控制级别策略：

```kotlin
if (BuildConfig.DEBUG && Log.isLoggable(TAG, Log.DEBUG)) {
    Log.d(TAG, "user=${user.name}, payload=${encodeLargePayload(data)}")
}
```

这项条件判断可以跳过字符串插值和 `encodeLargePayload()`。如果只在调用外再包一层普通函数，但仍传入已经构造的 `String`，就无法取得同样效果。自建 logger 若支持用 lambda 延迟求值，应确认 lambda 只在日志级别允许时执行。

### 5.2 用 R8 按级别删除 release 日志

当前 R8 文档提供了专门的 `-maximumremovedandroidloglevel`。例如，release 构建可以删除 verbose、debug 和 info 日志：

```proguard
# INFO 对应数值 4；删除 INFO 及以下级别。
-maximumremovedandroidloglevel 4
```

R8 会处理匹配的 `Log.*` 与 `Log.isLoggable()` 调用。这个规则近年才进入正式文档，使用前要确认项目实际采用的 R8/AGP 版本支持它。规则应只进入 release 变体，并通过反编译、mapping/usage 输出和自动化测试确认结果。若只想作用于特定包或方法，可追加类规范（class specification）。

`-assumenosideeffects` 也能声明某些日志方法无副作用，但它属于强制优化假设。调用参数中具有可观察副作用的函数，不应依赖“日志调用被删后一定连带消失”。构建期删除仍应配合调用前的条件判断。

### 5.3 release 不会自动静音

`debuggable=false` 不会自动删除所有 `Log.d()`。liblog 会按 tag 属性和默认优先级判断是否写入，但调用点、参数求值和 JNI 入口仍可能发生。发布策略应按信息价值设计：

| 内容 | 发布版处理建议 |
|---|---|
| 高频调试轨迹 | 构建期删除 |
| 可恢复状态变化 | 聚合、限频，只保留诊断所需字段 |
| 警告与错误 | 保留稳定错误码和必要上下文 |
| 凭据、令牌、完整账号、原始请求体 | 禁止写入 |

采样率不能机械固定成“每 100 次一次”。故障可能集中在被跳过的请求，多线程共享计数器也会改变样本分布。需要采样时，应明确采样单位、用于稳定决定同一对象是否入样的 key、时间窗口和紧急开关，并在构造昂贵消息之前作出决定。

### 5.4 隐私边界

Android 4.1 以后，全局 `READ_LOGS` 读取能力受到特权权限限制，但预装特权组件、bugreport、工程构建和设备厂商诊断工具仍可能接触日志。限制读取权限不能抵消敏感数据已经写入系统日志的风险。

发布版日志应采用字段白名单，令牌、密码和会话密钥必须完全删去；掩码只适合允许显示部分信息的字段。异常对象也要审查，因为服务端响应、URI 查询参数和用户输入可能通过异常文本进入日志。

官方依据：[Log Info Disclosure](https://developer.android.com/privacy-and-security/risks/log-info-disclosure) 与 [R8 Additional rule types](https://developer.android.com/topic/performance/app-optimization/additional-rule-types)。

## 6. 设备上如何定位日志开销

### 6.1 确认容量和丢失现象

以下命令分别观察容量和统计信息：

```bash
adb logcat -g
adb logcat -S
adb shell pidof logd
```

`-S` 输出 logd 统计，可结合 `--pid` 查看特定进程；具体字段和可见范围受构建与权限影响。不要从 `/proc/<pid>/fdinfo` 推断 logd 的逻辑 buffer 已用量，它反映不了 serialized chunks 的占用与裁剪状态。

### 6.2 区分调用方成本和守护进程成本

一次有效测量至少要区分四组事件：

1. 调用前消息格式化与对象分配；
2. 应用进程的 JNI、`writev()` 次数及 `EAGAIN`；
3. logd 的 CPU 调度、接收、压缩和裁剪；
4. logcat reader 的解压、正则匹配与输出介质。

Perfetto 可同时观察应用与 logd 的线程调度、CPU 时间和频率变化。`userdebug`/`eng` 环境还可用 CPU 采样工具 simpleperf 分析应用或 logd 热点；短时使用系统调用跟踪工具 `strace`，能验证应用是否频繁调用 `writev()`，以及调用是否返回 `EAGAIN`。Android 的 bpfloader 负责加载系统批准的 BPF 程序，并不表示普通应用可以随意加载自定义 BPF 程序，因此排障手册不应把它写成通用方案。

AOSP 自带 `system/logging/liblog/tests/liblog_benchmark.cpp`，其中有轻载写入和高压写入基准。结果取决于 SoC、内核、构建类型（build type）、buffer 和 logd 负载，不能据此给出跨设备固定的“单条若干微秒”。比较优化前后的结果时，应固定消息长度、日志级别、CPU 状态和读取客户端配置，并同时记录丢失量；只统计成功循环次数，会把日志丢弃误判为吞吐提升。

### 6.3 一个实用的判断顺序

- trace 中调用方在编码或字符串构造上耗时：减少参数工作；
- 应用 `writev()` 很密集且出现 `EAGAIN`：降低写入率，保留错误码和聚合结果；
- logd CPU 高：检查全机日志源、buffer 裁剪与 reader 数量；
- 只有某个 logcat 进程 CPU 高：检查客户端正则、格式化和文件输出；
- 线上现场缺失：同时检查 liblog socket 的新日志丢弃和 logd 的旧数据裁剪。

## 7. 版本演进边界

| 版本阶段 | 相关变化 |
|---|---|
| Android 4.x 及更早 | 历史实现使用内核 logger 字符设备；只用于阅读旧源码和旧设备问题 |
| Android 5.0 起 | 用户态 logd 与 Unix socket 成为现代日志主路径 |
| Android S | serialized compression 取代旧 Chatty 方案，详见 `README.compression.md` |
| Android R 起 | StatsD 原生 atom 经独立 statsd socket 传输，应与 EventLog 路径分开分析 |
| Android 17 / API 37 | logd 核心仍为 C++；默认使用 serialized/Zstd buffer；接收端具备由功能开关控制的 io_uring 路径；Rust logging 代码位于客户端侧 |

版本演进可以保留旧路径，供分析历史 trace 时参考；当前行为判断均以 `android-17.0.0_r1` 为准。现代应用日志链路不依赖 kernel 日志驱动实现，无需引入 `android17-6.18-2026-06_r6` 的额外假设。

## 8. 源码核查清单

复核或移植这些结论时，可从这些文件开始：

- Java/JNI：`frameworks/base/core/java/android/util/Log.java`、`frameworks/base/core/jni/android_util_Log.cpp`
- liblog 写端：`system/logging/liblog/logger_write.cpp`、`logd_writer.cpp`、`README.protocol.md`
- logd 接收：`system/logging/logd/LogListener.cpp`、`flags/logd_flags.aconfig`
- buffer：`LogSize.cpp`、`SerializedLogBuffer.cpp`、`SerializedLogChunk.cpp`、`CompressionEngine.cpp`
- reader：`LogReader.cpp`、`LogReaderThread.cpp`
- logcat 客户端过滤：`system/logging/logcat/logcat.cpp`
- 历史 Chatty 边界：`system/logging/logd/README.compression.md`
- StatsD：`packages/modules/StatsD/lib/libstatssocket/statsd_writer.cpp`

这些锚点均按 `android-17.0.0_r1` 核查。产品分支若修改了 liblog socket flags、logd buffer type 或权限策略，应以设备对应源码和运行时命令输出为准。
