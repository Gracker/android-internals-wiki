---


title: 设备 Benchmark（CPU、GPU、Web 与存储）
chapter: '19'
section: '19.17'
status: finalized
drafted_date: '2026-04-24'
drafted_by: codex
applicable_versions: Geekbench 6：官方当前要求 Android 10 (API 29) - Android 17 (API 37) / 4 GB RAM；Vellamo：历史工具，仅用于旧报告；其他 Benchmark
  按工具版本逐项核验
last_verified: '2026-06-07'
last_verified_against: Geekbench 6 download page / Benchmark Internals, Android Performance
  Class docs, 3DMark / PCMark / Speedometer / AnTuTu official materials
confidence: medium
tags:
- apm
- benchmark
- geekbench
- 3dmark
- device-tiering
- antutu
- pcmark
related_chapters:
- '19.0'
consolidated_from:
- "src/part3-tools/ch19-apm/22-storage-benchmark.md"
sources:
- type: official
  path: https://www.geekbench.com/
- type: official
  path: https://www.geekbench.com/download/
- type: official
  path: https://www.geekbench.com/doc/geekbench6-benchmark-internals.pdf
- type: official
  path: https://benchmarks.ul.com/3dmark-android
- type: official
  path: https://benchmarks.ul.com/pcmark-android
- type: official
  path: https://browserbench.org/announcements/speedometer3/
- type: official
  path: https://www.antutu.com/en/doc/129591.htm
pipeline_stage: ready-to-publish
task6_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: 2026-06-07
last_task6_audit: '2026-06-19'
task6_result: pass-light-edit
task9_state: 'reviewed'
task2b_state: 'fixed'
task9_result: 'auto-fixed'
task9_reviewed_date: '2026-05-13'
task9_reviewed_by: 'openclaw-task9'
last_task9_at: '2026-06-07T10:20:00+08:00'
task2b_result: fixed
last_task2b_at: '2026-04-25T02:49:32+08:00'
repaired_date: '2026-04-25'
repaired_by: openclaw-task2b
last_task9_review_log: 'logs/deep-review/2026-06-07-10-audit.md'
auto_promoted: true
task9_review_notes: '2026-06-07 idle audit: auto-fixed Geekbench 6 Android requirement drift（官方当前要求 Android 10+ / 4 GB RAM），回到 Task6 复审。'
last_task9_audit: '2026-06-07'
last_task9_autofix_at: '2026-06-07'
last_deepseek_polish_at: 2026-05-25
deepseek_polish_state: done
last_task6_at: 2026-06-07T13:06:00+08:00
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-18
---


# 设备 Benchmark（CPU、GPU、Web 与存储）

## 先把设备基线和 App 数据分开

Geekbench、3DMark、PCMark、安兔兔和 Speedometer 给设备施加固定负载，用于描述 CPU、GPU、存储或浏览器执行路径的能力。线上 APM、Macrobenchmark 和业务场景 trace 描述的是 App 在指定版本、账号、网络和数据规模下的体验。两类数据可以互相解释，不能互相替代。

下面三种说法都越过了证据边界：

- “Geekbench 单核高，所以 App 冷启动一定快。”
- “3DMark 稳定性高，所以列表滚动一定稳定。”
- “安兔兔总分高，所以 SQLite 事务一定快。”

更稳妥的表达是：某项设备分数提示了可能的资源上限；要判断它是否限制当前 App，还要用启动、帧时间、I/O、内存和功耗数据验证。

## 版本号决定分数能不能比较

测试报告至少要记录三个版本：Benchmark 应用版本、应用内测试项目版本、被测系统与驱动版本。只写“3DMark 最新版”或“Geekbench 6”不足以复现结果。

截至 2026-07-25，各工具的处理口径如下：

