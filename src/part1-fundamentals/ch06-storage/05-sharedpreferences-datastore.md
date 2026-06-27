---

last_task9_at: "2026-04-20T11:51:17+08:00"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-04-20
title: "SharedPreferences/DataStore 性能与 ANR 优化"
chapter: "6.5"
status: finalized
drafted_date: "2026-04-08"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 1.0 (API 1) - Android 17 (API 37)"
last_verified: "2026-04-08"
last_verified_against: "AOSP android-16.0.0_r1"
reviewed_date: "2026-04-20"
reviewed_by: "openclaw-task6"
task6_result: pass-light-edit
confidence: medium
sources:
  - type: blog
    path: "https://mp.weixin.qq.com/s/kfF83UmsGM5w43rDCH544g"
  - type: aosp
    path: "frameworks/base/core/java/android/app/SharedPreferencesImpl.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/QueuedWork.java"
  - type: aosp
    path: "frameworks/base/core/java/android/content/BroadcastReceiver.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java"
  - type: official
    path: "https://developer.android.com/topic/libraries/architecture/datastore"
tags: [sharedpreferences, datastore, anr, io, storage, performance, queuedwork]
related_chapters: ["6.1", "6.3", "9.1", "9.2", "8.2", "4.5"]
section: "6.5"
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task9_result: pass-tech-review
task2b_state: fixed
task2b_result: fixed
last_task9_audit: "2026-06-27T09:23:02+0800"
last_task6_audit: "2026-06-25"
last_task9_audit_log: "logs/deep-review/2026-06-11-14-audit.md"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-16
---

# 6.5 SharedPreferences/DataStore 性能与 ANR 优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 SharedPreferences 首次加载阻塞与 `awaitLoadedLocked()` 的等待点
- 🔹 `apply()`、`QueuedWork.waitToFinish()` 与生命周期切换中的 ANR 关系
- 🔹 SP 写入的完整过程：内存更新、后台落盘、主线程等待
- 🔹 DataStore 的异步模型，以及它和 SP 的关键差异
- 🔹 在 Perfetto / traces.txt 中定位 SP 相关 ANR 的方法
- 🔹 从 SP 迁移到 DataStore 的实战策略与注意事项

### 扩展（可选深入）

- 🔸 MMKV 与 DataStore 的选型边界
- 🔸 多进程 KV 存储的替代方案

### OpenClaw 加工指引

> 锚点是最低覆盖要求，加工时必须逐条落实并标注验证状态。
> 扩展内容视素材完整度决定是否展开，无法确认的技术细节保留 `[待验证]`，不要硬写结论。
<!-- outline-end -->

## 为什么要了解 SharedPreferences 的性能问题

SharedPreferences（以下简称 SP）是 Android 最古老的数据持久化方案之一。它的 API 很简洁，`putString()`、`apply()` 两行代码就能把数据写到磁盘。也正因为这种便捷，SP 成了 Android 应用中使用频率最高的存储方式之一。

但 SP 的设计有一个根本性的矛盾：它声称自己是"轻量级"的键值存储，却在实际使用中被当作通用数据仓库来用。开发者往里面塞越来越多的数据，调用越来越频繁的 `apply()`，直到有一天 ANR 爆发，traces.txt 里的主线程堆栈赫然指向 `QueuedWork.waitToFinish()`。

这个问题并不偶发。在字节跳动（今日头条）的 ANR 优化实践中，SP 相关 ANR 一直很顽固。即使常规的 ANR 治理已经生效，这类问题仍然持续出现，因为触发点不在应用业务代码本身，而在系统框架会在组件生命周期切换时强制等待。

了解 SP 的性能陷阱和 DataStore 的替代方案，对于任何一个需要做 ANR 治理或存储优化的 Android 工程师来说都是必要的。

## SP 导致 ANR 的两类路径

SP 导致 ANR 主要有两类路径，分别发生在读取和写入阶段。


### 路径一：首次加载阻塞

SP 文件创建后，`SharedPreferencesImpl` 会立刻触发一次异步读盘，但 android-16.0.0_r1 已经不是旧版本里那个固定线程名的实现。当前代码是把 `loadFromDisk()` 投递到静态 `sLoadExecutor`：

