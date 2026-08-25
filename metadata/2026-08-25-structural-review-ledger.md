# 正文结构审查台账（2026-08-25）

## 审查口径

当前正文共有 274 篇，分布在 26 个大章。旧的 `2026-08-24-article-review-ledger.json` 只证明结构扫描和语义相似度筛查完成，不能替代人工逐篇审查。本台账只把已经核对过标题契约、完整正文推进线、章节归属、前后顺序和相邻文章边界的文章记为“通过”。

每篇文章按以下问题判断：

1. 标题能否准确覆盖正文，正文是否混入另一篇文章应负责的主题。
2. 开头是否交代问题和阅读收益，H2/H3 是否按读者理解顺序推进。
3. 合并稿是否残留重复开头、中途总结、重复参考资料或旧文章包装标题。
4. 与同章前后文章、跨章近邻的责任边界是否清楚。
5. 文章在大章中的位置是否满足“基础机制 → 具体路径 → 诊断/实践 → 边界”的阅读顺序。

## 进度

| 大章 | 正文数 | 已审 | 状态 | 结论与处理 |
| --- | ---: | ---: | --- | --- |
| 第 1 章：系统架构全景 | 29 | 29 | 已完成 | 逐篇确认基础运行时、IPC/调度、系统服务、隔离与观测的责任边界。删除 1.7 误并的 Sharesheet 教程；重命名 1.6、1.9、1.12；清理 1.3 编号残留、1.9 重复 DeliQueue 段和 1.17/1.22 自指；补齐全章发布阶段。目标顺序随全书统一重编号落地。 |
| 第 2 章：渲染系统 | 17 | 17 | 已完成 | 逐篇确认从帧调度、App/HWUI、GPU/BufferQueue 到 SurfaceFlinger/HWC/Display 的责任链，修复 2.2/2.3/2.7/2.8 断裂编号、合并稿自指与 TaskSnapshot 内部矛盾。原 2.18 的 Pausable Composition 实验步骤并入 22.2 后删除；其余 17 篇保留。目标顺序随全书统一重编号落地。 |
| 第 3 章：输入系统 | 6 | 6 | 已完成 | 顺序保持为分发主链 → 触摸时延 → 系统导航手势 → 应用手势识别 → 输入法 → 桌面输入。修复 3.1 与 3.3 合并后断裂的章节编号；把 3.2 末尾游离的重采样源码段移动到批处理机制之后；4 篇待审状态转为可发布。 |
| 第 4 章：内存管理 | 10 | 10 | 已完成 | 顺序保持为全景口径 → ART Heap/GC → 系统压力治理 → App 优化 → 16 KB 兼容 → 资源终结 → 内核回收/规整 → ZRAM 恢复 → MTE → 跨进程推理。清理 4.1–4.3 合并稿的中途结论、重复关联和自引用，补齐全文收束；修复 4.3 编号跳跃及 4.4 重复旧标题入口；10 篇状态统一为可发布。 |
| 第 5 章：CPU 调度与能耗管理 | 9 | 9 | 已完成 | 顺序保持为调度/选核 → DVFS/温控/系统功耗 → 后台政策 → ADPF → 端侧 AI Runtime/NPU → LLM 能效 → 传感器 → Cache → LE Audio。为 5.1–5.3 三篇合并主稿和 5.5 补齐全文小结，清理自引用与重复关联；修复 5.1 温控误指 5.5、5.8 启动测量误指 21.4。第 21 章复审时把重复的通用缓存稿中独有的 SLRU/扫描污染内容并入 5.8。 |
| 第 6 章：存储与 I/O | 4 | 4 | 已完成 | 顺序保持为架构全景 → 文件系统/块层 → 配置存储 API → 共享存储。修复 6.2 双稿拼接形成的中途“结论/参考资料”、泛化标签和缺失的关联章节；修复 6.1、6.4 合并后的旧章节引用；4 篇状态转为可发布。 |
| 第 7 章：流畅性 | 6 | 6 | 已完成 | 顺序保持为定义/根因 → 方法/场景/案例 → 感知节奏 → SystemUI → HWC 合成 → 系统辅助服务。清理 7.1、7.2 合并稿的重复收尾和旧稿分隔线，修复同目标重复链接；3 篇待审状态转为可发布。 |
| 第 8 章：响应速度 | 7 | 7 | 已完成 | 顺序保持为通用响应模型 → 启动链路 → 启动优化 → 协程调度 → 登录 → 推送 → 完整性校验。清理 8.1、8.5 双重收尾和 8.1 案例分隔线；修正 8.2 重复关联、8.6 标题责任边界及 8.6/8.7 收尾顺序；4 篇待审状态转为可发布。 |
| 第 9 章：ANR | 7 | 7 | 已完成 | 顺序保持为机制/类型 → 联合诊断 → 跨边界场景 → 案例 → Notification → ContentProvider → Android 17 预警。清理 9.1/9.2/9.7 合并后的重复资料与中途关联、9.4 案例分隔线；扩充 9.4 标题并修正 9.6 版本元数据；4 篇待审状态转为可发布。 |
| 第 10 章：内存性能 | 4 | 4 | 已完成 | 顺序保持为分析方法/案例 → 系统低内存影响 → 分配抖动 → GPU 图形内存。删除 10.1 重复导语并修正层级，修复 10.2 重复编号/重复延伸阅读和 README 的 10.5 旧编号；10.4 改为能覆盖统计、归因和诊断的标题。 |
| 第 11 章：功耗 | 5 | 5 | 已完成 | 顺序保持为系统功耗模型/策略 → App 通用优化与案例 → WakeLock → Bluetooth 专项 → 用户与业务配置。修复 11.1 编号断层、11.2 两套版本边界的标题歧义、11.4 失效的跨章关联；11.5 改为覆盖全部正文变量的标题。 |
| 第 12 章：网络性能 | 2 | 2 | 已完成 | 顺序保持为端到端请求/TLS → netd/DNS 系统诊断。修复 Connectivity 旧章节号、TLS 诊断误跳和 README 中已迁出的包体积阅读路径。 |
| 第 13 章：Perfetto | 13 | 13 | 已完成 | 逐篇确认采集、UI/状态、SQL/自动化、埋点与专项诊断的责任边界。清理 13.1 自引用、旧稿分隔和重复资料；为 6 篇合并稿补齐全文收束；区分 13.6/13.7/13.13 分段资料责任；标题统一为 FrameTimeline。13 篇状态统一为可发布。 |
| 第 14 章：其他分析工具 | 17 | 17 | 已完成 | 逐篇确认 IDE、命令行、量产采集、系统指标、Hook、GPU/UI/Camera、eBPF 与构建分析工具的责任边界。清理合并稿自引用、旧分隔线和重复资料；重命名 14.12、14.13；补齐 14.13、14.16 全文收束。章内目标顺序把平台内建采集放在第三方 Hook 之前，随全书统一重编号一次落地。 |
| 第 15 章：方法论 | 8 | 8 | 已完成 | 逐篇确认原则/实证/治理、责任归因、指标监控、测试、竞品、源码阅读、AI 评测与设备策略的层级。原 21.11 是跨启动/渲染/内存/媒体的方法论，移入本章作为 15.8。目标顺序调整为原则 → 归因 → 指标 → 设备策略 → 通用测试 → 竞品测试 → 源码阅读 → AI 评测，随全书统一重编号落地。 |
| 第 16 章：AOSP 性能优化 | 9 | 9 | 已完成 | 顺序调整为平台方法/构建 → kernel/编译/启动/Rust → AppFlow/AOHP 研究原型。16.3 删除与 16.4 重复的 AutoFDO 采集教程；两篇研究原型在标题与阅读路径中明确非 AOSP 主线；修复旧编号和失效 wiki 链接。 |
| 第 17 章：OEM 与设备差异 | 7 | 7 | 已完成 | 顺序调整为 OEM 总览 → SoC → 调度/输入 → Power HAL/调频/统计 → MPC → Private Space/应用锁 → 车载。原 17.6 Power HAL 前移为 17.4，原 17.4/17.5 顺延；清理失效来源、自指和合并稿中途资料入口，为三篇补齐全文收束。 |
| 第 18 章：渲染管线专题 | 14 | 14 | 已完成 | 顺序保持为通用方法 → 软件/载体/API/layer → 框架路径 → WebView/Camera/视频/游戏 → XR/WebGPU。逐篇清理自指、重复关系与旧编号，补齐 5 篇全文收束和发布阶段；EyeDropper 不属于渲染管线，移至 22.20，余下 14 篇连续编号。 |
| 第 19 章：APM 工具与性能监控生态 | 12 | 12 | 已完成 | 顺序保持为全景选型 → 当前工具 → 历史方案 → Benchmark/实验室 → 专项采集 → 端侧架构。修正 19.4 对 Measure 的标题与导语误判、README 的 14.10 错误选型入口及 19.7 发布阶段。 |
| 第 20 章：应用稳定性治理 | 14 | 14 | 已完成 | 逐篇确认 14 篇都有单一主问题，不再合并。后半章重排为 Native 内存 → FD → 线程/协程 → Binder → Keystore → MTE → Hook → DCL → SDK；重命名 20.5/20.6，清理死链来源、自指、重复导航与断裂编号，统一补齐全文收束。 |
| 第 21 章：启动优化 | 9 | 9 | 已完成 | 逐篇确认路径/度量、任务、Provider/多进程、Profile、Splash、广告 SDK、GC、DI 与 Compose 的责任边界。通用缓存稿与 5.8 高度重复，独有 SLRU 内容并回 5.8 后删除；设备分级移入 15.8。修正自指、断裂编号、标题误导和错误关联，补齐全章收束。 |
| 第 22 章：渲染性能实践 | 20 | 20 | 已完成 | 逐篇确认 View/Compose、动画与图形效果、Surface/媒体/相机和系统能力的应用实践边界。原 2.18 的同版本验证、依赖解析和回退步骤并入 22.2 后删除；修复合并稿自指、编号断层、资料层级和错误关联，补齐 11 篇全文收束；22.16 扩充标题。目标顺序随全书统一重编号落地。 |
| 其余 4 章 | 45 | 0 | 待审 | 按章节逐篇推进。累计完成 229/274，剩余 45 篇。全书章节号存在 `1–12 → 18 → 13–15 → 19 → 16–17 → 20–26` 的确定性顺序错误，待内容合并完成后统一重编号；已确认的章内顺序也在该次重编号中一次性调整。 |

## 第 1 章逐篇结论

