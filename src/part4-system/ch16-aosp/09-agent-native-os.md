---
title: AOHP：将 Android 改造为 Agent 原生 OS
chapter: '16.9'
section: '16.9'
status: ready-for-review
applicable_versions: Android 16 (API 36) - Android 17 (API 37)
last_verified: '2026-08-14'
last_verified_against: arXiv 2606.23449v1; AOHP aohp b8ab9e98, platform_frameworks_base a2d4a80b, platform_system_core d1fc184b; AOSP android-17.0.0_r1 and API 37 docs
confidence: medium
consolidated_from:
- src/part1-fundamentals/ch05-cpu-power/5.21-cross-app-agent-system-primitive.md
sources:
- type: paper
  path: https://arxiv.org/abs/2606.23449
  note: 'AOHP: An Open-Source OS-Level Agent Harness for Personalized, Efficient and Secure Interaction'
- type: obsidian
  path: 论文/Android-2026-07-09-AOHP-Agent-Native-Android/03-精读.md
- type: repository
  path: https://github.com/aohp-os/aohp
- type: source
  path: https://github.com/aohp-os/platform_frameworks_base/blob/a2d4a80ba16211ac73eee4baf6e73d6c7ba669fe/services/core/java/com/android/server/aohp/AohpVirtualDisplayService.java
- type: source
  path: https://github.com/aohp-os/platform_frameworks_base/blob/a2d4a80ba16211ac73eee4baf6e73d6c7ba669fe/services/core/java/com/android/server/aohp/AohpEventStreamService.java
- type: source
  path: https://github.com/aohp-os/platform_frameworks_base/blob/a2d4a80ba16211ac73eee4baf6e73d6c7ba669fe/services/core/java/com/android/server/aohp/AohpSecurityBridgeService.java
- type: source
  path: https://github.com/aohp-os/platform_frameworks_base/blob/a2d4a80ba16211ac73eee4baf6e73d6c7ba669fe/services/core/java/com/android/server/aohp/AohpVaultService.java
- type: source
  path: https://github.com/aohp-os/platform_frameworks_base/blob/a2d4a80ba16211ac73eee4baf6e73d6c7ba669fe/services/core/java/com/android/server/aohp/AohpTaintTrackerService.java
- type: source
  path: https://github.com/aohp-os/platform_frameworks_base/blob/a2d4a80ba16211ac73eee4baf6e73d6c7ba669fe/services/core/java/com/android/server/aohp/AohpContainerService.java
- type: source
  path: https://github.com/aohp-os/platform_frameworks_base/blob/a2d4a80ba16211ac73eee4baf6e73d6c7ba669fe/services/core/java/com/android/server/aohp/AohpFileBridgeService.java
- type: source
  path: https://github.com/aohp-os/platform_frameworks_base/blob/a2d4a80ba16211ac73eee4baf6e73d6c7ba669fe/services/accessibility/java/com/android/server/accessibility/AohpUiTreeDumper.java
- type: source
  path: https://github.com/aohp-os/platform_frameworks_base/blob/a2d4a80ba16211ac73eee4baf6e73d6c7ba669fe/services/core/java/com/android/server/aohp/AohpUiTreeSanitizer.java
- type: source
  path: https://github.com/aohp-os/aohp/blob/b8ab9e98a2bd51f7fbd01a95d3b45dca078c5884/skills/aohp-sandbox/SKILL.md
- type: source
  path: https://github.com/aohp-os/platform_system_core/blob/d1fc184b0a138a5a1b1da70512516cd2406980d9/aohp-containerd/container_manager.cpp
- type: official
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/appfunctions/AppFunctionManager.java
- type: official
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/appfunctions/java/com/android/server/appfunctions/AppFunctionManagerService.java
- type: official
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/appfunctions/java/com/android/server/appfunctions/ServiceConfigImpl.java
- type: official
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/packages/NeuralNetworks/framework/module/java/android/app/ondeviceintelligence/OnDeviceIntelligenceManager.java
- type: official
  path: https://developer.android.com/ai/appfunctions
- type: official
  path: https://developer.android.com/reference/android/app/appfunctions/AppFunctionManager
- type: official
  path: https://developer.android.com/reference/android/app/appfunctions/package-summary
- type: official
  path: https://developer.android.com/reference/android/hardware/display/DisplayManager
- type: official
  path: https://source.android.com/docs/core/display/multi_display/activity-launch
- type: paper
  path: https://www.usenix.org/conference/osdi10/legacy-presentation/taintdroid-information-flow-tracking-system-realtime-privacy
tags:
- agent-os
- aohp
- ai-agent
- android-architecture
- information-flow-security
- virtual-display
related_chapters:
- '1.17'
- '4.10'
- '5.5'
- '13.11'
---

# AOHP：将 Android 改造为 Agent 原生 OS

AOHP（Android Open Harness Project）是一套基于 AOSP fork 的研究原型。fork 是从 AOSP 分出的独立源码分支，不代表这些改动已经进入标准 Android。

本文沿用 agent 这个术语，指能观察环境、调用工具并连续执行多步任务的 AI agent（智能体）。
AOHP 为它提供 OS-level harness，也就是由系统服务、接口和策略组成的运行支架。
AOHP 把能力调用、策略检查和审计放进系统控制面；这里的控制面负责决定“谁能调用什么、数据可流向哪里”。

论文与开源仓库都把 AOHP 标为早期研究项目，不适合生产环境或高安全场景。

证据分为四类，阅读时要保持边界：

- **论文设计**：来自 arXiv 2606.23449 v1，说明作者提出的架构和实验；
- **AOHP 实现**：framework 结论固定到 `a2d4a80b...`，container daemon 固定到 `d1fc184b...`，说明当前原型已经写出的机制；
- **Android 17 对照**：来自 `android-17.0.0_r1` 和 API 37 文档，说明标准平台提供什么；
- **工程判断**：依据前述证据推导的接入建议，不能冒充平台行为。

