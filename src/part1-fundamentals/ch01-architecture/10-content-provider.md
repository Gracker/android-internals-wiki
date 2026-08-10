---
title: ContentProvider 性能与优化
chapter: '1.10'
section: '1.10'
status: finalized
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
last_verified: '2026-07-25'
last_verified_against: AOSP android-17.0.0_r1 + Android Developers
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/content/ContentProvider.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/content/ContentResolver.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/content/ContentProviderClient.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/content/IContentProvider.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ContentProviderHelper.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ContentProviderRecord.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/ComputerEngine.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/database/CursorWindow.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/database/BulkCursorToCursorAdaptor.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/database/sqlite/SQLiteCursor.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/database/sqlite/SQLiteQuery.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/database/sqlite/SQLiteSession.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/res/res/values/config.xml @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/native/libs/binder/ProcessState.cpp @ android-17.0.0_r1"
  - type: official
    path: "https://developer.android.com/guide/topics/providers/content-provider-basics"
  - type: official
    path: "https://developer.android.com/topic/libraries/app-startup"
  - type: official
    path: "https://developer.android.com/reference/android/content/ContentResolver"
  - type: official
    path: "https://developer.android.com/reference/android/content/ContentProviderClient"
  - type: official
    path: "https://developer.android.com/reference/android/database/CursorWindow"
  - type: official
    path: "https://developer.android.com/reference/android/os/TransactionTooLargeException"
tags:
  - content-provider
  - binder
  - cursor-window
  - sqlite
  - app-startup
  - anr
related_chapters:
  - '1.3'
  - '1.4'
  - '1.8'
  - '1.14'
  - '8.3'
  - '9.1'
drafted_date: '2026-04-05'
drafted_by: openclaw-task2a
reviewed_by: openclaw-task6
reviewed_date: '2026-07-02'
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
task9_result: pass-tech-review
task2b_state: fixed
task2b_result: fixed-lite
pipeline_stage: ready-to-publish
deepseek_cn_review_state: done
finalized_by: "openclaw-task6-auto-promote"
finalized_date: "2026-07-14"
last_task9_review_log: "logs/deep-review/2026-07-02-05-deep-review.md"
last_task9_at: "2026-07-02T05:27:44+08:00"
last_task2b_at: '2026-05-27T13:35:00+08:00'
last_task2b_lite_at: '2026-05-27'
review_round: 8
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-07-02"
task9_review_notes: "2026-04-27 task9 deep-review: needs-rework。P0 1 / P1 1 / P2 2。;2026-04-28 task9 deep-review: needs-rework。P0 1 / P1 2 / P2 2。;2026-04-28 task9 deep-review: needs-rework。P0 0 / P1 1 / P2 0。 | 2026-05-27 14:20 Task9 auto-fix：修正 Provider 进程冷启动序列，明确 `attachBaseContext()` / provider install / publish / `Application.onCreate()` 的先后关系；回到 Task6 复审。 | 2026-05-27 15:22 Task9 auto-fix：修正 ContentProvider publish/ready/getType 超时口径，并把 Binder 线程池默认值统一为 ProcessState DEFAULT_MAX_BINDER_THREADS=15；回到 Task6 复审。 | 2026-05-27 16:21 Task9 deep-review: pass-tech-review；P0 0 / P1 0 / P2 0 新增；Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-07-01 10:28 Task9 idle-audit AUTO-FIX: 修正 ContentProviderTimeout / contentProviderTimeout 非 AOSP android-17.0.0_r1 稳定日志关键字，改为 ContentProviderHelper 的 publish/ready/not-responding 实际路径；同步 source anchor 到 android-17.0.0_r1。回到 Task6 复审。详见 logs/deep-review/2026-07-01-10-audit.md。 | 2026-07-02 05:27 Task9 formal deep-review: pass-tech-review。复核 android-17.0.0_r1 源码锚点与版本边界；P0 0 / P1 0 / P2 0。Task6 已通过且 queue 无 pending，自动晋升 finalized。"
review_notes: '2026-04-28 task6 re-review-2 (revisiting→reviewed): pass-light-edit。Frontmatter去重整理。无新增L1/L2问题。无B类大问题。评分:
  结构5/5·措辞5/5·一致性5/5·验证4/5·元数据4/5。'