```java
// frameworks/base/core/java/android/app/SharedPreferencesImpl.java
// @ AOSP android-16.0.0_r1
private void startLoadFromDisk() {
    synchronized (mLock) {
        mLoaded = false;
    }

    sLoadExecutor.execute(() -> {
        loadFromDisk();
    });
}
```

后续无论是 `getString()` 还是 `edit().putString()`，只要需要访问内存中的 map，都会先走 `awaitLoadedLocked()`：

```java
@GuardedBy("mLock")
private void awaitLoadedLocked() {
    if (!mLoaded) {
        BlockGuard.getThreadPolicy().onReadFromDisk();
    }
    while (!mLoaded) {
        try {
            mLock.wait();
        } catch (InterruptedException unused) {
        }
    }
    if (mThrowable != null) {
        throw new IllegalStateException(mThrowable);
    }
}
```

这里的等待点很直接：后台 executor 线程还在做 `Os.stat()`、`XmlUtils.readMapXml()` 时，主线程如果先访问 SP，就会卡在 `mLock.wait()`。如果 XML 已经长到几十 KB 甚至几百 KB，这段等待在低端机或 I/O 繁忙场景里会明显放大。

在 Perfetto 里，我们更适合去找 `XmlUtils.readMapXml()`、文件读取和对应的后台 executor 线程，而不是硬写 `SharedPreferencesImpl-load` 这个旧线程名。线程名字在新版实现里不再是稳定观察点。


### 路径二：`apply()` 只对调用方异步

`apply()` 会先把修改写进内存，再把磁盘 I/O 放进 `QueuedWork`。调用栈从 `apply()` 返回时不会阻塞，但组件收尾时系统会把这笔等待要回来。

在 android-16.0.0_r1 里，等待点分成四类：

- pre-Honeycomb Activity：`ActivityThread.handlePauseActivity()` 中 `if (r.isPreHoneycomb()) QueuedWork.waitToFinish();`
- 现代 Activity：`ActivityThread.handleStopActivity()` 中 `if (!r.isPreHoneycomb()) QueuedWork.waitToFinish();`
- Service：`handleServiceArgs()` 和 `handleStopService()` 都会调用 `QueuedWork.waitToFinish()`
- BroadcastReceiver：`PendingResult.finish()` 不直接调 `waitToFinish()`，而是在 `QueuedWork.hasPendingWork()` 为真时，把 `sendFinished()` 追加到队尾，等 pending work 清空后再向 AMS 回执

`QueuedWork.waitToFinish()` 现在也不只是“把等待器 poll 出来跑一遍”。AOSP 当前实现先取消延迟消息，再主动执行 `sWork`，然后再 drain `sFinishers`：

```java
// frameworks/base/core/java/android/app/QueuedWork.java
// @ AOSP android-16.0.0_r1
public static void waitToFinish() {
    synchronized (sLock) {
        handlerRemoveMessages(QueuedWorkHandler.MSG_RUN);
        sCanDelay = false;
    }

    StrictMode.ThreadPolicy oldPolicy = StrictMode.allowThreadDiskWrites();
    try {
        processPendingWork();
    } finally {
        StrictMode.setThreadPolicy(oldPolicy);
    }

    try {
        while (true) {
            Runnable finisher;
            synchronized (sLock) {
                finisher = sFinishers.poll();
            }
            if (finisher == null) {
                break;
            }
            finisher.run();
        }
    } finally {
        sCanDelay = true;
    }
}

private static void processPendingWork() {
    synchronized (sProcessingWork) {
        LinkedList<Runnable> work;
        synchronized (sLock) {
            work = sWork;
            sWork = new LinkedList<>();
            handlerRemoveMessages(QueuedWorkHandler.MSG_RUN);
        }
        for (Runnable w : work) {
            w.run();
        }
    }
}
```

`sWork` 是实际写盘任务，`sFinishers` 才是 `awaitCommit` 这一类收尾等待。`waitToFinish()` 先执行 `processPendingWork()`，意味着主线程有时会自己把 `writeToDiskRunnable` 跑掉；如果写盘已经在后台线程里开始了，主线程随后又会在 `sFinishers` 里卡到 `CountDownLatch.await()`。

