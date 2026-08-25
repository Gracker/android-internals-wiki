---
title: Dynamic Linker、VNDK 与 Native 库隔离
chapter: '1.7'
section: '1.7'
status: finalized
applicable_versions: Android 12 (API 31) - Android 17 (API 37)
tags:
- vndk
- linker
- native-library
- dlopen
- namespace
- performance
- self-contained-hal
- linker64
- dynamic-linker
- ELF
- RELRO
- bionic
related_chapters:
- '1.1'
- '1.6'
- '4.5'
- '8.2'
last_verified: '2026-08-19'
last_verified_against: AOSP android-17.0.0_r1
confidence: high
last_body_apply_at: '2026-08-06T13:15:32+08:00'
last_body_apply_run_id: 20260806-131532-f1fcd970
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
pipeline_stage: ready-to-publish
last_review_finalize_at: '2026-08-06T14:07:19+08:00'
last_review_finalize_run_id: 20260806-140539-50b252ca
sources:
- type: aosp
  path: bionic/linker
- type: aosp
  path: system/linkerconfig
- type: official
  path: https://source.android.com/docs/core/architecture/vndk
- type: official
  path: https://source.android.com/docs/core/architecture/vndk/linker-namespace
- type: aosp
  path: bionic/linker/linker.cpp
- type: aosp
  path: bionic/linker/linker_relocate.cpp
- type: aosp
  path: bionic/linker/linker_phdr.cpp
- type: aosp
  path: bionic/linker/linker_phdr_16kib_compat.cpp
- type: aosp
  path: bionic/linker/linker_soinfo.cpp
- type: aosp
  path: bionic/linker/linker_namespaces.h
- type: aosp
  path: bionic/linker/dlfcn.cpp
- type: aosp
  path: art/runtime/jni/java_vm_ext.cc
- type: kernel
  path: common/mm/mmap.c, common/mm/memory.c, common/mm/filemap.c @ android17-6.18-2026-06_r6
- type: official
  path: https://developer.android.com/guide/practices/page-sizes
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part2-performance/ch08-responsiveness/11-native-library-loading-dynamic-linker.md
- src/part1-fundamentals/ch01-architecture/40-vndk-isolation-native-library-performance.md
- src/part1-fundamentals/ch01-architecture/50-dynamic-linker-native-library.md
---

# Dynamic Linker、VNDK 与 Native 库隔离

Android 进程执行原生代码之前，要把 ELF（Executable and Linkable Format，可执行与可链接格式）文件映射进地址空间，找到依赖库，解析动态符号，写入重定位结果，再调整页面权限并运行初始化函数。64 位进程中的这些工作由 bionic 自带的 dynamic linker（动态链接器）完成，常见解释器路径是 `/system/bin/linker64`，下文简称 linker64。

平台源码以 Android 17 / API 37 / `android-17.0.0_r1` 为准；涉及 `mmap()`、文件缺页和写时复制（Copy-on-Write，COW）的内核行为以 `android17-6.18-2026-06_r6` 为准。VNDK（Vendor Native Development Kit，厂商原生开发套件）的可见性规则在本文后半部分展开；以下先聚焦 linker64 的执行顺序及各阶段对启动时间、内存和故障定位的影响。

后文保留 linker 源码中的常用名称：DSO（Dynamic Shared Object）指 `.so` 动态共享对象；SONAME 是 ELF 内用于依赖匹配的逻辑库名；linker namespace（链接器命名空间）负责约束库的搜索路径和可见范围。RELRO 是“重定位完成后只读”的内存区域，TLS 是每个线程独立保存的数据区，PLT/GOT 是动态函数调用和地址重定位所用的表，ABI 则是二进制接口约定。

Native 库加载先由 linker64 解析依赖、命名空间和重定位，再受分区隔离与稳定 ABI 规则约束。启动慢、找不到库和符号不匹配需要沿同一装载路径定位。

## linker64 装载、重定位与命名空间

### linker64 的职责边界

linker64 有两条主要入口：

- 进程启动：内核根据主程序的 `PT_INTERP`（指定 ELF 解释器的段）装入 linker64。linker64 完成自身重定位，再装入主程序、`LD_PRELOAD` 指定的优先库和 `DT_NEEDED` 声明的依赖库；这些工作完成后，控制权交给程序入口。
- 运行时装载：`dlopen()` 或 `android_dlopen_ext()` 进入 `do_dlopen()`，加载可访问范围内尚未存在的 DSO；`dlsym()` 查询符号；`dlclose()` 递减装载组引用计数并在满足条件时卸载。

linker64 不是常驻系统服务，也没有跨进程共享的“已解析符号缓存”。每个进程维护自己的 `soinfo` 依赖图、namespace、符号查找范围和引用计数。文件页可以经内核页缓存（page cache）在进程间复用，地址空间和重定位结果仍属于各进程。

`bionic/linker/Android.bp` 将 linker 配置为 `static_executable: true`。这里的“静态”表示它不能依赖另一个动态链接器替自己完成普通启动；源码注释进一步说明，linker 自身按共享对象布局链接，并由静态库构成。“它是普通静态程序”的说法遗漏了自举重定位，也就是 linker 先修正自身地址、再去装载其他 ELF 的过程。

### 一次 `dlopen()` 的执行顺序

#### 所有公开装载操作先经过同一把递归互斥锁

`bionic/linker/dlfcn.cpp` 中的 `dlopen`、`dlsym`、`dlclose`、`dl_iterate_phdr` 等入口都会持有 `g_dl_mutex`。它是 `PTHREAD_RECURSIVE_MUTEX_INITIALIZER_NP`，因此构造函数递归调用 `dlopen()` 时不会因重复加锁立刻死锁。

递归锁不等于并行装载。Android 17 的 `find_libraries()` 使用顺序循环扩展依赖、映射文件、预链接和重定位。另一个线程同时进入 linker API 时要等待这把锁。由于 `do_dlopen()` 在返回前还会调用 ELF 构造函数，耗时构造函数也会延长其他线程的 loader-lock wait，也就是等待链接器全局锁的时间。

两个执行特征：

- 同一依赖层的兄弟 DSO 不会由 linker64 自动并行加载。
- 把依赖图改得更“扁平”不会换来 linker 内部并行，只可能改变查找范围、构造顺序和待加载节点。

#### 阶段一：确定调用者和 namespace

`do_dlopen()` 先用调用地址查找所属 `soinfo`，再由 `get_caller_namespace()` 得到起始 namespace。若调用的是 `android_dlopen_ext()`，并且 `android_dlextinfo` 带有 `ANDROID_DLEXT_USE_NAMESPACE`，显式 namespace 可以覆盖这一步的结果。

