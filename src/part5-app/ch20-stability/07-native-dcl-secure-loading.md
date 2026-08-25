---
title: Native 动态库安全发布、装载与回滚
chapter: '20.7'
section: '20.7'
status: finalized
applicable_versions: Android 14 (API 34) - Android 17 (API 37); System.load writable-file enforcement requires Android 17 with targetSdkVersion 37
last_verified: '2026-08-24'
last_verified_against: Android 17 behavior changes and AOSP android-17.0.0_r1 Runtime, VMRuntime and bionic linker; Android 14 safer DCL and current Android DCL security guidance
confidence: high
sources:
- type: official
  path: https://developer.android.com/about/versions/17/behavior-changes-17#safer-native-dcl-c
- type: official
  path: https://developer.android.com/about/versions/14/behavior-changes-14#safer-dynamic-code-loading
- type: official
  path: https://developer.android.com/privacy-and-security/risks/dynamic-code-loading
- type: official
  path: https://developer.android.com/ndk/guides/jni-tips#native-libraries
- type: official
  path: https://developer.android.com/guide/practices/page-sizes
- type: aosp
  path: https://source.android.com/docs/core/permissions/namespaces_libraries
- type: aosp
  path: https://android.googlesource.com/platform/libcore/+/android-17.0.0_r1/ojluni/src/main/java/java/lang/Runtime.java
- type: aosp
  path: https://android.googlesource.com/platform/libcore/+/android-17.0.0_r1/libart/src/main/java/dalvik/system/VMRuntime.java
- type: aosp
  path: https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/linker/linker.cpp
tags:
- stability
- native
- dynamic-code-loading
- secure-loading
- elf
- system-load
- rollback
- android17
related_chapters:
- '1.10'
- '1.22'
- '4.5'
- '20.3'
- '20.11'
pipeline_stage: finalized
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part5-app/ch20-stability/07-16kb-native-library-compatibility.md
- src/part5-app/ch20-stability/13-android17-native-dcl-stability.md
---

# Native 动态库安全发布、装载与回滚

Native 动态库能够被 linker 装入，不等于它适合直接发布。应用还要证明文件来自可信来源、发布过程没有暴露半成品、加载时已不可写，并且新版本失败后能够回到最近一次确认可用的版本。

动态代码加载（Dynamic Code Loading，DCL）是指应用在运行时加载未随当前 APK（Android 安装包）或 AAB（用于发布的 Android App Bundle）常规安装路径直接提供的可执行代码。本章讨论其中的原生动态库：由 C/C++ 等语言编译为机器码、通常以 `.so` 为扩展名的共享库。

Android 17 把原生 DCL 的只读要求加到了 `System.load(path)` 路径。应用运行在 Android 17（API 37）上且以 API 37 或更高版本为目标时，如果 `System.load()` 发现目标文件仍可写，会在进入 native linker（原生动态链接器）前抛出 `UnsatisfiedLinkError`。target SDK 是应用向系统声明已适配的目标 API 级别。常见受影响场景包括运行时下载 `.so`、从插件包解压 `.so`、把 assets（随安装包携带的原始资源目录）中的库释放到私有目录，以及为兼容旧系统而再次解压并加载库。

这项检查只处理“加载时文件仍可修改”造成的竞态。只读权限不能证明文件来自可信发布方，也不能代替签名、哈希、ABI、ELF、依赖库与回滚检查。排查问题时，应分别收集平台只读检查、发布文件可信度和动态链接失败的证据。

平台实现以 AOSP（Android Open Source Project，Android 开源项目）`android-17.0.0_r1` 为锚点。16 KB 页的 ELF、APK 与运行时兼容检查由 [4.5 16 KB Page Size 与 Android 性能](../../part1-fundamentals/ch04-memory/05-16kb-page-size.md) 统一维护，本文只在独立 `.so` 发布时引用该检查结果。

## Android 17 的 Native DCL 装载边界

### 四条加载路径的检查范围

`System.load()` 接收库文件的绝对路径，`System.loadLibrary()` 接收去掉 `lib` 前缀和 `.so` 后缀的逻辑库名。`ClassLoader` 是 Java/Android 用来查找类和原生库的加载器；`dlopen()` 则是 C/C++ 代码直接请求 bionic 动态链接器打开共享库的函数。同一份 `.so` 经过这些入口时，Android 17 AOSP 走过的 Java 代码不同：

