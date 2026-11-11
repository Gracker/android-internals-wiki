---
title: 音频链路（Audio Pipeline）延迟与性能
chapter: '1.20'
section: '1.20'
status: finalized
applicable_versions: Android 8.0 (API 26) - Android 17 (API 37)
last_verified: '2026-11-11'
last_verified_against: AOSP android-17.0.0_r1 + Android 17 API 37 official documentation; FAST admission and downmix TODO, AAudio/MMAP and offload API availability, AudioTrack flush/provenance, background hardening default/throw behavior, and tee sink privacy boundaries checked 2026-11-11
confidence: high
sources:
- type: official
  path: https://source.android.com/docs/core/audio
- type: official
  path: https://source.android.com/docs/core/audio/latency/design
- type: official
  path: https://source.android.com/docs/core/audio/latency/measurements
- type: official
  path: https://source.android.com/docs/core/audio/aaudio
- type: official
  path: https://source.android.com/docs/core/audio/debugging
- type: official
  path: https://source.android.com/docs/core/audio/aidl-hidl-comp
- type: official
  path: https://developer.android.com/ndk/guides/audio/audio-latency
- type: official
  path: https://developer.android.com/ndk/guides/audio/aaudio/aaudio
- type: official
  path: https://developer.android.com/about/versions/17/changes/bg-audio
- type: official
  path: https://developer.android.com/about/versions/17/features
- type: official
  path: https://developer.android.com/reference/android/media/AudioTrack
- type: official
  path: https://perfetto.dev/docs/reference/perfetto-cli
- type: aosp
  path: frameworks/av/services/audioflinger/Threads.cpp @ android-17.0.0_r1
- type: aosp
  path: frameworks/av/services/audioflinger/fastpath/FastMixerState.cpp @ android-17.0.0_r1
- type: aosp
  path: frameworks/av/services/audioflinger/fastpath/FastMixerState.h @ android-17.0.0_r1
- type: aosp
  path: frameworks/av/media/libaaudio/include/aaudio/AAudio.h @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/media/java/android/media/AudioTrack.java @ android-17.0.0_r1
tags:
  - audio
  - audioflinger
  - aaudio
  - mmap
  - fastmixer
  - latency
  - perfetto
related_chapters:
- '1.9'
- '5.1'
- '5.2'
- '18.1'
last_idle_audit_at: '2026-11-11T22:40:17+08:00'
last_source_verified_at: '2026-11-11T22:40:17+08:00'
---

# 音频链路（Audio Pipeline）延迟与性能

音频性能问题，很少能靠“一个缓冲区有多少帧”回答。从应用生成一个音频采样值，到扬声器发声，中间可能经过客户端队列、AudioFlinger、HAL、DSP、Codec，以及最终把电信号转换成声音的换能器。录制与播放同时进行时，还要再加上输入链路、应用算法，以及两套并不严格同步的音频时钟。

> 源码基线：Android 17 / API 37，AOSP `android-17.0.0_r1`。

围绕这条链路，我们回答四个工程问题：

1. 这条流最终走了 Normal、Fast、MMAP 还是 Offload 路径？
2. 延迟来自排队、调度、重采样、算法处理，还是硬件路径？
3. 出现输出欠载（underrun）或输入溢出（overrun）——两者统称 xrun——时，哪一环没有按时生产或消费数据？
4. Android 17 的后台音频限制和新硬件卸载 API，是否改变了现象的含义？

## 1. 先分清四类延迟

我们按官方 NDK 文档的分法，先把四类延迟摆清楚：

- **输出延迟**：应用生成音频数据，到扬声器或耳机播放出声音的时间。
- **输入延迟**：声音到达麦克风等输入端，到对应数据可被应用读取的时间。
- **往返延迟**：输入延迟、应用处理时间与输出延迟之和。
- **预热延迟**：首次放入数据后，整条音频链路从关闭或待机（standby）状态启动所需的时间。

这四个指标各测各的：播放器报告的写入耗时算不上输出延迟，`AudioTimestamp` 或 AAudio 时间戳给出的是音频帧位置与时钟的对应关系，声学往返时间则要靠回环测试来量。

### 1.1 缓冲区时长只是一个局部量

音频帧表示同一采样时刻所有声道的一组采样值。单个缓冲区承载的音频时长为：

```text
buffer_duration = frame_count / sample_rate
```

例如，采样率为 48kHz 时，240 帧对应 5ms。这只说明这个缓冲区覆盖了多少音频；端到端输出延迟要看整条真实路径，其中可能包含：

```text
App 已排队数据
+ client/server 共享队列
+ mixer 周期
+ HAL / driver 队列
+ DSP 算法延迟
+ Codec / 无线传输缓冲
+ 调度抖动
```

各项相加才接近整条链路的排队与处理时间。“双缓冲所以乘 2”同样是个案：不同输出配置档（output profile）、路由、HAL、DSP 和设备会形成深度不同的队列，要以实际测量为准。

### 1.2 系统特性声明与实测延迟

Android 没有公共 API 能返回任意路由的完整端到端延迟。系统特性（feature）只表达设备声明的能力：

- `android.hardware.audio.low_latency`：声明连续输出延迟不高于 45ms。
- `android.hardware.audio.pro`：声明连续往返延迟不高于 20ms，并以前一项为前提。

它们是兼容性能力声明，说明的是设备整体能力；当前蓝牙耳机、音效配置或系统负载下的实时延迟，要靠专业音频应用在目标设备和目标路由上做回环（loopback）测试来量：把输出信号送回输入端，测量整条往返链路。

下面的代码只能读取设备是否声明了这两项能力：