因此，同一个绝对路径或 SONAME 在 shell 测试程序里能加载、在应用进程里却可能失败：两者的搜索起点和可见边界并不相同。

#### 阶段二：按广度优先顺序扩展 `DT_NEEDED`

`find_libraries()` 先创建 `LoadTask`，随后遍历不断增长的任务列表。每个新 ELF 的 `DT_NEEDED` 会追加成后续任务，因此依赖发现顺序是广度优先。此时会：

- 复用 namespace 中已经加载且可访问的 `soinfo`；
- 为新库打开文件、读取 ELF 头、Program Header 和动态段所需信息；
- 建立父子边，记录依赖来自哪个 namespace；
- 跨 namespace 时沿允许的链接关系寻找指定 SONAME。

这里不是简单的 `find_library() → load_library() → load_dependencies()` 递归链。`LoadTask` 把“发现依赖”和“映射所有新库”分成不同阶段，便于失败时回收本次装载创建的对象。

#### 阶段三：映射新库的 `PT_LOAD`

linker64 从新任务中生成待映射列表。普通路径会打乱映射顺序；使用 `ANDROID_DLEXT_RESERVED_ADDRESS_RECURSIVE` 时，为满足保留地址区布局，顺序保持稳定。这项随机排列属于地址布局策略，不是并发调度。

`ElfReader::Load()` 负责保留地址空间、映射 `PT_LOAD` 可装载段、定位运行时 Program Header（程序头表），并解析 GNU property（编译器写入 ELF 的架构特性说明）。`android_dlopen_ext()` 还能通过文件描述符（fd）、fd 内偏移、保留地址区或 RELRO fd 提供特殊装载条件，WebView loader 是 RELRO 共享能力的重要使用者。

`mmap()` 成功只表示建立了映射。尚未访问的文件页可以继续留在磁盘或 page cache 中；“`dlopen()` 完成”不代表库的全部代码页已经产生缺页并进入物理内存。

#### 阶段四：预链接并登记 TLS

所有新映射完成后，linker64 按广度优先顺序调用 `prelink_image()`。这里的“预链接”是解析动态段并准备后续链接，不会预先固定进程中的装载地址。这一阶段解析 `.dynamic`，记录：

- 字符串表、动态符号表和 GNU/SysV hash；
- `DT_NEEDED`、`DT_RUNPATH` 和符号版本信息；
- REL、RELA、RELR、APS2 packed relocation 的位置；
- `DT_INIT`、`DT_INIT_ARRAY`、`DT_FINI_ARRAY`、`DT_FINI`；
- TLS、AArch64 MTE（Memory Tagging Extension，内存标记扩展）和其他处理器相关动态项。

随后注册该 DSO 的静态 TLS 模块。若任一新库通过 `DT_AARCH64_MEMTAG_STACK` 请求 stack MTE，linker 会通知 libc 的对应回调。

#### 阶段五：构造 global group 与 local group

符号查找不会在进程内所有 DSO 中随意扫描。linker64 为每个待链接根节点组织：

- 全局组（global group）：预加载库以及带全局可见语义的库；
- 局部组（local group）：从当前根节点沿可访问依赖边得到的局部装载组。

`SymbolLookupList` 按这两个集合组织查找顺序。依赖边穿越 namespace 边界时，会产生单独的 local-group root，随后在所属 namespace 中完成链接。

#### 阶段六：重定位、页面保护与调试登记

`soinfo::link_image()` 对 local group（当前根节点及其可访问依赖组成的局部装载组）中尚未链接的库逐个执行以下工作：

1. 根据 global/local lookup list（全局/局部符号查找列表）解析重定位；
2. 把 `PT_GNU_RELRO` 对应页面改为只读；
3. 完成 16 KB app compatibility 路径需要的权限调整；
4. 处理 MTE globals；
5. 按 `android_dlextinfo` 写出或复用共享 RELRO；
6. 通知调试器，并把该 image 标为 linked。

任一环节失败，本次调用会沿失败保护路径卸载已创建的对象，`dlopen()` 返回 `nullptr`。

#### 阶段七：增加引用计数并运行构造函数

链接成功后，根 `soinfo` 的引用计数增加。`do_dlopen()` 随后同步调用 `soinfo::call_constructors()`，成功后才返回 handle（装载句柄）。

应用侧看到的一次 `System.loadLibrary()` 或 `dlopen()` 耗时，可能包含文件处理、映射、重定位和 ELF 构造函数。Java 调用链还包含 ART 的 `JNI_OnLoad`，不能把总时间都归因于“linker 重定位慢”。

### `soinfo`：运行时的 DSO 记录

`soinfo` 是 linker64 对一个已发现 DSO 的运行时描述，不是 ELF 文件头的简单副本。Android 17 的对象中可找到这些信息：

- `base`、`size`、`load_bias`、Program Header；
- `.dynamic`、字符串表、符号表与 hash 表；
- 普通、PLT、RELR 和 Android packed relocation；
- 构造/析构函数数组；
- 父子依赖边、primary/secondary namespace；
- local-group root、引用计数与 `RTLD_*` 标记；
- TLS、MTE、GNU property 和 CFI（Control-Flow Integrity，控制流完整性）相关状态；
- realpath、SONAME、版本和 link 状态。

同一文件是否复用现有 `soinfo`，受到 realpath、SONAME、namespace 可见性和装载参数影响，不能只看文件名。不同隔离空间也可能持有各自的装载关系。

Android 17 源码没有“把频繁访问与很少访问的字段按 CPU cache line（缓存行）分开”的明确设计证据。分析性能时应观察对象数量、依赖边、符号查找和页面行为，不应仅凭字段排列推导未经测量的缓存收益。

### Linker Namespace：控制“从哪里找”和“允许看见谁”

`android_namespace_t` 主要维护：

- `ld_library_paths_`：运行时设置的搜索路径；
- `default_library_paths_`：配置给 namespace 的常规搜索路径；
- `permitted_paths_`：isolated namespace 可访问的额外目录；
- `allowed_libs_`：允许装入的库名集合；
- `linked_namespaces_`：可跨边界查询的目标及 SONAME 白名单；
- `soinfo_list_`：当前 namespace 可见的 DSO。

对于 isolated namespace（启用路径隔离检查的命名空间），路径可访问性和库名都要满足配置。当前空间找不到库时，linker 只会查询已建立链接且允许该 SONAME 的目标 namespace；它不会在失败后无条件扫描 `system`、`vendor`、`product` 的全部目录。

