---
title: "功耗与包体积案例集"
chapter: "25.9"
section: "25.9"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-12"
last_verified_against: "Android Developers power / vitals / APK size docs + AOSP android-17.0.0_r1 + Clippings structure references"
confidence: medium-high
drafted_date: "2026-05-14"
polish_count: 1
task2b_state: fixed
task6_state: revisiting
task9_state: reviewed
pipeline_stage: task6_pending
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/power/setup-battery-historian"
  - type: official
    path: "https://developer.android.com/studio/profile/power-profiler"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/excessive-wakelock"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/stuck-wakelock"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/wakeup"
  - type: official
    path: "https://developer.android.com/develop/background-work/background-tasks/awake/wakelock/identify-wls"
  - type: official
    path: "https://developer.android.com/studio/debug/apk-analyzer"
  - type: official
    path: "https://developer.android.com/tools/apkanalyzer"
  - type: official
    path: "https://developer.android.com/topic/performance/reduce-apk-size"
  - type: official
    path: "https://developer.android.com/topic/performance/app-optimization/customize-which-resources-to-keep"
  - type: official
    path: "https://developer.android.com/ndk/guides/abis"
  - type: official
    path: "https://developer.android.com/guide/app-bundle"
  - type: official
    path: "https://developer.android.com/guide/practices/page-sizes"
  - type: official
    path: "https://source.android.com/docs/core/power/power-stats-hal"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/BatteryStatsService.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/power/PowerManagerService.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/apex/jobscheduler/service/java/com/android/server/alarm/AlarmManagerService.java"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 如何才能做好 Android 性能优化？.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 资源文件的体积优化实战.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - so 文件的体积优化实战.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - dex 文件的体积优化实战.md"
tags: [case-study, power, wakelock, apk-size, optimization, release-gate]
related_chapters: ["25.1", "25.2", "25.3", "25.6", "25.7", "25.8", "11.1", "11.2", "14.11"]
task2b_result: fixed-lite
last_task2b_lite_at: "2026-05-31"
reviewed_by: openclaw-task6
reviewed_date: "2026-06-02"
task6_result: pass-light-edit
task6_reviewed_at: "2026-06-02T07:07:00+08:00"
task6_reviewed_by: openclaw-task6
last_task6_at: "2026-06-02T07:07:00+08:00"
last_task6_review_log: "logs/review/2026-06-02-07-review.md"
task6_review_notes: "2026-06-02 07:07 Task6：L1/L2 复审通过，未发现新增回炉项；Task9 已 pass-tech-review 且 queue 无 pending，自动晋升 finalized。"
task9_result: auto-fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-31"
last_task9_at: "2026-07-12T01:24:48+08:00"
last_task9_audit: "2026-07-12"
last_task9_audit_at: "2026-07-12T01:24:48+08:00"
last_task9_audit_log: "logs/deep-review/2026-07-12-01-audit.md"
last_task9_audit_result: "auto-fixed"
last_task9_audit_notes: "idle audit auto-fix: AOSP source anchors updated from android-16.0.0_r1/unversioned paths to android-17.0.0_r1; BatteryStatsService, PowerManagerService, and AlarmManagerService paths verified under Android 17 tag; no queue item added."
last_task9_autofix_at: "2026-07-12"
last_task9_review_log: "logs/deep-review/2026-05-31-11-deep-review.md"
task9_review_notes: "2026-05-31 Task9：pass-tech-review。P0 0 / P1 4 / P2 6；原理链完整性需补系统证据到业务归因映射，知识盲区需补厂商差异和Android 17特性，数据支撑需真实案例。自动晋升 finalized条件不满足（有P1问题）。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-01
---

# 功耗与包体积案例集

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 后台功耗异常排查实战
- 🔹 APK 体积从 100 MB 到 50 MB 的优化路径
- 🔹 WakeLock 泄漏导致的电量投诉治理

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要看功耗与包体积案例集