repaired_date: '2026-04-27'
repaired_by: openclaw-task2b
task6_review_notes: "2026-07-14 Task6 revisiting-final: pass-light-edit. L1 小修 2 处（形容词+冒号起手式 ×2：「设计初衷很简单」→「解决的核心问题」、「优化策略很直接」→「优化重点是」）。无新增 L3/L4 回炉项。Task9 pass-tech-review，queue 无 pending，自动晋升 finalized。 | 2026-05-16 Task6 stale-recheck：修复文风禁令/冗余副词 11 处；未新增 L3/L4 回炉项；保留既有 Task9 needs-rework。 | 2026-05-27 14:05 Task6：pass-light-edit。修复 outline 标记、结构元叙述、占位省略号和代码引导句等 6 处；复核 Task2B Lite 修正后的 remote provider 语义；无新增 L3/L4 回炉项，保留既有 Task9 needs-rework。 | 2026-05-27 15:08 Task6：复审 Task9 auto-fix 后内容；统一中英文混排周边标点与少量第一人称引导，未新增 L3/L4 回炉项；Task9 result 为 auto-fixed，未满足 pass-tech-review 自动晋升条件，送 Task9 复审。 | 2026-05-27 16:08 Task6：复审 Task9 auto-fix 后内容；统一正文半角标点、括号和少量发布稿格式；无新增 L3/L4 回炉项，Task9 result 为 auto-fixed，继续送 Task9 复审。 | 2026-07-02 05:06 Task6 re-review (revisiting after Task9 idle-audit auto-fix): pass-light-edit. Task9 idle-audit 修正 ContentProviderTimeout 日志关键字路径已平滑落地，正文无新增 L1/L2 问题；无 B 类回炉项。Task9 result=auto-fixed，送 Task9 正式通过。"
task6_reviewed_by: "openclaw-task6"
task6_reviewed_date: "2026-05-27"
last_task6_at: 2026-07-14T13:14:05+08:00
last_task6_audit: "2026-07-13"
last_task6_review_log: "logs/review/2026-05-27-16-review.md"
review_type: "task6-writing-quality-review"
p0: 0
p1: 0
p2: 0
last_task9_autofix_at: "2026-07-01"
task6_l1_l2_fixes: 54
task6_l3_l4_issues: 0
last_task2b_verifier_at: "2026-05-27T15:34:00+08:00"
task2b_verifier_result: ready-for-task6
last_deepseek_cn_review_at: 2026-07-14
last_task9_audit: "2026-07-16 00:20:31"
last_task9_idle_audit_log: "logs/deep-review/2026-07-16-00-audit.md"
---

# 1.10 ContentProvider 性能与优化

ContentProvider 同时出现在两条关键路径上：

- 进程首次绑定应用时，当前进程声明的 Provider 会早于 `Application.onCreate()` 初始化；
- 跨进程访问数据时，调用方通过 Binder 同步进入提供方，查询结果再借助 `CursorWindow` 分批传递。

前一条路径影响冷启动，后一条路径容易造成主线程阻塞、Binder 线程池排队和数据库 I/O。分析 ContentProvider 问题时，需要先确认调用发生在同一进程还是跨进程，以及提供方当时已经运行还是正在冷启动；URI 是后续检查项。

当前源码基线为 AOSP `android-17.0.0_r1`。Android 8～16 只在解释版本演进时保留。

---

## ContentProvider 在系统中的位置

ContentProvider 为结构化数据提供统一的 URI、权限和调用协议。`content://authority/path` 中，authority 用于找到 Provider；path 和查询参数由 Provider 自己解释。

一次访问涉及三方：

| 参与者 | 主要对象 | 职责 |
|---|---|---|
| 调用方 | `ContentResolver`、`ContentProviderClient` | 解析 URI、取得 Provider、发起同步调用、管理引用 |
| `system_server` | `ContentProviderHelper`、`ContentProviderRecord` | 按 authority 查找 Provider，必要时启动进程，跟踪发布和引用关系 |
| 提供方 | `ContentProvider`、内部 `Transport` | 校验传入身份与权限，执行 query/insert/update/delete 等实际逻辑 |