#### namespace 名称和配置由设备决定

`system`、`vendor`、`product` 等名称在设备配置中很常见，但它们不是 linker64 源码里不可改变的层级枚举。实际 namespace 由 linker config 生成，进程类型、APEX（可独立更新和挂载的系统模块）及厂商配置都能改变名称、路径与链接关系。

Android 17 的配置选择仍保留多级来源。源码会依次考虑与 APEX 可执行文件对应的配置、架构相关的 `/system/etc/ld.config.<ABI>.txt`、生成的 `/linkerconfig/ld.config.txt`、VNDK 路径和静态备用配置。因此，不能把 Android 17 的行为概括成“只认 `/linkerconfig/ld.config.txt`，旧配置已经删除”。

应用的 ClassLoader namespace 还涉及 `libnativeloader` 与 ART。排查 `System.loadLibrary()` 时，应把 Java ClassLoader、NativeLoader 创建的 namespace 和 bionic 的路径检查连起来看，不能只查看 `/system/lib64` 是否存在目标文件。

### Android 使用 eager binding（立即绑定）

传统 ELF 文档经常把 `RTLD_LAZY` 描述为“第一次经过 PLT（过程链接表）调用函数时再解析目标地址”，也就是 lazy binding（延迟绑定）。这不适用于 Android 17 的 bionic linker：

- `dlopen()` 接受 `RTLD_LAZY`，但 `linker.cpp` 明确注明该模式不受支持；
- 普通 REL/RELA 之后，PLT REL/RELA 也在 `relocate()` 中立即处理；
- 用于 lazy TLSDESC 的动态项被忽略，源码注释是“Bionic resolves everything eagerly”；
- `DT_BIND_NOW` 被忽略，因为相关语义已由 `DF_BIND_NOW` 表达，而 bionic 本身仍执行 eager relocation。

Android 上没有“默认 lazy、加 Full RELRO（让可保护的重定位区域全部只读）后才改为 eager”的性能二选一，也没有 `_dl_runtime_resolve` 在首次 JNI 调用时逐项补 PLT 的常规路径。

#### Android 17 支持的重定位编码

编码格式与 CPU 重定位类型是两个维度。以 64 位进程为例：

| 编码或表 | 作用 | 运行时特征 |
| --- | --- | --- |
| `DT_RELR` | 压缩大量 relative relocation | 只需基址与位图展开，不查动态符号 |
| `DT_ANDROID_RELA` + `APS2` | Android packed relocation | 用分组和差值编码缩小重定位表 |
| 普通 `.rela.dyn` | 一般数据、符号与 TLS 重定位 | 某些条目需要在 lookup list 中查符号 |
| `.rela.plt` | PLT/GOT 中的函数入口地址 | 在 `dlopen()` 返回前完成 |

32 位 ABI 可以使用 REL 及 `DT_ANDROID_REL`。在 AArch64 上，linker 的快路径覆盖 `R_AARCH64_RELATIVE`、`R_AARCH64_JUMP_SLOT`、`R_AARCH64_GLOB_DAT`、`R_AARCH64_ABS64` 等常见类型；复杂或带版本的符号进入完整查找路径。

`DT_ANDROID_REL(A)` 表示 APS2 压缩重定位数据，不是预链接地址信息。Android 17 也支持标准 `DT_RELR`。两者的作用都是压缩存储，并让常见的 relative relocation（只需根据装载基址修正的相对重定位）更容易批量处理；运行时仍要按当前进程的随机装载基址写入目标地址。

#### 符号查找为何会变慢

一次需要符号解析的重定位，成本取决于：

- global/local lookup list 中要访问多少 DSO；
- 目标库使用 GNU hash 还是 SysV hash；
- 符号是否带版本约束；
- weak symbol、符号优先查找（symbolic lookup）、跨 namespace 边界等规则；
- 符号与 hash 表所在页面是否已经驻留。

GNU hash 的 Bloom filter（布隆过滤器，一种快速排除“不可能命中”结果的数据结构）可以迅速筛掉不匹配库，但不能保证总成本固定为 O(1)。linker 的慢路径带有单符号查找缓存，但它不是面向整个进程、长期保存任意查询结果的通用缓存。

### GNU RELRO：重定位完成后把页面设为只读

RELRO（Relocation Read-Only）由 ELF Program Header 中的 `PT_GNU_RELRO` 描述。`soinfo::link_image()` 完成重定位后调用 `protect_relro()`，后者对相应页面执行 `mprotect(PROT_READ)`。这可以阻止后续代码随意改写已经填好目标地址的 GOT（全局偏移表）和其他敏感数据。

判断一个库覆盖了多大 RELRO 范围，需要查看链接器生成的 segment，而不是寻找 `GNU_PROPERTY_RELRO`；Android 17 没有这个 property。下面的命令用于同时检查 RELRO segment、绑定标记和实际重定位表：

```bash
llvm-readelf -lW libfoo.so | grep GNU_RELRO
llvm-readelf -dW libfoo.so | grep -E 'BIND_NOW|FLAGS'
llvm-readelf -rW libfoo.so
```

在 bionic eager binding 的前提下，`BIND_NOW` 不会再制造一轮“从 lazy 变 eager”的差异。性能上应观察 RELRO 页面数量、重定位写入量、符号查找和后续 `mprotect()`；安全上则要确认预期区域确已落入 `PT_GNU_RELRO`。

`ANDROID_DLEXT_WRITE_RELRO` 与 `ANDROID_DLEXT_USE_RELRO` 还允许把 GNU RELRO 写入 fd，供另一个地址布局匹配的进程复用。Android 17 源码特别说明，WebView 使用这条路径共享包含大量 C++ vtable（虚函数表）的 RELRO 页。这是专用加载器协议，并非所有 system DSO 自动拥有的“预链接信息”。

### 构造函数：`dlopen()` 同步路径中的库代码

`soinfo::call_constructors()` 先设置 `constructors_called` 防递归，然后：

1. 递归调用子依赖的构造函数；
2. 调用当前 DSO 的 `DT_INIT`；
3. 正序调用 `DT_INIT_ARRAY`。

共享库中的 `DT_PREINIT_ARRAY` 会被忽略并产生警告；preinit 只用于主程序。卸载时顺序相反：逆序执行 `DT_FINI_ARRAY`，再执行 `DT_FINI`。

