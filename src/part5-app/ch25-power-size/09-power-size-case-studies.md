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
task6_state: reviewed
task9_state: reviewed
pipeline_stage: ready-to-publish
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
reviewed_date: "2026-07-12"
task6_result: pass-light-edit
task6_reviewed_at: "2026-06-02T07:07:00+08:00"
task6_reviewed_by: openclaw-task6
last_task6_at: "2026-07-12T04:10:00+08:00"
last_task6_review_log: "logs/review/2026-06-02-07-review.md"
task6_review_notes: "2026-07-12 04:10 Task6 revisiting-review: pass-light-edit。修复禁用词对齐→关联（1处）；L1/L2 通过，无新增回炉项。Task9 result=auto-fixed，不满足自动晋升条件。"
task9_result: pass-tech-review
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-07-12"
last_task9_at: "2026-07-12T04:28:18+08:00"
last_task9_audit: "2026-07-12"
last_task9_audit_at: "2026-07-12T01:24:48+08:00"
last_task9_audit_log: "logs/deep-review/2026-07-12-01-audit.md"
last_task9_audit_result: "auto-fixed"
last_task9_audit_notes: "idle audit auto-fix: AOSP source anchors updated from android-16.0.0_r1/unversioned paths to android-17.0.0_r1; BatteryStatsService, PowerManagerService, and AlarmManagerService paths verified under Android 17 tag; no queue item added."
last_task9_autofix_at: "2026-07-12"
last_task9_review_log: "logs/deep-review/2026-07-12-04-deep-review.md"
task9_review_notes: "2026-07-12 Task9 deep-review：pass-tech-review。按 Android 17/API 37 边界复核功耗、WakeLock、Alarm 与包体积案例；AOSP 锚点和官方阈值描述无 P0/P1，queue 无 pending，已自动晋升 finalized。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-12
---

# 功耗与包体积案例集

## 案例的使用方式

前面几节已经把功耗诊断、后台限制、WakeLock / Alarm、WorkManager、定位、APK 分析、R8、AAB 分发分别讲完。现在需要把这些工具放进几个完整场景，说明排查顺序、取舍点和发布守门方式。

这里给出可复现的排查模板。数字必须来自项目自己的 release 制品、bugreport、Perfetto、Play Console Vitals 和灰度数据，不能把示例目标写成普遍收益。

正文的平台行为以 Android 17（API 37）和 `android-17.0.0_r1` 为锚点。功耗案例使用框架层归因与调度入口；没有把 kernel 实现当作应用 UID 功耗结论的直接依据。

## 后台功耗异常排查实战

后台功耗投诉通常从一句“升级后更耗电”开始，工程上要先把它改写成可验证问题：哪个版本、哪类设备、哪个时间窗口、App 在前台还是后台、屏幕是否关闭、网络和定位是否活跃、是否伴随 WakeLock 或 Alarm。没有这个转换，后面只会在日志、线程和业务代码之间来回猜。

本案例采用一个常见场景：用户升级后反馈夜间待机掉电变快，App 本身没有长时间前台任务。排查从 §25.1 的功耗诊断流程开始，不重复 BatteryStats 和 Perfetto 的基础用法。

| 步骤 | 产物 | 要回答的问题 | 进入下一步的条件 |
|------|------|--------------|------------------|
| 复现场景 | 固定设备、固定版本、项目约定的息屏窗口 | 候选版本是否比基线多唤醒 | 同机、同网络、同亮度、电量区间接近 |
| 采集系统证据 | `bugreport.zip`、`batterystats.txt`、Perfetto trace | 异常归到 CPU、网络、GPS、WakeLock、Alarm 中哪一类 | UID 级统计或时间线出现明显差异 |
| 关联业务事件 | 任务平台日志、网络日志、定位日志、前台服务日志 | 哪个业务动作触发后台活动 | 事件时间与系统功耗信号重合 |
| 修改代码 | 调度约束、重试退避、取消条件、批处理 | 是否减少无用户价值的后台活动 | 候选包复测指标回到基线附近 |
| 建守门 | nightly / 灰度功耗看板 | 后续版本是否复发 | 指标能按版本、设备、业务负责人拆分 |