> [!NOTE]
> AOHP 没有进入 Android 17。AOHP 仓库以 Android 16 QPR2 作为构建基线；
> 标准平台对照为 Android 17 / API 37 / `android-17.0.0_r1`。AOHP 自己的 framework fork 不能当作 Android 17 源码。

## 1. AOHP 要解决什么问题

传统 Android 以应用 UID、组件和用户可见界面组织能力。
这个模型适合人直接操作应用，但 agent 的工作方式多了几个系统过去无需统一处理的维度：

| 维度 | 标准应用交互 | agent 工作负载带来的变化 |
| --- | --- | --- |
| 能力入口 | Activity、Service、Provider、Intent 和应用内 UI | 一次任务可能跨多个应用、CLI、文件和服务 |
| 观察形式 | 像素与面向人的语义 | agent 更适合结构化、可定位、可验证的状态 |
| 生命周期 | 前台交互、受控后台执行 | agent 可能等待事件、并行处理多个子任务 |
| 授权对象 | 权限授给应用或角色 | 数据可能继续进入模型上下文、工具和外部服务 |
| 审计单位 | 组件调用、AppOps、网络或文件访问 | 还需解释一次任务中数据从 source 到 sink 的传播 |

信息流语境中的 source 是数据进入任务的位置，sink 是数据离开受控范围或触发动作的边界。
例如，联系人地址是 source，上传接口或支付确认是 sink。

标准 Android 已有 Binder、权限、AppOps、URI grant、Keystore、Accessibility、VirtualDisplay 和后台执行规则。
AppOps 是系统对敏感操作做运行时记录与限制的机制，URI grant 则把某个 `content://` 对象的临时访问权交给指定组件。

缺口集中在跨工具的任务语义、数据传播和 agent 专用控制面。AOHP 选择修改 framework 与系统服务，把这些能力放到统一 harness 中。

论文把方案归为三部分：

1. **个性化服务组合**：从 API、CLI、结构化 UI 和 GUI 中发现能力，按用户任务生成入口；
2. **高效 agent 接口**：用虚拟显示、结构化 UI、文件对象、事件流和本地执行环境减少 GUI 往返；
3. **安全信息流**：在 agent 看到数据前把敏感明文替换为不透明引用，并在输入、输出和敏感动作处执行策略。

“OS 级”在这里有明确含义：AOHP 修改 `frameworks/base`、`system/core`、SELinux policy、Launcher3 和 system app。
普通 APK 安装几项公开 API 无法复制同等权限。

## 2. 从论文架构到代码路径

### 2.1 四层模型

AOHP 论文从下到上划分四层：

| 层 | 职责 | 典型对象 |
| --- | --- | --- |
| Android 兼容层 | 继续运行现有应用、系统服务和硬件 | Activity、Binder、Display、文件、传感器 |
| 统一交互层 | 归一化 agent 能调用的接口 | API、CLI、Structured UI、Rendered GUI |
| AOHP 能力层 | 管理可复用状态和执行能力 | system memory、skills、UI utilities |
| 服务组合层 | 围绕任务生成用户入口 | task schema、service graph、presentation policy |

这里的 system memory 指 OS 管理的偏好与任务状态，不是物理内存；skill 指可复用的能力描述和执行步骤。
task schema 规定任务输入，service graph 描述服务发现与组合，presentation policy 决定结果的呈现方式。

这是一张研究架构图，不代表每个框都具有稳定 API。
仓库中的 `AohpVirtualDisplayService`、`AohpEventStreamService`、`AohpContainerService`、`AohpFileBridgeService`、`AohpVaultService` 和 `AohpSecurityBridgeService` 提供了可追踪的实现入口。

服务组合质量仍依赖 skill 描述、应用适配和 agent 规划。

### 2.2 生成式服务入口

论文中的 generated entrance 是围绕当前任务生成的用户入口，不是 Android 已有的组件类型。它包含三个要素：

- **task schema**：任务字段契约，包括目标、输入和完成条件；
- **service graph**：API、CLI、GUI 或 skill 之间的依赖与执行关系；
- **presentation policy**：决定哪些结果展示给用户，哪些中间状态留在任务内部。

能力描述需要输入/输出 schema、前置条件、副作用和策略标签。
搜索商品可以并行执行，付款和外发敏感文件则要经过确认。
这个划分有助于把“会读取数据”和“会改变外部状态”分开。

AOHP 允许 legacy 应用通过 GUI 或结构化 UI 参与。
legacy 在这里指没有为 AOHP 或 AppFunctions 专门改造的既有应用。
它们的能力发现仍处于研究阶段，论文把更强的自动推断列为后续工作。
工程文档不应把任意页面描述成已经自动转换成可靠函数。

### 2.3 跨服务记忆

论文把记忆分为三类：

| 类型 | 作用域 | 风险控制 |
| --- | --- | --- |
| 持久 profile | 跨任务偏好 | 可审计、可撤销、限制用途 |
| task-local | 当前任务的候选项和中间状态 | 任务结束后清理 |
| sensitive memory | 地址、支付凭据等私密值 | 由 vault token 间接引用 |

这里的 profile 是长期偏好档案，不是性能 profile；task-local 表示状态只在当前任务内有效。
vault token 是对敏感明文的间接引用，后文会说明当前实现的限制。

这套 memory 是论文中的 OS 管理状态，不等于 LLM context window。context window 是一次模型请求可容纳的输入范围，也不等于跨任务持久存储。