```kotlin
val pm = context.packageManager
val lowLatency = pm.hasSystemFeature(
    PackageManager.FEATURE_AUDIO_LOW_LATENCY
)
val proAudio = pm.hasSystemFeature(
    PackageManager.FEATURE_AUDIO_PRO
)
```

`lowLatency` 和 `proAudio` 的读数只回答“设备声明了什么”，距离当前路由上的实际延迟，还差一次实测。

## 2. Android 音频架构：控制面与数据面

控制面负责创建音频流、选择路由和修改状态，数据面负责持续传送音频样本。我们分析音频问题时，先把这两面分开。

数据面上流转的 PCM（脉冲编码调制），是未经有损压缩的数字音频样本表示。

```text
控制面
App
  └─ AudioTrack / AudioRecord / AAudio / Oboe
       ├─ AudioPolicyService：选设备、output/input profile 与 flags
       ├─ AudioFlinger：创建对应 playback/record thread 与 track
       └─ Audio HAL：打开 stream、配置 route、buffer 与 capability

数据面（典型 PCM legacy path）
App buffer
  └─ client/server shared memory
       └─ AudioFlinger mixer/ record thread
            └─ Audio HAL
                 └─ driver / DSP / Codec / transducer
```

对照这张图可以看到：Binder 主要负责建流、状态、路由、参数和控制操作，高频 PCM 数据通常走共享内存队列；“每个音频缓冲区都经过一次 Binder 序列化”这类描述，可以直接排除。

<!-- gracker-diagram: ch01-20-audio-control-data -->
![音频控制操作与连续 PCM 数据的分工](../../assets/diagrams/ch01/ch01-20-audio-control-data.png)

图：控制侧协商设备、配置档和轨道；典型传统 PCM 播放的数据侧通过客户端与服务端共享队列进入 AudioFlinger，再交给 HAL 与设备。MMAP、Direct 和 Offload 的具体样本路径另行区分。

### 2.1 AudioPolicyService 决定“用哪条路”

我们先看决定“走哪条路”的一侧：策略侧根据 `AudioAttributes`、设备连接状态、产品音频策略和可用配置档，选择输出或输入。它会影响：

- 扬声器、USB、蓝牙、HDMI 等目标设备。
- primary（默认主输出）、fast、deep-buffer（通过更深的队列换取稳定性或省电）、direct、offload、MMAP 等输入/输出配置档，描述设备支持的路径、格式、采样率和标志。
- `usage` 对应的音量组和路由策略。
- 设备切换时重新打开或迁移流。

路由切换常伴随音频流的重新配置：旧端点（endpoint）关闭、新端点启动，因此可能出现短暂静音或声音不连续。我们分析切换问题时，把切换前后当作两条不同的路径来看。

### 2.2 AudioFlinger 决定“这条音轨怎么运行”

AudioFlinger 运行在 `audioserver` 中。音频服务在 Android 7 就已从原来的 `mediaserver` 进程拆出，常被误记成 Android 8 才分离。

AudioFlinger 用 track 表示一条应用侧播放或录制流。按输出类型，它会使用不同线程或端点：

- `MixerThread`：通用 PCM 混音。
- `FastMixer`：与某个混音输出关联的短周期快速混音（Fast）线程。
- `DirectOutputThread` / `OffloadThread`：绕过通用软件混音器的直接输出或硬件卸载输出。
- `MmapPlaybackThread`：MMAP 输出的服务端管理路径。
- `RecordThread`、`FastCapture`、`MmapCaptureThread`：输入侧对应路径。

AudioFlinger 负责创建 track、维护共享缓冲区状态、混音或转交数据、与 HAL 交互，并记录输出欠载等情况。所以最终路径由两道关卡共同决定：AudioPolicyService 选路在先，AudioFlinger 的 track 接纳条件在后。

### 2.3 Audio HAL 的 AIDL（Android Interface Definition Language）与 HIDL（HAL Interface Definition Language）

Android 14 起，官方鼓励厂商把 Audio HAL 从 HIDL 迁移到 AIDL；Android 框架仍同时支持两者。AIDL Core HAL 的 `IConfig` 承接一部分原先来自 HIDL XML 的系统级配置。

Android 16 扩展了 AIDL Audio HAL 对可配置音频策略（Configurable Audio Policy，CAP）的支持，但迁移进度因产品而异，运行 Android 16/17 的设备未必都已完成。查看具体设备时应确认：

- 厂商实现使用 AIDL 还是 HIDL Audio HAL。
- 策略来自 AIDL `IConfig`、XML，还是兼容转换路径。
- 产品音频策略中实际声明了哪些混音端口、路由和标志。

## 3. 四类输出路径不要混在一起

| 路径 | 常见数据 | 主要目标 | 关键约束 |
| --- | --- | --- | --- |
| Normal Mixer | PCM | 功能完整、兼容性好 | 可重采样、混音、挂接音效，周期与队列通常更深 |
| Fast Mixer | PCM | 降低交互式输出延迟 | 线性 PCM、硬件采样率、可接受的声道布局，以及 FastMixer 槽位和音效条件 |
| AAudio MMAP | PCM | 降低输入、输出或往返延迟 | HAL、驱动和配置档必须支持；共享与独占模式的含义不同 |
| Direct / Offload | 压缩音频或设备支持的直接输出格式 | 减少软件处理与长时间播放的功耗，或保留特殊格式 | 设备能力、格式、音频属性和独占资源共同决定是否可用 |

低延迟和低功耗在这张表里是两套目标：MMAP / Fast 为交互式音频缩短排队；Offload 把部分处理交给音频硬件，并允许硬件队列承接更多数据，让 CPU 与 Android 框架的数据管道休眠更久。两者都绕过了部分普通混音工作，但走的是不同路径。

## 4. FastMixer：从请求到接纳

