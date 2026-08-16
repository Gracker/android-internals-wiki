---
title: "SAF 文件访问性能：DocumentFile、ContentResolver 与路径选择"
chapter: "24.18"
section: "24.18"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [SAF, DocumentFile, ContentResolver, ScopedStorage, IO, performance, file-access]
related_chapters: ["6.6", "6.7", "24.1", "24.11"]
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
last_draft_polish_at: "2026-08-15T13:24:49+08:00"
last_draft_polish_run_id: "20260815-132449-gracker-writing-439"
last_verified: "2026-08-15"
last_review_finalize_at: "2026-08-15T13:24:49+08:00"
last_review_finalize_run_id: "20260815-132449-gracker-writing-439"
confidence: high
sources:
- type: official
  path: "https://developer.android.com/training/data-storage/shared/documents-files"
- type: official
  path: "https://developer.android.com/reference/androidx/documentfile/provider/DocumentFile"
- type: official
  path: "https://developer.android.com/reference/android/provider/DocumentsContract"
- type: official
  path: "https://developer.android.com/reference/android/provider/MediaStore"
- type: official
  path: "https://developer.android.com/training/data-storage/shared/photo-picker"
- type: aosp
  path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/provider/DocumentsProvider.java"
- type: aosp
  path: "https://android.googlesource.com/platform/packages/providers/MediaProvider/+/refs/tags/android-17.0.0_r1/jni/FuseDaemon.cpp"
- type: kernel
  path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/fuse/fuse_bpf_backing.c"
---

# SAF 文件访问性能：DocumentFile、ContentResolver 与路径选择

Android 的文件访问入口很多，性能问题往往来自入口与场景不匹配：把 `content://` URI（统一资源标识符）当成本地路径，把 `DocumentFile` 当成批量查询接口，或在取得文件描述符后仍把每次读写都归因于 Binder。

本文以 Android 17（API 37，AOSP 标签 `android-17.0.0_r1`）为版本基线，说明存储访问框架（Storage Access Framework，SAF）、`DocumentFile`、`ContentResolver`、MediaStore 和直接文件路径的性能边界。判断依据是查询、打开文件和传输数据分别经过哪些组件，而非给这些入口排列固定的快慢顺序。

## 先分清五种访问入口

SAF 由系统文件选择器、`DocumentsContract` 协议和文档提供器共同组成。文档提供器是 `DocumentsProvider` 的实现，本文简称 Provider；它负责列出文档、检查权限并提供内容。`content://` URI 中类似主机名的部分叫作 `authority`，用于标识负责处理该 URI 的 Provider。

同一个 `content://` 形式可以对应完全不同的存储对象，例如：

- 本机共享存储上的普通文件；
- USB、SD 卡或工作资料中的文件；
- 云文档提供方按需下载的对象；
- Provider 通过管道（pipe）或成对套接字（socket pair）即时生成的数据流；
- 没有可直接读取二进制内容的虚拟文档。

因此，同一套 API 在两个 Provider 上可能有不同的延迟、随机访问能力和错误类型。性能记录至少要包含 `authority`、Provider 类型、内容是否已缓存在本机、访问模式和文件大小。只给出 SAF 与 `File` 的单一快慢比较，无法用于定位问题，也不适合外推到其他 Provider。

| 访问入口 | 适合场景 | 调用路径 | 主要边界 |
| --- | --- | --- | --- |
| `File` / `java.nio.file.Path` | 应用内部目录、应用专属外部目录、应用可合法直接访问的文件 | 应用 → 内核虚拟文件系统层（VFS）→ 具体文件系统 | 仍受分区存储（Scoped Storage）约束；存储卷状态变化时路径可能失效 |
| SAF + `DocumentsContract` | 用户选择的文档、目录树或云盘内容 | 应用 → `ContentResolver` → `DocumentsProvider` | 元数据查询和打开操作可能跨进程；能力由标志位（flag）声明 |
| AndroidX `DocumentFile` | 少量文件的便利操作、兼容 `File` 风格的调用 | 对 `DocumentsContract` 的轻量封装 | 属性方法通常各自查询，大目录容易形成一次列表查询加 N 次属性查询 |
| MediaStore | 共享图片、视频、音频和下载项的索引访问 | 应用 → `MediaProvider` 数据库；内容读取再打开 URI | 受媒体权限、所有权和用户授权约束 |
| Photo Picker | 用户选择少量图片或视频 | 系统照片选择器 → 本地或云媒体 Provider | 只覆盖图片和视频；读取前可能下载或转码 |