它也不等于 Android 17 的 `OnDeviceIntelligenceManager`。
后者在标准 AOSP 17 中是受权限管理的 `@SystemApi` 推理服务接口，部分能力还受 feature flag（功能开关）约束。
API 37 公开文档没有 `FoundationModelManager` 这一平台类，`OnDeviceIntelligenceManager` 也没有定义 AOHP 的跨应用记忆协议。

## 3. 高效 agent 接口的实现边界

### 3.1 虚拟显示与后台交互

Android 公共 `DisplayManager.createVirtualDisplay()` 从早期版本就已存在。
公共 API 创建的 display 默认是 private、non-secure：private display 主要限制其他 UID 在其上放置 Activity，non-secure display 不能显示受 `FLAG_SECURE` 保护的内容。
安全显示、自动镜像、可信显示和输入注入还受系统权限限制。

因此，创建一个 `VirtualDisplay` 不会自动获得以下能力：

- 在后台随意启动其他应用 Activity；
- 绕过 private display 的 UID 放置规则；
- 读取 `FLAG_SECURE` 窗口；
- 向任意应用注入输入；
- 豁免进程冻结、后台启动、前台服务和资源限制。

AOHP 通过 `signature|privileged` 权限 `MANAGE_AOHP_VIRTUAL_DISPLAY` 和 framework 内部接口扩展了这条路径。
这类权限只会授予使用系统签名或位于特权分区且进入许可名单的应用。
下面的源码片段说明原型默认创建的 display flag：

```java
effectiveFlags = DisplayManager.VIRTUAL_DISPLAY_FLAG_PUBLIC
        | DisplayManager.VIRTUAL_DISPLAY_FLAG_OWN_CONTENT_ONLY
        | DisplayManager.VIRTUAL_DISPLAY_FLAG_TRUSTED
        | DisplayManager.VIRTUAL_DISPLAY_FLAG_SUPPORTS_TOUCH;
effectiveFlags |= DisplayManager.VIRTUAL_DISPLAY_FLAG_OWN_FOCUS;
```

`PUBLIC` 允许其他 UID 的 Activity 按策略进入 display，`OWN_CONTENT_ONLY` 禁止在无内容时回退到默认屏幕镜像，`TRUSTED` 表示系统可把受限内容放到这个可信 display，`SUPPORTS_TOUCH` 声明它支持触摸，`OWN_FOCUS` 则给它独立输入焦点。
这些 flag 仍依赖系统权限与内部 display policy；`SUPPORTS_TOUCH` 本身不会授予调用方输入注入权限。

`AohpVirtualDisplayService` 还通过 `DisplayManagerInternal` 创建 display，保存 owner UID 与 session，并用 system_server 内部 Activity 启动路径把应用放到目标 display。
session 是一次虚拟显示会话，owner UID 是拥有和管理它的调用方。
普通应用调用公共 `VirtualDisplay` API 得不到这组能力。

AOHP 为每个虚拟显示挂接一个 RGBA 像素格式的 `ImageReader`，将 `maxImages` 设为 3，并在后台线程持续获取和关闭最新帧。
`maxImages` 限制同时被获取且尚未释放的 image 数量，不代表系统长期保存 3 张截图。

这个 `ImageReader` 向 display 暴露一个 producer surface，也就是显示帧写入缓冲队列的端点，避免 display 因没有输出 surface 而进入 `STATE_OFF`。`ImageReader` 在另一端消费并及时关闭这些帧。
代价仍然存在：WindowManager、SurfaceFlinger、应用进程、图形 buffer、GPU 合成和输入分发都要工作。

论文没有报告虚拟显示的 CPU、GPU、内存、thermal 和能量开销，并把资源调度列为 future work。工程评估至少要记录：

- 同时运行的 display、task 和应用进程数量；
- `ImageReader` buffer、图形内存、PSS（按共享页比例折算后的进程内存占用）与 LMKD（Android 的低内存回收守护进程）压力；
- SurfaceFlinger layer、GPU busy、帧率和无效重绘；SurfaceFlinger 是 Android 的显示合成服务，layer 是它管理的合成图层；
- agent 与前台用户争用 CPU/GPU 时的延迟；
- screen-off、Doze、thermal throttling（过热降频）与进程冻结行为；
- display 销毁、应用崩溃和 session owner 退出后的清理；session owner 指创建并持有这次会话的调用方。

### 3.2 Structured UI

AOHP 的 Structured UI（SUI）从 Android accessibility tree（可访问性节点树）导出节点类型、文本、层级、resource ID、可操作性、bounds 和 display 信息。
resource ID 是应用为 View 声明的资源标识，bounds 是节点在屏幕上的矩形坐标。
相比截图，这种表示省去了纹理、阴影和其他像素细节。

仓库中的 `AohpUiTreeDumper` 负责导出树，`AohpUiTreeSanitizer` 在结果进入 agent 视野前处理敏感字段。
当前 sanitizer 依赖应用声明，并用手机号、银行卡号等少量启发式规则补充识别，不能据此宣称覆盖所有敏感文本。

SUI 不能覆盖全部 Android UI：

- Canvas、OpenGL、游戏引擎和视频可能没有完整语义节点；
- WebView、Compose 和自定义 accessibility semantics 的质量取决于应用；semantics 是应用暴露给辅助功能与自动化工具的节点语义；
- 节点树与屏幕像素可能处在不同帧；
- resource ID、文本和 bounds 会随版本、语言和布局改变；
- 登录、支付、验证码等界面可能主动限制自动化。

因此，SUI 适合作为结构化观察通道，GUI 则是节点语义不足时的兼容回退。
执行动作后仍要验证目标状态，不能把“命令返回成功”当成业务完成。

### 3.3 Event Stream

论文的 Event Stream 覆盖瞬态 UI 事件和传感器流。
当前 framework 源码中，`AohpEventStreamService` 对 Toast、notification posted 和 notification removed 提供 session buffer，也就是按会话保存的短期事件队列：