下面的命令清空旧统计、打开完整 WakeLock 历史，再导出本轮场景的 bugreport、聚合统计和事件历史。

```bash
adb shell dumpsys batterystats --reset
adb shell dumpsys batterystats --enable full-wake-history
# 断开 USB，执行固定后台场景
adb bugreport bugreport-background-power.zip
adb shell dumpsys batterystats --charged > batterystats-charged.txt
adb shell dumpsys batterystats --history > batterystats-history.txt
```

`--reset` 会清除已有 BatteryStats 数据，不能在保留现场之前执行；`full-wake-history` 不跨重启保存，只适合受控复现。导出后按目标 UID 查 CPU 时间、WakeLock、网络、GPS、Job、Sync 和 Alarm，再回到 Perfetto 对齐同一时间段的线程与系统事件。

Battery Historian 官方页面已经标注“不再积极维护”，新排查应优先使用 System Trace、Macrobenchmark 功耗指标或 Power Profiler；旧项目仍可用 Historian 阅读 Batterystats 时间线。Power Profiler 的 ODPM power rail 是整机数据，不是单个应用的计量结果；当前官方支持范围是运行 Android 10 及以上的 Pixel 6 及后续 Pixel 设备，具体 rail 仍由设备决定。

总耗电百分比会受屏幕、信号、温度和系统后台任务影响。判断应比较候选版本相对基线新增的行为，例如息屏后出现周期网络请求、Worker 重试没有退避、定位监听未在页面退出后移除，或者 Alarm 唤醒后继续运行异步任务。

| 观察结果 | 常见根因 | 修复方向 | 回归指标 |
|----------|----------|----------|----------|
| 息屏后 `cpu_running` 密集出现，但网络和 GPS 不高 | 后台轮询、日志压缩、数据库扫描、锁等待 | 取消无价值轮询；可延迟的可靠任务使用 WorkManager；重试指数退避 | UID CPU 时间、线程运行时长、Worker 执行次数 |
| `network` 出现小而密的脉冲 | 心跳、失败重试、日志上报、HTTPDNS 刷新 | 批量上报；弱网退避；按网络类型限制；优先读取本地缓存 | 请求次数、移动网络 radio active 时间、失败重试队列长度 |
| `gps` 或 sensor 在后台连续活跃 | 定位监听未移除、地图 SDK 生命周期错误、运动场景未停止 | 页面不可见降频；用 geofence / passive / batched location 替代持续高精度 | GNSS active 时间、定位请求间隔、前后台状态 |
| WakeLock 跨过场景结束点 | 异常路径未释放、异步回调丢失、系统 API 归因到 App | 统一封装；固定 tag；超时；释放路径审计 | WakeLock 持有时长、held 状态、Vitals 趋势 |
| Alarm 密集唤醒 | 固定周期精确 Alarm、任务拆得过碎、取消失败 | 非精确窗口；合并提醒；取消等价 PendingIntent | wakeup alarm 次数、Alarm tag、触发间隔 |

## APK 体积从 100 MB 到 50 MB 的优化路径

“100 MB 到 50 MB”是案例目标，不是打开某个开关后的固定收益。开始修改前先建立体积账本，再按 dex、资源、`.so`、assets 和分发形态逐项计算可回收空间。现代工程还要记录 AAB、Dynamic Feature、asset pack、16 KB page size 和渠道包边界。

体积账本要同时记录文件原始大小、压缩后大小、下载体积估算、安装后占用和功能覆盖范围。下面的命令读取 APK 总大小与下载体积估算，并按连接设备的规格估算 AAB 首次交付体积。

