---
tags:
  - android
  - performance
  - paper
  - rendering
  - audio
---

# 1.16 Audio Pipeline 延迟与性能

<!-- outline-start -->
## 要点

### 🔹 锚点 1：为什么 Audio Pipeline 性能值得关注
- 音频延迟对用户体验的直接影响（游戏、音乐、VoIP、VR/AR）
- AudioFlinger 与 SurfaceFlinger 的对称关系：一个管画面合成，一个管声音混音
- 人类听觉感知阈值：>20ms 可感知延迟，专业音频 <10ms
- Android 音频延迟的历史演进：从 100ms+ 到平均 <40ms

### 🔹 锚点 2：Audio Pipeline 架构全景
- App → AudioTrack/AAudio → AudioFlinger → Audio HAL → DSP/Codec → Speaker
- AudioFlinger 内部架构：Normal Mixer vs FAST Mixer 路径
- AudioPolicyService：路由决策、设备选择、音量管理
- Audio HAL 演进：HIDL → AIDL（Android 14+）
- MMAP 模式（Android 8.1+）：绕过 AudioFlinger 直接访问硬件缓冲区

### 🔹 锚点 3：延迟分解与量化
- 输出延迟（output latency）：App 写入 → 声音输出
- 输入延迟（input latency）：声音采集 → App 读取
- 往返延迟（round-trip latency）：输入 + 处理 + 输出
- 缓冲区大小与采样率对延迟的影响
- FAST Mixer 路径的延迟优势：如何进入 FAST 轨道

### 🔹 锚点 4：AAudio vs OpenSL ES vs Java AudioTrack API
- AAudio（Android 8.0+）：低延迟 C API，推荐用于游戏和实时音频
- OpenSL ES：已废弃但仍广泛使用
- Java AudioTrack：最上层 API，延迟最高
- Oboe 库：跨版本兼容封装，Google 推荐
- 各 API 在不同 Android 版本上的延迟表现对比

### 🔹 锚点 5：AudioFlinger 内部机制与性能
- FAST Mixer 线程：低延迟路径的调度优先级与锁策略
- Normal Mixer：多轨混音、重采样、音量调节
- BufferQueue 管理：缓冲区分配与回收策略
- 音频焦点（Audio Focus）对性能的影响
- AudioFlinger 的 Binder IPC 开销

### 🔹 锚点 6：在 Perfetto 中的表现
- `audio.*` atrace 标签：AudioTrack/AudioFlinger 活动
- 音频线程的 CPU 调度状态：SCHED_FIFO 实时调度
- 缓冲区水位线（underrun/overrun）在 Trace 中的识别
- 音频功耗分析：持续 CPU 唤醒对功耗的影响

### 🔹 锚点 7：Android 17 Audio 性能变更
- Background Audio Hardening：后台音频交互的严格限制
- 音频焦点请求在无效生命周期状态下的失败处理
- AIDL Audio HAL 全面过渡的性能影响
- reduced-wakelock AlarmManager 回调对音频调度的影响

## 扩展

### 🔸 扩展点 1：蓝牙音频延迟分析
- A2DP vs aptX vs LDAC 延迟对比
- Bluetooth Audio HAL 的额外缓冲区开销
- 空间音频 + 头部追踪对延迟的要求（Audio HAL 7.1）

### 🔸 扩展点 2：游戏音频性能最佳实践
- AAudio 低延迟配置清单
- Oboe 库集成与性能优化
- 音频线程优先级设置与避坑

<!-- outline-end -->

> 本节内容待加工。