| 工具 | 当前状态 | 可比性规则 | Android 17 项目的建议 |
|---|---|---|---|
| Geekbench 7 | 2026-07-23 发布；官方下载页要求 Android 12+、4 GB RAM | CPU、GPU 工作负载和多核规则相对 Geekbench 6 均有改动，不能把两个大版本的分数放进同一时间序列 | 新建 Geekbench 7 基线；已有 Geekbench 6 数据冻结在独立字段 |
| Geekbench 6 | 保留其公开 Benchmark Internals 作为可审计的工作负载样本 | 同一大版本也要保存精确应用版本；没有官方兼容声明时，按精确版本比较 | 用于维护既有 GB6 设备库，不再向 GB7 字段写入 |
| 3DMark Android | 当前应用版本 2.6.5056，发布于 2026-04-07 | 应用版本和 Wild Life、Steel Nomad Light 等测试版本是两套编号；比较时以同一测试及其版本为准 | 从设置页同时抄录应用版本、测试名、测试版本和模式 |
| PCMark Android | 当前应用版本 3.1.4113，发布于 2026-06-15 | 3.1 与 3.0 的总分大致可比，但官方仍建议使用同一 workload 版本；Work 3.0、Storage 2.0 不可与旧测试混比 | 新报告固定 Work 3.0 或 Storage 2.0，并保存 System WebView 版本 |
| 安兔兔 | 官方下载区当前为 V11.1.4，发布于 2026-06-30 | V11 和 V10 因测试项变化不可比；跨 OS 的分数也不用于工程回归 | 总分仅作沟通标签，归因时查看 CPU、GPU、MEM、UX 子项及 App 实测 |
| Speedometer | 当前稳定口径为 3.1 | 3.1 修正了测量框架；不要把 3.0 和 3.1 混在一组 | 固定 Speedometer、浏览器或 WebView、系统和电源状态 |
| Vellamo | Qualcomm 的可核验官方资料停留在 2012 年的套件介绍，没有当前版本依据 | 历史报告只能在原工具、原版本和相近环境内阅读 | 冻结旧数据，不再补录 Android 17 新设备 |

Geekbench 7 于 2026-07-23 发布。当前设备库若已积累大量 Geekbench 6 数据，不应为追新而覆盖旧列；增加 `geekbench_major=7` 和新分数字段，等样本覆盖率足够后再迁移分层规则。

## 工具分工：先选问题，再选分数

| 要回答的问题 | 首选信号 | 它没有回答什么 |
|---|---|---|
| 单线程通用 CPU 容量怎样 | Geekbench CPU single-core | App 主线程具体花在 Java、Binder、I/O 还是锁等待 |
| 受控工作负载的多线程吞吐怎样 | Geekbench CPU multi-core | App 是否具备可并行任务、线程池是否合理 |
| GPU Compute 容量怎样 | Geekbench GPU（Vulkan / OpenCL） | 图形渲染帧率、合成、触控延迟 |
| 重图形短时性能怎样 | 3DMark 指定图形测试 | 普通 View 或 Compose 页面是否卡顿 |
| 重图形持续性能怎样 | 3DMark Stress Test 的循环曲线 | App 自身的帧生成、资产加载和网络抖动 |
| WebView、视频、文档、图片、数据处理的组合表现怎样 | PCMark Work 3.0 子项 | 单个业务页面的启动或交互时延 |
| 内部存储、外部存储和 SQLite 组合表现怎样 | PCMark Storage 2.0 子项 | 某个文件系统调用、Room 查询或数据库事务的根因 |
| 浏览器前端交互执行路径怎样 | Speedometer 3.1 | 网络速度、服务端耗时、App 内 WebView 的完整链路 |
| 面向大众的设备综合档位怎样 | 安兔兔 V11 总分与子项 | 单项资源瓶颈和 App 性能因果 |

分数命名也要带上工具语义。`gpu_score` 这样的字段会把 Geekbench Compute 和 3DMark Graphics 混在一起，建议写成 `gb7_vulkan_compute`、`3dmark_wild_life_v1_score` 和 `3dmark_wild_life_stability`。

## Geekbench：把分数理解为代理变量

### Geekbench 6 的单核分数由什么组成

Geekbench 6 的公开内部文档说明，CPU 总分由 integer 和 floating-point 两部分加权，权重分别为 65% 和 35%；各子测试先按参考系统归一化，再组合成分数。分数翻倍表示这套 Benchmark 工作负载中的性能翻倍，不表示任意 App 代码都快一倍。

下表把公开工作负载映射到 Android 工程问题。表中的“可提出假设”只用于确定下一步测量方向：

| Geekbench 6 工作负载 | 主要资源或算法 | 可提出的 Android 假设 | App 内验证方式 |
|---|---|---|---|
| File Compression（LZ4、ZSTD、AES、SHA1） | 整数、内存访问、压缩与加密指令 | 安装包解压、离线资源解压或同步加密可能受 CPU 限制 | 对 App 使用的压缩库、数据规模和线程模式做 Microbenchmark |
| Navigation（Dijkstra、OpenStreetMap 数据） | 图算法、分支和内存访问 | 离线路径规划或大型关系图计算可能受单线程容量影响 | 对业务图规模采样，并在目标机型上测端到端耗时 |
| HTML5 Browser | 受控的 HTML/JavaScript 负载 | 轻线程网页计算可能随单核档位变化 | 用目标 WebView 版本跑页面 trace；不能把该子项当作 Chrome 或 WebView 分数 |
| PDF Renderer（PDFium） | 文档解析与栅格化 | PDF 首屏或翻页可能受 CPU 和内存共同影响 | 固定 PDF 文件，在 App 使用的 PDF 组件中测首屏和逐页时间 |
| Photo Library / Photo Editor | 图片编解码、SQLite、图像处理及部分 ML | 相册扫描、缩略图生成或编辑可能受 CPU、内存和指令集影响 | 复用业务图片格式、分辨率和模型做 Macrobenchmark 或业务基准 |
| Clang、Text Processing、Asset Compression | 编译、正则、SQLite、纹理及几何资产压缩 | 文本处理、开发工具或资产管线可能有相近计算特征 | 对业务库直接基准；不要把 Text Processing 等同于 JSON 解析 |