```bash
apkanalyzer -h apk file-size app-release.apk
apkanalyzer -h apk download-size app-release.apk

bundletool get-device-spec --output=device-spec.json
bundletool build-apks --bundle=app-release.aab --output=app-release.apks
bundletool get-size total \
  --apks=app-release.apks \
  --device-spec=device-spec.json
```

`apkanalyzer apk download-size` 给出 APK 下载大小估算。`bundletool get-size total` 统计指定设备的 APK Set，默认包含首次下载时安装的所有 module；两者口径不同。未传 keystore 的 `build-apks` 会尝试使用 debug key，本例产物只用于本地分析。

第一版账本可以这样填。表里的“本轮实测”必须来自项目构建产物，不使用网上案例数字。

| 产物 | 常见来源 | 排查工具 | 可用动作 | 本轮实测 |
|------|----------|----------|----------|----------|
| `classes*.dex` | 业务代码、三方 SDK、过宽 keep 规则、生成代码 | APK Analyzer、R8 `usage.txt`、`configuration.txt`、`-whyareyoukeeping` | R8 全模式、收窄 keep、拆 SDK、删除废弃模块 | 由项目填写 |
| `res/` 与 `resources.arsc` | 多密度图片、重复图片、未使用资源、多语言、多主题 | APK Analyzer、lint、资源缩减报告 | `optimization.enable`、WebP / AVIF、VectorDrawable、精确保留规则、密度 / 语言过滤 | 由项目填写 |
| `assets/` | 离线包、模型、字体、Web 资源、配置大文件 | APK Analyzer、文件哈希、业务访问日志 | 按需下载、字体子集化、首启后加载、CDN / asset pack | 由项目填写 |
| `lib/<abi>/` | 多 ABI 副本、调试符号、低频 native 能力 | APK Analyzer、NDK 符号文件、ABI 占比 | App Bundle / split、发布包剥离符号、随功能模块交付、16 KB 对齐检查 | 由项目填写 |
| 分发形态 | universal APK、国内渠道单 APK、Google Play AAB | bundletool、渠道安装验证 | AAB、dynamic feature、universal APK 回退方案、多 APK | 由项目填写 |

实际执行按风险从低到高排列。

1. **启用应用优化**：release 变体同时启用 R8 代码优化和资源优化。AGP 9.3 的新 DSL 用一个 `optimization` 块控制两者；旧 DSL 仍受支持，但不能只开资源缩减而关闭代码缩减。
2. **处理明显重复产物**：删除无用资源、重复图片、多余语言或密度资源，排查 `assets/` 里的旧离线包和未使用字体。通过字符串拼接访问的资源需要精确保留，不要用覆盖整个资源目录的宽规则。
3. **收窄 dex 与依赖**：从 APK Analyzer 的 dex 包名增长项开始，检查三方 SDK 是否只用少量能力却带入整套库；再查 consumer rules 是否把大包固定住。R8 规则细节见 §25.7。
4. **治理 native 库**：用 App Bundle 或 APK split 按 ABI 交付，避免所有设备下载全部 ABI。发布 APK 中的 `.so` 应由构建工具剥离调试符号，同时归档未剥离符号文件供 native 崩溃还原；不要手工删除 ELF section。
5. **拆分低频能力**：OCR、地图、视频编辑和模型推理等低频大模块可以评估 Dynamic Feature。非代码的大型资源可以使用 PAD；非 Play 渠道只能在渠道具备对应能力时采用 split，否则要准备单 APK 或自建非代码资源交付。
6. **检查 16 KB page size**：Android 17 设备可能采用 4 KB 或 16 KB 页。包含 native 库的应用既要检查 ELF `LOAD` 段对齐，也要检查未压缩 `.so` 在 APK 中的 ZIP 对齐；只通过其中一项仍可能无法安装或运行。

下面的命令只检查 APK 内未压缩 `.so` 的 ZIP 对齐，不检查 ELF 段本身。

