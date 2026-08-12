---
title: "SAF/DocumentFile/ContentResolver 文件访问性能选型与治理"
chapter: "24.18"
section: "24.18"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [SAF, DocumentFile, ContentResolver, ScopedStorage, IO, performance, file-access]
related_chapters: ["6.6", "6.7", "24.1", "24.11"]
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
last_draft_polish_at: "2026-08-03T11:36:11+08:00"
last_draft_polish_run_id: "20260803-113535-draft-polish-331c7d09"
last_verified: "2026-08-03"
last_review_finalize_at: "2026-08-03T12:09:07+08:00"
last_review_finalize_run_id: "20260803-120756-8c57cb22"
confidence: high
sources:
- type: reference
  path: Android Developers SAF/DocumentFile/ContentResolver/MediaStore/Photo Picker
- type: aosp
  path: AOSP android-17.0.0_r1 DocumentsContract/DocumentsProvider/MediaProvider FuseDaemon
- type: kernel
  path: Android common kernel android17-6.18 FUSE passthrough/BPF
---

# SAF/DocumentFile/ContentResolver 文件访问性能选型与治理

文件访问性能问题通常出在选错入口：应用把 `content://` 当成本地路径，把
`DocumentFile` 当成批量查询接口，或者在拿到文件描述符之后仍把每次读写都归因于 Binder。
平台锚点为 Android 17 / API 37 / `android-17.0.0_r1`，重点分析 SAF、
`DocumentFile`、`ContentResolver`、MediaStore 和直接文件路径各自适合的场景。

## 先建立访问路径全景

SAF 定义文档访问协议，具体存储实现由 Provider 决定。一个 `content://` URI 背后可能是：

- 本机共享存储上的普通文件；
- USB、SD 卡或工作资料中的文件；
- 云文档提供方按需下载的对象；
- Provider 通过 pipe 或 socket pair 动态生成的数据；
- 没有可直接读取二进制内容的虚拟文档。

由此得到一条性能边界：同一套 API 在两个 Provider 上可能有完全不同的延迟、
可寻址能力和错误类型。测试报告必须记录 URI 的 authority、Provider 类型、文件是否已在本地、
访问模式和文件大小，单写“SAF 比 File 慢多少”没有可复用价值。

| 访问入口 | 适合场景 | 调用路径 | 主要边界 |
| --- | --- | --- | --- |
| `File` / `java.nio.file.Path` | 应用内部目录、应用专属外部目录、合法持有路径的文件 | 应用 → VFS → 文件系统 | 不能绕过 Scoped Storage；路径可能因卷状态失效 |
| SAF + `DocumentsContract` | 用户选择的任意文档、目录树、云盘 | 应用 → `ContentResolver` → `DocumentsProvider` | 元数据和打开操作跨 Provider；能力由 flags 声明 |
| AndroidX `DocumentFile` | 少量文件的便利操作、兼容 `File` 风格调用 | 对 `DocumentsContract` 的轻量封装 | 属性方法多为独立查询，大目录容易产生 N+1 |
| MediaStore | 共享图片、视频、音频和下载项的索引访问 | 应用 → `MediaProvider` 数据库；内容读取再打开 URI | 受媒体权限、所有权和用户授权约束 |
| Photo Picker | 用户选择少量图片或视频 | 系统选择器 → 本地或云媒体 Provider | 只覆盖视觉媒体；可能下载或转码 |

应用内部数据优先放 `filesDir`、`cacheDir` 或数据库；这些路径可以直接使用
`File`，也不会经过共享存储 FUSE。用户希望在卸载应用后继续保留的文档，应使用
SAF 或合适的共享集合。媒体列表与批量筛选交给 MediaStore，用户选择少量视觉媒体时优先
Photo Picker。

## SAF 的授权和 URI 语义

`ACTION_OPEN_DOCUMENT` 授权单个文档，`ACTION_CREATE_DOCUMENT` 创建新文档，
`ACTION_OPEN_DOCUMENT_TREE` 授权一棵目录树。Android 11（API 30）及以上不允许通过
`ACTION_OPEN_DOCUMENT_TREE` 选择可靠存储卷根目录、`Download` 根目录、
`Android/data` 或 `Android/obb`。