- 默认上限 200 条，可配置范围为 1–2000；
- 默认 TTL 10 分钟，可配置范围为 10 秒到 1 小时；TTL（time to live）是事件在缓冲区中的保留时限；
- `register`、`drain`、`unregister` 管理消费生命周期；
- notification 的 display 归属只能尽力推断，因为 Android notification 天生不属于某个 display；
- 可附带事件时截图，但 inline screenshot 受 2 MiB 上限约束；inline 表示把 Base64 图片直接嵌进事件 JSON。

AOHP 在 NotificationManagerService、SystemUI 和 Toast 路径加入 system_server hook；
这里的 hook 是插入原有系统路径的回调点。这种实现不能用第三方 `NotificationListenerService` 等价复制。
标准应用使用后者时仍要用户授予通知访问权，也无法依靠该 API 完整捕获其他应用 Toast。

事件流比轮询更省 agent 往返，但还要处理积压、重复、乱序、过期和敏感字段。
消费者应保存 event ID 或时间戳，并把动作设计为幂等：同一事件被重复处理时，不会重复付款或重复发送。
还要区分“缓冲区暂时无事件”和“session 已过期”。

### 3.4 文件桥

AOHP 把 GUI 产生的文件与 CLI/API 消费的文件归一成任务对象。
这个设计减少 agent 从截图猜测路径的行为，但实现依赖 privileged file bridge，也就是具有系统权限的文件转接服务，以及相应的策略检查。

标准 Android 应用之间传文件时，优先使用 Storage Access Framework（系统文件选择框架）、`ContentProvider`/`FileProvider`、`content://` URI 与临时 URI grant。
grant 是针对具体 URI 和目标组件的临时读写凭证。

共享存储绝对路径还会受到 scoped storage（分区存储）、用户选择、MIME type、provider 生命周期和目标应用支持的影响，不能笼统写成“比 Intent 更可靠”。

一个可审计的文件交接至少记录：

- source provider、URI、MIME type、长度和内容摘要；
- grant 的读写方向、目标 package 与过期时间；
- 文件是否包含 vault token 或敏感派生内容；
- 目标动作是否会上传、分享、覆盖或删除；
- 操作完成后 grant 和临时文件怎样回收。

### 3.5 本地沙箱

AOHP 的 `AohpContainerService` 通过 init 创建的 Unix domain socket 与设备侧 daemon 通信。
domain socket 是同一设备上进程间通信的本地端点，daemon 是在后台处理容器命令的 native 进程。
当前 CLI 把执行环境描述为 Linux chroot sandbox，skill 文档还说明这些 sandbox 共享设备 network namespace（网络命名空间）。

固定到 `d1fc184b...` 的 daemon 实现会尝试 `unshare(CLONE_NEWNS)` 创建独立 mount namespace，进入每个 sandbox 的 cgroup，再执行 `chroot()`。
mount namespace 隔离挂载视图，cgroup 负责资源计量与上限；代码在 namespace 创建失败时会继续使用宿主挂载视图。

init 配置让 daemon 以 root 和多项 Linux capability 启动，当前子进程路径没有再执行 `setuid()`/`setgid()` 降权。
capability 是拆分后的 root 特权，seccomp 是系统调用过滤器。
结合共享 network namespace 可知，这套实现已有文件系统视图、挂载和资源分组机制，但没有形成强身份与网络隔离。

chroot 只改变路径解析根目录，本身不是完整安全边界。
评价“可安全执行 agent 代码”时还要核对 UID/GID、SELinux domain、mount namespace 失败路径、capability、seccomp、cgroup、网络出口、设备节点和凭据挂载。
当前原型适合受控 Cuttlefish/userdebug 实验，不能直接负责不可信代码的生产隔离。

## 4. 安全信息流：设计目标与原型现状

### 4.1 论文提出的处理流程

论文的敏感数据路径可以拆成六步：

1. source 被声明或启发式规则识别为敏感；
2. 明文进入 agent context 前替换为 typed placeholder；
3. vault 保存明文与 token 的映射；
4. agent 只携带 token 提交操作意图；
5. trusted executor 检查 source、purpose、destination、action 与 consent；
6. sink 前执行放行、确认或拒绝，并写审计记录。

typed placeholder 是带有数据类别但不含明文的占位引用，例如 `<home-address:uuid>`。
trusted executor 是获准解析引用并执行敏感操作的系统组件，consent 则是绑定 source、用途、目的地和动作的用户确认。

这套模型试图控制“数据已经交给某个 agent 后又流向哪里”。
Android 的运行时权限主要回答某个 UID 能否访问资源，URI grant 主要回答某个组件能否访问一个对象；
两者不会自动理解 LLM prompt、tool result 或跨工具派生数据。

### 4.2 当前 vault 是内存 token 表

AOHP framework commit `a2d4a80b...` 中，`AohpVaultService` 明确把实现标为 in-memory，核心状态如下：

```java
private static final String PREFIX = "aohp://vault/";
private final Map<String, Entry> mEntries = new ConcurrentHashMap<>();
```

`Entry` 直接保存 plaintext（明文）、category、source package 和创建时间。
进程重启后映射会消失；当前类没有持久加密、硬件密钥绑定、用户切换隔离、自动过期和 secure erase（可验证安全擦除）机制。

token 的不透明性可以减少 agent 直接接触明文，但不能单独证明 vault 达到了凭据存储的安全要求。

### 4.3 当前 taint tracker 不是全系统动态污点传播

taint 在这里表示附在数据上的来源与敏感级别标记，也称 provenance metadata，不表示数据已损坏。
`AohpTaintTrackerService` 为 vault token 建立 `taintId`，记录 source app、category、sensitive 标志和时间。

