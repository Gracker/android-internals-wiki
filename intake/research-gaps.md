# Research Gaps - Task 9 Deep Technical Review

## Created: 2026-06-03 07:20

### Chapter: Measure (19.09)
**Gap ID**: RG-MEASURE-001
**Priority**: High
**Type**: Integration Capability
**Description**: Missing documentation on Measure integration with Perfetto/FrameMetrics for system-level rendering analysis
**Evidence**: Measure focuses on SDK-level events but lacks guidance on correlating with system-level rendering traces
**Action Required**: Research and document integration points between Measure session timelines and Perfetto traces

### Chapter: Measure (19.09) 
**Gap ID**: RG-MEASURE-002
**Priority**: High  
**Type**: External Systems
**Description**: Missing documentation on Measure integration with Android Vitals crash aggregation
**Evidence**: No guidance on how Measure crash data integrates with system-level Vitals reporting
**Action Required**: Document compatibility and data flow between Measure and Android Vitals

### Chapter: 崩溃与 ANR 捕获机制 (19.24)
**Gap ID**: RG-ANR-001
**Priority**: Medium
**Type**: Enterprise Limitations
**Description**: Missing documentation on ProfilingManager rate limiter and privacy compliance in enterprise environments
**Evidence**: ProfilingManager usage in enterprise settings with privacy requirements is not covered
**Action Required**: Document rate limiting policies, compliance considerations, and enterprise deployment guidelines

### Chapter: TextureView 合成链路 (18.7)
**Gap ID**: RG-TV-001
**Priority**: High
**Type**: Backend Performance
**Description**: Missing Metal/Vulkan backend performance comparison for TextureView rendering
**Evidence**: Section focuses on OpenGL ES backend but doesn't cover modern graphics APIs
**Action Required**: Research and document performance characteristics and optimization strategies for Metal/Vulkan backends

### Chapter: TextureView 合成链路 (18.7)
**Gap ID**: RG-TV-002
**Priority**: Medium
**Type**: Engine Integration
**Description**: Missing guidance on TextureView usage in game engines (Unity/Unreal)
**Evidence**: No special handling or optimization guidance for game engine contexts
**Action Required**: Document TextureView integration patterns and performance considerations for major game engines

### Chapter: TextureView 合成链路 (18.7)
**Gap ID**: RG-TV-003
**Priority**: High
**Type**: Form Factor Adaptation
**Description**: Missing TextureView behavior on foldable/irregular screen displays
**Evidence**: No considerations for foldable screens, notched displays, or other form factors
**Action Required**: Research and document TextureView behavior and optimization on modern display form factors

## [2026-06-04] 5.11 端侧 AI 推理性能：NPU/GPU 加速与 TFLite 管线 — 知识盲区

### 盲区描述
Android 17 的 NPU feature、LiteRT NPU delegate / CompiledModel、AICore、NNAPI/NN HAL 和厂商 QNN/Neuron 路径在章节中混成一条源码链,且部分源码路径无法在 Android 17/AOSP 或官方仓库中闭环。当前需要把“平台 API 可发布事实”和“厂商 runtime / Google AI Edge 生态能力”拆开验证。

### 重要程度
高

### 建议研究方向
- 以 Android 17 API reference / release notes 为准,确认 `PackageManager.FEATURE_NEURAL_PROCESSING_UNIT`、常量值 `android.hardware.npu`、targetSdkVersion 37 直接访问 NPU 的 manifest 要求。
- 分别核对 LiteRT upstream source、AOSP android-17.0.0_r1、Google AI Edge 文档和 AICore 文档,标出哪些路径是 AOSP、哪些是 Google/AndroidX/upstream、哪些只是厂商 SDK 日志。
- 复核 QNN / FastVLM / CompiledModel benchmark 数字的设备、模型、delegate/runtime 版本、测试条件和官方来源;无法闭环的数字不要写入发布稿。

### 关联章节
5.11, 5.16, 5.13, 25.11

## [2026-06-04] 6.3 I/O 调度与性能 — Android 16/17 I/O 栈版本证据

### 盲区描述
`Android 16/17 的 I/O 栈加速` 小节把 io_uring FUSE、dm-verity multi-buffer hashing、Android 17 cgroup v2 io controller / 1000:10 权重写成正文结论，但当前正文仍有 `[待验证]` 标记，且本轮未找到可用于 Android 17 正文锚定的 `android-17.0.0_r1` 标签。

### 重要程度
高

### 建议研究方向
- 用 AOSP `android-16.0.0_r1`/`android-16.0.0_r4` 复核 storage / vold / FUSE 路径中是否存在 io_uring 集成、默认启用条件和 Perfetto 可观察点。
- 用 Android common kernel 6.12 或 Android 16 GKI tag 复核 dm-verity multi-buffer hashing 的实际 commit、配置条件和 Android 平台版本映射，避免把 generic kernel 优化写成 Android 16 平台保证。
- 等 `android-17.0.0_r1` 或官方 Android 17 文档可用后，再确认 task_profiles / cgroups 配置是否移除 blkio v1、是否存在 1000:10 io.weight 默认值；只有 main/master 资料时保持待验证或删除正文结论。

### 关联章节
6.3, 6.4, 25.6