“单核分数影响 JSON 解析”这句话过于确定。Geekbench 6 没有以你的 JSON 库、序列化模型和数据规模运行；它只能给出通用单线程容量线索。JSON、protobuf、XML inflate、Compose measure/layout 和 `RecyclerView` bind 仍要分别测量。I/O 等待、锁竞争或 Binder 往返占比高时，单核分数的解释力会更弱。

ARM 设备还可能按运行时能力使用 AES、SHA、FP16、Dot Product、I8MM 等指令。两个设备的分差有时来自特定指令路径，而业务实现未必走同一条路径。跨 SoC 解释子项时，要核对 App 使用的库、ABI、编译选项和硬件加速路径。

### 多核分数不是“所有核心相加”

Geekbench 6 相对 Geekbench 5 改用 shared-task 模型，让多个线程协作处理共同任务，纳入线程协调和共享数据带来的成本。2026-07-23 发布的 Geekbench 7 又调整了规则：只有在对应现实任务适合并行时才进入多线程套件，例如其 HTML5 Browser 不进入多线程测试。

因此，GB6 和 GB7 的多核分数都不能直接回答“App 开八个线程会快多少”。要先检查任务依赖、可并行比例、调度优先级、线程池拥塞和内存带宽。主线程上的串行关键路径不会因多核总分高而自动缩短。

### Compute 分数不等于图形帧率

Geekbench 6 的 GPU Benchmark 通过 Vulkan 或 OpenCL 运行计算工作负载，并将子项组合成 Compute 分数。它适合为图像处理、部分 ML、视频处理或通用 GPU 计算提出容量假设。

游戏和 Android UI 还涉及顶点与像素着色、光栅化、纹理、内存带宽、SurfaceFlinger 合成、显示刷新和帧调度。Compute 分数没有覆盖完整显示管线。分析渲染问题时应改看 3DMark Graphics、Perfetto、FrameTimeline 和 App 自身帧数据。

## 3DMark：峰值、持续性能和温控要一起看

### 选择设备能稳定完成的测试

3DMark Android 会根据设备能力推荐测试。Android 17 项目常见选择如下：

| 测试 | 适用对象 | 读取结果时的重点 |
|---|---|---|
| Wild Life | 支持 Android 10、Vulkan 1.1 且至少 3 GB RAM 的主流设备 | 短时 Graphics score、平均帧率以及同型号分布 |
| Wild Life Extreme | 能稳定完成更重 Vulkan 负载的高性能设备 | 重负载下的性能上限；低帧率本身不代表测试异常 |
| Steel Nomad Light | 新一代高性能移动设备的非光追负载 | 更重的现代图形路径；官方版本说明曾标注 8 GB RAM 要求，纳入设备库前应按当前应用提示复核 |
| Solar Bay | 支持 Vulkan ray query 的设备 | 移动光追能力，不覆盖普通设备，也不代表传统栅格化帧率 |
| Sling Shot / Sling Shot Extreme | 旧设备与历史 OpenGL ES 数据 | 只维护历史序列，不与 Wild Life 或新测试换算 |

标准测试、Extreme、Stress 和 Unlimited/离屏模式是不同负载。即使名称相近，也要分别存储，不能只保留一个 `3dmark_score`。

### Stability 需要和帧率共同解释

Wild Life 的普通 Benchmark 用于观察短时间高性能；Stress Test 连续运行二十轮，用于观察性能和温度随时间的变化。UL 面向 PC Stress Test 结果页公开的 Frame Rate Stability 定义是最低循环平均帧率除以最高循环平均帧率，再乘以 100%；Android Wild Life 官方说明更强调二十轮曲线。移动端报告应保存应用显示的 stability 和整条曲线，不要把 PC 页面给出的 97% pass 条件照搬成 App 的产品门槛。

这个比例有两个容易忽略的边界：

- 98% stability 可能来自“每一轮都只有较低帧率”，说明稳定但不够快。
- 很高的首轮帧率配合 65% stability 可能说明峰值强、持续性能弱。

报告至少同时列出 best loop、worst loop、stability、每轮帧率曲线和热状态。若要解释游戏体验，还要在游戏自身固定场景中采集帧时间、CPU/GPU 频率、功耗和温控事件。