`AohpUiTreeSanitizer` 会在 UI 字段替换为 vault token 时注册该元数据，security bridge 再在输入、tap、skill output、file share 等选定边界执行检查。

这与 TaintDroid 的运行时数据传播粒度不同。
当前 AOHP 类没有在 Java/ART 指令、native 内存、Binder payload、文件内容和任意字符串变换中自动传播标签。
把它写成“每一次 LLM 请求、每一个工具输入输出都自动携带 taint”会超过源码证据。

TaintDroid 是 2010 年 OSDI 论文中的 Android 研究原型，修改 Dalvik 和系统路径实现多粒度动态 taint tracking。
它没有成为 Android 标准安全组件，因此“后来被 Google 从 AOSP 移除”的说法不符合其演进历史。
AOHP 论文引用的是这一研究方向。

### 4.4 策略检查与已知缺口

`AohpSecurityBridgeService` 已实现或部分实现：

- UI tree 敏感字段替换；
- vault token 输入前的 sink 校验；
- 敏感 tap 和输入的 consent；
- skill input/output 策略；
- file share 检查；
- audit log 与 fail-closed 异常路径；fail closed 表示检查异常或策略缺失时默认拒绝。

源码也保留了清晰的未完成边界。下面的返回值用于文件读写策略尚未实现时拒绝请求：

```java
o.put("mode", "DENY");
o.put("stub", true);
o.put("reason", "file_read_policy_not_implemented");
```

这段代码说明原型愿意在缺少策略时 fail closed，但文件读写的信息流控制还没有完成。
安全报告应逐个 sink 标明 implemented（已实现）、partial（部分实现）、stub（仅占位）或 unobserved（未观测），不能用论文架构图覆盖代码缺口。

### 4.5 五个 security case 怎样解读

论文在一个带敏感标注的支付应用上测试五类行为：敏感显示替换、普通动作放行、敏感动作确认、未支持访问拒绝、敏感事件脱敏。
五项均通过，能够证明这五个测试用例在该原型与该应用中按预期运行。

这些结果尚不能证明：

- 对任意第三方应用的字段识别完整；
- 隐式流、native code、截图像素和 side channel（侧信道）都被跟踪；
- prompt injection（把外部数据伪装成指令的提示注入）无法诱导已授权动作；
- 用户审批不会被混淆、疲劳或界面覆盖攻击影响；
- vault 在重启、多用户、备份和设备失窃场景安全；
- framework service 不存在提权、绕过或 denial-of-service（拒绝服务）问题。

## 5. 实验数据：数字成立在哪个范围

### 5.1 任务完成率

论文使用 OpenClaw 作为 agent 执行框架，并设计了 30 个移动任务。
任务覆盖 GUI、非 GUI、事件捕获、多源检索、记忆和混合工作流，每类 5 个。

评分按 objective checkpoint（可客观验证的中间或最终检查点）加权，因此完成率不是“完整完成任务数 / 30”：

| 设置 | checkpoint 加权完成率 | 完整完成 | 部分完成 |
| --- | ---: | ---: | ---: |
| OpenClaw on stock Android | 54.44% | 13 | 7 |
| OpenClaw on AOHP | 75.56% | 20 | 5 |
| 差值 | +21.12 个百分点 | +7 | -2 |

这组结果支持“同一 agent 在该任务集上使用 AOHP 接口后完成度提高”。
它不支持对所有 Android 应用、设备、模型或 agent 框架作同幅度推广。

### 5.2 执行成本

工具调用、时长、token 和 LLM 请求只统计两组都完整完成的 11 个任务。这里的 token 是模型处理文本时使用的计量单位：

| 设置 | 工具调用 | 时长 | Token | LLM 请求 |
| --- | ---: | ---: | ---: | ---: |
| stock Android | 233 | 33.94 min | 7,103,192 | 273 |
| AOHP | 129 | 18.93 min | 3,441,759 | 143 |
| 降幅 | 44.64% | 44.21% | 51.55% | 47.62% |

其中 input token 降低 51.50%，output token 降低 57.48%。结构化观察与较短操作路径减少了该子集的上下文和往返。

论文表格给出的是这 11 个任务的汇总值，仍缺少以下实验信息，复现时应补齐：

- 模型名称、版本、采样参数和输入计费口径；
- stock 与 AOHP 的提示词、tool schema（工具参数契约）和重试策略；
- 每个任务的多次运行分布，不能只看单组 aggregate（汇总值）；
- 设备/模拟器配置、温度、网络和应用版本；
- AOHP 系统服务自身的 CPU、内存、GPU、磁盘和能量；
- 对 AppFunctions、Accessibility 自动化或其他结构化 baseline（对照方案）的比较。

“token 减半”是这 11 个共同成功任务的测量结果，不能直接归因给 SUI 单一机制。
文件桥、事件流、CLI、虚拟显示和路径长度都同时变化。
论文没有给出消融实验，也就是没有逐项关闭机制来测量各自贡献。

## 6. Android 17 AppFunctions 的标准平台边界

### 6.1 API 演进

AppFunctions 是目标应用主动发布结构化 function、再由获授权 caller 搜索和执行的平台接口。
它从 API 36 进入平台，Android 17 / API 37 扩展了动态注册、搜索、观察和 activity-scoped function 等能力。

官方页面截至 2026-08-14 仍把 AppFunctions 标为 experimental preview（实验性预览）；
与 Gemini 和 system agent 的完整集成只通过限量 early access program 开放。
平台类存在，不代表所有 Android 16/17 设备都具备可用的端到端产品链路。

两种 provider（能力提供方）形态要分开：

