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
  - self-contained-hal
  - linker64
  - dynamic-linker
related_chapters:
- '1.1'
- '1.6'
- '4.5'
- '8.2'
last_verified: '2026-11-04'
last_verified_against: AOSP android-17.0.0_r1
last_source_verified_at: '2026-11-04T18:40:00+08:00'
last_idle_audit_at: '2026-11-04T18:40:00+08:00'
confidence: high
last_body_apply_at: '2026-08-06T13:15:32+08:00'
last_review_finalize_at: '2026-08-06T14:07:19+08:00'
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
  path: bionic/linker/linker_tls.cpp
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

# Dynamic Linker、VNDK（Vendor Native Development Kit，厂商原生开发套件） 与 Native 库隔离

Android 进程执行原生代码之前，要把 ELF（Executable and Linkable Format，可执行与可链接格式）文件映射进地址空间，找到依赖库，解析动态符号，写入重定位结果，再调整页面权限并运行初始化函数。这些工作由 bionic 自带的 dynamic linker（动态链接器）完成；64 位进程的常见解释器路径是 `/system/bin/linker64`，下文简称 linker64。

> 源码基线：AOSP `android-17.0.0_r1`（Android 17 / API 37）；内核 `android17-6.18-2026-06_r6`。涉及 `mmap()`、文件缺页和写时复制（Copy-on-Write，COW）的内核行为以该分支为准；设备可能使用其他内核分支。

启动慢、找不到库、符号不匹配，这三类症状都要沿同一条装载路径逐段定位：linker64 先确定调用者的命名空间，在允许的搜索路径与跨 namespace 链接中解析依赖，随后完成重定位；分区隔离与稳定 ABI 规则约束可依赖的库和接口。本文前半部分讲 linker64 的执行顺序，以及各阶段对启动时间、内存和故障定位的影响；VNDK 的可见性规则放在后半部分。

正文沿用 linker 源码里的名称：DSO（Dynamic Shared Object）指 `.so` 动态共享对象，SONAME 是 ELF 内用于依赖匹配的逻辑库名，linker namespace（链接器命名空间） 约束库的搜索路径和可见范围。内存布局方面还会用到几个名字：RELRO（重定位后改为只读的区域） 是“重定位完成后只读”的内存区域，TLS 是每个线程独立保存的数据区，PLT/GOT 是动态函数调用和地址重定位所用的表，ABI 则是二进制接口约定。

## linker64 装载、重定位与命名空间

### linker64 的职责边界

我们先从入口看起。linker64 有两条主要入口：

- 进程启动：内核根据主程序的 `PT_INTERP`（指定 ELF 解释器的段）装入 linker64。linker64 完成自身重定位，再装入主程序、`LD_PRELOAD` 指定的优先库和 `DT_NEEDED` 声明的依赖库；这些工作完成后，控制权交给程序入口。
- 运行时装载：`dlopen()` 或 `android_dlopen_ext()` 进入 `do_dlopen()`，加载可访问范围内尚未存在的 DSO；`dlsym()` 查询符号；`dlclose()` 递减装载组引用计数并在满足条件时卸载。

linker64 不是常驻系统服务，也没有跨进程共享的“已解析符号缓存”：每个进程各自维护 `soinfo` 依赖图、namespace、符号查找范围和引用计数。文件页经内核页缓存（page cache）可以在进程间复用，地址空间和重定位结果仍归各进程所有。

`bionic/linker/Android.bp` 把 linker 配置为 `static_executable: true`。这里的“静态”表示它不能依赖另一个动态链接器替自己完成普通启动；源码注释也说明，linker 自身按共享对象布局链接，由静态库构成。把它当成普通静态程序的说法，漏掉了自举重定位——linker 先修正自身地址，再去装载其他 ELF。

### `soinfo`：运行时的 DSO 记录

`soinfo` 是 linker64 对一个已发现 DSO 的运行时描述，内容远多于 ELF 文件头的副本。Android 17 的对象里有这些字段：

- `base`、`size`、`load_bias`、Program Header；
- `.dynamic`、字符串表、符号表与 hash 表；
- 普通、PLT、RELR 和 Android packed relocation；
- 构造/析构函数数组；
- 父子依赖边、primary/secondary namespace；
- local-group root、引用计数与 `RTLD_*` 标记；
- TLS、MTE、GNU property 和 CFI（Control-Flow Integrity，控制流完整性）相关状态；
- realpath、SONAME、版本和 link 状态。

同一文件会不会复用现有 `soinfo`，要看 realpath、SONAME、namespace 可见性和装载参数，文件名相同说明不了问题；不同隔离空间也可能各自持有一套装载关系。

Android 17 源码里找不到 soinfo “把频繁访问与很少访问的字段按 CPU cache line（缓存行）分开”的明确证据。分析性能时，我们观察对象数量、依赖边、符号查找和页面行为；仅凭字段排列推导未经测量的缓存收益，是在猜。

### 一次 `dlopen()` 的执行顺序

#### 所有公开装载操作先经过同一把递归互斥锁

下面七个阶段都在持锁状态下执行。`bionic/linker/dlfcn.cpp` 中的 `dlopen`、`dlsym`、`dlclose`、`dl_iterate_phdr` 等入口都会持有 `g_dl_mutex`。它是 `PTHREAD_RECURSIVE_MUTEX_INITIALIZER_NP`，因此构造函数递归调用 `dlopen()` 时不会因重复加锁立刻死锁。

递归锁只解决重入，换不来并行装载：Android 17 的 `find_libraries()` 在顺序循环里完成依赖扩展、文件映射、预链接和重定位，另一个线程同时进入 linker API 时就得等这把锁。`do_dlopen()` 返回前还会调用 ELF 构造函数，所以一个耗时的构造函数同样会延长其他线程的 loader-lock wait（等待链接器全局锁的时间）。

两个执行特征：

- 同一依赖层的兄弟 DSO 不会由 linker64 自动并行加载。
- 把依赖图改得更“扁平”不会换来 linker 内部并行，只可能改变查找范围、构造顺序和待加载节点。

#### 阶段一：确定调用者和 namespace

`do_dlopen()` 先用调用地址查找所属 `soinfo`，再由 `get_caller_namespace()` 得到起始 namespace。走 `android_dlopen_ext()` 且 `android_dlextinfo` 带有 `ANDROID_DLEXT_USE_NAMESPACE` 时，显式 namespace 可以覆盖这一步得到的结果。