```bash
zipalign -c -P 16 -v 4 app-release.apk
```

`-c` 表示只校验，不改写已签名制品。ELF 段对齐要结合 NDK 版本、链接参数和 `llvm-objdump -p libname.so` 的 `LOAD` 段结果检查，完整流程见 §25.6。

下面是 AGP 9.3 及以上的 release 优化基线。`compileSdk` 固定到 Android 17/API 37，`optimization.enable` 同时启用代码和资源优化。

```kotlin
android {
    compileSdk = 37

    buildTypes {
        release {
            optimization {
                enable = true
            }
        }
    }
}
```

使用新 DSL 时，自定义 keep rules 放在 `src/<variant>/keepRules/` 下以 `.keep` 结尾的文件中。配置打开后要跑 release 冒烟测试，覆盖反射、JSON / protobuf、Room、Hilt、Retrofit、深链、推送、JNI、换肤、通知图标、WebView bridge、动态页面和多语言。体积下降不能替代功能验证：R8 误删入口或资源优化误删动态资源都属于发布阻断问题。

一份“100 MB 到 50 MB”的计划更适合写成预算表，避免写成承诺收益：

| 阶段 | 交付物 | 通过标准 | 风险 |
|------|--------|----------|------|
| 账本阶段 | APK / AAB 体积分解、版本差异、主要增长文件 | 大体积条目均已分类，未知项有继续排查的负责人 | 只看 APK 文件大小，忽略下载估算和安装后占用 |
| 低风险清理 | 无用资源、重复资源、废弃 assets、明显多余 ABI | release 冒烟测试通过，下载体积下降 | 动态资源名误删 |
| 规则收窄 | R8 keep、consumer rules、依赖替换 | `usage.txt` 和线上功能覆盖一致 | 反射、序列化、JNI 失败 |
| 分发拆分 | AAB / Dynamic Feature / asset pack / 渠道 APK | 代表设备安装、首启、按需下载都通过 | 渠道不支持 split 安装会话，误把 configuration split 当独立 APK |
| 发布守门 | CI 体积阈值、模块负责人、版本 diff 报告 | 新增大文件必须说明来源和下发策略 | 只在版本末期突击瘦身 |

这个案例完成时，每个大项都要有负责人、项目阈值、测试用例和回滚方案。体积检查接入发版流程后，后续版本可以按基线处理增量，避免在版本末期集中清理。

## WakeLock 泄漏导致的电量投诉治理

WakeLock 泄漏的特征是：用户看不到持续任务，设备却无法进入应有的低功耗状态。Android Vitals 将两类问题分开统计：