`ContentProvider.Transport` 是 Binder Stub。跨进程调用会进入提供方的 Binder 线程；同进程调用可以取得本地 Provider 引用，直接在调用方线程执行。同一个 `query()` 因此可能采用完全不同的线程模型：

```text
同进程：
调用线程 → ContentProvider.query()

跨进程：
调用线程 → IContentProvider Proxy → Binder
        → 提供方 Binder 线程 → ContentProvider.Transport.query()
        → ContentProvider.query()
```

ContentProvider 调用不一定经过 Binder。可用进程名、PID 和 Binder 事务确认边界。

### 权限检查发生在哪里

Provider 可以通过 `readPermission`、`writePermission`、path permission 和临时 URI 授权控制访问。`Transport` 会校验 authority、调用方归因信息和读写权限，再把请求交给 Provider 实现。

性能优化不能绕过这层安全语义：

- 只导出需要跨应用访问的 Provider；
- 对可共享的最小 URI 发放临时授权；
- `selection` 使用占位符和 `selectionArgs`，不要拼接来自调用方的字符串；
- `call()`、`openFile()` 等自定义入口同样要设计权限边界。

---

## 进程启动时，Provider 为什么早于应用

Android 17 的 `ActivityThread.handleBindApplication()` 先创建应用对象。`Application.attach()` 已经执行，因此 `attachBaseContext()` 也已经完成。随后，主线程按以下顺序继续：

```text
makeApplicationInner()
  → Application.attach() / attachBaseContext()
  → installContentProviders()
      → installProvider()
          → ContentProvider.attachInfo()
              → ContentProvider.onCreate()
      → publishContentProviders()
  → Instrumentation.callApplicationOnCreate()
      → Application.onCreate()
```

内容提供者的 `onCreate()` 在主线程执行。同一进程的内容提供者会逐个安装，全部安装后才一起发布给 `system_server`。`Application.attachBaseContext()` 位于内容提供者之前，`Application.onCreate()` 位于发布之后。

如果任意 Provider 在 `onCreate()` 中做磁盘扫描、数据库迁移、同步网络等待或复杂依赖初始化，后续内容提供者和 `Application.onCreate()` 都会被推迟。远程调用方也可能正在等待这个进程发布 Provider。

### `initOrder` 只保证数值优先级

`ComputerEngine.queryContentProviders()` 按 `ProviderInfo.initOrder` 降序排列，值大的先安装。Android 17 的 comparator 对相同值返回 0，因此源码只明确保证数值优先级；不能把同值 Provider 的实际顺序设计成依赖条件。

如果初始化组件之间存在依赖，应该使用显式依赖图，或由应用在可控入口中组织，而不是依靠两个库碰巧选择了不同的 `initOrder`。

### 远程 Provider 冷启动

当调用方请求的 Provider 进程尚未运行时，`system_server` 会启动它。调用方需要等待：

```text
fork 进程
  → 运行时和 APK 加载
  → Application.attachBaseContext()
  → 安装当前进程 Provider
  → publishContentProviders()
  → 调用方取得 IContentProvider
  → 执行本次请求
```

`Application.onCreate()` 位于发布之后，通常不在“等待 Provider 发布”的前置路径内。不过 Provider 一经发布，远程 Binder 请求就可能与提供方主线程的 `Application.onCreate()` 并发执行。若二者争用同一数据库锁、CPU 或 I/O，首次查询仍会被间接拖慢。

---

## 跨进程查询怎样返回游标

`query()` 是同步 API。调用方线程会等到 Provider 返回一个可用的游标接口；把它放在主线程上，远程进程冷启动、数据库锁和磁盘 I/O 都会直接变成界面卡顿。

### `CursorWindow` 传的是窗口，不是整个结果集

跨进程游标不会把全部行序列化进一笔 Binder 事务。提供方用 `CursorWindow` 保存一批行，Binder 传递描述符和控制元数据，调用方通过 `BulkCursorToCursorAdaptor` 访问窗口。

AOSP Android 17 的 `config_cursorWindowSize` 默认是 2048 KiB，但这是产品可覆盖的默认值，不是所有窗口不可改变的硬上限。公开构造函数 `CursorWindow(String, long)` 允许调用方指定容量；实际内存按写入数据动态分配，不超过该窗口的配置容量。