ELF constructor（构造函数）由 linker 在库装入时自动调用，其 ABI 没有返回值。linker 也没有 `DL_ERR_CONSTRUCTOR_FAILED` 供应用捕获。构造函数若触发 `SIGSEGV`、`SIGABRT` 或未处理异常，进程通常直接终止；它不会把错误转成 `dlerror()`，再让 `dlopen()` 调用者继续执行。

工程上应把构造函数限制为必要、可预测且不阻塞的初始化：

- 不在 constructor 中等待 Binder、文件锁或其他线程；
- 不扫描大目录，不同步读取可延后的配置；
- 避免 constructor 相互 `dlopen()` 形成复杂递归；
- 需要业务上下文的工作放到显式初始化 API，并由调用方选择线程和时机。

Android 17 没有 `android_set_dl postpone_init()` 之类的公开 API，可以让 `dlopen()` 跳过 constructor、稍后再补执行。若要延后工作，只能调整库代码或延后整个装载调用。

### `JNI_OnLoad` 属于 ART 阶段

`System.loadLibrary()` 经过 ClassLoader/NativeLoader 后会进入 native 装载。bionic 完成 `dlopen()` 和 ELF constructor 后，ART 的 `JavaVMExt::LoadNativeLibrary()` 再查找 `JNI_OnLoad` 并同步调用它。`JNI_OnLoad` 是库可选提供的初始化入口，常用于检查虚拟机环境和注册 native 方法。

ART 还维护每个库的 `JNI_OnLoad` 状态：

- 同一库若正在由另一个线程执行 `JNI_OnLoad`，后来的线程等待结果；
- 没有 `JNI_OnLoad` 可以视为加载成功；
- 返回 `JNI_ERR` 或不支持的 JNI 版本会使这次 Java native library load 失败；
- ART 不会贸然 `dlclose()` 一个已经部分注册 native 方法的失败库，而是记录失败，令后续装载也失败。

这和 ELF constructor 的故障模型不同。`JNI_OnLoad` 有返回值，ART 能识别失败；constructor 没有受控失败协议。

#### 静态查找与 `RegisterNatives`

未显式注册的 native 方法在首次解析时，ART 会把 Java 类名和方法名按 JNI 规则编码成 mangled name（重整后的符号名），再到已为对应 ClassLoader 装入的 native 库中查找。找到的入口会安装到方法中，后续调用不会每次都重新扫描所有 DSO。

`RegisterNatives` 直接把 Java 方法与函数地址关联，适合这些情况：

- 不希望导出很长的 `Java_package_Class_method` 名称；
- 需要在一个可审查的表里明确 Java 签名和 native 地址；
- 希望减少首次方法解析时的 `dlsym()` 查询。

它也有成本：注册表要维护，签名错误会在加载阶段暴露，而且放在 `JNI_OnLoad` 中就会占用 `System.loadLibrary()` 的同步路径。动态注册不会自动转到后台，也不是通用的 native 热修复机制。选择注册方式应依据 API 管理和实测查找成本，不应套用“每个静态 JNI 固定耗时若干毫秒”的数字。

### `dlerror()`、故障返回与 `dlclose()`

#### `dlerror()` 是线程局部状态

公开接口用返回值表示失败：

- `dlopen()` 失败返回 `nullptr`；
- `dlsym()` 失败需要结合 `dlerror()` 判断；
- `dlclose()` 失败返回非零值。

bionic 把内部错误文本格式化到当前线程的 dlerror buffer。它没有对应用稳定公开的 `DL_ERR_*` 枚举，也没有供所有线程争用的单一 `g_dl_error` 字符串。诊断代码应保存 `dlerror()` 文本，不要依赖自造错误码或匹配可能变化的整句文案。

namespace 拒绝、ELF 类型或 ABI 错误、缺少符号、重定位失败都会在受控路径返回错误。constructor crash、越界写和信号终止则属于进程故障，不能指望 `dlerror()` 收集。

#### `dlclose()` 处理的是装载组

`dlclose()` 不是对一个文件简单执行 `munmap()`。Android 17 会：

1. 检查 local-group root 的引用计数；
2. 检查 `RTLD_NODELETE`（要求保留装载对象）与 `RTLD_GLOBAL`（让符号进入全局查找范围）等不可卸载条件；
3. 沿依赖图区分本地卸载节点和外部装载组引用；
4. 调用析构函数；
5. 注销 TLS 模块、通知 unload hook（卸载回调）和调试器、更新用于快速检查间接调用目标的 CFI shadow；
6. 释放映射与 `soinfo`，再递归处理外部引用。

源码明确包含 `unregister_soinfo_tls()`，“Android 的 DSO TLS 永远不回收”并不准确。应用仍不应频繁卸载含活动线程、回调或缓存函数指针的库：linker 能维护自己的图，却无法替业务代码找到所有悬空地址。

### 16 KB 页面：同时检查 ELF 和 APK

Android 15 开始支持使用 16 KB 内存页（page size）的设备。Android 17 的 linker64 以运行时 `page_size()` 校验 ELF，而不是读取 `ro.page_size_16k`。在设备上确认页面大小，可执行：

```bash
adb shell getconf PAGE_SIZE
```

当系统页大小至少为 16 KB、ELF 的最小 `PT_LOAD p_align` 小于系统页大小且 compatibility mode（兼容模式）未启用时，`ElfReader::LoadSegments()` 会返回“program alignment cannot be smaller than system page size”。Android 17 同时保留 `linker_phdr_16kib_compat.cpp` 的 4 KB 对齐兼容装载路径，因此不能断言旧库在所有 16 KB 设备上都会立即拒载。

`bionic.linker.16kb.app_compat.enabled` 在 Android 17 源码中有三种取值：

- `true`：对不满足对齐的 ELF 启用 compatibility path；
- `false`：不由该属性启用，包级 app compat mode 仍可能生效；
- `fatal`：不启用兼容；发现对齐不足时设置 abort message（进程终止原因）并触发 `SIGABRT`，方便测试尽早暴露问题。

要在 Android 17 测试设备上对所有应用强制关闭兼容模式，并让不兼容二进制立即终止，需要同时关闭 Package Manager 的包级兼容：

```bash
adb shell setprop bionic.linker.16kb.app_compat.enabled fatal
adb shell setprop pm.16kb.app_compat.disabled true
```

只设置第一项时，包级 app compat mode 仍可能让 `should_use_16kib_app_compat_` 成立。测试完成后应恢复设备原有属性。

兼容路径是迁移工具，不应作为发布质量标准。它要处理按 4 KB segment 落入同一 16 KB 页时的权限冲突，代码明显比原生 16 KB 对齐路径复杂。