这也是很多文章把 ANR 栈写错的地方。现代 App 更常见的栈顶是 `handleStopActivity()`，不是 `handlePauseActivity()`。`handlePauseActivity()` 里的等待只保留给 pre-Honeycomb Activity。Service 和 BroadcastReceiver 也各有自己的收尾路径，不能都折叠成一个 `onPause()` 场景。

[已验证: AOSP android-16.0.0_r1, `frameworks/base/core/java/android/app/QueuedWork.java`, `frameworks/base/core/java/android/app/ActivityThread.java`, `frameworks/base/core/java/android/content/BroadcastReceiver.java`]


## SP 写入的完整过程

我们沿着 `apply()` 和 `commit()` 的真实代码路径走一遍。

**第一步：内存提交与 finisher 注册**

```java
// SharedPreferencesImpl.EditorImpl.apply()
public void apply() {
    final MemoryCommitResult mcr = commitToMemory();
    final Runnable awaitCommit = new Runnable() {
        public void run() {
            try {
                mcr.writtenToDiskLatch.await();
            } catch (InterruptedException ignored) {
            }
        }
    };
    QueuedWork.addFinisher(awaitCommit);
    Runnable postWriteRunnable = new Runnable() {
        public void run() {
            awaitCommit.run();
            QueuedWork.removeFinisher(awaitCommit);
        }
    };
    SharedPreferencesImpl.this.enqueueDiskWrite(mcr, postWriteRunnable);
    notifyListeners(mcr);
}
```

`commitToMemory()` 先改内存里的 map。`writtenToDiskLatch` 记录磁盘写入是否结束。`awaitCommit` 被放进 `sFinishers`，所以组件收尾时主线程有可能执行到这段等待。

**第二步：`enqueueDiskWrite()` 决定谁来写盘**

```java
private void enqueueDiskWrite(final MemoryCommitResult mcr,
                              final Runnable postWriteRunnable) {
    final boolean isFromSyncCommit = (postWriteRunnable == null);

    final Runnable writeToDiskRunnable = new Runnable() {
        @Override
        public void run() {
            synchronized (mWritingToDiskLock) {
                writeToFile(mcr, isFromSyncCommit);
            }
            synchronized (mLock) {
                mDiskWritesInFlight--;
            }
            if (postWriteRunnable != null) {
                postWriteRunnable.run();
            }
        }
    };

    if (isFromSyncCommit) {
        boolean wasEmpty = false;
        synchronized (mLock) {
            wasEmpty = mDiskWritesInFlight == 1;
        }
        if (wasEmpty) {
            writeToDiskRunnable.run();
            return;
        }
    }

    QueuedWork.queue(writeToDiskRunnable, !isFromSyncCommit);
}
```

这里有两个常被写错的点。

第一，写盘锁是 `mWritingToDiskLock`，不是 `SharedPreferencesImpl.this`。`writeToFile()` 负责串行化写盘的对象就是这把锁。

第二，`commit()` 也不是每次都在当前线程 inline 执行。只有 `postWriteRunnable == null` 且 `mDiskWritesInFlight == 1` 时，当前这次同步提交才会直接 `writeToDiskRunnable.run()`。如果前面已经有未完成写盘，`commit()` 一样会走 `QueuedWork.queue(...)`。

`apply()` 的行为更直接：它一定带着 `postWriteRunnable` 进入 `QueuedWork`，写盘结束后再执行 `postWriteRunnable.run()`，里面会调用 `awaitCommit.run()` 并把对应 finisher 从 `sFinishers` 里移除。

**第三步：`writeToFile()` 全量重写 XML**

`writeToFile()` 不是增量更新。`MemoryCommitResult.mapToWriteToDisk` 会被完整序列化回 XML，随后执行 `fsync()`，再通过 `mcr.setDiskWriteResult()` 触发 `writtenToDiskLatch.countDown()`。

这就是为什么 SP 在大文件和高频写场景里会很脆弱。哪怕只改一个 key，也要重新写整份 XML。等待时间长短取决于文件大小、磁盘状态和前面排队的写盘数量，而不只取决于这次改了几个字段。