Android 4.1 引入 FastMixer。官方设计文档给出的推荐周期是 2–3ms；如果调度稳定性需要，也可用约 5ms。这个数值是设计建议，各设备的实际周期以实测为准。

FastMixer 保留：

- Normal Mixer 预先混合出的子混音（submix）。
- 应用快速音轨（client fast tracks）的混音。
- 每条音轨的音量衰减。

它省掉的是每条快速音轨的重采样、单音轨音效和混音整体音效，混音本身仍然要做：Normal Mixer 先把普通音轨合成一份子混音，经索引 0 送给 FastMixer，FastMixer 再把它与应用快速音轨合并后写向 HAL。

<!-- gracker-diagram: ch01-20-fastmixer-topology -->
![FastMixer 同时接收普通子混音与快速音轨](../../assets/diagrams/ch01/ch01-20-fastmixer-topology.png)

图：在启用 FastMixer 的混音输出中，普通轨先经 Normal Mixer 形成子混音，再与已接纳的快速轨合并。默认总槽位 8 个，其中 0 号用于普通子混音；总数可由设备配置覆盖。

### 4.1 源码里的接纳条件

`android-17.0.0_r1` 的 `PlaybackThread::createTrack_l()` 在处理 FAST 请求前写着：

```cpp
// client expresses a preference for FAST, but we get the final say
```

源码注释中的 `preference` 表明 FAST 标志只表达偏好，AudioFlinger 可以清除它。因此，`PERFORMANCE_MODE_LOW_LATENCY`、`AAUDIO_PERFORMANCE_MODE_LOW_LATENCY` 或 `AUDIO_OUTPUT_FLAG_FAST` 都只是请求。最终是否成为快速音轨，要同时满足：

1. AudioPolicy 选出的输出支持低延迟或快速路径。
2. 数据是线性 PCM。
3. 采样率等于当前输出的硬件采样率。
4. 声道掩码通过当前实现的兼容性判断：请求掩码与输出（含触觉声道）一致，或输出掩码不是立体声，或请求音轨为单声道。
5. 这个混音输出关联了 FastMixer。
6. 快速音轨槽位仍有空位；一个槽位表示 FastMixer 可同时接纳的一条输入音轨。
7. 会话、输出级或设备上的音效链不会移除 FAST 标志。

声道条件旁仍保留着一个 TODO：抽取用于检查是否需要高成本向下混音（downmix）的函数。现有掩码判断不能视为完整的声道转换成本检查，排查多声道配置时还要核对实际转换路径。

另一句常见的误写是“帧数不匹配就一定拒绝 FAST”。对流式快速音轨，系统会把缓冲区帧数至少提高到 `mFrameCount * fast_track_multiplier`，调整的是实际缓冲配置，帧数检查不在第一层拒绝条件里。打开音轨后要读取实际配置，builder（构建器）里的请求未必原样生效。

### 4.2 默认为什么最多看到 7 条应用快速音轨

`FastMixerState` 用下面三个常量定义槽位数的下限、上限和默认值：

```cpp
static constexpr unsigned kMinFastTracks = 2;
static constexpr unsigned kMaxFastTracks = 32;
static constexpr unsigned kDefaultFastTracks = 8;
```

`PlaybackThread` 把索引 0 留给 Normal Mixer 的子混音，所以默认配置下可供应用使用的是 7 个槽位。厂商可以用只读属性 `ro.audio.max_fast_tracks` 在 2～32 之间配置总数。我们把结论写成三条：

- AOSP 默认总数为 8，应用默认最多使用 7 个。
- 设备可能覆盖这个值。
- 槽位用完后新请求会降级，判断依据要来自打开后的实际配置。

### 4.3 FastMixer 的实时调度解决什么

FastMixer 使用提升后的 `SCHED_FIFO` 实时调度优先级：按固定优先级调度实时线程，缩短线程被唤醒后等待 CPU 的时间。不过它仍会在 HAL `write()` 处等待，把实时调度理解成“永不阻塞”并不合适。

应用侧的供数线程同样关键：系统接纳快速音轨并取得客户端线程 tid 后，会请求 ActivityManager 为该线程配置音频优先级，这个请求仍可能失败。FastMixer 准时醒来只是前提，应用侧也要按时生产数据；应用供数延误时，输出欠载照样发生。

## 5. AAudio、MMAP 与 Oboe

### 5.1 AAudio 与 MMAP 的关系

AAudio 从 Android 8.0 / API 26 提供。它是面向高性能音频的 C API，同一套 API 可以落到不同数据路径：

- 设备支持并成功打开 MMAP：走 MMAP。
- MMAP 不可用或自动（AUTO）模式打开失败：回退到传统的 AudioFlinger 路径。

所以“用了 AAudio”只说明选了这套 API，具体走哪条路要另行核对。Android 16 / API 36 起，我们可以用下面的公开 NDK API 直接核对实际路径：

```cpp
bool mmapUsed = AAudioStream_isMMapUsed(stream);
```

返回 `true` 才表示这个已经打开的流使用了 MMAP。较早平台上要结合设备属性、AAudio 日志和 `dumpsys audio` / `dumpsys media.audio_flinger` 判断。

### 5.2 低延迟构建参数要留出协商空间

AAudio 的 builder 用来在创建音频流时集中设置参数；拿最低延迟通常要请求 `LOW_LATENCY` 并使用数据回调。下面的代码同时请求低延迟和独占模式：