### 热数据不要只抄一个温度

Android 17 平台的 `ThermalManagerService` 聚合 Thermal HAL 上报并维护当前 thermal status，`PowerManager.getCurrentThermalStatus()` 向应用提供从 `NONE` 到 `SHUTDOWN` 的状态。`THERMAL_STATUS_NONE` 只表示当前没有进入节流状态，不表示设备已经回到相同初始温度。

内核侧以 `android17-6.18-2026-06_r6` 为源码锚点。Linux thermal sysfs 文档说明，`thermal_zone` 暴露当前温度与 trip point，cooling device 参与温控。量产设备对传感器名称、可见性和温度标定的实现不同，不能把两个厂商的 `thermal_zone0` 数值直接横向比较。

温控测试更适合记录同一设备的相对变化：起始表面温度、每轮温度或 thermal status、首轮到稳定轮的性能衰减，以及冷却回基线所需时间。

## PCMark：工作负载比总分更有解释力

PCMark Android 3.1.4113 是当前应用版本，Work 3.0 包含 Web Browsing、Video Editing、Writing、Photo Editing 和 Data Manipulation；Storage 2.0 覆盖内部存储、外部存储和 SQLite 数据库操作。

这些子项比总分更接近 Android 业务，但仍需注意实现差异：

- Web Browsing 3.0 使用系统 Android WebView。系统更新后，即使 PCMark 应用版本不变，执行引擎也可能变化，因此要记录 `com.google.android.webview` 或设备实际 WebView provider 的版本。
- Video Editing 3.0 使用 `MediaCodec`、ExoPlayer 和 OpenGL ES 2.0。它反映一套受控媒体工作流，不代表 App 的编解码参数、滤镜和文件格式。
- Writing 3.0 使用 Android `EditText` 与 `PdfDocument`。它适合作为文档工作负载背景，不能替代业务编辑器测量。
- Storage 2.0 的 Database 子项使用 SQLite，但 App 的 schema、索引、事务、WAL、文件系统和缓存状态都会改变结果。

PCMark 3.1 发布说明指出，3.1 与 3.0 总体分数大致可比，同时明确建议在相同 workload 版本间比较。工程回归应遵守更严格的后一句：版本或 workload 变化就切分时间序列。Work 3.0、Storage 2.0 也不能与 Work 2.0、Storage 1.0 混比。

## 存储专项 Benchmark：协议比工具名重要

存储工具只能描述“这台设备在这套路径、参数和缓存状态下”的 I/O 背景，不能指出 App 哪个文件、线程或 SQL 慢，也不能证明一次 `write()` 已经持久化到闪存。从分数到业务结论还要补 App 路径、调用栈、事务、查询计划与用户场景。

### AndroBench、A1 SD Bench 与现代替代

AndroBench 可公开核对的协议源于 2011 年：顺序读文件 32 MB、写文件 2 MB，随机测试使用 4 KiB 操作，每项三轮平均。文件规模很容易被现代设备的页缓存、写缓冲和短时突发能力主导。A1 SD Bench 公开描述了 Quick、Longer、Accurate、Random I/O、RAM、SD/USB 与自定义路径，但没有足够信息说明 cache、同步、块大小、预分配和汇总算法。

两者保留用于解释历史报告，不作为 Android 17 新设备库的默认基线。历史连续性要求补测时，保存 APK 版本、hash、模式和全部参数。

现代设备实验室优先选择协议可审计的工具或业务自建基准：

- CPDT 可以配置文件大小、4 KiB random、write buffering 与 in-memory caching，并导出时序；仍需固定源码版本并先做 API 37 兼容验证。
- PCMark Storage 2.0 提供内部、外部与 SQLite 的组合 workload，但输出仍是工作负载分数，不是裸 UFS 吞吐。
- 最有预测力的方案是在目标 App 实际目录中复用相同文件格式、SQLite schema、事务、同步语义和线程模型。

### 四类指标与必要参数

| 指标 | 必填参数 | 可提出的假设 | 不能直接解释 |
|---|---|---|---|
| 顺序读吞吐 | 文件、buffer、cache、并发 | 大资源连续读取上限 | 大量小文件冷启动 |
| 顺序写吞吐 | 文件、buffer、direct/buffered、sync 语义 | 下载、导出、批量日志 | 单事务 commit 延迟 |
| 随机读 IOPS/latency | block、范围、QD、线程、分布 | 小块读取与索引背景 | 目录扫描和反序列化 CPU |
| 随机写 IOPS/latency | 上述参数 + 同步频率和预分配 | 数据库日志与元数据更新风险 | 业务事务设计是否合理 |