前面几节已经把功耗诊断、后台限制、WakeLock / Alarm、WorkManager、定位、APK 分析、R8、AAB 分发分别讲完。现在需要把这些工具放进几个完整场景，说明排查顺序、取舍点和发布守门方式。

案例写法保持一个边界：不编造某个项目的真实收益，不把参考书里的例子改头换面放进正文。这里给的是可复现的排查账本和判断模板，项目里的实际数字要用自己的 release 包、bugreport、Perfetto、Play Console Vitals 和灰度数据填进去。

《Android 性能优化》把包体积拆成 dex、资源、`.so` 三类产物，再按精简、压缩、动态化处理；这个结构适合迁移到案例复盘里。功耗部分参考它的系统化组织方式，但事实验证以 Android Developers、AOSP 和前面 §25.1-§25.8 已验证内容为准。

## 后台功耗异常排查实战

后台功耗投诉通常从一句“升级后更耗电”开始，工程上要先把它改写成可验证问题：哪个版本、哪类设备、哪个时间窗口、App 在前台还是后台、屏幕是否关闭、网络和定位是否活跃、是否伴随 WakeLock 或 Alarm。没有这个转换，后面只会在日志、线程和业务代码之间来回猜。

本案例采用一个常见场景：用户升级后反馈夜间待机掉电变快，App 本身没有长时间前台任务。排查从 §25.1 的功耗诊断流程开始，不重复 BatteryStats 和 Perfetto 的基础用法。

| 步骤 | 产物 | 要回答的问题 | 进入下一步的条件 |
|------|------|--------------|------------------|
| 复现场景 | 固定设备、固定版本、息屏 30-60 分钟 | 候选版本是否比基线多唤醒 | 同机、同网络、同亮度、电量区间接近 |
| 采集系统证据 | `bugreport.zip`、`batterystats.txt`、Perfetto trace | 异常归到 CPU、网络、GPS、WakeLock、Alarm 中哪一类 | UID 级统计或时间线出现明显差异 |
| 对齐业务事件 | 任务平台日志、网络日志、定位日志、前台服务日志 | 哪个业务动作触发后台活动 | 事件时间与系统功耗信号重合 |
| 修改代码 | 调度约束、重试退避、取消条件、批处理 | 是否减少无用户价值的后台活动 | 候选包复测指标回到基线附近 |
| 建守门 | nightly / 灰度功耗看板 | 后续版本是否复发 | 指标能按版本、设备、业务负责人拆分 |

采集命令只保留最小集合。它们负责把证据拿回来，判断仍要放到时间线里完成。

```bash
adb shell dumpsys batterystats --reset
adb shell dumpsys batterystats --enable full-wake-history
# 断开 USB，执行固定后台场景
adb bugreport bugreport-background-power.zip
adb shell dumpsys batterystats --charged > batterystats-charged.txt
adb shell dumpsys batterystats --history > batterystats-history.txt
```

`--enable full-wake-history` 适合短时复现；长时间压测会增加历史记录量，脚本要控制采样窗口。导出后先按目标 UID 查 CPU time、WakeLock、network、GPS、Job / Sync / Alarm 记录，再回到 Perfetto 里看同一时间段的线程、网络包和 power rail。Power Profiler 读取 ODPM 设备的 power rail 数据，Pixel 6 及之后机型和部分支持 ODPM 的设备更容易拿到完整轨道。

判断时不要盯一个总耗电百分比。总耗电会受屏幕、信号、温度、系统后台任务影响。更稳的判断是“候选版本相比基线新增了什么行为”：例如息屏后新增周期网络请求、某个 Worker 重试未退避、定位请求没有在页面退出后释放、Alarm 唤醒后又启动一段异步任务。