这也解释了我们常见的一类现象：同一个绝对路径或 SONAME，在 shell 测试程序里能加载，到应用进程里却可能失败——两者的搜索起点和可见范围并不相同。

#### 阶段二：按广度优先顺序扩展 `DT_NEEDED`

`find_libraries()` 先创建 `LoadTask`，随后遍历不断增长的任务列表。每个新 ELF 的 `DT_NEEDED` 会追加成后续任务，因此依赖发现顺序是广度优先。此时会：

- 复用 namespace 中已经加载且可访问的 `soinfo`；
- 为新库打开文件、读取 ELF 头、Program Header 和动态段所需信息；
- 建立父子边，记录依赖来自哪个 namespace；
- 跨 namespace 时沿允许的链接关系寻找指定 SONAME。

这里不是简单的 `find_library() → load_library() → load_dependencies()` 递归链。`LoadTask` 把“发现依赖”和“映射所有新库”分成不同阶段，便于失败时回收本次装载创建的对象。

#### 阶段三：映射新库的 `PT_LOAD`

linker64 从新任务中生成待映射列表：普通路径会随机化映射顺序；使用 `ANDROID_DLEXT_RESERVED_ADDRESS_RECURSIVE` 时，为满足保留地址区布局，顺序保持稳定。这项随机排列属于地址布局策略，与并发调度无关。

`ElfReader::Load()` 负责保留地址空间、映射 `PT_LOAD` 可装载段、定位运行时 Program Header（程序头表），并解析 GNU property（编译器写入 ELF 的架构特性说明）。

`android_dlopen_ext()` 还能通过文件描述符（fd）、fd 内偏移、保留地址区或 RELRO fd 提供特殊装载条件；WebView loader 用的就是其中的 RELRO 共享路径。

`mmap()` 成功只表示建立了映射，尚未访问的文件页仍可以留在磁盘或 page cache 中；就算 `dlopen()` 已经返回，库的全部代码页也未必都已缺页进入物理内存。

#### 阶段四：预链接并登记 TLS

所有新映射完成后，linker64 按广度优先顺序调用 `prelink_image()`。这里的“预链接”指解析动态段、为后续链接做准备，并不在这一步固定进程中的装载地址。这一阶段解析 `.dynamic`，记录：

- 字符串表、动态符号表和 GNU/SysV hash；
- `DT_NEEDED`、`DT_RUNPATH` 和符号版本信息；
- REL、RELA、RELR、APS2 packed relocation 的位置；
- `DT_INIT`、`DT_INIT_ARRAY`、`DT_FINI_ARRAY`、`DT_FINI`；
- TLS、AArch64 MTE（Memory Tagging Extension，内存标记扩展）和其他处理器相关动态项。

随后调用 `register_soinfo_tls()`，为含有 TLS 且尚未登记的 DSO 注册模块。进程启动时，静态 TLS 布局完成前会为模块预留静态偏移；布局完成后由 `dlopen()` 新注册的模块，其 `static_offset` 为 `SIZE_MAX`，不会再扩展静态 TLS 布局。若任一新库通过 `DT_AARCH64_MEMTAG_STACK` 请求 stack MTE，linker 会通知 libc 的对应回调。

#### 阶段五：构造 global group 与 local group

符号查找不会在进程内所有 DSO 中随意扫描。linker64 为每个待链接根节点组织：

- 全局组（global group）：预加载库以及带全局可见语义的库；
- 局部组（local group）：从当前根节点沿可访问依赖边得到的局部装载组。

`SymbolLookupList` 按这两个集合组织查找顺序。依赖边穿越 namespace 边界时，会产生单独的 local-group root，随后在所属 namespace 中完成链接。

#### 阶段六：重定位、页面保护与调试登记

`soinfo::link_image()` 对 local group 里尚未链接的库逐个执行以下工作：

1. 按 global/local lookup list（全局/局部符号查找列表） 解析重定位；
2. 把 `PT_GNU_RELRO` 对应页面改为只读；
3. 完成 16 KB app compatibility 路径需要的权限调整；
4. 处理 MTE globals；
5. 按 `android_dlextinfo` 写出或复用共享 RELRO；
6. 通知调试器，并把该 image 标为 linked。

任一环节失败，本次调用会沿失败保护路径卸载已创建的对象，`dlopen()` 返回 `nullptr`。

#### 阶段七：增加引用计数并运行构造函数

链接成功后，根 `soinfo` 的引用计数增加。`do_dlopen()` 随后同步调用 `soinfo::call_constructors()`，成功后才返回 handle（装载句柄）。

所以我们看到一次 `System.loadLibrary()` 或 `dlopen()` 耗时，它可能包含文件处理、映射、重定位和 ELF 构造函数，Java 调用链还包含 ART 的 `JNI_OnLoad`。把总时间都归到“linker 重定位慢”上，归因就下错了地方。

<!-- gracker-diagram: ch01-07-dlopen-stages -->
![dlopen 的装载阶段与链接器全局锁](../../assets/diagrams/ch01/ch01-07-dlopen-stages.png)

图：这里展示需要装载新 DSO 时的成功主路径。公开装载入口持有 g_dl_mutex，ELF 构造函数也在 dlopen 返回前同步执行；映射顺序的随机化不代表并行加载。

### Linker Namespace：控制“从哪里找”和“允许看见谁”

`android_namespace_t` 主要维护：

- `ld_library_paths_`：运行时设置的搜索路径；
- `default_library_paths_`：配置给 namespace 的常规搜索路径；
- `permitted_paths_`：isolated namespace 可访问的额外目录；
- `allowed_libs_`：允许装入的库名集合；
- `linked_namespaces_`：可跨边界查询的目标及 SONAME 白名单；
- `soinfo_list_`：当前 namespace 可见的 DSO。

对 isolated namespace 来说，路径可访问性和库名都要满足配置。当前空间找不到库时，linker 只查询已建立链接、且允许该 SONAME 的目标 namespace，失败后并不会无条件扫描 `system`、`vendor`、`product` 的全部目录。

#### namespace 名称和配置由设备决定

`system`、`vendor`、`product` 等名称在设备配置中很常见，但它们并不是 linker64 源码里固定不变的层级枚举：实际 namespace 由 linker config 生成，进程类型、APEX（可独立更新和挂载的系统模块）及厂商配置都能改变名称、路径与链接关系。