IOPS 不带 block size 和 queue depth 没有工程意义。吞吐越高越好，但坏尾位于低侧，多轮报告应看 median 与 P10；latency 越低越好，单操作可看 p50/p95/p99。只有五轮时不渲染稳定分位数，使用 median、min/max 与 MAD。

### 路径、缓存与持久化语义

| 路径 | Android 17 访问模型 | 结果边界 |
|---|---|---|
| `filesDir` / `cacheDir` / database | App 私有内部存储 | 接近业务私有数据，但仍包含加密、文件系统和内核缓存 |
| `getExternalFilesDir()` | App-specific external | 可能位于共享或可移除卷，不能假设永远可用 |
| MediaStore | 集合、权限与 provider | 包含 Binder、元数据和介质路径 |
| SAF | 用户授权的 URI / tree | 包含 DocumentsProvider 与底层介质 |
| SD / USB | 卷、文件系统、读卡器和授权 | 不只代表卡片本身 |
| RAM | 内存复制或内存文件 | 不进入闪存排名 |

普通 buffered write 返回可能只表示数据进入页缓存；没有 `fsync`、`fdatasync` 或等价协议时，不能宣称安全落盘。冷读、热读和 reboot 后首次读取是三组不同实验；量产 user build 不应为跑分写 `drop_caches`。剩余空间、文件系统 GC、discard、加密、温度、后台媒体扫描和系统更新都要记录。

SQLite 分数也使用工具自己的表、索引、journal 和事务。业务验证要检查批量写是否在同一事务、WAL 与 synchronous、checkpoint、N+1 查询、索引和 `EXPLAIN QUERY PLAN`，并用真实数据记录 p50/p95 latency 与 rows scanned。

存储 Benchmark 只负责设备背景；Perfetto 的 database/文件系统事件、Matrix IO Canary 或 StrictMode 提供时间与调用位置，A/B 业务测试证明修改有效。比如“随机写弱设备 + 启动主线程重复小写 + trace 对齐 + 批量后台写后 P95 回落”才能支持因果链，单张跑分截图不能。

## 安兔兔：总分只保留为沟通标签

安兔兔 V11 包含 CPU、GPU、MEM 和 UX 等组合测试。官方 V11 公测说明明确写出，V11 因测试项调整不能与 V10 比较，并给出 27℃±1℃、电量 80% 以上、亮度 300 nit 的示例测试条件。这里的条件说明跑分对环境敏感，不表示所有团队都必须采用相同电量。

若产品、测试和市场已经习惯用安兔兔总分描述设备档位，可以保留总分，但设备字典还要保存大版本和子项。工程排查从相关子项开始：

- 启动慢优先检查 CPU 单线程、存储和 App 启动 trace。
- 游戏掉帧优先检查 GPU 子项、持续性能和游戏帧时间。
- 数据库慢优先检查存储与业务 SQL，不从 UX 总分推断。
- 后台恢复或 OOM 优先检查物理内存、进程状态和 App 内存峰值。

两个设备总分相近时，一个可能是 CPU 强、存储弱，另一个是 CPU 弱、GPU 强。总分把不同资源结构压成一个数，会隐藏 App 所依赖的那一维。

## Speedometer：浏览器分数不能代替 WebView 实测

Speedometer 3.1 通过模拟用户操作，测量 TodoMVC、富文本编辑器、图表和新闻站点等 Web 应用负载的响应性。它不测网络吞吐，也不覆盖 Web Worker 中并发异步工作的完整成本；官方还明确说明，不能用它比较 JavaScript 框架优劣。

Android 上用 Chrome 跑出的分数描述“这台设备 + 这个 Chrome 版本 + 当前配置”的浏览器路径。App 内 WebView 的 provider、版本、启动方式、缓存、JS bridge、页面资源和进程模型都可能不同。需要判断 App 的 Web 页面时，建议补一套受控 WebView 容器，固定 provider 与页面资源，并采集 WebView/Chromium trace。

Speedometer 官方建议使用最新稳定浏览器、干净 profile、关闭其他标签页和后台程序、保持页面前台，并在两次测试间按需冷却。移动设备测试还要把充电状态记入报告；若团队选择不充电以避开发热，也可以，但同一比较组必须保持一致。

## Vellamo：冻结历史，不推断“当前版本”

Qualcomm 2012 年官方资料把 Vellamo 描述为包含 HTML5 与 Metal 等章节的移动 Benchmark 套件。该资料可用于解释旧报告中的字段，不能证明它在 Android 17 上仍有维护、兼容性或稳定口径。

处理旧数据时保留 APK hash、工具版本、Android 版本、设备和原始分数。新设备不再补跑，也不尝试把 Vellamo 分数换算成 Speedometer、Geekbench 或 PCMark 分数。