| 入口 | Android 17 AOSP 调用路径 | 是否执行 `Runtime.load0()` 的可写检查 | 使用建议 |
|---|---|---:|---|
| `System.load("/abs/libx.so")` | `System.load() -> Runtime.load0() -> nativeLoad()` | 是 | 自行管理原生 DCL 时需要适配的入口 |
| `System.loadLibrary("x")` | `Runtime.loadLibrary0() -> ClassLoader.findLibrary() -> nativeLoad()` | 否，当前源码未经过同一段检查 | APK/AAB 随包库的常规入口，优先使用 |
| 自定义 `ClassLoader.findLibrary()` 配合 `loadLibrary()` | `loadLibrary0() -> nativeLoad()` | 否，当前源码未经过同一段检查 | 不可用来规避安全要求；仍要验证来源和链接结果 |
| 原生代码直接调用 `dlopen()` | bionic 动态链接器 | 否，不进入 Java `Runtime.load0()` | 只说明调用边界，不构成兼容方案 |

表中的差异来自 `android-17.0.0_r1` 源码调用关系：`Runtime.load0()` 检查文件后调用 `nativeLoad()`；`loadLibrary0()` 让 `ClassLoader` 找到文件，再直接调用 `nativeLoad()`。C/C++ 中的 `dlopen()` 直接进入 bionic 动态链接器，不会回到 Java 的 `Runtime.load0()`。这是当前版本的实现边界，不能据此假设未来版本仍然相同。

改用 `dlopen()` 只会绕开这段 Java 检查，不会让下载的代码变得可信。原生库仍受链接器命名空间、ELF 格式、`DT_NEEDED` 依赖项、符号解析、进程位数和 16 KB 页面大小等条件限制；远程 DCL 还可能违反 Google Play 政策。迁移时应优先减少 DCL，随应用发布的库继续使用 `System.loadLibrary()`。确需保留 DCL 时，无论入口是否触发当前 Java 检查，都应执行同一套只读发布与来源验证。

### `Runtime.load0()` 的检查顺序

在 `android-17.0.0_r1` 的 `libcore/ojluni/src/main/java/java/lang/Runtime.java` 中，`load0()` 按以下顺序执行：

1. 要求传入绝对路径，否则抛出“`Expecting an absolute path of the library`”。
2. 读取进程 UID（Linux 用来标识进程所属用户的数字）。普通应用 UID 才进入这条检查；源码排除了 root 超级用户（0）、Android 系统身份 system（1000）和 `adb shell` 使用的 shell 身份（2000）。
3. 如果文件所在的文件系统可写，并且 `File.canWrite()` 对当前进程返回 `true`，记录一次不安全 DCL 事件。
4. Android 17 的功能开关已启用、系统 API 不低于 37，且兼容性变更对该应用生效时，抛出“`Attempt to load writable file: ...`”。`VMRuntime.java` 把该变更标为从 target SDK 37 启用。
5. 检查通过后才调用 `nativeLoad(filename, classLoader, caller)`。

`File.canWrite()` 给出当前进程对该路径的可写判断；mode bit 是 `stat` 返回的 Unix 所有者、组和其他用户权限位。两者含义不同，不能只看到代表“仅所有者可读”的 `0400` 就断定平台检查一定通过。线上诊断可同时记录 mode bit 与 `canWrite()`，调用 `System.load()` 前则应确认后者为 `false`。

文件权限和目录权限也要分开看。inode 是文件系统保存文件内容位置与权限等元数据的对象；目录项负责把文件名指向 inode。文件改成 `0400` 后，拥有可写父目录的进程仍可能执行 `unlink`（删除目录项）或 `rename`（更换目录项名称或目标）。因此，只读文件可以阻止普通的原地改写，却不能单独保证某个路径始终指向同一组字节。版本化路径、禁止覆盖、签名校验和版本选择记录需要配合使用。

## 可信发布与回滚协议

### 只读检查不等于来源可信

Android 官方建议尽量避免动态代码加载，并把代码放在可信位置。业务确需下载原生模块时，至少需要下面四类校验：