| 文章 | 标题契约与推进线 | 章节边界 | 处理结果 |
| --- | --- | --- | --- |
| 1.1 Android 分层架构、进程模型与线程协作 | 从系统层次进入进程创建/回收，再落到线程协作与诊断，承担全章总览。 | 只建立进程生命周期模型；1.6 展开组件/adj/锁，1.29 展开 cgroup，1.12 展开 Binder Freezer。 | 保留合并；补写三篇下钻入口，发布阶段转为可发布。 |
| 1.2 系统启动、Zygote 与图形栈预加载 | 按 Boot ROM/init/SystemServer → Zygote/预加载 → App 图形首帧推进，主线完整。 | 负责系统与应用冷启动前置机制；1.20/1.5 负责类加载和编译，2.x/18.x 负责图形细节。 | 保留；发布阶段转为可发布。 |
| 1.3 Android IPC 全景与 Binder 性能 | 先按控制面/数据面选择 IPC，再把 Binder 组织成慢调用的事务与等待链。 | 负责 IPC 选型和 Binder 通用模型；1.12 专讲线程池/oneway/Freezer，1.17 专讲缓冲区和证据。 | 保留合并；把第二大段改为诊断视角，清除“16.x”旧稿编号。 |
| 1.4 Android 版本演进中的架构变化 | 以 Treble/GKI/Mainline/ART 和 Android 15—17 变量建立版本地图。 | 负责解释后续机制为何受 targetSdk、模块、vendor 和内核版本影响。 | 保留；目标位置移动到全章总览之后。 |
| 1.5 ART 编译、验证与去优化机制 | 按 AOT/JIT/Profile → Verifier/VDEX/ODEX/dexopt → deopt 推进。 | 负责方法执行与编译状态；1.20 负责类解析、类加载和 Boot Image。 | 保留；发布阶段转为可发布。 |
| 1.6 ActivityManager 组件调度、进程优先级与锁模型 | 以组件事件 → 进程责任 → OomAdjuster → system_server 锁契约形成完整因果链。 | 广播只保留 AMS 入口，完整队列模型交给 1.19；cgroup 实际落点交给 1.29。 | 扩充标题与全文结论，补写 1.19 边界，发布阶段转为可发布。 |
| 1.7 应用分发、安装验证与 PackageManager 性能 | 从 PMS/安装主路进入开发者验证、Staged Install、AAB 与 PackageInstaller。 | 负责软件制品交付；运行时 `ACTION_SEND`/Sharesheet 不属于安装流水线。 | 删除误并的 Sharesheet 教程及其源码/资料，只留责任边界；发布阶段转为可发布。 |
| 1.8 ContentProvider 性能与优化 | 从进程启动、跨进程 Cursor、客户端稳定性、超时和线程池进入诊断与优化。 | 负责 Provider 生命周期与 RPC；Binder 通用机制回到 1.3/1.12。 | 保留。 |
| 1.9 MessageQueue 与锁竞争：从 DeliQueue 到系统等待链 | 先以 DeliQueue 解释队列去锁，再扩展到 Monitor/futex/Binder/system_server 等待链。 | 负责进程内消息队列和通用锁归因，不重复 1.12 的 Binder 队列容量。 | 扩充标题与导语；把后半篇重复 DeliQueue 实现改为等待链中的诊断回扣。 |
| 1.10 JNI、NDK 与 Bionic 原生运行时性能 | 从托管/Native 边界进入 Bionic 分配、线程、同步、MTE、页大小和 libc。 | 16 KB 前段负责 App 产物验收，后段负责 linker/Bionic 运行时机制；1.22 继续展开动态链接。 | 保留合并；明确两处 16 KB 的不同责任，重写全文结论并转为可发布。 |
| 1.11 音频链路（Audio Pipeline）延迟与性能 | 从 AudioTrack/AudioFlinger/Audio HAL 到 fast path、offload、时钟和诊断闭环。 | 负责音频数据面和延迟，不重复通用 Binder、调度或功耗机制。 | 保留。 |
| 1.12 Binder 线程池、异步事务与 Freezer | 按线程供给 → oneway 队列/反压 → 缓存进程 Freezer 的因果顺序展开。 | 缓冲区只保留解释异步预算所需语义，完整分配器/观测交给 1.17；cgroup 细节交给 1.29。 | 按正文顺序重命名，修复“14 → 12”编号并补边界，发布阶段转为可发布。 |
| 1.13 应用归档（App Archiving）机制与恢复性能 | 从归档状态、特殊卸载、Launcher 恢复请求进入回调、性能和安全边界。 | 负责已安装 App 的归档/恢复；1.7 负责一般安装与分发。 | 保留。 |
| 1.14 ResourcesManager 与 Configuration 变更性能 | 从资源管理和配置传播进入 Activity 重建、View/Compose 和性能诊断。 | 负责配置变化；1.16 负责窗口与显示系统。 | 保留。 |
| 1.15 Android AI 手机技术栈：平台接口、端侧推理与协作边界 | 按交付方分层，比较 NNAPI/HAL、AICore/ML Kit、LiteRT、AppFunctions 和性能/热边界。 | 负责 AI 生态选型全景；5.5/5.6 负责 Runtime/NPU/LLM 性能专题。 | 保留；发布阶段补为可发布，作为平台服务之后的生态收束。 |
| 1.16 Android 显示架构与 WindowManager | 从 App 窗口到 SurfaceFlinger/HWC/显示设备，再下钻 WMS 窗口、Surface 和事务。 | 负责系统显示与窗口全景；第 18 章负责各种渲染管线，后续审查时再校正重复深度。 | 保留合并；发布阶段转为可发布。 |
| 1.17 Binder 事务缓冲区与可观测性 | 先讲映射/分配/大小边界，再讲 AIDL Trace、Perfetto、binderfs/debugfs 和错误快照。 | 负责空间与证据；1.12 负责线程池、oneway 消费与冻结语义。 | 修复三处当前文章自指并更新 1.12 标题，发布阶段转为可发布。 |
| 1.18 Android 17 AVF 架构与 pKVM 隔离性能边界 | 从宿主组件、Microdroid/pKVM 内存隔离进入 CPU、I/O、生命周期与测量。 | 负责虚拟化隔离；Binder RPC 只引用 1.3，不扩展普通 Binder 实现。 | 保留；发布阶段补为可发布。 |
| 1.19 Android 17 BroadcastQueue 进程级调度与广播性能边界 | 从按进程队列、可运行选择和冷启动槽位进入优先级、超时与证据链。 | 负责广播专项；1.6 只保留组件调度入口和进程重要性背景。 | 保留；与 1.6 的边界已写回正文。 |
| 1.20 Java 类加载与 ART Boot Image | 从 ClassLoader/委派、类解析和初始化进入 Boot Image、共享页与启动诊断。 | 负责类身份与加载；1.5 负责编译/验证/deopt，1.22 负责 Native 动态链接。 | 保留。 |
| 1.21 Android logd 日志系统性能与开销 | 按写入 → socket/daemon 缓冲 → reader/权限 → 性能和观测推进。 | 负责 Android 日志数据路径，不把日志文本当成完整时间线。 | 保留；发布阶段转为可发布。 |
| 1.22 Dynamic Linker、VNDK 与 Native 库隔离 | 从 linker64 装载顺序进入 namespace、VNDK/vendor 隔离、16 KB 和诊断。 | 负责 Native 库解析与隔离；1.10 负责 JNI/Bionic 通用运行时。 | 把同篇 VNDK 自指改为“后文”，发布阶段转为可发布。 |
| 1.23 Android 17 / ACK 6.18 BPF 可观测性与可编程边界 | 从 Hook/Map/加载与权限进入可观测场景、限制和工具边界。 | 负责平台能力与内核边界；14.16 负责具体 eBPF 观测工作流。 | 保留；发布阶段转为可发布。 |
| 1.24 Telephony 服务架构、状态传播与回调 | 从 Telephony framework/RIL/HAL 进入数据、通话、短信、SIM 与回调性能。 | 负责蜂窝系统服务；Connectivity 选网与网络验证交给 1.25。 | 保留。 |
| 1.25 Connectivity 服务、网络选择与回调 | 从 ConnectivityService/NetworkAgent 进入验证、评分选择、callback、策略、VPN 与版本边界。 | 负责系统网络编排；12.x/24.x 负责请求、DNS/TLS 和 App 网络实践。 | 保留；发布阶段转为可发布。 |
| 1.26 Android 17 NotificationManager 架构与性能优化 | 按 App 构建/同步提交 → NMS 入队排序 → listener → SystemUI → 观测和新 API 推进。 | 负责通知系统完整控制链；8.6/9.5 负责推送和 ANR 场景。 | 保留；发布阶段补为可发布。 |
| 1.27 Android 17 BiometricService 架构与性能优化 | 按 AuthService/预认证 → AuthSession → sensor scheduler/HAL → 安全令牌/UI → 分段诊断推进。 | 负责 BiometricPrompt 系统仲裁；8.5/20.10 负责登录与密钥治理。 | 保留；发布阶段补为可发布。 |
| 1.28 Android 17 LocationManager 架构与性能优化 | 从请求/权限进入 Provider 合并与回调，再下钻 GNSS HAL、batching、PSDS、围栏和证据链。 | 负责平台 LocationManager；Play services Fused/Geofencing 明确排除在外。 | 保留；发布阶段补为可发布。 |
| 1.29 Android 17 cgroup v1/v2 混合层级与进程资源隔离机制 | 从默认拓扑、init/libprocessgroup、task profile 进入 OomAdjuster、CPU/memory/freezer 与 OEM 审计。 | 负责 framework 策略怎样落到内核控制器；1.6 负责策略计算，1.12 负责 Binder Freezer。 | 保留；发布阶段补为可发布，目标位置紧跟 ActivityManager 进程策略。 |

章内统一重编号的目标顺序为：架构总览 → 版本变量 → 启动/Zygote → 类加载/Boot Image → ART 编译 → JNI/Bionic → linker/VNDK → MessageQueue → IPC/Binder 总览 → Binder 线程池/异步/Freezer → Binder 缓冲区/观测 → ActivityManager → cgroup → BroadcastQueue → ContentProvider → Package/安装 → App Archiving → ResourcesManager → 显示/WMS → Audio → Telephony → Connectivity → Notification → Biometric → Location → AVF → logd → BPF → AI 生态。该顺序与全书大章编号修复在同一次重命名中执行，避免产生两轮文件名、章节号和交叉引用迁移。

## 第 2 章逐篇结论

| 文章 | 标题契约与推进线 | 章节边界 | 处理结果 |
| --- | --- | --- | --- |
| 2.1 Android 渲染架构与版本演进 | 先建立当前出图主线，再回溯 Android 3–17 的架构变量，承担全章总览。 | 只建立对象和责任地图；后续文章分别下钻调度、BufferQueue、SF 与显示场景。 | 保留合并。 |
| 2.2 帧率、刷新率与显示模式选择 | 按口径与截止时间 → ARR 约束 → 模式切换 → RefreshRateSelector 评分推进。 | 负责频率与模式决策；2.3 负责 VSync 调度，2.9 负责生产者帧节奏。 | 修复三段合并稿的编号断层、同篇自链和过度偏 ARR 的全文结论；转为可发布。 |
| 2.3 VSync、Choreographer 与 SurfaceFlinger 调度 | 从 VSync 源与预测，进入 App Choreographer，再到 SF 调度与显示策略。 | 负责“何时开始并以何节拍执行”；2.2 决定频率，2.17 解释实际帧是否超期。 | 修复三段稿件各自的中文编号跳号。 |
| 2.4 MainThread、RenderThread 与 Hardware Layer | 先拆开 UI/RT/GPU 提交边界，再讲 Hardware Layer 的录制、缓存、失效与寿命周期。 | 负责 App Window 内 HWUI 执行与离屏层；不把 View layer 与 SF layer 混为一物。 | 保留合并；删除关联章节中的同篇自链。 |
| 2.5 SurfaceFlinger 合成、FrontEnd 与事务队列 | 按 layer/合成/present → FrontEnd state/snapshot → transaction 入口与 readiness 推进。 | 负责 SF 中的状态、事务和合成；2.8 负责 buffer slot 与 fence 寿命周期。 | 合并重复的 2.8 入口，转为可发布。 |
| 2.6 过度绘制 | 从边界与颜色标记进入成本、工具、Surface 拓扑、View/Compose 修复与验收。 | 负责重复像素工作；2.7 负责更广的 GPU pipeline 与 API 选型。 | 保留。 |
| 2.7 GPU 渲染与图形 API 选型 | 先讲 GPU pipeline、瓶颈与测量，再比较 GLES、Vulkan 与 ANGLE。 | 负责 GPU 执行和 API 选型；2.4 负责 HWUI 线程边界，2.5 负责 SF 合成。 | 修复后半篇“9 → 11”的编号跳号。 |
| 2.8 BufferQueue、Gralloc 与 Sync Fence | 按 slot/所有权/反压 → buffer 分配共享 → acquire/present/release fence 推进。 | 负责 Producer–Consumer 交接和同步；2.5 负责 SF 如何消费它们。 | 修复两段合并稿源码节的跳号和对当前章节的错误自指。 |
| 2.9 Frame Pacing Library 与帧节奏控制 | 从控制量与 trace 征兆进入 Swappy、fallback、自动模式、集成和验证。 | 负责游戏/原生 Producer 的提交节奏；2.2/2.3 负责显示选择和 VSync 时序。 | 保留。 |
| 2.10 多窗口、PiP 与桌面模式渲染管线 | 从 session/display 模型进入 window/thread/surface 拓扑、Shell 几何、SF Output 和场景诊断。 | 负责窗口化出图拓扑；2.15 负责 Display 生命周期，2.13 负责折叠切换。 | 保留；转为可发布。 |
| 2.11 文字渲染性能 | 按线程与产物、Layout 选择、Minikin cache、Span/Emoji、优化与证据推进。 | 负责 HWUI/Compose 中的文字专项；不扩展到整个 GPU/SF 管线。 | 保留。 |
| 2.12 Android 17 Edge-to-Edge 渲染与 WindowInsets 处理性能 | 从版本边界和 App Window 拓扑进入 Insets 分发、动画、静态处理和多窗口诊断。 | 负责 Edge-to-Edge/Insets 对布局与合成的影响；Predictive Back 实践交给 22.9。 | 保留；补齐 22.9 关联章节。 |
| 2.13 折叠屏显示切换、窗口连续性与渲染性能 | 按 DeviceState → DMS layout → WMS/Shell → App continuity → SF/HWC 的五层链路推进。 | 负责折叠这一复合场景；2.15 提供通用 DMS 机制。 | 保留。 |
| 2.14 TaskSnapshot 捕获、Overview 缩略图与启动窗口 | 先分清 snapshot、静态卡片、live tile 与 starting window，再追踪捕获、缓存、展示和故障。 | 负责任务画面捕获与三类消费对象；不把 TaskSnapshot 与 SF LayerSnapshot 混同。 | 删除与前文“无固定秒数”相矛盾的 5 秒缓存表述，转为可发布。 |
| 2.15 DisplayManagerService：显示器发现、拓扑、功耗与渲染交接 | 从服务启动、DisplayDevice/LogicalDisplay 进入锁模型、DeviceState、VSync 边界、mode/power/VirtualDisplay 和交接。 | 负责通用 Display 管理生命周期；2.13 只在折叠场景引用该机制。 | 保留。 |
| 2.16 HDR 显示管线与色彩管理性能 | 从 ColorSpace/Dataspace/format 进入 SF 输出色彩、HWC/RenderEngine、HDR/SDR 混合、WCG/Ultra HDR/视频与观测。 | 负责色彩语义与合成位置；2.7 负责 GPU 通用执行，2.5 负责 SF 通用合成。 | 保留。 |
| 2.17 Android 17 FrameTimeline、FrameTracer 与合成边界 | 从覆盖范围、token 模型与帧边界，进入 CLIENT/DEVICE、jank、fence、SQL 和诊断步骤。 | 负责用时间线证据判断责任段；不代替 2.3 调度机制或 2.8 buffer/fence 状态机。 | 保留。 |
| 原 2.18 Compose Pausable Composition 实战指南 | 从版本轴、Lazy Layout 代码结构、cache window 进入同版本 A/B、Macrobenchmark、Perfetto 和回退。 | 内容完全属于应用层 Compose 列表实践，与 22.2 的 Lazy 预取和版本验证重叠。 | 把依赖解析、同版本开关 A/B、升级/回退等独有步骤并入 22.2 后删除。 |

