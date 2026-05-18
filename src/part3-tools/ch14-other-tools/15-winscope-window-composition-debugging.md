---
title: "Winscope 与窗口/合成状态可视化调试"
chapter: "14.15"
status: ready-for-review
drafted_date: "2026-05-19"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-05-19"
last_verified_against: "android-latest-release / Android 15+ Winscope Perfetto data sources"
confidence: medium
sources:
  - type: official
    path: "https://source.android.com/docs/core/graphics/tracing-win-transitions"
  - type: official
    path: "https://source.android.com/docs/core/graphics/winscope/capture/winscope"
  - type: official
    path: "https://source.android.com/docs/core/graphics/winscope/capture/adb"
  - type: official
    path: "https://source.android.com/docs/core/graphics/winscope/analyze/sf"
  - type: official
    path: "https://source.android.com/docs/core/graphics/winscope/analyze/search"
  - type: official
    path: "https://source.android.com/docs/core/graphics/surfaceflinger-windowmanager"
  - type: daily-info
    path: "intake/daily-info/2026-05-19.md"
tags: [winscope, surfaceflinger, windowmanager, perfetto, tracing, rendering, input]
related_chapters: ["2.6", "2.12", "2.13", "2.16", "3.1", "13.3", "13.10", "14.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-19"
gap_source: "官方文档/每日信息/AOSP工具文档"
---

# 14.15 Winscope 与窗口/合成状态可视化调试

Winscope 解决的是窗口和 layer 状态证据问题：某一帧谁可见、谁挡住了谁、输入焦点落在哪个窗口、某个 `SurfaceControl.Transaction` 改了哪些属性。它不替代 Perfetto 的 CPU 调度、Binder、fence、GPU 队列分析；它给出的是 WindowManager、SurfaceFlinger、Transitions、Transactions、ViewCapture 等系统状态在时间轴上的快照。读完这一节，应能把「白屏」「黑屏」「点不动」「动画错位」这类现象拆成可验证的窗口树和 layer 树问题，再决定是否继续用 Perfetto 或 AGI 追耗时。

[已验证: 官方文档, source.android.com/docs/core/graphics/tracing-win-transitions]

## Winscope 的证据边界

Winscope 的价值来自两个事实。WindowManager 管窗口生命周期、输入和焦点、屏幕方向、转场、动画、位置、变换和 z-order；SurfaceFlinger 接收 buffer、合成 layer，并把结果交给显示设备。两边的状态分开看很容易漏掉中间差异：WindowManager 里某个窗口已经 `visible=true`，SurfaceFlinger 里对应 layer 仍可能没有 buffer、被 opaque layer 遮挡，或者被父 layer 的裁剪影响。

[已验证: 官方文档, source.android.com/docs/core/graphics/surfaceflinger-windowmanager]

Winscope 支持的证据类型可以按问题划分：

| 证据 | 回答的问题 | 不适合回答的问题 |
|------|------------|------------------|
| Window Manager trace / dump | 窗口是否创建、可见、获得焦点，窗口容器如何组织，转场和动画状态是否符合预期 | 某段 Java 或 native 代码为什么耗时 |
| SurfaceFlinger layers trace / dump | layer 是否可见、z-order 是否正确、是否有 buffer、输入区域和可见区域是否异常 | RenderThread、GPU、HWC 各阶段耗时归因 |
| SurfaceFlinger transactions trace | 哪个 transaction 改了 layer 属性，layer 何时被添加、移动、隐藏或销毁 | transaction 发起方内部为什么晚提交 |
| Shell transitions trace | 转场 id、参与者、handler、状态是 played、merged 还是 aborted | App 内动画每一帧的绘制成本 |
| ViewCapture | 支持 ViewCapture 的系统窗口内 View 属性变化，例如 System UI 或 Launcher | 普通三方 App 任意 View 树的完整复盘 |
| Screen recording / Screenshot | 把系统状态和用户肉眼看到的画面对上 | 替代状态证据本身 |

这张表也说明了边界。Winscope 适合回答「状态对不对」，Perfetto 适合回答「时间花在哪」，AGI 的 SurfaceFlinger Tracks 更适合看合成、buffer、present 相关轨道。涉及 fence 等同步细节时，详见 2.16 节；涉及 SurfaceFlinger 合成机制时，详见 2.6 节；涉及 Perfetto 视图和 SQL 时，详见 13.3、13.10 节。

## 采集入口与 trace 类型选择

Winscope 有三种常见入口：网页端采集、adb 命令采集、离线加载 bugreport 或 dump。网页端适合交互式本地排障；adb 命令适合脚本化采集；dump 适合只关心某个时刻的窗口或 layer 状态，不想让 trace 持续采集影响设备。

[已验证: 官方文档, source.android.com/docs/core/graphics/winscope/capture/winscope]

Android 15 起，Winscope trace 进入 Perfetto 数据源体系。官方 adb 文档明确说，每类 Winscope trace 都是独立 Perfetto data source，可以单独启用，也可以放在同一次 tracing session 里。Android 14 及更低版本仍使用各自命令，例如 `wm tracing start`、`dumpsys SurfaceFlinger --proto` 等。

[已验证: 官方文档, source.android.com/docs/core/graphics/winscope/capture/adb]

采集时按问题选开关，避免把所有高开销选项都打开：

| 问题 | 建议采集 | 配置取舍 |
|------|----------|----------|
| 窗口可见性、焦点、方向、窗口容器异常 | WindowManager trace | 常规排障用 `LOG_LEVEL_DEBUG` + `LOG_FREQUENCY_FRAME`；要看同一帧内的中间状态再改成 transaction 频率 |
| layer 被遮挡、z-order 错、黑屏、闪屏 | SurfaceFlinger layers trace + screen recording | 常规场景打开 input、composition；`TRACE_FLAG_EXTRA`、`TRACE_FLAG_HWC` 内存开销高，只在需要看额外元数据时打开 |
| transaction 是否提交了错误几何或 alpha | SurfaceFlinger transactions trace | `MODE_CONTINUOUS` 适合 bugreport 类采集；`MODE_ACTIVE` 适合本地复现时完整记录 |
| 启动/返回/分屏/PIP 转场异常 | Shell transitions + WindowManager + SurfaceFlinger | 通过 transition id 把转场参与者和对应 layer 对上 |
| System UI / Launcher 内部 View 位移异常 | ViewCapture + screen recording | 只覆盖支持 ViewCapture 的系统窗口，不当成普通 App View 调试器 |
| 只想留一个现场快照 | WindowManager dump + SurfaceFlinger dump + screenshot | dump 不连续，不能证明状态变化顺序 |

这个 Perfetto 配置用于本地复现窗口与 layer 同步异常，读者重点看三个 data source 名称：`android.windowmanager`、`android.surfaceflinger.layers`、`android.surfaceflinger.transactions`。

```bash
adb root
adb shell -t perfetto \
  -c - --txt \
  -o /data/misc/perfetto-traces/winscope_trace \
  <<'EOF'
unique_session_name: "winscope_window_sf_debug"
buffers: {
  size_kb: 63488
  fill_policy: RING_BUFFER
}
data_sources: {
  config {
    name: "android.windowmanager"
    windowmanager_config: {
      log_level: LOG_LEVEL_DEBUG
      log_frequency: LOG_FREQUENCY_FRAME
    }
  }
}
data_sources: {
  config {
    name: "android.surfaceflinger.layers"
    surfaceflinger_layers_config: {
      mode: MODE_ACTIVE
      trace_flags: TRACE_FLAG_INPUT
      trace_flags: TRACE_FLAG_COMPOSITION
      trace_flags: TRACE_FLAG_BUFFERS
    }
  }
}
data_sources: {
  config {
    name: "android.surfaceflinger.transactions"
    surfaceflinger_transactions_config: {
      mode: MODE_CONTINUOUS
    }
  }
}
EOF
```

这组配置不会采集 CPU 调度、Binder 或 GPU 队列。发现状态异常后，再另开 Perfetto 性能 trace 补时间线证据；发现状态正常但画面仍卡顿时，Winscope 只能证明窗口和 layer 没错，耗时归因要回到 Perfetto。

## 窗口、layer、输入焦点的对照方法

窗口问题不能只盯一个面板。WindowManager 负责 Window 对象和窗口元数据，SurfaceFlinger 负责把 surface/layer 合成到屏幕。官方文档给出的关系是：WindowManager 向 SurfaceFlinger 请求 layer，并保留 `SurfaceControl` 操作 layer 外观；App 获得 surface 后提交 buffer，SurfaceFlinger 在 VSync 间隔收集可见 layer 的 buffer 并合成。

[已验证: 官方文档, source.android.com/docs/core/graphics/surfaceflinger-windowmanager]

排障时按这条顺序对照：

1. 在 WindowManager 里定位目标窗口：看 title、token、parent token、`is_visible`、focused app/window、display、bounds。目标窗口如果在 WM 里不可见，问题还停在窗口管理层。
2. 在 SurfaceFlinger 里找对应 layer：名字通常带包名、Activity 名或系统窗口名。找不到时，检查窗口是否还没创建 surface、layer 是否被销毁、是否只存在父容器 layer。
3. 对比可见性解释：SurfaceFlinger viewer 会给出 flags、invisibility reason、occluded、partially occluded、covered、buffer、destination frame、z-order、relative parent 等属性。
4. 对照输入区域：SF 的 input 属性可以显示 touchable region、focus 等相关信息。点击无响应时，先确认触摸坐标落入哪个 layer 的输入区域，再回到 WindowManager 看焦点窗口是否一致。
5. 回放相邻帧：状态错误通常只持续一两帧。Winscope 可用时间戳跳转，也可以逐帧前后移动，看错误是在 transaction 提交前、提交后，还是合成结果里出现。

[已验证: 官方文档, source.android.com/docs/core/graphics/winscope/analyze/sf]

SurfaceFlinger viewer 的可见性解释尤其适合黑屏/白屏问题。一个 App layer 即使 `visible=true`，仍可能因为没有 buffer、被父层隐藏、可见区域为空、被上层 opaque layer 完全遮挡而看不到。官方示例中，NotificationActivity 的 layer 可见但可见区域为空，前方的 NotificationShade 变成 opaque，结果用户看到短暂黑屏。这个例子证明：WindowManager 的「窗口可见」和 SurfaceFlinger 的「最终能被看到」不是同一个判断。

[已验证: 官方文档, source.android.com/docs/core/graphics/tracing-win-transitions]

## 与 Perfetto / AGI 的分工

Winscope、Perfetto、AGI 不该互相替代。把工具按证据类型拆开，排障速度会快很多：

| 工具 | 证据形态 | 典型判断 |
|------|----------|----------|
| Winscope | 每帧窗口、layer、transaction、transition、View 状态 | 目标窗口有没有出现；layer 是否被遮挡；transition 是否 aborted；transaction 是否改错 bounds 或 alpha |
| Perfetto | 线程、slice、counter、ftrace、部分 Android data source 时间线 | 主线程、RenderThread、Binder、系统服务、调度、内存或 I/O 为什么慢 |
| AGI | 图形栈和 GPU 相关分析视图 | 合成、buffer、GPU workload、图形 API 行为是否符合预期 |
| dumpsys | 单时刻文本/proto 状态 | 复核当前 WM/SF 状态；在没有连续 trace 时留现场 |

一个实用判断是：画面「不对」先看 Winscope，画面「慢」先看 Perfetto。画面既不对又慢，先用 Winscope 定位哪个对象错，再用 Perfetto 找这个对象状态变化前后的耗时。反过来，如果直接从 Perfetto 追 CPU running，很容易证明某个线程忙，却没证明用户看到的 layer 到底是谁。

[已验证: 官方文档, source.android.com/docs/core/graphics/winscope/analyze/sf]

## 典型排障路径

### 白屏 / 黑屏

白屏和黑屏先判断屏幕上到底是哪一个 layer。操作顺序是：跳到用户报错时间点，打开 SurfaceFlinger rects view，打开 `Show only V` 找当前可见 layer；再选中目标 App layer，看 invisibility reason、buffer、visible region 和被遮挡状态。若目标 App 没有 buffer，回到启动、BufferQueue、首帧路径；若 App 有 buffer 但上层系统窗口遮住它，继续看 z-order、opaque flag 和对应 transaction。

### 启动后首帧未出现

首帧问题要把 splash layer、Activity layer、starting window 和 WindowManager 容器对上。WM 里 Activity 可见只说明窗口状态到了，不代表 SF 已拿到能合成的 buffer。SF 里如果 `Frame Number` 没增长、destination frame 不对或可见区域为空，继续查 App 首帧提交、RenderThread、BufferQueue 和 fence，相关机制见 2.13、2.16 节。

### 转场动画异常

启动、返回、分屏、PIP、Recents 等问题要同时看 Shell transitions、WindowManager 和 SurfaceFlinger。Transitions 面板给 transition id、handler、参与者和 played/merged/aborted 状态；SurfaceFlinger 面板验证对应 layer 的 bounds、alpha、z-order 是否按转场结果变化。官方示例还会从 transition 的 dispatch time 跳到 SurfaceFlinger 视图核对 rects。

[已验证: 官方文档, source.android.com/docs/core/graphics/tracing-win-transitions]

### 横竖屏切换错位

旋转问题先看 WindowManager 的 display、orientation、bounds，再看 SurfaceFlinger 的 requested/calculated geometry。SF 属性面板区分 requested 和 calculated：子 layer 请求的几何属性可能被父 layer 继承或变换后才生效。错位如果只出现在 calculated 值，往父容器和 display transform 查；如果 requested 已经错，往 WindowManager 或 App transaction 查。

### 系统窗口遮挡

状态栏、导航栏、输入法、NotificationShade、screen decor overlay、PIP overlay 都可能让 App 看起来「没显示」。处理这类问题时，不要只看 App layer；把 `Show only V` 打开，按 z-order 从上往下看所有可见系统 layer。被 opaque 系统 layer 完整覆盖时，App layer 在 SF 里可能仍显示为 visible，但用户看不到。

### PIP / 自由窗口 layer 错位

PIP、自由窗口、分屏这类多窗口场景容易出现父子 layer、relative Z、crop、rounded corner、display area surface 互相影响。排查时把 layer hierarchy 展开到父容器，不只选 leaf layer；对照 parent、relative parent、z-order、bounds、screen bounds、crop 和 corner radius。若 transition 参与者里有 WM container 和 SF layer id，可以用 Search 面板把它们关联起来。

## Android 版本、权限与数据保真边界

Winscope 采集不是越多越准。版本、权限、buffer 和采样模式都会改变证据质量。

- Android 15+：Winscope trace 集成到 Perfetto，每类 trace 是独立 data source。脚本化采集时优先使用 Perfetto 配置。
- Android 14 及更低版本：不同 trace 类型有不同 adb 命令，文件通常落在 `/data/misc/wmtrace`，再拉到本地用 Winscope 打开。
- build 类型：官方 adb 文档说明命令行采集用于 debug builds，也就是 userdebug 和 eng，并且采集前运行 `adb root`。
- ring buffer：WindowManager 和 SurfaceFlinger 都可能使用内存 ring buffer。buffer 太小会丢掉早期状态；buffer 太大又会增加内存压力。
- SurfaceFlinger layers：默认只在几何变化时记录新状态；要捕获 buffer 变化，需要打开 trace buffers / `TRACE_FLAG_BUFFERS`。
- SurfaceFlinger active mode：官方文档标注 `MODE_ACTIVE` 计算开销高，会影响性能。性能敏感 trace 可使用 generated bugreport 类模式。
- verbose 元数据：SurfaceFlinger metadata / HWC、WindowManager verbose、ProtoLog stacktrace 都会增加内存和运行开销，本地复现时再打开。
- input trace：`TRACE_MODE_TRACE_ALL` 会记录系统处理的输入事件。官方警告该模式只用于本地设备或测试，不用于 field tracing。
- Web Device Proxy：官方文档标注它暂不支持 macOS；macOS 上通常走 Winscope Proxy 或 adb 离线采集。

[已验证: 官方文档, source.android.com/docs/core/graphics/winscope/capture/adb]

## 扩展：Winscope Search 与 SQL 视图

Winscope 的 Search viewer 可以在 Perfetto trace 上跑 SQL。官方提供的 helper view 覆盖 SurfaceFlinger、Transactions、Transitions、ViewCapture，并在较新文档中补充了 WindowManager、ProtoLog 等搜索能力。属性名采用 snake_case，嵌套属性用 dot notation，重复字段在 `property` 里带下标，在 `flat_property` 里不区分下标。

[已验证: 官方文档, source.android.com/docs/core/graphics/winscope/analyze/search]

这些视图适合批量找状态变化，不适合靠肉眼在 UI 里一帧一帧翻：

| 视图 | 常用字段 | 用法 |
|------|----------|------|
| `sf_layer_search` | `ts`、`layer_id`、`layer_name`、`is_visible`、`property`、`value`、`previous_value` | 找某个 layer 的可见性、bounds、alpha、buffer、z-order 变化 |
| `transactions_search` | `ts`、`transaction_id`、`property`、`value` | 找哪一笔 transaction 修改了 layer x/y、alpha、crop 或新增 layer |
| `transitions_search` | `ts`、`transition_id`、`property`、`value` | 找特定 transition handler、flags、状态和参与者 |
| `viewcapture_search` | `package_name`、`window_name`、`class_name`、`property`、`value` | 找 System UI / Launcher View 的位移、alpha、可见性变化 |
| `wm_search` | `title`、`token`、`parent_token`、`is_visible`、`property`、`value` | 找窗口容器可见性、surface position、bounds 等变化 |

这条 SQL 用于定位某个 App layer 从不可见变可见的时刻，重点看 `value != previous_value` 和 `is_visible`。

```sql
SELECT ts, layer_id, layer_name, value, previous_value
FROM sf_layer_search
WHERE layer_name LIKE '%com.example%'
  AND property = 'is_visible'
  AND value != previous_value
ORDER BY ts;
```

查询结果只能证明 SurfaceFlinger trace 里记录到 layer 可见性变化。要判断为什么变晚，还要把同一时间点附近的 WindowManager、transactions、Perfetto 主线程和 RenderThread 证据补上。

这条 SQL 用于找 transaction 何时把某个 layer 的 x 坐标改成异常值，适合追横竖屏切换或 PIP 位移动画问题。

```sql
SELECT ts, transaction_id, value
FROM transactions_search
WHERE flat_property = 'transactions.layer_changes.x'
  AND value = '-54.0'
ORDER BY ts;
```

如果查到 transaction id，再去 ProtoLog 或 WindowManager 搜同一时间段的转场/窗口状态，通常能判断这次修改来自转场、布局还是窗口容器变化。

## 扩展：与 dumpsys window / dumpsys SurfaceFlinger 的互证

Winscope 的 UI 很方便，但不能只信 UI 面板。没有连续 trace 时，`dumpsys window --proto` 和 `dumpsys SurfaceFlinger --proto` 仍能保留单时刻状态；有 trace 时，dump 也能作为现场快照互证。

这两个命令用于保存窗口和 SurfaceFlinger 的 proto dump，读者重点看输出文件后缀 `.winscope`，它们可以直接被 Winscope 加载。

```bash
adb exec-out dumpsys window --proto > window_dump.winscope
adb exec-out dumpsys SurfaceFlinger --proto > sf_dump.winscope
```

dump 只能说明命令执行那一刻的状态。转场、闪屏、一两帧黑屏这类问题仍要靠 trace；dump 更适合复核「当前为什么点不到」「当前哪个系统窗口盖住了 App」这类静态现场。

[已验证: 官方文档, source.android.com/docs/core/graphics/winscope/capture/adb]

## 扩展：Windows 平台采集与离线分析注意事项

每日信息里出现了 Windows 平台 Winscope 使用教程，说明团队外部读者会在非 AOSP 开发机上使用这个工具。Windows 端可按保守路径处理：采集尽量走 adb 命令或网页端 Web Device Proxy；离线分析时把 `.winscope`、Perfetto trace、screen recording 放在同一目录，文件名带设备、版本、场景和时间，例如 `pixel8_a16_split_screen_2026-05-19.winscope`。

[来源: intake/daily-info/2026-05-19.md]

大 trace 在浏览器里加载有内存风险。采集前控制 trace 时长，少开 HWC、metadata、verbose、stacktrace 等高开销选项；问题能稳定复现时，用短时间窗口重复抓两三次，比抓一个十几分钟的大文件更容易分析。

## 参考资料

- [已验证: 官方文档, source.android.com/docs/core/graphics/tracing-win-transitions]
- [已验证: 官方文档, source.android.com/docs/core/graphics/winscope/capture/winscope]
- [已验证: 官方文档, source.android.com/docs/core/graphics/winscope/capture/adb]
- [已验证: 官方文档, source.android.com/docs/core/graphics/winscope/analyze/sf]
- [已验证: 官方文档, source.android.com/docs/core/graphics/winscope/analyze/search]
- [已验证: 官方文档, source.android.com/docs/core/graphics/surfaceflinger-windowmanager]
- [来源: intake/daily-info/2026-05-19.md]