Android 17 仍从多级来源选择配置，依次考虑：与 APEX 可执行文件对应的配置、架构相关的 `/system/etc/ld.config.<ABI>.txt`、生成的 `/linkerconfig/ld.config.txt`、VNDK 路径和静态备用配置。所以“只认 `/linkerconfig/ld.config.txt`、旧配置已经删除”的说法与源码对不上，我们判断一台设备的配置来源时，要对照这份顺序。

应用的 ClassLoader namespace 还涉及 `libnativeloader` 与 ART。排查 `System.loadLibrary()` 时，我们要把 Java ClassLoader、NativeLoader 创建的 namespace 和 bionic 的路径检查连起来看，单看 `/system/lib64` 里有没有目标文件是不够的。

### Android 使用 eager binding（立即绑定）

传统 ELF 文档经常把 `RTLD_LAZY` 描述为“第一次经过 PLT（过程链接表）调用函数时再解析目标地址”，也就是 lazy binding（延迟绑定）。这不适用于 Android 17 的 bionic linker：

- `dlopen()` 接受 `RTLD_LAZY`，但 `linker.cpp` 明确注明该模式不受支持；
- 普通 REL/RELA 之后，PLT REL/RELA 也在 `relocate()` 中立即处理；
- 用于 lazy TLSDESC 的动态项被忽略，源码注释是“Bionic resolves everything eagerly”；
- `DT_BIND_NOW` 被忽略，因为相关语义已由 `DF_BIND_NOW` 表达，而 bionic 本身仍执行 eager relocation。

在 Android 上，“默认 lazy、加 Full RELRO（让可保护的重定位区域全部只读）后才改为 eager”的性能二选一并不存在，`_dl_runtime_resolve` 在首次 JNI 调用时逐项补 PLT 的常规路径同样没有。

#### Android 17 支持的重定位编码

编码格式与 CPU 重定位类型是两个维度。以 64 位进程为例：

| 编码或表 | 作用 | 运行时特征 |
| --- | --- | --- |
| `DT_RELR` | 压缩大量 relative relocation | 只需基址与位图展开，不查动态符号 |
| `DT_ANDROID_RELA` + `APS2` | Android packed relocation | 用分组和差值编码缩小重定位表 |
| 普通 `.rela.dyn` | 一般数据、符号与 TLS 重定位 | 某些条目需要在 lookup list 中查符号 |
| `.rela.plt` | PLT/GOT 中的函数入口地址 | 在 `dlopen()` 返回前完成 |

32 位 ABI 可以使用 REL 及 `DT_ANDROID_REL`。在 AArch64 上，linker 的快路径覆盖 `R_AARCH64_RELATIVE`、`R_AARCH64_JUMP_SLOT`、`R_AARCH64_GLOB_DAT`、`R_AARCH64_ABS64` 等常见类型；复杂或带版本的符号进入完整查找路径。

`DT_ANDROID_REL(A)` 里的内容是 APS2 压缩重定位数据，而非预链接地址信息；Android 17 也支持标准 `DT_RELR`。两者的作用都是压缩存储，让常见的 relative relocation（只需根据装载基址修正的相对重定位）更容易批量处理；运行时仍要按当前进程的随机装载基址写入目标地址。

#### 符号查找为何会变慢

一次需要符号解析的重定位，成本取决于：

- global/local lookup list 中要访问多少 DSO；
- 目标库使用 GNU hash 还是 SysV hash；
- 符号是否带版本约束；
- weak symbol、符号优先查找（symbolic lookup）、跨 namespace 边界等规则；
- 符号与 hash 表所在页面是否已经驻留。

GNU hash 的 Bloom filter（布隆过滤器）可以迅速筛掉不匹配的库，但总成本并不因此固定为 O(1)。每次 `soinfo::relocate()` 都创建一个 `Relocator`，其中的单项缓存记录最近一次查找的符号索引及结果；同一 DSO 本次重定位中，后续条目查找相同索引时可以复用，快路径和通用路径都能使用。缓存随这次 `relocate()` 结束而失效，不跨 DSO 或后续 `dlsym()` 调用长期保留。

### GNU RELRO：重定位完成后把页面设为只读

RELRO（Relocation Read-Only）由 ELF Program Header 中的 `PT_GNU_RELRO` 描述。`soinfo::link_image()` 完成重定位后调用 `protect_relro()`，由它对相应页面执行 `mprotect(PROT_READ)`，阻止后续代码改写已经填好目标地址的 GOT（全局偏移表）和其他敏感数据。

要看一个库覆盖了多大 RELRO 范围，我们查链接器生成的 segment 即可；`GNU_PROPERTY_RELRO` 在 Android 17 里并不存在。下面的命令用于同时检查 RELRO segment、绑定标记和实际重定位表：

```bash
llvm-readelf -lW libfoo.so | grep GNU_RELRO
llvm-readelf -dW libfoo.so | grep -E 'BIND_NOW|FLAGS'
llvm-readelf -rW libfoo.so
```

在 bionic eager binding 的前提下，`BIND_NOW` 不会再制造一轮“从 lazy 变 eager”的差异。性能上我们观察 RELRO 页面数量、重定位写入量、符号查找和后续 `mprotect()`；安全上确认预期区域确已落入 `PT_GNU_RELRO`。

`ANDROID_DLEXT_WRITE_RELRO` 与 `ANDROID_DLEXT_USE_RELRO` 还允许把 GNU RELRO 写入 fd，供另一个地址布局匹配的进程复用。Android 17 源码特别说明，WebView 使用这条路径共享包含大量 C++ vtable（虚函数表）的 RELRO 页。这是专用加载器协议，并非所有 system DSO 自动拥有的“预链接信息”。

### 构造函数：`dlopen()` 同步路径中的库代码

`soinfo::call_constructors()` 先设置 `constructors_called` 防递归，然后：

1. 递归调用子依赖的构造函数；
2. 调用当前 DSO 的 `DT_INIT`；
3. 正序调用 `DT_INIT_ARRAY`。

共享库中的 `DT_PREINIT_ARRAY` 会被忽略并产生警告；preinit 只用于主程序。卸载时顺序相反：逆序执行 `DT_FINI_ARRAY`，再执行 `DT_FINI`。

ELF constructor（构造函数）由 linker 在库装入时自动调用，它的 ABI 没有返回值，linker 也没有 `DL_ERR_CONSTRUCTOR_FAILED` 供应用捕获。因此构造函数一旦触发 `SIGSEGV`、`SIGABRT` 或未处理异常，进程通常直接终止，错误不会被转成 `dlerror()` 交回 `dlopen()` 调用者。

工程上的做法，是把构造函数限制在必要、可预测、不阻塞的初始化上：