章内统一重编号的目标顺序为：架构总览 → 帧率/显示模式 → VSync/调度 → MainThread/RenderThread/Hardware Layer → 过度绘制 → 文字渲染 → GPU/API 选型 → BufferQueue/Gralloc/fence → SurfaceFlinger/FrontEnd/事务 → HDR/色彩 → Frame Pacing → FrameTimeline 诊断 → DisplayManagerService → 多窗口/桌面 → Edge-to-Edge/Insets → 折叠屏 → TaskSnapshot。原 Compose Pausable Composition 不进入该顺序，独有实验步骤已并入 22.2 后删除。

## 第 4 章逐篇结论

| 文章 | 标题契约与推进线 | 章节边界 | 处理结果 |
| --- | --- | --- | --- |
| 4.1 Android 与 Linux 内存管理全景 | 先建立进程内存域与统计口径，再进入页分配、回收、缓存与 Swap，把应用视角和内核页管理连成一条因果链。 | 负责全景与口径；4.2 下钻 ART，4.3 下钻压力治理，4.7/4.8 分别展开规整和 ZRAM。 | 保留合并；把第一段“结论”改为诊断顺序，区分两组源码锚点，并在全文末尾统一收束。 |
| 4.2 ART Heap、GC 与后台维护调度 | 从对象分配/空间进入分代回收、暂停来源、HeapTask、后台维护和 trim，标题覆盖完整运行时闭环。 | 负责 ART 内部；4.6 负责终结与 Cleaner，4.3 负责系统压力和进程处置。 | 保留合并；删除中途重复关联与自引用，重写原本只总结 HeapTask 的结尾，使其覆盖 Heap、GC、后台任务和 trim。 |
| 4.3 lmkd、Cached App Freezer 与内存压力治理 | 按全局压力/lmkd → 冻结与外部回收 → MemoryLimiter/memcg → 产品预取与工作集代价推进。 | 负责系统压力下四类不同机制；4.4 负责 App 主动释放，4.8 负责换入恢复，10.2 负责性能影响。 | 保留合并；把两处中途结论改为机制判断边界，删除重复延伸阅读和自引用，修正“9 → 11”为“9 → 10”，补充全文小结。 |
| 4.4 App 内存优化与诊断 | 从优化对象和四步方法进入分配、Bitmap、泄漏、原生资源、trim、Compose、预算和线上诊断，形成应用侧闭环。 | 负责 App 通用方法；4.2/4.3 提供平台机制，23.x 负责更细的专项治理。 | 保留；删除参考资料前的旧稿分隔线，合并两条指向 4.1 的旧标题并改成当前可点击入口。 |
| 4.5 16 KB Page Size 与 Android 性能 | 先区分兼容性与性能，再按页模型、ELF/ZIP 对齐、链接器兼容、迁移、故障和测量推进。 | 负责 16 KB 的平台机制与迁移全景；20.12/20.13 负责稳定性场景中的 Hook 与动态库兼容。 | 保留；状态转为可发布。 |
| 4.6 ART FinalizerDaemon、Cleaner 与 ReferenceQueue | 从角色分工和运行时路径进入同步/看门狗/Cleaner 差异，再落到资源所有权、诊断和案例。 | 负责延迟清理机制与显式资源所有权，不重复 4.2 的一般 GC 调度。 | 保留；已发布状态保持。 |
| 4.7 内存规整与直接回收性能边界 | 先拆开四类同名机制，再沿 order、慢路径、线程、PSI、lmkd/mmd、工具和实战判读推进。 | 负责连续页与同步回收的性能边界；4.3 负责进程治理，4.8 负责 ZRAM 后处理。 | 保留；审查任务和发布状态转为已完成。 |
| 4.8 ZRAM 压缩交换与应用重启延迟 | 先用 PID 区分换入恢复和冷启动，再进入 MMD、内核实现、长尾、观测与应用/系统策略。 | 负责匿名页交换和恢复成本；4.3 负责是否终止进程，8.2/8.3 负责正常启动链与优化。 | 保留；审查任务和发布状态转为已完成。 |
| 4.9 Android 17 ARM MTE 内存标签扩展实战 | 从硬件标签与检测模式进入内核/Bionic/Scudo、堆栈全局覆盖、启用验证和安全边界。 | 负责 MTE 平台机制与接入；20.11 负责与 GWP-ASan 等稳定性手段的选型。 | 保留；状态转为可发布。 |
| 4.10 跨进程内存共享与端侧推理预算 | 从 PID/UID 归属和 PSS 记账进入 IPC、共享载体、推理预算、MemoryLimiter/lmkd 与测量评审。 | 负责跨进程共享与端侧推理的组合设计；4.3 提供压力机制，23.7 负责应用侧模型内存治理。 | 保留；补齐发布阶段并转为可发布。 |

## 第 5 章逐篇结论

| 文章 | 标题契约与推进线 | 章节边界 | 处理结果 |
| --- | --- | --- | --- |
| 5.1 Linux 调度、EAS 与大小核架构 | 从异构 CPU 的 capacity/拓扑进入运行队列、EEVDF、优先级与放置，再以 EAS 统一能量模型。 | 负责“谁在何处何时运行”；5.2 负责频率、温控和系统功耗，5.8 负责代码与数据局部性。 | 保留合并；删除两处合并后的自指，修复温控误写为 5.5，补充覆盖三段主线的全文小结并转为可发布。 |
| 5.2 DVFS、Thermal 与 Android 功耗管理 | 依次解释频率/电压控制环、温度预算与降频约束、Power HAL/挂起/WakeLock/后台状态。 | 负责“以什么性能状态运行以及何时休眠”；5.1 负责选核，5.3 负责后台任务契约，11.x 负责功耗专项。 | 保留合并；补充全文小结，已发布状态保持。 |
| 5.3 后台执行、任务调度与 App Hibernation | 从进程状态和后台限制进入 Job/Work/Alarm 的执行窗口，再讲长期未使用后的 Hibernation 与恢复。 | 负责后台工作是否获得执行机会；5.2 提供功耗控制背景，11.x 负责能量归因。 | 保留合并；把三处旧 5.3 自引用改为“前文”，补充全文小结并转为可发布。 |
| 5.4 ADPF 自适应性能框架 | 从 HintSession 反馈回路进入 Headroom、Thermal、Game Mode/State、接入与 Perfetto 验证。 | 负责应用向系统表达周期目标和读取约束，不承诺固定频率或核心；5.2 解释底层响应。 | 保留；合并两条 5.2 旧标题入口，补成当前可点击链接。 |
| 5.5 Android 端侧 AI Runtime 与 NPU 性能边界 | 按模型执行/委托/搬运 → Runtime/驱动/NPU 能力 → 系统托管 GenAI/资源竞争推进。 | 负责端侧 AI 的运行时和平台边界；5.6 负责 LLM DVFS/能效实验，4.10 负责跨进程内存预算。 | 保留合并；删除第一套中途关联和两条自引用，统一文章末尾交叉阅读并补充全文小结，转为可发布。 |
| 5.6 移动端 LLM 推理的 DVFS 与能效边界 | 从 TTFT/TPOT 指标和硬件路径进入研究边界、ADPF、工作量缩减、能效实验和热稳态。 | 负责持续 LLM 负载的频率与能量；5.5 负责通用 Runtime/NPU 能力，23.7 负责模型内存。 | 保留；已发布状态保持。 |
| 5.7 SensorService 与传感器批处理功耗模型 | 从采样/搬运/唤醒成本进入 FIFO、客户端聚合、suspend、WakeLock、Direct Channel 和 frozen PID。 | 负责传感器系统链与批处理；25.7 负责 App 场景治理，11.1 提供系统功耗总览。 | 保留；已发布状态保持。 |
| 5.8 CPU Cache 友好代码与数据布局优化 | 从硬件 Cache 模型进入局部性、业务缓存冷热分段、伪共享、C++/Java 布局、DEX Profile、Simpleperf 与源码案例。 | 负责硬件/软件 cache 名称消歧和数据访问效率；5.1 负责调度拓扑，21.4 负责 Profile 构建全流程。 | 保留；统一英文 References 标题，修复“启动测量见 21.4”为 21.1。复审 21.10 后接收其独有的 SLRU、扫描污染、加载去重和锁外释放内容。 |
| 5.9 Bluetooth LE Audio 延迟与功耗性能 | 从协议与延迟预算进入 Android 路由/软件与 offload 路径、功耗、广播、HAP/ASHA 和测量。 | 负责 LE Audio 全链路性能；11.4 负责 Bluetooth 通用功耗，25.9 负责后台音频策略。 | 保留；完成待审任务并转为可发布。 |

## 第 3 章逐篇结论

| 文章 | 标题契约与推进线 | 章节边界 | 处理结果 |
| --- | --- | --- | --- |
| 3.1 Input 分发、拦截与安全边界 | 先讲 evdev 到 View 的分发、队列、完成反馈和诊断，再讲过滤、监控、注入与权限，两部分都由输入分发责任边界连接。 | 负责平台主链与特权分支；3.2 负责输入到显示时延，3.4 负责应用内识别。 | 保留合并；修正“十 → 十三 → 11.1”的断裂编号并转为可发布。 |
| 3.2 触摸延迟、预测与低延迟渲染 | 从测量口径和七段时延进入采样、批处理/重采样、诊断、预测与低延迟显示，标题覆盖正文。 | 负责触摸到显示的时间链；3.1 不重复渲染阶段，3.4 不重复系统时延。 | 保留；把游离在误区之后的重采样源码段移动到批处理之后并转为可发布。 |
| 3.3 系统手势导航与 Predictive Back | 先解释系统手势路由，再深入 Predictive Back 生命周期、目标预测、动画和观测，属于同一系统返回手势主题。 | 负责 SystemUI/WMS/Shell 的系统返回路径；22.9 负责 App 导航实践。 | 保留合并；修正第 11 节后跳到第 13 节的编号。 |
| 3.4 手势识别算法与性能优化 | 按事件所有权、速度估算、状态机、View 冲突、阈值、自定义识别器和 Compose 推进。 | 负责应用进程内的识别与消费，不重复 3.1 的窗口分发和 3.3 的系统手势。 | 保留。 |
| 3.5 InputMethodManager 与软键盘性能 | 按请求语义、系统显示链、冷启动/会话、Insets 动画、ImeTracker 与复现测量推进。 | 负责 IME 会话和显示路径；3.6 只说明硬件键盘经过 IME 的分发位置。 | 保留；转为已审。 |
| 3.6 键盘、鼠标与指针输入性能 | 从设备映射、捕获、键盘/鼠标分发扩展到多窗口、多显示和拖放，覆盖桌面模式输入闭环。 | 负责非触摸与桌面交互，作为输入系统最后一篇。 | 保留；转为可发布。 |

## 第 6 章逐篇结论