`DocumentsContract.Document.COLUMN_DOCUMENT_ID` 由 Provider 定义，客户端必须把它当作
不透明标识。一个文档还可以同时出现在多个父目录中。以下做法都不可靠：

- 从 URI 字符串截取 `/storage/emulated/0/...`；
- 把 display name 拼成后代 URI；
- 假定 rename 后 URI 不变；
- 假定同一个 URI 永远对应本机普通文件；
- 用 `File(uri.path)` 打开 `content://` URI。

### 持久化授权只做一次

短期 URI grant 通常随重启或进程使用场景结束。需要在重启后继续编辑，或者把工作交给
WorkManager 时，应在用户选择完成后持久化 Provider 提供的读写权限。

下面的代码只保存结果 Intent 中实际提供的访问位，避免申请 Provider 没有授予的写权限：

```kotlin
fun persistDocumentGrant(
    resolver: ContentResolver,
    result: Intent,
): Uri {
    val uri = requireNotNull(result.data)
    val takeFlags = result.flags and (
        Intent.FLAG_GRANT_READ_URI_PERMISSION or
            Intent.FLAG_GRANT_WRITE_URI_PERMISSION
        )

    require(takeFlags != 0) { "The picker returned no read/write grant" }
    resolver.takePersistableUriPermission(uri, takeFlags)
    return uri
}
```

`takePersistableUriPermission()` 是授权生命周期操作，不是文件读取优化。它不应放进每次
open 或每个 Worker 的循环中。文档被删除或移动后，持久化授权仍可能失效；应用启动任务前
要处理 `SecurityException`、`FileNotFoundException`，并给用户重新选择入口。长期不用的授权
应通过 `releasePersistableUriPermission()` 释放。

Photo Picker 返回的媒体 URI 也可在长任务前持久化读取权限。它适用于选中的图片和视频，
不等价于目录树授权。

## `DocumentFile` 的性能成本来自哪里

AndroidX 官方文档把 `DocumentFile` 定义为模仿 `File` 的便利封装，并明确指出它有较高开销；
需要更好性能和完整能力时，应直接使用 `DocumentsContract`。Android 17 时稳定版本为
`androidx.documentfile:documentfile:1.1.0`。

### `listFiles()` 是一次查询