```cpp
AAudioStreamBuilder* builder = nullptr;
AAudio_createStreamBuilder(&builder);

AAudioStreamBuilder_setDirection(
        builder, AAUDIO_DIRECTION_OUTPUT);
AAudioStreamBuilder_setPerformanceMode(
        builder, AAUDIO_PERFORMANCE_MODE_LOW_LATENCY);
AAudioStreamBuilder_setSharingMode(
        builder, AAUDIO_SHARING_MODE_EXCLUSIVE);
AAudioStreamBuilder_setDataCallback(
        builder, DataCallback, userData);

AAudioStream* stream = nullptr;
aaudio_result_t result =
        AAudioStreamBuilder_openStream(builder, &stream);
AAudioStreamBuilder_delete(builder);
// 继续使用 stream 前必须检查 result == AAUDIO_OK。
```

打开之后先确认 `result == AAUDIO_OK`，再继续使用 `stream`。`EXCLUSIVE` 只是请求：端点已被占用或设备不支持时，系统可能给出共享流。除业务必须固定的字段外，可让采样率、格式和声道数使用 `AAUDIO_UNSPECIFIED`，打开后再读取实际值：

```cpp
int32_t sampleRate = AAudioStream_getSampleRate(stream);
int32_t channelCount = AAudioStream_getChannelCount(stream);
aaudio_format_t format = AAudioStream_getFormat(stream);
aaudio_sharing_mode_t sharing =
        AAudioStream_getSharingMode(stream);
aaudio_performance_mode_t performance =
        AAudioStream_getPerformanceMode(stream);
```

这些返回值分别给出实际采样率、声道数、样本格式、共享模式和性能模式。“请求成功”与“拿到预期路径”是两件事，日志和性能报告里要记录的是打开后的实际配置。

### 5.3 MMAP 的数据面与控制面

Android 8.1 扩展了 AAudio MMAP。设备需要在 Audio HAL 和驱动中声明并实现 MMAP/NOIRQ 能力，还要提供对应的音频策略配置档。MMAP 让应用和驱动通过内存映射（MMAP）缓冲区交换数据；NOIRQ 表示这条路径不依赖传统的周期性中断通知方式。

- **EXCLUSIVE**：应用可写入与 ALSA（Linux 的音频驱动框架）驱动共享的内存映射缓冲区，绕过普通软件混音器；延迟最低，但端点更容易因路由变化或资源竞争而断开。
- **SHARED**：多个流共享端点，由系统侧负责混合与管理；这里没有应用独占的硬件缓冲区。

所以无论哪种模式，建流、权限、路由、状态切换、时间戳、xrun 和错误恢复仍要走 AAudio 服务、AudioFlinger / AudioPolicy 与 HAL 的控制路径。“应用直接打开 `/dev/snd/*`，audioserver 完全不参与”的画法，漏掉的正是这条控制路径。

AAudio 的 MMAP 策略通常允许自动回退。只有在专用验证环境里才适合强制 MMAP 并禁止回退；面向用户的代码要能处理传统 AudioFlinger 路径。

<!-- gracker-diagram: ch01-20-aaudio-paths -->
![AAudio API 不等于 MMAP 独占数据路径](../../assets/diagrams/ch01/ch01-20-aaudio-paths.png)

图：AAudio 在设备能力、系统策略与参数允许时打开 MMAP；AUTO 策略下不可用时可以回退传统路径。MMAP 独占由应用访问与驱动共享的映射缓冲区，共享模式则由服务侧混合；控制与资源管理始终由系统参与。

### 5.4 Oboe 的能力与选路

Oboe 是 Google 的 C++ 封装：

- 平台可用时调用 AAudio。
- AAudio 不可用时回退 OpenSL ES。
- 统一音频流构建器、数据回调、错误恢复和一部分设备兼容处理。

Oboe 的选路没有固定的“MMAP EXCLUSIVE → MMAP SHARED → FAST → Normal”决策表，最终路径仍受 API 级别、构建参数、设备配置档、端点占用和厂商实现影响。

Oboe 的工程价值在于减少跨版本分支，并提供 `getAudioApi()`、`getSharingMode()`、`getPerformanceMode()` 等结果查询。至于 HAL 的 MMAP 能力与数据回调中的锁等待，Oboe 的封装管不到这里，仍要应用自己处理。

## 6. 缓冲区、数据回调与 xrun

### 6.1 区分容量、大小和 burst

AAudio 中三个概念容易混淆，我们先把它们分开：

- **缓冲区容量（buffer capacity）**：这条流最多可容纳多少音频帧。
- **缓冲区大小（buffer size）**：当前使用的填充或阻塞阈值，可在容量范围内调节。
- **每次 burst 的帧数（frames per burst）**：设备每批硬件数据处理多少帧，由系统与设备决定。

这里的 burst 指硬件按固定节奏处理的一批音频数据。低延迟输出通常让缓冲区大小保持为 burst 的整数倍：太大增加排队，太小则可能在一次调度延迟后立即欠载。常用的调优方法是：

1. 从能稳定播放的大小开始。
2. 每次减小一个 burst。
3. 观察 `AAudioStream_getXRunCount()`。
4. 一旦 xrun 增长，就增大一到数个 burst，然后在真实负载下、设备充分运行升温后、有后台干扰时分别复测。

对输入流，调优方向要反过来：输入端会尽快搬运数据，应用更应该关注读取是否及时、有没有发生输入溢出；这套“逐步增大缓冲区来防止欠载”的调法是给输出侧用的。

### 6.2 把耗时工作移出数据回调

AAudio/Oboe 的数据回调运行在高优先级线程上。回调内应避免：

- `malloc` / `new` 和不可控的对象构造。
- 文件、网络或 Binder I/O。
- 互斥锁、条件变量等待和休眠。
- 停止或关闭当前音频流。
- 在触发回调的同一条流上再次调用 `read()` / `write()`。
- 大量日志和复杂的轨迹名称拼接。

环形缓冲区是一块循环复用的固定容量内存。下面的结构让普通工作线程完成耗时任务，音频回调只从无锁环形缓冲区取数：