| 文章 | 标题契约与推进线 | 章节边界 | 处理结果 |
| --- | --- | --- | --- |
| 6.1 Android 存储架构 | 以一次 I/O 的完整层级为主线，按器件、块层、分区、文件系统/加密、OTA 和观测展开，标题能够覆盖正文。 | 负责全景与层级定位；6.2 负责文件系统/调度细节，6.4 负责共享存储数据路径。 | 保留；把“老设备卡顿”泛化引用改为 7.2 中有实际内容支撑的存储/内存压力案例。 |
| 6.2 文件系统与 I/O 调度 | 两个主题都属于一次 I/O 的连续下半程，但合并后保留了两套旧稿收尾。 | 负责 VFS、ext4/F2FS/EROFS、块队列、调度与 Perfetto 定位；不展开 6.3 的 API 生命周期和 6.4 的 FUSE 权限路径。 | 保留合并；把中途“参考资料/结论”改为对应机制的源码锚点和判断边界，补充主题标签、关联章节并转为可发布。 |
| 6.3 SharedPreferences 与 DataStore | 从 SP 首次读取/写盘/组件收尾风险，推进到 DataStore 语义、迁移、多进程、选型与观测，形成完整实践链。 | 负责配置数据 API 与一致性；底层文件系统等待只引用 6.2，不重复解释。 | 保留；审查状态转为可发布。 |
| 6.4 vold、MediaProvider 与 FUSE | 围绕控制面/数据面、四类访问入口、passthrough/BPF、App 场景与诊断展开，主题聚焦。 | 负责共享存储；6.1 只提供架构概览，24.9 负责 App 侧媒体 API 与转码实践。 | 保留；合并旧引用为当前 6.2 和 24.9 标题，审查状态转为可发布。 |

## 第 7 章逐篇结论

| 文章 | 标题契约与推进线 | 章节边界 | 处理结果 |
| --- | --- | --- | --- |
| 7.1 卡顿定义、分类与原因体系 | 先统一 FrameTimeline、JankType 和统计口径，再沿主线程、RenderThread、GPU、BufferQueue、SurfaceFlinger 与显示末端建立原因树。 | 负责“卡顿是什么、可能从哪里来”；7.2 负责如何取证，8.x 负责响应延迟，9.x 负责 ANR。 | 保留合并；删除第一套“与其他章节”收尾，把关联入口和两组资料统一到文章末尾。 |
| 7.2 卡顿分析方法、典型场景与案例 | 按异常帧归因方法、滚动/动画/启动等场景、五个证据案例推进，形成“方法 → 应用 → 复盘”的完整链。 | 负责跨场景的调查方法；22.x 负责具体 UI 工程优化，13.x 负责 Perfetto 工具操作。 | 保留合并；删除 19 处旧稿分隔线和两套中途关联章节，合并同目标重复链接，按三类整理资料并转为可发布。 |
| 7.3 感知流畅性：步幅波动与无掉帧卡顿 | 从“帧准时不等于运动均匀”进入时间量化、轨迹残差、对照实验和修复边界。 | 负责 FrameTimeline 无异常时的运动节奏；不重复 7.2 的迟到帧诊断。 | 保留。 |
| 7.4 SystemUI 性能分析 | 从 flag、窗口和线程拓扑进入通知 Shade、状态栏、导航、多显示、启动/Overview 与现场取证。 | 负责 SystemUI/Launcher/WM Shell 共同参与的系统界面；普通 App 场景仍回到 7.2。 | 保留；审查状态转为可发布。 |
| 7.5 HWC Overlay Plane 与合成降级排查 | 从 App 按时交帧但显示仍迟到的边界，进入 composition 语义、validate/present、证据、场景和验证。 | 负责显示合成降级；2.5/2.8 负责基础机制，18.11 负责视频编解码场景。 | 保留。 |
| 7.6 Accessibility、ContentCapture 与 Autofill 性能 | 先讲无障碍事件/节点查询，再比较 ContentCapture 与 Autofill 的结构传输；两部分由“界面语义结构与跨进程成本”连接。 | 负责辅助服务改变 UI/响应开销的专项；3.1 负责输入过滤，22.1 负责普通 View 结构优化。 | 保留合并；明确两组源码资料的主题归属，修正验证版本元数据并转为可发布。 |

## 第 8 章逐篇结论

| 文章 | 标题契约与推进线 | 章节边界 | 处理结果 |
| --- | --- | --- | --- |
| 8.1 响应速度原理、场景与案例 | 从交互起止点和 input-to-present 主链进入页面、点击、搜索、Deep Link 等场景，再用四个案例说明收益边界。 | 负责响应速度的通用口径和场景地图；8.2/8.3 负责启动专项，7.x 负责连续帧流畅性。 | 保留合并；删除第一套中途结论和 8 处案例分隔线，统一文章级小结并按平台/案例整理资料。 |
| 8.2 App 冷启动链路与 Binder Trace 分析 | 先拆解冷启动、TTID/TTFD、Provider、Profile 与首帧，再用 Binder Trace 下钻跨进程等待。 | 负责启动系统链与 IPC 证据；8.3 负责改造策略，13.x 负责通用 Perfetto 操作。 | 保留合并；明确启动资料入口，合并两条指向 1.12 的关联并删除自引用，审查状态转为可发布。 |
| 8.3 启动优化策略 | 按指标/关键路径、延迟与懒加载、初始化 DAG、Provider、Splash、布局、Profile、回归推进。 | 负责工程改造与验证，不重复 8.2 的平台启动时序。 | 保留。 |
| 8.4 Kotlin Coroutine、Flow 与线程调度实践 | 从 Dispatcher、切换成本和结构化并发进入 Flow 背压、工具观测、自定义线程与版本边界。 | 负责异步执行语义和资源预算；具体启动任务编排仍由 8.3 负责。 | 保留。 |
| 8.5 Keystore、Biometric 与 Credential 登录性能 | 从 Keystore/KeyMint operation 进入认证 UI、Credential provider 与登录完成，两部分共同组成安全登录关键路径。 | 负责性能和安全约束的分段归因；20.10 负责配额/失效稳定性，8.7 负责 Play Integrity。 | 保留合并；删除第一套关联/结论，将 Keystore 判断并入全文小结，移除无关的 20.2 关联并转为可发布。 |
| 8.6 推送通知管线性能：FCM 投递、NMS 入队与 SystemUI 渲染 | 按到达定义、消息形态/优先级、App 回调、NMS 入队、SystemUI 视图和端到端观测推进。 | 负责推送到可见通知的全链路；9.5 负责通知相关 ANR，7.4 负责 SystemUI 通用性能。 | 标题改为准确表达三段责任方；把小结移到交叉引用/资料之前并转为可发布。 |
| 8.7 Play Integrity API 性能与集成延迟 | 从接口边界、Standard/Classic、服务端校验进入分段延迟、重试、配额和观测。 | 负责闭源 Play 完整性服务的集成边界；8.5 负责本地密钥/认证，12.1 负责网络/TLS。 | 保留；合并同目标交叉引用、补成可点击的当前章节链接，调整为“交叉引用 → 参考资料”并转为可发布。 |

## 第 9 章逐篇结论

| 文章 | 标题契约与推进线 | 章节边界 | 处理结果 |
| --- | --- | --- | --- |
| 9.1 ANR 机制、类型与触发条件 | 先讲计时责任、处置流程和证据产物，再逐项说明 Input、Broadcast、Service、Provider 与 JobService 超时。 | 负责 detector 和期限契约；9.2 负责诊断证据，9.7 负责 Android 17 deadline 前预警。 | 保留合并；删除正文末尾与文章级参考资料重复的第二套源码/官方资料入口。 |
| 9.2 ANR 与 Kernel Trace 联合诊断 | 从现场保护和线程栈进入 Perfetto、日志、线上聚类，再下钻调度、Binder、I/O、内存和 eBPF。 | 负责从快照到时间线的跨层证据；13.x 负责工具通用操作，26.2 负责监控平台。 | 保留合并；删除两段正文之间的重复关联章节，在文章末尾统一成当前入口，去掉自引用/重复资料并转为可发布。 |
| 9.3 特殊与跨边界 ANR | 以证据跨进程、组件和内核边界为总线，覆盖饥饿/freezer、广播、Provider、SharedPreferences、Binder、GC/LMK、FGS 与 SQLite。 | 负责基础 detector 之外的复合现场；机制回到 9.1，通用取证回到 9.2。 | 保留；审查状态转为可发布。 |
| 9.4 ANR 诊断案例集 | 七个案例按证据分级、时间对齐、根因与修复复盘，末尾给统一分析顺序和线上聚合方法。 | 负责完整案例，不重复 9.2 的通用步骤和 9.3 的主题目录。 | 标题由“案例集”扩充为可脱离目录理解的标题；删除 7 处旧稿分隔线。 |
| 9.5 Notification 性能与 ANR | 按发布同步边界、NMS、RemoteViews、NLS、典型模式和 Perfetto 诊断推进。 | 负责通知造成的 ANR；8.6 负责 FCM 到可见通知的端到端延迟，7.4 负责 SystemUI 通用性能。 | 保留。 |
| 9.6 ContentProvider 超时与 ANR 四路径 | 依次区分 publish guard、ready timeout、call hang detector 和 async callback timeout，再给决策表与修复。 | 负责 Provider 四类计时器；1.8 负责 Provider 架构，9.1 负责通用 ANR 类型。 | 保留；修正仍写 Android 16 的验证元数据，补齐发布状态并转为可发布。 |
| 9.7 Android 17 ANR 预警与 Input pre-ANR | 先讲公开 warning API，再沿 InputDispatcher、WMS、AMS 还原 no-focus pre-ANR 到正式 ANR 的时序。 | 负责 API 37 预警能力和 Input producer；不把 warning 误写成所有 ANR 的统一前置阶段。 | 保留合并；区分两处版本边界标题，把关联章节与两组资料分开，删除重复链接并转为可发布。 |

## 第 11 章逐篇结论

| 文章 | 标题契约与推进线 | 章节边界 | 处理结果 |
| --- | --- | --- | --- |
| 11.1 Android 功耗模型与系统级优化 | 先建立组件功耗、驻留时间和归因口径，再进入调度、休眠、后台限制、节电策略与诊断，标题覆盖完整系统侧闭环。 | 负责系统模型与政策；11.2 负责 App 侧组件和业务案例，25.1 负责以工具为中心的功耗诊断。 | 保留合并；修正第 10 节后跳到第 13、14 节的编号断层。 |
| 11.2 App 耗电优化与案例 | 从组件活动、唤醒和后台工作进入六类案例，机制与案例形成“原则 → 落地”关系。 | 负责 App 通用优化方法；11.3、11.4 分别下钻 WakeLock 和 Bluetooth，25.x 承担场景化实践。 | 保留合并；分别命名案例版本边界和全文版本边界，避免两处同名收尾。 |
| 11.3 WakeLock 机制与功耗分析 | 按 API 语义、PowerManagerService、SystemSuspend、内核唤醒源和现场诊断推进。 | 负责 WakeLock 全栈机制，作为通用 App 优化之后的第一篇专项。 | 保留。 |
| 11.4 Bluetooth 扫描与连接功耗分析 | 从扫描约束、生命周期、GATT 连接进入证据链与 BLE Audio，覆盖蓝牙功耗主路径。 | 负责 Bluetooth 专项；5.9 负责 LE Audio 时延/功耗权衡，25.9 负责后台音频场景。 | 保留；删除误指向崩溃/ANR 和定位传感器的关联章节，改为 5.9、25.9。 |
| 11.5 用户设置与业务配置对能耗的影响 | 从测量口径进入亮度、刷新率、深色模式、节电模式、视频清晰度、消息长度和网络状态，再落到实验与产品策略。 | 负责用户可调设置和业务变量，是本章从平台机制到产品决策的收尾。 | 扩充标题以覆盖正文；修复 11.5.2 误写成 11.3.2。 |

## 第 12 章逐篇结论

| 文章 | 标题契约与推进线 | 章节边界 | 处理结果 |
| --- | --- | --- | --- |
| 12.1 Android 网络与 TLS 性能优化 | 先分解请求排队、DNS、连接、传输和应用处理，再下钻 TLS 握手、证书与安全策略，标题覆盖两条连续路径。 | 负责应用端到端请求和 TLS；12.2 负责系统 DNS 内部，24.3/24.4 负责 App 网络工程实践。 | 保留合并；把系统选网引用从旧的 1.24 修正为当前 1.25。 |
| 12.2 netd 与 DnsResolver | 按组件边界、版本迁移、API、系统调用路径、Private DNS、诊断、HTTPDNS 和指标推进。 | 负责系统 DNS 与故障证据；普通 HTTP/TLS 性能回到 12.1。 | 保留；修复 TLS 慢时错误跳回本篇的问题。 |

## 第 10 章逐篇结论