- **来源**：发布系统用私钥为清单生成数字签名，应用用内置公钥或受控公钥链验证签名。这样可以确认清单来自获授权的发布者。若 SHA-256 与文件由同一个未认证响应一起下发，它只能帮助发现传输损坏，攻击者仍可同时替换二者。
- **内容**：经签名的清单应覆盖模块名、版本、ABI、长度、SHA-256、ELF Build ID、最低应用版本、最低/最高 API，以及允许回滚到哪些版本。SHA-256 是文件内容摘要；ABI（应用二进制接口）描述 CPU 架构、位数和调用约定；ELF 是 Android 原生库采用的可执行与可链接文件格式；Build ID 是链接器写入的构建标识。
- **位置**：文件只进入应用私有目录。不要从共享外部存储加载，也不要信任其他进程可写的路径。
- **生命周期**：每个版本使用独立路径，发布后不覆盖；版本选择记录只指向已验证文件，失败版本持久化标记为 `BAD`。

Android 官方安全指南指出，许多 DCL 形式，尤其是从远端获取代码，可能违反 Google Play 政策并导致应用被暂停。是否合规需要按实际下载内容和分发方式单独审查，不能从“系统允许加载”推出“商店允许发布”。

### 用发布状态机隔离未完成文件

状态机是把发布过程表示为有限状态及其允许转换的模型。这里可把下载、验证、发布和启用分为：

`STAGED -> VERIFIED -> PUBLISHED -> SELECTED -> LOADED`

签名、哈希、ELF 或加载任一环节失败时，都把该版本标记为 `BAD`。回滚只更新版本选择记录，不改写已发布文件。各状态含义如下：

- `STAGED`：临时文件已经创建，加载线程还不能选择它。
- `VERIFIED`：签名清单、内容摘要、长度、ABI 和 ELF 元数据均已通过验证。
- `PUBLISHED`：临时文件已在同一文件系统内通过原子 `rename` 切换到唯一版本路径。这里的“原子”指其他进程只能看到切换前或切换后的目录项，不会看到中间状态。
- `SELECTED`：小型选择清单已通过 `AtomicFile` 或等价文件事务更新。`AtomicFile` 是 Android 用于整份小文件安全替换的辅助类，可在写入中断时保留旧版本。
- `LOADED`：当前进程已经加载该版本；之后修改选择清单只影响尚未加载它的进程。

Android 没有面向应用的通用、可靠的原生库卸载和同进程热切换协议。库被某个 `ClassLoader` 加载后，JNI（Java Native Interface，Java/Kotlin 调用 C/C++ 的接口）注册、静态对象、线程、TLS（线程局部存储）和函数指针都可能仍被引用。较稳妥的启用时机是下次进程启动；需要即时切换时，可把插件放入能够单独重启的隔离进程。

#### 发布顺序

发布进程应持有跨进程锁，也就是让同一应用的多个进程互斥执行发布操作，并确保临时文件与目标文件位于同一私有文件系统。建议按以下顺序执行：

1. 使用唯一临时文件名和 `O_CREAT | O_EXCL | O_CLOEXEC` 创建文件。三个标志分别表示“文件不存在时创建”“文件已存在则失败”和“执行其他程序时自动关闭该描述符”，可避免复用旧临时文件；创建路径时还要拒绝跟随已有符号链接，也就是不能让一个特殊文件把当前路径转向另一个路径。
2. 保持写入用的文件描述符（file descriptor，fd）处于打开状态，立即调用 `fchmod`，把该文件设为仅所有者可读。
3. 通过已经打开的 fd 流式写入并计算摘要，完成后调用 `fsync`，请求系统把该文件的缓存数据提交给存储设备。
4. 验证已签名清单、长度、摘要、ABI、ELF 的位数与机器类型、Build ID 和依赖声明。
5. 在发布锁内确认目标不存在，再用 `rename` 切换到唯一版本路径。若要求设备掉电后仍可恢复，随后还要同步父目录。
6. 原子更新选择清单。加载者只读取 `PUBLISHED` 且已被选择的版本。
7. 再次检查 `canWrite() == false`，然后调用 `System.load()`。