```text
普通 worker
  └─ 解码 / 网络 / 文件 / 模型计算
       └─ lock-free ring buffer
            └─ audio callback：只取固定数量 frames + 轻量 DSP
```

这种分工减少了高优先级回调被外部工作阻塞的机会。但“无锁”两个字本身保证不了安全：生产者和消费者必须定义清楚容量、读写索引、跨线程读写可见性的内存顺序、欠载时的填零策略和音频流关闭时序。

<!-- gracker-diagram: ch01-20-callback-buffer-boundary -->
![把音频数据回调与耗时生产工作隔开](../../assets/diagrams/ch01/ch01-20-callback-buffer-boundary.png)

图：工作线程负责解码、网络与复杂计算，数据回调只消费预备好的样本并做有界处理。队列的容量、内存可见性、欠载策略和关闭顺序需要明确设计；使用无锁队列本身并不保证音频按期供数。

### 6.3 输入和输出时钟的漂移

即便两边都报告 48kHz，我们也要把录制时钟与播放时钟当作两个可能来自不同晶振的时钟，实际速率略有差异。长时间回环时，固定大小的 FIFO 会逐渐积满或耗空。

实时通话、KTV 和乐器处理需要：

- 用时间戳估计输入和输出的音频帧位置。
- 监控环形缓冲区中的数据量。
- 用异步采样率转换或小幅速度补偿，吸收输入、输出实际速率之间不断累积的时钟漂移。
- 把算法固有延迟与系统排队延迟分开记录。

只把输入回调的缓冲区原样交给输出回调，短时间测试可能正常，长时间运行仍会周期性出现 xrun。

<!-- gracker-diagram: ch01-20-duplex-clock-drift -->
![双向音频为何需要监控时钟漂移](../../assets/diagrams/ch01/ch01-20-duplex-clock-drift.png)

图：输入与输出即使都标为 48 kHz，实际时钟仍可能有偏差。应用应结合时间戳与 FIFO 水位估计漂移，以异步重采样或小幅速度补偿稳定供数；增大队列只能延后问题暴露并增加延迟。

## 7. Android 17 / API 37 的音频行为变化

导语里的第四个问题在这一节展开：后台音频限制和新的硬件卸载 API，会改变部分现象的含义。我们按四类变化来看——后台准入、硬件卸载、来源信息与音量行为，每一类都有自己的排查入口。

### 7.1 后台音频限制（audio hardening）

先把术语说清：这一节的 hardening 指系统更严格地执行后台使用条件；音频焦点用于协调多个应用谁可以主导当前声音输出。Android 17 对后台播放、音频焦点请求、音量与铃声修改施加生命周期限制。

对所有运行在 Android 17 上的应用，至少要满足以下一项：

- 有可见的 Activity；或
- 正在运行非 `SHORT_SERVICE` 类型的前台服务。

`targetSdk` 为 37 及以上的后台应用还要满足更严格的条件：

- 前台服务具有系统标记的 while-in-use（WIU）能力，表示应用当前满足“使用期间”访问条件；或
- 应用获得精确闹钟权限，且操作的是 `USAGE_ALARM` 音频流。

不满足时：

- 播放和音量修改通常静默失败。
- `requestAudioFocus()` 返回 `AUDIOFOCUS_REQUEST_FAILED`。

默认行为下，播放被静音时 API 不会提供失败消息，因此不能靠 `write()` 报错来识别限制。先在 `dumpsys audio` 或 logcat 中查找带包名的 `AudioHardening` 记录：`level: partial` 表示没有运行前台服务，`level: full` 表示前台服务缺少 WIU 能力。持续的写入错误属于下文 `throw` 测试模式的诊断行为。

下面的命令用于在测试设备上强制切换限制强度，并配合日志与系统状态做对照：

```bash
# 强制对所有 App 启用完整限制；WIU 和 alarm 豁免也被收紧
adb shell cmd audio set-enable-hardening enable

# 在完整限制基础上启用 loud failure
adb shell cmd audio set-enable-hardening throw

# 关闭限制，用于 A/B 对照
adb shell cmd audio set-enable-hardening disable

adb logcat -s AudioHardening
adb shell dumpsys audio
```

`throw` 模式下，音量或音频焦点操作可抛出 `IllegalStateException`；显式调用 `write()` 的播放会持续返回错误，某些没有显式 `write()` 的播放模式可能直接让应用崩溃。测试模式比默认发布行为更严格，报告里必须写明使用了哪个开关。

### 7.2 AAudio Power Saving Offloaded：Android 16 引入，Android 17 继续扩展

`AAUDIO_PERFORMANCE_MODE_POWER_SAVING_OFFLOADED` 从 API 36 提供。`AAudio.h` 对它的定义是：

- 只支持输出流。
- 使用音频硬件卸载路径。
- 可在短时间内向硬件缓冲区写入数秒数据。
- Android 框架的数据管道随后可暂停，让 CPU 有更长的休眠时间。

它服务于长音频省电而非交互式低延迟，与 `LOW_LATENCY` 互斥。成功打开后仍应读取实际性能模式，并通过 `dumpsys` 确认输出类型；“已经卸载”只给出状态这一层，具体用了哪种 DSP 或硬件解码实现，还要另行确认。

Android 17 / API 37 又为 AAudio 硬件卸载增加了按音频帧位置刷新队列的能力：`AAudio_getFlushFromFrameSupport()` 与 `AAudioStream_flushFromFrame()`。使用前要用已经填好卸载性能模式、格式、声道掩码和采样率的 `AAudioStreamBuilder` 调用 `AAudio_getFlushFromFrameSupport()`；Java `AudioTrack` 侧则用 `AudioFormat` 与 `AudioAttributes` 查询设备是否支持。