[`TreeDocumentFile.listFiles()`](https://android.googlesource.com/platform/frameworks/support/+/27495ca3d1fe4a1166bea16413ecf8cff5d85855/documentfile/documentfile/src/main/java/androidx/documentfile/provider/TreeDocumentFile.java)
构造 `buildChildDocumentsUriUsingTree()`，然后用一次 `ContentResolver.query()` 只读取
`COLUMN_DOCUMENT_ID`。它遍历 Cursor，把每个 ID 包装成新的 `TreeDocumentFile`。

因此，“目录有 N 个文件，`listFiles()` 就执行 N 次 IPC”并不准确。一次目录枚举通常对应
一次查询；Cursor 分窗和远端 Provider 的实现仍可能产生后续通信，但不是 Java 层逐项调用
`query()`。

### 属性读取会形成 N+1

问题出在拿到数组之后。`TreeDocumentFile.getName()`、`getType()`、`lastModified()`、
`length()` 和 `exists()` 会进入
[`DocumentsContractApi19`](https://android.googlesource.com/platform/frameworks/support/+/27495ca3d1fe4a1166bea16413ecf8cff5d85855/documentfile/documentfile/src/main/java/androidx/documentfile/provider/DocumentsContractApi19.java)，
每个方法各自查询一个或两个字段。

例如，目录有 N 个子项时，以下代码会产生一次列表查询，再产生 N 次名称查询：

```kotlin
val names = directory.listFiles().mapNotNull { it.name }
```

这段代码适合少量、低频的交互。文件管理器、同步器或大目录扫描应在子项查询中一次取回
ID、名称、MIME、大小、修改时间和能力 flags。

`DocumentFile.findFile(name)` 也会先调用 `listFiles()`，再逐项调用 `getName()`。
在同一目录循环查找多个名称，会重复枚举和属性查询。批量查找应先构建一次名称索引，
同时准备名称重复的处理规则；display name 不保证在所有 Provider 中唯一。

### 一次查询取齐列表所需字段

下面的实现把目录列表页需要的字段放在一个 projection 中。调用方传入树授权 URI 和
目标目录的文档 ID；查询应在工作线程执行：

```kotlin
data class DocumentRow(
    val uri: Uri,
    val documentId: String,
    val displayName: String,
    val mimeType: String,
    val sizeBytes: Long?,
    val lastModifiedMillis: Long?,
    val flags: Int,
)

fun queryChildren(
    resolver: ContentResolver,
    treeUri: Uri,
    parentId: String,
    signal: CancellationSignal,
): List<DocumentRow> {
    val parentDocumentUri = DocumentsContract.buildDocumentUriUsingTree(
        treeUri,
        parentId,
    )
    val childrenUri = DocumentsContract.buildChildDocumentsUriUsingTree(
        parentDocumentUri,
        parentId,
    )
    val projection = arrayOf(
        DocumentsContract.Document.COLUMN_DOCUMENT_ID,
        DocumentsContract.Document.COLUMN_DISPLAY_NAME,
        DocumentsContract.Document.COLUMN_MIME_TYPE,
        DocumentsContract.Document.COLUMN_SIZE,
        DocumentsContract.Document.COLUMN_LAST_MODIFIED,
        DocumentsContract.Document.COLUMN_FLAGS,
    )

    val cursor = resolver.query(
        childrenUri,
        projection,
        Bundle.EMPTY,
        signal,
    ) ?: throw IOException("Provider returned a null cursor: ${childrenUri.authority}")

    return cursor.use { c ->
        val idIndex = c.getColumnIndexOrThrow(
            DocumentsContract.Document.COLUMN_DOCUMENT_ID,
        )
        val nameIndex = c.getColumnIndexOrThrow(
            DocumentsContract.Document.COLUMN_DISPLAY_NAME,
        )
        val typeIndex = c.getColumnIndexOrThrow(
            DocumentsContract.Document.COLUMN_MIME_TYPE,
        )
        val sizeIndex = c.getColumnIndex(
            DocumentsContract.Document.COLUMN_SIZE,
        )
        val modifiedIndex = c.getColumnIndex(
            DocumentsContract.Document.COLUMN_LAST_MODIFIED,
        )
        val flagsIndex = c.getColumnIndexOrThrow(
            DocumentsContract.Document.COLUMN_FLAGS,
        )

        buildList {
            while (c.moveToNext()) {
                val id = c.getString(idIndex)
                add(
                    DocumentRow(
                        uri = DocumentsContract.buildDocumentUriUsingTree(
                            parentDocumentUri,
                            id,
                        ),
                        documentId = id,
                        displayName = c.getString(nameIndex),
                        mimeType = c.getString(typeIndex),
                        sizeBytes = if (sizeIndex >= 0 && !c.isNull(sizeIndex)) {
                            c.getLong(sizeIndex)
                        } else {
                            null
                        },
                        lastModifiedMillis =
                            if (modifiedIndex >= 0 && !c.isNull(modifiedIndex)) {
                                c.getLong(modifiedIndex)
                            } else {
                                null
                            },
                        flags = c.getInt(flagsIndex),
                    ),
                )
            }
        }
    }
}
```

查询授权根目录时，`parentId` 取
`DocumentsContract.getTreeDocumentId(treeUri)`；进入子目录后，使用上一轮结果中的
`documentId`。文档 ID 只交回同一个 authority，不参与路径拼接。

这段代码消除了列表页的逐项属性查询，但不能保证任意 Provider 都支持分页和排序。
`QUERY_ARG_LIMIT`、`QUERY_ARG_OFFSET`、结构化排序参数属于 Provider 可选能力；
客户端应检查 Cursor extras 中的 `EXTRA_HONORED_ARGS`，不能仅凭传入参数就认定 Provider
已经执行。对于不支持分页的 Provider，客户端分批消费 Cursor 只能减少自身峰值内存，
不能减少 Provider 生成结果集的成本。

### `canWrite()` 不能代表“可覆盖内容”

Android 官方 SAF 指南专门提醒：`DocumentFile.canWrite()` 在支持删除或目录创建时也可能返回
`true`。要判断能否编辑内容，应直接查询 `COLUMN_FLAGS`，检查
`FLAG_SUPPORTS_WRITE`；创建、删除、rename、copy、move、trash 各有独立 flag。

## `ContentResolver`：Binder 是控制面，文件描述符是数据面

`ContentResolver.openFileDescriptor()` 经 Binder 调用 Provider 的 `openFile()`，
返回 `ParcelFileDescriptor`。Binder 负责 URI、模式、权限和文件描述符传递；拿到描述符后，
普通文件的正文读写由文件描述符完成，不会把每个数据块装入 Binder transaction。

因此，“大文件复制慢是 Binder buffer 被文件内容占满”通常是错误诊断。需要分别测量：

- `openFileDescriptor()` 返回前的 Provider、权限、认证和按需下载时间；
- 从 open 返回到首个字节的时间；
- 描述符上的持续读写吞吐；
- close、flush 或 Provider 提交远端修改的时间。

`"r"` 或 `"w"` 模式可能返回 pipe 或 socket pair，便于 Provider 流式生成或接收数据；
这类描述符通常不能 seek。`"rw"` 表示需要可寻址的磁盘文件，但 Provider 可以不支持。
写模式的 truncate 语义也由 Provider 实现决定。代码不能假定所有 URI 都能
`FileChannel.position()`、`size()`、`map()` 或 `transferTo()`。

### 大文件复制的通用实现

同一 Provider 内，如果源文档声明 `FLAG_SUPPORTS_COPY`，应优先调用
`DocumentsContract.copyDocument()`。Provider 可以在自身存储或服务端完成复制，避免文件内容
经过应用进程。跨 Provider 或不支持 copy 时，再做应用侧流式复制。

下面的实现面向可能由 pipe 支持的 URI，不要求 seek；取消由调用方在读写循环中协作完成：

```kotlin
@Throws(IOException::class)
fun copyDocumentBytes(
    resolver: ContentResolver,
    source: Uri,
    target: Uri,
    isCancelled: () -> Boolean,
): Long {
    val input = requireNotNull(resolver.openInputStream(source)) {
        "Provider returned no input stream"
    }
    val output = requireNotNull(resolver.openOutputStream(target, "wt")) {
        "Provider returned no output stream"
    }

    return input.use { from ->
        output.use { to ->
            val bytes = ByteArray(DEFAULT_BUFFER_SIZE)
            var total = 0L
            while (true) {
                if (isCancelled()) throw InterruptedIOException("Copy cancelled")
                val count = from.read(bytes)
                if (count < 0) break
                to.write(bytes, 0, count)
                total += count
            }
            to.flush()
            total
        }
    }
}
```

`openFileDescriptor(uri, mode, CancellationSignal)` 可以取消尚未完成的 open；
描述符返回之后，`CancellationSignal` 不会自动中断普通流读取，所以循环仍需协作取消。
复制失败后目标文档可能保留部分内容。应用要记录任务状态，必要时删除未完成目标，
不能把两个 Provider 间的复制当作原子操作。

对于确认是本地、可寻址普通文件的两个描述符，可以基准测试 `FileChannel.transferTo()`。
它在某些文件系统和内核上可以减少用户态复制，但对 pipe、转码流、云 Provider 或带偏移的
`AssetFileDescriptor` 不适用。接口名称不足以决定哪一种实现更快。

## Cursor、批处理和观察器的边界

### CursorWindow 分窗传输查询结果

远端查询返回 Cursor 时，Provider 生产 `CursorWindow`，客户端进程获得只读视图。
Cursor 移动超出当前窗口时可能要求 Provider 填充后续窗口。宽 projection、大字符串和
BLOB 会更快耗尽窗口空间，增加填充和内存成本。

查询应遵守四条规则：

- 明确 projection，不传 `null` 取全部列；
- selection 使用 `?` 和 `selectionArgs`，不拼接用户输入；
- 在工作线程遍历 Cursor，并用 `use` 及时关闭；
- 给可取消的界面查询传 `CancellationSignal`。

Provider 是否利用数据库索引，取决于该 authority 的契约和实现。MediaStore 的列、
索引与查询策略不能直接套到任意云盘 Provider。对第三方 Provider 使用未公开 SQL 表达式，
还可能被拒绝或忽略。

### `applyBatch()` 的原子性由 Provider 决定

`ContentResolver.applyBatch()` 把同一 authority 的
`ContentProviderOperation` 列表交给 Provider。官方契约明确写明：发生
`OperationApplicationException` 时，已经成功多少项由实现决定。

`DocumentsContract.createDocument()`、`copyDocument()`、`moveDocument()` 和
`renameDocument()` 使用 Provider 定义的文档调用，不会自动合入一笔通用
`ContentProviderOperation` 事务。跨 Provider 更不存在平台级文件事务。

批量文件工作应采用可恢复设计：

- 每项记录源 URI、目标 URI、操作状态和最近错误；
- 支持重试时检查目标是否已存在，避免重复副本；
- Provider 支持 copy/move flag 时使用原生操作；
- 应用侧复制完成后再更新任务状态；
- 失败清理也要容忍 URI 已失效或权限被撤销。

MediaStore 的批量用户授权是另一套 API。Android 11（API 30）引入
`createWriteRequest()`、`createTrashRequest()` 和 `createDeleteRequest()`；
它们生成用户确认用的 `PendingIntent`，不会把任意 SAF 文档操作变成事务。
对目标 Android 16（`BAKLAVA`）及以上的应用，每次请求最多包含 2000 个具体
MediaStore item URI，Android 17 应按这一限制分组。

### `ContentObserver` 是失效通知

`registerContentObserver(uri, notifyForDescendants, observer)` 监听 Provider 对 URI
发出的 `notifyChange()`。Provider 可以只通知集合 URI，也可以通知具体 item；
insert、update、delete flags 是可选信息。回调数量、粒度和顺序不能当作文件变更日志。

可靠做法是把回调当作“相关数据可能变了”：

1. 合并短时间内的重复通知。
2. 在工作线程重新查询受影响的目录或集合。
3. 比较文档 ID、修改时间、大小和业务版本。
4. 界面销毁时注销观察器。

云 Provider 还可能先返回部分结果，并在 Cursor extras 中设置
`DocumentsContract.EXTRA_LOADING`。加载完成后 Provider 再发变更通知。
客户端应显示加载状态，并允许同一目录重新查询。

## MediaStore、SAF 和 Photo Picker 怎么选

MediaStore 是共享媒体索引，适合图片、视频、音频的枚举、筛选、generation 增量和缩略图。
SAF 面向任意文档类型和用户选择的目录树。Photo Picker 面向用户主动选择的图片或视频，
无需获得整个媒体库的读取范围。

Photo Picker 从 Android 13（API 33）进入平台，并可在部分旧版本设备上通过模块获得。
它不是 SAF 的通用替代品：

- 不能选择任意 PDF、压缩包或源码目录；
- 不提供目录树编辑；
- 返回项可能来自云媒体 Provider；
- HDR 等媒体可能按应用能力转码；
- 性能取决于本地缓存、下载和转码，不能宣称一定比 SAF 快。

需要修改其他应用拥有的 MediaStore item 时，可用 `createWriteRequest()` 让用户成组授权。
这类写权限与发起请求的 Activity 生命周期关联，并且不支持持久化或前缀授权。
长时间后台读取 Photo Picker 结果时，应按官方指引持久化逐项读取权限。

媒体查询、分页、缩略图和 generation 同步的完整方案见 24.11 节；这里仅保留与
SAF 选型交叉的边界。

## Scoped Storage、FUSE 与 BPF

### SAF 不必经过 FUSE

SAF 调用的是 `DocumentsProvider`。云 Provider 可以返回 pipe；企业 Provider 可以代理远端
内容；本地 Provider 可以直接返回普通文件描述符。只有数据落在 Android 共享外部存储并经
模拟存储挂载访问时，才会进入 MediaProvider 的 FUSE 路径。

Android 11 弃用 `sdcardfs`，共享外部存储默认使用 FUSE 来执行 Scoped Storage 权限、
脱敏和媒体策略。应用内部 `/data/data` 不在这条挂载路径上；
应用专属外部目录也有专门的绕行和隔离处理。

### FUSE passthrough 减少持续读写开销

Android 12 开始支持 FUSE passthrough。打开文件时，FUSE daemon 完成权限判断；
符合条件时把下层文件引用交给内核，后续 read/write 可直接转发到下层文件系统。
Android 17 内核锚点
[`fs/fuse/passthrough.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/fuse/passthrough.c)
包含 `fuse_passthrough_read_iter()`、`write_iter()`、splice 和 mmap 路径。

passthrough 依赖设备内核、MediaProvider 和产品配置。应用无法从 API 名称判断它是否生效，
也不应通过申请更宽权限来换取它。open、权限检查、元数据查询和不满足条件的访问仍可能进入
FUSE daemon。

### Android 17 FUSE-BPF 的适用范围

Android 17 的
[`FuseDaemon.cpp`](https://android.googlesource.com/platform/packages/providers/MediaProvider/+/refs/tags/android-17.0.0_r1/jni/FuseDaemon.cpp)
会尝试取得 `/sys/fs/bpf/prog_fuseMedia_fuse_media`。源码注释限定当前 FUSE-BPF
只用于 `Android/data` 和 `Android/obb` 目录，使匹配请求直接转到下层文件系统。
对应内核实现位于
[`fs/fuse/fuse_bpf_backing.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/fuse/fuse_bpf_backing.c)。

普通应用从 Android 11 起不能通过 SAF 选择 `Android/data` 或 `Android/obb`。
因此，FUSE-BPF 不能作为普通 SAF 文档读写的性能依据。SAF 性能分析仍应从具体 Provider、
查询次数、open 延迟和描述符类型开始。

## Android 17 的文档 API 变化

AndroidX DocumentFile 1.1.0 没有新增批量元数据、Path 互操作或回收站封装。
Android 17 的变化位于平台 `DocumentsContract` 和 `DocumentsProvider`：

- `FLAG_SUPPORTS_TRASH`、`trashDocument()`；
- `FLAG_SUPPORTS_RESTORE`、`restoreDocumentFromTrash()`；
- `Root.FLAG_SUPPORTS_QUERY_TRASH`、`queryTrashDocuments()`；
- `COLUMN_CONTENT_SYNC_STATE_FLAGS`；
- 本地可用、存在本地修改、上传/下载进行中、上传/下载错误等同步状态位；
- `Root.FLAG_LIMITED_FUNCTIONALITY_WHEN_OFFLINE`。

客户端在 API 37 上仍需检查 `COLUMN_FLAGS`。下面的代码只在 Provider 声明回收站能力时调用
Android 17 API：

```kotlin
@RequiresApi(37)
fun trashIfSupported(
    resolver: ContentResolver,
    documentUri: Uri,
    flags: Int,
): Uri? {
    val supported =
        (flags and DocumentsContract.Document.FLAG_SUPPORTS_TRASH) != 0
    if (!supported) return null
    return DocumentsContract.trashDocument(resolver, documentUri)
}
```

文档进入回收站后，Provider 会撤销原文档的 URI grants。返回的新 URI 可能不同，
调用方必须更新自己的记录，不能继续使用旧 URI。

云文档列表可以读取 `COLUMN_CONTENT_SYNC_STATE_FLAGS`，区分内容已在本地、正在下载、
存在本地修改或发生同步错误。这个字段是可选列；缺失或 `null` 表示 Provider 没有提供状态，
不代表文件已经在本地。

### `content://` 与 `java.nio.file.Path` 没有通用转换

`Path` 表示文件系统 Provider 中的路径。Android 没有把任意 `content://` URI 映射成
`java.nio.file.Path` 的公开契约。拿到可寻址的 `ParcelFileDescriptor` 后可以使用
`FileChannel` 操作描述符，但不能从中恢复稳定的共享存储路径。

需要 Path 的第三方库有三种选择：

- 库支持文件描述符时，直接传递 fd，并约定所有权；
- 把文档复制到应用内部临时文件，再传入 Path；
- 更换支持 `InputStream`、`OutputStream` 或 `SeekableByteChannel` 的库。

临时副本需要空间检查、取消、清理和源文档变化检测。它是一种兼容策略，不应伪装成 URI
到路径的零成本转换。

## 场景选型

| 场景 | 推荐入口 | 实现重点 |
| --- | --- | --- |
| 应用内部配置、索引、下载中间文件 | 内部 `File` / Room | 原子替换、空间管理、避免主线程 I/O |
| 应用专属大文件 | `getExternalFilesDir()` + `File` | 卷状态、卸载清理、敏感数据风险 |
| 用户打开或保存 PDF、Office 文档 | `ACTION_OPEN_DOCUMENT` / `ACTION_CREATE_DOCUMENT` | 持久化 grant、工作副本、保存失败恢复 |
| 用户选择一个目录进行同步 | `ACTION_OPEN_DOCUMENT_TREE` + `DocumentsContract` | 一次 projection 取元数据、可恢复任务、Provider 差异 |
| 相册、视频库、音乐库 | MediaStore | 索引查询、generation、缩略图、用户授权 |
| 用户选择少量图片或视频 | Photo Picker | 云项、持久化逐项授权、转码延迟 |
| 文件管理、备份、杀毒等核心能力 | 合规评估后的 `MANAGE_EXTERNAL_STORAGE` | Play 声明、最小收集、仍不可访问其他应用专属目录 |

### 文档编辑器

远端或不可寻址文档适合“本地工作副本 + 显式保存”：

1. 打开 URI，复制到内部临时文件。
2. 编辑期间只操作内部文件。
3. 保存前重新读取源元数据，检查是否被外部修改。
4. 写回目标 URI；Provider 支持时使用 truncate 写模式。
5. 写回成功后更新基线元数据并删除临时文件。

修改时间和大小只能用于冲突提示，不能证明内容相同。需要强一致时，应用应保存内容摘要或
Provider 提供的业务版本。

### 文件管理器

目录列表应直接查询 `DocumentsContract`，不在 RecyclerView 绑定阶段调用
`DocumentFile.getName()`、`length()` 或 `lastModified()`。复制和移动按钮由
`COLUMN_FLAGS` 决定；Provider 原生 copy/move 优先，应用侧流式复制作为兼容路径。

### 云同步

WorkManager 只能保证调度约束，不能替应用保存 URI 权限。任务入队前持久化 grant，
输入数据只保存 URI 字符串和任务 ID，不把大量文件列表塞入 WorkRequest。
Worker 运行时重新查询目录、检查权限和网络约束，并按单项记录恢复进度。

## 性能监控与基准

### 线上指标分段记录

不要只记录一次“文件操作总耗时”。至少拆成：

| 指标 | 起止点 | 可帮助判断的问题 |
| --- | --- | --- |
| query 延迟 | 调用 `query()` 到获得 Cursor | Provider 启动、数据库或远端查询 |
| 首行延迟 | 获得 Cursor 到 `moveToFirst()` | CursorWindow 填充、远端结果 |
| 枚举行数与耗时 | 遍历开始到 Cursor 关闭 | 结果规模、窗口补充、对象分配 |
| open 延迟 | 调用 open 到取得描述符/流 | 权限、认证、下载、转码 |
| 首字节延迟 | open 返回到第一次成功读取 | pipe 生产方、存储唤醒 |
| 持续吞吐 | 首字节之后的 bytes / active time | 文件系统、网络、FUSE、复制实现 |
| close/提交延迟 | flush/close 开始到完成 | Provider 提交、远端上传、错误上报 |

维度至少包含 authority、MIME、操作类型、文件大小区间、是否本地、网络类型、
Android 版本和设备型号。URI、display name 和用户目录属于敏感信息，监控中应去标识化。

### StrictMode 和 Perfetto

StrictMode 的 `detectDiskReads()`、`detectDiskWrites()` 可发现应用自身主线程磁盘操作；
远端 Provider 中的耗时不一定表现为调用进程的磁盘违规。应用还应对 query、open、首字节、
copy、close 添加独立 trace section。

Perfetto 排查时关注：

- 调用线程是否在主线程等待 Binder；
- Provider 进程是否冷启动、被调度延迟或等待数据库锁；
- FUSE daemon、文件系统和块 I/O 是否活跃；
- 云 Provider 是否在 Binder 调用中同步等待网络；
- 复制线程是否频繁小读写或被取消后仍继续运行。

`dumpsys activity providers` 可以确认 authority 对应的 Provider 进程。
shell 用户不会继承应用通过选择器获得的 URI grant，使用 `adb shell content query`
失败不能证明应用内访问也会失败。

### 基准测试维度

同一操作至少覆盖：

- 本机 Provider与云 Provider；
- 冷启动与 Provider 已存活；
- 内容已在本地与需要下载；
- 小目录、大目录、深目录；
- 顺序读、随机读、写入和 rename；
- `DocumentFile` 便利调用与单次 projection；
- 支持与不支持 Provider 原生 copy；
- FUSE passthrough 可用与不可用的设备。

报告原始分布和错误率，不把一台设备的一次结果写成 Android 平台常量。

## `MANAGE_EXTERNAL_STORAGE` 的边界

`MANAGE_EXTERNAL_STORAGE` 是 Android 11 引入的特殊访问权限。它适用于文件管理、备份恢复、
杀毒、文档管理、设备迁移等以广泛文件访问为核心能力的应用。Google Play 要求提交权限声明
并通过审核；媒体访问或用户手动选择文件不是合格理由。

即使获得该权限，应用仍不能访问其他应用在 `Android/data` 下的专属目录。
这项权限也不会让云 SAF URI 变成本地路径。用它规避几次 Provider 查询，会扩大数据访问范围，
无法作为普通性能优化方案。

## 收尾检查

提交文件访问方案前，逐项确认：

- 访问对象属于应用内部、共享媒体、用户文档还是云文档；
- URI grant 是否覆盖任务生命周期；
- 列表是否用一次 projection 取得所需字段；
- Provider 的 query 参数和 `COLUMN_FLAGS` 是否已检查；
- open、首字节、持续吞吐和 close 是否分别计时；
- 代码是否兼容 pipe、未知长度和不可寻址描述符；
- copy/move 失败是否可恢复，是否会留下部分目标；
- `ContentObserver` 是否只用于触发重查；
- Android 17 同步状态、trash/restore 能力是否按可选字段处理；
- 日志和监控是否避免保存用户文件名与 URI。

## 参考资料

- [Android 共享文档与 SAF 指南](https://developer.android.com/training/data-storage/shared/documents-files)
- [`DocumentFile` API 与性能说明](https://developer.android.com/reference/androidx/documentfile/provider/DocumentFile)
- [AndroidX DocumentFile 1.1.0 发布说明](https://developer.android.com/jetpack/androidx/releases/documentfile)
- [`ContentResolver` API](https://developer.android.com/reference/android/content/ContentResolver)
- [`DocumentsContract` API](https://developer.android.com/reference/android/provider/DocumentsContract)
- [`MediaStore` API](https://developer.android.com/reference/android/provider/MediaStore)
- [Photo Picker 指南](https://developer.android.com/training/data-storage/shared/photo-picker)
- [Scoped Storage 实现说明](https://source.android.com/docs/core/storage/scoped)
- [FUSE passthrough](https://source.android.com/docs/core/storage/fuse-passthrough)
- [Google Play 的 All files access 政策](https://support.google.com/googleplay/android-developer/answer/10467955)
- [Android 17 `DocumentsContract.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/provider/DocumentsContract.java)
- [Android 17 `DocumentsProvider.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/provider/DocumentsProvider.java)
- [Android 17 `FuseDaemon.cpp`](https://android.googlesource.com/platform/packages/providers/MediaProvider/+/refs/tags/android-17.0.0_r1/jni/FuseDaemon.cpp)