“先设为只读，再通过已打开的 fd 写入”利用了 Linux 的文件访问规则：`fchmod` 会影响后续打开文件时的权限检查，却不会撤销已经成功取得的写入权限。Android 14 的 DCL 文档也采用先设只读、后写内容的顺序，以缩短其他线程打开可写文件的时间窗口。

下面的 Kotlin 代码只演示文件发布的主要顺序；跨进程锁、目录 `fsync`、ELF 解析和选择清单由外层组件负责：

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

这段代码没有把整个库读入内存，摘要覆盖的就是写入 fd 的同一串字节。`verifyElf()` 即使需要重新打开文件，仅所有者可读的权限也允许当前应用读取。

示例依赖外层跨进程锁来保证只有一个合作发布者。`require(!finalFile.exists())` 与之后的 `Os.rename()` 是两次操作，不能原子地表达“目标存在时绝不覆盖”；POSIX（类 Unix 系统接口规范）的 `rename` 还可能替换已有目标。若威胁模型包含不遵守该锁的同 UID 写入者，生产实现要使用支持原子“不覆盖”语义的系统接口或等价协议。`rename` 成功后，还应按持久性要求同步父目录，并在发布状态写入成功后才允许加载。

#### `File.renameTo()` 不是完整的发布事务

`File.renameTo()` 只返回布尔值，无法直接说明失败原因，也不能表达“目标存在时失败”之类的附加规则。`Os.rename()` 失败时会提供 `ErrnoException`，可据此区分路径、权限和文件系统错误，但它本身也没有“不覆盖”保证。无论使用哪一层 API，源与目标都应位于同一文件系统；需要禁止覆盖时，还要引入具备原子“不覆盖”语义的操作。

原子 `rename` 只保证运行中的观察者不会看到半次目录项切换；它不自动保证掉电后的目录更新已经持久化，也不包含选择清单更新。恢复逻辑应分别处理“文件未发布”“文件已发布但尚未选择”“选择记录已提交”这几种状态。启动扫描只接受签名完整且状态为 `PUBLISHED` 的版本，未被引用的临时文件可以延迟清理。

### ABI、ELF 与动态链接条件

只读检查通过后，`nativeLoad()` 才进入 ART（Android Runtime，Android 应用运行时）和 bionic 动态链接器的加载路径。以下问题仍会表现为 `UnsatisfiedLinkError`。

#### 不要直接取 `Build.SUPPORTED_ABIS[0]`

应用进程可能以 32 位或 64 位运行，设备支持列表中的第一项不一定对应当前进程。选择模块时应同时检查：

- `Process.is64Bit()` 与 ELF `EI_CLASS` 是否一致；`EI_CLASS` 表示该文件采用 32 位还是 64 位格式。
- ELF `e_machine` 与清单声明的 ABI 是否一致；`e_machine` 表示目标指令集架构，例如用于 64 位 Arm 的 AArch64。
- 所选 ABI 是否可供当前进程使用，不能只依据设备理论上支持的全部 ABI。
- 清单中的版本和 Build ID 是否与文件内记录一致。

多个 ABI 复用同一个版本目录，可能让错误文件覆盖正确文件，最终只留下动态链接错误。目录至少应包含固定格式的模块名、ABI 和不可变版本号，例如 `files/native/arm64-v8a/feature/42/libfeature.so`。

#### 检查 `DT_NEEDED` 与链接器命名空间

`DT_NEEDED` 是 ELF 动态段中声明直接依赖库名的条目。链接器命名空间（linker namespace）则规定一组库能够看见和加载哪些其他库。每个依赖都必须能在调用方 `ClassLoader` 对应的命名空间中解析。应用不能依赖未向应用公开的私有平台库；按猜测顺序手工逐个调用 `dlopen()` 也容易在系统升级后失败。发布前可用工具链中的 `readelf -d` 读取 ELF 动态段并列出 `DT_NEEDED`，再与 APK 随包库及系统允许应用访问的公共库核对。

在 Android 17 这份源码中，`System.load()` 与 `System.loadLibrary()` 最终都会把调用类及其 `ClassLoader` 传给 `nativeLoad()`。前者直接使用绝对路径，并额外经过 `load0()` 的只读检查；后者先由 `ClassLoader.findLibrary()` 把逻辑库名解析为文件。排查命名空间问题时，应记录实际调用类、`ClassLoader` 和解析后的路径，不能仅凭 API 名称判断依赖环境。