| 形态 | 声明与实现 | 生命周期 |
| --- | --- | --- |
| `AppFunctionService` | XML metadata + manifest service | 系统可按调用绑定服务，适合全局能力 |
| runtime registration | XML metadata + `registerAppFunction(s)` | 只能从 Activity 或 Service context 注册，随 registration/context 生命周期 |

metadata 是 function 的标识、参数、作用域等描述信息。两种形态都要先在 XML asset 声明 function；
runtime registration（运行时注册）只是为已声明标识绑定当前实现，不会让 agent 随意执行任意应用方法。
identifier、scope、注册状态、权限、package visibility 和 enabled state 都参与校验。

搜索其他 package 的 function 时，caller 需要 `EXECUTE_APP_FUNCTIONS`、`EXECUTE_APP_FUNCTIONS_SYSTEM` 或 `DISCOVER_APP_FUNCTIONS` 之一，并且目标 package 对 caller 可见。
执行跨包 function 时，`DISCOVER_APP_FUNCTIONS` 不够，仍需 `EXECUTE_APP_FUNCTIONS` 或 `EXECUTE_APP_FUNCTIONS_SYSTEM`。

公开文档把这类 caller 视为受信任调用方。普通应用不能默认发现和执行所有其他应用 function。

API 37 的 runtime function 还有一个容易遗漏的边界：注册进程被冻结时，系统不会进入该实现；
注册 context 销毁后 registration 会被移除。这里的 context 是发起注册的 Activity 或 Service 生命周期对象。
AppFunctions 因此不等价于 AOHP 的虚拟显示后台 GUI session。

### 6.2 system_server 如何启动服务

Android 17 的 `SystemServer` 通过 `AppFunctionManagerConfiguration.isSupported(context)` 决定是否启动主服务。
这里的 gate 是控制某段代码是否生效的条件开关。下面的源码片段展示了启动条件：

```java
if (AppFunctionManagerConfiguration.isSupported(context)) {
    t.traceBegin("StartAppFunctionManager");
    mSystemServiceManager.startService(AppFunctionManagerService.class);
    t.traceEnd();
}
```

`AppFunctionManagerConfiguration.isSupported()` 在该 tag 中返回 `enableAppFunctionManager()` flag。
`AppFunctionManagerService.onStart()` 发布 Binder service（跨进程调用入口）前再次检查相同条件。

代码说明功能受 build/device flag 控制；仅凭这个分支无法断言所有 AOSP user build 默认开启或关闭。

V2 permission 模型还有独立的 `enableAppFunctionPermissionV2()` gate，`SystemServer` 会据此先启动 `AllowlistService`。
allowlist 是明确列出获准主体的许可名单。

构造函数中的 access service、`AppInteractionServiceImpl` 和 allowlist reader 也分别受 flag 管理。这些 gate 说明权限与交互能力可以分阶段配置。

### 6.3 metadata、搜索与动态注册

`android-17.0.0_r1` 中可追踪的主要路径如下：

1. 应用在 XML asset 与 manifest property/service 中声明 function；
2. system_server 的 metadata reader/sync 组件把静态与动态 metadata 组织到可查询存储；
3. `AppFunctionManager.searchAppFunctions()` 通过 `AppSearchManager` 查询可见 metadata；`AppSearchManager` 提供设备内结构化索引与搜索；
4. caller 组装 `ExecuteAppFunctionRequest`；
5. `AppFunctionManagerServiceImpl` 做身份、权限、可见性、enabled state、URI grant 和目标服务校验；
6. 调用进入 `AppFunctionService` 或 runtime registry 中的实现；
7. cancellation、结果、异常和日志沿 Binder callback 返回。

AppFunctions 提供结构化参数和结果，但不会替 provider 自动完成业务授权。
创建订单、分享文件、读取账号或修改设备状态仍要由应用检查登录态、用户确认、数据权限和幂等性。

### 6.4 DeviceConfig 参数的准确含义

`ServiceConfigImpl` 从 DeviceConfig 的 `app_functions` namespace 同步读取以下参数。
DeviceConfig 是平台按命名空间保存运行时配置的机制，namespace 用来隔离不同模块的键：

| property | 默认值 | 用途 |
| --- | ---: | --- |
| `execute_app_function_cancellation_timeout_millis` | 5000 ms | 取消信号发出后，强制解绑目标 service 前的等待时限 |
| `search_app_function_page_size` | 20 | 内部搜索分页 |
| `app_function_metadata_change_debounce_ms` | 500 ms | metadata 变更 debounce |
| `app_function_enabled_state_change_debounce_ms` | 200 ms | enabled state 变更 debounce |
| `app_function_enabled_state_change_max_debounce_ms` | 1000 ms | debounce 最大等待 |
| `app_function_allowlist_cache_size` | 5 | allowlist cache 大小 |

debounce（防抖）会在连续变更后等待一小段时间再处理，避免同一批更新触发多次工作。
这个类没有注册 `OnPropertiesChangedListener`，也没有把 getter 结果永久缓存；
每个 getter 调用 `DeviceConfig.getLong/getInt`。
因此参数会在对应 getter 下次执行时读取，不能写成“必须重启服务才生效”。

`services/appfunctions/Android.bp` 中 stats log generator 的 `--minApiLevel 35` 只属于生成 `AppFunctionsStatsLog` 的构建命令。
它不能证明 API 35 以下“不生成服务”，也不能用来推断 AppFunctions 主 API 的引入版本。

API 边界应以 SDK stubs（SDK 暴露的 API 签名）、`@AddedIn` 文档和 feature flag 为准。

## 7. AOHP 与 AppFunctions 的准确对照

标准 Android 上常被用于跨应用 agent 的三条入口不能互换。
`AccessibilityService` 面向辅助功能，依据可访问性树观察和操作 UI；
`VoiceInteractionService` 是每个用户选择的 assistant 角色入口；AppFunctions 则由目标应用主动发布结构化能力。