对应用而言有两层对齐要求：

- ELF 内部：每个 native DSO 的 `PT_LOAD` 对齐；
- APK 外部：未压缩 `.so` 在 ZIP 中的起始偏移要满足 16 KB 对齐，才能直接通过 `mmap()` 映射。

下面这组命令分别检查 DSO 和最终 APK：

```bash
llvm-objdump -p libfoo.so | grep -A3 LOAD
zipalign -v -c -P 16 4 app-release.apk
```

按 Android 官方文档：

- NDK（Native Development Kit）r28 及以上默认生成 16 KB 对齐的 native 库；
- NDK r27 或更早的兼容构建要同时传入 `-Wl,-z,max-page-size=16384` 和 `-Wl,-z,common-page-size=16384`；
- 使用未压缩 native library 时，AGP（Android Gradle Plugin）8.5.1 及以上可正确处理 16 KB ZIP alignment（ZIP 内文件起始偏移对齐）。

`android:extractNativeLibs="false"` 表示库可以从 APK 直接映射，前提是未压缩且偏移满足对齐。它不会修复 ELF 的 `p_align`，也不能代替对最终 APK 执行 `zipalign` 校验。

### AArch64 MTE 与 BTI：按 ELF 声明执行

这里的 MTE 用内存标签检查特定越界或悬空访问，BTI（Branch Target Identification，分支目标识别）限制间接分支可到达的入口，PAC（Pointer Authentication Code，指针认证码）则用签名校验指针。三者都需要硬件、内核、工具链和 ELF 声明共同配合，名称相近但职责不同。

Android 17 解析的 MTE 动态项包括：

- `DT_AARCH64_MEMTAG_MODE`；
- `DT_AARCH64_MEMTAG_HEAP`；
- `DT_AARCH64_MEMTAG_STACK`；
- `DT_AARCH64_MEMTAG_GLOBALS` 与 `DT_AARCH64_MEMTAG_GLOBALSSZ`。

开启 MTE globals 时，linker 可能把含可写数据的文件映射重映射为带 `PROT_MTE` 的匿名页，然后根据 descriptor stream（描述各对象位置和标签规则的数据流）为全局对象分配内存标签，再恢复应有的只读权限。这会减少相应数据页的文件共享机会。WebView 的共享 RELRO 路径为此使用确定性的 global tagging，即让不同进程按同一规则生成标签，从而继续复用 RELRO 内容。

BTI 走另一条路径：`linker_note_gnu_property.cpp` 解析 `GNU_PROPERTY_AARCH64_FEATURE_1_BTI`，硬件和 ELF 都满足条件时，linker 给可执行 segment 加 `PROT_BTI`。

`DT_AARCH64_PAC_PLT` 在 Android 17 的动态段解析中被列为忽略的处理器专用 tag。这个动态项不能证明 linker64 会给进程内所有代码指针自动做 PAC 签名。PAC 是否生效取决于编译器生成的指令、ABI 和运行硬件，不由 `dlopen()` 统一开启。

APEX 只改变库的来源、配置和激活边界，不会在进程运行期间替换已经映射的 DSO。APEX 新版本生效后，新启动进程会按新挂载与 namespace 配置装载；老进程若仍持有旧映射，必须由模块自身的重启策略处理。

### 可测量的延迟模型

一次 Java 侧 native library load 可分解为：

```text
T(loadLibrary)
  = T(loader-lock wait)
  + T(namespace and file lookup)
  + T(ELF read and mmap)
  + T(relocation and symbol lookup)
  + T(RELRO/MTE/page protection)
  + T(ELF constructors)
  + T(JNI_OnLoad)
```

这个式子用于划分测量区间，不表示各项彼此完全独立。冷缓存，也就是所需文件页尚未进入 page cache 的状态，会同时影响 ELF 元数据、符号表和构造函数访问的数据页；另一个线程的 constructor 又可能表现为当前线程的 loader-lock wait。

下面几项经常比 `.so` 文件总大小更能解释波动：

- 本次调用新增多少个 `DT_NEEDED` 节点，多少依赖已经加载；
- APK 内直接映射、独立文件或 APEX 路径带来的文件访问差异；
- relative relocation、带符号 relocation 和 TLS relocation 的数量；
- lookup list 宽度、导出符号数与版本约束；
- constructor 与 `JNI_OnLoad` 执行了多少同步工作；
- 所需页面位于 page cache、压缩存储还是需要实际 I/O；
- 是否在等待其他线程持有 `g_dl_mutex`。

“每个 DSO 固定 0.5 ms”“依赖每深一层增加 3–8 ms”“冷启动固定慢 5–20 倍”都缺少设备、存储、构建产物和缓存状态，不能作为 Android 17 的通用规律。库数量也没有适合所有应用的 5–8 个上限；合并 DSO 虽能减少文件和 ELF 元数据处理，也可能增大常驻映射、RELRO、更新耦合及符号冲突范围。

#### 把加载点放回应用启动关键路径

`System.loadLibrary()` 从调用开始到返回的实际经过时间（wall time），会同时覆盖 ART / `libnativeloader`、linker、ELF constructor 和 `JNI_OnLoad`。它若由 `ContentProvider`、App Startup initializer、`Application.onCreate()` 或静态初始化块触发，就会直接进入冷启动关键路径。排查时应先扫描应用和三方 SDK 的 `System.loadLibrary()` / `System.load()`，再给可控加载点加稳定的 trace 名称；否则只看到一个 `dlopen` slice（trace 中的一段计时区间），仍无法定位是哪个业务模块触发。

把加载从首帧前挪走不等于优化完成。首次功能入口如果因此多出同步等待，只是把延迟换了位置。更稳妥的策略是按功能依赖确定最晚加载点，在明确的空闲窗口预先装载，并保留取消、超时和失败后的备用路径。`JNI_OnLoad` 只做 VM 校验、native 注册和少量确定状态；文件 I/O（输入输出）、设备枚举、大对象构造和线程创建放进可观测的显式初始化阶段。

并发调用多个 `System.loadLibrary()` 也不是通用加速方案。公开 linker 操作共用 `g_dl_mutex`，DSO 依赖、constructor 与 SDK 全局状态还可能有隐含顺序；只有已经证明互不依赖、且不阻塞首帧的提前装载任务才适合并行实验。

### 分阶段排查

#### 1. 检查静态产物

这些命令分别查看依赖、动态符号、重定位和 Program Header：

