#!/usr/bin/env python3
"""Add reviewed opening bridges to canonical articles that start abruptly.

Each paragraph states the article's decision boundary and reading path. The
mapping is intentionally explicit: this is editorial work, not title-based text
generation. Dry-run by default.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
H1_RE = re.compile(r"^#\s+.+?\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


OPENINGS = {
    "src/part1-fundamentals/ch01-architecture/15-android-ai-phone-ecosystem.md": "手机上的 AI 能力可能由系统服务、应用内运行时、云端模型或跨应用代理交付；接口名称相似，并不代表执行位置、数据边界和可用性相同。选型时应先确定能力由谁交付、模型在哪里运行、失败后由谁兜底，再比较具体 API。",
    "src/part1-fundamentals/ch01-architecture/23-bpf-observability-boundary.md": "Android 上“内核支持 BPF”不等于普通应用可以任意装载程序。可观测范围同时受内核配置、平台加载器、SELinux 与公开接口约束，排查时要把编译能力、系统已部署程序和应用可访问证据分开。",
    "src/part1-fundamentals/ch01-architecture/24-telephony-service.md": "Telephony 调用跨越应用进程、`system_server`、Phone 进程以及 Radio HAL，表面上的同步 API 背后可能包含多段 Binder 与异步基带交互。分析延迟或状态错乱时，应先定位请求和回调分别经过哪些进程，再判断等待发生在哪一段。",
    "src/part1-fundamentals/ch01-architecture/25-connectivity-service.md": "Connectivity 处理的不是单一“联网开关”，而是网络注册、能力验证、策略评分、默认网络切换和回调分发组成的状态机。排障时先区分物理链路、已验证网络与应用实际绑定的网络，才能解释回调顺序和切网延迟。",
    "src/part1-fundamentals/ch02-rendering/06-overdraw.md": "过度绘制只描述同一像素在一帧内被重复覆盖的程度，不能单独证明页面已经成为 GPU 瓶颈。有效优化需要把颜色提示与 Surface 拓扑、离屏渲染、带宽和实际帧时间一起验证，避免为了降低颜色层级破坏正确性。",
    "src/part1-fundamentals/ch02-rendering/08-window-manager.md": "WMS 决定窗口状态、层级、焦点和 Surface 拓扑，但它不直接完成应用内容绘制。理解窗口创建、`relayout`、StartingWindow 与过渡的边界，才能把启动白屏、尺寸跳变和动画卡顿定位到正确组件。",
    "src/part1-fundamentals/ch03-input/02-touch-performance.md": "触摸体验由采样、事件分发、应用处理、渲染和显示共同决定，单看回调耗时会漏掉前后两端。应先固定 input-to-display 的测量口径，再判断问题来自采样密度、批处理、主线程、帧调度还是显示提交。",
    "src/part1-fundamentals/ch03-input/04-gesture-recognition-performance.md": "手势识别既是状态机问题，也是事件所有权问题。优化前要先确认事件序列是否完整、由哪个 View 或识别器持有，再分析速度估计、阈值判断和自定义算法的 CPU 成本。",
    "src/part1-fundamentals/ch04-memory/04-app-memory-optimization.md": "内存优化的对象可能是泄漏、峰值、持续增长、频繁分配或系统压力下的存活能力，它们需要不同证据。先统一统计口径和复现场景，再沿对象所有权、分配调用栈与回收行为选择手段，不能只追求某一时刻的低 PSS。",
    "src/part1-fundamentals/ch04-memory/08-zram-compressed-swap-relaunch.md": "ZRAM 会用 CPU 换取匿名页的压缩驻留空间，但它既不能保证进程存活，也不能消除重新调页和解压的长尾。分析重启或恢复变慢时，应先区分进程被杀后的冷路径与存活进程的换入路径。",
    "src/part1-fundamentals/ch05-cpu-power/04-adpf.md": "ADPF 提供的是应用与系统之间的反馈接口，不是固定升频开关。应用需要用可解释的工作周期、容量余量和热状态驱动降级策略，并通过帧时间、能耗与温升复测系统是否做出了更合适的调度。",
    "src/part1-fundamentals/ch06-storage/01-storage-architecture.md": "一次应用 I/O 会跨越 API、文件系统、页缓存、块层和存储器件，任何一层都可能把短请求放大成长尾。阅读这条链路的目的，是把“磁盘慢”拆成可观测的缓存命中、回写、排队、同步和介质延迟。",
    "src/part1-fundamentals/ch06-storage/03-sharedpreferences-datastore.md": "`SharedPreferences.apply()` 只保证调用较快返回，并不等于写盘工作与主线程生命周期完全解耦；多进程一致性也不是它的契约。选用 SP 或 DataStore 时，应同时检查首次加载、写入收尾、序列化成本和数据所有权。",
    "src/part1-fundamentals/ch06-storage/04-vold-mediaprovider-fuse.md": "共享存储把挂载与权限控制面、文件数据面以及 MediaProvider 元数据管理叠在一起。定位 I/O 问题时，应先识别请求实际走的是直接文件、FUSE 还是 `ContentResolver` 路径，再分析跨进程与逐项访问成本。",
    "src/part2-performance/ch07-smoothness/08-hwc-overlay-composition-downgrade.md": "应用按时提交 buffer 后，显示链路仍可能因合成策略变化而迟到。排查 Overlay 降级要从具体 DisplayFrame 和 Layer 属性出发，验证 HWC 的 validate/present 决策，不能用固定 plane 数或单一 composition type 推断所有设备。",
    "src/part2-performance/ch08-responsiveness/03-launch-optimization.md": "启动优化应围绕用户可见关键路径安排初始化，而不是简单把任务全部异步化。先固定 TTID、TTFD 和业务可用点，再决定哪些工作必须前置、可以懒加载、适合并发，最后用依赖与资源争用验证收益。",
    "src/part2-performance/ch09-anr/05-notification-performance-anr.md": "通知发布会跨越应用构建、Binder 调用、系统服务处理、`RemoteViews` 加载和监听器分发，多处阻塞都可能最终表现为主线程超时。分析时应按调用方向和线程归属还原链路，而不是把所有通知 ANR 都归因于 NotificationManagerService。",
    "src/part2-performance/ch18-rendering-pipelines/08-flutter-rendering-pipeline.md": "Flutter 在 Android 上既遵循平台的 VSync、Surface 与合成规则，又有 Engine、Dart isolate 和 Impeller 自己的调度边界。定位掉帧时要先确认当前 RenderMode 和外部纹理路径，再把 UI、Raster、平台线程与显示帧对齐。",
    "src/part2-performance/ch18-rendering-pipelines/10-webview-rendering.md": "WebView 的一帧横跨应用 View 树、Chromium 多进程管线和 Android 合成系统，provider 版本还可能独立于平台版本更新。排查时应同时记录两套版本，并先确认当前走硬件 functor、软件 fallback 还是独立 Surface 路径。",
    "src/part2-performance/ch18-rendering-pipelines/11-camera-pipeline.md": "Camera 不是单 Producer 到单 Surface 的线性管线；同一 request 可以生成多个 buffer，并被预览、拍照、分析或编码消费者以不同节奏接收。诊断卡顿和时序问题时，要沿 request、result、buffer 与时间戳分别追踪。",
    "src/part2-performance/ch18-rendering-pipelines/13-game-engine.md": "游戏帧由输入采样、模拟、渲染提交、Surface 队列和显示合成共同组成，稳定帧间隔与最低延迟也可能互相牵制。分析时应以职责和依赖识别线程，而不是依赖某个引擎版本的线程名。",
    "src/part2-performance/ch18-rendering-pipelines/14-variable-refresh-rate.md": "VRR 改变的是显示刷新时刻的可调范围，不会取消应用提交 deadline，也不等同于简单切换离散刷新率模式。判断策略是否生效，需要同时检查应用帧率请求、系统 vote、显示能力与实际 present 节奏。",
    "src/part2-performance/ch18-rendering-pipelines/15-eyedropper-crossdevice.md": "EyeDropper 的公开契约、Android 17 AOSP 实现和厂商跨设备能力不是同一层承诺。接入前应先限定可用设备、颜色返回语义和取消路径，再评估截图、合成、IPC 或远端协作带来的成本。",
    "src/part2-performance/ch18-rendering-pipelines/16-android-xr-spatial-ui-rendering.md": "空间 UI 的性能预算不只包含传统 2D 布局与绘制，还包括姿态更新、双目显示、3D 资产和运行时合成。应先区分 Android XR 平台、Jetpack XR SDK 与设备运行时各自负责的阶段，再为资源加载和每帧更新建立预算。",
    "src/part3-tools/ch13-perfetto/05-input-latency-sql.md": "输入延迟 SQL 的关键不是拼出一张大表，而是先选定事件身份、时间窗口和终点语义。只有把 InputDispatcher 队列、应用消费与 FrameTimeline 的 token 关系对齐，计算出的 input-to-display 延迟才可复查。",
    "src/part3-tools/ch14-other-tools/01-as-profiler.md": "Android Studio Profiler 适合从应用视角快速关联 CPU、内存、网络和能耗信号，但不同采集模式的开销与时间精度差异很大。使用前应按问题选择任务入口，并明确何时需要转向系统级 Perfetto 证据。",
    "src/part3-tools/ch14-other-tools/04-dumpsys.md": "`dumpsys` 提供的是各系统服务在某一时刻或一段累计周期内的内部状态，适合快速缩小范围，不等同于完整时间线。调用每个子命令前要确认统计窗口、重置行为和字段口径，再与 trace、日志或复现步骤交叉验证。",
    "src/part3-tools/ch14-other-tools/17-r8-configuration-analyzer.md": "R8 体积问题常由多条 keep 规则叠加造成，只看最终 APK 无法回答是哪条配置保留了哪些符号。Configuration Analyzer 的作用是建立规则到保留结果的因果链，再按功能正确性和体积收益逐条收窄。",
    "src/part3-tools/ch15-methodology/02-system-vs-app.md": "“系统问题”与“App 问题”不是互斥标签：应用可能触发系统等待，系统压力也可能放大应用关键路径。归因应从同一延迟窗口出发，用线程状态、Binder、内存回收和显示证据确定控制权与可修复边界。",
    "src/part3-tools/ch15-methodology/04-competitive-analysis.md": "竞品对比只有在场景、设备状态、版本和指标口径一致时才有解释力。目标不是得出笼统排名，而是找出差异发生在哪个用户阶段，并用可重复实验判断哪些设计可迁移。",
    "src/part3-tools/ch15-methodology/05-testing-best-practices.md": "性能测试测量的是受设备、温度、后台负载和数据状态影响的分布，而不是一个永远稳定的数字。先写清场景、环境、采样和判定合同，才能让回归门禁区分真实劣化与测量噪声。",
    "src/part3-tools/ch15-methodology/06-aosp-reading.md": "源码阅读应由具体运行证据驱动：先固定平台 tag、模块和调用入口，再沿日志、trace 或 Binder 接口向上下游展开。这样得到的是可验证的实现解释，而不是在当前主干代码中寻找一个可能不存在于目标设备的答案。",
    "src/part3-tools/ch15-methodology/07-google-android-bench-ai-coding-evaluation-methodology.md": "Android Bench 的分数取决于任务数据、执行环境、verifier 和统计方法，不能脱离方法版本直接比较。理解一次任务如何构建、运行和判定，是解释 pass@1 以及复现实验结果的前提。",
    "src/part3-tools/ch19-apm/05-open-source-apm-history.md": "这些历史项目的依赖和界面未必适合直接接入现代 Android，但它们保留了卡顿监控、插件化采集和调试看板的典型取舍。阅读重点应放在可迁移的机制、已经过时的假设以及迁移成本。",
    "src/part3-tools/ch19-apm/06-jankstats-framemetrics.md": "JankStats 和 FrameMetrics 都提供应用窗口的帧级信号，但覆盖版本、字段语义和归因能力不同。选择工具前要明确需要的是线上轻量检测、平台时长分解还是系统级因果分析，并用设备刷新率校准阈值。",
    "src/part4-system/ch16-aosp/05-profile-dm-sdm-install-compilation.md": "Profile、Dex Metadata 与 Secure Dex Metadata 分属不同交付和校验阶段，名称接近却不能互换。要判断安装编译收益，应沿安装会话、ART Service 和运行时消费路径确认元数据何时被接受、验证并实际使用。",
    "src/part4-system/ch16-aosp/07-appflow-large-app-cold-launch-memory-scheduling.md": "GB 级应用冷启动会同时竞争文件页、匿名页、CPU 与进程生存空间，单点预读可能把延迟转移成更强的内存压力。AppFlow 的价值和边界需要从论文证据出发，分别审视预加载、回收和杀进程策略如何协同。",
    "src/part4-system/ch16-aosp/08-rust-system-services-performance.md": "Rust 能减少部分内存安全风险，但不会自动消除 Binder、FFI、分配或调度成本。评估平台 Rust 服务时，应把语言运行时、CXX 边界、错误处理和 Soong 构建配置拆开，并以目标进程的实际调用路径验证。",
    "src/part4-system/ch17-oem/02-soc-differences.md": "SoC 型号只能提供硬件拓扑的起点，最终性能还受设备散热、内存配置、内核和厂商策略影响。跨平台分析应把 CPU、GPU、加速器、内存与调度证据分别对齐，避免用品牌或核心名称替代实测。",
    "src/part4-system/ch17-oem/05-private-space-app-lock-boundary.md": "Private Space、工作资料、厂商应用锁和应用自身认证属于不同隔离模型，生命周期、可见性与通知行为不能类推。兼容性设计要先确认系统身份边界，再检查启动、分享、最近任务和 URI 授权链路。",
    "src/part5-app/ch22-rendering-practice/06-webview-optimization.md": "WebView 页面性能由实例初始化、Chromium 渲染、资源加载和页面脚本共同决定，单改某一端通常只能移动瓶颈。应先按业务可见节点拆分时间线，再针对进程预热、缓存、Bridge 和前端执行分别治理。",
    "src/part5-app/ch22-rendering-practice/10-adaptive-layout-multi-form-factor.md": "自适应布局应响应当前窗口和姿态，而不是猜测设备类别；桌面窗口、折叠状态和旋转都可能在运行中改变可用空间。把尺寸决策集中在页面入口，并限制重组与重新布局范围，才能同时保证正确性和性能。",
    "src/part5-app/ch22-rendering-practice/12-adaptive-refresh-rate.md": "应用能表达内容期望帧率，但最终刷新节奏仍由窗口、Surface、系统策略和显示能力共同决定。接入时要让请求贴近实际更新源，并通过 FrameTimeline 与显示模式验证，而不是只检查 API 调用成功。",
    "src/part5-app/ch23-memory-practice/02-bitmap-optimization.md": "图片内存取决于解码尺寸、像素格式、存储位置、生命周期和缓存策略，文件体积不能直接代表运行时占用。优化顺序应从限制目标尺寸开始，再用大图监控、复用与 Hardware Bitmap 处理不同场景。",
    "src/part5-app/ch23-memory-practice/05-large-heap-multiprocess.md": "`largeHeap` 与多进程都可能扩大单个故障前的可用空间，却会引入更高系统压力、跨进程成本和回收不确定性。只有在对象所有权、进程生命周期和设备预算已经量化后，才适合把它们作为架构选择。",
    "src/part5-app/ch23-memory-practice/06-memory-monitoring.md": "线上内存治理需要区分泄漏、峰值、持续增长和系统回收风险，并把每个信号关联到版本、场景和设备分层。采集方案既要统一 PSS、RSS、Java 与 Native 口径，也要控制快照成本和隐私边界。",
    "src/part5-app/ch24-io-network/10-bluetoothsocket-read-disconnect.md": "阻塞中的 `BluetoothSocket.read()` 以 EOF、异常或数据返回来表达连接状态，业务层不能把任一结果简单等同于可立即重连。可靠长连接需要把读写线程、关闭顺序、状态机和退避预算放在同一套治理中。",
    "src/part5-app/ch25-power-size/04-location-sensor.md": "定位与传感器功耗主要由采样频率、精度、批处理、唤醒和后台持续时间决定。优化时应从业务所需的新鲜度和准确度反推请求参数，再用系统记录验证硬件活动是否真正减少。",
    "src/part5-app/ch25-power-size/06-app-bundle-delivery.md": "按需分发把安装包体积问题转化为模块边界、下载时机和失败恢复问题。设计 AAB、Dynamic Feature 或资源包时，应同时考虑商店能力、首用路径、离线场景和版本兼容，而不只比较基础 APK 大小。",
    "src/part5-app/ch25-power-size/07-hybrid-webview-power.md": "Hybrid 页面的能耗来自 WebView 进程、JavaScript、网络、媒体和原生桥接的共同活动，技术栈名称本身不能预测功耗。原生化决策应基于同场景测量，先定位持续 CPU、唤醒和数据传输，再比较改造成本。",
    "src/part5-app/ch25-power-size/10-application-cpu-optimization.md": "应用 CPU 优化要同时回答谁在运行、为何运行以及运行是否位于用户关键路径。线程池、预加载和周期任务都可能把平均利用率换成更高峰值或更差调度，必须结合调用栈、线程状态和设备约束复测。",
    "src/part5-app/ch25-power-size/11-thermal-throttling-performance.md": "热节流是设备维持安全温度的动态控制结果，不同机型的阈值和降级动作不会完全一致。应用应把 thermal status 与 headroom 当作趋势信号，提前降低可选工作，并用持续性能而非瞬时峰值验收。",
    "src/part5-app/ch26-observability/04-ab-testing-regression.md": "性能实验既要识别平均收益，也要防止长尾、设备分层或业务指标被掩盖。发布阶段应预先定义随机化单位、样本比例、护栏和回归阈值，并把异常归因到同一版本与场景。",
}


def insert_opening(path: Path, paragraph: str) -> str:
    original = path.read_text(encoding="utf-8")
    if paragraph in original:
        return original
    lines = original.splitlines()
    fenced = False
    h1_index = None
    for index, line in enumerate(lines):
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        if not fenced and H1_RE.match(line):
            h1_index = index
            break
    if h1_index is None:
        raise ValueError(f"missing H1: {path.relative_to(ROOT)}")
    insert_at = h1_index + 1
    while insert_at < len(lines) and not lines[insert_at].strip():
        insert_at += 1
    revised = lines[: h1_index + 1] + ["", paragraph, ""] + lines[insert_at:]
    ending = "\n" if original.endswith("\n") else ""
    return "\n".join(revised) + ending


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    changed = 0
    for rel, paragraph in OPENINGS.items():
        path = ROOT / rel
        if not path.exists():
            raise FileNotFoundError(rel)
        revised = insert_opening(path, paragraph)
        if revised == path.read_text(encoding="utf-8"):
            continue
        changed += 1
        print(rel)
        if args.apply:
            path.write_text(revised, encoding="utf-8")
    mode = "applied" if args.apply else "dry-run"
    print(f"{mode}: {changed} opening bridges")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