- [Excessive partial wake locks](https://developer.android.com/topic/performance/vitals/excessive-wakelock)：所有非豁免 Partial WakeLock 在 24 小时内的后台累计时间达到 2 小时；如果 28 天内受影响的应用会话超过 5%，可能影响应用在 Play 中的曝光。
- [Stuck partial wake locks](https://developer.android.com/topic/performance/vitals/stuck-wakelock)：24 小时内出现至少一次在后台连续持有 1 小时的 Partial WakeLock。

Vitals 只累计应用位于后台或运行前台服务时的持锁时间，并豁免音频、定位和 JobScheduler 用户发起 API 等具备明确用户价值的场景。阈值用于识别线上风险，项目内的告警不应等到触线后才触发。

治理从 Play Console 或本地复现都能开始，但两个入口的侧重点不同。

| 入口 | 适合回答的问题 | 证据 | 局限 |
|------|----------------|------|------|
| Play Console Vitals | 哪个版本、设备、WakeLock tag 影响用户面最大 | 受影响会话、持有时间、WakeLock 名称 | 聚合数据有延迟，无法直接给出代码栈 |
| 本地 `dumpsys power` | 复现场景结束后锁是否仍 held | 当前 WakeLock、uid、tag | 只看当前状态，错过历史可能没有证据 |
| `dumpsys batterystats --history` | acquire / release 是否成对，何时跨过息屏窗口 | 历史事件、UID 统计 | 需要固定场景和时间标记 |
| Perfetto / Power Profiler | WakeLock 附近 CPU、网络、Alarm 是否同步活跃 | 时间线、线程、power rail | 需要设备支持和 trace 配置 |
| Background Task Inspector | Worker、Job、Alarm 和 WakeLock 的本地状态 | 任务状态、重试、持锁明细 | 依赖调试环境，不替代线上趋势 |

Android Developers 的 wake lock 归因文档提醒：App 不直接调用 `PowerManager.newWakeLock()`，也可能因为 WorkManager、JobScheduler、DownloadManager、AlarmManager、定位、FCM、媒体播放等 API 产生归因到 App 的 WakeLock。WorkManager worker 在后台执行时获取的 WakeLock 会归因到创建 worker 的 App；AlarmManager 的 wakeup alarm 触发时，系统会让设备离开低功耗状态并持有 Partial WakeLock。

排查顺序可以压成五步：

1. **先确认 tag**：Vitals 或 `dumpsys power` 中的 tag 是否能映射到业务模块。无意义 tag 先改命名规范，否则下一轮仍难归因。
2. **再看生命周期**：持锁开始时间、释放时间、场景结束时间是否成对。重点查异常、取消、超时、进程切后台、网络回调丢失。
3. **区分直接锁和系统归因锁**：直接锁查 `PowerManager.WakeLock` 封装；系统归因锁查 WorkManager、Alarm、下载、定位和媒体 API。
4. **修持锁模型**：能交给 WorkManager 的任务不要手写 WakeLock；必须手写时固定 tag、带超时、`try/finally` 释放、封装在单一负责人里。
5. **接发布守门**：新增 WakeLock、Exact Alarm、长时间后台 worker 都要进入 review；灰度看 Vitals 和自建 APM 的趋势。

Android 17 源码中的责任边界可以沿着三个入口核对：[`PowerManagerService`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/power/PowerManagerService.java) 管理系统 WakeLock 状态；[`BatteryStatsService`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/BatteryStatsService.java) 提供统计、历史与 `dumpsys batterystats` 入口；[`AlarmManagerService`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/apex/jobscheduler/service/java/com/android/server/alarm/AlarmManagerService.java) 处理 Alarm 调度、触发和唤醒。具体调用链见 §25.3，这里只用它们确认系统与应用的责任分界。

WakeLock 治理的代码审查清单要比“有没有 release”更细：

| 检查项 | 合格写法 | 失败信号 |
|--------|----------|----------|
| tag | 包名或模块名前缀 + 稳定业务名 | `wakelock`、`service`、随机数、用户信息 |
| 负责人 | 单一模块创建、释放、上报 | 多模块共享一把全局锁 |
| 超时 | `acquire(timeout)` 只作兜底，业务完成仍主动释放 | 只依赖超时释放，任务失败时不记录原因 |
| 异常路径 | `finally`、取消回调、超时回调都释放 | 网络回调、协程取消、线程池拒绝后锁仍 held |
| 替代 API | WorkManager / JobScheduler / DownloadManager / FGS 能覆盖时优先使用 | 后台同步、周期任务、下载都手写锁 |
| 观测字段 | tag、负责人、触发源、获取/释放 uptime、超时、用户是否可见 | 线上只看到耗电，无法映射业务 |

## 小结

功耗与体积案例都从可比较的基线开始。功耗记录时间窗口、UID、硬件活动、业务触发源和回归指标；体积记录 dex、资源、assets、`.so`、分发形态和版本差异。缺少这些记录时，修改前后没有统一口径。

团队可以直接复用后台功耗排查表、APK 体积预算表和 WakeLock 审计表。每次变更都要确认技术断言已有来源，并把项目实测数据与示例模板分开保存。