选择入口时，先按数据归属判断。应用内部数据优先放在 `filesDir`、`cacheDir` 或数据库中，这些位置可以直接使用 `File`，也不经过共享外部存储的 FUSE（用户空间文件系统）挂载。用户希望在卸载应用后仍保留的文档，使用 SAF 或合适的共享集合。图片、视频和音频的列表与批量筛选交给 MediaStore；只需用户挑选少量图片或视频时，优先使用 Photo Picker。

## SAF 的授权和 URI 语义

`ACTION_OPEN_DOCUMENT` 让用户选择并授权单个文档，`ACTION_CREATE_DOCUMENT` 让用户指定新文档的位置，`ACTION_OPEN_DOCUMENT_TREE` 则授权一棵目录树。这里的 URI 授权（URI grant）是系统赋予调用应用的读写能力，不等同于传统文件权限。

从 Android 11（API 30）开始，`ACTION_OPEN_DOCUMENT_TREE` 不能选择内部存储卷或可靠 SD 卡卷的根目录，也不能选择 `Download` 根目录、`Android/data` 和 `Android/obb`。选择器界面是否展示某个位置，与应用能否取得该位置的树授权是两件事。

`DocumentsContract.Document.COLUMN_DOCUMENT_ID` 由 Provider 自行定义。客户端只能把它当作不透明标识：可以原样交回同一个 `authority`，不能解析其中的路径含义。一个文档也可能同时出现在多个父目录中。以下假设都不成立：

- 从 URI 字符串截取 `/storage/emulated/0/...`；
- 把显示名称（display name）拼成子文档 URI；
- 假定重命名后 URI 不变；
- 假定同一个 URI 永远对应本机普通文件；
- 用 `File(uri.path)` 打开 `content://` URI。

### 需要跨重启使用时，及时持久化授权

选择器通过结果 `Intent` 临时授予 URI 访问权。需要在设备重启后继续编辑，或把任务交给 WorkManager 后台执行时，应在收到结果后调用 `takePersistableUriPermission()`，持久化 Provider 已经授予的访问位。

这段实现只保存结果 `Intent` 中已有的读写访问位，不额外申请 Provider 没有授予的写权限：

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

`takePersistableUriPermission()` 管理的是授权生命周期，不会加快读取速度，也不应放进每次打开文件或每个 Worker 的循环中。文档被删除、移动，或 Provider 撤销授权后，持久化记录仍可能失效。任务开始前要检查访问结果，处理 `SecurityException` 和 `FileNotFoundException`，并提供重新选择文档的入口。长期不用的授权通过 `releasePersistableUriPermission()` 释放。

Photo Picker 返回的媒体 URI 也可以为长任务持久化逐项读取权限。该权限只覆盖用户选中的图片或视频，不等同于目录树授权。

## `DocumentFile` 的性能成本来自哪里

AndroidX 官方文档将 `DocumentFile` 定义为模仿 `File` 的便利封装，并明确提示它会增加较多开销。需要批量读取元数据或使用完整的文档能力时，应直接调用 `DocumentsContract`。截至 2026 年 8 月，稳定版本仍是 `androidx.documentfile:documentfile:1.1.0`。

### `listFiles()` 是一次查询