## Performance Class 只能做能力下限标签

Android 的 Media Performance Class 从 Android 12 体系引入。Android 17 / API 37 的 AOSP `Build.VERSION.MEDIA_PERFORMANCE_CLASS` 仍从设备属性读取声明值，未声明时返回 0。Jetpack Core Performance 可以从 build 信息或 Google Play services 查询兼容等级。

截至 2026-07-25，Android 官方公开定义的等级是 30、31、33、34、35，其中没有 MPC 32；0 表示未定义。Performance Class 可向前兼容：设备升级到 Android 17 后，仍可能报告它原先满足的 33、34 或 35。不要自行创造“MPC 37”，也不要把 Android 版本号当作设备必然报告的等级。

| 信号 | 可以表达什么 | 不能表达什么 |
|---|---|---|
| Media Performance Class | CDD/CTS 约束下的媒体、相机、内存、I/O、显示等能力下限 | CPU 综合排名、App 启动 P95、列表慢帧率 |
| Geekbench / 3DMark / PCMark | 固定测试里的 CPU、GPU、工作流和存储代理信号 | 业务代码路径的直接结果 |
| 线上 APM 和 App 基准 | 指定 App 版本与真实用户/受控场景的体验 | 脱离样本分布后的通用硬件排名 |

因此，Performance Class 适合做设备字典中的官方标签，不适合作为唯一档位。服务端要把它和 CPU、GPU、RAM、存储、热稳定性及线上表现组合使用。

## 可复现测试规范

下面是一套适合团队设备实验室的起始规范。次数和温度窗口不是 Android 或 Benchmark 厂商规定，可在试运行后按方差调整。

### 记录设备身份

- 设备品牌、市场型号、硬件 SKU、SoC、RAM、存储容量；同名机型的不同 SoC 或内存版本分开。
- Android 版本、build fingerprint、安全补丁、基带、GPU driver、实际 kernel release。知识库源码锚点是 Android 17 / API 37 / `android-17.0.0_r1` 与 `android17-6.18-2026-06_r6`，测试报告仍应记录量产机的实际构建。
- Benchmark 应用版本、测试名、测试版本、API 或运行模式。Web 测试另记浏览器或 WebView provider 版本。

### 固定运行条件

- 固定屏幕分辨率、刷新率和亮度；关闭自动亮度。
- 固定充电或放电状态、电量区间、性能/游戏模式、省电模式和散热配件。
- 固定室温与设备摆放；每组开始前等待表面温度回到约定窗口，并记录 thermal status。
- 完成系统更新和应用优化后再测试；关闭无关应用、下载、录屏、日志洪泛和同步任务。
- 需要联网的测试固定接入点与网络条件；不需要联网的负载避免让后台网络成为噪声。

这些 shell 命令用于保存 Android 17 设备的基本身份与热状态快照：

```bash
adb shell getprop ro.build.fingerprint
adb shell getprop ro.build.version.release
adb shell getprop ro.build.version.sdk
adb shell getprop ro.build.version.security_patch
adb shell uname -r
adb shell dumpsys battery
adb shell dumpsys thermalservice
adb shell dumpsys webviewupdate
```

`dumpsys thermalservice` 能显示框架服务掌握的 thermal status 与温度信息，但不同厂商的字段和传感器可见性不同。报告应保存原始输出，不要只提取一个跨设备比较的“CPU 温度”。

### 重复、取值与作废规则

- 短测试建议预热一轮后至少保留 5 个有效轮次；报告中给出中位数、最小值、最大值和 MAD（median absolute deviation）。
- 长时间 Stress Test 建议在完整冷却后做至少 3 个独立 session；每个 session 保留全部循环曲线。
- 轮次更多时可以报告 P10/P90；5 个样本不适合渲染成稳定的分位数分布。
- 来电、通知弹窗、失去前台、后台安装、系统更新、意外网络切换或测试崩溃都应作废并写明原因。
- 热状态或起始温度不在约定窗口时不并入同一比较组。`THERMAL_STATUS_NONE` 不能单独证明温度已经复位。

平均值容易被一次异常高分或低分拉动，中位数更适合小样本跑分。任何“回归 3%”的结论都要先和同设备、同版本的自然波动比较。

## 用分项能力建立机型分层

设备分层应保存一个能力向量，而非只保存综合档位：

