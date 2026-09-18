# Android 技术内幕：系统机制、性能优化与工具实战

[English navigation summary](README.en.md)

> *Android Internals: System Architecture, Performance & Tooling in Practice*

面向有经验的 Android 开发者和系统工程师。覆盖 App、Framework、Native 与 Kernel，当前基准是 Android 17 / API 37，源码核对标签是 AOSP `android-17.0.0_r1`。

完整目录见 [`src/SUMMARY.md`](src/SUMMARY.md)。每周会把正文编成 EPUB，放在 [GitHub Releases](https://github.com/Gracker/android-internals-wiki/releases)。

<!-- android-performance-ecosystem:start -->
## Android 性能分析生态

[Android Performance Ecosystem](https://github.com/Gracker/android-performance-ecosystem) 通过导航 Hub 与七个核心项目，把可选插桩、采集、分析、系统知识与可复现案例连接成一套完整路径。

| 阶段 | 项目 | 作用 | 地址 |
| --- | --- | --- | --- |
| 导航 | [Android Performance Ecosystem](https://github.com/Gracker/android-performance-ecosystem) | 维护统一项目地图、交接元数据、README 导航区块与漂移检查。 | [GitHub](https://github.com/Gracker/android-performance-ecosystem) |
| 插桩 | [TraceFix](https://github.com/Gracker/TraceFix) | 在编译期注入 App 侧 android.os.Trace section，让方法执行在运行时 Trace 中可见。 | [GitHub](https://github.com/Gracker/TraceFix) |
| 采集与测量 | [Perfetto Tools](https://github.com/Gracker/perfetto-tools) | 抓取可复现的 Perfetto Trace，并采集 FPS 或 Simpleperf 测量结果。 | [GitHub](https://github.com/Gracker/perfetto-tools) |
| 分析 | [SmartPerfetto](https://github.com/Gracker/SmartPerfetto) | 通过 AI 辅助 Web UI、CLI、报告、会话、对比和证据工作流分析 Trace。 | [GitHub](https://github.com/Gracker/SmartPerfetto) |
| Agent 分析 | [Perfetto Skills](https://github.com/Gracker/Perfetto-Skills) | 为 Agent 提供可移植的 Android、Linux、Chromium Perfetto 分析 Skill，并通过固定版本流程同步选定资产。 | [GitHub](https://github.com/Gracker/Perfetto-Skills) |
| 学习 | [Android Performance Blog](https://github.com/Gracker/Gracker.github.io) | 通过文章、系统原理和案例复盘讲解 Perfetto 与 Systrace 分析。 | [AndroidPerformance.com](https://www.androidperformance.com/) · [GitHub](https://github.com/Gracker/Gracker.github.io) |
| 系统知识 | Android Internal Wiki | 处于 alpha 阶段的 Android 系统知识库，覆盖 App、Framework、Native 与 Kernel 机制。 | [GitHub](https://github.com/Gracker/android-internals-wiki) |
| 复现 | [Trace for Blog (SystraceForBlog)](https://github.com/Gracker/SystraceForBlog) | 提供文章使用的 Perfetto、Systrace 及相关案例文件，支持动手复现。 | [GitHub](https://github.com/Gracker/SystraceForBlog) |
<!-- android-performance-ecosystem:end -->

## 怎么读

- 跨层：从应用代码追到 Framework、Native 和 Kernel，同一条问题链写在相邻章节里。
- 按 Android 版本追踪变化，正文确定性结论最高覆盖 Android 17。
- 机制说明带 AOSP 路径，方便回到同一份源码核对。
- 工具章写采集、SQL 和证据形态；实践章写启动、渲染、内存、I/O、功耗和线上治理。

当前版本为中文。v1.0 之后会提供完整英文版。

## 内容结构

### 第一部分：Android 系统运行机制

系统怎么把应用跑起来，画面、输入、内存、调度和存储分别在哪一层等待。

- [第 1 章 系统架构全景](src/part1-fundamentals/ch01-architecture/README.md)：进程模型、Zygote、Binder、cgroup 和系统服务边界。慢启动、ANR 或 native 崩溃时，先确认代码跑在哪个进程、跨过哪条 IPC。
- [第 2 章 渲染系统](src/part1-fundamentals/ch02-rendering/README.md)：从主线程、RenderThread、BufferQueue、SurfaceFlinger 到 HWC 和面板。掉帧、首帧晚、SurfaceView 错位，要先分清帧走哪条生产和合成路径。
- [第 3 章 输入系统](src/part1-fundamentals/ch03-input/README.md)：点击无响应、滑动不跟手、返回动画晚一拍。帧率正常也不能证明输入及时到达应用，要把事件和产生反馈的那一帧放在同一条时间线上。
- [第 4 章 内存管理](src/part1-fundamentals/ch04-memory/README.md)：GC、缺页、direct reclaim、zram、进程冻结和图形缓冲。OOM 只是其中一种结局，内存压力也会变成卡顿和后台重建。
- [第 5 章 CPU 调度与能耗管理](src/part1-fundamentals/ch05-cpu-power/README.md)：可运行却排队、大小核放置、DVFS、温控和后台执行政策。只看 CPU 使用率分不清这些原因。
- [第 6 章 存储与 I/O](src/part1-fundamentals/ch06-storage/README.md)：page fault、`fsync`、块设备争用，以及共享存储上的 MediaProvider / FUSE。只看 Java 栈，容易把存储等待当成业务计算。

### 第二部分：性能问题与优化

用户能感觉到的卡、慢、无响应、耗电和网络差，分别对应哪类系统行为。

- [第 7 章 流畅性](src/part2-performance/ch07-smoothness/README.md)：掉帧、输入延迟、合成降级和温控限制。相似的“卡”背后，要改的位置可能完全不同。
- [第 8 章 响应速度](src/part2-performance/ch08-responsiveness/README.md)：从操作到可见反馈或恢复可交互的时间。和流畅性分开：一个看首响，一个看连续帧间隔。
- [第 9 章 ANR](src/part2-performance/ch09-anr/README.md)：系统判定应用没有在时限内完成输入、广播或服务回调。机制、Kernel Trace 联合诊断和典型路径。
- [第 10 章 内存性能](src/part2-performance/ch10-memory-perf/README.md)：从应用性能视角看 OOM、频繁 GC、换页和图形内存。先分清增长发生在哪类内存、谁持有、怎样变成可感知延迟。
- [第 11 章 功耗](src/part2-performance/ch11-power/README.md)：功耗速率和一段时间的耗电量。WakeLock、蓝牙扫描、后台执行和用户设置，时间窗口通常比卡顿更长。
- [第 12 章 网络性能](src/part2-performance/ch12-apk-network/README.md)：请求进入网络栈之后的排队、DNS、连接复用、TLS 和 `netd`。网络选择与 `NetworkCallback` 见 1.22。
- [第 13 章 渲染管线专题](src/part2-performance/ch13-rendering-pipelines/README.md)：View、SurfaceView、Vulkan、Compose、Flutter、WebView、Camera、视频 Overlay、游戏引擎和 XR。先确认谁生产 buffer、写入哪个 Surface、合成发生在哪一层。

### 第三部分：性能工具与方法论

怎么采集证据、读懂工具，以及怎样把一次调查写到能复查。

- [第 14 章 Perfetto](src/part3-tools/ch14-perfetto/README.md)：把渲染、输入、调度、Binder、I/O 和功耗放到同一条时间轴。目标是采到够用的数据，读懂 track / slice，并写成可复核的 SQL。
- [第 15 章 其他分析工具](src/part3-tools/ch15-other-tools/README.md)：Android Studio Profiler、simpleperf、HPROF、dumpsys、Battery Historian、GPU capture、Winscope 和 eBPF。Perfetto 覆盖不了的证据形态在这里。
- [第 16 章 方法论](src/part3-tools/ch16-methodology/README.md)：现象怎么定义，现有证据能证明什么，App、系统和测试环境各影响哪一段，修复后怎么验证。
- [第 17 章 APM 工具与性能监控生态](src/part3-tools/ch17-apm/README.md)：Firebase、Matrix、KOOM、LeakCanary、Benchmark 和崩溃 / ANR / 耗电采集机制。面向选型和实现，不替代第 14–16 章的线下分析。

### 第四部分：系统与厂商优化

平台和量产设备上还能改什么，以及不能把 AOSP 基线当成某台机器的行为。

- [第 18 章 AOSP 性能优化](src/part4-system/ch18-aosp/README.md)：系统服务、编译调试、Kernel 6.18、AutoFDO、Profile 安装编译和开机耗时。面向可以改系统代码的人。
- [第 19 章 OEM 与设备差异](src/part4-system/ch19-oem/README.md)：Power HAL、SoC、游戏模式、Media Performance Class，以及 Private Space、车机等产品形态。量产设备会叠加内核、固件和散热差异。

### 第五部分：应用性能实践

应用团队能改的启动、渲染、内存、I/O、功耗和线上观测。

- [第 20 章 应用稳定性治理](src/part5-app/ch20-stability/README.md)：Java / Native Crash、ANR、OOM、FD 和线程泄漏。保留能确定责任模块的日志、堆栈和版本信息。
- [第 21 章 启动优化](src/part5-app/ch21-startup/README.md)：进程创建、初始化、首帧和后台任务。冷 / 温 / 热启动、页面可见和业务可用要分开计时。
- [第 22 章 渲染优化实战](src/part5-app/ch22-rendering-practice/README.md)：布局、列表、Compose、动画、图片、WebView、CameraX 和 Media3。改动要放进当前刷新周期的帧预算里验证。
- [第 23 章 内存实践](src/part5-app/ch23-memory-practice/README.md)：Java Heap、泄漏、Native Heap、Bitmap 和端侧大模型预算。对象泄漏、分配过快和图形缓冲堆积，处理方式不一样。
- [第 24 章 I/O 与网络优化](src/part5-app/ch24-io-network/README.md)：文件、数据库、序列化、连接和缓存。把主线程阻塞、系统调用、协议往返和失败重试分开量，不要都写成“接口慢”。
- [第 25 章 功耗与包体积优化](src/part5-app/ch25-power-size/README.md)：后台任务、定位、音频、ADPF、热节流，以及 DEX / SO / 资源体积。同一设备和同一测试条件下比较改动前后。
- [第 26 章 应用可观测性](src/part5-app/ch26-observability/README.md)：崩溃上报、性能采集、线上排查和发布质量门禁。第 17 章讲 APM 怎么实现，这一章讲应用团队怎么把证据用起来。

附录目前保留 [性能分析 Checklist](src/appendix/analysis-checklist.md)。

## 作者

高建武（Gracker）。人在成都，做 Android 系统开发优化和应用侧的快、省、稳。完整介绍见 [作者简介](src/preface/about-author.md)。

- 博客：<https://www.androidperformance.com/>
- 知乎：<https://www.zhihu.com/people/gracker>
- 即刻：<https://okjk.co/pJbjFa>
- 微信公众号：AndroidPerformance
- 掘金：<https://juejin.cn/user/1816846860560749>
- Bilibili：<https://space.bilibili.com/213254842>
- 微信：553000664
- 邮箱：dreamtale.jg@gmail.com

## 支持这个项目

提 Issue、提 PR，或给仓库点 Star，都直接有用。

也可以打赏，用来给家里的猫豆豆买猫粮。码在 [支持这个项目](src/preface/support.md)，支付宝和微信都可以。

<table>
<tr>
<td align="center"><img src="src/preface/images/alipay.png" alt="支付宝赞赏码" width="200" height="200"><br>支付宝</td>
<td align="center"><img src="src/preface/images/wechat-pay.png" alt="微信支付码" width="200" height="200"><br>微信</td>
</tr>
</table>

## 贡献

欢迎开 Issue 或 Pull Request。错别字、失效链接、事实勘误可以直接 PR；新章节或大段重写请先开 Issue。

每天 11:40 和 19:40（Asia/Shanghai）会有定时任务读未分流的 Issue/PR：致谢、打标签、缺证据时会在评论里问。它不会改书，也不会合 PR。合并由维护者人工完成。规范见 [CONTRIBUTING.md](CONTRIBUTING.md)。

正文由 AI 辅助整理结构与初稿，技术判断和定稿由人工完成。

## License

正文和电子书可以公开阅读。社区使用按 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh-hans)：非商业转载和改编须署名，并保留相同许可。

出版、上架销售、收费培训、把正文打进付费产品，须取得版权人高建武（Gracker）的书面授权。克隆仓库或下载免费 EPUB 不等于获得出版权，也不等于放弃商业收益。说明见 [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md)，书里的摘要见 [许可说明](src/preface/license.md)。

仅下载仓库或 Knowledge Pack 不代表获得商业授权。SmartPerfetto 使用的公开
Knowledge Pack 收录规范章节目录中的所有正文，不以 `status`、`pipeline_stage`、
Task6/Task9 或 queue 状态作为门槛。各级 `README.md`、`SUMMARY.md` 和自动生成的
导航/分析产物不属于正文；私有路径行会在公开投影中脱敏，密钥命中会阻断发布。构建和分发规则见
[`knowledge-pack/policy.yaml`](knowledge-pack/policy.yaml)，Pack 再分发边界见
[`KNOWLEDGE-PACK-LICENSE.md`](KNOWLEDGE-PACK-LICENSE.md)。

> 注：本书引用的 AOSP 源码遵循 Apache License 2.0。引用他人内容均已标注原始出处，仅用于技术说明目的。