[已验证: AOSP android-16.0.0_r1, `frameworks/base/core/java/android/app/SharedPreferencesImpl.java`]

## Jetpack DataStore：为什么它是更好的替代方案

Google 在 Jetpack 中引入了 DataStore，明确将其定位为 SP 的替代品。DataStore 分为两个变体：Preferences DataStore（键值对，类似 SP）和 Proto DataStore（结构化数据，基于 Protocol Buffers）。

### 异步架构的根本差异

DataStore 的核心设计原则是：所有 I/O 操作都必须在 `Dispatchers.IO` 上执行，永远不阻塞主线程。

```kotlin
// Preferences DataStore 基本使用
val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "settings")

// 读取：返回 Flow，不阻塞
val nightModeFlow: Flow<Boolean> = context.dataStore.data
    .map { preferences -> preferences[SettingsKeys.NIGHT_MODE] ?: false }

// 写入：suspend 函数，在协程中调用
suspend fun updateNightMode(enabled: Boolean) {
    context.dataStore.edit { settings ->
        settings[SettingsKeys.NIGHT_MODE] = enabled
    }
}
```

`edit {}` 是一个 `suspend` 函数，它内部通过 `Mutex` 保证原子性，通过 `Flow` 实现响应式更新。与 SP 的关键区别在于：

1. **没有 `QueuedWork` 依赖**：DataStore 不使用 `QueuedWork`，因此在 Activity/Service 生命周期切换时不会被系统强制等待。
2. **没有主线程 `fsync()`**：所有磁盘写入都在 `Dispatcher.IO` 上完成，主线程完全无感知。
3. **没有全量 XML 重写**：Preferences DataStore 使用 Protocol Buffers 序列化（虽然 API 层面仍是键值对），Proto DataStore 则直接使用 Protobuf schema。
4. **内置错误处理**：DataStore 提供了 `DataStoreFactory` 的 `corruptionHandler` 参数，可以在数据损坏时执行恢复逻辑。SP 在数据损坏时直接抛异常。


### SP 到 DataStore 的迁移

DataStore 提供了内置迁移工具 `SharedPreferencesMigration`。迁移发生在第一次读取 DataStore 之前，官方把它设计成 one-shot migration：同一个 key 迁过去之后，不会在后续访问里反复覆盖。

```kotlin
val Context.dataStore: DataStore<Preferences> by preferencesDataStore(
    name = "settings",
    produceMigrations = { context ->
        listOf(
            SharedPreferencesMigration(
                context = context,
                sharedPreferencesName = "old_sp_name",
                keysToMigrate = setOf("theme", "font_scale")
            )
        )
    }
)
```

这里有三个边界需要写清楚：

1. 如果不传 `keysToMigrate`，默认迁移全部兼容类型的 key；如果传了集合，只迁那几个 key。
2. 迁移是一次性的。迁移完成后还继续读写旧 SP，会形成数据分叉，因为 DataStore 不会在每次启动时重新把旧值覆盖回来。
3. 迁移后的 cleanup 会把已迁走的 key 从旧 SP 里移除；只有旧文件被清空后，旧 XML 才可能被删除。

所以迁移的收尾动作不是“第一次访问成功”就结束，而是“第一次访问成功后，代码里停掉旧 SP 的读写”。这一步如果没做，线上最容易出现的现象就是新旧两份配置同时存在，排查时看起来像随机丢数据。

[已验证: 官方文档 `https://developer.android.com/topic/libraries/architecture/datastore`]


### Proto DataStore vs Preferences DataStore

选型可以按数据形态和进程边界来分：

- **单进程键值配置**：用 `preferencesDataStore` 或 `DataStoreFactory`
- **单进程结构化对象**：用 Proto DataStore
- **多进程共享同一份配置文件**：从 DataStore 1.1.0 起用 `MultiProcessDataStoreFactory`
- **需要关系查询、分页、复杂事务或 SQL 条件**：用 Room

`MultiProcessDataStoreFactory` 已经是官方支持方案，不需要再把“DataStore 只能单进程”当成固定结论。Room 仍然有位置，但它解决的是查询和事务模型，不是所有多进程 KV 都要先上 Room。