```bash
llvm-readelf -dW libfoo.so | grep NEEDED
llvm-readelf --dyn-syms -W libfoo.so
llvm-readelf -rW libfoo.so
llvm-readelf -lW libfoo.so
```

检查重点是非预期 `DT_NEEDED`、导出符号是否过多、重定位表类型和数量、`GNU_RELRO` 范围，以及 `PT_LOAD` 对齐。

#### 2. 用 Perfetto 区分链接与 constructor

Android 17 的 `do_dlopen()` 写入 `dlopen: <name>` 与 `dlopen: <name> - loading and linking` trace，`call_constructors()` 还写入 `calling constructors: <realpath>`。`loading and linking` 在 `find_library()` 返回后结束，外层 `dlopen` slice 则继续覆盖 constructor，因此两者的差值可以帮助定位构造阶段。

锁等待不在这两条 bionic slice 内：`dlfcn.cpp` 的 `dlopen_ext()` 获取 `g_dl_mutex` 后才调用 `do_dlopen()`。测 loader-lock wait 时，需要在调用侧给整个 `System.loadLibrary()` 或 `dlopen()` 加 trace，并结合线程调度、futex（内核提供的用户态互斥量等待机制）状态及同时持锁线程的 bionic slice 一起看。调用侧 slice 开始到 `dlopen:` slice 出现前的区间，才可能包含等锁时间。

若 Java 调用仍比 bionic slice 长，再检查 ART 的 native library load 与 `JNI_OnLoad`。

#### 3. 在可调试进程中打开 linker 日志

`debug.ld.app.<进程主名>` 和 `debug.ld.all` 接受 `dlerror`、`dlopen`、`dlsym`。下面的示例只针对指定应用，设置后要重启进程：

```bash
adb shell setprop debug.ld.app.com.example.app dlopen,dlerror
adb shell am force-stop com.example.app
```

linker 会检查进程是否为 dumpable，也就是系统安全策略是否允许导出其调试信息。普通 `user` build 上的不可调试应用通常拿不到这些日志。测试结束后用空值清理属性，避免持续产生无用日志：

```bash
adb shell setprop debug.ld.app.com.example.app ''
```

对于 shell 启动的测试程序，`LD_DEBUG` 还支持 `calls`、`dynamic`、`lookup`、`props`、`reloc`、`statistics`、`timing` 等选项。应用孵化路径可能过滤环境变量，不应把 shell 环境下的结果直接当成生产应用的行为。

#### 4. 对照运行时映射

`/proc/<pid>/maps` 能确认实际加载路径、权限和地址区间，`smaps` 可进一步观察 file-backed（内容来自文件）、anonymous（匿名映射）、private dirty（进程私有且已写脏）页面与 RSS（该进程当前驻留物理内存的页面总量，共享页也会计入）。看到 `.so` 映射不等于所有页面已驻留；分析内存时要读 `smaps`，不能只把虚拟地址区间长度相加。

### 优化时按证据下手

1. **移除非预期依赖。** 用 `DT_NEEDED` 和构建图确认来源，配合正确的构建目标依赖（target dependency）与 `--as-needed`。不要直接编辑 ELF 动态段。
2. **控制动态导出面。** `-fvisibility=hidden` 和 version script（符号导出控制脚本）能减少 `.dynsym` 中对外可见的符号。`strip` 主要删除调试符号和普通符号表，运行时仍需要的动态符号与重定位不会被随意删掉。
3. **让当前 NDK/LLD 生成合适的压缩重定位。** LLD 是 LLVM 工具链中的链接器；RELR 或 APS2 能减小产物和读取量，但要用目标 API、ABI 和设备验证兼容性。
4. **缩短 constructor 与 `JNI_OnLoad`。** 这是调用方最能控制、也最容易从 trace 直接确认的一段。
5. **避免高频装卸。** 稳定复用 handle 通常比反复 `dlopen()`/`dlclose()` 安全；若必须卸载，应建立线程、回调、TLS 和函数指针的生命周期约束。
6. **合并库前后都测。** 对比装载节点、重定位数、RELRO、文件页和增量发布影响，不设置脱离产物的库数量或体积指标。
7. **把 16 KB 校验放进构建流水线。** 同时检查每个 ABI 的 ELF 与最终 APK/AAB（Android App Bundle）产物，兼容模式只用于发现和迁移旧库。
8. **依据接口管理选择 JNI 注册方式。** 动态注册可收窄导出面并提前绑定；静态查找可减少注册代码。性能判断以具体 trace 和符号表为准。

对三方 SDK 和跨平台引擎，还要记录 APK/AAB 内路径、ABI、build ID（用于唯一识别二进制构建的标识）、`DT_NEEDED`、LOAD alignment（可装载段对齐）、constructor / `JNI_OnLoad` 和首次触发线程。React Native、Flutter、Unity、Unreal、Cocos 的“官方版本支持 16 KB”不能替代最终产物扫描，旧插件仍可能覆盖正确的链接参数。

CI 应检查每个 release APK/AAB，而不是只读 CMake 参数。至少验证所有 ABI 的 ELF LOAD segment、未压缩 `.so` 的 ZIP alignment、AAB page-alignment 配置、`DT_NEEDED` 与动态符号规模，并在 16 KB 设备覆盖启动、动态功能模块、native 插件和低内存场景。即使源码参数正确，最终生成的 split APK（拆分安装包）仍可能被旧版 bundletool（从 AAB 生成安装包的工具）或三方产物破坏，因而必须以发布包的检查结果为准。

### 版本演进边界

- Android 10 已广泛使用 namespace 与 APEX 路径兼容逻辑，旧应用行为还受到 target SDK 兼容分支影响。
- Android 11 起，LinkerConfig 生成的 `/linkerconfig/ld.config.txt` 成为常见配置来源，但 Android 17 源码仍保留其他配置选择与兜底。
- Android 12 至 Android 14 期间，工具链、RELR、MTE 和 BTI 支持持续演进。分析旧设备时要用对应分支，不能把 Android 17 的 tag 与兼容路径倒推到所有版本。
- Android 15 开始面向 16 KB page-size 设备发布应用兼容要求。
- Android 17 / API 37 的源码同时包含原生 16 KB 路径、app compatibility loader 与 `fatal` 测试模式；发布产物仍应满足原生 16 KB 对齐。

### Android 17 的装载链边界

linker64 的装载顺序是：调用者 namespace 决定候选库，`LoadTask` 扩展依赖，`ElfReader` 建立映射，local/global group 限定符号查找，重定位完成后保护 RELRO，随后同步运行 constructor。ART 的 `JNI_OnLoad` 紧接其后，但属于另一套状态机。