#### 16 KB 页面大小要检查 ELF 程序头

ELF 程序头描述运行时如何把文件映射进内存；其中 `PT_LOAD` 条目代表需要加载的段，`p_align` 表示该段要求的对齐方式。运行时释放出的独立 `.so` 应按 4.5 节的规则检查这些字段。APK ZIP 对齐只影响从 APK 直接 `mmap` 未压缩库的路径；`mmap` 是把文件内容映射到进程虚拟内存的系统调用。文件解压到私有目录后，ZIP 中的偏移对齐不再是这个独立文件的加载条件。ELF 段对齐与 APK ZIP 对齐应分别检查。

### 多进程与回滚

多进程应用可能遇到这种时序：主进程正在发布版本 B，远程服务仍按旧清单加载版本 A，清理线程随后删除了 A。可采用以下约束：

- 只有一个发布者能够持有跨进程锁；在锁内完成版本文件发布和选择清单更新。
- 读取者只加载状态为 `PUBLISHED` 的不可变路径，不打开临时文件。
- 已加载版本在对应进程退出前都视为仍被引用。缺少可靠的跨进程引用计数时，至少保留 `active`（当前选择）与 `last-known-good`（最近一次确认可用）两个版本，并延迟清理更早版本。
- 版本 B 失败后写入 `BAD` 记录，把版本选择切回 A；同一进程不要无限重试 B。

文件锁只表示当前有没有进程占用它，不能说明前一次发布是否完成。进程被终止后，内核会释放锁，但磁盘上可能留下临时文件，或处于“文件已发布、选择记录未更新”的中间状态。恢复时应读取签名清单和持久状态，不能根据“现在能取得锁”推测上一次操作成功。

## 故障分类、诊断与发布验证

### 失败分类与处理

`UnsatisfiedLinkError` 可由多个加载阶段抛出。应结合异常消息和本地检查结果分类，不能把同一异常类型都归因于 Android 17 的只读规则：

| 类别 | 典型证据 | 处理 |
|---|---|---|
| Android 17 可写拒绝 | 消息包含 `Attempt to load writable file`，`canWrite() == true` | 标记发布流程故障，禁止重试同一路径 |
| 非绝对路径 | 消息包含 `Expecting an absolute path` | 修正 `System.load()` 调用参数 |
| ABI / ELF 不匹配 | `wrong ELF class`、`bad ELF magic` 或机器类型不符 | 禁用该文件，选择匹配当前进程 ABI 的版本 |
| 16 KB 不兼容 | ELF `PT_LOAD` 段对齐检查失败或链接器报告对齐错误 | 按 4.5 节的工具链与产物基线重新构建 |
| 依赖 / 命名空间 | `library ... not found`、依赖不可访问 | 修正 `DT_NEEDED` 或随包依赖 |
| 符号错误 | `cannot locate symbol` | 回滚库与调用方版本组合 |
| 签名 / 摘要失败 | 本地验证未通过，尚未调用加载 API | 删除临时文件并上报告警 |
| 并发 / 残缺文件 | 长度、状态、Build ID 不一致 | 修复发布事务，禁止加载 |

可选功能可以在加载处捕获 `UnsatisfiedLinkError`，记录失败并关闭该功能入口；捕获后不能继续调用对应 JNI 方法。启动必需库应优先使用随 APK/AAB 发布的版本。若存在已签名、兼容且最近一次确认可用的动态版本，可以在新进程中回退；不要在已经执行过新版 JNI 代码的进程中强行换库。

### 诊断记录

每次加载至少记录以下字段，便于区分发布、权限和动态链接问题：

- 应用版本、`targetSdkVersion`、系统 API、进程名、进程位数；
- 固定格式的模块名、版本、ABI、发布状态、选择清单版本；
- 文件长度、mode bit、`canWrite()`、摘要比对结果、签名密钥 ID、ELF Build ID；密钥 ID 只标识用于验签的公钥，不记录私钥材料；
- 加载入口：`System.load`、`System.loadLibrary` 或原生 `dlopen`；
- `DT_NEEDED` 检查结果、16 KB 对齐结果；
- `UnsatisfiedLinkError` 的原始消息和分类结果；
- 回退版本、`BAD` 标记和重试次数。