### 7.3 `AudioTrack.flushWrittenFramesFromPosition()`

API 37 的 Java `AudioTrack` 增加了按音频帧位置丢弃已写数据的能力。下面的构建方式表明它只允许用于硬件卸载播放：

```java
new AudioTrack.Builder()
        .setOffloadedPlayback(true)
        // format / attributes / buffer...
        .build();
```

`.setOffloadedPlayback(true)` 是必要条件，但设备仍可能不支持指定格式和属性。创建音轨前应先查询：

```java
int support =
        AudioTrack.getFlushWrittenFramesFromPositionSupport(
                format, attributes);
```

`support` 返回指定格式与属性是否具有这项能力。支持后仍要处理两种精度：

- `FLUSH_FROM_ACCURACY_BEST_EFFORT`：尽量从不早于请求位置的可实现位置刷新，并返回实际位置。
- `FLUSH_FROM_ACCURACY_EXACT`：精确位置满足不了就整体失败；这个模式里没有近似刷新，调用方要处理失败结果。

调用期间要避免并发执行 `write()`；成功后如果活动音频流的剩余数据很少，应及时续写，避免输出欠载。它解决的是硬件卸载队列中跳转播放位置后的局部清理，普通 PCM `AudioTrack` 这次同样没有获得通用跳转 API。

### 7.4 编解码来源（codec provenance）的用途

这里的 codec provenance 指音频数据原本来自哪种编解码格式。API 37 的 `AudioTrack.Builder.setCodecProvenance()` 接收 `audio/...` MIME 媒体类型，例如 `MediaFormat.MIMETYPE_AUDIO_EAC3_JOC`。它告诉 Android 框架和 HAL：送进 `AudioTrack` 的数据源自哪种编解码器（Codec）。当前音轨格式与原始格式不同时，这项信息可辅助系统选择空间音频渲染路径。

`getCodecProvenance()` 返回配置时保存的媒体类型；未设置时返回空字符串。它的信息量到 MIME 类型为止：Codec2 组件名、厂商模块名，以及软件解码、硬件解码还是硬件卸载（Offload）路径的判定，都要另找办法。

### 7.5 Assistant 独立音量

Android 17 为 `USAGE_ASSISTANT` 增加独立的 Assistant 音量流，使语音助手音量与媒体音量分离。具有相应权限或角色的助手应用可使用 `MODE_ASSISTANT_CONVERSATION` 向系统表明当前正在对话，从而改善没有活动播放或连接蓝牙外设时的音量控制一致性。

这是一项路由与音量行为变化；`USAGE_ASSISTANT` 并未顺带获得低延迟路径，相关条件仍是前文 FastMixer 与 AAudio 那套。

## 8. 观测：dumpsys、Perfetto 与回环测试

### 8.1 先记录测试条件

我们在采集系统轨迹前，先把测试条件写下来：

- 构建指纹（标识系统软件版本的一串信息）、Android 版本，以及是否为 `userdebug` 调试构建。
- 输入、输出设备及其连接方式。
- 应用使用的 API、`usage`、格式、采样率和声道数。
- 请求与实际获得的共享模式和性能模式。
- 缓冲区容量、大小和每次 burst 的帧数。
- 是否启用音效、空间音频和后台音频限制测试开关。
- 复现时设备是否切路由、熄屏、发热或有并发音频。

音频路径对路由非常敏感；漏掉这些记录，两份轨迹很可能来自不同的音频链路。

### 8.2 先用 dumpsys 确认路径

下面三条命令分别查看 AudioFlinger、音频策略状态和快速音轨总数配置：

```bash
adb shell dumpsys media.audio_flinger
adb shell dumpsys audio
adb shell getprop ro.audio.max_fast_tracks
```

重点核对：

- 应用进程 pid 和 uid 对应的音轨。
- 输出线程类型、采样率、格式和缓冲区帧数。
- 音轨标志中是否接受 FAST；官方调试文档也建议用音轨列中的 `F` 确认快速音轨。
- 快速音轨可用槽位掩码和欠载计数器。
- 输出属于混音、直接输出、硬件卸载还是 MMAP。
- 当前路由、设备与活动状态。

AAudio 侧同时记录下面这些 API 的返回值：

```text
getPerformanceMode()
getSharingMode()
getSampleRate()
getFramesPerBurst()
getBufferSizeInFrames()
getBufferCapacityInFrames()
getXRunCount()
isMMapUsed()  // API 36+
```

这些值把性能模式、共享模式、实际采样率、缓冲配置、xrun 次数和 MMAP 使用情况集中在一处，我们排查时直接对照这一组。

### 8.3 Perfetto 看调度与因果顺序

下面的 Perfetto 轻量采集命令记录应用、音频事件、线程调度、CPU 频率和空闲状态：

```bash
adb shell perfetto \
  -o /data/misc/perfetto-traces/audio.perfetto-trace \
  -t 10s -b 64mb \
  -a com.example.app \
  audio sched freq idle

adb pull \
  /data/misc/perfetto-traces/audio.perfetto-trace
```

第一条命令在设备上采集 10 秒，第二条把轨迹文件拉到本机。设备支持的 atrace 分类会随版本和产品变化，先运行 `adb shell atrace --list_categories` 看清楚，各厂商音频轨迹区段的名称以列表输出为准。

拿到轨迹后，我们按这条顺序检查：

1. 应用的数据回调或写入线程是否按周期运行。
2. 线程被唤醒后，是立即获得 CPU，还是长时间停留在 Runnable 状态等待调度。
3. 回调内是否出现锁、Binder、I/O、分配或长计算。
4. FastMixer / MixerThread / RecordThread / FastCapture 的唤醒是否稳定。
5. 路由、待机、音频流启动或停止是否恰好与缺口重合。
6. CPU 频率、过热降频或更高优先级的 RT 线程是否改变调度窗口。

