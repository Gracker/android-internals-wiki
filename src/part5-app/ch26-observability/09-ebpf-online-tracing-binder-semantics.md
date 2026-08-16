---
title: "eBPF 在线追踪与 Binder 语义重建"
chapter: "26.9"
section: "26.9"
status: "finalized"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-08-15"
last_source_verified_at: "2026-08-15"
last_verified_against: "WOOTdroid arXiv:2604.27830 v1, current Android eBPF and ProfilingManager docs, AOSP android-17.0.0_r1 system/bpf, and android17-6.18-2026-06_r39 Binder sources retrieved 2026-08-15; the cited r6 Binder files are byte-identical to r39"
confidence: high
sources:
  - type: legacy-reference-preserved
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 6.md"
  - type: legacy-reference-preserved
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 13.md"
  - type: legacy-reference-preserved
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 35.md"
  - type: legacy-reference-preserved
    path: "论文/Android-2026-05-03-WOOTdroid/03-精读.md"
  - type: paper
    path: "https://arxiv.org/abs/2604.27830"
  - type: official
    path: "https://source.android.com/docs/core/architecture/kernel/bpf"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing/profiling-manager/how-to-capture"
  - type: official
    path: "https://developer.android.com/privacy-and-security/risks/log-info-disclosure"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/bpf/+/refs/tags/android-17.0.0_r1/loader/bpfloader.rs"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/include/uapi/linux/android/binder.h"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/drivers/android/binder.c"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/drivers/android/binder_trace.h"
  - type: internal
    path: "src/part3-tools/ch14-other-tools/23-ebpf-performance-analysis.md"
  - type: internal
    path: "src/part1-fundamentals/ch01-architecture/04-binder.md"
  - type: internal
    path: "src/part5-app/ch26-observability/05-online-troubleshooting.md"