`by preferencesDataStore(name = "...")` 这个委托适合单进程单例。只要同一进程里全局复用一个实例，它就能保证读写串行、读不会被写阻塞。

如果同一份配置需要被 App 进程、独立 Service 进程或 provider 进程共同访问，应该在所有进程里都用 `MultiProcessDataStoreFactory` 指向同一个文件。官方文档从 1.1.0 开始明确支持这一模式，并给出 read-after-write consistency、writes are serialized 这些保证。


## 实战分析：SP ANR 在 Perfetto 中的特征

### 案例 1：现代 Activity 的 stop 路径

**现象**：设置页连续 `apply()` 后按返回，页面已经开始退出，但主线程在生命周期收尾阶段卡住。

**主线程典型栈**：

```
at android.app.QueuedWork.waitToFinish(QueuedWork.java:XXX)
at android.app.ActivityThread.handleStopActivity(ActivityThread.java:XXXX)
at android.app.ActivityThread$H.handleMessage(ActivityThread.java:XXXX)
```

android-16.0.0_r1 里，现代 Activity 的等待点在 `handleStopActivity()`，不是 `handlePauseActivity()`。只有 pre-Honeycomb Activity 才会在 `handlePauseActivity()` 里调 `waitToFinish()`。

**Perfetto 观察点**：
1. 在主线程附近找 Activity stop 相关 slice，再看 callstack 是否落在 `handleStopActivity()`
2. 对照 `queued-work-looper` 或主线程自身的 file I/O 行为，判断这次是“主线程自己帮忙写盘”还是“主线程在等别人写完”
3. 如果 stop 阶段阻塞时长和 `fsync()` / `writeToFile()` 重合，基本就能锁定 SP 写盘堆积

### 案例 2：Service command / destroy 路径

`ActivityThread.handleServiceArgs()` 在 `onStartCommand()` 返回后会立刻调用 `QueuedWork.waitToFinish()`。`handleStopService()` 在 `onDestroy()` 后也会再走一次。

**主线程典型栈**：

```
at android.app.QueuedWork.waitToFinish(QueuedWork.java:XXX)
at android.app.ActivityThread.handleServiceArgs(ActivityThread.java:XXXX)
at android.app.ActivityThread$H.handleMessage(ActivityThread.java:XXXX)
```

或者：

```
at android.app.QueuedWork.waitToFinish(QueuedWork.java:XXX)
at android.app.ActivityThread.handleStopService(ActivityThread.java:XXXX)
at android.app.ActivityThread$H.handleMessage(ActivityThread.java:XXXX)
```

这类 ANR 常见于 Service 收到命令后顺手写一串 SP，再马上 `stopSelf()` 或被系统 stop。表面上看是 Service 生命周期问题，根因还是 pending SP write 没清掉。

### 案例 3：BroadcastReceiver 收尾路径

BroadcastReceiver 没有直接调用 `QueuedWork.waitToFinish()`。收尾逻辑在 `BroadcastReceiver.PendingResult.finish()`：

```java
// frameworks/base/core/java/android/content/BroadcastReceiver.java
// @ AOSP android-16.0.0_r1
if (QueuedWork.hasPendingWork()) {
    QueuedWork.queue(new Runnable() {
        @Override public void run() {
            sendFinished(mgr);
        }
    }, false);
} else {
    sendFinished(mgr);
}
```

如果 `onReceive()` 里做了 `apply()`，receiver 虽然从 Java 代码返回了，AMS 看到的完成回执仍会被排到 pending work 后面。队列前面是磁盘写入，后面才是 `sendFinished()`，超时后就会表现成 broadcast ANR。

Perfetto 里要同时看两件事：主线程的 `onReceive()` 何时结束，以及 `queued-work-looper` 何时把 finish runnable 执行掉。

### 案例 4：首次加载大 XML 文件阻塞

**现象**：冷启动后第一次进入某个页面，主线程没有明显写盘，但页面会卡在 SP 读取上。

**主线程典型栈**：

