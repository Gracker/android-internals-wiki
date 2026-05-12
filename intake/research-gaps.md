# 知识盲区记录

## 2026-05-12 新增盲区

### Android 16 云编译与 SDM 机制
- **盲区描述**: Android 16 的云端编译（Cloud Compilation）和 SDM 机制缺乏一手 AOSP 源码证据
- **涉及章节**: 1.9 Package Manager Service
- **验证状态**: 需要查阅 AOSP android-16.0.0_r1 中相关实现
- **建议行动**: 联系 AOSP 团队获取官方文档或源码分析

### 厂商定制的安装优化路径
- **盲区描述**: 主流手机厂商的安装优化路径（如 vivo 的 Turbo、小米的 HyperOS）缺乏实机测试数据
- **涉及章节**: 1.9 Package Manager Service
- **验证状态**: 需要在不同厂商设备上进行实际测试
- **建议行动**: 收集各厂商设备安装过程的 Perfetto 数据

### 厂商游戏模式输入优先级
- **盲区描述**: 厂商定制的游戏模式中输入优先级提升机制缺乏一手证据
- **涉及章节**: 1.10 ContentProvider 与 2.3 输入事件拦截
- **验证状态**: 当前描述基于推测，缺乏厂商源码验证
- **建议行动**: 获取厂商 Input 源码或进行实际性能测试

### 厂商防误触实现
- **盲区描述**: 各厂商防误触机制的具体实现位置和方案差异缺乏实机测试数据
- **涉及章节**: 2.3 输入事件拦截与安全机制
- **验证状态**: 需要在不同厂商设备上验证防误触实现
- **建议行动**: 测试各厂商设备在边缘触控和口袋防误触的表现

## [2026-05-12] 8.8 Android 多媒体管线性能 — Codec2 / tunneled playback / Media3 ABR

### 盲区描述
章节需要补齐 OMX → Codec2 的媒体框架演进、tunneled playback 在 OMX 与 Codec2 下的实现差异，以及 Media3 ABR “主动预测 / 亚 100ms 决策”是否有官方 release note、commit 或 benchmark 支撑。

### 重要程度
高

### 建议研究方向
- 核对 `frameworks/av/media/codec2/`、`frameworks/av/media/libstagefright/`、Codec2 component 配置与 tunneled playback 相关源码锚点。
- 核对 AndroidX Media3 release notes、`AdaptiveTrackSelection` / `BandwidthMeter` 变更与可复现实验数据。
- 整理 SurfaceView / TextureView / tunneled sideband 三路径在 Android 10-17 的版本边界。

### 关联章节
8.8、2.6、2.15、2.16、14.9

## [2026-05-13] 7.8 RecyclerView 列表滑动性能深度优化 — Android 17 DeliQueue 与 MessageQueue 版本口径

### 盲区描述
章节把 Android 17 DeliQueue、Treiber Stack、`targetSdk >= 37` 生效条件以及 missed frames / 首帧 P95 收益写成确定结论，但当前 sources 未给出 AOSP 源码路径、官方 behavior changes、commit 或 benchmark 条件。

### 重要程度
高

### 建议研究方向
- 核对 Android 17 `android.os.MessageQueue` / native looper / DeliQueue 相关源码路径与 targetSdk gating。
- 查找 Google 官方 Android 17 behavior changes、I/O presentation 或 benchmark，确认 4%、7.7%、9.1% 三组数字的设备、样本和统计口径。
- 复核 RecyclerView GapWorker 通过 `postFromTraversal()` → `recyclerView.post(this)` 投递到主线程队列后，DeliQueue 是否会实际改变预取 deadline 命中率。

### 关联章节
7.8、5.10、16.5


## [2026-05-13] 8.6 Kotlin Coroutine 性能实践 — 知识盲区

### 盲区描述
ADPF hint session 与 Kotlin 协程线程迁移的工程化边界缺少一手验证。

### 重要程度
高

### 建议研究方向
- 复核 PerformanceHintManager.Session 文档、setThreads 行为与 Android 15/16 flagged API 状态
- 用 DefaultDispatcher/limitedParallelism/固定 Executor 三种模型做 TID 迁移 trace
- 评估 reportActualWorkDuration 调用频率和 IPC 开销的实测数据

### 关联章节
5.9、8.6

## [2026-05-13] 14.3 内存分析工具 — 知识盲区

### 盲区描述
MTE ASYMM 在 Android App memtagMode=async 下是否自动启用缺少源码闭环。

### 重要程度
高

### 建议研究方向
- 定位 bionic/scudo/kernel 中 memtag async/asymm 选择路径
- 区分 Arm 硬件 mte3 能力、/sys mte_tcf_preferred、Zygote runtimeFlags 和 manifest memtagMode
- 补充 Pixel 8/9 或 Android 15/16 实机验证

### 关联章节
4.3、14.3