| 文章 | 标题契约与推进线 | 章节边界 | 处理结果 |
| --- | --- | --- | --- |
| 10.1 App 内存分析与案例 | 先统一内存口径、工具和基线，再用四个案例展示从曲线到持有者/系统证据的归因。 | 负责诊断入口与案例；4.x 负责平台机制，23.x 负责 App 专项治理。 | 保留合并；删除第二套重复导语，修正 6.2 的标题层级和 10.4 新标题引用。 |
| 10.2 低内存对系统性能的影响 | 从回收、PSI、lmkd 推进到 Perfetto、ZRAM/MGLRU/MemoryLimiter 和 App 适配。 | 负责系统压力如何转化为用户性能损失，不重复 4.3 的 lmkd 机制全解。 | 保留；修复重复 7.1、合并指向同一 4.1 的重复延伸阅读。 |
| 10.3 内存抖动与频繁 GC | 从短命分配与 CMC 边界进入热点、证据、优化和 Compose 分配，主题聚焦。 | 负责 allocation churn；泄漏治理由 23.1 负责，ART 收集器机制由 4.2 负责。 | 保留。 |
| 10.4 GPU 与图形内存统计、归因与诊断 | 从计量口径进入 GpuService/DMA-BUF，再给归因实验、资源生命周期、修复方向和场景预算。 | 负责图形内存证据链；工具操作与单帧分析由 14.11 负责，图片/Surface 实践由 22.5、22.17 负责。 | 标题扩充“归因与诊断”，修复失效的 22.9 关联并转为可发布。 |

## 第 13 章逐篇结论

| 文章 | 标题契约与推进线 | 章节边界 | 处理结果 |
| --- | --- | --- | --- |
| 13.1 Perfetto 入门、Trace 抓取与可靠性 | 从架构和入口进入采集配置、大文件分析，最后用丢包、时钟和观测开销收口。 | 负责“如何得到可信 trace”；13.2 负责读图，13.6/13.12 负责写入路径。 | 保留四段合并；清理自引用、旧稿分隔、编号跳跃和重复资料，补充全文小结。 |
| 13.2 Perfetto UI、状态轨道与版本边界 | 先建立 track/slice/counter/flow 的读图语义，再专门解释 state track 和多版本线。 | 负责界面与通用轨道语义；13.3 下钻 CPU 状态，13.13 下钻帧数据。 | 保留合并；补充全文小结并统一为可发布。 |
| 13.3 线程 CPU 状态分析 | 按数据来源 → Running/Runnable/Sleeping/D → IRQ → 窗口量化 → 误读推进。 | 负责线程调度状态的证据语义，不承担通用 UI 入门或 DVFS 因果。 | 保留。 |
| 13.4 Perfetto 指标自动化与分析平台 | 从 SQL Metric、批处理和 CI 扩展到任务、证据、provider 和企业存储治理。 | 负责“如何规模化复用分析”；13.7 负责 SQL 本身，13.11 负责单次 Agent 调查协议。 | 保留合并；补充全文小结。 |
| 13.5 Perfetto 输入延迟 SQL 深度分析 | 按两条数据链 → 公开表/延迟公式 → input-to-display → 队列/ANR → 模板与批量对比推进。 | 负责输入专项 SQL；3.2 负责触摸机制，9.x 负责 ANR 通用诊断。 | 保留。 |
| 13.6 Android Tracing 基础设施与自定义 Trace | 从 ftrace/atrace/Perfetto 数据路径进入应用的同步、异步和 counter 埋点。 | 负责平台追踪基础设施和公开 Trace API；13.12 负责 Perfetto SDK 与自定义 data source。 | 保留合并；区分前半篇源码锚点，补充全文小结。 |
| 13.7 Perfetto SQL、SPAN_JOIN 与 Jank CUJ | 按基础数据模型 → 区间关联/窗口函数 → Jank CUJ 标准库推进。 | 负责通用查询方法；13.5、13.9、13.10、13.13 是各数据域的专项应用。 | 保留三稿合并；为三组源码资料标明局部责任，补充全文小结。 |
| 13.8 Perfetto Profile 导入与 Flamegraph 分析 | 从 pprof/Simpleperf/linux.perf 的数据差异进入火焰图、符号、SQL 和跨数据源拼接。 | 负责 CPU profile 文件导入与样本解读，不把样本宽度当墙上时间。 | 保留。 |
| 13.9 Perfetto CPU 频率与 DVFS 关联分析 | 从频率轨语义进入区间重建、Running 相交、迁核、AI 负载和 thermal 交叉验证。 | 负责 trace 中的 DVFS 证据；5.1/5.2 负责调度和功耗机制。 | 保留；补充全文小结并转为可发布。 |
| 13.10 BufferQueue 阻塞的 Perfetto 识别 | 从 FrameTimeline 定位 Surface，再追 dequeue、BLAST 计数器、release 和线程状态。 | 负责“如何证明某条队列背压”；2.8 负责 BufferQueue 机制，13.13 负责帧身份和帧阶段。 | 保留。 |
| 13.11 Agent 辅助 Perfetto 分析协议 | 按输入约束 → scratchpad → schema-first SQL → 候选方向 → 证据输出与补采推进。 | 负责 Agent 调查过程和停止条件；13.4 负责平台化，13.7 负责查询方法。 | 保留；完成待审状态并转为可发布。 |
| 13.12 Perfetto SDK 与应用内 Trace 数据源 | 按 backend 边界、custom schema/importer、启动采集、构建兼容、隐私与验收推进。 | 负责 SDK 与应用自定义 data source；13.6 负责 ATrace 和系统基础设施。 | 保留。 |
| 13.13 FrameTracer 与 FrameTimeline 分析 | 先讲 Graphics Frame Event 与 BufferQueue frame number，再讲 Expected/Actual、token 和 Jank 分类。 | 负责两套帧身份和时间语义；13.10 使用它们做 BufferQueue 专项归因。 | 保留合并；区分两组源码资料，删除自引用，补充全文小结，标题统一为 FrameTimeline。 |

## 第 14 章逐篇结论

| 文章 | 标题契约与推进线 | 章节边界 | 处理结果 |
| --- | --- | --- | --- |
| 14.1 Android Studio Profiler | 从问题与任务入口进入 CPU 三种模式、内存、采集开销、Perfetto 互补、功耗与量产边界。 | 负责 IDE 内的应用视角分析入口；14.2 下钻 CPU，14.3 下钻内存，14.8 负责量产采集 API。 | 保留；通读确认结构完整、状态保持可发布。 |
| 14.2 Simpleperf 与 ARM Topdown 微架构分析 | 从采样/调用图/硬件事件基础推进到 Android 17 SPE 工作流，再用 Topdown 分类和反证收束。 | 负责 CPU 热点与微架构证据；13.8 负责 profile 导入，14.16 负责 eBPF 观测。 | 保留合并；删除两处当前文章自指，按 Simpleperf 与 ARM Topdown 重组资料。 |
| 14.3 内存分析、HPROF 与 Heap Dump 工具 | 先按 Java、Native、图形和映射选择工具，再下钻 HPROF 生成、传输与引用图，最后声明版本边界。 | 负责工具选型和堆产物；4.x/10.x 负责机制与性能影响，23.x 负责应用专项治理。 | 保留合并；按内存工具与 HPROF/ART Heap Graph 重组资料。 |
| 14.4 dumpsys 系列命令 | 先固定快照证据语义，再依次覆盖 activity、meminfo、gfxinfo、cpuinfo、window、batterystats、SurfaceFlinger 与自定义 dump。 | 负责系统服务当前状态和累计窗口；时间因果交给 Perfetto/Winscope，专项对象图与功耗交给对应工具。 | 保留；通读确认命令顺序、口径和取证清单形成闭环。 |
| 14.5 Battery Historian 与功耗分析工具 | 从证据类型和工具选择进入 Historian/batterystats、Perfetto rail、Power Profiler、PowerMetric、PowerMonitor 与 A/B 实验。 | 负责功耗工具与计量口径；11.x 负责功耗机制和优化策略。 | 保留；删除旧稿末尾分隔线，状态保持可发布。 |
| 14.6 自动化性能测试与 CLI Agent 工作流 | 从场景、基线、重复测量和门禁进入 CLI/Agent 编排、证据回传与常见误区。 | 负责测试与工具编排；13.4 负责 Perfetto 分析平台，13.11 负责单次 Agent 调查协议。 | 保留合并；按基准自动化与 CLI/Agent 重组资料，删除重复 Macrobenchmark 链接。 |
| 14.7 三方性能库、Hook 与可观测性基础设施 | 先比较信号覆盖、运行开销与选型，再进入插桩、Native Hook、回调安全和验证约束。 | 负责第三方能力及其风险；平台内建 ProfilingManager/statsd/StrictMode 应先于本篇出现。 | 保留合并；清除旧稿自引用，章内位置将在统一重编号时移到当前 14.10 之后。 |
| 14.8 ProfilingManager | 按采集类型选择、API/trigger 版本、请求与回调、文件隐私、失败结果、场景和上线清单推进。 | 负责量产设备受控采集；14.1 负责连接设备上的 IDE 交互分析。 | 保留合并；修复发布阶段，确认显式请求与系统触发两条主线完整。 |
| 14.9 statsd 与系统级指标采集 | 从 statsd/atom/metric 模型进入本地配置、事件入口、交叉验证、权限、CTS/APM 与厂商扩展。 | 负责系统事件索引与聚合；Perfetto 负责时间线，App APM 负责业务会话。 | 保留；通读确认“模型 → 操作 → 证据边界 → 长期治理”顺序成立。 |
| 14.10 StrictMode 性能检查与开发期诊断 | 从 ThreadPolicy/VmPolicy 进入 detector、penalty、Binder 传播、自动化、多进程与能力缺口。 | 负责开发期运行时违规信号；精确耗时和系统因果仍交给 Perfetto。 | 保留；通读确认性能、资源与安全 detector 均由“开发期诊断”标题覆盖。 |
| 14.11 GPU 调试与 AGI 单帧分析 | 先按 API 捕获、counter 和 system trace 选型，再讲 AGI 捕获/重放/单帧分析及误区。 | 负责 GPU 命令与单帧内容；14.12 负责连续 counter、内存和 GpuService 时间线。 | 保留合并；修复发布阶段，全文结论覆盖两段主线。 |
| 14.12 GPU Counter、内存与 GpuService 可观测性 | 从频率/counter/内存事件进入 GpuService 数据源、时间线和驱动统计。 | 负责连续 GPU 可观测证据；10.4 负责图形内存归因方法，14.11 负责单帧调试。 | 标题由泛化的 observability 扩充为可直接覆盖三类正文对象；修复发布阶段。 |
| 14.13 Android Performance Analyzer 与 GAPS：性能追踪与目标可达性 | 先讲 APA 的统一性能检查与 system trace，再讲 GAPS 的静态路径重建和动态触达验证。 | 两类工具共享“自动取得现场证据”，但分别证明性能时序和目标方法可达性。 | 扩充标题以消除缩写含义不明；按两类工具分组资料并补充全文小结。 |
| 14.14 Camera 性能分析工具：Perfetto、SQL 与 GFXReconstruct | 从最小 Buffer 模型与 Perfetto/SQL 进入预览卡顿、功耗、Camera2/CameraX、HAL3 和像素问题。 | 负责 Camera 工具链和证据；2.x 负责通用图形管线，22.x 负责应用 UI/媒体场景。 | 保留；修复发布阶段，通读确认专项工具与问题类型顺序成立。 |
| 14.15 Winscope、Layout Inspector 与 UI 状态调试 | 先用 Winscope 观察窗口、Layer、transition 与输入时间线，再用 Layout Inspector 检查 View/Compose 当前结构。 | 负责系统窗口状态与应用布局快照的互补；帧耗时交给 Perfetto，GPU/像素交给 AGI。 | 保留合并；删除 Layout Inspector 段落对当前文章的自链接，按两类工具分组资料并补齐审查状态。 |
| 14.16 Android eBPF 架构与性能观测 | 从 Hook 点/Map/场景进入 bpfloader、对象组织/权限，再落到 Android 17 程序、事件和消费端。 | 负责内核与用户态探针基础设施；14.2 负责 PMU 采样，14.9 负责聚合 atom。 | 保留三段合并；删除旧稿分隔、自引用和中途延伸阅读，区分三组源码资料并补充全文小结。 |
| 14.17 R8 Configuration Analyzer 与 keep 规则体积归因 | 从报告生成和指标进入规则代价、排查、full mode、CI、APK Analyzer 边界和 Agent 安全边界。 | 负责 keep 规则因果；25.5 负责 APK/AAB、资源与 Native SO 的总体体积优化。 | 保留；补齐审查状态，删除同一 25.5 入口的连续重复引用。 |

## 第 15 章逐篇结论