```
at java.lang.Object.wait(Native Method)
at android.app.SharedPreferencesImpl.awaitLoadedLocked(SharedPreferencesImpl.java:XXX)
at android.app.SharedPreferencesImpl.getString(SharedPreferencesImpl.java:XXX)
```

同一时间段里，后台 executor 线程通常正在执行 `XmlUtils.readMapXml()` 或文件读取。这里要找的是读盘线程和 XML 解析，而不是旧文章里常见的 `SharedPreferencesImpl-load` 固定线程名。

### 在 traces.txt 中区分“主线程自己写盘”和“主线程纯等待”

两种栈的含义不同。

**主线程自己执行写盘**：

```
at android.app.SharedPreferencesImpl.writeToFile(SharedPreferencesImpl.java:XXX)
at android.app.SharedPreferencesImpl$1.run(SharedPreferencesImpl.java:XXX)
at android.app.QueuedWork.processPendingWork(QueuedWork.java:XXX)
at android.app.QueuedWork.waitToFinish(QueuedWork.java:XXX)
at android.app.ActivityThread.handleStopActivity(ActivityThread.java:XXXX)
```

这说明 `waitToFinish()` 先调用了 `processPendingWork()`，主线程把 `sWork` 里的 `writeToDiskRunnable` 自己跑掉了。

**主线程纯等待后台线程**：

```
at java.util.concurrent.CountDownLatch.await(CountDownLatch.java:XXX)
at android.app.SharedPreferencesImpl$EditorImpl$1.run(SharedPreferencesImpl.java:XXX)
at android.app.QueuedWork.waitToFinish(QueuedWork.java:XXX)
at android.app.ActivityThread.handleServiceArgs(ActivityThread.java:XXXX)
```

这说明写盘已经在 `queued-work-looper` 或其他后台线程里进行，主线程只是 drain `sFinishers` 时卡在 `awaitCommit` 上。

## 迁移策略与最佳实践

### 从 SP 到 DataStore 的渐进式迁移

不要试图一次性迁移所有 SP 使用点。推荐按以下策略逐步推进：

1. **优先迁移高频写入场景**：这些是 ANR 风险最高的部分。比如用户设置页面的 `apply()` 调用。
2. **优先迁移大文件**：XML 文件超过 50KB 的 SP 文件，加载和写入都慢，应该尽早迁移。
3. **低频只读场景可以后迁**：只在应用启动时读取一次的配置项，风险较低。
4. **新代码直接用 DataStore**：从今天起，所有新的键值存储需求都使用 DataStore，不再新增 SP 依赖。

迁移期间建议监控 ANR 率的变化，对比迁移前后的数据。


### SP 的"安全使用"规范

如果短期内还不能完全迁到 DataStore，至少把下面几条守住：

1. **不要在主线程调用 `commit()`**：同步提交会把当前线程直接拖进 `writeToFile()` 或后续等待。
2. **不要在组件收尾前连续 `apply()`**：现代 Activity 主要在 `handleStopActivity()` 等待，Service 在 `handleServiceArgs()` / `handleStopService()` 等待，BroadcastReceiver 则把 `sendFinished()` 排到 pending work 后面。
3. **把多次修改合并成一次提交**：一次 `edit { ... }` + 一次 `apply()`，比 20 次单 key `apply()` 更安全。
4. **控制 SP 文件大小**：SP 适合轻量配置，不适合不断增长的业务数据。文件越大，首读和全量重写越慢。
5. **提前触发加载只能降低概率，不能改变模型**：在 `Application` 早期调用 `getSharedPreferences()` 可以把首次读盘前移，但不会消除 `awaitLoadedLocked()` 和全量 XML 重写。
6. **跨进程不要继续押注 SP**：`MODE_MULTI_PROCESS` 已废弃。KV 共享优先看 `MultiProcessDataStoreFactory`；如果还需要复杂查询和事务，再上 Room。

### DataStore 使用注意事项

1. **单例模式**：每个 DataStore 实例应该全局只有一个（通过 `by preferencesDataStore` 委托属性保证）。
2. **作用域管理**：DataStore 的协程作用域应该与应用生命周期匹配，避免在短生命周期的组件（如 Activity）中创建。
3. **错误处理**：使用 `catch()` 操作符处理 `data` Flow 中可能抛出的 `IOException`：