| 维度 | 建议来源 | 线上问题 |
|---|---|---|
| CPU single | GB6 或 GB7 的独立版本序列 | 主线程 CPU 计算、启动中的串行计算 |
| CPU multi | 同一 Geekbench 大版本 | 可并行图片、压缩、媒体或后台批处理 |
| GPU graphics | 3DMark 指定测试与模式 | 游戏、地图、相机特效和重图形页面 |
| GPU compute | Geekbench Vulkan/OpenCL 或业务计算基准 | 图像、部分 ML 与通用计算 |
| Storage | PCMark Storage 2.0 子项与业务 I/O 基准 | 冷启动文件、SQLite、缓存和资源加载 |
| RAM | 物理内存、低内存设备标志和线上采集 | OOM、后台恢复、缓存上限 |
| Thermal | 3DMark Stress 曲线、thermal status 和业务长测 | 游戏、视频、直播的持续性能 |
| MPC | Jetpack Core Performance | 官方能力下限与功能开关参考 |

### 四档不是四个固定分数线

入门、中端、高端、旗舰的边界应从团队已冻结版本的设备样本分布中计算。例如，可在同一国家/渠道覆盖集内按关键维度的 P20、P50、P80 切四档，再由线上数据校正。换 Geekbench 大版本、3DMark 测试或设备覆盖集后，要重新计算边界。

| 档位 | 设备能力特征 | 性能预算与产品策略 |
|---|---|---|
| 入门 | 一个或多个关键维度位于低分位，常伴随小 RAM 或弱存储 | 核心路径采用最严格预算；默认降低预取、并发、图片规格和高成本效果 |
| 中端 | 关键维度覆盖主流下半区 | 维持完整核心功能；对非必要动画、媒体和缓存设置上限 |
| 高端 | 关键维度位于主流上半区且持续性能稳定 | 可开放更高质量资源，但仍受线上耗时和内存预算约束 |
| 旗舰 | 多个相关维度处于高分位 | 可试验高规格效果；不能因档位高而跳过启动、慢帧、功耗和温控验收 |

分档应围绕业务选择维度。资讯 App 可能重视 CPU single、Storage 和 RAM；游戏更重视 GPU graphics 与 Thermal；离线视频编辑还要加入媒体编解码业务基准。不存在一套对所有 App 都合理的总分权重。

## 把设备字典连接到线上数据

不建议让每个客户端在线跑 Benchmark，也不建议在每条 APM 事件里上传跑分。团队可以维护版本化设备字典，客户端只上报已有的设备与系统标识，分析平台再关联能力字段。

下面是一个仅用于说明字段关系的虚构事件，不代表 Pixel 8 或 Tensor G3 的实测结论：

```text
event: app_start
app_version: 12.4.0
device_model: Pixel 8
soc: Tensor G3
ram_gb: 8
android_sdk: 37

device_dictionary_join:
capability_schema: 2026-07-gb7
cpu_single_bucket: high
gpu_graphics_bucket: high
storage_bucket: medium
thermal_bucket: medium
mpc: 35
```

`capability_schema` 让历史事件始终能还原当时的分层规则。设备字典还应区分同型号的 SoC、RAM、存储和区域版本；无法精确匹配时写入 `unknown`，不要凭市场名称猜测。

### 关联示例不能当作因果结论

假设某次分析得到以下虚构结果：

| CPU single 档位 | 冷启动 P95 | 样本量 |
|---|---:|---:|
| low | 1,480 ms | 820,000 |
| medium | 1,090 ms | 1,760,000 |
| high | 810 ms | 940,000 |

这个表只说明分档和启动 P95 同时变化。低档设备还可能拥有更慢存储、更小 RAM、旧系统或不同地区网络。分析时应固定 App 版本与启动口径，并按存储、RAM、Android 版本、网络和地区拆分；再用分桶趋势或 Spearman 相关判断是否稳定。需要证明某段 CPU 代码受限，还要回到 Macrobenchmark、trace 或 Microbenchmark。

### 灰度、预算和告警

- 灰度发布按能力档位分层抽样。新效果可以从小比例高档设备开始，但进入全量前必须覆盖入门档；面向低端优化的版本应优先保证低档样本量。
- 性能预算从真实用户分布和业务目标制定。例如按档位分别约束冷启动 P95、慢帧率、OOM 率和峰值内存，不从 Geekbench 分数换算毫秒。
- 告警阈值使用同 App 版本、同能力档位的历史波动。Benchmark 版本变化只触发设备字典重算，不直接触发线上性能告警。
- 功能降级由明确能力维度驱动。例如 GPU/thermal 弱时降低实时特效质量，RAM 小时降低缓存；不要用安兔兔总分作为单一开关。

## 综合分误导的一个例子

假设设备 A 的 CPU single 很强、存储随机读写较弱，设备 B 的 CPU single 较弱、存储较强，两者恰好拥有相同综合分。图片解码计算重的 App 可能在 A 上更快；冷启动读取许多小文件的 App 可能在 B 上更快。相同总分无法给出统一排序。