窗口能减少大结果集的复制，但不能让无限数据一次返回。一个窗口装不下全部结果时，调用方移动到窗口外的行，`BulkCursorToCursorAdaptor` 会调用远端 `getWindow(newPosition)` 取得新窗口。若 Provider 要求接收所有移动事件，即使目标仍在当前窗口，也可能调用远端 `onMove()`。

“`moveToNext()` 永远不走 Binder”并不准确。通常在当前窗口内读取列值不需要远程取数；窗口失效、越界或 Provider 请求所有移动回调时，仍会发生 Binder 往返。

### 深位置访问为什么会变慢

SQLite 查询返回 `SQLiteCursor` 时，窗口填充路径是：

```text
SQLiteCursor.onMove()
  → SQLiteCursor.fillWindow(requiredPos)
  → SQLiteQuery.fillWindow(window, startPos, requiredPos, countAllRows)
  → SQLiteSession.executeForCursorWindow(...)
```

Framework 没有把原 SQL 自动改写成高效的键集分页。访问很深的位置时，底层查询仍可能遍历大量前序结果才能填到目标窗口。数据量大且需要翻页的接口，应让 Provider 直接暴露分页条件，例如：

```sql
SELECT _id, title
FROM article
WHERE _id > ?
ORDER BY _id
LIMIT ?
```

这类键集分页要有匹配索引和稳定排序键。它解决的是查询计划问题，不是单纯把 `CursorWindow` 调大。

### Binder 缓冲区仍然重要

`frameworks/native/libs/binder/ProcessState.cpp` 的 Android 17 默认映射大小是 `1 MiB - 2 × page size`。这是一个进程内多笔进行中 Binder 事务共享的空间，并非每次调用都独享 1 MiB。

`CursorWindow` 中的行数据不直接塞进这块缓冲区，但下列内容仍会占用 Binder transaction：

- URI、`projection`、`selection`、参数和 extras；
- `ContentValues`、`Bundle`、`ContentProviderOperation` 数组；
- 返回的元数据、异常和文件描述符；
- 同一进程并发进行的其他 Binder 请求。

`applyBatch()` 的批次并非越大越好。它减少往返次数，却可能让单笔 parcel 过大并触发 `TransactionTooLargeException`。批大小应通过真实数据分布测试。

图片、视频和大文件应通过 `openFile()`、`openAssetFile()` 或 `openTypedAssetFile()` 返回 `ParcelFileDescriptor`，不要塞进 `Bundle` 或 `ContentValues`。

---

## Stable 与 unstable client

`ContentResolver.acquireContentProviderClient()` 返回 stable client。系统会记录调用方对 Provider 的稳定依赖；调用方用完客户端后必须调用 `close()`。

`acquireUnstableContentProviderClient()` 适合调用方不信任提供方稳定性的场景。它关闭了 Provider 进程死亡时清理依赖进程的那套稳定引用语义，但调用者必须自己处理：

- `DeadObjectException`；
- 当前 client 已失效；
- 关闭旧 client；
- 需要时重新获取，让系统重启 Provider。

unstable 不会让慢查询自动变快，也不为 CRUD 增加超时。它解决的是 Provider 进程死亡时的故障边界。

---

## 四类超时不要混用

Android 17 的 ContentProvider 没有覆盖所有操作的“统一 10 秒超时”。AOSP 标准值还会乘以 `Build.HW_TIMEOUT_MULTIPLIER`，所以表中的秒数是常规构建下的名义值：

| 场景 | 名义时间 | Android 17 实现 | 超时后的含义 |
|---|---:|---|---|
| 已附加的进程发布 Provider | 10 秒 | `CONTENT_PROVIDER_PUBLISH_TIMEOUT_MILLIS` | `system_server` 清理 launching providers，并以初始化失败原因移除提供方进程 |
| 调用方等待新进程发布 Provider | 20 秒 | `CONTENT_PROVIDER_READY_TIMEOUT_MILLIS` | acquire 等待结束，返回失败或进入相应清理 |
| 已取得 Provider 后的 `getTypeAsync()` 等回调 | 3 秒 | 私有 `CONTENT_PROVIDER_TIMEOUT_MILLIS` | `ContentResolver` 停止等待并返回失败结果 |
| 普通 query/insert/update/delete | 无统一 Provider 超时 | 同步 Binder 调用 | 后果由调用线程所处场景、应用 ANR 条件或系统 API 监测决定 |