| 观察结果 | 常见根因 | 修复方向 | 回归指标 |
|----------|----------|----------|----------|
| 息屏后 `cpu_running` 密集出现，但网络和 GPS 不高 | 后台轮询、日志压缩、数据库扫描、锁等待 | 改成 WorkManager 约束任务；页面退出取消；重试指数退避 | UID CPU time、线程运行时长、Worker 执行次数 |
| `network` 出现小而密的脉冲 | 心跳、失败重试、日志上报、HTTPDNS 刷新 | 批量上报；弱网退避；按网络类型限制；缓存读取优先 | 请求次数、radio active 时间、失败重试队列长度 |
| `gps` 或 sensor 在后台连续活跃 | 定位监听未移除、地图 SDK 生命周期错误、运动场景未停止 | 页面不可见降频；用 geofence / passive / batched location 替代持续高精度 | GNSS active 时间、定位请求间隔、前后台状态 |
| WakeLock 跨过场景结束点 | 异常路径未释放、异步回调丢失、系统 API 归因到 App | 统一封装；固定 tag；超时；释放路径审计 | WakeLock 持有时长、held 状态、Vitals 趋势 |
| Alarm 密集唤醒 | 固定周期精确 Alarm、任务拆得过碎、取消失败 | 非精确窗口；合并提醒；取消等价 PendingIntent | wakeup alarm 次数、Alarm tag、触发间隔 |

## APK 体积从 100 MB 到 50 MB 的优化路径

“100 MB 到 50 MB”不能靠单个开关承诺。更稳妥的做法是先建立体积账本，再按 dex、资源、`.so`、assets、分发形态分别找收益。参考书按 dex / 资源 / `.so` 三类产物组织包体积优化，这个结构适合做第一版账本；现代工程还要补 AAB、dynamic feature、asset pack、16 KB page size 和渠道包边界。

体积账本要同时记录 raw file size、download size、安装后占用和功能覆盖范围。APK Analyzer 文档说明它会展示 zipped / raw file size 与 download file size；命令行可以用 `apkanalyzer` 和 `bundletool` 生成 CI 可读结果。

```bash
apkanalyzer -h apk file-size app-release.apk
apkanalyzer -h apk download-size app-release.apk

bundletool build-apks --bundle=app-release.aab --output=app-release.apks
bundletool get-size total --apks=app-release.apks --device-spec=pixel-8.json
```

第一版账本可以这样填。表里的“本轮实测”必须来自项目构建产物，不使用网上案例数字。

| 产物 | 常见来源 | 排查工具 | 可用动作 | 本轮实测 |
|------|----------|----------|----------|----------|
| `classes*.dex` | 业务代码、三方 SDK、过宽 keep 规则、生成代码 | APK Analyzer、R8 `usage.txt`、`configuration.txt`、`-whyareyoukeeping` | R8 全模式、收窄 keep、拆 SDK、删除废弃模块 | 由项目填写 |
| `res/` 与 `resources.arsc` | 多密度图片、重复图片、未使用资源、多语言、多主题 | APK Analyzer、lint、资源缩减报告 | `isShrinkResources`、WebP / AVIF、VectorDrawable、`tools:keep`、密度 / 语言过滤 | 由项目填写 |
| `assets/` | 离线包、模型、字体、Web 资源、配置大文件 | APK Analyzer、文件 hash、业务访问日志 | 按需下载、字体子集化、首启后加载、CDN / asset pack | 由项目填写 |
| `lib/<abi>/` | 多 ABI 副本、debug symbol、低频 native 能力 | APK Analyzer、NDK symbol 文件、ABI 占比 | App Bundle / split、strip symbol、低频功能动态下发、16 KB 对齐检查 | 由项目填写 |
| 分发形态 | universal APK、国内渠道单 APK、Google Play AAB | bundletool、渠道安装验证 | AAB、dynamic feature、universal APK 回退方案、多 APK | 由项目填写 |

实际执行按风险从低到高排列。