遇到 native 加载慢或失败，应使用 trace 和 ELF 信息定位具体阶段，再决定修正依赖、导出面、重定位、构造函数、JNI 初始化、16 KB 对齐还是 namespace 配置。结论应能回到 Android 17 源码和具体构建产物核对，不能把一台设备上的毫秒数写成平台规则。


## VNDK 隔离与跨分区 Native 依赖

linker namespace 决定进程能看到哪些库，VNDK 和分区规则进一步限定 vendor、system 与应用之间可依赖的 ABI。

### 一、Android 17 的 VNDK 边界

VNDK（Vendor Native Development Kit）曾规定 vendor 原生代码可以使用哪些 framework 原生库，以便系统框架与厂商实现分别升级。VNDK 从 Android 15 开始弃用。`vendor` 或 `product` 分区面向 Android 15 及以上版本构建时，原 VNDK 库与其他可用库一样安装到对应分区，不再生成当前版本的 VNDK APEX，`ro.vndk.version` 与 `ro.product.vndk.version` 也被移除。

两类兼容边界仍要保留：

- VNDK 版本 14 及以下的 APEX 继续用于支持旧 vendor image，也就是保留旧厂商分区镜像运行所需的对应版本库；
- LL-NDK（底层原生接口库集合）不属于 VNDK，其稳定 ABI 仍用于 `system`/`vendor` 边界。ABI 指已经编译的二进制之间必须一致的函数调用、数据布局和符号约定。

因此，Android 17 新设备的库隔离不能继续描述为“当前 VNDK APEX 执行五级检查”。VNDK 的历史版本兼容、Soong 构建系统生成 `vendor` 变体的规则、动态链接器的 namespace 和 SELinux 是彼此相邻却各自独立的机制，生命周期也不同。

#### “Self-contained HAL”不是新的 linker 模式

旧 VNDK 文档要求 VNDK-SP（可安全加载进 framework 进程的一组 VNDK 库）及 SP-HAL（同样会被 framework 进程加载的 vendor HAL）依赖集合满足自包含约束，避免加载 `vendor` HAL 时继续依赖不允许进入该进程的厂商私有库。Android 17 的 Bionic 中没有名为“Self-contained HAL”的新 namespace 类型、`dlopen()` 标志或预加载调度器。

把 HAL 及依赖放在 `vendor`/`product` 侧，是构建与部署约束。静态链接多少库、是否采用 AIDL HAL、哪些库由 LL-NDK 提供，要由模块定义、稳定接口要求和升级边界决定。“自包含”不会自动减少动态库数量，平台也没有承诺由此获得固定的启动收益。

### 二、linker namespace 仍是运行时隔离基础

Android 11 起，`linkerconfig` 根据分区、已安装 APEX、公开库和运行时环境生成 `/linkerconfig/ld.config.txt` 及相关配置。动态链接器读取配置后，为进程建立 default、APEX、`vendor`、SP-HAL 等所需 linker namespace。namespace 是一组库搜索和可见性规则；namespace link 则声明可以跨边界访问哪些 soname，soname 是 ELF 共享库记录的逻辑名称，例如 `libfoo.so`。

一个进程可以有多个 namespace。每个 namespace 保存自己的搜索路径、许可路径、允许库名和到其他 namespace 的链接。跨 namespace 的库查找只会沿配置好的 link 继续，且通常只允许指定的共享库 soname。

应用还会由 `libnativeloader` 为各 ClassLoader 创建对应的 native namespace。系统原生进程、应用 JNI、APEX 进程和 `vendor` 守护进程的 namespace 关系图并不相同，不能从一个进程的 `LD_LIBRARY_PATH` 推断整台设备的库可见性。

### 三、`is_accessible()` 的准确语义

`android_namespace_t::is_accessible(path)` 是通用的 isolated namespace（限制库可见范围的隔离 namespace）检查，不是 VNDK 专用算法。下面的代码省略日志和局部变量，只保留 Android 17 的判断顺序：

```cpp
if (!is_isolated_) {
    return true;
}
if (!allowed_libs_.empty()) {
    const char* name = basename(file.c_str());
    if (std::find(allowed_libs_.begin(), allowed_libs_.end(), name)
            == allowed_libs_.end()) {
        return false;
    }
}
for (const auto& dir : ld_library_paths_) {
    if (file_is_in_dir(file, dir)) return true;
}
for (const auto& dir : default_library_paths_) {
    if (file_is_in_dir(file, dir)) return true;
}
for (const auto& dir : permitted_paths_) {
    if (file_is_under_dir(file, dir)) return true;
}
return false;
```

这段摘录展示了条件满足后立即返回、库名限制与三组路径检查的先后关系。`ld_library_paths_` 与 `default_library_paths_` 使用 `file_is_in_dir()`，只接受目录的直接子项；`permitted_paths_` 使用 `file_is_under_dir()`，允许更深层路径。

`allowed_libs_` 的实现类型是 `std::vector<std::string>`，检查使用线性查找的 `std::find()`。“哈希表平均 O(1)”与源码不符。它也不是独立的动态允许列表服务；配置会在 namespace 建立时写入对象。

正常按路径加载时，linker 先解析候选文件并取得消除符号链接等影响后的规范路径（realpath），再执行 namespace 可访问性检查。文件的 DAC（传统 Unix 用户/组/其他权限）、挂载选项和 SELinux 仍由各自层次处理；`permitted_paths_` 不会递归验证每级父目录权限，也不能替代 SELinux。

#### 搜索路径和许可路径回答不同问题

`ld_library_paths_` 与 `default_library_paths_` 参与按 soname 搜索。`permitted_paths_` 允许 isolated namespace 通过绝对路径访问额外目录，但不会自动把目录加入 soname 搜索顺序。把路径加入 permitted 列表，只表示某个绝对路径可能通过可访问性检查，不表示 `dlopen("libfoo.so")` 会从那里找到库。

`LD_LIBRARY_PATH` 只在非 secure execution 环境读取；secure execution 指动态链接器因进程具有特殊权限等安全条件而忽略部分环境变量。该变量只作用于 default namespace 的对应搜索路径。Android 17 Bionic 没有名为 `LOADER_PATH` 的同类环境变量。系统进程和应用还受启动环境、namespace 配置与公开库规则限制。

### 四、符号可见性怎样限制

库文件能够装入某个 namespace，只说明它通过了路径层检查。重定位（把代码中的符号引用绑定到实际地址）与 `dlsym()` 查找还受下面几组范围影响：