如果 `ContentResolver.getType()` 不能直接取得 Provider，Android 17 还会走 `system_server` 的异步 fallback；对应等待上限由 ready timeout 与 3 秒回调超时组合而来。它仍然不是 CRUD 超时。

### `setDetectNotResponding()` 不属于普通应用超时 API

`ContentProviderClient.setDetectNotResponding()` 是 `@SystemApi` / `@hide` 能力，并要求 `REMOVE_TASKS` 权限。调用者给它设置时长后，`NotRespondingRunnable` 才会调用 `appNotRespondingViaProvider()`，把已连接 Provider 标记为无响应。

普通应用不能借此获得通用的内容提供者 ANR 计时器。应用侧应该：

- 在后台线程执行同步的 ContentResolver API；
- 为自己的业务请求设置超时；
- 向支持取消的查询传入 `CancellationSignal`；
- 超时后取消请求并丢弃迟到结果。

下面的 Kotlin 代码让调度器在 5 秒后主动取消远程查询。5 秒是业务选择，不是 Android 平台常量：

```kotlin
suspend fun queryWithTimeout(
    resolver: ContentResolver,
    uri: Uri,
    projection: Array<String>,
    scheduler: ScheduledExecutorService,
): Cursor? {
    return withContext(Dispatchers.IO) {
        val signal = CancellationSignal()
        val timeout = scheduler.schedule(
            { signal.cancel() },
            5,
            TimeUnit.SECONDS,
        )
        try {
            resolver.query(uri, projection, null, null, null, signal)
        } catch (_: OperationCanceledException) {
            null
        } finally {
            timeout.cancel(false)
        }
    }
}
```

调用方还要用 `use` 或其他结构及时关闭游标，避免窗口和 Provider 引用长期占用。

---

## Binder 线程池如何耗尽

跨进程 Provider 的 CRUD 默认在提供方 Binder 线程执行。`ProcessState.cpp` 中 `DEFAULT_MAX_BINDER_THREADS` 为 15，但它是默认配置，不代表跟踪记录中必然只能看到 15 条 Binder 线程；线程池启动方式、已加入线程和产品代码都可能影响实际数量。

典型的耗尽过程是：

1. 多个调用方并发进入同一个 Provider；
2. 提供方 Binder 线程都在等待数据库写锁、文件 I/O 或下游 Binder；
3. 可执行 Binder 线程逐渐用尽；
4. 新请求在驱动或线程池中排队；
5. 调用方同步等待，随后可能触发自身场景的 ANR 条件，或被 framework 的 Provider 无响应监测处理。

这里不存在“system_server 心跳拿不到 Binder 线程，所以自动判 ANR”的通用机制。应按证据区分三种位置：

- 调用方主线程停在 `IContentProvider` Proxy：正在等待远端回复；
- 提供方多条 Binder 线程停在同一锁或 I/O：提供方并发被串行瓶颈卡住；
- 提供方主线程停在 `handleBindApplication()` 或 Provider `onCreate()`：Provider 还在冷启动或发布。

锁竞争是根因时，仅把 Provider 移到独立进程不会消除问题。它只能改变内存与线程池边界。

---

## 独立 Provider 进程的收益和代价

Manifest 中的 `android:process=":provider"` 会把 Provider 放入应用私有的独立进程：

```xml
<provider
    android:name=".ArticleProvider"
    android:authorities="${applicationId}.articles"
    android:exported="false"
    android:process=":provider" />
```

可能的收益包括：

- 独立 Java heap 和 GC；
- 独立 Binder 线程池；
- Provider 崩溃不一定直接终止主进程。

代价同样明确：

- 首次访问需要完整冷启动；
- 独立应用实例会重复初始化未区分进程的 SDK；
- 进程基础内存、类加载和页表成本增加；
- 调用全部变成 Binder IPC；
- Provider 进程被回收后，下次访问要重新启动。

Provider 侧 GC 虽不会暂停主进程线程，却会延迟远程回复，因此调用方仍能感知到停顿。

如果多个进程访问同一个 SQLite 文件，WAL 通常能提高读写并发，但不是“多进程访问的必选开关”，也不能消除所有写串行和 `SQLITE_BUSY`。数据库结构、事务长度、连接配置和跨进程 invalidation 都要在目标设备上验证。