1. **打开官方 shrink 路径**：release 包启用 R8 和资源缩减。Android Developers 明确说明构建过程中先由 R8 移除无用代码，再由 Android Gradle Plugin 移除无用资源；资源缩减要和代码缩减一起使用。
2. **处理明显重复产物**：删除无用资源、重复图片、多余语言 / 密度资源，排查 `assets/` 里的旧离线包和未使用字体。动态资源名通过 `res/raw/*.keep.xml` 明确保留，避免 shrink 后线上缺资源。
3. **收窄 dex 与依赖**：从 APK Analyzer 的 dex 包名增长项开始，检查三方 SDK 是否只用少量能力却带入整套库；再查 consumer rules 是否把大包固定住。R8 规则细节见 §25.7。
4. **治理 native 库**：NDK 文档说明 fat APK 会比单 ABI APK 大很多，建议使用 App Bundle 或 APK Splits，在保持兼容的同时减少下载体积。release 包还要移除不必要 debug symbol，并归档 symbol 给 native crash 还原。
5. **拆分低频能力**：OCR、地图、视频编辑、模型推理、小游戏资源这类低频大模块，优先评估 dynamic feature、Play Asset Delivery 或国内渠道的自研按需下载。AAB 支持按条件或运行时下载 feature module，大型资源可用 asset pack 的 install-time、fast-follow、on-demand 模式。
6. **补兼容门禁**：Android 15 起 16 KB page size 设备成为 native 库兼容风险点；如果 APK 包含 `.so`，要检查 ELF segment alignment，`zipalign -P 16` 可用于让 `.so` 适配 16 KiB 与 4 KiB page 设备。

下面这段 Gradle 配置只是 release 基线，不代表所有项目都能直接把体积减半。读者重点看代码缩减和资源缩减必须配套开启。

```kotlin
android {
    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
}
```

配置打开后要跑 release 冒烟测试。需要覆盖反射、JSON / protobuf、Room、Hilt、Retrofit、深链、推送、JNI、换肤、通知图标、WebView bridge、动态页面和多语言。包体积案例里最危险的事故，是 shrink 后下载体积降了，但运行时入口被删或动态资源丢失。

一份“100 MB 到 50 MB”的计划更适合写成预算表，避免写成承诺收益：

| 阶段 | 交付物 | 通过标准 | 风险 |
|------|--------|----------|------|
| 账本阶段 | APK / AAB 体积分解、版本 diff、top 增长文件 | 能解释 90% 以上体积来源 | 只看 APK raw size，忽略 download size 和安装后占用 |
| 低风险清理 | 无用资源、重复资源、废弃 assets、明显多余 ABI | release 冒烟测试通过，下载体积下降 | 动态资源名误删 |
| 规则收窄 | R8 keep、consumer rules、依赖替换 | `usage.txt` 和线上功能覆盖一致 | 反射、序列化、JNI 失败 |
| 分发拆分 | AAB / dynamic feature / asset pack / 渠道 APK | 代表设备安装、首启、按需下载都通过 | 国内渠道不支持 split session，误把 config split 当独立 APK |
| 发布守门 | CI 体积阈值、模块负责人、版本 diff 报告 | 新增大文件必须说明来源和下发策略 | 只在版本末期突击瘦身 |

这个案例的收尾标准不能停在“文件变小”四个字。每个大项都要有负责人、阈值、测试用例和回滚方案。体积治理一旦接入发版流程，后续版本只处理增量；不接门禁，几个月后还会回到 100 MB。

## WakeLock 泄漏导致的电量投诉治理

WakeLock 泄漏的特征是明确的：用户看不到任务，设备却无法进入应有的低功耗状态。Android Vitals 对后台 Partial WakeLock 有两类视角：excessive partial wake lock 和 stuck partial wake lock。前者关注 24 小时内后台 Partial WakeLock 累计持有至少 2 小时，且 28 天内影响超过 5% session 的坏行为阈值；后者关注 24 小时内至少一次后台持续 1 小时的 Partial WakeLock。Vitals 只统计非豁免的后台或前台服务中持有的 wake lock，音频、定位、JobScheduler 用户发起 API 等场景有豁免。

治理从 Play Console 或本地复现都能开始，但两个入口的侧重点不同。