- 不在 constructor 中等待 Binder、文件锁或其他线程；
- 不扫描大目录，不同步读取可延后的配置；
- 避免 constructor 相互 `dlopen()` 形成复杂递归；
- 需要业务上下文的工作放到显式初始化 API，并由调用方选择线程和时机。

Android 17 没有 `android_set_dl postpone_init()` 之类能让 `dlopen()` 跳过 constructor、稍后补执行的公开 API；要延后工作，只能调整库代码，或推迟整个装载调用。

### `JNI_OnLoad` 属于 ART 阶段

`System.loadLibrary()` 经过 ClassLoader/NativeLoader 后会进入 native 装载。bionic 完成 `dlopen()` 和 ELF constructor 后，ART 的 `JavaVMExt::LoadNativeLibrary()` 再查找 `JNI_OnLoad` 并同步调用它。`JNI_OnLoad` 是库可选提供的初始化入口，常用于检查虚拟机环境和注册 native 方法。

ART 还维护每个库的 `JNI_OnLoad` 状态：

- 同一库若正在由另一个线程执行 `JNI_OnLoad`，后来的线程等待结果；
- 没有 `JNI_OnLoad` 可以视为加载成功；
- 返回 `JNI_ERR` 或不支持的 JNI 版本会使这次 Java native library load 失败；
- ART 不会贸然 `dlclose()` 一个已经部分注册 native 方法的失败库，而是记录失败，令后续装载也失败。

这和 ELF constructor 的故障模型不同。`JNI_OnLoad` 有返回值，ART 能识别失败；constructor 没有受控失败协议。

<!-- gracker-diagram: ch01-07-elf-jni-initialization -->
![ELF 构造函数与 JNI_OnLoad 的先后边界](../../assets/diagrams/ch01/ch01-07-elf-jni-initialization.png)

图：System.loadLibrary 先经 ART/NativeLoader 完成原生库装载；bionic 的 dlopen 同步执行 ELF 构造函数。返回后，ART 才查找并调用可选 JNI_OnLoad，两个阶段具有不同的等待与失败处理。

#### 静态查找与 `RegisterNatives`

未显式注册的 native 方法在首次解析时，ART 会把 Java 类名和方法名按 JNI 规则编码成 mangled name（重整后的符号名），再到已为对应 ClassLoader 装入的 native 库中查找。找到入口后安装到方法上，后续调用不会每次重新扫描所有 DSO。

`RegisterNatives` 直接把 Java 方法与函数地址关联，适合这些情况：

- 不希望导出很长的 `Java_package_Class_method` 名称；
- 需要在一个可审查的表里明确 Java 签名和 native 地址；
- 希望减少首次方法解析时的 `dlsym()` 查询。

`RegisterNatives` 也有成本：注册表要维护，签名错误会在加载阶段暴露；放在 `JNI_OnLoad` 里，就占用了 `System.loadLibrary()` 的同步路径。动态注册不会自动转到后台，也不是通用的 native 热修复机制。两种方式怎么选，我们看 API 管理需求和实测查找成本；“每个静态 JNI 固定耗时若干毫秒”这类数字，没有参考价值。

### `dlerror()`、故障返回与 `dlclose()`

#### `dlerror()` 是线程局部状态

公开接口用返回值表示失败：

- `dlopen()` 失败返回 `nullptr`；
- `dlsym()` 失败需要结合 `dlerror()` 判断；
- `dlclose()` 失败返回非零值。

bionic 把内部错误文本格式化到当前线程的 dlerror buffer；对应用稳定公开的 `DL_ERR_*` 枚举并不存在，也没有供所有线程争用的单一 `g_dl_error` 字符串。所以诊断代码保存 `dlerror()` 文本就好，自造错误码、匹配可能变化的整句文案都靠不住。

namespace 拒绝、ELF 类型或 ABI 错误、缺少符号、重定位失败，都会走受控路径返回错误；constructor crash、越界写和信号终止则属于进程故障，`dlerror()` 收集不到它们。

#### `dlclose()` 处理的是装载组

`dlclose()` 做的远多于对一个文件执行 `munmap()`。Android 17 会：

1. 检查 local-group root 的引用计数；
2. 检查 `RTLD_NODELETE`（要求保留装载对象）与 `RTLD_GLOBAL`（让符号进入全局查找范围）等不可卸载条件；
3. 沿依赖图区分本地卸载节点和外部装载组引用；
4. 调用析构函数；
5. 注销 TLS 模块、通知 unload hook（卸载回调）和调试器、更新用于快速检查间接调用目标的 CFI shadow；
6. 释放映射与 `soinfo`，再递归处理外部引用。

源码里明确有 `unregister_soinfo_tls()`，所以“Android 的 DSO TLS 永远不回收”这个说法可以放下。不过，频繁卸载含活动线程、回调或缓存函数指针的库依然危险：linker 能维护自己的依赖图，悬空地址却要业务代码自己负责。

### 16 KB 页面：同时检查 ELF 和 APK

Android 15 起出现了使用 16 KB 内存页（page size）的设备，装载校验也随之多了一层。Android 17 的 linker64 校验 ELF 用的是运行时 `page_size()`，而非 `ro.page_size_16k`。在设备上确认页面大小，可执行：

```bash
adb shell getconf PAGE_SIZE
```

三种条件同时成立时，`ElfReader::LoadSegments()` 会返回“program alignment cannot be smaller than system page size”：系统页大小至少为 16 KB、ELF 的最小 `PT_LOAD p_align` 小于系统页大小、compatibility mode（兼容模式）未启用。

Android 17 同时保留了 `linker_phdr_16kib_compat.cpp` 的 4 KB 对齐兼容装载路径；因此旧库未必在所有 16 KB 设备上立即拒载。

`bionic.linker.16kb.app_compat.enabled` 在 Android 17 源码中有三种取值：

- `true`：对不满足对齐的 ELF 启用 compatibility path；
- `false`：不由该属性启用，包级 app compat mode 仍可能生效；
- `fatal`：不启用兼容；发现对齐不足时设置 abort message（进程终止原因）并触发 `SIGABRT`，方便测试尽早暴露问题。

若在 Android 17 测试设备上想让所有应用都关闭兼容模式、不兼容二进制立即终止，要同时关掉 Package Manager 的包级兼容：

```bash
adb shell setprop bionic.linker.16kb.app_compat.enabled fatal
adb shell setprop pm.16kb.app_compat.disabled true
```