独立进程适合明确需要故障或内存隔离、且能接受冷启动成本的服务端数据组件，不属于常规数据库优化选项。

---

## 启动阶段怎样减负

### Provider `onCreate()` 只做发布前必需工作

发布前必须完成的工作越少越好。可以保留：

- 保存 application context；
- 创建轻量级依赖容器；
- 注册必需的句柄。

应该推迟：

- 全库扫描和迁移后的预热；
- 同步网络请求；
- 大量磁盘读取；
- 与第一次 CRUD 无关的 SDK 初始化；
- 等待其他线程完成的阻塞任务。

延迟初始化不等于把工作无条件丢到线程池。Provider 的第一次查询可能马上到来，必要状态要用明确的并发协议保护，并允许取消或失败返回。

### 正确理解 Jetpack App Startup

App Startup 用一个 `InitializationProvider` 发现多个 `Initializer`，并按 `dependencies()` 构建依赖顺序。它可以减少各库各自声明初始化 Provider 的重复成本，但初始化代码本身仍运行在启动路径上。

如果某个组件不应自动初始化，需要从合并后的清单中移除对应 metadata，再在需要时调用 `AppInitializer.initializeComponent()`。这才是 App Startup 的延迟初始化；不存在自动把重任务移出启动路径的“lazy 标记”。

收益必须用目标应用实测。不能使用“每减少一个 Provider 固定节省 2 ms”或“必然提升 35%”这类没有设备、构建和样本条件的数字。

---

## 减少跨进程成本

### 先减数据，再减调用次数

查询时应：

- 明确 projection，只返回需要的列；
- 用 `selection` 与 `selectionArgs` 在数据库层过滤；
- 为筛选和排序字段建立合适索引；
- 避免在单列中返回大 BLOB 或大段 JSON；
- 对列表接口设计稳定的分页契约。

批量写入可以用 `bulkInsert()` 或 `applyBatch()`，但要控制每批 parcel 大小：

```java
ArrayList<ContentProviderOperation> operations = new ArrayList<>();
for (ContentValues values : pendingRows) {
    operations.add(
            ContentProviderOperation.newInsert(uri)
                    .withValues(values)
                    .build());
}
ContentProviderResult[] results =
        contentResolver.applyBatch(uri.getAuthority(), operations);
```

Android 17 中，`ContentProvider.applyBatch()` 的默认实现只是逐个调用 `ContentProviderOperation.apply()`。它不会自动开启 SQLite transaction，也不保证失败时回滚前面已完成的操作。

若 Provider 要提供原子批处理，必须在自己的存储层实现事务：

```java
@Override
public ContentProviderResult[] applyBatch(
        ArrayList<ContentProviderOperation> operations)
        throws OperationApplicationException {
    SQLiteDatabase db = helper.getWritableDatabase();
    db.beginTransaction();
    try {
        ContentProviderResult[] result = super.applyBatch(operations);
        db.setTransactionSuccessful();
        return result;
    } finally {
        db.endTransaction();
    }
}
```

调用方不能假定任意第三方 Provider 的 `applyBatch()` 都具有原子性，需要查阅目标 Provider 的契约。

---

## Perfetto 与 traces 怎样互相印证

### 远程 CRUD

Android 17 的 `ContentProvider.Transport` 会用 `TRACE_TAG_ACTIVITY_MANAGER` 记录这些名称：

- `query: <authority>`
- `insert: <authority>`
- `bulkInsert: <authority>`
- `applyBatch: <authority>`
- `delete: <authority>`
- `update: <authority>`
- `openFile: <authority>`
- `call: <authority>`

采集时启用 Activity Manager atrace 分类，并同时记录 Binder、sched、进程和文件系统 I/O。诊断顺序是：

1. 在调用方找到同步 Binder 等待；
2. 沿 Binder 事务定位提供方线程；
3. 查看 `query: authority` 等片段内部是运行、锁等待还是 I/O；
4. 再看数据库线程、GC 和下游 Binder。

### Provider 初始化

`ActivityThread.installContentProviders()` 在 Android 17 固定源码中没有可依赖的同名 trace section。不能预设 Perfetto 一定存在 `installContentProviders` slice。