文件绝对路径可能包含用户或业务标识。上报时保留受控目录类型和经过清理的相对路径即可，不要把原始外部路径直接发送到服务端。摘要和 Build ID 可用于确认文件版本，库内容不应进入日志。

### Android 17 分阶段测试表

升级 `targetSdkVersion` 前，至少覆盖以下用例：

| 用例 | 预期 |
|---|---|
| target SDK 36，`System.load()` 加载可写测试库 | 观察兼容性变更是否启用；即使仍能加载，也继续按只读规则发布 |
| target SDK 37，`System.load()` 加载可写测试库 | 抛出带 `Attempt to load writable file` 的 `UnsatisfiedLinkError` |
| target SDK 37，加载按规定发布的只读库 | 通过只读检查并进入动态链接阶段 |
| `System.loadLibrary()` 加载随 APK/AAB 发布的库 | 常规路径正常 |
| 原生 `dlopen()` 加载测试文件 | 验证它不经过 Java `load0()`；文件仍按可信、只读规则发布 |
| 清单签名、SHA-256、长度任一错误 | 在调用加载 API 前拒绝 |
| ABI 错误、ELF 位数错误、缺少 `DT_NEEDED`、符号未解析 | 分类为动态链接或发布文件问题，不误报为权限问题 |
| 4 KB 对齐库运行在 16 KB 环境 | 被本节的构建检查或运行测试发现 |
| 两个进程同时发布和加载 | 读取者只见完整 `PUBLISHED` 版本 |
| `rename` 后、选择记录更新前终止进程 | 重启后继续使用旧选择，或根据已验证状态完成恢复 |
| 新版本加载失败 | 写入 `BAD`，新进程回退到最近一次确认可用的版本，不循环重试 |
| 可选模块加载失败 | 功能关闭且 JNI 不再被调用，主流程继续运行 |

测试中可以保留一条原生 `dlopen()` 用例，用来持续确认 AOSP 的调用边界，并验证诊断系统不会误判为 `Runtime.load0()` 拒绝。该用例不应成为线上绕开只读发布要求的依据。

### 与相邻章节的边界

- 1.22 讨论链接器命名空间、依赖解析与加载性能，本章只引用其中的加载条件。
- 20.3 讨论 signal crash（由 POSIX 信号终止的原生崩溃）、tombstone（Android 生成的原生崩溃报告）、backtrace（调用栈）和符号化。只读拒绝通常表现为 Java `UnsatisfiedLinkError`，此时还没有执行目标库中的原生代码。
- 4.5 讨论 16 KB 页下的 ELF、APK 和运行时代码兼容，本文只使用独立 `.so` 的 ELF 检查结果。
- 1.10 讨论 JNI 注册与调用边界。库加载失败后仍调用对应原生方法，才会引出后续 JNI 故障。


## 参考资料

- [Android 17 behavior changes - Safer Native DCL-C](https://developer.android.com/about/versions/17/behavior-changes-17#safer-native-dcl-c)
- [AOSP `android-17.0.0_r1`：`java.lang.Runtime`](https://android.googlesource.com/platform/libcore/+/android-17.0.0_r1/ojluni/src/main/java/java/lang/Runtime.java)
- [AOSP `android-17.0.0_r1`：`dalvik.system.VMRuntime`](https://android.googlesource.com/platform/libcore/+/android-17.0.0_r1/libart/src/main/java/dalvik/system/VMRuntime.java)
- [AOSP `android-17.0.0_r1`：bionic linker](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/linker/linker.cpp)
- [Android 14 behavior changes - Safer dynamic code loading](https://developer.android.com/about/versions/14/behavior-changes-14#safer-dynamic-code-loading)
- [Dynamic Code Loading security risks](https://developer.android.com/privacy-and-security/risks/dynamic-code-loading)
- [Android NDK JNI tips - Native libraries](https://developer.android.com/ndk/guides/jni-tips#native-libraries)
- [AOSP：Namespaces for native libraries](https://source.android.com/docs/core/permissions/namespaces_libraries)