只设置第一项时，包级 app compat mode 仍可能让 `should_use_16kib_app_compat_` 成立。测试完成后应恢复设备原有属性。

兼容路径是给迁移期用的工具，发布质量以原生 16 KB 对齐为准。它要处理按 4 KB segment 落入同一 16 KB 页时的权限冲突，代码明显比原生 16 KB 对齐路径复杂。

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

`android:extractNativeLibs="false"` 表示库可以从 APK 直接映射，前提是未压缩且偏移满足对齐。它改变不了 ELF 的 `p_align`，对最终 APK 的 `zipalign` 校验也替代不了。

### AArch64 MTE 与 BTI：按 ELF 声明执行

这一组安全特性名称相近、职责不同，都要求硬件、内核、工具链和 ELF 声明配合：MTE 用内存标签检查特定越界或悬空访问，BTI（Branch Target Identification，分支目标识别）限制间接分支可到达的入口，PAC（Pointer Authentication Code，指针认证码）用签名校验指针。

Android 17 解析的 MTE 动态项包括：

- `DT_AARCH64_MEMTAG_MODE`；
- `DT_AARCH64_MEMTAG_HEAP`；
- `DT_AARCH64_MEMTAG_STACK`；
- `DT_AARCH64_MEMTAG_GLOBALS` 与 `DT_AARCH64_MEMTAG_GLOBALSSZ`。

开启 MTE globals 时，linker 可能把含可写数据的文件映射重映射为带 `PROT_MTE` 的匿名页，然后根据 descriptor stream（描述各对象位置和标签规则的数据流）为全局对象分配内存标签，再恢复应有的只读权限。这会减少相应数据页的文件共享机会。

WebView 的共享 RELRO 路径为此使用确定性的 global tagging，即让不同进程按同一规则生成标签，从而继续复用 RELRO 内容。

BTI 走另一条路径：`linker_note_gnu_property.cpp` 解析 `GNU_PROPERTY_AARCH64_FEATURE_1_BTI`，硬件和 ELF 都满足条件时，linker 给可执行 segment 加 `PROT_BTI`。

`DT_AARCH64_PAC_PLT` 在 Android 17 的动态段解析中被列为忽略的处理器专用 tag。据此判断 linker64 会给进程内所有代码指针自动做 PAC 签名是靠不住的：PAC 是否生效取决于编译器生成的指令、ABI 和运行硬件，不由 `dlopen()` 统一开启。

### 可测量的延迟模型

把一次 Java 侧 native library load 拆开，得到下面这个延迟模型：

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

这个式子用来划分测量区间，各项之间会有交叠：冷缓存（所需文件页尚未进入 page cache）会同时影响 ELF 元数据、符号表和构造函数访问的数据页，另一个线程的 constructor 又可能表现为当前线程的 loader-lock wait。

下面几项通常比 `.so` 文件总大小更能解释加载耗时的波动：

- 本次调用新增多少个 `DT_NEEDED` 节点，多少依赖已经加载；
- APK 内直接映射、独立文件或 APEX 路径带来的文件访问差异；
- relative relocation、带符号 relocation 和 TLS relocation 的数量；
- lookup list 宽度、导出符号数与版本约束；
- constructor 与 `JNI_OnLoad` 执行了多少同步工作；
- 所需页面位于 page cache、压缩存储还是需要实际 I/O；
- 是否在等待其他线程持有 `g_dl_mutex`。

“每个 DSO 固定 0.5 ms”“依赖每深一层增加 3–8 ms”“冷启动固定慢 5–20 倍”都缺少设备、存储、构建产物和缓存状态的支撑，写不成 Android 17 的通用规律。库数量同样没有适合所有应用的 5–8 个上限；合并 DSO 能减少文件和 ELF 元数据处理，代价可能是常驻映射、RELRO、更新耦合和符号冲突范围变大。

#### 把加载点放回应用启动关键路径

`System.loadLibrary()` 从调用开始到返回的实际经过时间（wall time），会同时覆盖 ART / `libnativeloader`、linker、ELF constructor 和 `JNI_OnLoad`。我们回头看冷启动慢的时候，要注意它的触发点：`ContentProvider`、App Startup initializer、`Application.onCreate()` 或静态初始化块里的加载，都会直接落在冷启动关键路径上。

排查时先扫描应用和三方 SDK 的 `System.loadLibrary()` / `System.load()`，再给可控加载点加上稳定的 trace 名称；否则只看到一个 `dlopen` slice（trace 中的一段计时区间），仍定位不到是哪个业务模块触发。

把加载从首帧前挪走，优化并没有就此完成：首次功能入口如果因此多出同步等待，延迟只是换了位置。更稳妥的策略是按功能依赖确定最晚加载点，在明确的空闲窗口预先装载，并保留取消、超时和失败后的备用路径。`JNI_OnLoad` 只做 VM 校验、native 注册和少量确定状态；文件 I/O（输入输出）、设备枚举、大对象构造和线程创建放进可观测的显式初始化阶段。

并发调用多个 `System.loadLibrary()` 也算不上通用加速方案：公开 linker 操作共用 `g_dl_mutex`，DSO 依赖、constructor 与 SDK 全局状态还可能有隐含顺序。并行实验只适合已经证明互不依赖、且不阻塞首帧的提前装载任务。

### 分阶段排查

#### 1. 检查静态产物

排查从静态产物开始，我们先用命令把依赖、动态符号、重定位和 Program Header 各看一遍：

```bash
llvm-readelf -dW libfoo.so | grep NEEDED
llvm-readelf --dyn-syms -W libfoo.so
llvm-readelf -rW libfoo.so
llvm-readelf -lW libfoo.so
```

检查重点是非预期 `DT_NEEDED`、导出符号是否过多、重定位表类型和数量、`GNU_RELRO` 范围，以及 `PT_LOAD` 对齐。

#### 2. 用 Perfetto 区分链接与 constructor

Android 17 的 `do_dlopen()` 写入 `dlopen: <name>` 与 `dlopen: <name> - loading and linking` trace，`call_constructors()` 还写入 `calling constructors: <realpath>`。

`loading and linking` 在 `find_library()` 返回后结束，外层 `dlopen` slice 则继续覆盖 constructor，因此两者的差值可以帮助定位构造阶段。

锁等待不在这两条 bionic slice 内：`dlfcn.cpp` 的 `dlopen_ext()` 获取 `g_dl_mutex` 后才调用 `do_dlopen()`。