```kotlin
val preferencesFlow: Flow<Preferences> = context.dataStore.data
    .catch { exception ->
        if (exception is IOException) {
            emit(emptyPreferences())
        } else {
            throw exception
        }
    }
```

## 在 Perfetto 和其他工具中的表现

### SP ANR 在 Perfetto 中的定位方法

1. **主线程 track**：搜索 `QueuedWork` 关键字，如果出现长时间 slice，说明主线程在等待 SP 写入。
2. **`queued-work-looper` 线程**：观察这个系统线程的活动，如果它持续执行 `writeToFile`，说明有大量 SP 写入排队。
3. **futex wait**：在主线程搜索 `futex` 系统调用，配合堆栈信息判断是否是 `CountDownLatch.await()`。


### 自定义 Trace Point 监控 DataStore 性能

```kotlin
suspend fun updateSettings(key: Preferences.Key<Boolean>, value: Boolean) {
    Trace.beginSection("DataStore.write.${key.name}")
    try {
        context.dataStore.edit { preferences ->
            preferences[key] = value
        }
    } finally {
        Trace.endSection()
    }
}
```

如果项目已经接入 `androidx.tracing:tracing-ktx`，也可以写成 `trace("DataStore.write.${key.name}") { ... }`。这两种写法都能在 Perfetto 里留下可编译、可追踪的 slice。

### Android Studio Profiler 中的可见性

Android Studio 的 CPU Profiler 可以捕获 SP 相关的磁盘 I/O 操作。在 Call Chart 中搜索 `writeToFile` 或 `QueuedWork`，就能看到主线程在这些操作上的等待时间。但 Profiler 本身有性能开销，建议在开发阶段使用，不要用于生产环境监控。


## MMKV 与其他高性能 KV 存储方案

MMKV 通过 `mmap` 减少了传统文件 I/O 的一部分开销。在高频小写入场景里，它通常比 SP 更轻，迁移成本也低，所以很多存量项目会先用 MMKV 兜住 SP 的 ANR 问题。

选型可以这样看：

- **已经是 Kotlin + coroutine 体系，需求是单进程或官方支持的多进程 KV**：优先 DataStore
- **追求低迁移成本，接口形态想尽量贴近 SP，写入频率很高**：可以考虑 MMKV
- **需要多进程 KV，但不需要 SQL 查询**：优先评估 `MultiProcessDataStoreFactory`，MMKV MultiProcess 作为工程化替代
- **需要关系查询、分页、复杂事务或对外暴露 provider**：用 Room

## 多进程 KV 存储的安全方案

`MODE_MULTI_PROCESS` 已经退出历史舞台。现在更稳妥的做法有三类：

1. **MultiProcess DataStore**：同一份文件由多个进程共享，官方从 DataStore 1.1.0 开始支持，适合配置、flag 和轻量状态。
2. **MMKV MultiProcess**：基于文件锁和 `mmap`，适合已经大量使用 MMKV 的项目。
3. **ContentProvider + Room**：适合需要统一数据入口、复杂查询和事务一致性的场景。

一个反模式仍然要避开：用 ContentProvider 再包一层 SP。这样只是在 SP 的 XML 全量写入之外，又叠了一层 Binder IPC，问题不会自己消失。

## 参考资料

- AOSP SharedPreferencesImpl.java: `frameworks/base/core/java/android/app/SharedPreferencesImpl.java`
- AOSP QueuedWork.java: `frameworks/base/core/java/android/app/QueuedWork.java`
- AOSP ActivityThread.java: `frameworks/base/core/java/android/app/ActivityThread.java`
- AOSP BroadcastReceiver.java: `frameworks/base/core/java/android/content/BroadcastReceiver.java`
- [Jetpack DataStore 官方文档](https://developer.android.com/topic/libraries/architecture/datastore)
- [今日头条 ANR 优化实践系列 - 告别 SharedPreference 等待](https://mp.weixin.qq.com/s/kfF83UmsGM5w43rDCH544g)
- [Google I/O 2024: DataStore 最佳实践](https://developer.android.com/videos/play/live/308012)