[`TreeDocumentFile.listFiles()`](https://android.googlesource.com/platform/frameworks/support/+/27495ca3d1fe4a1166bea16413ecf8cff5d85855/documentfile/documentfile/src/main/java/androidx/documentfile/provider/TreeDocumentFile.java) 先用 `buildChildDocumentsUriUsingTree()` 构造子项集合 URI，再执行一次 `ContentResolver.query()`，只读取 `COLUMN_DOCUMENT_ID`。它遍历查询结果游标（`Cursor`），把每个文档 ID 包装成新的 `TreeDocumentFile`。

所以，目录中有 N 个文件时，`listFiles()` 本身通常只发起一次查询。`Cursor` 分批装载数据或远端 Provider 的内部实现仍可能发生多次进程间通信（IPC）；Java 代码没有逐项调用 `query()`。

### 属性读取会形成 N+1

额外查询发生在取得数组以后。`TreeDocumentFile.getName()`、`getType()`、`lastModified()`、`length()` 和 `exists()` 会进入 [`DocumentsContractApi19`](https://android.googlesource.com/platform/frameworks/support/+/27495ca3d1fe4a1166bea16413ecf8cff5d85855/documentfile/documentfile/src/main/java/androidx/documentfile/provider/DocumentsContractApi19.java)，每次方法调用各自查询一两个字段。

这就是常说的 N+1 查询：先查一次列表，再为 N 个结果各查一次属性。目录有 N 个子项时，这段代码会产生一次列表查询和 N 次名称查询：

```kotlin
val names = directory.listFiles().mapNotNull { it.name }
```

少量、低频的交互可以接受这项成本。文件管理器、同步器或大目录扫描应在一次子项查询中取得 ID、名称、媒体类型（MIME type，例如 `image/jpeg`）、大小、修改时间和能力标志位。

`DocumentFile.findFile(name)` 也会先调用 `listFiles()`，再逐项调用 `getName()`。在同一目录中循环查找多个名称，会反复枚举并查询属性。批量查找应先构建一次名称索引，并定义名称重复时的处理规则；Provider 不保证显示名称唯一。

### 一次查询取齐列表所需字段

查询中的投影（projection）是需要 Provider 返回的列名数组。这个实现把目录列表所需的字段放入一个投影；调用方传入树授权 URI、目标目录的文档 ID 和用于取消查询的 `CancellationSignal`，并在工作线程执行查询：

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

查询授权根目录时，`parentId` 取 `DocumentsContract.getTreeDocumentId(treeUri)`；查询某个子目录时，使用上一轮结果中的 `documentId`。文档 ID 只应交回同一个 `authority`，不参与路径拼接。

这段代码消除了列表页的逐项属性查询。分页和排序仍由 Provider 决定是否支持。`QUERY_ARG_LIMIT`、`QUERY_ARG_OFFSET` 和结构化排序参数都属于可选查询能力；客户端要检查 `Cursor` 附加数据（`getExtras()`）中的 `EXTRA_HONORED_ARGS`，确认哪些参数已被接受。若 Provider 不支持分页，客户端分批遍历 `Cursor` 只能降低自身的峰值内存，无法减少 Provider 生成整个结果集的成本。

### `canWrite()` 不表示可以改写内容

Android 官方 SAF 指南提醒，`DocumentFile.canWrite()` 在文档可删除或目录可创建子项时也可能返回 `true`。判断能否改写文件内容时，应查询 `COLUMN_FLAGS` 并检查 `FLAG_SUPPORTS_WRITE`。创建、删除、重命名、复制、移动和移入回收站分别有自己的能力标志位，不能用一个布尔值代替。

## `ContentResolver`：Binder 负责协商，文件描述符负责传输

Binder 是 Android 的进程间通信机制。`ContentResolver.openFileDescriptor()` 通过 Binder 调用 Provider 的 `openFile()`，取得包装系统文件描述符的 `ParcelFileDescriptor`。这一步传递 URI、打开模式、授权信息和文件描述符，可以称为控制阶段。对于普通文件，随后的内容读写直接通过文件描述符进行，可以称为数据传输阶段；文件内容不会逐块放进 Binder 事务。

大文件复制缓慢时，应分别测量以下阶段，不能只归因于 Binder 缓冲区：

- `openFileDescriptor()` 返回前的 Provider 启动、权限检查、身份认证和按需下载时间；
- 打开调用返回到首个字节的时间；
- 描述符上的持续读写吞吐；
- 刷新与关闭流，以及 Provider 提交远端修改的时间。

`"r"` 或 `"w"` 模式可能得到管道或成对套接字，便于 Provider 边生成边发送或边接收边处理。这类描述符一般只能顺序访问，不能随意改变读写位置（seek）。`"rw"` 表示调用方需要可读写、可定位的文件，Provider 仍可以拒绝该模式。写入时是否截断原内容也由 Provider 实现决定。代码不能假定所有 URI 都支持 `FileChannel.position()`、`size()`、`map()` 或 `transferTo()`。

### 大文件复制的通用实现

在同一个 Provider 内，如果源文档声明 `FLAG_SUPPORTS_COPY`，应优先调用 `DocumentsContract.copyDocument()`。Provider 可能在自身存储或云服务端完成复制，无需让文件内容经过应用进程。跨 Provider 复制，或 Provider 未声明复制能力时，再由应用流式传输内容。

这个实现兼容由管道提供内容的 URI，不要求随机访问；调用方在读写循环中检查取消状态：

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

`openFileDescriptor(uri, mode, CancellationSignal)` 可以取消尚未完成的打开请求。描述符返回后，`CancellationSignal` 不会自动中断普通流读取，所以读写循环仍要主动检查取消状态。

复制失败后，目标文档可能留下部分内容。应用要记录任务状态，并在适当时机删除未完成的目标。原子复制要求操作失败时不留下部分结果；两个 Provider 之间没有这项保证。

如果两个描述符已经确认对应本机可随机访问的普通文件，可以基准测试 `FileChannel.transferTo()`。在部分文件系统和内核上，它能减少应用进程中的数据复制；它不适用于管道、转码流、云 Provider，也不能直接套用于带起始偏移的 `AssetFileDescriptor`。应以目标设备和目标 Provider 的测量结果决定实现，不能从接口名称推断速度。

## Cursor、批处理和观察器的边界

### `CursorWindow` 分批承载查询结果

跨进程查询返回 `Cursor` 时，Provider 使用 `CursorWindow` 承载一批行，客户端进程读取其只读视图。当游标移动到当前窗口以外的行时，系统可能要求 Provider 填充另一个窗口。投影包含的列越多，或结果中有大字符串和二进制大对象（BLOB），窗口越容易装满，后续填充次数与内存开销也会增加。

查询时遵守四条规则：

- 明确列出投影，不传 `null` 读取全部列；
- 筛选条件（selection）使用 `?` 占位符和 `selectionArgs`，不拼接用户输入；
- 在工作线程遍历 `Cursor`，并用 `use` 及时关闭；
- 可取消的界面查询传入 `CancellationSignal`。

Provider 是否利用数据库索引，取决于该 `authority` 的公开契约和具体实现。MediaStore 的列、索引与查询策略不能直接套到任意云盘 Provider。第三方 Provider 还可能拒绝或忽略未公开的 SQL 表达式。

### `applyBatch()` 的原子性由 Provider 决定

`ContentResolver.applyBatch()` 把同一 `authority` 的 `ContentProviderOperation` 列表交给 Provider；列表中的对象描述插入、更新、删除等内容操作。官方契约明确说明：如果发生 `OperationApplicationException`，其中多少项已经生效由 Provider 实现决定。调用 `applyBatch()` 本身不等于获得跨实现一致的事务保证。

`DocumentsContract.createDocument()`、`copyDocument()`、`moveDocument()` 和 `renameDocument()` 使用文档协议中的专用调用，不会自动合并到一笔通用的 `ContentProviderOperation` 事务中。Android 也不提供跨 Provider 的文件事务。

批量文件工作应采用可恢复设计：

- 为每项记录源 URI、目标 URI、操作状态和最近一次错误；
- 支持重试时检查目标是否已存在，避免重复副本；
- Provider 声明复制或移动能力时使用其原生操作；
- 应用侧复制完成后再更新任务状态；
- 失败清理也要容忍 URI 已失效或权限被撤销。

MediaStore 的批量用户授权属于另一套 API。Android 11（API 30）引入 `createWriteRequest()`、`createTrashRequest()` 和 `createDeleteRequest()`，由它们生成封装待执行系统操作的 `PendingIntent`，再显示系统确认界面。这些 API 不会为任意 SAF 文档提供事务能力。

应用以 Android 16（API 36，`BAKLAVA`）或更高版本为目标时，一次请求最多包含 2000 个具体的 MediaStore 项目 URI；超过上限会抛出 `IllegalArgumentException`。在 Android 17 上也要按 2000 项分组，并分别处理用户取消或部分批次未执行的情况。

### `ContentObserver` 是失效通知

`ContentObserver` 是内容变化观察器。`registerContentObserver(uri, notifyForDescendants, observer)` 监听 Provider 通过 `notifyChange()` 发出的通知。Provider 可以通知集合 URI，也可以通知具体项目；插入、更新和删除的操作标志同样是可选信息。回调的数量、粒度和顺序都不构成可靠的文件变更日志。

回调只表示相关数据可能已经变化，收到后重新查询：

1. 合并短时间内的重复通知。
2. 在工作线程重新查询受影响的目录或集合。
3. 比较文档 ID、修改时间、大小和 Provider 提供的业务版本。
4. 界面销毁时注销观察器。

云 Provider 还可能先返回部分结果，并在 `Cursor` 的附加数据中设置 `DocumentsContract.EXTRA_LOADING`，表示列表仍在加载。加载完成后，Provider 再发送变更通知。客户端应展示加载状态，并允许对同一目录重新查询。

## MediaStore、SAF 和 Photo Picker 怎么选

MediaStore 是共享媒体索引，适合枚举和筛选图片、视频、音频，也提供缩略图和增量同步所需的世代号（generation）。世代号由 MediaStore 随数据库变化递增，比文件修改时间更适合判断索引变化；如果 MediaStore 的版本发生变化，仍要执行一次全量同步。SAF 面向任意文档类型和用户选择的目录树。Photo Picker 只授予用户选中的图片或视频，无需申请整个媒体库的读取范围。

Photo Picker 从 Android 13（API 33）进入平台。支持模块化系统更新的 Android 11 及以上设备可以通过系统模块获得它；支持 Google Play 服务的 Android 4.4 至 Android 10 设备，以及部分 Android Go 11/12 设备，还可安装回移版本。AndroidX Activity 的 `ActivityResultContracts.PickVisualMedia` 依次尝试平台 Photo Picker、OEM 或系统应用提供的兼容选择器，最终回退到 `ACTION_OPEN_DOCUMENT`。因此，不能只根据系统版本判断选择器实现。

Photo Picker 的范围比 SAF 窄：

- 不能选择任意 PDF、压缩包或源码目录；
- 不提供目录树编辑；
- `PickVisualMedia` 返回的 URI 只读，不会授予写权限；
- 返回项可能来自云媒体 Provider；
- 高动态范围（HDR）视频可能根据应用的解码能力转码；
- 打开延迟取决于本地缓存、云端下载和转码，不能预设它比 SAF 快。

需要修改其他应用拥有的 MediaStore 项目时，可以用 `createWriteRequest()` 请求用户成组授权。该写权限与发起请求的 `Activity` 生命周期绑定，不支持持久化授权或 URI 前缀授权。后台服务或作业需要继续使用时，要按 API 文档通过带授权标志的 `ClipData` 或 `Intent` 传递 URI。长时间后台读取 Photo Picker 结果属于另一种场景，应持久化用户所选项目的逐项读取权限。

24.11 节给出了媒体查询、分页、缩略图和世代号同步的完整实现。

## Scoped Storage、FUSE 与 BPF

### SAF 请求不一定经过 FUSE

FUSE（Filesystem in Userspace）是一种让用户空间进程处理文件系统请求的机制。Android 使用它管理共享外部存储的权限与存储视图。SAF 调用的对象则是 `DocumentsProvider`：云 Provider 可以返回管道，企业 Provider 可以代理远端内容，本地 Provider 也可以直接返回普通文件描述符。只有内容位于 Android 共享外部存储并通过模拟存储挂载访问时，才可能进入 MediaProvider 的 FUSE 路径。

Android 11 弃用 `sdcardfs`，共享外部存储改用新版 FUSE 执行分区存储的权限、隐私与媒体策略。应用内部数据目录（如 `/data/user/0/<package>`）不在这条挂载路径上；`Android/data` 和 `Android/obb` 中的应用专属外部目录也有独立的隔离与访问处理。因此，某次 SAF 访问较慢时，不能在没有路径证据的情况下把原因归给 FUSE。

### FUSE 透传减少持续读写开销

Android 12 开始支持 FUSE 透传（passthrough）。打开文件时，FUSE 守护进程先完成权限判断；满足条件时，它把下层文件引用交给内核，随后的读写请求可直接转发到下层文件系统，减少内核与用户空间之间的往返。Android 17 内核的 [`fs/fuse/passthrough.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/fuse/passthrough.c) 包含 `fuse_passthrough_read_iter()`、`write_iter()`、用于在文件描述符间传递数据的 `splice`，以及内存映射（`mmap`）路径。

透传是否可用取决于设备内核、MediaProvider 和产品配置，应用无法从 API 名称判断某个文件是否启用了透传。打开文件、权限检查、元数据查询和不满足透传条件的访问仍可能进入 FUSE 守护进程。申请更宽的存储权限也不能保证启用透传。

### Android 17 FUSE-BPF 的适用范围

Android 17 的 MediaProvider 包含 FUSE-BPF 支持。BPF 是可在内核受控环境中运行的小程序机制；这里的用途是把匹配路径的请求转给下层文件系统。[`FuseDaemon.cpp`](https://android.googlesource.com/platform/packages/providers/MediaProvider/+/refs/tags/android-17.0.0_r1/jni/FuseDaemon.cpp) 会尝试取得 `/sys/fs/bpf/prog_fuseMedia_fuse_media`，并在源码注释中将当前范围限定为 `Android/data` 和 `Android/obb`。对应的内核支撑代码位于 [`fs/fuse/fuse_bpf_backing.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/fuse/fuse_bpf_backing.c)。

普通应用从 Android 11 起不能通过 SAF 选择 `Android/data` 或 `Android/obb`。FUSE-BPF 因而不适合作为普通 SAF 文档读写的性能依据。分析 SAF 性能时，仍应先确认具体 Provider、查询次数、打开延迟和描述符类型。

## Android 17 的文档 API 变化

AndroidX DocumentFile 1.1.0 没有提供批量元数据、`Path` 转换或回收站封装。Android 17 的新增能力位于平台 `DocumentsContract` 和 `DocumentsProvider`，是否可用仍由 Provider 的列与标志位决定：

- `FLAG_SUPPORTS_TRASH`、`trashDocument()`；
- `FLAG_SUPPORTS_RESTORE`、`restoreDocumentFromTrash()`；
- `Root.FLAG_SUPPORTS_QUERY_TRASH`、`queryTrashDocuments()`；
- `COLUMN_CONTENT_SYNC_STATE_FLAGS`；
- `COLUMN_ORIGINAL_RELATIVE_PATH`，表示回收站文档原位置的相对路径；
- 本地可用、存在本地修改、上传或下载进行中、上传或下载失败等同步状态位；
- `Root.FLAG_LIMITED_FUNCTIONALITY_WHEN_OFFLINE`。

`Root.FLAG_LIMITED_FUNCTIONALITY_WHEN_OFFLINE` 告诉系统文件选择器：离线时，如果文档内容不在本机，打开、复制和移动等依赖内容的操作可能不可用。重命名和删除等不读取内容的操作不受这条规则影响。

客户端在 API 37 上仍要先检查 `COLUMN_FLAGS`。这个实现只在 Provider 声明回收站能力时调用 Android 17 API：

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

文档进入回收站后，框架会撤销原文档 ID 对应的 URI 授权。Provider 返回的新 URI 可能使用不同的文档 ID；调用方要更新记录，并在访问失败时重新取得合适的授权，不能继续依赖旧 URI。

云文档列表可以读取 `COLUMN_CONTENT_SYNC_STATE_FLAGS`，区分内容是否已在本机、是否存在待上传的本地修改、上传或下载是否正在进行，以及最近一次同步是否失败。这是可选列；缺失或 `null` 只表示 Provider 没有报告状态，不能解释成文件已经在本机。

### `content://` 与 `java.nio.file.Path` 没有通用转换

`java.nio.file.Path` 表示某个文件系统中的路径。Android 没有公开契约可以把任意 `content://` URI 映射成 `Path`。取得支持随机访问的 `ParcelFileDescriptor` 后，可以用 `FileChannel` 操作该描述符；描述符本身仍不能还原出稳定的共享存储路径。

第三方库只接受 `Path` 时，可以选择：

- 如果库也支持文件描述符，直接传递文件描述符（fd），并约定由哪一方负责关闭；
- 把文档复制到应用内部临时文件，再传入 `Path`；
- 更换支持 `InputStream`、`OutputStream` 或 `SeekableByteChannel` 的库。

使用临时副本时，要检查可用空间，支持取消和清理，并检测源文档在编辑期间是否变化。这种兼容方案包含复制成本，不能视为 URI 到路径的直接转换。

## 场景选型

| 场景 | 推荐入口 | 实现重点 |
| --- | --- | --- |
| 应用内部配置、索引、下载中间文件 | 内部 `File` / `Room` 数据库 | 原子替换、空间管理、避免在主线程读写 |
| 应用专属大文件 | `getExternalFilesDir()` + `File` | 卷状态、卸载清理、敏感数据风险 |
| 用户打开或保存 PDF、Office 文档 | `ACTION_OPEN_DOCUMENT` / `ACTION_CREATE_DOCUMENT` | 持久化 URI 授权、工作副本、保存失败恢复 |
| 用户选择一个目录进行同步 | `ACTION_OPEN_DOCUMENT_TREE` + `DocumentsContract` | 一次投影查询取得元数据、可恢复任务、Provider 差异 |
| 相册、视频库、音乐库 | MediaStore | 索引查询、世代号同步、缩略图、用户授权 |
| 用户选择少量图片或视频 | Photo Picker | 云项、持久化逐项授权、转码延迟 |
| 文件管理、备份恢复、杀毒等核心能力 | 通过权限与政策评估后的 `MANAGE_EXTERNAL_STORAGE` | Play 权限声明、最小化数据访问、仍不可访问其他应用的专属目录 |

这张表先按数据归属缩小选择范围，再依据 Provider 能力与实测结果决定具体实现。单纯为了减少几次查询，不应从 SAF 改成访问范围更广的权限。

### 文档编辑器

远端文档或不能随机访问的文档，适合采用本地工作副本，并由用户明确触发保存：

1. 打开 URI，复制到内部临时文件。
2. 编辑期间只操作内部文件。
3. 保存前重新读取源元数据，检查是否被外部修改。
4. 写回目标 URI；确认 Provider 支持时使用会截断旧内容的写入模式。
5. 写回成功后更新基线元数据并删除临时文件。

修改时间和大小只能用于冲突提示，不能证明内容相同。需要严格判断时，应用应保存内容摘要，或使用 Provider 提供的业务版本号。

### 文件管理器

目录列表应直接查询 `DocumentsContract`，不要在 `RecyclerView` 绑定列表项时调用 `DocumentFile.getName()`、`length()` 或 `lastModified()`。复制和移动按钮是否可用由 `COLUMN_FLAGS` 决定；Provider 的原生复制或移动优先，应用侧流式复制作为兼容方案。

### 云同步

WorkManager 负责按约束调度后台工作，不会替应用保存 URI 权限。任务入队前要持久化授权；输入数据只保存 URI 字符串和任务 ID，不把大量文件列表放入 `WorkRequest`。`Worker` 运行时重新查询目录，检查授权和网络条件，并根据每一项的状态记录恢复进度。

## 性能监控与基准

### 分段记录运行时指标

不要只记录文件操作总耗时，至少按阶段记录：

| 指标 | 起止点 | 可帮助判断的问题 |
| --- | --- | --- |
| 查询延迟 | 调用 `query()` 到获得 `Cursor` | Provider 启动、数据库或远端查询 |
| 首行延迟 | 获得 `Cursor` 到 `moveToFirst()` | `CursorWindow` 填充、远端首批结果 |
| 枚举行数与耗时 | 开始遍历到关闭 `Cursor` | 结果规模、窗口补充、对象分配 |
| 打开延迟 | 发起打开调用到取得描述符或流 | 权限检查、身份认证、下载、转码 |
| 首字节延迟 | 打开返回到第一次成功读取 | 管道生产方、存储设备唤醒 |
| 持续吞吐 | 首字节后的字节数 / 有效读写时间 | 文件系统、网络、FUSE、复制实现 |
| 关闭与提交延迟 | 开始刷新或关闭到操作完成 | Provider 提交、远端上传、错误上报 |

每条指标至少带上 `authority`、MIME 类型、操作类型、文件大小区间、内容是否在本机、网络类型、Android 版本和设备型号。URI、显示名称和用户目录属于敏感信息，采集前应删除或散列可识别用户的部分。

### StrictMode 和 Perfetto

StrictMode 是开发期的线程与资源违规检测工具。它的 `detectDiskReads()` 和 `detectDiskWrites()` 可以发现应用自身的主线程磁盘操作；远端 Provider 的耗时不一定表现为调用进程的磁盘违规。应用还应使用 `Trace` 为查询、打开、首字节、复制和关闭分别记录时间片，便于在 Perfetto 中区分各阶段。

Perfetto 是 Android 的系统级追踪工具。分析记录时关注：

- 调用线程是否在主线程等待 Binder；
- Provider 进程是否冷启动、被调度延迟或等待数据库锁；
- FUSE 守护进程、文件系统和块设备 I/O 是否活跃；
- 云 Provider 是否在 Binder 调用中同步等待网络；
- 复制线程是否频繁小读写或被取消后仍继续运行。

`dumpsys activity providers` 可以确认某个 `authority` 对应的 Provider 进程。ADB 命令运行在 `shell` 用户身份下，不会继承应用通过选择器取得的 URI 授权；`adb shell content query` 失败，不能证明应用进程内的同一访问也会失败。

### 基准测试维度

同一操作至少覆盖：

- 本机 Provider 与云 Provider；
- 冷启动与 Provider 已存活；
- 内容已在本地与需要下载；
- 小目录、大目录、深目录；
- 顺序读取、随机读取、写入和重命名；
- `DocumentFile` 便利调用与单次投影查询；
- Provider 支持与不支持原生复制；
- FUSE passthrough 可用与不可用的设备。

报告耗时分布和错误率，不把一台设备的一次测量结果写成 Android 平台常量。

## `MANAGE_EXTERNAL_STORAGE` 的边界

`MANAGE_EXTERNAL_STORAGE` 是 Android 11 引入的所有文件访问特殊权限。它只适用于以广泛文件访问为核心功能的应用，例如文件管理、备份恢复、杀毒、文档管理、设备迁移和设备内文件搜索。Google Play 要求应用提交权限声明并通过审核；媒体访问或让用户手动选择文件不属于获准理由。

取得该权限后，应用仍不能访问其他应用在 `Android/data` 中的专属目录。它也不会把云 SAF URI 转换成本地路径。为了减少几次 Provider 查询而申请这项权限，会无谓扩大数据访问范围，也不符合普通性能优化的用途。

## 实施前检查

提交文件访问方案前，确认：

- 访问对象属于应用内部、共享媒体、用户文档还是云文档；
- URI 授权是否覆盖任务生命周期；
- 列表是否用一次投影查询取得所需字段；
- Provider 的查询参数和 `COLUMN_FLAGS` 是否已检查；
- 打开、首字节、持续吞吐和关闭是否分别计时；
- 代码是否兼容管道、未知长度和不可随机访问的描述符；
- 复制或移动失败是否可恢复，是否会留下部分目标；
- `ContentObserver` 是否只用于触发重查；
- Android 17 同步状态、回收站与恢复能力是否按可选字段和标志位处理；
- 日志和监控是否避免保存用户文件名与 URI。

## 参考资料

- [Android 共享文档与 SAF 指南](https://developer.android.com/training/data-storage/shared/documents-files)
- [`DocumentFile` API 与性能说明](https://developer.android.com/reference/androidx/documentfile/provider/DocumentFile)
- [AndroidX DocumentFile 1.1.0 发布说明](https://developer.android.com/jetpack/androidx/releases/documentfile)
- [`ContentResolver` API](https://developer.android.com/reference/android/content/ContentResolver)
- [`DocumentsContract` API](https://developer.android.com/reference/android/provider/DocumentsContract)
- [`MediaStore` API](https://developer.android.com/reference/android/provider/MediaStore)
- [共享存储中的媒体访问指南](https://developer.android.com/training/data-storage/shared/media)
- [Photo Picker 指南](https://developer.android.com/training/data-storage/shared/photo-picker)
- [`ActivityResultContracts.PickVisualMedia` API](https://developer.android.com/reference/androidx/activity/result/contract/ActivityResultContracts.PickVisualMedia)
- [Scoped Storage 实现说明](https://source.android.com/docs/core/storage/scoped)
- [FUSE passthrough](https://source.android.com/docs/core/storage/fuse-passthrough)
- [Google Play 的 All files access 政策](https://support.google.com/googleplay/android-developer/answer/10467955)
- [Android 的所有文件访问说明](https://developer.android.com/training/data-storage/manage-all-files)
- [Android 17 `DocumentsContract.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/provider/DocumentsContract.java)
- [Android 17 `DocumentsProvider.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/provider/DocumentsProvider.java)
- [Android 17 `FuseDaemon.cpp`](https://android.googlesource.com/platform/packages/providers/MediaProvider/+/refs/tags/android-17.0.0_r1/jni/FuseDaemon.cpp)