测 loader-lock wait 时，我们要在调用侧给整个 `System.loadLibrary()` 或 `dlopen()` 加 trace，结合线程调度、futex（内核提供的用户态互斥量等待机制）状态及同时持锁线程的 bionic slice 一起看；调用侧 slice 开始到 `dlopen:` slice 出现前的区间，才可能包含等锁时间。

若 Java 调用仍比 bionic slice 长，再检查 ART 的 native library load 与 `JNI_OnLoad`。

#### 3. 在可调试进程中打开 linker 日志

`debug.ld.app.<进程主名>` 和 `debug.ld.all` 接受 `dlerror`、`dlopen`、`dlsym`。下面的示例只针对指定应用，设置后要重启进程：

```bash
adb shell setprop debug.ld.app.com.example.app dlopen,dlerror
adb shell am force-stop com.example.app
```

linker 会检查进程是否为 dumpable，也就是系统安全策略是否允许导出其调试信息。普通 `user` build 上的不可调试应用通常拿不到这些日志。测试结束后用空值清理属性，避免一直产生无用日志：

```bash
adb shell setprop debug.ld.app.com.example.app ''
```

shell 启动的测试程序还可以用 `LD_DEBUG`，支持 `calls`、`dynamic`、`lookup`、`props`、`reloc`、`statistics`、`timing` 等选项。不过应用孵化路径可能过滤环境变量，把 shell 环境下的结果直接当成生产应用的行为，容易得出错误结论。

#### 4. 对照运行时映射

`/proc/<pid>/maps` 能确认实际加载路径、权限和地址区间，`smaps` 还能观察 file-backed（内容来自文件）、anonymous（匿名映射）、private dirty（进程私有且已写脏）页面与 RSS（进程当前驻留物理内存的页面总量，共享页也计入）。看到 `.so` 映射，离所有页面已驻留还差一步；分析内存时以 `smaps` 为准，只把虚拟地址区间长度相加说明不了问题。

### 优化时按证据下手

1. **移除非预期依赖。** 用 `DT_NEEDED` 和构建图确认来源，配合正确的构建目标依赖（target dependency）与 `--as-needed`。不要直接编辑 ELF 动态段。
2. **控制动态导出面。** `-fvisibility=hidden` 和 version script（符号导出控制脚本）能减少 `.dynsym` 中对外可见的符号。`strip` 主要删除调试符号和普通符号表，运行时仍需要的动态符号与重定位不会被随意删掉。
3. **让当前 NDK/LLD 生成合适的压缩重定位。** LLD 是 LLVM 工具链中的链接器；RELR 或 APS2 能减小产物和读取量，但要用目标 API、ABI 和设备验证兼容性。
4. **缩短 constructor 与 `JNI_OnLoad`。** 这是调用方最能控制、也最容易从 trace 直接确认的一段。
5. **避免高频装卸。** 稳定复用 handle 通常比反复 `dlopen()`/`dlclose()` 安全；若必须卸载，应建立线程、回调、TLS 和函数指针的生命周期约束。
6. **合并库前后都测。** 对比装载节点、重定位数、RELRO、文件页和增量发布影响，不设置脱离产物的库数量或体积指标。
7. **把 16 KB 校验放进构建流水线。** 同时检查每个 ABI 的 ELF 与最终 APK/AAB（Android App Bundle）产物，兼容模式只用于发现和迁移旧库。
8. **依据接口管理选择 JNI 注册方式。** 动态注册可收窄导出面并提前绑定；静态查找可减少注册代码。性能判断以具体 trace 和符号表为准。

对三方 SDK 和跨平台引擎，还要记录 APK/AAB 内路径、ABI、build ID（用于唯一识别二进制构建的标识）、`DT_NEEDED`、LOAD alignment（可装载段对齐）、constructor / `JNI_OnLoad` 和首次触发线程。React Native、Flutter、Unity、Unreal、Cocos 声称“官方版本支持 16 KB”，也替代不了最终产物扫描，旧插件仍可能覆盖正确的链接参数。

CI 应检查每个 release APK/AAB，只读 CMake 参数是不够的。至少验证所有 ABI 的 ELF LOAD segment、未压缩 `.so` 的 ZIP alignment、AAB page-alignment 配置、`DT_NEEDED` 与动态符号规模，并在 16 KB 设备覆盖启动、动态功能模块、native 插件和低内存场景。

即使源码参数正确，最终生成的 split APK（拆分安装包）仍可能被旧版 bundletool（从 AAB 生成安装包的工具）或三方产物破坏，因而必须以发布包的检查结果为准。

### 版本演进边界

- Android 10 已广泛使用 namespace 与 APEX 路径兼容逻辑，旧应用行为还受到 target SDK 兼容分支影响。
- Android 11 起，LinkerConfig 生成的 `/linkerconfig/ld.config.txt` 成为常见配置来源，但 Android 17 源码仍保留其他配置选择与兜底。
- Android 12 至 Android 14 期间，工具链、RELR、MTE 和 BTI 支持持续演进。分析旧设备时要用对应分支，不能把 Android 17 的 tag 与兼容路径倒推到所有版本。
- Android 15 开始面向 16 KB page-size 设备发布应用兼容要求。
- Android 17 / API 37 的源码同时包含原生 16 KB 路径、app compatibility loader 与 `fatal` 测试模式；发布产物仍应满足原生 16 KB 对齐。

### Android 17 的装载链边界

到这里我们可以把整条装载链串起来：调用者 namespace 决定候选库，`LoadTask` 扩展依赖，`ElfReader` 建立映射，local/global group 限定符号查找，重定位完成后保护 RELRO，随后同步运行 constructor。ART 的 `JNI_OnLoad` 紧接其后，但属于另一套状态机。

遇到 native 加载慢或失败，我们用 trace 和 ELF 信息定位到具体阶段，再决定修依赖、修导出面、修重定位、构造函数、JNI 初始化、16 KB 对齐还是 namespace 配置。结论要能回到 Android 17 源码和具体构建产物核对；一台设备上量到的毫秒数，写不成平台规则。


## VNDK 隔离与跨分区 Native 依赖

讲完进程内部的装载，我们再看分区之间：linker namespace 决定进程能看到哪些库，VNDK 和分区规则进一步限定 vendor、system 与应用之间可依赖的 ABI。

### 一、VNDK 的弃用与现存机制

VNDK（Vendor Native Development Kit）曾规定 vendor 原生代码可以使用哪些 framework 原生库，让系统框架和厂商实现分别升级；这套机制从 Android 15 开始弃用。`vendor` 或 `product` 分区面向 Android 15 及以上版本构建时，原 VNDK 库与其他可用库一样安装到对应分区，当前版本的 VNDK APEX 不再生成，`ro.vndk.version` 与 `ro.product.vndk.version` 也随之移除。