应用代码可用 `android.os.Trace` 或 `<android/trace.h>` 标记生产、回调与消费区间，但每条轨迹事件本身也有开销；不要在每个采样值或极短循环里插桩。

### 8.4 输出欠载的计数器证据

Perfetto 不保证每次 xrun 都出现名为 `underrun` 的标准轨迹区段；更可靠的判断依据是下面这组计数器：

- AAudio `getXRunCount()` 前后差值。
- `AudioTrack.getUnderrunCount()`。
- `dumpsys media.audio_flinger` 中音轨或 FastMixer 的欠载计数器。
- 轨迹中应用供数间隙与服务端线程的消费时点。
- 可控构建上的 AudioFlinger 日志，或自定义 `userdebug` / `eng` 构建上的 tee sink；后者会复制一份音频流供调试，出于隐私考虑，编译与运行时开关默认均关闭。调试后应关闭 tee sink，不能在生产构建中保持启用。

接下来做一个二分：计数器增长、且回调线程在截止时间前长期停在 Runnable 状态等 CPU，优先检查调度；回调已按时完成而计数器仍在涨，再检查缓冲区、HAL 写入、路由和设备侧。

### 8.5 声学延迟需要回环测试

Perfetto 能解释软件时序；扬声器振膜何时发声、麦克风声学信号何时到达，都在它的视野之外。端到端往返延迟应使用：

- CTS Verifier / OboeTester 等回环测试。
- 受支持的物理回环适配器，或受控的声学回路。
- 明确输入、输出路由，并关闭额外信号处理的测试配置。

报告至少给出中位数、P95、样本数、路由和测试方法。P95 表示 95% 的样本落在该值以内，适合观察较慢的尾部样本；稳定延迟要看分布，单个最佳值代表不了它。

## 9. 常见故障的证据链

| 现象 | 先查 | 进一步验证 |
| --- | --- | --- |
| 点击后很久才发声 | 预热状态、已经排队的帧数、实际输出路径 | 分开测量首次与稳定状态；检查待机、启动和缓冲区大小 |
| 持续延迟大但无杂音 | Normal、deep-buffer、Offload、重采样和音效 | 用 `dumpsys` 核对标志、采样率和输出线程 |
| 间歇爆音或断续 | xrun 计数器、回调截止时间 | 用 Perfetto 检查线程等待调度的时间、锁、I/O 和 CPU 频率 |
| 同时录放越久越不稳 | 输入、输出时间戳和 FIFO 中的数据量 | 检查时钟漂移与异步重采样 |
| `LOW_LATENCY` 请求无效 | 打开后的模式、采样率、共享方式和 FAST 标志 | 检查槽位、音效链、设备配置档和 MMAP 回退 |
| 切换耳机时短暂静音 | 路由以及打开、关闭时序 | 结合 `dumpsys audio` 与 AudioPolicy / AudioFlinger 轨迹 |
| Android 17 后台突然无声 | 应用生命周期、前台服务、WIU、音频焦点结果 | 检查带包名的 `AudioHardening` 日志与 `partial/full` 级别，并记录强制测试开关 |

## 10. 蓝牙音频的延迟构成

蓝牙路径会在链路上叠加编码、分包（把音频装入无线传输的数据包）、无线调度、抖动缓冲（吸收数据包到达时间的波动）、耳机解码和本地 DSP。SBC、AAC、aptX、LDAC、LC3 只是其中一部分变量；同一种编解码器在不同缓冲配置、耳机固件、链路质量和模式下也会有明显差异。

蓝牙编解码器名称不足以给出固定的端到端延迟范围。延迟数值需要注明设备、路由、缓冲配置和测试方法，否则容易把音质模式和低延迟模式混为一谈。排查时可以按下面的步骤复测：

1. 固定手机、耳机、编解码器、蓝牙协议配置与场景模式。
2. 记录实际蓝牙路由和协商结果。
3. 用高速摄像、外部采集或声学回环测试测量端到端延迟。
4. 分开报告中位数、尾部延迟与断续率。

对节奏游戏或虚拟乐器，内置扬声器、有线或 USB 路径通常更容易获得稳定的交互延迟。必须支持蓝牙时，产品应做校准，或根据实测提供延迟补偿；FastMixer 或 MMAP 在手机侧成功，无线和耳机端的缓冲仍然存在。

## 11. API 选择

| 场景 | 优先考虑 | 关键验证 |
| --- | --- | --- |
| 游戏、合成器、实时音效 | Oboe/AAudio 数据回调 + `LOW_LATENCY` | 实际采样率、模式、共享方式、MMAP、xrun，以及触摸到声音的实测延迟 |
| 数字音频工作站（DAW）、吉他效果、KTV | Oboe/AAudio 输入 + 输出 | 往返回环、时钟漂移，以及 FastCapture / MMAP 输入 |
| 视频会议、网络语音（VoIP） | Telecom / 通信栈配合 AAudio/Oboe | 路由、回声消除（AEC）、降噪（NS）算法延迟、输入输出同步和前台服务 |
| 长音乐、播客 | Media3/ExoPlayer，设备支持时使用 Offload | 无缝衔接、跳转播放、路由、功耗和硬件卸载能力 |
| 短音效 | 预加载的 SoundPool 或低延迟音频引擎 | 首次预热与稳态分开测 |
| 语音助手 | 正确的 `USAGE_ASSISTANT` 与 Assistant 角色能力 | Android 17 独立音量行为、音频焦点与后台生命周期 |

这张表刻意避开“必须小于 10ms/20ms”这类写死的数值：目标取决于设备能力和产品交互。API 负责提出请求，结果要靠测量来证明。