三者的 `BIND_*` 权限约束服务实现者，不是调用方在 manifest 中声明后即可获得的通行证。
产品应优先采用目标应用明确发布的 function。
只有业务确属辅助功能或系统 assistant 时，才使用相应服务角色，并把用户授权、可见提示与撤销路径纳入设计。

| 维度 | AOHP 研究原型 | Android 17 AppFunctions |
| --- | --- | --- |
| 交付方式 | AOSP fork + system services + privileged app/CLI | Android platform API + system_server service + Jetpack 辅助库 |
| 能力来源 | API、CLI、SUI、GUI、skills | 应用声明的结构化 function |
| legacy 应用 | 可通过 UI/CLI 适配，但语义质量不稳定 | 未声明 function 的应用不会自动获得 function |
| 后台 GUI | 特权虚拟显示与自定义 Activity/display policy | 不提供任意后台 GUI workspace |
| 执行生命周期 | AOHP session、display、container 和 agent driver | Service binding 或 Activity/Service runtime registration |
| 安全模型 | vault token、字段声明、边界策略、consent、审计原型 | Binder 身份、权限、package visibility、allowlist、enabled state、URI grant |
| 数据传播 | 原型在选定 UI/tool/file 边界记录 taint metadata | 不提供跨 LLM/tool 的通用 taint tracking |
| 兼容成本 | 需要定制系统镜像和持续合并 AOSP | 标准设备可用性由 API、flag、扩展库和 OEM 配置决定 |
| 成熟度 | README 明示 early-stage research prototype | API 仍标为 experimental preview，但属于标准平台接口 |

两者可以组合使用：AppFunctions 适合让应用主动暴露稳定、类型化的操作；
AOHP 探索系统如何容纳 legacy GUI、跨服务记忆、虚拟执行和敏感数据引用。

组合前仍需定义单一的身份、consent、审计和撤销模型，避免两个控制面给同一 agent 重复授予权限。

## 8. 对工程团队的建议

### 8.1 应用开发者

可优先采用以下顺序：

1. 对稳定业务能力使用 AppFunctions、公开 SDK、Provider 或受控 deep link（应用内深链入口）；
2. 对未提供结构化入口的 UI，使用 Accessibility/UI automation 只做兼容路径；
3. 为每个动作标明 read-only（只读）、reversible（可撤销）、destructive（破坏性）或 external side effect（外部副作用）；
4. 对支付、发送、发布、删除和权限变更要求用户确认；
5. 返回可验证的结果 ID、状态和幂等键；幂等键用于识别重试，防止同一动作执行两次；
6. 文件通过 `content://` URI 和最小范围 grant 交接；
7. 日志中记录 caller、function、目标对象、结果和取消状态，过滤敏感参数。

结构化接口的价值来自少走 GUI 步骤和减少观察噪声。
AOHP 实验给出了方向性证据，但单个项目仍要测自己的成功率、延迟、token、回退率和错误后果。

### 8.2 系统与 ROM 开发者

系统级 agent 至少要拆分以下权力：

- 发现能力；
- 读取结构化状态；
- 启动组件；
- 注入输入；
- 解析 vault token；
- 执行 shell/container；
- 访问文件与传感器；
- 代表用户确认外部副作用。

AOHP 当前多个服务共用 `MANAGE_AOHP_VIRTUAL_DISPLAY` 这一 `signature|privileged` permission。
研究镜像便于迭代，生产设计则应按能力拆分 permission、AppOp 和 role：
permission 校验调用资格，AppOp 记录或限制具体操作，role 表示用户选择的系统角色。

每次调用还应绑定 caller UID、user、display、task 与 purpose，避免一次授权被挪到另一项任务。

虚拟显示并行度要进入资源管理：

- 设定每 agent、每 user 和全局 display 上限；
- 前台用户交互拥有更高 CPU/GPU/thermal 优先级；
- session 空闲、owner 死亡或 screen-off 时回收资源；
- 防止一个 display 上的应用观察或影响另一个 display；
- 对输入注入、截图、secure content 和 clipboard 建立独立审计；
- 用 `dumpsys display/window/activity`、Perfetto、meminfo 和 power rail 验证；power rail 是设备硬件电源轨的能量计数口径。

### 8.3 安全评审

安全评审不能停在“有 vault 和 taint”这两个名词。逐条回答：

1. source 怎样声明，启发式误报和漏报怎样处理；
2. token 是否可伪造、重放、跨 user 使用或通过日志泄露；
3. plaintext 在内存、Binder、文件、截图和 crash dump 中出现在哪里；
4. derived value（由敏感输入计算出的派生值）的标签怎样合并和降级；
5. 每个 sink 的策略是 implemented、partial、stub 还是 unobserved；
6. consent UI 是否绑定准确的 source、destination、amount 和 action；
7. prompt injection 能否改变 purpose 或绕过 confirmation；
8. 审计日志是否可篡改，保留多久，由谁读取；
9. 服务重启、设备重启、备份恢复和用户切换时怎样处理；
10. fail closed 会不会被攻击者反复触发，形成可利用的拒绝服务。

## 9. 如何复现与扩展这些结论

复现 AOHP 论文结果时，建议把实验拆成四组。baseline 是用来比较增益的对照设置：

| 组 | 目的 | 主要指标 |
| --- | --- | --- |
| stock GUI | 建立原始 agent baseline | 完成率、步骤、token、时长 |
| stock structured | 隔离 Accessibility/AppFunctions 的贡献 | 同上，并记录结构化覆盖率 |
| AOHP interface | 测量 SUI、event、file、CLI 的组合收益 | 成功率、回退率、事件丢失 |
| AOHP full security | 加入 vault、consent、policy | 泄露率、误拒绝、审批次数、延迟 |