冷启动分析可以使用：

- `bindApplication` 所在主线程时间段；
- `Application.onCreate()` 的边界；
- 内容提供者用 `Trace.beginSection()` 添加的短埋点；
- simpleperf 或 Perfetto callstack sampling；
- 提供方主线程 traces 栈；
- `system_server` 的进程启动和 Provider publish 日志。

SDK 或应用自定义内容提供者适合在 `onCreate()` 内对可疑步骤分别埋点，而不是只包住整个方法。

### ANR 现场

至少同时保留：

- 调用方主线程；
- 提供方主线程；
- 提供方全部 Binder 线程；
- `system_server` 中相关 Provider 记录；
- 同时段的 EventLog / system log；
- Perfetto 中的 Binder、调度、monitor contention 和 I/O。

发布超时的源码原因字符串是 `timeout publishing content providers`；外部等待路径可见 `Timeout waiting for provider ...`。通过系统 API 设置无响应检测的路径会记录 `ContentProvider not responding`。这些日志属于不同机制，不能用一个关键字替代全部判断。

---

## 版本演进

| 版本 | 已确认变化 | 使用边界 |
|---|---|---|
| Android 9（API 28） | 公开 `CursorWindow(String, long)`，旧的 local/remote 构造语义废弃 | 可指定窗口容量，但不能替代分页和索引 |
| Android 11（API 30） | 固定标签中可见 `ContentProviderClient.setDetectNotResponding()` 的系统/测试能力 | 需要系统权限，不属于普通应用 CRUD 超时 API |
| Android 12（API 31） | `ContentResolver.getType()` 内部使用 `getTypeAsync()` 回调 | 公开 API 仍是同步 `getType()`；应用仍应自行选择线程 |
| Android 17（API 37） | 当前实现基线，保留 10 秒发布、20 秒就绪、3 秒已连接异步回调的分层语义 | 数值受 `Build.HW_TIMEOUT_MULTIPLIER` 影响，CRUD 仍无统一 Provider 超时 |

版本迭代只说明能够由对应标签或官方 API 确认的变化。Photo Picker、Scoped Storage 等功能会改变数据访问方式，但不应被写成 ContentProvider Binder 或超时机制本身的版本断点。

---

## 常见误区

### “Provider 一定运行在 Binder 线程”

同进程调用可以直接在调用方线程执行。只有跨进程调用才进入提供方 Binder 线程。

### “所有 Provider 都有 10 秒 CRUD 超时”

10 秒是进程附加后的发布窗口。普通 CRUD 没有这个统一计时器。

### “CursorWindow 绕过了 Binder”

行数据使用共享窗口，但窗口描述、控制调用、翻页和其他参数仍通过 Binder。

### “多进程能消除数据库卡顿”

多进程改变隔离边界，却增加冷启动、内存和 IPC 成本。共享数据库的锁与 I/O 仍然存在。

### “App Startup 会自动延迟所有初始化”

它默认仍在 `InitializationProvider` 中运行 Initializer。实际的延迟初始化需要从合并后的 Manifest 移除对应 metadata registration，并在业务入口手动初始化。

### “批处理天然具有事务性”

Framework 默认 `applyBatch()` 只按顺序应用操作。事务语义由具体 Provider 实现。

---

## 源码阅读顺序

一次远程冷启动查询涉及以下源码路径：

1. `ContentResolver.acquireProvider()`：调用方怎样向 AMS 取得 Provider；
2. `ContentProviderHelper.getContentProviderImpl()`：authority 查找、进程启动与就绪等待；
3. `ActivityThread.handleBindApplication()` / `installContentProviders()`：提供方怎样创建和发布 Provider；
4. `ContentProvider.Transport.query()`：权限校验和远程调用入口；
5. `BulkCursorToCursorAdaptor`：远程窗口怎样交给调用方；
6. `SQLiteCursor.fillWindow()` / `SQLiteSession.executeForCursorWindow()`：查询结果怎样填入窗口；
7. `ContentProviderClient`：stable/unstable 引用和系统 API 无响应监测。

一次慢 query 分成“等进程”“等发布”“等 Binder 线程”“等数据库”和“等新 CursorWindow”五类问题。分清阶段后，才能避免优化破坏安全、正确性或进程稳定性。