弃用之后，有两类兼容安排保留了下来：

- VNDK 版本 14 及以下的 APEX 继续支持旧 vendor image，也就是保留旧厂商分区镜像运行所需的对应版本库；
- LL-NDK（底层原生接口库集合）不属于 VNDK，它的稳定 ABI（已经编译的二进制之间必须一致的函数调用、数据布局和符号约定）仍然约束 `system`/`vendor` 之间的接口。

所以描述新设备的库隔离时，“当前 VNDK APEX 执行五级检查”这套说法已经失效；实际在起作用的是几个各自独立的机制——VNDK 历史版本兼容、Soong 生成 `vendor` 变体的规则、动态链接器 namespace 和 SELinux，它们的生命周期各不相同。

APEX 改变的是库的来源、配置和激活方式；进程里已经映射好的 DSO，在进程存活期间保持原样。APEX 新版本生效后，新启动的进程按新挂载与 namespace 配置装载，老进程若仍持有旧映射，要由模块自身的重启策略处理。

#### “Self-contained HAL”与 VNDK-SP 自包含约束

旧 VNDK 文档要求 VNDK-SP 与 SP-HAL 的依赖集合满足自包含约束。VNDK-SP 指可安全加载进 framework 进程的一组 VNDK 库，SP-HAL 指同样由 framework 进程加载的 vendor HAL；这条约束要避免的情况是：加载 `vendor` HAL 时，还要依赖不允许进入该进程的厂商私有库。

把 HAL 及其依赖放在 `vendor`/`product` 侧，属于构建与部署层面的约束。我们在 Android 17 的 Bionic 里找不到名为“Self-contained HAL”的新 namespace 类型、`dlopen()` 标志或预加载调度器；静态链接多少库、是否采用 AIDL HAL、哪些库由 LL-NDK 提供，要由模块定义、稳定接口要求和分区升级方式决定。“自包含”不会自动减少动态库数量，固定的启动收益也谈不上平台承诺。

### 二、linker namespace 仍是运行时隔离基础

Android 11 起，`linkerconfig` 根据分区、已安装 APEX、公开库和运行时环境生成 `/linkerconfig/ld.config.txt` 及相关配置。动态链接器读取配置后，为进程建立 default、APEX、`vendor`、SP-HAL 等所需 linker namespace。namespace 是一组库搜索和可见性规则；namespace link 则声明可以跨 namespace 访问哪些 soname（如 `libfoo.so`）。

一个进程可以有多个 namespace。跨 namespace 的库查找只沿配置好的 link 继续，且通常只放行指定的共享库 soname。应用还会由 `libnativeloader` 为各 ClassLoader 创建对应的 native namespace；系统原生进程、应用 JNI、APEX 进程和 `vendor` 守护进程的 namespace 关系图各不相同，所以查一台设备的库可见性要按进程类型分别看配置，单看一个进程的 `LD_LIBRARY_PATH` 得不到全貌。

### 三、`is_accessible()` 的判断顺序

路径层的拦截发生在 `is_accessible()`：`android_namespace_t::is_accessible(path)` 是通用的 isolated namespace（启用路径隔离检查的命名空间）检查，VNDK 只是它的使用场景之一。下面的代码省略日志和局部变量，保留完整的判断顺序：

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

这段摘录的重点在顺序：`is_isolated_` 为假时直接返回 true；`allowed_libs_` 非空时先查库名，不在集合里就直接返回 false；三组路径检查排在库名限制之后。

两组路径函数的行为不同：`ld_library_paths_` 与 `default_library_paths_` 使用 `file_is_in_dir()`，只接受目录的直接子项；`permitted_paths_` 使用 `file_is_under_dir()`，允许更深层路径。

<!-- gracker-diagram: ch01-07-namespace-access -->
![isolated namespace 的库名与路径检查顺序](../../assets/diagrams/ch01/ch01-07-namespace-access.png)

图：is_accessible 先判断 namespace 是否隔离，再按非空 allowed_libs 检查库名，最后检查三组路径。这里的 true 只表示通过该 namespace 的路径检查，文件权限和 SELinux 仍单独生效。

`allowed_libs_` 的实现类型是 `std::vector<std::string>`，检查用的是线性查找的 `std::find()`，所以“哈希表平均 O(1)”的印象与源码对不上；这份名单在 namespace 建立时就写进了对象，是一份静态配置，运行期没有单独的动态允许列表服务可查。

正常按路径加载时，linker 先解析候选文件，得到消除符号链接等影响的规范路径（realpath），再执行 namespace 可访问性检查。`permitted_paths_` 只做路径归属判断，文件的 DAC（传统 Unix 用户/组/其他权限）、挂载选项、每级父目录权限和 SELinux，仍由各自的层次负责。

#### 搜索路径与许可路径的分工

`ld_library_paths_` 与 `default_library_paths_` 参与按 soname 搜索；`permitted_paths_` 允许 isolated namespace 通过绝对路径访问额外目录。一个路径进了 permitted 列表，只是有机会通过可访问性检查，soname 搜索顺序仍由搜索路径列表决定——`dlopen("libfoo.so")` 能否从那里找到库，要看搜索路径列表里有没有它。

secure execution 指动态链接器因进程具有特殊权限等安全条件而忽略部分环境变量，`LD_LIBRARY_PATH` 只在非 secure execution 环境读取，而且只作用于 default namespace 的对应搜索路径；Bionic 里同样没有名为 `LOADER_PATH` 的同类环境变量。系统进程和应用还受启动环境、namespace 配置与公开库规则限制。

### 四、符号可见性怎样限制

库文件能装入某个 namespace，只说明它过了路径这一关；重定位（把代码中的符号引用绑定到实际地址）与 `dlsym()` 查找还要经过下面几组范围的筛选：

- 本 namespace 的 global group（全局可参与解析的库）与 local dependency group（从当前库出发可达的局部依赖）；
- 共享或次级 namespace 的成员关系；
- namespace link 是否允许该 soname；
- ELF 符号可见性、控制导出符号的 version script、`RTLD_LOCAL`、`RTLD_GLOBAL` 与 `DF_1_GLOBAL`；
- 目标库的 `DT_NEEDED` 依赖能否继续解析。