| 文章 | 标题契约与推进线 | 章节边界 | 处理结果 |
| --- | --- | --- | --- |
| 15.1 Android 性能优化原则、实证与治理 | 从道/术/器和实验设计进入真实问题模式与证据要求，最后落到基线、门禁、角色和发布验收。 | 负责把单次调查组织成长期工程闭环；15.2 下钻归因，15.3 下钻指标，15.5 下钻测试协议。 | 保留三稿合并；清除当前文章自指和重复关系，按方法、实证、治理分组资料并删除重复入口。 |
| 15.2 如何区分系统问题和 App 问题 | 从目标延迟窗口和线程状态进入 CPU、Binder、内存、渲染、thermal、ANR 与系统版本 A/B。 | 负责跨层责任归因；具体机制回到各专项章，15.1 负责治理流程。 | 保留；通读确认“观测 → 直接原因 → 所有者 → 改动责任”贯穿全文。 |
| 15.3 性能指标体系与线上监控 | 先定义指标合同、分位数和场景基线，再进入信号/证据/分析三层、采样聚合、告警和版本归因。 | 负责长期指标和线上系统；15.1 负责治理，15.5 负责受控测试，14.x 负责工具细节。 | 保留两稿合并；删除当前文章自指，按指标计量、源码索引和线上 API 重组资料并去重。 |
| 15.4 竞品分析方法 | 从可比性与控制变量进入启动、流畅性、包体积，再讲误区、自动化和功耗扩展。 | 负责跨应用对照实验，是通用性能测试方法的具体应用。 | 保留；正文顺序成立；将在统一重编号时移动到通用测试之后。 |
| 15.5 性能测试最佳实践 | 从测试合同和环境标准化进入干扰控制、采样、异常值、基线、报告、CI 和线上数据边界。 | 负责所有受控性能实验的通用协议；14.6 负责工具编排，15.4 负责竞品场景。 | 保留；把 Macrobenchmark CI 从“扩展”改为核心段落，合并重复的 15.3 关系说明；目标位置前移到竞品分析之前。 |
| 15.6 AOSP 代码阅读 | 从版本/项目/路径坐标进入在线搜索、关键目录、日志/trace 反查、四个入口、跨边界调用链和版本历史。 | 负责从运行证据到当前 tag 源码的阅读方法，不重复各机制章的具体实现。 | 保留；通读确认“证据 → 定位 → 构建归属 → 运行验证 → 版本”闭环，状态转为可发布。 |
| 15.7 Google Android Bench：AI 编码能力评测方法论 | 从数据集、执行框架和 verifier 进入版本差异、pass@1、污染、排行榜与私有评测设计。 | 负责 AI Android 编码评测；15.5 提供一般实验与统计原则。 | 保留；补齐审查与发布状态，确认 Android 平台版本与评测框架版本明确分离。 |
| 15.8 设备分级性能策略实战 | 从稳定能力画像、工作负载策略和会话压力进入公开 API、策略映射、动态收缩、离线配置和实验。 | 负责跨启动、渲染、内存、媒体与网络的设备策略方法；具体机制回到各专项章。 | 从原 21.11 移入方法论；补全文小结，并纳入统一重编号时的章内目标顺序。 |

## 第 16 章逐篇结论

| 文章 | 标题契约与推进线 | 章节边界 | 处理结果 |
| --- | --- | --- | --- |
| 16.1 AOSP 性能优化与 Android 版本变更 | 先讲平台改动的定位、证据、交付与回滚，再按 Android 12—17 梳理 target/平台/API 变化，最后下钻 Android 17 适配。 | 负责平台优化方法和版本地图；ART、Binder、图形与 kernel 机制交给各专项。 | 保留合并；修正当前文章自指、失效 wiki 链接，补齐全文小结。 |
| 16.2 AOSP 源码编译与调试环境 | 从主机、源码 tag、Soong/lunch 进入模块构建、Cuttlefish/真机同步、调试、内核构建和实验记录。 | 负责把源码判断变成可运行构建；不承担具体子系统优化方法。 | 保留；通读确认“固定版本 → 构建 → 部署 → 验证”闭环成立。 |
| 16.3 Android 17 Kernel 6.18 与 ARM64 安全开销 | 先核对 GKI 调度、存储、MGLRU 与构建能力，再按 ARM64 安全机制、设备状态和 A/B 边界推进。 | 负责 kernel 功能集合与安全开销；AutoFDO 完整采集和构建流程交给 16.4。 | 删除与 16.4 重复的 AutoFDO 采集教程，只保留启用证据；修正 Rust 编号并补齐全文小结。 |
| 16.4 AutoFDO 反馈导向优化与 Android 验证 | 从 Sample PGO、用户态/GKI 接入进入 ETM 采集、Profile 转换、质量控制、A/B 和团队职责。 | 负责 AutoFDO 全流程；ART Baseline/Cloud Profile 由 16.5、21.4 负责。 | 保留；作为 16.3 的专项下钻，补充双向关联。 |
| 16.5 Profile、DM 与 Secure Dex Metadata 安装编译 | 先区分 Profile/DM/SDM/SDC，再沿 PackageInstaller、ART Service、运行时加载、性能实验和分发职责推进。 | 负责 ART 安装编译产物；native/kernel AutoFDO 交给 16.4，应用 Baseline Profile 交给 21.4。 | 保留合并；通读确认三篇来源围绕同一安装编译主链。 |
| 16.6 Android 系统启动耗时优化与 bootanalyze | 从启动终点与样本分类进入 bootanalyze/bootio/Perfetto，再按 init、kernel、Zygote、SystemServer 和启动尾部诊断。 | 负责整机上电到可交互；App 冷启动由 8.2、21.1 负责。 | 保留；修复重复/失效边界链接并转为可发布。 |
| 16.7 Android 17 平台 Rust 性能边界：Binder、CXX 与 Soong | 从平台采用现状进入 Binder/CXX/JNI、panic/所有权、运行时成本、Soong、测量和优化。 | 负责已进入 AOSP 的 Rust 系统组件与跨语言边界；不讨论 kernel Rust。 | 从原 16.8 前移到两篇研究原型之前；完成发布状态。 |
| 16.8 AppFlow 研究原型：GB 级应用冷启动内存联合调度 | 从论文证据进入预读、内存回收、进程终止，再与 Android 17 LMKD/MGLRU 对照并设计产品实验。 | 负责非主线研究原型，不把论文参数或收益写成 Android 17 默认能力。 | 原 16.7 后移；标题增加“研究原型”，修正旧编号和 wiki 链接。 |
| 16.9 AOHP 研究原型：将 Android 改造为 Agent 原生 OS | 从架构与实现进入虚拟显示/SUI/事件/沙箱、安全信息流、实验，再与 AppFunctions 对照。 | 负责 OS 级 Agent 研究原型和标准平台边界；不把 AOHP fork 当作 AOSP 17。 | 标题增加“研究原型”，作为全章未来方向收束并转为可发布。 |

## 第 17 章逐篇结论

| 文章 | 标题契约与推进线 | 章节边界 | 处理结果 |
| --- | --- | --- | --- |
| 17.1 OEM 性能优化与应用协作 | 前半从设备资源、Freezer、预加载和后台治理建立 OEM 分析框架，后半进入 Game Mode、ADPF、启动案例、折叠屏和跨形态实验。 | 负责公共机制、厂商策略、目标设备证据和应用协作的总览；SoC、调度和功耗细节由 17.2—17.4 展开。 | 保留两段合并；把中途资料标题限定为前半部分核查入口，修正当前文章自指，删除两个已确认失效且不作证据的来源，补齐全文小结。 |
| 17.2 SoC 平台差异 | 从证据层级与代表性平台进入 CPU、GPU、NPU/DSP/ISP、内存、工具和跨设备实验流程。 | 负责硬件与驱动差异的取证口径；17.3 负责调度策略，17.4 负责控制与能量统计。 | 保留；合并两条重复的 5.1 边界说明并补充全文小结。 |
| 17.3 OEM 调度、游戏模式与输入优先级 | 前半讲 sched_ext、MUSCHED、Binder 依赖传播和回退，后半沿触控到显示链路核对 Game Mode、InputDispatcher、刷新率与 OEM 增强。 | 负责线程获得 CPU 的策略和游戏输入延迟归因；Power HAL、schedutil 与能量结果交给 17.4，游戏渲染交给 18.12。 | 保留合并；新增双主线导语与全文小结，修复游戏渲染编号，删除失效的上游 raw 路径并转为可发布。 |
| 17.4 Power HAL、schedutil 与 Power Stats | 先按应用、Framework/HAL、内核和硬件建立控制链，再讲 Power Stats 对象、日志、公开监视器、能力分级与实验口径。 | 负责控制信号如何落到调频，以及能量/驻留结果怎样观测；17.3 负责调度策略本身，14.5 负责功耗工具选型。 | 从原 17.6 前移以紧跟调度主线；修正合并稿自指，补齐覆盖控制与统计两段的全文小结并转为可发布。 |
| 17.5 Media Performance Class 与设备能力分级 | 从 Android 17 等级变化进入读取兼容、CDD 阈值、运行时能力组合、产品分级、上报与认证证据。 | 负责应用消费公开能力声明；不把 MPC 当通用跑分，也不替代 17.2/17.4 的目标机实验。 | 原 17.4 顺延；通读确认结构与标题一致，完成发布状态。 |
| 17.6 Private Space 与应用锁的兼容性边界 | 先区分四类锁，再展开 Private Space 资料模型、普通 App/Launcher 边界、启动通知、URI、OEM 兼容和隐私观测。 | 负责用户资料隔离和访问入口；AAOS App Lock 只用于名称消歧，完整车载场景交给 17.7。 | 原 17.5 顺延；通读确认平台、OEM、应用内认证和车载特权组件边界清楚。 |
| 17.7 Android Auto 与 Android Automotive OS 性能优化 | 从两种平台与三类 UI 责任进入版本轴、模板、地图、媒体、网络、AAOS 资源/电源、VHAL 和端到端诊断。 | 负责车载垂直场景，复用前文的 SoC、功耗和 OEM 证据方法，不把 AAOS 接口外推到 Android Auto。 | 保留为全章收束；通读确认“执行位置 → 资源生命周期 → 可观测性”主线完整。 |

## 第 18 章逐篇结论