工程报告应从业务关键路径反推资源维度，再选择子项。综合分可以留在摘要中，结论和行动项必须引用相关分项及 App 证据。

## 历史数据与工具迁移

工具停更、测试项目升级或分数口径改变时，按下面的规则处理：

- 冻结旧序列，保留原始分数、单位、应用版本、测试版本、日期和运行条件。
- 新工具或大版本使用新字段，不覆盖历史分数。
- 厂商没有发布换算公式时，不做经验换算，也不把百分位强行对齐成“等价分数”。
- 分层迁移期并行维护两套设备覆盖率，通过线上指标验证新分档后再切换配置。
- 旧工具只用于解释原报告，不为 Android 17 新设备补跑 Vellamo 等历史项目。

Geekbench 6 到 7、安兔兔 V10 到 V11、PCMark Work 2.0 到 3.0 都应按大版本迁移处理。3DMark 还要在应用版本之外维护测试版本，避免应用自动更新后误判数据已经跨代。

## 测试报告模板

下面的模板用于保存可复现信息和结论边界：

```yaml
report_id: android-benchmark-2026-07-25-001
device:
  brand: ""
  model: ""
  sku: ""
  soc: ""
  ram_gb: 0
  storage_gb: 0
software:
  android_release: "17"
  api_level: 37
  build_fingerprint: ""
  security_patch: ""
  kernel_release: ""
  gpu_driver: ""
benchmark:
  app_name: ""
  app_version: ""
  test_name: ""
  test_version: ""
  api_or_mode: ""
conditions:
  room_temperature_c: null
  start_surface_temperature_c: null
  battery_percent: null
  charging: false
  brightness_nit: null
  refresh_rate_hz: null
  performance_mode: ""
  thermal_status_start: ""
results:
  warmup_runs: 1
  valid_runs: []
  median: null
  min: null
  max: null
  mad: null
  invalid_runs: []
app_validation:
  metric: ""
  app_version: ""
  scenario: ""
  result: ""
conclusion:
  supported_claim: ""
  unsupported_inference: ""
```

模板把设备基线与 App 验证分开保存。`supported_claim` 只写当前数据能支持的判断，`unsupported_inference` 主动记录容易被误读的推论。

## 源码与官方资料

- [Geekbench 7 发布说明](https://www.geekbench.com/blog/2026/07/geekbench-7/)
- [Geekbench 当前下载要求](https://www.geekbench.com/download/)
- [Geekbench 6 Benchmark Internals](https://www.geekbench.com/doc/geekbench6-benchmark-internals.pdf)
- [3DMark for Android](https://benchmarks.ul.com/3dmark-android)
- [3DMark Android 应用版本说明](https://support.benchmarks.ul.com/support/solutions/articles/44002142020-3dmark-android-application-release-notes)
- [3DMark Wild Life 概览](https://support.benchmarks.ul.com/support/solutions/articles/44002135593)
- [3DMark Stress Test 结果定义](https://support.benchmarks.ul.com/support/solutions/articles/44002134931-stress-test-result-screen)
- [PCMark for Android](https://benchmarks.ul.com/pcmark-android)
- [PCMark Android 应用版本说明](https://support.benchmarks.ul.com/support/solutions/articles/44002199189-pcmark-for-android-application-release-notes)
- [Speedometer 3.1](https://www.browserbench.org/Speedometer3.1/)
- [Speedometer 3.1 方法说明](https://www.browserbench.org/Speedometer3.1/about.html)
- [Speedometer 3.1 测试说明](https://www.browserbench.org/Speedometer3.1/instructions.html)
- [安兔兔 V11 公测说明](https://www.antutu.com/doc/135125.htm)
- [Qualcomm 2012 Vellamo 资料](https://www.qualcomm.com/news/onq/2012/09/vellamo-mobile-benchmark-suite)
- [Android Performance Class](https://developer.android.com/topic/performance/performance-class)
- [Android `PowerManager` Thermal API](https://developer.android.com/reference/android/os/PowerManager#getCurrentThermalStatus())
- [AOSP `Build.VERSION.MEDIA_PERFORMANCE_CLASS`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/Build.java)
- [AOSP `ThermalManagerService`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/power/thermal/ThermalManagerService.java)
- [Linux thermal sysfs（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/driver-api/thermal/sysfs-api.rst)
- [AndroBench 论文 DOI](https://doi.org/10.1007/978-3-642-27552-4_89)
- [CPDT 固定源码](https://github.com/maxim-saplin/CrossPlatformDiskTest/tree/a507cda4f487afc9334e0f02673af34a366961d9)
- [Android SQLite 性能指南](https://developer.android.com/topic/performance/sqlite-performance-best-practices)
- [Linux F2FS 文档（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/filesystems/f2fs.rst)
