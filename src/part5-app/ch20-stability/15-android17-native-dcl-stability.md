---
title: "Android 17 Native DCL 只读约束与动态库加载稳定性"
chapter: "20.15"
section: "20.15"
status: "finalized"
drafted_by: "openclaw-task2a"
drafted_date: "2026-05-25"
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: [stability, native, dynamic-code-loading, android17, system-load]
related_chapters: ["1.58", "20.3", "20.13", "1.15"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-25"
gap_source: "官方文档/AOSP结构/每日信息"
last_verified: "2026-05-25"
last_verified_against: "Android Developers Android 14/17 behavior changes; Android Dynamic Code Loading security guidance; Android NDK JNI tips; AOSP native library namespace docs"
confidence: medium
task2a_state: processed
task2a_result: processed-draft
task6_state: "reviewed"
reviewed_by: openclaw-task6
reviewed_date: "2026-05-25"
task6_result: pass-light-edit
task9_state: "reviewed"
pipeline_stage: "ready-to-publish"
sources:
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-17#safer-native-dcl-c"
  - type: official
    path: "https://developer.android.com/about/versions/14/behavior-changes-14#safer-dynamic-code-loading"
  - type: official
    path: "https://developer.android.com/privacy-and-security/risks/dynamic-code-loading"
  - type: official
    path: "https://developer.android.com/ndk/guides/jni-tips#native-libraries"
  - type: aosp
    path: "https://source.android.com/docs/core/permissions/namespaces_libraries"
source_refs:
  - "[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Crash 监控：为我们应用插上监控 Native Crash 的电子眼.md]"
  - "[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Backtrace：Native 堆栈信息获取.md]"
  - "[结构参考: Clippings/Android 应用稳定性剖析与优化 - ELF 文件与 readelf & objdump ：了解 ELF 格式与解析工具.md]"
  - "[结构参考: Clippings/Android 应用稳定性剖析与优化 - Android.bp 文件与符号表：如何才能找到函数符号？.md]"
  - "[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Hook 全解析：Native 闯关入门秘籍.md]"
task9_result: "pass-tech-review"
task2b_state: fixed
task2b_result: fixed-lite
last_task2b_lite_at: "2026-06-01"
task9_reviewed_date: "2026-06-01"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-01T08:20:00+08:00"
last_task9_review_log: "logs/deep-review/2026-06-01-08-deep-review.md"
task9_review_notes: "2026-06-01 Task9 deep-review: pass-tech-review。复核 Android 17 Native DCL System.load 只读约束、Android 14 DEX/JAR DCL 顺序、发布状态机与崩溃归因边界；无 P0/P1/P2，Task6 已通过且 queue 无 pending，自动晋升 finalized。"
p0: 0
p1: 0
p2: 0
updated_by: "openclaw-task9"
updated_date: "2026-06-01"
task9_p0_issues: 0
task9_p1_issues: 0
task9_p2_issues: 0
last_task6_audit: "2026-07-12"
last_task9_audit: "2026-07-07"
last_task9_audit_log: "logs/deep-review/2026-07-07-20-audit.md"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-19
---

# 20.15 Android 17 Native DCL 只读约束与动态库加载稳定性

Android 17 把 native 动态代码加载的只读要求加到了 `System.load(path)` 路径。应用以 Android 17（API 37）为目标版本时，`System.load()` 看到目标文件仍可写，会在进入 native linker 前抛出 `UnsatisfiedLinkError`。受影响的常见场景包括：运行时下载 `.so`、从插件包解压 `.so`、把 assets 中的库释放到私有目录，以及某些兼容旧系统的“二次解压再加载”方案。

这项检查只解决“加载时文件仍可修改”这一类竞态。只读权限不能证明文件来自可信发布方，也不能替代签名、哈希、ABI、ELF、依赖库与回滚检查。排障时应把平台门禁、制品可信度和 linker 失败拆成三组证据。

平台源码锚点为 `android-17.0.0_r1`。16KB page size 相关结论沿用 20.13 的 Android 17 平台基线，不涉及 kernel 专属逻辑。

## 1. 先分清四条加载路径

同一份 `.so` 经由不同入口加载，Android 17 AOSP 中经过的 Java 代码并不相同：

| 入口 | Android 17 AOSP 路径 | `Runtime.load0()` 的可写检查 | 工程建议 |
|---|---|---:|---|
| `System.load("/abs/libx.so")` | `System.load() -> Runtime.load0() -> nativeLoad()` | 会经过 | 自管 native DCL 的主要适配对象 |
| `System.loadLibrary("x")` | `Runtime.loadLibrary0() -> ClassLoader.findLibrary() -> nativeLoad()` | 不经过同一段检查 | APK/AAB 随包库的常规入口，优先使用 |
| 自定义 `ClassLoader.findLibrary()` 配合 `loadLibrary()` | `loadLibrary0() -> nativeLoad()` | 不经过同一段检查 | 不应拿来规避平台约束；仍需可信发布和 linker 验证 |
| native 代码直接调用 `dlopen()` | bionic linker | 不经过 Java `Runtime.load0()` | 这只是调用边界，不能当兼容方案 |

表里的“不过检查”来自 `android-17.0.0_r1` 源码调用关系：`Runtime.load0()` 先检查文件，再调用 `nativeLoad()`；`loadLibrary0()` 根据 ClassLoader 找到文件名后直接调用 `nativeLoad()`。native `dlopen()` 从 C/C++ 进入 bionic linker，也不会回到 Java 的 `Runtime.load0()`。

这个边界不等于“换成 `dlopen()` 就安全了”。动态下载 native 代码仍会受到 linker namespace、ELF 格式、`DT_NEEDED`、符号解析、进程位数和 16KB page size 等约束；远程 DCL 还可能违反 Google Play 政策。工程迁移应优先减少 DCL，随应用发布的库继续使用 `System.loadLibrary()`。确需保留 DCL 时，即使当前入口不触发 Java 检查，也应按同一套只读与可信发布规则处理。

## 2. `Runtime.load0()` 到底检查了什么

在 `android-17.0.0_r1` 的 `libcore/ojluni/src/main/java/java/lang/Runtime.java` 中，`load0()` 的顺序是：

1. 要求传入绝对路径，否则抛出“`Expecting an absolute path of the library`”。
2. 读取进程 UID。普通应用 UID 才进入这条 DCL 检查；root、system、shell 有源码中的例外。
3. 文件系统本身可写且 `File.canWrite()` 返回 `true` 时，记录 unsafe DCL 事件。
4. 相关兼容开关启用且目标 SDK 至少为 API 37 时，抛出“`Attempt to load writable file: ...`”。
5. 检查通过后才调用 `nativeLoad(filename, classLoader, caller)`。

因此，`File.canWrite()` 是按当前进程身份得到的有效可写性判断，不能只看一组固定 mode bit。线上诊断可以同时记录 `stat` 权限位和 `canWrite()`，但加载前门禁应以后者为准。

还要注意目录权限：文件改成 `0400` 后，拥有可写父目录的进程仍可能 unlink 或 rename 该文件。只读文件能阻止原地改写，却不能单独保证“这个路径永远指向同一组字节”。版本化路径、禁止覆盖发布、签名校验与选择指针必须一起设计。

## 3. 只读是门禁，签名才回答“该不该信”

Android 官方建议尽量避免动态代码加载，并把代码放在可信位置。若业务必须下载 native 模块，至少需要下面四层约束：

- **来源**：包清单由发布系统签名，应用内只保存固定公钥或受控公钥链。服务端同一次响应里附带 SHA-256 只能发现偶发损坏，无法抵抗响应和文件一起被替换。
- **内容**：签名清单覆盖模块名、版本、ABI、长度、SHA-256、ELF Build ID、最低应用版本、最低/最高 API，以及允许回滚到哪些版本。
- **位置**：文件只进入应用私有目录。不要从共享外部存储加载，也不要信任其他进程可写的路径。
- **生命周期**：每个版本使用独立路径，发布后不覆盖；选择指针只指向已验证版本，失败版本持久化为 `BAD`。

远程下载 DCL 还要单独经过 Play 政策审查。技术上能够加载，并不表示分发方式符合商店政策。

## 4. 发布状态机：让读取者只看到完整版本

建议把“下载”和“启用”拆成明确状态：

`STAGED -> VERIFIED -> PUBLISHED -> SELECTED -> LOADED`

任何签名、哈希、ELF 或加载失败都进入 `BAD`；回滚只把选择指针切回已知可用版本，不改写原文件。各状态的含义如下：

- `STAGED`：临时文件已创建，还不可被加载线程选择。
- `VERIFIED`：签名清单、字节摘要、长度、ABI、ELF 元数据均通过。
- `PUBLISHED`：临时文件已在同一文件系统内原子 rename 到唯一版本路径。
- `SELECTED`：小型选择清单已通过 `AtomicFile` 或等价事务更新。
- `LOADED`：当前进程已经加载该版本；此后修改选择清单只影响新进程。

Android 没有面向应用的可靠通用 native 卸载与同进程热切换协议。库一旦被某个 ClassLoader 加载，JNI 注册、静态对象、线程、TLS 和函数指针都可能仍在使用。更稳妥的启用时机是下次进程启动；需要即时切换时，把插件放进可重启的隔离进程。

### 4.1 发布顺序

发布者应持有跨进程锁，并确保临时文件与目标文件位于同一私有文件系统。推荐顺序如下：

1. 用唯一临时文件名和 `O_CREAT | O_EXCL | O_CLOEXEC` 创建文件，拒绝复用旧临时文件或跟随既有符号链接。
2. 保持写 fd 已打开，立即用 `fchmod` 把路径标成 owner-read-only。
3. 通过这个已打开的 fd 流式写入，同时计算摘要；写完后 `fsync`。
4. 验证已签名清单、长度、摘要、ABI、ELF class/machine、Build ID 和依赖声明。
5. 用 `rename` 发布到唯一版本路径。若要求断电后也持久，随后同步父目录。
6. 原子更新选择清单。加载者只读取 `PUBLISHED` 且已被选择的版本。
7. 再次检查 `canWrite() == false`，然后调用 `System.load()`。

“先改成只读，再通过已打开 fd 写入”看起来反常，但它正是 Android DCL 文档用于消除时间窗口的顺序。`chmod` 改变路径对应 inode 的权限检查结果，不会撤销已经成功打开的写 fd。

下面的 Kotlin 代码只演示文件发布的关键顺序；跨进程锁、目录 `fsync`、ELF 解析和选择清单应由外围组件负责：

```kotlin
private fun publishLibrary(
    source: InputStream,
    tmp: File,
    finalFile: File,
    manifest: SignedNativeManifest,
    pinnedKey: PublicKey,
): File {
    require(tmp.parentFile == finalFile.parentFile)
    require(verifyManifestSignature(manifest, pinnedKey))
    require(finalFile.name == manifest.fileName)
    require(!finalFile.exists())

    val flags = OsConstants.O_WRONLY or
        OsConstants.O_CREAT or
        OsConstants.O_EXCL or
        OsConstants.O_CLOEXEC
    val fd = Os.open(
        tmp.absolutePath,
        flags,
        OsConstants.S_IRUSR or OsConstants.S_IWUSR,
    )

    try {
        // 路径先变为只读；已打开的 fd 仍可完成本次写入。
        Os.fchmod(fd, OsConstants.S_IRUSR)
    } catch (t: Throwable) {
        Os.close(fd)
        throw t
    }

    val digest = MessageDigest.getInstance("SHA-256")
    try {
        FileOutputStream(fd).use { output ->
            source.use { input ->
                val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
                while (true) {
                    val count = input.read(buffer)
                    if (count < 0) break
                    output.write(buffer, 0, count)
                    digest.update(buffer, 0, count)
                }
            }
            output.fd.sync()
        }

        require(tmp.length() == manifest.size)
        require(digest.digest().contentEquals(manifest.sha256))
        verifyElf(tmp, manifest)
        require(!tmp.canWrite())
        Os.rename(tmp.absolutePath, finalFile.absolutePath)
        return finalFile
    } catch (t: Throwable) {
        tmp.delete()
        throw t
    }
}
```

这段代码没有把整个库读进内存，摘要对应的也是写入 fd 的同一串字节。生产实现还要做到：目标版本的文件预先存在时拒绝覆盖；`rename` 后按耐久性需求同步父目录；发布结果进入状态存储后才允许加载。若 `verifyElf()` 需要打开文件，owner-read-only 权限不影响当前应用读取。

### 4.2 不要把 `File.renameTo()` 当成完整事务

`File.renameTo()` 只返回布尔值，失败原因不清晰，也无法表达“不覆盖目标”之类的额外规则。`Os.rename()` 能保留 `ErrnoException`，便于区分路径、权限和文件系统问题。无论使用哪一层 API，都要保证源与目标在同一文件系统，并在发布前确认目标版本名尚未占用。

原子 rename 只保证目录项切换，不自动保证掉电后的目录持久性，也不包含选择清单事务。对崩溃后必须恢复的模块，需要把“文件发布”和“选择指针更新”设计成可重放的两阶段恢复：启动扫描只接受完整签名且状态为 `PUBLISHED` 的版本，孤立临时文件可以延迟清理。

## 5. ABI、ELF 与 linker 约束仍然存在

只读检查通过后，`nativeLoad()` 才进入 ART/bionic 的加载路径。下面几类错误仍会表现为 `UnsatisfiedLinkError`：

### 5.1 不要直接取 `Build.SUPPORTED_ABIS[0]`

应用进程可能以 32 位或 64 位运行，设备列表的第一项不一定对应当前进程。选择模块时应同时检查：

- `Process.is64Bit()` 与 ELF `EI_CLASS`；
- ELF `e_machine` 与声明 ABI；
- 当前进程可用 ABI，而非设备理论支持的全部 ABI；
- 清单中的版本、Build ID 与文件内值一致。

跨 ABI 复用同一个版本目录会把发布错误伪装成 linker 错误。目录至少应包含规范化模块名、ABI 和不可变版本号，例如 `files/native/arm64-v8a/feature/42/libfeature.so`。

### 5.2 检查 `DT_NEEDED` 和 native namespace

依赖库必须能在调用者 ClassLoader 对应的 linker namespace 中解析。应用不能依赖未向应用公开的私有平台库；手工按猜测顺序逐个 `dlopen()` 依赖也很脆弱。发布前可用 `readelf -d` 列出 `DT_NEEDED`，再对照 APK 随包库与允许访问的系统公共库。

`System.loadLibrary()` 把 ClassLoader 和调用类传给 `nativeLoad()`，它们会参与 namespace 选择。把同一文件改成绝对路径 `System.load()`，并不能保证获得相同的依赖解析环境。

### 5.3 16KB page size 要检查 ELF program header

运行时释放出的裸 `.so` 要检查 ELF `PT_LOAD` 的 `p_align`，并按 20.13 的 Android 17 规则验证。APK ZIP 对齐只与“从 APK 直接 mmap 未压缩库”有关；文件已经解压到私有目录后，ZIP 对齐不再是该文件的加载条件。两者不要混成一个检查项。

## 6. 多进程与回滚

多进程应用常见的错误是：主进程正在发布版本 B，远程服务仍按旧清单加载版本 A，随后清理线程删掉 A。稳定策略可以收敛为四条：

- 只有一个发布者持有跨进程锁；锁内完成版本产物发布和选择清单更新。
- 读取者只加载状态为 `PUBLISHED` 的不可变路径，不打开临时文件。
- 已加载版本在对应进程退出前都视为被引用。缺少可靠存活引用统计时，至少保留 active 与 last-known-good 两个版本，并延迟清理更老版本。
- 版本 B 失败后写入 `BAD` 记录，选择指针回到 A；同一进程不要无限重试 B。

文件锁本身也不是业务状态。进程被杀后，内核会释放锁，但磁盘上可能留下临时文件或“文件已发布、指针未更新”的中间状态。恢复逻辑必须根据签名清单和持久状态判断，而不能根据“现在能拿到锁”推测前一次发布成功。

## 7. 失败分类与止损

`UnsatisfiedLinkError` 是一类宽泛异常。建议按消息和本地证据归类，避免看到异常类型就全算作 Android 17 只读问题：

| 类别 | 典型证据 | 处理 |
|---|---|---|
| Android 17 可写拒绝 | 消息包含 `Attempt to load writable file`，`canWrite() == true` | 标记发布流程故障，禁止重试同一路径 |
| 非绝对路径 | 消息包含 `Expecting an absolute path` | 修正 `System.load()` 调用参数 |
| ABI / ELF 不匹配 | `wrong ELF class`、`bad ELF magic` 或机器类型不符 | 禁用该制品，回到匹配 ABI |
| 16KB 不兼容 | ELF segment 对齐门禁失败或 linker 对齐错误 | 回到符合 20.13 基线的构建 |
| 依赖 / namespace | `library ... not found`、不可访问依赖 | 修正 `DT_NEEDED` 或随包依赖 |
| 符号错误 | `cannot locate symbol` | 回滚库与调用方版本组合 |
| 签名 / 摘要失败 | 本地验证未通过，尚未调用 loader | 删除临时文件并告警 |
| 并发 / 残缺文件 | 长度、状态、Build ID 不一致 | 修复发布事务，禁止加载 |

可选功能可以在加载边界捕获 `UnsatisfiedLinkError`，记录失败并关闭入口；捕获后严禁继续调用对应 JNI 方法。启动必需库应优先使用随包版本。若确有已签名且兼容的 last-known-good 动态版本，可以在新进程中回退；不要在已部分执行新版 JNI 的进程里强行换库。

## 8. 可观测证据包

一次加载事件至少记录以下字段：

- 应用版本、`targetSdkVersion`、系统 API、进程名、进程位数；
- 规范化模块名、版本、ABI、发布状态、选择清单版本；
- 文件长度、mode、`canWrite()`、摘要比对结果、签名 key id、ELF Build ID；
- 加载入口：`System.load`、`System.loadLibrary` 或 native `dlopen`；
- `DT_NEEDED` 检查结果、16KB 对齐结果；
- `UnsatisfiedLinkError` 的原始消息和归一化分类；
- 回退版本、`BAD` 标记和重试次数。

文件绝对路径可能包含用户或业务标识。上报时保留受控目录类型与规范化相对路径即可，不要把原始外部路径直接发送到服务端。摘要和 Build ID 可用于确认制品，库内容不应进入日志。

## 9. Android 17 灰度测试表

升级 `targetSdkVersion` 前，至少覆盖这些用例：

| 用例 | 预期 |
|---|---|
| target SDK 36，`System.load()` 加载可写测试库 | 用于观察兼容开关行为，不能把“仍可加载”当发布规则 |
| target SDK 37，`System.load()` 加载可写测试库 | 抛出带 `Attempt to load writable file` 的 `UnsatisfiedLinkError` |
| target SDK 37，加载按规定发布的只读库 | 通过只读门禁并进入 linker |
| `System.loadLibrary()` 加载随 APK/AAB 发布的库 | 常规路径正常 |
| native `dlopen()` 加载测试文件 | 验证它不经过 Java `load0()`；制品仍必须按可信只读规则发布 |
| 清单签名、SHA-256、长度任一错误 | 在 loader 调用前拒绝 |
| 错 ABI、错 ELF class、缺少 `DT_NEEDED`、未解析符号 | 分类为 linker/制品问题，不误报为权限问题 |
| 4KB 对齐库运行在 16KB 环境 | 被 20.13 的门禁或运行测试发现 |
| 两个进程同时发布和加载 | 读取者只见完整 `PUBLISHED` 版本 |
| rename 后、选择指针更新前杀进程 | 重启恢复到旧选择或完成可验证恢复 |
| 新版本加载失败 | 写入 `BAD`，新进程回退 last-known-good，不循环重试 |
| 可选模块加载失败 | 功能关闭且 JNI 不再被调用，主流程继续运行 |

测试里可以保留一条专门的 native `dlopen()` 用例，用于持续确认 AOSP 路径边界；这条用例的意义是防止监控归因错误，不是给线上方案寻找绕行入口。

## 10. 与相邻章节的边界

- 1.58 负责 native linker namespace、依赖解析与加载性能，这里只引用其加载约束。
- 20.3 负责 signal crash、tombstone、backtrace 和符号化。只读拒绝通常是 Java `UnsatisfiedLinkError`，尚未进入 native 执行。
- 20.13 负责 16KB page size 的 ELF 与 APK 兼容，这里只把对应结果纳入制品门禁。
- 1.15 负责 JNI 注册与调用边界。库加载失败后继续调用 native 方法，才会产生后续 JNI 故障。

## 参考资料

- [Android 17 behavior changes - Safer Native DCL-C](https://developer.android.com/about/versions/17/behavior-changes-17#safer-native-dcl-c)
- [AOSP `android-17.0.0_r1`：`java.lang.Runtime`](https://android.googlesource.com/platform/libcore/+/android-17.0.0_r1/ojluni/src/main/java/java/lang/Runtime.java)
- [AOSP `android-17.0.0_r1`：bionic linker](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/linker/linker.cpp)
- [Android 14 behavior changes - Safer dynamic code loading](https://developer.android.com/about/versions/14/behavior-changes-14#safer-dynamic-code-loading)
- [Dynamic Code Loading security risks](https://developer.android.com/privacy-and-security/risks/dynamic-code-loading)
- [Android NDK JNI tips - Native libraries](https://developer.android.com/ndk/guides/jni-tips#native-libraries)
- [AOSP：Namespaces for native libraries](https://source.android.com/docs/core/permissions/namespaces_libraries)