| 文章 | 标题契约与推进线 | 章节边界 | 处理结果 |
| --- | --- | --- | --- |
| 18.1 Android View 渲染管线与分析方法 | 先建立 Producer、Surface、layer 与 present 的统一模型，再展开 View/HWUI 主链和跨路径取证方法。 | 负责全章共同坐标与标准 View 路径；各专项文章只展开自己的 Producer 和载体。 | 保留合并；删除当前文章自指、Flutter 错链和重复视频入口。 |
| 18.2 Android 软件、离屏与混合渲染路径 | 从 CPU Raster 与 bitmap/offscreen 进入软件层上传、多 layer 和 CPU/GPU 混合成本。 | 负责非标准全硬件路径；18.3 负责 Surface 载体，18.4/18.5 负责图形 API。 | 保留合并；删除重复关联并补齐全文小结。 |
| 18.3 SurfaceView 与 TextureView 渲染管线 | 按独立 layer 与宿主纹理两种消费模型比较生命周期、同步、合成和选型。 | 负责输出载体；不重复上游 GLES/Vulkan 命令或下游 SF/HWC 机制。 | 保留合并；清理自指并补齐全文小结。 |
| 18.4 OpenGL ES、EGL 与 ANGLE | 从 EGL context/surface 与 GLES 提交进入驱动路径，再比较 ANGLE 的 GLES→Vulkan 翻译和证据。 | 负责 GLES/EGL/ANGLE；18.5 负责应用直接 Vulkan 与 HWUI Vulkan。 | 保留合并；删除重复关系和旧编号，重写全文收束。 |
| 18.5 Vulkan 原生管线与 HWUI 多队列 | 先追应用管理的 swapchain/queue，再对照框架管理的 HWUI Vulkan 与多队列同步。 | 负责两种 Vulkan 所有权模型；18.4 负责 GLES/ANGLE，18.6 负责 layer/buffer 交接。 | 保留合并；扩充全文结论以覆盖原生与 HWUI 两条主线。 |
| 18.6 SurfaceControl 与 HardwareBufferRenderer | 从 SurfaceControl transaction/layer 进入 HardwareBufferRenderer 的离屏生产、同步和消费边界。 | 负责 layer 控制与可共享 buffer；18.3 负责控件载体，2.8 负责 BufferQueue 通用机制。 | 保留合并；删除中途旧入口并补齐覆盖两段的全文结论。 |
| 18.7 Flutter 渲染管线：Engine、Impeller 与 Surface | 从 Dart/Engine/UI-Raster 线程进入 Impeller、Surface 提交和 Android 系统显示链路。 | 负责 Flutter 专有运行时；16 KB 插件兼容交给 4.5。 | 保留；删除偏离主题的详细 16 KB 插件教程，改为专项入口。 |
| 18.8 Jetpack Compose 渲染管线：Composition、Layout 与 RenderNode | 按重组、布局、绘制、RenderNode/HWUI 与帧诊断推进。 | 负责 Compose 到 Android 图形栈的边界；18.1 负责 View/HWUI 公共坐标。 | 保留；通读确认标题和结构一致。 |
| 18.9 Android 17 WebView 渲染管线 | 从 Chromium 多进程和 renderer/GPU process 进入 Surface、合成、首屏与诊断。 | 负责 WebView 内核渲染；应用优化实践交给 22.6，WebGPU 运行时差异由 18.14 收束。 | 保留；修复失效编号和错误跨章链接。 |
| 18.10 Android Camera 平台管线：HAL3、Buffer、ZSL 与显示 | 从 Camera2/HAL3 request 与 stream 进入 buffer、ZSL、预览显示和取证。 | 负责 Camera 平台数据面；18.11 负责视频播放/编解码，22.19 负责 CameraX 应用实践。 | 保留；修复相关章节编号，Camera buffer 特有的 16 KB/DMA-BUF 边界继续保留。 |
| 18.11 视频 Overlay、Media3 与专业编解码管线 | 依次解释显示 overlay、Media3/Codec2 播放链和专业编解码/APV，按显示到媒体栈再到 codec 能力推进。 | 负责视频与 codec 数据面；Camera 和 CameraX 分别交给 18.10、22.19。 | 保留三段合并；删除自指与重复关系，修正 Media3 误链到 CameraX。 |
| 18.12 Android 17 游戏引擎渲染链路 | 从引擎 game/render loop 与交换链进入 frame pacing、ADPF、显示提交，再划清小游戏、云游戏、AR/XR。 | 负责游戏 Producer 与显示节奏；XR runtime 深入交给 18.13。 | 保留；清理重复关系和误放的 EyeDropper 关联。 |
| 18.13 Android 17 / Android XR 空间 UI 与环境资产渲染性能 | 先区分 2D panel、空间内容、OpenXR 和 Projected，再进入资产、视点、runtime cadence、工具与功耗。 | 负责应用与 XR runtime/compositor 的责任边界；不把普通 SurfaceFrame 当最终头显 present。 | 原 18.14 前移；补齐全文小结、关联章节和发布状态。 |
| 18.14 Android 17 Jetpack WebGPU 渲染与计算管线 | 从 Dawn/AndroidX 架构进入能力查询、可见渲染、compute、线程、性能、调试和 WebView 边界。 | 负责 Jetpack WebGPU；GLES/Vulkan/Surface 基础分别由 18.3—18.6 负责，WebView runtime 由 18.9 负责。 | 原 18.15 前移；补齐全文小结、关联章节和发布状态。 |

## 第 22 章逐篇结论

| 文章 | 标题契约与推进线 | 章节边界 | 处理结果 |
| --- | --- | --- | --- |
| 22.1 View 布局与自定义绘制优化 | 从 measure/layout/draw 基础进入自定义 View、Canvas、缓存与性能验收。 | 负责 View 侧布局绘制实践；Compose 布局与 Canvas 分别由 22.14、22.8 展开。 | 保留。 |
| 22.2 RecyclerView 与 Compose LazyList 性能 | 先建立两类虚拟列表的成本模型，再进入复用、预取、稳定身份、基准和同版本开关实验。 | 负责列表实践与 Lazy 预取；22.3 负责编译器/Modifier 诊断。 | 接收原 2.18 的依赖解析、同版本 A/B、升级与回退步骤；删除重复稿并补齐断裂编号。 |
| 22.3 Compose 性能、Compiler 与 Modifier.Node 诊断 | 从状态与阶段基线进入 Compiler 指标、运行时证据和 Modifier.Node 迁移。 | 负责 Compose 通用诊断；列表机制交给 22.2，互操作生命周期交给 22.11。 | 写明相邻专题边界，修正编号和自链，补充全文小结。 |
| 22.4 View、Compose 动画与共享元素性能 | 按 View 动画 → Compose 动画 → SharedTransition 逐层推进。 | 负责动画 API 与共享元素实践；运行时图形效果交给 22.8。 | 修复两处编号、缺失首节、自链和分段结论标题。 |
| 22.5 图片加载、Bitmap 解码与 RenderNode | 从请求/缓存/生命周期进入解码、像素存储、上传与绘制缓存。 | 负责图片端到端应用实践；10.4 负责图形内存统计，2.x/18.x 负责系统管线。 | 删除合并段自指，区分局部小结并补充全文收束。 |
| 22.6 WebView 性能优化实战 | 从初始化与首屏进入网络缓存、JS Bridge、显示、renderer 生命周期与诊断。 | 负责应用接入和优化；18.9 负责 Chromium/WebView 内核渲染管线。 | 修正错误的机制章编号，补充全文小结。 |
| 22.7 帧率监控与线上卡顿治理 | 从帧信号采集进入堆栈采样、归因、告警、回放与治理闭环。 | 负责线上监控；13.x 负责 Perfetto 工具，15.3 负责通用指标体系。 | 保留；发布阶段转为可发布。 |
| 22.8 Runtime 图形效果与 Compose Canvas | 先讲 RenderEffect/AGSL，再讲 Canvas 状态读取、缓存、图层和测量。 | 负责应用图形效果与自绘；22.16 负责底层管线创建和缓存。 | 把分段结论改为 Canvas 小结，补充全文收束。 |
| 22.9 Fragment、Predictive Back 与 Navigation Compose 页面切换 | 按 Fragment 切换 → Predictive Back → Navigation Compose 推进。 | 负责 App 导航与转场实践；3.3 负责系统返回手势路由。 | 修正三段合并后的结论标题、编号和自链，补充全文小结。 |
| 22.10 自适应布局、桌面窗口与多形态设备性能 | 从窗口尺寸类别与决策入口进入折叠姿态、resize、多窗口、多显示和分层验收。 | 负责应用自适应布局；2.10/2.13/2.15 负责系统窗口与显示机制。 | 清除指向已合并原 2.18 的失效来源，补充全文小结。 |
| 22.11 Compose First 与 View/Compose 互操作性能实战 | 从 AndroidView/ComposeView 对象模型进入复用、生命周期、滚动、迁移和测试门槛。 | 负责完整互操作生命周期；Compose 编译诊断、刷新率和 Surface 专题只保留边界。 | 写明三类相邻专题边界，删除相关章节中的同篇自链并补齐当前入口。 |
| 22.12 自适应刷新率与帧率策略实战 | 从内容/应用/显示三种帧率进入 View、Window、Surface 请求、系统选择和跨设备验收。 | 负责应用 ARR 策略；2.2 负责系统模式选择机制。 | 保留；统一全文小结标题。 |
| 22.13 App Widget 更新性能：RemoteViews IPC 与 Glance 渲染 | 按 provider → system_server → host 三段模型进入更新语义、调度、图像、Glance 和测量。 | 负责桌面 Widget 跨进程渲染；不把 Glance 等同于 Compose UI 管线。 | 补充跨三进程的全文小结并顺延检查清单编号。 |
| 22.14 Compose 布局、测量与文字渲染 | 先解释约束/测量/放置/Subcompose，再进入字体整形、段落缓存与绘制。 | 负责布局和文本的运行时成本；22.3 负责组合稳定性诊断，22.8 负责 Canvas。 | 删除同篇自链，按布局/文本/旧版本重组资料，并补充覆盖两部分的全文小结。 |
| 22.15 Compose Snapshot、状态一致性与并发 | 从多版本记录、apply/冲突进入依赖观察、跨线程、Recomposer、成本与测试。 | 负责 Runtime 状态一致性；22.3 负责编译器，22.14 负责布局。 | 补齐关联章节和全文小结，顺延后续编号。 |
| 22.16 Vulkan 管线缓存与 Impeller 着色器编译实战 | 先区分 HWUI/原生 Vulkan 管线所有权，再把同一模型映射到 Impeller shader、PSO、预热和显示取证。 | 负责应用/引擎的管线键、调度、缓存和降级；18.5/18.7 负责机制架构。 | 扩充标题，修复“十 → 十三”的编号断层，为 Vulkan、Impeller 和全文分别补齐收束。 |
| 22.17 SurfaceView 与 TextureView：渲染路径、选型与排障 | 用最小拓扑模型进入延迟/功耗/内存、生命周期、场景选型、Compose 包装和反向追帧。 | 负责应用选型与排障；18.3 负责完整源码管线。 | 在开头明确与 18.3 的边界，补齐关联并统一全文小结标题。 |
| 22.18 Media3 视频播放：解码、帧时序与渲染 | 从 renderer/codec/release timestamp 进入 Surface、效果、HDR/DRM、tunnel、帧率、首帧和 Perfetto。 | 负责 Media3 应用侧播放实践；18.11 负责 Codec2/overlay 数据面。 | 把落在源码列表之后的全文小结移到正文结束、相关章节之前。 |
| 22.19 CameraX：UseCase、Camera2 映射与性能 | 从版本与会话配置进入 Preview、Analysis、Capture/ZSL、Video、Extensions、热稳定和工具选择。 | 负责 CameraX 应用配置；18.10 负责 HAL3/Buffer/ZSL 平台管线，14.14 负责工具。 | 修正把平台 Camera 误指到 18.9 WebView 的关联，补充全文小结并整理尾部编号。 |
| 22.20 Android 17 EyeDropper：系统取色、截图边界与跨设备同步 | 从公开 Intent 契约进入 AOSP 特权实现、截图与安全边界，再讲接入、trace 和应用自建跨设备协议。 | 负责系统能力的应用接入与性能实践；不属于第 18 章的持续渲染 Producer 管线。 | 从原 18.13 移入本章；重命名并更新章节关系、README 与 SUMMARY。 |

章内统一重编号的目标顺序为：View 布局/绘制 → RecyclerView/Lazy 列表 → Compose 编译诊断 → Compose 布局/文本 → Snapshot/并发 → View/Compose 互操作 → 动画/共享元素 → Canvas/图形效果 → 图片 → 帧监控 → 导航 → 自适应布局 → 自适应刷新率 → SurfaceView/TextureView → Vulkan/Impeller → WebView → Media3 → CameraX → App Widget → EyeDropper。该顺序随全书统一重编号一次落地。

## 第 19 章逐篇结论

