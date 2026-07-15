---
title: "EyeDropper API 与跨设备协作性能"
chapter: "18.21"
status: ready-for-review
applicable_versions: "Android 17 (API 37)"
task9_result: needs-rework
task9_reviewed_date: "2026-04-24"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-04-24T08:27:00+08:00"
last_task9_audit: "2026-07-15"
tags: [eyedropper, activity-result, color-picking, system-ui, collaboration]
related_chapters: ["2.6", "8.2", "18.20"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-10"
gap_source: "官方文档+新特性"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/reference/android/content/Intent#ACTION_OPEN_EYE_DROPPER"
    title: "Intent.ACTION_OPEN_EYE_DROPPER"
    date: "2026"
  - type: official
    path: "https://developer.android.com/reference/android/content/Intent#EXTRA_COLOR"
    title: "Intent.EXTRA_COLOR"
    date: "2026"
  - type: official
    path: "https://developer.android.com/training/basics/intents/result"
    title: "Get a result from an activity"
    date: "2026"
pipeline_stage: task9_pending
task6_state: reviewed
task9_state: pending
task2b_state: fixed
reviewed_by: openclaw-task6
reviewed_date: 2026-07-15
last_task6_at: "2026-07-15T08:15:00+08:00"
task6_result: pass-light-edit
last_task6_audit: "2026-07-15"
task2b_result: fixed-lite
last_task2b_lite_at: "2026-07-15"
---

# EyeDropper API 与跨设备协作性能

## 这章要解决什么问题

Android 17 提供了一个通过 Intent 拉起的系统级取色入口。公开 API 没有提供可实例化的 `EyeDropper` 对象。工程上要掌握的重点是四件事：启动入口、结果读取、隐私边界、以及跨设备协作时应用自己要承担的同步工作。

公开 API 只保证两件东西：`Intent.ACTION_OPEN_EYE_DROPPER` 用来拉起系统取色器，`Intent.EXTRA_COLOR` 用来回传 ARGB 颜色值。系统不会把完整屏幕像素流交给应用，也没有公开的跨设备同步 API。

## 真实调用链

对调用方来说，流程很短：`Intent.ACTION_OPEN_EYE_DROPPER` → 系统取色界面 → 用户点选像素 → activity result 回传 `Intent.EXTRA_COLOR`。

### App 侧入口

下面这段代码只演示真实的启动和回调路径，重点看 `ACTION_OPEN_EYE_DROPPER`、`EXTRA_COLOR` 和降级分支。

```kotlin
class EditorActivity : ComponentActivity() {

    private val eyeDropperLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            if (result.resultCode != Activity.RESULT_OK) return@registerForActivityResult

            val color = result.data?.getIntExtra(
                Intent.EXTRA_COLOR,
                Color.TRANSPARENT
            ) ?: return@registerForActivityResult

            applyPickedColor(color)
        }

    fun openSystemEyeDropper() {
        if (Build.VERSION.SDK_INT < 37) {
            openInAppColorPicker()
            return
        }

        val intent = Intent(Intent.ACTION_OPEN_EYE_DROPPER)
        if (intent.resolveActivity(packageManager) == null) {
            openInAppColorPicker()
            return
        }

        eyeDropperLauncher.launch(intent)
    }
}
```

应用拿到的是一个 `0xAARRGGBB` 格式的整型颜色值。取色界面的宿主 Activity、覆盖层形态和内部控制器属于系统实现细节，公开文档没有承诺固定的类名和进程边界。

### 系统负责的部分

`Intent.ACTION_OPEN_EYE_DROPPER` 的文档给了两个硬边界：

- 颜色结果通过 activity result 回传，读取键是 `Intent.EXTRA_COLOR`
- secure window 和 protected buffer 上的像素会被涂黑，应用拿不到这些内容的真实颜色

EyeDropper 解决的是“用户明确点一次，系统返回一个颜色值”这个场景。它不等价于屏幕截图，也不等价于持续采样。

## 为什么不需要屏幕捕获授权

EyeDropper 不把整帧图像交给调用方。应用最终只收到一个颜色值，像素采样和安全内容裁剪都由系统侧完成。

从权限边界看，它和 MediaProjection 是两条不同的路：

| 方案 | 应用拿到的数据 | 用户确认方式 | 适用场景 |
|:---|:---|:---|:---|
| EyeDropper | 单个 ARGB 颜色值 | 用户在系统取色界面中点选 | 取一个颜色、吸色笔、配色 |
| 应用内取色器 | 应用自己的 View / Bitmap 像素 | 无额外系统确认 | 只在应用内容内取色 |
| MediaProjection | 屏幕图像流 | 系统屏幕捕获授权 | 录屏、远程协作、全屏分析 |

如果产品需求是连续采样、批量颜色分析、远端屏幕共享，EyeDropper 不能替代 MediaProjection。它的边界更窄，换来的是更小的数据面和更直接的隐私隔离。

## 性能和可观测性该怎么理解

### 默认没有公开保证的 EyeDropper 专属 Trace 标记

公开 API 文档只定义了 Intent action 和 result extra，没有定义稳定的 Perfetto slice 名、counter 名，AOSP 公开资料里也还缺少系统宿主组件的固定锚点。实战里如果直接按 EyeDropper 相关关键字去搜系统 slice，通常得不到可靠结果。

更稳妥的做法是把观测口径放在调用链两端：

- App 发起 `eyeDropperLauncher.launch()` 的时刻
- App 收到 `Intent.EXTRA_COLOR` 并更新 UI 的时刻
- 取色界面弹出和返回期间，调用方页面的 FrameTimeline 是否出现额外 jank

### 建议的打点方式

如果要量化“点开系统取色器到拿回颜色”的耗时，直接在应用侧补自定义 trace marker。下面的代码只做一件事，给 launch 和 result callback 各留一个稳定锚点。

```kotlin
fun openSystemEyeDropper() {
    Trace.beginSection("eye_dropper_launch")
    try {
        eyeDropperLauncher.launch(Intent(Intent.ACTION_OPEN_EYE_DROPPER))
    } finally {
        Trace.endSection()
    }
}

private fun onEyeDropperResult(result: ActivityResult) {
    Trace.beginSection("eye_dropper_result")
    try {
        if (result.resultCode != Activity.RESULT_OK) return
        val color = result.data?.getIntExtra(Intent.EXTRA_COLOR, Color.TRANSPARENT) ?: return
        applyPickedColor(color)
    } finally {
        Trace.endSection()
    }
}
```

这样抓 Perfetto 时，至少可以稳定回答两个问题：

- 系统取色器拉起到结果回调，中间隔了多久
- 返回结果后，应用自己的配色刷新有没有把主线程或 RenderThread 顶慢

如果没有应用侧打点，只靠系统默认 Trace，通常只能看到普通 activity / window transition 和显示合成片段，难以把取色流程单独摘出来。

## 跨设备协作怎么实现

当前公开 API 到 `Intent.EXTRA_COLOR` 为止。跨设备协作需要应用自己补后一段流程，把已经选中的颜色值同步给另一台设备。系统取色器本身仍然只在本地设备上工作。

工程上更可控的做法是：

- 本地设备完成一次 EyeDropper 取色，得到 `argb`
- 把 `argb`、时间戳、会话 ID 这类小负载发到已有协作通道，比如 WebSocket、Nearby、WebRTC 或业务后端
- 远端设备只消费颜色结果，按自己的 UI 状态更新色板、画笔或选中态

这段流程里，网络带宽通常不是瓶颈。颜色值本身只有几个字节，真正要控制的是同步频率、重复事件合并、以及远端 UI 回放节奏。把截图、放大镜位置、持续采样流一起同步，会把问题从“配色协作”扩大成“屏幕共享”。

## 降级策略和边界

- API 下限是 Android 17 / API 37。更老的设备继续走应用内取色器或导入图片取色。
- `ACTION_OPEN_EYE_DROPPER` 在 Android 17（API 37）引入，截至 `android-17.0.0_r1` 仍可用，但在 main 分支（Android 18+）中尚未确认其保留状态。工程实现中应将 `resolveActivity()` 检查作为运行时前置条件，不要硬编码对该 API 的存在性假设。
- AIW 版本边界为 Android 17 / API 37。本章结论不覆盖 Android 18 / API 38 及更高版本，该 API 在后续版本中的行为以官方文档为准。
- 取色结果依赖系统提供的处理器。防御式代码仍然应该保留 `resolveActivity()` 或异常兜底。
- secure window 和 protected buffer 会被涂黑，不能把 EyeDropper 当成绕过内容保护的入口。
- EyeDropper 面向用户显式操作，不适合后台自动化或高频批量取样。

## 参考资料

- [Intent.ACTION_OPEN_EYE_DROPPER](https://developer.android.com/reference/android/content/Intent#ACTION_OPEN_EYE_DROPPER)
- [Intent.EXTRA_COLOR](https://developer.android.com/reference/android/content/Intent#EXTRA_COLOR)
- [Get a result from an activity](https://developer.android.com/training/basics/intents/result)