## 12. 版本演进

| 版本 | 变化 | 分析重点 |
| --- | --- | --- |
| Android 4.1 | 引入 FastMixer | 建立低延迟 PCM 输出的快速路径 |
| Android 7 | AudioFlinger / AudioPolicyService 所在的音频服务从 mediaserver 分离到 audioserver | 进程与权限边界变化 |
| Android 8.0（API 26） | 引入 AAudio | 原生高性能音频 C API |
| Android 8.1（API 27） | AAudio 增加 MMAP/NOIRQ 低延迟路径 | 需要 HAL、驱动和音频策略配置档支持 |
| Android 14（API 34） | 官方鼓励新实现迁移到 AIDL Audio HAL；Android 框架兼容 AIDL/HIDL | 不能仅凭系统版本断言 HAL 类型 |
| Android 16（API 36） | AIDL HAL 扩展 CAP；AAudio 增加 Power Saving Offloaded；公开 `isMMapUsed()` | 分开验证省电硬件卸载与低延迟 MMAP |
| Android 17（API 37） | 加强后台音频限制；AudioTrack/AAudio 支持按位置局部刷新；增加 codec provenance 与 Assistant 独立音量 | 当前源码以 `android-17.0.0_r1` 为准 |

## 13. 常见误区

### “用了 AAudio 就一定是 MMAP”

用了 AAudio 只说明选了这套 API；AAudio 可以回退到传统 AudioFlinger 路径。API 36 及以上版本可用 `AAudioStream_isMMapUsed()` 核对。

### “请求 LOW_LATENCY 就一定是快速音轨”

这个请求只表达低延迟偏好；采样率、声道布局、FastMixer、可用槽位和音效都会影响是否接纳。

### “FastMixer 不做混音”

FastMixer 是做混音的：它把 Normal Mixer 的子混音与应用快速音轨合并，只是功能比 Normal Mixer 精简。

### “缓冲区是 5ms，所以输出延迟就是 5ms”

这个数只描述一个缓冲区承载的音频时长，其他队列、DSP、硬件和调度时间都还要叠加进来。

### “EXCLUSIVE 意味着系统其他声音都消失”

EXCLUSIVE 独占的是一个端点；系统声音可能通过另一个端点继续播放。请求也可能被降级为 SHARED。

### “xrun 一定是缓冲区太小”

数据回调等待锁、线程没有及时获得 CPU、HAL 阻塞、路由切换和时钟漂移都能造成 xrun。增大缓冲区换来的只是对调度波动更高的容忍度，代价是延迟增加。

### “`getCodecProvenance()` 能判断硬解或软解”

它返回配置的编解码器 MIME 媒体类型；编解码组件名称和实际执行路径都在它的返回范围之外。

### “Perfetto 能直接量出扬声器发声时间”

Perfetto 解释的是软件时序；声学端到端延迟要做回环测试。

## 14. 排查清单

1. 固定设备、系统构建版本、路由和测试内容。
2. 区分预热、稳态输出、输入与往返延迟。
3. 记录构建器请求与打开后的实际音频流参数。
4. 用 `dumpsys` 确认 Normal、Fast、MMAP 或 Offload 路径。
5. 同时记录应用的 xrun 计数器与 AudioFlinger 欠载计数。
6. 用 Perfetto 对齐数据回调、服务端线程、调度、频率和路由事件。
7. 从数据回调中移除分配、锁、I/O 和耗时不定的计算。
8. 以 burst 为单位调整缓冲区，并在真实压力下复测尾部延迟。
9. 输入输出同时运行时处理时钟漂移。
10. Android 17 后台问题先查前台服务、WIU 与 `AudioHardening`，不要误判为混音器性能退化。
11. 最终用回环或外部测量验证端到端指标。

## 参考资料

- [AOSP：Audio architecture](https://source.android.com/docs/core/audio)
- [AOSP：Design for reduced latency](https://source.android.com/docs/core/audio/latency/design)
- [AOSP：Audio latency measurements](https://source.android.com/docs/core/audio/latency/measurements)
- [AOSP：AAudio and MMAP](https://source.android.com/docs/core/audio/aaudio)
- [AOSP：Audio debugging](https://source.android.com/docs/core/audio/debugging)
- [AOSP：AIDL and HIDL Audio HAL comparison](https://source.android.com/docs/core/audio/aidl-hidl-comp)
- [Android NDK：Audio latency](https://developer.android.com/ndk/guides/audio/audio-latency)
- [Android NDK：AAudio](https://developer.android.com/ndk/guides/audio/aaudio/aaudio)
- [Android 17：Background audio hardening](https://developer.android.com/about/versions/17/changes/bg-audio)
- [Android 17：Features and APIs](https://developer.android.com/about/versions/17/features)
- [Android API：AudioTrack](https://developer.android.com/reference/android/media/AudioTrack)
- [Oboe：Full Guide](https://github.com/google/oboe/blob/main/docs/FullGuide.md)
- [Perfetto CLI reference](https://perfetto.dev/docs/reference/perfetto-cli)
- [AOSP：Threads.cpp（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/av/+/refs/tags/android-17.0.0_r1/services/audioflinger/Threads.cpp)
- [AOSP：FastMixerState.cpp（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/av/+/refs/tags/android-17.0.0_r1/services/audioflinger/fastpath/FastMixerState.cpp)
- [AOSP：FastMixerState.h（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/av/+/refs/tags/android-17.0.0_r1/services/audioflinger/fastpath/FastMixerState.h)
- [AOSP：AAudio.h（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/av/+/refs/tags/android-17.0.0_r1/media/libaaudio/include/aaudio/AAudio.h)
- [AOSP：AudioTrack.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/media/java/android/media/AudioTrack.java)