tags: [ebpf, binder, observability, tracing, online-diagnosis, security-audit]
related_chapters: ["1.4", "13.9", "14.23", "26.5"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_draft_polish_at: "2026-08-15T20:16:41+08:00"
last_draft_polish_run_id: "20260815-201641-gracker-writing-470"
last_review_finalize_at: "2026-08-15T20:16:41+08:00"
last_review_finalize_run_id: "20260815-201641-gracker-writing-470"
last_rework_at: "2026-08-15T20:16:41+08:00"
last_rework_run_id: "20260815-201641-gracker-writing-470"
---

# 26.9 eBPF 在线追踪与 Binder 语义重建

线上排障通常从日志、应用埋点和短时间的系统跟踪（system trace）入手。它们未覆盖的系统调用与 Binder 边界，可以在具备系统权限的设备上用 ftrace 或 eBPF 补充：ftrace 是 Linux 内核自带的事件追踪框架；eBPF 是在内核内运行、先经安全校验的受限程序；Binder 是 Android 主要的进程间通信（IPC）机制。这里的“在线”只表示设备运行期间持续或按条件追踪，普通应用仍无权在商店发布包中自行加载 BPF 程序。

适用范围为 Android 12～17。平台源码核对到 `android-17.0.0_r1`；Binder 内核接口与追踪事件核对到 `android17-6.18-2026-06_r39`。文末保留的 r6 链接是这篇文章原有的历史锚点，经复核，涉及的三个 Binder 文件与 r39 内容一致。WOOTdroid 的正式实验使用两台已 root（取得超级用户权限）的 Pixel 9，系统为 Android 16；论文另用 Pixel 7 和 Pixel 9 检查逐系统调用 tracepoint 的可用性。实验结果不能直接外推到 Android 17 的量产 user build、其他芯片平台（SoC）或厂商内核。

这类能力适合设备厂商（OEM）系统集成、开放额外调试能力的 userdebug 测试机和经过授权的安全实验。普通应用应优先使用应用日志、系统管理的性能分析 API `ProfilingManager`、Android Vitals，以及用户授权生成的 bugreport（系统诊断包）。

## ftrace 的能力与事件丢失边界

ftrace 是 Android / Perfetto 系统追踪的重要数据源，适合观察调度、频率、Binder 和输入输出（I/O）等内核事件。它通常把事件写入“每 CPU 缓冲区”，也就是每个处理器核心各自维护的环形存储区。读取端消费不及时且空间耗尽时，较早的事件可能被覆盖。短时间人工诊断可以通过扩大缓冲区、缩小事件集和控制复现步骤来降低风险；常驻审计还要控制持续事件率、读取阻塞、存储占用和耗电。

ftrace 本身能提供不少信息。Android 17 的 Binder 驱动提供 `binder_transaction`、`binder_transaction_received`、`binder_command`、`binder_return` 等 tracepoint；tracepoint 是内核预先定义、供追踪工具订阅的事件点。这些事件适合观察事务路由和驱动阶段，但不携带完整的 `Parcel` 参数，也不属于 Android 应用 SDK 的稳定契约。若要还原方法含义，还需建立 transaction code（接口内的方法编号）与具体接口版本之间的映射。

WOOTdroid 关注系统调用审计：WDSys 在 eBPF 侧过滤并编码事件，再通过 perf buffer（BPF 的事件传输缓冲区）交给用户态进程。论文让它与基于 ftrace 的系统调用追踪同时运行，再比较两份日志。这个实验说明缓冲和读取架构会影响观察结果，但无法证明任一方案获得了全部事件，因为实验没有独立真值（ground truth），也就是一份可以确认所有应出现事件的第三方记录。

生产追踪至少要记录以下健康度：

| 维度 | 要回答的问题 | 约束 |
|---|---|---|
| 窗口与触发 | 常驻摘要、故障前滚动窗口，还是人工抓取 | 明细窗口有时长、事件类型和设备范围限制 |
| 内核侧丢失 | map（内核与用户态共享的键值存储）更新、perf buffer 输出或 BPF ring buffer 空间预留是否失败 | 每条丢失路径分别计数，计数器本身也要防溢出 |
| 用户态积压 | 读取进程（reader）的延迟、队列长度和落盘速度是否恶化 | 达到项目阈值后停止参数采集或关闭追踪 |
| 关联完整性 | 进入/退出事件（enter / exit）、请求/接收事件和应用阶段能否匹配 | 缺失一端时标记为 partial（记录不完整），不补造时长 |
| 权限来源 | root、userdebug、OEM 系统镜像分别允许什么 | 能力报告必须带构建类型（build type）、内核和策略版本 |
| 数据类别 | 只保留元数据，还是读取 Parcel 内容 | 参数读取默认关闭，并由接口白名单和授权控制 |

“没有观察到事件”只说明这套采集流程没有产出该事件。若丢失计数、过滤规则或权限状态不完整，就不能据此认定“事件没有发生”。


## Android eBPF 系统调用追踪路径

Android 平台自身就在使用 eBPF。AOSP 文档说明，系统镜像中的 BPF 对象由 Android BPF loader 在启动阶段加载，所需 map 和 program 会 pin 到 BPF 文件系统；pin 表示给内核对象建立持久路径，使 loader 退出后其他进程仍可按权限访问。Android 17 的 `system/bpf` 源码还显示，平台程序受 loader 描述项和文件权限管理，带 `skip_on_user` 标记的对象会在 `ro.build.type=user` 时跳过。它属于系统集成机制；普通应用即使把编译后的 `.o` 对象文件放进自身目录，也不会因此获得加载权。

WDSys 的论文原型可以拆成五个阶段：

1. **入口**：论文作者在 Pixel 7 和 Pixel 9 上没有找到可用的逐系统调用 tracepoint，因此改挂 `raw_syscalls:sys_enter` 与 `raw_syscalls:sys_exit`，再按 syscall id（系统调用编号）分派。这个设备观察不适用于所有 Android 12～17 内核，部署前要枚举目标内核实际提供的 tracepoint。
2. **过滤与配对**：enter 事件保存参数，exit 事件保存返回值。过滤器按 UID（应用或系统主体标识）、TGID（Linux 线程组标识，通常对应进程）、syscall id 和项目规则减少事件。线程提前退出、tail call 失败，或 map 更新与查询失败，都可能只留下进入或退出一侧的记录。
3. **复杂度分段**：论文用 program array（一张保存 BPF 程序引用的 map）和 tail call（从一个 BPF 程序直接跳到另一个程序）拆分逻辑，以满足 verifier 对栈空间和程序复杂度的限制。verifier 是内核在加载前执行的安全检查器。tail call 属于该原型的程序组织方式，Android 系统调用追踪协议没有规定必须这样实现。
4. **传输**：WOOTdroid 使用 perf buffer，论文也称其为 perf ring buffer。`BPF_MAP_TYPE_RINGBUF` 是另一种 BPF map 类型；两者在空间预留、事件提交、跨 CPU 顺序和丢失统计上都有差异，设计文档应写明具体机制。
5. **用户态消费**：读取进程负责拼接分片、统一时间表示、落盘和审计。内核程序成功输出只表示事件进入传输缓冲区，仍需单独确认读取进程已经消费并持久化。

为了读取带 tag 的用户地址，论文的 Pixel 原型使用了固定按位掩码。这里的 tag 是 arm64 可放在地址高位的标记；TBI（Top Byte Ignore）允许处理器忽略地址最高字节，MTE（Memory Tagging Extension）则用标签检测内存访问错误。该常量依赖所测设备的虚拟地址布局，不能照搬成 Android 17 通用方案。去除地址标签前，需要结合目标 arm64 内核、TBI/MTE 配置、BPF helper（内核提供给 BPF 程序的受控函数）行为和进程 ABI（应用二进制接口）验证；验证失败时只记录元数据，不读取用户缓冲区。

eBPF 在这里更像内核侧筛选器：尽早排除无关事件，只送出长度有上限的结构化数据。字符串、用户栈和可变长 payload（事件携带的数据内容）都会增加校验、内存读取、传输带宽和隐私成本。代码运行在内核内，也无法消除这些开销。

## Binder 语义重建的关键问题

应用调用 AIDL Proxy 后，接口 token 和参数会按该接口版本的规则写入 `Parcel`，再由 `IBinder.transact()` 进入 Binder 驱动。AIDL 是 Android 接口定义语言，Proxy 是 AIDL 工具生成的客户端代理；`Parcel` 是 Binder 用来顺序编码参数的二进制容器；接口 token 通常是标识接口的 descriptor 字符串。驱动只处理 transaction code、flags（同步、oneway 等事务标志）、目标 handle（进程内的 Binder 引用编号）、数据缓冲区和对象 offsets（特殊 Binder 对象在缓冲区中的位置表）。方法名与 Java/Kotlin 参数类型不在 Binder 内核 ABI 中，驱动无法直接提供这些语义。

Android 17 / 6.18 的 UAPI（内核向用户空间公开的二进制接口）可以从 `include/uapi/linux/android/binder.h` 核对。`BINDER_WRITE_READ` 的参数是 `binder_write_read`，其中 `write_buffer` 指向一串 Binder 命令；`BC_TRANSACTION` 和 `BC_TRANSACTION_SG` 后面跟着大小不同的事务结构。驱动的 `binder_ioctl_write_read()` 先用 `copy_from_user()` 读取 `binder_write_read`，再分别处理写入与读取部分。这里的 ioctl 是进程通过文件描述符向设备驱动发送控制命令的系统调用。

WDBind 在 `raw_syscalls:sys_enter` 事件中运行于内核态，但读取的数据仍来自调用进程的用户地址。它观察的是驱动执行 `copy_from_user()` 之前的 `binder_write_read` 和 `Parcel`，还未经过驱动复制、校验和 Binder 对象重写。因此，采集器读到的字节与驱动稍后使用的字节之间可能出现 TOCTOU（检查时与使用时数据发生变化）、短读、地址标签和 ABI 兼容风险。

语义重建可分为四层：

| 层级 | 可验证的数据 | 仍然缺少什么 |
|---|---|---|
| syscall | `ioctl` 参数、返回值、PID / TID（进程/线程标识）与时间 | fd（文件描述符）是否指向 Binder 设备、命令流内容与事务结果 |
| Binder UAPI | `BINDER_WRITE_READ`、命令字、transaction code、flags、数据长度 | Java 方法名与字段类型 |
| Parcel | interface token、字节序列、对象 offsets | 当前接口版本对应的参数布局 |
| 签名表 | descriptor、transaction code、方法与参数类型 | 厂商（vendor）接口、动态注册接口以及复杂自定义序列化 |

一套可审计的解析过程应完成这些检查：

1. 证明 fd 对应正确的 Binder 设备节点，不能只因 ioctl cmd 数值相同就认定是 Binder。
2. 校验 `write_size`、指针、命令边界和单次读取上限；一个 write buffer 可以包含多条命令。
3. 按目标 UAPI 同时识别 `BC_TRANSACTION`、`BC_TRANSACTION_SG` 等已支持命令；未知命令停止当前段解析，不继续猜偏移。
4. 检查 `data_size`、`offsets_size` 和对象位置是否满足大小上限及 ABI 要求的内存边界。读取失败时保留 transaction code、大小与错误类型。
5. 用与 `Build.FINGERPRINT`（完整系统构建标识）、AIDL 接口版本和采集器版本绑定的签名表解码。不能假定同一个 transaction code 在不同系统版本中仍对应同一方法。

WOOTdroid 论文通过设备上的 Java reflection（运行时反射）生成 Android framework（系统框架）AIDL 签名表。原型能够解析基本类型、`String` 和部分 Binder 对象，但不会继续解析 fd 或指针指向的内容，也不处理事务回复（transaction reply）。复杂 `Parcelable`（可写入 `Parcel` 的结构化对象）、厂商接口和动态注册接口也未得到系统性覆盖。论文把 WDBind 的完整性和性能评估列为后续工作。

只需要路由和时序、不需要参数内容时，Android 17 的 Binder tracepoint 更合适。`binder_transaction` 给出事务调试编号、目标进程或线程、reply 标记、code 和 flags，`binder_transaction_received` 表示目标侧收到事务。它们仍受 ftrace 权限和缓冲区限制；字段属于内核追踪接口，不受应用 API 的稳定性保证。

`BINDER_WRITE_READ` 的 ioctl 时长不能直接当作一次 Binder RPC（远程过程调用）时长。一次 ioctl 可以写入多条命令，也可能进入读取路径等待工作；oneway transaction（单向事务）不会同步等待回复。端到端时延应结合客户端应用 slice、Binder transaction / received 事件和服务端 slice 分段计算。slice 是 trace 中带开始与结束时间的一段任务区间；缺少关联点时，只报告已经观察到的区间。

## 性能开销与完整性指标

WOOTdroid v1 的数据可以用于理解实验方法，不能当作产品预算。论文用独有事件率（Unique Event Rate，UER）衡量两个采集器各自多记录了多少事件：

| 项目 | 论文结果 | 解读限制 |
|---|---|---|
| Geekbench 6 | WDSys 单核分数下降 3.6%，多核下降 0.9%；ftrace 对照为 5.9% 和 2.9% | Geekbench 6 是 CPU 性能基准；实验使用两台已 root 的 Pixel 9、Android 16，并重复十次。这里只评估 WDSys，不能代表 WDBind 的开销 |
| 自动交互 | 数据集是当时 Google Play 各类别最常用的 100 个免费应用；每个应用注入 1000 个 Monkey 输入，间隔 500 ms | Monkey 是 Android 随机生成触摸、按键等输入的测试工具；覆盖受数据集、安装结果和随机路径影响，不能代表业务场景覆盖 |
| UER | WDSys 均值 37.75%，ftrace 均值 4.27%，相差 33.48 个百分点 | 某采集器的 UER = 只有该采集器记录到的事件数 ÷ 两份日志的事件并集；该指标不能表示绝对召回率（所有应采事件中成功采到的比例），也不能作为独立测得的丢失率 |

ftrace 的 UER 非零，说明有些事件只出现在 ftrace 日志里。因此，WDSys 也存在残余事件缺失，不能写成“完整捕获”。论文摘要中的“多追踪 33%”要按 UER 的定义理解，准确说法是两者平均 UER 相差 33.48 个百分点。

团队自己的评估需要覆盖四类数据：

- **带独立真值的完整性**：在受控进程中注入带序号的事件，把 enter / exit、transaction / received 和读取结果逐级核对。
- **每条失败路径**：分别统计 BPF map 冲突、tail call 失败、缓冲空间预留或输出失败、用户态解码失败和落盘失败。
- **业务扰动**：在目标设备组合上测 CPU、内存、存储 I/O、耗电、温度、启动、帧和应用无响应（ANR）；阈值由产品预算决定。
- **单独测量 WDBind**：Parcel 读取与解码的事件率、最大 payload、复杂接口比例和失败分布不能借用 WDSys 的 Geekbench 数字。

## 用于 ANR、隐私审计和冷启动回溯

eBPF 与 Binder 语义只在权限和数据治理允许的受控设备上补充证据。

### ANR 与卡死回放

主线程栈停在 Binder 等待，只说明采样时正在等待 IPC。要区分客户端调用前耗时、驱动路由、服务端排队、服务端执行和回复，需要多侧时间点。

在受控设备上，可以组合这些证据：

- App slice：调用点、线程、业务阶段和客户端总耗时。
- Binder tracepoint：transaction code、目标进程/线程、事务发送与接收阶段。
- WDBind 语义解析：在允许读取 payload 时提供接口 descriptor（接口标识）、方法候选和解码状态。
- 调度、I/O 与 futex 事件：用于判断客户端或服务端线程在相关区间是否获得 CPU、等待锁或执行 I/O。futex 是 Linux 在用户态快速竞争、必要时进入内核等待的同步机制，许多锁最终会用到它。

WDBind v1 不处理 reply，ioctl enter / exit 又可能混合 write 与 read，因此不能独立输出 request / reply latency。`/sys/kernel/debug/binder/` 也需要特权，格式和可用性不属于 Android 应用契约，不应成为发布包方案。

### 隐私审计

WOOTdroid 案例重建了十个安全相关的 framework 方法，包含短信、电话、包管理、权限、账户和通知场景。它证明原型能在所测 Android 16 设备上解析这些样例，不代表覆盖所有 Binder 接口。

审计目标通常只需要回答“哪个 UID 在何时调用了哪个敏感接口”，无需保存参数正文。解码策略默认应丢弃内容：

| 数据类别 | 默认处理 |
|---|---|
| token、密码、认证材料 | 不读取或立即丢弃，禁止写日志 |
| 短信、剪贴板、通知、联系人正文 | 不落盘，仅记录接口、结果类别和调用计数 |
| 电话、账户、设备标识 | 默认不记录值；业务确需关联时使用受控令牌化（用无业务含义的随机令牌代替原值）。输入范围很小、容易穷举的值不能靠普通 hash 冒充匿名化 |
| 精确位置、SSID/BSSID | SSID 是 Wi-Fi 网络名称，BSSID 通常标识具体接入点；这些值默认丢弃，安全用例只保留经审批的粗粒度分类 |
| 包名与权限名 | 按审计目的建立允许列表，其他值使用稳定分类或聚合 |
| transaction code、flags、大小、耗时 | 可作为元数据，但仍受保留期和访问控制约束 |

端侧脱敏要发生在持久化和上传之前。原始 Parcel 进入用户态 reader 后就已经扩大了敏感数据暴露面，所以“服务端再清洗”不满足最小化原则。

### 冷启动回溯

冷启动包含进程创建、dex/oat 代码加载、资源与文件 I/O、`ContentProvider` 初始化、Binder 查询、权限检查和应用初始化。dex 是 Android 字节码格式，oat 是 Android Runtime（ART）为安装或运行准备的编译产物。系统调用追踪能观察 `openat`（打开文件）、`mmap`（建立内存映射）、`read`、`futex`、`ioctl` 等边界，却看不到每段应用代码的业务含义。

较稳妥的组合是：

- 应用埋点提供启动 ID、阶段名和依赖关系。
- Perfetto 把调度、Binder、I/O 与应用 slice 放进同一时间轴。
- eBPF 仅在 OEM/实验设备上补充经过筛选的 syscall 或 Binder 元数据。

三类数据要记录时钟来源和同步误差。仅有 syscall 序列时，不应把相邻事件的时间差全部归给某个系统调用。

## 部署边界与合规风险

自定义 eBPF 不属于 Android 应用公开 API。能否使用取决于系统镜像、SELinux、BPF loader、内核配置和签名，单靠应用声明权限无法获得。SELinux 是 Android 用来限制进程和资源访问的强制访问控制机制，即使进程身份满足要求，策略仍可拒绝操作。

| 环境 | 能力边界 |
|---|---|
| 普通 user build 应用 | 不能加载任意追踪程序；Android 15 / API 35 起可通过 `ProfilingManager` 请求系统 trace、Java 堆转储、堆分析或栈采样。请求有频控，也不保证执行 |
| adb / userdebug | adb 是 Android 调试桥；userdebug 是额外开放调试能力的系统构建。两者适合验证 Perfetto、ftrace 和实验性 BPF，但不代表量产权限 |
| root 研究机 | 可复现实验，但 root 会改变设备的安全与完整性条件，不能作为普通用户部署方案 |
| OEM 系统集成 | 可把程序、loader 配置、SELinux、用户态采集进程和更新策略纳入系统镜像；需要平台测试与安全审查 |
| 企业受管设备 | Device Owner 是企业设备管理应用的最高管理角色，但该身份不授予 BPF 加载权；仍需 OEM 系统能力或专用调试环境 |

部署清单至少包括：

- 精确记录构建类型、Android 源码标签、内核版本、BPF helper / tracepoint、Binder ABI、SELinux 策略和采集器版本。
- 参数采集使用显式接口允许列表，未识别接口只保留最小元数据。
- 设备端设定 CPU、内存、缓冲、磁盘和网络预算，并提供远程停止与升级失败回退。
- 用户诊断具备目的说明、范围、到期时间、撤销入口、保留期和删除路径。
- 原始附件加密，服务端按最小权限访问并保留审计记录。
- 系统无线升级（OTA）后重新验证 loader、程序、签名表、MTE / TBI、vendor Binder 接口与数据解析。

## 扩展：WOOTdroid 与 Android eBPF 工具链对比

| 工具 / 方案 | 主要入口 | 适合场景 | 主要限制 |
|---|---|---|---|
| Perfetto / system trace | atrace（Android trace 类别开关）、ftrace 与平台数据源 | 启动、卡顿、调度、Binder、I/O 分析 | 可用数据源和权限会随版本与构建类型变化；它不提供任意 eBPF 程序的装载入口 |
| `ProfilingManager` | 系统管理的分析请求 | API 35 起，普通应用可按条件请求系统 trace、Java 堆转储、堆分析或栈采样 | 有频控和配置限制，请求不保证执行，也不开放全部 Perfetto 配置 |
| Simpleperf | Linux perf 事件与采样 | CPU 热点、原生代码（native）/ Java 调用栈采样 | 事件主要描述 CPU 执行，不能直接重建 Binder 参数 |
| bpftrace / BCC | kprobe、tracepoint、uprobe | root / userdebug 实验室快速验证 | kprobe 追踪内核函数，uprobe 追踪用户态函数；user build 通常缺少权限与完整工具链，探针稳定性取决于目标符号和版本 |
| AOSP 系统 eBPF | BPF loader、系统镜像对象、已 pin 的 map/program | 平台网络、CPU、GPU、内存等系统功能 | 由系统组件与 SELinux 管理，普通应用不能扩展 |
| Binder ftrace tracepoint | Binder 驱动 trace event（追踪事件） | 事务路由、接收与线程分析 | 主要是元数据，没有完整 Parcel 类型语义 |
| WOOTdroid WDSys | `raw_syscalls` + eBPF + perf buffer | 已 root / OEM 环境的系统调用审计研究 | 论文只在 Android 16 Pixel 原型评估 |
| WOOTdroid WDBind | 系统调用入口读取 Binder 写入缓冲区 + 签名表 | 受控安全审计与语义研究 | reply（回复）、复杂类型、vendor 覆盖和性能尚未系统评估 |

选择工具时先看权限和问题类型：普通应用从 `ProfilingManager`、Perfetto 与 Simpleperf 开始；只有受控系统环境需要补充自定义 eBPF 或 WDBind。

## 扩展：Binder 参数脱敏策略

参数保护不能依赖通用字符串替换。解析器应先用“接口 descriptor + 方法 + 参数序号”查询策略，再决定跳过读取、只记录类型与长度、执行令牌化，或在受控实验中短暂保留。未知接口默认丢弃参数。

策略本身也要版本化。AIDL 增删参数、transaction code 变化或 vendor 接口复用时，旧规则可能对错字段执行处理。签名表、脱敏规则、build fingerprint（系统构建标识）和采集器版本必须作为同一配置发布；任一项不匹配就退回元数据模式。

安全实验若必须保留短时间的原始参数，应与生产数据域隔离，并具备明确的设备清单、审批人、加密密钥、到期删除和访问日志。hash 是把原值映射为固定摘要；geohash 是把经纬度编码为网格字符串。手机号后四位、未加密钥的普通 hash 和粗粒度 geohash 仍可能成为可关联标识，不能自动视为匿名数据。

## 小结

eBPF 能在具备系统权限的设备上补充系统调用与 Binder 边界证据，但不会自动带来完整事件、稳定的方法语义或普通应用权限。Android 17 的设计应同时核对 AOSP BPF loader、6.18 Binder UAPI / tracepoint、目标系统镜像权限和实际丢失计数。WOOTdroid 数据只适合作为 Android 16 研究原型的参考。

普通应用的线上诊断以公开 API 和应用自有观测为主。只有 OEM、userdebug 或授权研究环境需要更深的内核证据时，才启用版本绑定的 BPF / Binder 方案，并默认停在元数据层。

## 源码与文档锚点

- [Android 17 `system/bpf`](https://android.googlesource.com/platform/system/bpf/+/refs/tags/android-17.0.0_r1/)：平台 BPF loader、program 与 map 的实现入口。
- [Android 17 `bpfloader.rs`](https://android.googlesource.com/platform/system/bpf/+/refs/tags/android-17.0.0_r1/loader/bpfloader.rs)：平台对象描述、`skip_on_user`、加载、附着和 pin 规则。
- [AOSP：Extend the kernel with eBPF](https://source.android.com/docs/core/architecture/kernel/bpf)：系统镜像 BPF 对象、启动加载、pin 与 Android BPF library 的官方说明。
- [Android 17 common kernel 6.18 r39 `binder.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/include/uapi/linux/android/binder.h)：当前核验的 `BINDER_WRITE_READ`、`BC_TRANSACTION`、`BC_TRANSACTION_SG` 与 UAPI 结构。
- [Android 17 common kernel 6.18 r39 `binder.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/drivers/android/binder.c)：当前核验的 `binder_ioctl_write_read()`、命令处理和用户内存复制路径。
- [Android 17 common kernel 6.18 r39 `binder_trace.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/drivers/android/binder_trace.h)：当前核验的 Binder transaction、received、command 与 return tracepoint。
- [Android 17 common kernel 6.18 `binder.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/uapi/linux/android/binder.h)：原文保留的 r6 历史锚点；复核时与 r39 内容一致。
- [Android 17 common kernel 6.18 `binder.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder.c)：原文保留的 r6 历史锚点；复核时与 r39 内容一致。
- [Android 17 common kernel 6.18 `binder_trace.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder_trace.h)：原文保留的 r6 历史锚点；复核时与 r39 内容一致。
- [WOOTdroid v1](https://arxiv.org/abs/2604.27830)：WDSys/WDBind 设计、Android 16 实验数据和作者列出的限制。
- [Android Developers：App-driven profiling](https://developer.android.com/topic/performance/tracing/profiling-manager/how-to-capture)：`ProfilingManager` profile 类型、频控和配置边界。
- [Android Developers：Log Info Disclosure](https://developer.android.com/privacy-and-security/risks/log-info-disclosure)：日志敏感数据泄露风险与端侧处理建议。