| 文章 | 标题契约与推进线 | 章节边界 | 处理结果 |
| --- | --- | --- | --- |
| 19.1 APM 全景、Firebase 与商业平台选型 | 从信号、证据和采集架构建立选型维度，再分别进入 Firebase 与商业平台，最后落到 PoC、成本和迁移合同。 | 负责全章导航与平台选择；19.2—19.4 展开具体工具，19.8—19.12 展开专项采集与端侧架构。 | 保留三段合并；确认总论、具体平台和选型闭环属于同一标题。 |
| 19.2 Matrix、btrace 与 Tracing SDK | 先用 Trace API 建立事件语义，再进入 btrace 字节码采集和 Matrix 插件架构，按抽象到实现推进。 | 负责代码路径与框架型 trace/APM；13.x 负责 Perfetto 通用分析，19.12 负责端侧平台架构。 | 保留三段合并；确认工具间层次清楚，状态保持可发布。 |
| 19.3 KOOM 与 LeakCanary 内存诊断 | 从 LeakCanary 的对象监视、dump 和引用链进入 KOOM 的线上 Java/Native/线程资源监控。 | 负责内存诊断工具；4.x/10.x 负责平台内存机制，19.9 负责 crash/ANR 现场。 | 保留合并；开发期引用链与线上资源监控形成递进。 |
| 19.4 DoKit 调试工具与 Measure APM 平台 | 先说明 DoKit 的调试现场、兼容与 Release 隔离，再进入 Measure 的端侧采集、会话、平台、自托管和选型。 | DoKit 负责 Debug/QA 复现，Measure 负责生产 APM；两者只共享诊断信号，不共享部署责任。 | 修正原题把 Measure 误归为“开发期性能工具”的问题；重写全文导语、Measure 分段标题和过渡，并同步 README/SUMMARY。 |
| 19.5 历史开源 APM：BlockCanary、ArgusAPM、AndroidGodEye、Collie 与 Rabbit | 逐项提取旧项目仍有价值的机制与已失效口径，再横向比较并收束为最小 SDK。 | 负责历史方案和迁移判断；当前可用工具由 19.2—19.4 负责。 | 保留；确认“历史复盘 → 当前替代 → 架构提炼”闭环成立。 |
| 19.6 Jetpack Benchmark：Microbenchmark、Macrobenchmark 与测量协议 | 从两类 Benchmark 的适用边界进入工程结构、指标、环境、CI、线上回放与 Baseline Profile 验证。 | 负责可重复测量协议；19.7 负责人工/设备实验室工具，21.4 负责 Baseline Profile 完整工程实践。 | 保留；确认 Baseline Profile 是测量闭环的一部分，并已把完整接入留给专项文章。 |
| 19.7 实验室测试工具与设备 Benchmark | 先讲 PerfDog/SoloPi/Emmagee 的场景复现和指标证据，再讲设备分数、能力档位与线上设备字典。 | 负责实验室现场和跨设备基线；19.6 负责应用内自动化测量协议。 | 保留合并；两部分共享设备、温度、版本、轮次和判废规则；修正发布阶段值。 |
| 19.8 网络 APM 底层捕获原理 | 从 OkHttp 事件时间线与请求语义进入指标公式、重试、其他网络栈、Native/eBPF 边界和隐私控制。 | 负责网络采集器实现；12.x 负责网络/TLS/DNS 机制，24.x 负责应用网络实践。 | 保留；确认“采集路径 → 指标模型 → 覆盖缺口 → 成本隐私”顺序完整。 |
| 19.9 崩溃与 ANR 捕获机制 | 按 Java crash、native crash、ANR、资源耗尽、现场快照、多 SDK 冲突和平台补充能力推进。 | 负责故障采集与证据强度；9.x 负责 ANR 机制/诊断，20.x 负责稳定性工程。 | 保留；各类故障按可执行回调和证据边界分开，没有把退出原因误当根因。 |
| 19.10 耗电与发热监控 (Battery & Thermal) | 从证据等级进入 WakeLock、Alarm、定位/扫描/网络/CPU、电池、Thermal、Vitals 与上报边界。 | 负责电量和热状态采集器；11.x 负责功耗机制与优化，14.5 负责分析工具。 | 保留；请求、持有状态、系统统计和热保护动作的口径分离清楚。 |
| 19.11 混合栈与跨平台 APM (WebView / Flutter) | 从 WebView 加载时钟、白屏和 renderer 进入安全 Bridge，再转向 Flutter 帧语义，最终用 Session Timeline 统一关联。 | 负责 WebView/Flutter 跨运行时观测；各运行时保留原生语义，只共享会话和关联键。 | 保留；确认两类运行时以端到端会话为共同主线，不需要拆篇。 |
| 19.12 千万级 DAU 的 APM 端侧架构 | 从有界准入、单写者和多进程进入 mmap 恢复、编码、动态指令、持久上传、断路器、自监控和隐私。 | 负责把前述采集器组合成可发布 SDK；具体信号机制回到 19.8—19.11。 | 保留；作为全章架构收束，确认成本、可靠性、权限和运维边界完整。 |

## 第 20 章逐篇结论

| 文章 | 标题契约与推进线 | 章节边界 | 处理结果 |
| --- | --- | --- | --- |
| 20.1 应用稳定性度量、聚合与归因 | 按故障类型/恢复边界 → 分母/窗口/SLO → 指纹/聚合/责任归因推进，承担全章度量总论。 | 只定义事件、指标和 issue 模型；20.2—20.13 负责具体故障与工具。 | 保留三段合并；删除自指、重复 Native/OOM 导航和两条失效来源，区分分段核查入口并补全文小结。 |
| 20.2 Java Crash、异常架构与线程堆栈分析 | 从 Crash 恢复架构/SafeMode 进入未捕获异常与终止链，再展开线程快照和锁等待证据。 | 负责 Java fatal 边界与下次启动恢复；Native/ANR/OOM 只留证据交接。 | 保留三段合并；重命名首个 H2，清理自指与重复 Native 入口，修复 7/8 编号并补全文小结。 |
| 20.3 Native Crash、堆栈回溯与符号化 | 先保留 signal/tombstone 现场与采集边界，再按 unwind 和 Build ID 符号化恢复准确栈。 | 负责 Native Crash 证据链；MTE 、Hook 和 DCL 交给 20.11—20.13。 | 保留两段合并；扩充首段标题，去掉自指，分开两组源码核查入口并补全文小结。 |
| 20.4 ANR 治理策略 | 按修复优先级、系统预警、现场证据、回归与发布门禁推进。 | 第 9 章负责判定与诊断机制；本文只负责 App 侧治理。 | 保留；删除导语中完全重复的 9.1 引用。 |
| 20.5 OOM、进程资源治理与 WebView Renderer 恢复 | 前半按 Java/Native/线程/FD/地址空间分类和降级，后半按 Renderer gone 重建恢复。 | 负责 OOM 总分类和 WebView 进程边界；20.6—20.8 展开具体资源。 | 标题增加“进程资源”；删除两条失效来源，改写泛化“扩展”标题，区分 Renderer 小结与全文小结。 |
| 20.6 Native 内存泄漏的线上分层监控 | 从 Android 17 MemoryLimiter 与内存口径进入 mallinfo/RSS/PSS、Hook/heapprofd/安全工具，最后落到 L0—L3 分层。 | 负责证明 Native 增长与 owner 生命周期；20.11 负责内存安全错误。 | 从原 20.13 前移；标题从工具列表改为“线上分层监控”，补全文小结。 |
| 20.7 FD 耗尽监控与故障排查 | 从数量/编号/对象/owner 进入限额、代次、fdsan/hook、告警、恢复与验证。 | 只负责 FD；线程与 Native 内存分别交给 20.8/20.6。 | 从原 20.8 前移；删除两条不存在的旧来源，修正跨篇编号并补全文小结。 |
| 20.8 线程与协程泄漏治理 | 前半管 Linux task/Java/pthread/pool，后半管 Scope/Job/Flow/Dispatcher/Lifecycle，两条线用 owner 统一。 | 线程数与 Job 数不一一对应；FD 与 OOM 只作资源后果证据。 | 从原 20.12 前移；修正 15—17 编号和两处自指，区分首段收束与全文小结。 |
| 20.9 Binder IPC 故障判断与性能诊断 | 从传输失败位置和异常映射进入 Parcel 预算、死亡/冻结、线程池、Perfetto 与指标。 | 负责 IPC 传输/执行/业务结果；ANR 的系统判定交给 9.x/20.4。 | 从原 20.10 前移；通读确认十二段层层下钻，补全文小结。 |
| 20.10 Android 17 Keystore 密钥配额与登录恢复 | 从 UID 配额与错误分类进入 alias 生命周期、盘点回收、多进程和发布测试。 | 负责密钥数量和登录恢复；8.5 负责 Keystore/Biometric 性能链。 | 从原 20.9 后移；通读确认配额、认证与失效分类清楚，补全文小结。 |
| 20.11 MTE 与 GWP-ASan Native 内存安全检测 | 先展开 MTE 覆盖、模式、生效路径、报告和发布，再进入 GWP-ASan 抽样与两者分工。 | 负责 UAF/越界检测，不承担普通泄漏和业务 owner 判定。 | 从原 20.6 后移；删除两条不存在的旧来源，其余结构与标题一致。 |
| 20.12 Native Hook 技术选型与实现 | 先按命中层选择 PLT/GOT、Inline 或 Trap，再展开 linker/指令/信号/ABI 约束与生命周期。 | 负责 Hook 框架机制与风险；FD/内存只是两类使用场景。 | 从原 20.11 后移；修正 FD 编号，补充 section 元数据和全文小结。 |
| 20.13 Native 动态库安全发布、装载与回滚 | 从 Android 17 DCL 只读边界进入可信发布状态机、ELF/依赖、多进程回滚和发布验证。 | 负责运行时 `.so` 发布事务；1.22/4.5 负责 linker 与页兼容通用机制。 | 从原 20.7 后移；通读确认不与 Hook 合并，补全文小结。 |
| 20.14 第三方 SDK 性能影响评估与治理实战 | 从制品台账和 A/B 证据进入启动、内存、后台、稳定性、体积、准入和退出协议。 | 负责跨类型第三方能力治理；具体故障证据回到本章前文。 | 保留为全章收束；通读确认标题覆盖全部正文，补全文小结。 |

## 第 21 章逐篇结论

| 文章 | 标题契约与推进线 | 章节边界 | 处理结果 |
| --- | --- | --- | --- |
| 21.1 App 启动路径、监控与度量 | 前半沿进程创建、Provider/Application、Activity 和首帧建立启动路径，后半定义线上指标、`ApplicationStartInfo`、聚合和归因。 | 负责全章共同的时间边界与证据合同；后续文章分别治理具体启动成本。 | 保留两段合并；删除自指，修正 Perfetto 6.3/6.4 编号，确认复盘模板和全文小结处于最终收束。 |
| 21.2 启动任务编排、延迟初始化与并发调度 | 依次建立 DAG/失败协议、首帧后与首次使用触发、线程池/协程资源边界。 | 负责把任务的依赖、时机和执行资源统一建模；Provider、DI 和具体 UI 成本交给后文。 | 保留三段合并；移除两处当前文章自指，完成发布状态并补全文小结。 |
| 21.3 ContentProvider 与多进程启动治理 | 前半从 Provider 安装、Manifest、显式初始化和安全进入多进程/Direct Boot，后半展开进程拓扑、Binder ready、共享状态和死亡恢复。 | 负责 `Application.onCreate()` 之前的自动组件及进程边界；任务图细节交给 21.2。 | 保留两段合并；扩写最终小结，使 Provider 与多进程两条主线共同收束。 |
| 21.4 Baseline、Startup 与 Cloud Profile 编译优化 | 从规则生成、打包和 Macrobenchmark 进入 Cloud Profile、DM、ART Service、dexopt 与分发验证。 | 负责应用 Profile 从构建到设备编译的完整链路；业务初始化和渲染成本只作边界。 | 保留两段合并；把后半篇自指改为前半篇，补全文小结。 |
| 21.5 Splash Screen 与感知启动速度 | 从系统 starting surface 和 AndroidX 接入进入保持/退出、旧方案迁移、内容交接和 TTID/TTFD。 | 负责系统画面到应用首帧的视觉交接；不把动画或骨架冒充执行时间优化。 | 保留；确认系统机制、应用接入和体验度量顺序成立，补全文小结。 |
| 21.6 Privacy Sandbox 退场与广告 SDK 启动治理 | 先给出 Android 17 退场结论与 14—16 遗留边界，再转入普通广告 SDK 的清单、状态机、Provider、失败和迁移。 | 负责广告平台版本迁移与启动专项；通用任务、Provider 和指标分别回到 21.2、21.3、21.1。 | 保留；标题完整覆盖“平台退场 + 广告 SDK 治理”，现有小结成立。 |
| 21.7 ART GC 启动期开销与分配治理 | 从 HeapTaskDaemon/post-fork 机制进入 Perfetto/分配归因、安全治理、禁止方案和实验。 | 负责启动窗口内 GC 与对象分配；23.4 负责一般 Java Heap/Compose 分配，5.8 负责缓存局部性。 | 原标题“GC 抑制”容易把内部 Hook 当目标，改为“启动期开销与分配治理”；删除重复关系并补全文小结。 |
| 21.8 依赖注入框架性能：Dagger/Hilt/Koin 启动开销与优化 | 从 Dagger/Hilt 创建与 eager/lazy 语义进入 Koin 运行时、Profile/KSP、scope、测量与优化。 | 负责 DI 容器和对象图何时进入启动路径；不替代业务构造、I/O 和内存专项。 | 保留；清理重复 Profile 导航，更新 21.7 标题/路径并补全文小结。 |
| 21.9 Compose 首次组合开销与启动性能 | 沿 `setContent`、初始组合、布局绘制进入 Profile、首屏裁剪、多窗口/互操作和 TTID/TTFD 归因。 | 负责 Compose 首次组合；18.8 负责完整渲染管线，22.x 负责运行期 Compose 专项。 | 保留；修正 related chapter 18.6 为 18.8，完成发布状态并补全文小结。 |
| 原 21.10 缓存优化实战 | 通用 LRU/SLRU、CPU 数据布局、DEX 局部性和 PMU 工具并非启动章节的单一专题。 | 与 5.8 大量重叠，只有业务缓存扫描污染、冷热分段和加载去重具有独立增量。 | 把独有内容融合进 5.8 后删除重复文章；全书正文由 276 篇降为 275 篇。 |
| 原 21.11 设备分级性能策略实战 | 覆盖启动、渲染、内存、媒体、网络和动态压力，不以启动为主线。 | 属于跨场景策略方法论，而非启动专项。 | 移至 15.8；修正章节关系并补全文小结。 |