| 入口 | 适合回答的问题 | 证据 | 局限 |
|------|----------------|------|------|
| Play Console Vitals | 哪个版本、设备、WakeLock tag 影响用户面最大 | affected sessions、duration、wake lock names | 聚合延迟高，无法直接给代码栈 |
| 本地 `dumpsys power` | 复现场景结束后锁是否仍 held | 当前 WakeLock、uid、tag | 只看当前状态，错过历史可能没有证据 |
| `dumpsys batterystats --history` | acquire / release 是否成对，何时跨过息屏窗口 | 历史事件、UID 统计 | 需要固定场景和时间标记 |
| Perfetto / Power Profiler | WakeLock 附近 CPU、网络、Alarm 是否同步活跃 | 时间线、线程、power rail | 需要设备支持和 trace 配置 |
| Background Task Inspector | WorkManager 等库持锁情况 | 后台任务和 wake lock 视角 | 依赖调试环境，不替代线上趋势 |

Android Developers 的 wake lock 归因文档提醒：App 不直接调用 `PowerManager.newWakeLock()`，也可能因为 WorkManager、JobScheduler、DownloadManager、AlarmManager、定位、FCM、媒体播放等 API 产生归因到 App 的 WakeLock。WorkManager worker 在后台执行时获取的 WakeLock 会归因到创建 worker 的 App；AlarmManager 的 wakeup alarm 触发时，系统会让设备离开低功耗状态并持有 Partial WakeLock。

排查顺序可以压成五步：

1. **先确认 tag**：Vitals 或 `dumpsys power` 中的 tag 是否能映射到业务模块。无意义 tag 先改命名规范，否则下一轮仍难归因。
2. **再看生命周期**：持锁开始时间、释放时间、场景结束时间是否成对。重点查异常、取消、超时、进程切后台、网络回调丢失。
3. **区分直接锁和系统归因锁**：直接锁查 `PowerManager.WakeLock` 封装；系统归因锁查 WorkManager、Alarm、下载、定位和媒体 API。
4. **修持锁模型**：能交给 WorkManager 的任务不要手写 WakeLock；必须手写时固定 tag、带超时、`try/finally` 释放、封装在单一负责人里。
5. **接发布守门**：新增 WakeLock、Exact Alarm、长时间后台 worker 都要进入 review；灰度看 Vitals 和自建 APM 的趋势。

AOSP 侧可以用 §25.3 已验证的入口理解责任边界：`PowerManagerService` 负责系统 WakeLock 状态管理，`BatteryStatsService` / BatteryStats 体系记录归因统计，`AlarmManagerService` 负责 Alarm 触发与唤醒相关行为。正文只引用路径，不在本节展开实现。

WakeLock 治理的代码审查清单要比“有没有 release”更细：

| 检查项 | 合格写法 | 失败信号 |
|--------|----------|----------|
| tag | 包名或模块名前缀 + 稳定业务名 | `wakelock`、`service`、随机数、用户信息 |
| 负责人 | 单一模块创建、释放、上报 | 多模块共享一把全局锁 |
| 超时 | `acquire(timeout)` 只作兜底，业务完成仍主动释放 | 只依赖超时释放，任务失败时不记录原因 |
| 异常路径 | `finally`、取消回调、超时回调都释放 | 网络回调、协程取消、线程池拒绝后锁仍 held |
| 替代 API | WorkManager / JobScheduler / DownloadManager / FGS 能覆盖时优先使用 | 后台同步、周期任务、下载都手写锁 |
| 观测字段 | tag、owner、trigger、acquire / release uptime、timeout、visible_to_user | 线上只看到耗电，无法映射业务 |

## 本节小结

功耗与体积案例的共性是“先建账，再修代码”。功耗账本记录时间窗口、UID、硬件入口、业务触发源和回归指标；体积账本记录 dex、资源、assets、`.so`、分发形态和版本 diff。没有账本，优化只能靠经验猜。

本节产出的三个模板可以直接放进团队流程：后台功耗排查表、APK 体积预算表、WakeLock 审计表。落到团队流程后，重点看两件事：是否有未验证的技术断言，是否把项目实测数据和示例模板混在一起。