每个任务运行多次并随机化顺序，固定模型与 tool schema，保存完整调用 trace（按时间排列的模型、工具和系统调用记录）。

资源侧同时采集 system_server、agent driver（驱动任务执行的 agent 进程）、目标应用、SurfaceFlinger 和 sandbox 的 CPU、PSS、GPU 与能量。
安全侧加入未标注应用、custom View、WebView、native code、恶意 tool output、过期 token、跨用户和进程重启 case。

完成这些测试后，才能回答某个 AOHP 机制在目标产品上的收益和风险。
论文给出可运行原型与初步结果，Android 17 则给出标准化 AppFunctions 控制面；两者仍处在快速演进阶段。

## 10. 参考资料

### AOHP 一手资料

- [AOHP 论文：arXiv 2606.23449](https://arxiv.org/abs/2606.23449)
- [AOHP 项目仓库](https://github.com/aohp-os/aohp)
- [AOHP framework fork：`AohpVirtualDisplayService`](https://github.com/aohp-os/platform_frameworks_base/blob/a2d4a80ba16211ac73eee4baf6e73d6c7ba669fe/services/core/java/com/android/server/aohp/AohpVirtualDisplayService.java)
- [AOHP framework fork：`AohpEventStreamService`](https://github.com/aohp-os/platform_frameworks_base/blob/a2d4a80ba16211ac73eee4baf6e73d6c7ba669fe/services/core/java/com/android/server/aohp/AohpEventStreamService.java)
- [AOHP framework fork：`AohpSecurityBridgeService`](https://github.com/aohp-os/platform_frameworks_base/blob/a2d4a80ba16211ac73eee4baf6e73d6c7ba669fe/services/core/java/com/android/server/aohp/AohpSecurityBridgeService.java)
- [AOHP framework fork：`AohpVaultService`](https://github.com/aohp-os/platform_frameworks_base/blob/a2d4a80ba16211ac73eee4baf6e73d6c7ba669fe/services/core/java/com/android/server/aohp/AohpVaultService.java)
- [AOHP framework fork：`AohpTaintTrackerService`](https://github.com/aohp-os/platform_frameworks_base/blob/a2d4a80ba16211ac73eee4baf6e73d6c7ba669fe/services/core/java/com/android/server/aohp/AohpTaintTrackerService.java)
- [AOHP framework fork：`AohpContainerService`](https://github.com/aohp-os/platform_frameworks_base/blob/a2d4a80ba16211ac73eee4baf6e73d6c7ba669fe/services/core/java/com/android/server/aohp/AohpContainerService.java)
- [AOHP framework fork：`AohpFileBridgeService`](https://github.com/aohp-os/platform_frameworks_base/blob/a2d4a80ba16211ac73eee4baf6e73d6c7ba669fe/services/core/java/com/android/server/aohp/AohpFileBridgeService.java)
- [AOHP framework fork：`AohpUiTreeDumper`](https://github.com/aohp-os/platform_frameworks_base/blob/a2d4a80ba16211ac73eee4baf6e73d6c7ba669fe/services/accessibility/java/com/android/server/accessibility/AohpUiTreeDumper.java)
- [AOHP framework fork：`AohpUiTreeSanitizer`](https://github.com/aohp-os/platform_frameworks_base/blob/a2d4a80ba16211ac73eee4baf6e73d6c7ba669fe/services/core/java/com/android/server/aohp/AohpUiTreeSanitizer.java)
- [AOHP sandbox skill：chroot 与共享 network namespace](https://github.com/aohp-os/aohp/blob/b8ab9e98a2bd51f7fbd01a95d3b45dca078c5884/skills/aohp-sandbox/SKILL.md)
- [AOHP container daemon：mount namespace、cgroup 与 `chroot()`](https://github.com/aohp-os/platform_system_core/blob/d1fc184b0a138a5a1b1da70512516cd2406980d9/aohp-containerd/container_manager.cpp)

### Android 17 一手资料

- [Android 17 `AppFunctionManager`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/appfunctions/AppFunctionManager.java)
- [Android 17 `AppFunctionManagerService`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/appfunctions/java/com/android/server/appfunctions/AppFunctionManagerService.java)
- [Android 17 `ServiceConfigImpl`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/appfunctions/java/com/android/server/appfunctions/ServiceConfigImpl.java)
- [Android 17 `OnDeviceIntelligenceManager`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/packages/NeuralNetworks/framework/module/java/android/app/ondeviceintelligence/OnDeviceIntelligenceManager.java)
- [AppFunctions 概览](https://developer.android.com/ai/appfunctions)
- [平台 `AppFunctionManager` API](https://developer.android.com/reference/android/app/appfunctions/AppFunctionManager)
- [平台 `android.app.appfunctions` API](https://developer.android.com/reference/android/app/appfunctions/package-summary)
- [DisplayManager `VirtualDisplay` API](https://developer.android.com/reference/android/hardware/display/DisplayManager)
- [Android 多显示 Activity 启动策略](https://source.android.com/docs/core/display/multi_display/activity-launch)
- [TaintDroid OSDI 2010](https://www.usenix.org/conference/osdi10/legacy-presentation/taintdroid-information-flow-tracking-system-realtime-privacy)

### 库内延伸

- [系统托管 GenAI 与 OnDeviceIntelligence](../../part1-fundamentals/ch05-cpu-power/05-ondevice-ai-runtime-npu.md)
- [跨进程内存共享与端侧推理预算](../../part1-fundamentals/ch04-memory/10-cross-process-memory-ai-inference.md)
- [Agent Perfetto 分析协议](../../part3-tools/ch13-perfetto/11-agent-perfetto-analysis-protocol.md)