- 本 namespace 的 global group（全局可参与解析的库）与 local dependency group（从当前库出发可达的局部依赖）；
- 共享或次级 namespace 的成员关系；
- namespace link 是否允许该 soname；
- ELF 符号可见性、控制导出符号的 version script、`RTLD_LOCAL`、`RTLD_GLOBAL` 与 `DF_1_GLOBAL`；
- 目标库的 `DT_NEEDED` 依赖能否继续解析。

同名库可以分别存在于不同 namespace，减少 framework/vendor 或 APEX 之间意外解析到对方符号的情况。namespace 也允许显式导出少量稳定库。`dlopen()` 和 `dlsym()` 仍是 Bionic API，没有额外的“安全包装器”自动解决 ABI 不兼容或对象跨版本传递问题。

### 五、`dlopen()` 时间花在哪里

一次冷 `dlopen()` 可能包含：

1. soname 与 namespace link 搜索；
2. 路径解析、`open()`、ELF program header（描述各装载段的表）校验；
3. segment 映射与首次访问页面时发生的按需缺页；
4. `DT_NEEDED` 依赖图遍历；
5. GNU/SysV 哈希表中的符号查找与重定位；
6. RELRO（重定位后改为只读的区域）、TLS、MTE 等装载属性处理；
7. C/C++ 构造函数（constructors）。

namespace 的允许列表和路径检查只是其中一段。库大小、依赖数量、重定位数量、文件页是否已经在内存中、页大小、构造函数工作和设备 I/O 都会改变总耗时。AOSP 没有“VNDK 检查固定增加 15–25%”的结论；没有说明工作负载与测量方法的百分比，不能写进容量预算。

已经装入且可以复用的库，后续 `dlopen()` 可能命中链接器已有的库记录 `soinfo`；冷启动、首次缺页和构造函数成本不会按相同比例重复。跨 namespace 需要装入另一份库时，映射、重定位和进程修改后无法直接共享的私有脏页可能增加。能否共享物理文件页，还取决于加载的是同一 inode（文件系统中的同一个文件对象）还是不同分区中的不同副本。

Android 17 linker 是原生 C++ 实现，没有 JIT 编译访问检查，也没有基于 AI 的库访问预测。平台同样没有通用异步 `dlopen()` API；业务可以把允许后台执行的加载放到工作线程，但构造函数、JNI 注册和调用方线程约束仍要自行验证。

### 六、如何测量加载性能

Bionic 为 `dlopen()`、loading/linking、constructors、`dlsym()` 和 `dlclose()` 建立 trace 区间。Perfetto 中应把这些时间片与文件系统 I/O、缺页（page fault）、CPU 调度和应用启动阶段对齐，避免把整个加载窗口都归因于 namespace。

linker logger 支持 `dlopen`、`dlsym` 和 `dlerror` 三类选项。下面的命令只适合可调试进程，并应在复现结束后清除属性：

```bash
adb shell setprop debug.ld.app.com.example.app dlopen,dlsym,dlerror
adb logcat -s linker:D
adb shell setprop debug.ld.app.com.example.app ''
```

第一条命令启用指定进程的 linker 日志，第二条只显示 linker 标签，第三条在复现后清除属性。属性名使用进程 basename（路径或进程名的最后一段），带冒号的 service 进程会截断冒号及其后缀。不可转储（non-dumpable）的进程不会启用这组日志；量产用的 user build、权限与产品策略也可能限制设置属性。

设备上的 namespace 图应直接查看生成结果：

```bash
adb shell cat /linkerconfig/ld.config.txt
adb shell find /linkerconfig -maxdepth 3 -name ld.config.txt -print
```

这些文件反映设备当前分区与 APEX 组合，比套用历史 `ld.config.vndk_lite.txt` 模板可靠。读取权限和路径会随构建类型变化，脚本需要处理文件不可访问的情况。

性能实验至少区分文件页尚未缓存/已经缓存、首次/重复加载、相同/不同 namespace，并记录库及依赖的 build ID。报告中应给出 P50/P95（中位数和第 95 百分位）、CPU 时间、实际经过时间、需要/不需要存储 I/O 的 major/minor faults，以及重定位与构造函数区间；只报告一次 `dlopen()` 的实际经过时间，无法说明隔离开销。

### 七、Android 17 排障顺序

遇到 `dlopen failed` 时，可按错误信息依次确认：

1. 请求从哪个 namespace 发起，调用方属于哪个 ClassLoader、APEX 或 vendor 进程；
2. soname 是否在当前 namespace 的搜索路径中，或被相连 namespace 的允许列表放行；
3. 绝对路径是否通过 allowed libs 与 permitted paths；
4. `DT_NEEDED` 中是否存在跨分区私有依赖；
5. ELF 位数、ABI、页大小对齐、符号版本和重定位类型是否兼容；
6. 文件权限、SELinux denial、分区挂载和 APEX 激活状态；
7. 库是否带有耗时或有线程约束的 constructor。

错误信息中的 “not accessible for the namespace” 属于 linker namespace 边界；“library not found” 也可能表示某个依赖库没有找到；“cannot locate symbol” 则说明已经进入符号解析阶段。三者需要不同修复，扩宽 `permitted_paths_` 不会修复缺失符号或 ABI 不兼容。

### 八、源码与官方边界

- [VNDK overview 与弃用说明](https://source.android.com/docs/core/architecture/vndk)：Android 15 起的弃用范围、旧 VNDK APEX 与 LL-NDK 例外。
- [linker namespace 官方说明](https://source.android.com/docs/core/architecture/vndk/linker-namespace)：namespace 图、search/permitted path 与 linkerconfig 的历史边界。
- [linker_namespaces.cpp @ android-17.0.0_r1](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/linker/linker_namespaces.cpp)：路径与符号可访问性。
- [linker.cpp @ android-17.0.0_r1](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/linker/linker.cpp)：库搜索、装载、namespace link、relocation 与 `dlopen()` trace。
- [linker_logger.cpp @ android-17.0.0_r1](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/linker/linker_logger.cpp)：`debug.ld.*` 选项及 dumpable 限制。
- [linkerconfig README @ android-17.0.0_r1](https://android.googlesource.com/platform/system/linkerconfig/+/android-17.0.0_r1/README.md)：运行时配置输入、APEX public libraries 与输出文件。

### 九、版本范围

版本边界固定为 Android 17/API 37 与 `android-17.0.0_r1`。Android 17 的 linker namespace、VNDK 弃用说明和 Perfetto/linker logger 行为不能外推为后续平台能力。