同名库可以分别存在于不同 namespace，减少 framework/vendor 或 APEX 之间意外解析到对方符号的情况；namespace 也允许显式导出少量稳定库。`dlopen()` 和 `dlsym()` 仍是 Bionic API，ABI 不兼容或对象跨版本传递这类问题，没有额外的“安全包装器”代为解决。

### 五、`dlopen()` 时间花在哪里

隔离规则讲完，我们回到性能：一次冷 `dlopen()` 的时间可以拆成这些段：

1. soname 与 namespace link 搜索；
2. 路径解析、`open()`、ELF program header（描述各装载段的表）校验；
3. segment 映射与首次访问页面时发生的按需缺页；
4. `DT_NEEDED` 依赖图遍历；
5. GNU/SysV 哈希表中的符号查找与重定位；
6. RELRO、TLS、MTE 等装载属性处理；
7. C/C++ 构造函数（constructors）。

namespace 的允许列表和路径检查只是其中一段；库大小、依赖数量、重定位数量、文件页是否已在内存中、页大小、构造函数工作和设备 I/O 都会改变总耗时。“VNDK 检查固定增加 15–25%”在 AOSP 里找不到出处，缺少工作负载与测量方法说明的百分比，写进容量预算只会误导。

已经装入、可以复用的库，后续 `dlopen()` 可能直接复用 linker 里已有的 `soinfo` 记录，冷启动、首次缺页和构造函数成本不会按相同比例重复；跨 namespace 另装一份库时，映射、重定位和私有脏页（写脏后进程私有的页面）都可能增加。两次加载能否共享物理文件页，取决于它们指向同一个 inode（文件系统中的同一个文件对象），还是不同分区中的不同副本。

Android 17 linker 是原生 C++ 实现，访问检查在原生代码路径里同步完成，linker 里没有 JIT 编译的访问检查，也没有基于 AI 的库访问预测；平台没有提供通用异步 `dlopen()` API。业务可以把允许后台执行的加载放到工作线程，构造函数、JNI 注册和调用方线程约束仍要自行验证。

### 六、如何测量加载性能

测量时我们把 Bionic 为 `dlopen()`、loading/linking、constructors、`dlsym()` 和 `dlclose()` 建立的 trace 区间，与文件系统 I/O、缺页（page fault）、CPU 调度和应用启动阶段对齐，避免把整个加载窗口都归因于 namespace。

linker logger 支持 `dlopen`、`dlsym` 和 `dlerror` 三类选项。下面的命令只适合可调试进程，复现结束后应清除属性：

```bash
adb shell setprop debug.ld.app.com.example.app dlopen,dlsym,dlerror
adb logcat -s linker:D
adb shell setprop debug.ld.app.com.example.app ''
```

第一条命令启用指定进程的 linker 日志，第二条只显示 linker 标签，第三条在复现后清除属性。属性名使用进程 basename（路径或进程名的最后一段），带冒号的 service 进程会截断冒号及其后缀；不可转储（non-dumpable）的进程拿不到这组日志，量产用的 user build、权限与产品策略也可能限制设置属性。

设备上真实的 namespace 图，直接看生成结果最可靠：

```bash
adb shell cat /linkerconfig/ld.config.txt
adb shell find /linkerconfig -maxdepth 3 -name ld.config.txt -print
```

这些文件反映设备当前分区与 APEX 组合，比套用历史 `ld.config.vndk_lite.txt` 模板可靠；读取权限和路径会随构建类型变化，脚本要处理文件不可访问的情况。

性能实验至少区分文件页尚未缓存/已经缓存、首次/重复加载、相同/不同 namespace，并记录库及依赖的 build ID。报告里给出 P50/P95（中位数和第 95 百分位）、CPU 时间、实际经过时间、需要/不需要存储 I/O 的 major/minor faults，以及重定位与构造函数区间；隔离开销有多大，要靠这些对照数据回答，一次 `dlopen()` 的实际经过时间给不出结论。

### 七、排障顺序

遇到 `dlopen failed`，我们按错误信息依次确认：

1. 请求从哪个 namespace 发起，调用方属于哪个 ClassLoader、APEX 或 vendor 进程；
2. soname 是否在当前 namespace 的搜索路径中，或被相连 namespace 的允许列表放行；
3. 绝对路径是否通过 allowed libs 与 permitted paths；
4. `DT_NEEDED` 中是否存在跨分区私有依赖；
5. ELF 位数、ABI、页大小对齐、符号版本和重定位类型是否兼容；
6. 文件权限、SELinux denial、分区挂载和 APEX 激活状态；
7. 库是否带有耗时或有线程约束的 constructor。

三类报错各有含义：“not accessible for the namespace” 是 linker namespace 拦下了请求；“library not found” 可能是某个依赖库没有找到；“cannot locate symbol” 说明已经走到符号解析阶段。它们的修法各不相同，扩宽 `permitted_paths_` 解决不了缺失符号或 ABI 不兼容。

### 八、源码与官方资料

- [VNDK overview 与弃用说明](https://source.android.com/docs/core/architecture/vndk)：Android 15 起的弃用范围、旧 VNDK APEX 与 LL-NDK 例外。
- [linker namespace 官方说明](https://source.android.com/docs/core/architecture/vndk/linker-namespace)：namespace 图、search/permitted path 与 linkerconfig 的历史边界。
- [linker_namespaces.cpp @ android-17.0.0_r1](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/linker/linker_namespaces.cpp)：路径与符号可访问性。
- [linker.cpp @ android-17.0.0_r1](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/linker/linker.cpp)：库搜索、装载、namespace link、relocation 与 `dlopen()` trace。
- [linker_tls.cpp @ android-17.0.0_r1](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/linker/linker_tls.cpp)：TLS 模块登记与启动期静态 TLS 布局的边界。
- [linker_relocate.cpp @ android-17.0.0_r1](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/linker/linker_relocate.cpp)：重定位循环与 `Relocator` 单项符号缓存的生命周期。
- [linker_logger.cpp @ android-17.0.0_r1](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/linker/linker_logger.cpp)：`debug.ld.*` 选项及 dumpable 限制。
- [linkerconfig README @ android-17.0.0_r1](https://android.googlesource.com/platform/system/linkerconfig/+/android-17.0.0_r1/README.md)：运行时配置输入、APEX public libraries 与输出文件。

### 九、版本范围

版本范围固定为 Android 17/API 37 与 `android-17.0.0_r1`；本章描述的 linker namespace、VNDK 弃用过程和 Perfetto/linker logger 行为，只代表这一版本；后续平台的行为，要以对应分支为准。
