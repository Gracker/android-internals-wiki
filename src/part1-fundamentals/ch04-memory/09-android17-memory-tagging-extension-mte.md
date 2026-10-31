---
title: Android 17 ARM MTE 内存标签扩展实战
chapter: '4.9'
status: finalized
applicable_versions: Android 12 (API 31) - Android 17 (API 37)
last_verified: '2026-08-21'
last_verified_against: AOSP android-17.0.0_r1 / android17-6.18-2026-06_r6; bionic ifuncs.cpp MTE dispatch checked 2026-08-21
confidence: high
tags:
  - mte
  - memory-safety
  - arm
  - hardware-architecture
  - scudo
  - bionic
related_chapters:
- '20.11'
- '4.4'
- '15.3'
- '23.3'
last_deep_review_at: '2026-08-21T16:35:04+08:00'
sources:
- type: blog
  path: Cubox/四年之后，重新审视 MTE：从硬件架构到工程落地-2025-12-18.md
- type: blog
  path: Cubox/Android内存安全革命性改变：快手MTE探索与实践-2023-05-23.md
- type: aosp
  path: bionic/libc/bionic/libc_init_common.cpp
- type: aosp
  path: bionic/libc/platform/bionic/mte.h
- type: aosp
  path: frameworks/base/core/java/android/content/pm/ApplicationInfo.java
- type: aosp
  path: frameworks/base/core/java/com/android/internal/os/Zygote.java
- type: aosp
  path: bionic/libc/arch-arm64/ifuncs.cpp
- type: official
  path: https://source.android.com/docs/security/test/memory-safety/arm-mte
- type: official
  path: https://developer.android.com/ndk/guides/arm-mte
- type: research
  path: DeepResearch/2026-05-26-android-mte-asymm-auto-enablement-mechanism.md
---

# Android 17 ARM MTE 内存标签扩展实战

内存标签扩展（Memory Tagging Extension，MTE）通过比较指针标签与内存标签，检测一部分原生内存错误。这篇文章顺着一条主线展开：一次访问要满足什么条件才会被检查，SYNC、ASYNC、ASYMM 三种模式各自怎么报告错误，Bionic 与 Scudo 如何把 manifest 里的开关变成进程里的标签检查，以及堆、栈、全局变量三个范围分别怎么启用、怎么排错。

> 源码基线：AOSP `android-17.0.0_r1`；内核 `android17-6.18-2026-06_r6`。

MTE 的保护范围是走标签内存的原生访问。Java/Kotlin 对象仍由 ART 管理；32 位进程、未启用 MTE 的映射，以及没有正确设置标签的自定义分配器，都拿不到这层保护。

## MTE 硬件能力：从 FEAT_MTE 到 FEAT_MTE4

### FEAT_MTE、MTE2、MTE3、MTE4 与 Android 的关系

Arm 架构用 FEAT_MTE 到 FEAT_MTE4 这一组名字表示逐代扩展的硬件能力。我们在工程里最需要分清的是两处：

- Armv8.5-A 引入 MTE 的标签指令、标签内存和检查机制。
- Armv8.7-A 的 FEAT_MTE3 加入非对称模式（asymmetric mode）：读取错误同步报告，写入错误异步报告。

FEAT_MTE4 容易被误当成 Android 的第四种 `memtagMode`。它属于后续 CPU 的架构能力集合，和 manifest 取值是两回事：截至 Android 17 / API 37，应用 manifest 只接受 `off`、`default`、`sync` 和 `async`。在支持的 CPU 上，系统可以按首选模式把 ASYNC 请求运行成 ASYMM，但 manifest 里没有 `asymm` 和 `mte4` 这两个值。

判断一台设备是否支持 MTE，直接在设备上查最快，Android 版本号和 SoC 宣传名都推不出结论。下面的命令检查内核公布的 CPU 特性：

```bash
adb shell grep -w mte /proc/cpuinfo
```

输出里出现 `mte`，内核就已经向用户空间公布了这项能力。部分设备还需要在开发者选项里切换并重启，才会进入支持 MTE 的系统配置；开发者选项里没有这一项的设备，应用侧也补齐不了硬件或内核支持。

## 标签生成与硬件检测机制

MTE 的检测要从两个标签说起：一个跟着指针走，一个存在内存里。

### 逻辑标签、分配标签与 TBI

AArch64 的高字节忽略（Top Byte Ignore，TBI）允许地址翻译跳过虚拟地址高字节的一部分，MTE 就借用其中 `bits[59:56]` 这几位存放逻辑标签。内存侧按每 16 字节一个粒度保存一个 4 位分配标签（allocation tag）。CPU 访问标签内存时比较两者：

```text
指针：0x0A00_7f12_3456_7800
          ^^
          logical tag = 0xA

内存：[0x...7800, 0x...780f]  allocation tag = 0xA
```

两边标签一致，访问放行；不一致时怎么报告，取决于当前线程选的检查模式，我们留到后文“三种检测模式：报告行为与开销评估”再展开。

MTE 常用于发现两类原生内存错误：

- **空间错误**：指针越过分配边界，访问到标签不同的相邻粒度。
- **时间错误**：内存释放并重新分配后换了标签，旧指针继续访问时发生不匹配。

4 位标签只有 16 种取值，检测因此带有概率性；越界访问若还落在同一个 16 字节粒度里，标签一致，检查也就无从触发。MTE 的定位是原生内存安全的检测与缓解手段，跑完 MTE 测试没有报错，也只代表这两类错误这次没被抓到。标签元数据相对数据本身的存储比例，见后文“标签存储的内存开销与 vMTE 展望”。

<!-- gracker-diagram: ch04-09-pointer-tag-and-granule -->
![指针的逻辑标签，逐个对照 16 字节粒度的分配标签](../../assets/diagrams/ch04/ch04-09-pointer-tag-and-granule.png)

图：MTE 比较指针 bits[59:56] 的逻辑标签与访问地址所在 16 字节粒度的分配标签。示例中 A 指针访问 A 粒度可通过，越到 B 粒度或内存重标成 C 后仍使用旧 A 指针才会不匹配。同一粒度内的越界或标签碰撞可能漏检，比较通过也不证明业务访问合法。

### 标签指令与分配器约定

常用指令可以按职责分为以下几类：

| 指令 | 用途 |
| --- | --- |
| `IRG` | 从允许集合中生成逻辑标签，并写入指针 |
| `STG` / `ST2G` | 为一个或两个 16 字节粒度写入分配标签 |
| `STZG` / `STZ2G` | 写入标签，同时把对应数据清零 |
| `LDG` | 读取地址对应的分配标签 |

`IRG` 只给指针换逻辑标签，内存里的分配标签要靠 `STG` 写入。自定义分配器若只做了其中一步，合法访问也会对不上标签。

`bionic/libc/platform/bionic/mte.h` 里定义了：

```cpp
#define PR_MTE_TAG_SET_NONZERO (0xfffeUL << PR_MTE_TAG_SHIFT)
```

Bionic 初始化 MTE 时会把这个位掩码（mask）交给 `prctl()`。非零标签用于普通分配，标签 0 留给 Scudo 的分配块头（chunk header），专门用来捕获线性越界对分配器元数据的破坏。这一条是 Android Scudo 的实现约定，其他 MTE 分配器各有各的做法。

### 一次访问满足哪些条件才会检查

用户态的 load/store 指令要接受 MTE 检查，需要同时满足以下条件：

1. CPU 与内核公布 MTE 能力。
2. 地址所在映射以 `PROT_MTE` 建立，属于 Normal Tagged Memory。
3. 当前线程通过 `PR_SET_TAGGED_ADDR_CTRL` 选择了检查模式。
4. 当前执行上下文没有通过 `PSTATE.TCO` 临时关闭检查。

四个条件都满足后，CPU 才比较逻辑标签与分配标签。架构规范只约束外部可观察的异常语义；每款 CPU 的 TLB（地址转换缓存）、高速缓存、ROB（乱序重排序缓冲区）和写缓冲区怎么做，属于各自的微架构选择。这也是一套推测出来的流水线时序套不到所有 Arm CPU 头上的原因：开销要看数字，还是得回到目标设备。

<!-- gracker-diagram: ch04-09-mapping-thread-and-bypass -->
![映射与线程是两套开关，TCO 还可临时关闭检查](../../assets/diagrams/ch04/ch04-09-mapping-thread-and-bypass.png)

图：先有 CPU 与内核 MTE 能力，再分别给地址映射 PROT_MTE、给当前线程选择检查模式，且访问时 TCO 未关闭检查，才会比较标签。PR_GET_TAGGED_ADDR_CTRL 返回请求配置；请求多个模式时会保留多个位，不能据此证明某地址已带标签或当前 CPU 实际采用哪一个首选模式。

## 三种检测模式：报告行为与开销评估

三种模式的差别在报告精度和运行开销，我们逐个看出错时各自报告什么。

### SYNC：同步报告

同步模式在标签不匹配的那条 load/store 指令上当场报告错误，Linux 发来的是这样的信号：

```text
SIGSEGV
si_code = SEGV_MTESERR
si_addr = fault address
```

这一次访问就此作废。Android 的原生崩溃报告 tombstone 里，我们能拿到出错的程序计数器 PC 和地址；进程配置为 SYNC 时，Android 还会让 Scudo 记录内存分配与释放的调用栈，给释放后使用（use-after-free）或缓冲区溢出补上上下文。

所以 SYNC 适合开发、测试，以及值得花开销换准确归因的高价值进程。它的成本随 CPU、分配模式、内存访问和调用栈记录而变，3%～30% 只能当作量级参考，具体数字要在自己的设备上测。

### ASYNC：异步报告

异步模式让 CPU 先继续执行，之后再向出错线程补一条报告：

```text
SIGSEGV
si_code = SEGV_MTEAERR
si_addr = 0
```

代价是故障地址（fault address）和触发指令通常无法准确恢复，一次报告也可能对应之前一次或多次标签不匹配。它换来了低开销，适合生产环境的常态检测；发现问题后，再回到相同场景用 SYNC 复现。

还有一个常见误解是把报告时机说死：“一定在下一次系统调用报告”。内核文档只承诺异步语义，具体什么时候报，受架构与内核处理影响。

### ASYMM：读同步、写异步

ASYMM 把两种检查拆开用：读走同步，写走异步。AOSP 文档指出，它通常具有接近 ASYNC 的性能特征，同时又能准确定位读取错误。

应用接口请求不到 ASYMM，它由系统代选：Android 的 Bionic 在请求 ASYNC 时，先把 `PR_MTE_TCF_ASYNC | PR_MTE_TCF_SYNC` 两个可接受模式位一并交给内核，新内核据此结合当前 CPU 的首选模式，在 ASYNC、ASYMM 和 SYNC 里挑一个；内核若不接受多个模式位，Bionic 再回退到单独请求 ASYNC。

<!-- gracker-diagram: ch04-09-sync-async-asymm-reporting -->
![三种报告方式：精确访问位置与延后报告的取舍](../../assets/diagrams/ch04/ch04-09-sync-async-asymm-reporting.png)

图：SYNC 在出错访问报告 SEGV_MTESERR，地址与 PC 可定位；ASYNC 可在一次或多次错误后报告 SEGV_MTEAERR，地址为 0，报告 PC 不能直接视为触发指令。ASYMM 读同步、写异步。应用 manifest 只有 off/default/sync/async；ASYNC 请求可由 Bionic 提交多个可接受模式，再由内核按 CPU 首选代选。

### 开销评估与实测方法

开销随 CPU 与工作负载差别很大，抄一个固定百分比没有意义。评估时我们至少比较这几组数据：

- 关键场景耗时与帧耗时长尾；
- CPU 时间、指令数和高速缓存未命中次数；
- RSS（驻留集大小）/PSS（按比例分摊共享页后的内存） 及 Scudo 诊断元数据；
- 原生内存分配速率；
- MTE 崩溃数量和能够准确归因的比例。

做法是对同一个 release 构建分别跑 MTE OFF、ASYNC 或实际首选模式、SYNC 三轮，产品设备上的真实成本才有结论。硬件检查、Scudo 标签管理和 SYNC 调用栈记录，每一项都可能贡献开销。

## 内核 MTE 管理与 prctl 接口

内核这一层有两个开关：映射上的 `PROT_MTE`，线程上的 `prctl()` 配置。我们分开看。

### `PROT_MTE` 作用于映射

用户空间用 `mmap()` 或 `mprotect()` 给映射加上 `PROT_MTE`。Linux 接受匿名映射和基于内存的文件映射，例如 tmpfs、memfd；其他文件映射直接返回 `EINVAL`。

另有三个容易踩的约束：

- 新映射的分配标签初始为 0。
- `PROT_MTE` 加上之后就不能再用 `mprotect()` 撤掉。
- 执行 `MADV_DONTNEED` 或 `MADV_FREE` 后，内核可以把相关标签清为 0。

还要注意 `PROT_MTE` 只管映射这一层：线程若还处于 `PR_MTE_TCF_NONE`，标签不匹配照样没有 SYNC 或 ASYNC 报告。

### `prctl()` 控制当前线程

线程这一层由 `prctl()` 控制。`PR_SET_TAGGED_ADDR_CTRL` 一次配好三件事：带标签地址 ABI（应用二进制接口约定）、故障报告模式，以及 `IRG` 可用的标签位掩码。想确认当前线程是否选了某种 MTE 检查模式，可以用下面的代码：

```cpp
#include <sys/prctl.h>

bool running_with_mte() {
  int ctrl = prctl(PR_GET_TAGGED_ADDR_CTRL, 0, 0, 0, 0);
  return ctrl >= 0 && (ctrl & PR_MTE_TCF_MASK) != PR_MTE_TCF_NONE;
}
```

这个返回值只代表调用线程的配置，看不出任意地址是否映射了 `PROT_MTE`；Linux 的标签检查模式（TCF）是线程私有（per-thread）的，线程创建和上下文切换由 libc 与内核共同处理。

### CPU 首选模式

特权系统组件可以通过下面的 sysfs 内核属性节点，为每个 CPU 设置首选检查模式：

```text
/sys/devices/system/cpu/cpu<N>/mte_tcf_preferred
```

可写值是 `async`、`asymm`、`sync`，默认首选值为 `async`。内核的选择空间来自任务本身：任务请求了多个可接受的模式位，内核才有得挑；单独请求 SYNC 的线程，不会因为 CPU 的首选值被降成 ASYNC。

### `PSTATE.TCO` 与局部免检

`PSTATE.TCO=1` 会暂时关掉当前线程的标签检查。Bionic 用 `ScopedDisableMTE` 处理这套动作：保存旧值、写入 TCO，析构时恢复。它的正当用途是必须处理未知标签的底层代码，而不是拿去掩盖业务崩溃。

进入信号处理函数（signal handler）时，内核保证 `PSTATE.TCO=0`，`sigreturn()` 返回后再恢复被中断上下文的原值。

## Bionic/Scudo MTE 集成路径

这一节把启动链路走一遍：原生可执行文件自己选模式，应用进程由 Zygote 代选，最后都汇到 Scudo 的分配路径上。

### 原生可执行文件的初始化

动态可执行文件由链接器（linker）调用 `__libc_init_mte()`，静态可执行文件从 libc 初始化路径进入同一个函数。选择过程可以概括为：

1. 从 ELF 动态表项读取 `DT_AARCH64_MEMTAG_MODE` 以及堆、栈、全局变量标记；旧静态程序可以回退读取 Android ELF note 段。
2. 用环境变量或系统属性覆盖堆模式。
3. 调用 `PR_SET_TAGGED_ADDR_CTRL`。
4. 把初始堆标签级别、栈 ABI 状态写入 `__libc_shared_globals`。
5. Scudo 初始化时读取这些状态，决定是否为堆分配启用 MTE。

覆盖来源的优先级固定在 `libc_init_mte.cpp` 里：先 `MEMTAG_OPTIONS`，再 `arm64.memtag.process.<basename>`，然后是 DeviceConfig 里的进程覆盖值，最后是 `persist.arm64.memtag.default`。这些开关面向平台和调试配置，普通应用不要把它们当成稳定 API。


### 应用进程由 Zygote 决策

应用进程从 Zygote 派生（fork）而来，走不了原生可执行文件那套完整启动选择，改由 Zygote 代为决策。`Zygote.getRequestedMemtagLevel()` 在 `android-17.0.0_r1` 里按以下顺序取值：

1. `persist.arm64.memtag.app.<package>`；
2. `<process android:memtagMode>`；
3. `<application android:memtagMode>`；
4. `NATIVE_MEMTAG_SYNC` 兼容性变更开关（compat change）；
5. `NATIVE_MEMTAG_ASYNC` 兼容性变更开关；
6. 未命中以上来源时，若 `allowsNativeHeapPointerTagging()` 为 false，直接返回 NONE；否则读取 `persist.arm64.memtag.app_default`；
7. 仍未选定模式时，再判断旧版 TBI 指针标签兼容行为。

拿到结果后，`decideTaggingLevel()` 按硬件能力降级；在 userdebug/eng 调试系统且平台默认要求 SYNC 时，它还会把应用的 ASYNC 升为 SYNC。进程派生完成后，原生函数 `SpecializeCommon()` 把运行时标志转换成 `M_HEAP_TAGGING_LEVEL_*`，再调用：

```cpp
mallopt(M_BIONIC_SET_HEAP_TAGGING_LEVEL, heap_tagging_level);
```

这次 `mallopt()` 调用把堆标签级别交给 Bionic 内存分配器。

<!-- gracker-diagram: ch04-09-zygote-request-priority -->
![应用由 Zygote 决策：显式请求优先，默认前还有退出分支](../../assets/diagrams/ch04/ch04-09-zygote-request-priority.png)

图：Zygote 先取应用属性覆盖，再取 process/application manifest、SYNC/ASYNC compat 请求。都未命中时先检查是否退出原生堆指针标签，再读 app_default 和 TBI 兼容行为。decideTaggingLevel 根据硬件降级，调试系统还可升级 ASYNC；fork 后 SpecializeCommon 把运行时标志交给 Bionic 堆标签 mallopt。

`ApplicationInfo` 的内部常量是 `DEFAULT=-1`、`OFF=0`、`ASYNC=1`、`SYNC=2`。这几个整数属于隐藏实现，应用侧只认 manifest 字符串。

### Scudo 如何参与

堆 MTE 开启后，Scudo 在 `malloc`/`free` 两个入口管理指针标签和分配标签，堆缓冲区上溢/下溢和释放后使用都靠它发现。SYNC 配置会顺带打开内存分配调用栈跟踪，ASYNC 则关掉这项全量记录，把诊断成本降下来。

AOSP 暴露了两种分配标签策略，侧重点不同：

- `M_MEMTAG_TUNING_BUFFER_OVERFLOW`：让相邻内存块使用不同标签，优先发现线性越界。
- `M_MEMTAG_TUNING_UAF`：独立生成随机标签，在空间错误与释放后使用之间平衡检测概率。

粒度的限制还在：偏重缓冲区溢出的策略，同样管不到同一 16 字节粒度内的越界。

<!-- gracker-diagram: ch04-09-allocator-pointer-and-memory-tags -->
![分配器要同时维护指针与内存标签，IRG 不会替内存写标签](../../assets/diagrams/ch04/ch04-09-allocator-pointer-and-memory-tags.png)

图：IRG 生成指针逻辑标签，STG 等指令才写内存分配标签。Scudo 在 malloc/free 的受保护路径维护两端，普通分配排除标签 0，块头保留 0；启用释放重标记时还排除先前标签。越界和复用仍受粒度、选标策略与覆盖范围限制，不能仅按 4 位位宽给所有情形套统一检测概率。

### 堆标签级别的状态转换

`SetHeapTaggingLevel()` 允许 ASYNC 与 SYNC 之间来回切换。ASYNC/SYNC 降到 `NONE` 之后，Bionic 会关闭各线程的标签检查模式、停止栈 MTE，并通知 Scudo 禁用内存标签。这一步走完就回不去了：从 `NONE` 重新开启标签会失败，TBI 与 ASYNC/SYNC 之间也不能随意互换，因为进程中已有的指针、内存块和栈状态，恢复不成统一的带标签状态。所以策略要在进程启动时选好，运行时切换留给在 ASYNC 与 SYNC 之间复现问题。

<!-- gracker-diagram: ch04-09-heap-tagging-mode-transitions -->
![ASYNC 与 SYNC 可互换，关闭到 NONE 是单向转换](../../assets/diagrams/ch04/ch04-09-heap-tagging-mode-transitions.png)

图：在支持的进程配置中，SetHeapTaggingLevel 可在 ASYNC 与 SYNC 间切换，Bionic 同时调整线程 TCF 和 Scudo 分配栈记录。关闭到 NONE 会停止检查与标签管理，当前实现不支持再开启；TBI 与 ASYNC/SYNC 的切换也不被支持。这个进程级接口与直接调用某一线程 prctl 的范围不同。

## 栈与全局变量的 MTE 支持

这一节的实现都在当前源码基线上核对过，但各能力出现的版本有先有后：应用使用栈 MTE，官方从 Android 14 QPR3 开始支持；全局变量 MTE 的首发版本，要逐个核对历史源码标签才能确定，查不到就不猜。

### 堆、栈与全局变量三个范围

我们先把三个范围分开。只设置 `android:memtagMode`，覆盖的是普通系统分配器管理的原生堆（native heap）；栈上的局部对象要另做编译器插桩，全局变量则要编译器、LLD 链接器和 Android 动态链接器一起配合。

栈和全局变量（globals）用的 CMake 编译与链接配置，当前 NDK 文档给出如下：

```cmake
target_compile_options(
    ${TARGET} PUBLIC
    -fsanitize=memtag
    -fno-omit-frame-pointer
    -march=armv8-a+memtag)

target_link_options(
    ${TARGET} PUBLIC
    -fsanitize=memtag
    -fsanitize-memtag-mode=sync
    -march=armv8-a+memtag)
```

插桩构建只应在支持 MTE 的设备上运行，官方对它的定位是调试用途。发布包若只打算检查原生堆，启用 manifest 模式就够了，不必把所有原生目标都编成 memtag 插桩版本。

<!-- gracker-diagram: ch04-09-heap-stack-globals-coverage -->
![堆、栈、全局变量需要三套配合，manifest 只解决堆入口](../../assets/diagrams/ch04/ch04-09-heap-stack-globals-coverage.png)

图：普通原生堆依赖 manifest 模式与系统分配器；栈需要编译器按局部对象生命周期插桩，运行时准备标签栈与历史缓冲；全局变量需要编译器、LLD 描述符及动态链接器共同设置标签与重定位。只启用一个入口不能据此宣布三类存储都被覆盖。

### 栈 MTE

编译侧由 LLVM 的 AArch64 栈标签 pass 完成：给符合条件的栈对象设置生命周期标签，并可记录程序计数器、帧指针（frame pointer）和基础标签。运行时支持在 Bionic 里：

- 主程序或依赖声明 `DT_AARCH64_MEMTAG_STACK` 时，在启动阶段准备栈 MTE。
- 后续 `dlopen()` 加载带栈 MTE 的库时，链接器通过回调要求 libc 处理现有线程栈（stack）。
- MTE 已启用时，把线程栈重新映射为 `PROT_MTE`。
- 每个线程都为栈历史准备一块环形缓冲区；只要进程里有带栈标签的代码，哪怕运行设备没开 MTE，代码生成约定也要求线程局部存储（TLS）里留着这块缓冲区。

栈插桩能发现跨标签粒度的栈上溢/下溢，也更容易抓到部分函数返回后使用（use-after-return）问题。覆盖率则受编译器优化、对象布局、16 字节粒度和标签碰撞影响。

### 全局变量 MTE

链接器这一侧识别两个动态表项：

```text
DT_AARCH64_MEMTAG_GLOBALS
DT_AARCH64_MEMTAG_GLOBALSSZ
```

`should_tag_memtag_globals()` 要同时满足三个条件才成立：ELF 里带有全局变量描述符、描述范围大小非零、进程启用了 MTE。之后链接器依次做五件事：

1. 找到可写、不可执行的 `PT_LOAD` 数据段。
2. 尝试直接加入 `PROT_MTE`；文件映射不支持时，把内容复制到固定地址的私有匿名映射。
3. 解析采用 ULEB128 变长整数编码的描述符流，为每个全局变量范围写入分配标签。
4. 对符号地址和相关重定位项应用对应的逻辑标签。
5. 执行数据段保护步骤，并为替换文件映射的匿名虚拟内存区（VMA）命名，方便诊断；当前标签范围仍限于可写数据段。

这一步的代价是失去原有的文件页共享，所以链接器只在 ELF 明确请求全局变量标签、且设备支持 MTE 时才执行重新映射。


### 支持 MTE 的 libc ifunc

ifunc（indirect function，间接函数）让 libc 在运行时按硬件能力挑具体实现。`android-17.0.0_r1` 的 arm64 `ifuncs.cpp` 里，下面这些函数会检查 `HWCAP2_MTE`，支持时选 MTE 分支：

| libc 函数 | MTE 分支 |
| --- | --- |
| `memchr` | `__memchr_aarch64_mte` |
| `strchr` | `__strchr_aarch64_mte` |
| `strchrnul` | `__strchrnul_aarch64_mte` |
| `strlen` | `__strlen_aarch64_mte` |
| `strrchr` | `__strrchr_aarch64_mte` |
| `wcslen` | `portable_simd_wcslen_neon_mte` |
| `wmemchr` | `portable_simd_wmemchr_neon_mte` |

宽字符路径走 portable-simd 的 `_neon_mte` 版本；对应的 MTE 构建会把 `kReadAheadToPageBoundaryIsOK` 设为 `false`，不再像普通实现那样允许页边界预读。这套 ifunc 选择改的只是 libc 内部扫描实现，调用者的内存要享受 MTE，还得自己满足映射、线程模式和标签设置条件。

## 应用启用、验证与排错

### 调试构建使用 SYNC

我们建议只在调试版 manifest 里加以下覆盖配置：

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:tools="http://schemas.android.com/tools">
    <application
        android:memtagMode="sync"
        tools:replace="android:memtagMode" />
</manifest>
```

把文件放到 `app/src/debug/AndroidManifest.xml`，可以避免误把开发策略带到所有构建类型（build type）。支持 MTE 的设备上一旦出错，进程会生成带 `SEGV_MTESERR` 的 tombstone 崩溃报告。

### 无需改包的兼容性验证

manifest 是 `default` 或没写这个属性的应用，也有不改包的验证办法：临时启用兼容性变更开关。

```bash
adb shell am compat enable NATIVE_MEMTAG_SYNC com.example.app
adb shell am force-stop com.example.app
```

ASYNC 对应 `NATIVE_MEMTAG_ASYNC`。配置在下一次进程启动时生效；测试完把开关恢复回去，免得后续样本混进不同模式。

### 读取 tombstone

拿到 tombstone，我们先看信号代码：

- `SEGV_MTESERR`：同步错误，故障地址和 PC 能直接定位出错访问。
- `SEGV_MTEAERR`：异步错误，故障地址通常是 0，当前 PC 多半只是报告错误的位置。

SYNC 模式下还要看 `Cause: [MTE]`、内存分配/释放调用栈，以及故障地址周围的标签；用了栈插桩的话，再结合未剥离的调试符号、帧指针和栈历史还原局部对象。

常见排查顺序是：

1. 确认设备 `/proc/cpuinfo` 有 `mte`。
2. 确认应用进程重新启动后采用预期模式。
3. 用 SYNC 复现 ASYNC 上报的场景。
4. 对照内存分配、释放与故障调用栈。
5. 检查自定义分配器、JNI 指针算术、对象生命周期和跨线程移交。
6. 修复后用同一工作负载重新测试，并保留 MTE 与内存错误检测工具 ASan/HWASan 的互补测试。


## 标签存储的内存开销与 vMTE 展望

从架构信息量计算，每 16 字节数据需要 4 位分配标签，比例为：

```text
4 bit / (16 × 8 bit) = 1 / 32 = 3.125%
```

这个比例只描述标签元数据的容量。标签具体怎么存放、SoC 有没有预留连续物理区域、高速缓存怎么携带标签，都属于各家硬件实现。所以“32 GB 设备一定由引导加载程序预留 1 GB，而且操作系统看不见”，或者所有设备都采用 `Tag_PA = Base + (Data_PA >> 5)` 这一地址关系，都还只是猜测，应用侧据此下结论会出错。

Linux 核心转储（core dump）会把两个 4 位标签压成一个字节，标签内存对应的标签段文件大小因此也是数据范围的 `1/32`。运行时内存占用还要叠加分配器对齐、Scudo 元数据、SYNC 内存分配调用栈、栈历史，以及全局变量重新映射后失去的文件页共享。

“vMTE”常被用来指让标签存储更灵活或虚拟化的后续方案，Android 17 SDK/NDK 和 `android17-6.18-2026-06_r6` 都没有向应用提供这样的接口。评估 Android 17 产品时，我们以设备规格书、内核公布的能力和实测 PSS/RSS 为准，未来架构的设想先不算进当前收益。


## MTE 安全攻击面与缓解

### 检测概率与标签保密

攻击者猜中 4 位标签，或者错误访问仍落在同一标签粒度内，MTE 就可能漏报。AOSP 对独立随机标签策略给出的检测概率约为 93%，这是特定标签策略下的近似描述，不能直接等同于均匀使用全部 16 个标签的 `15/16` 模型：Android Scudo 的随机生成会排除标签 0，释放重标记还会排除先前标签。即时释放后访问与多次复用后的碰撞概率也不同。相邻标签策略则优先让常见的线性越界跨过内存块后撞上不同标签。

TIKTAG 等研究还展示了借助推测执行与高速缓存侧信道（cache side channel）推断 MTE 标签的可行性。做安全评估时，我们把标签当成可被推断的信息看待，而不是密码学秘密。某台 Android 17 设备是否受影响，取决于具体微架构、内核与缓解配置；CPU 声称支持 FEAT_MTE4，也证明不了设备已经免疫。

### 工程上的防护组合

MTE 在工程上要和其他措施搭着用：

- 使用 Rust、Java、Kotlin 等内存安全语言，缩小不安全 C/C++ 代码的范围。
- 在开发和持续集成（CI）阶段使用 HWASan/ASan，覆盖更丰富的错误模式。
- 在量产环境中，对安全价值较高的进程使用经过压测的 ASYNC 或 CPU 首选 ASYMM。
- 对抽样崩溃切换到 SYNC，获取准确的故障位置与分配器历史。
- 保持 CFI（控制流完整性）、FORTIFY（常见 libc 边界检查）、PAC/BTI（指针认证与分支目标保护）、seccomp（系统调用过滤）和最小权限等防护。
- 审计自定义分配器，保证 16 字节对齐、映射属性和标签更新都正确。

还有可用性这一面要提前想好：MTE 检测到错误时会终止进程。生产环境启用前，先测故障恢复、崩溃采集、版本回滚和关键数据持久化，别让内存安全收益变成不可控的用户损失。

## 版本演进与结论

| Android 版本 | 相关能力 |
| --- | --- |
| Android 12 / API 31 | AOSP 平台与用户空间内存分配器开始系统性支持 MTE |
| Android 13 / API 33 | 部分商用设备开始提供可用 MTE 支持 |
| Android 14 QPR3 | NDK 文档确认应用栈标签可用 |
| Android 17 / API 37 | Bionic/链接器已包含堆、栈、全局变量运行时支持，以及支持 MTE 的 `wcslen`/`wmemchr` ifunc |

我们把实用判断收成四条：先确认硬件和系统配置；开发阶段用 SYNC 获取准确报告；生产模式按目标 SoC 压测；堆、栈和全局变量分别验证覆盖范围。

> §20.11 继续讨论 MTE 与抽样式堆内存错误检测器 GWP-ASan 的模式选择、崩溃归因和分阶段启用策略。

## 参考资料

- [Android NDK：Arm Memory Tagging Extension](https://developer.android.com/ndk/guides/arm-mte)
- [AOSP：Arm Memory Tagging Extension](https://source.android.com/docs/security/test/memory-safety/arm-mte)
- [Linux kernel：Memory Tagging Extension in AArch64 Linux](https://docs.kernel.org/arch/arm64/memory-tagging-extension.html)
- [Arm：Memory Tagging Extension whitepaper](https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Arm_Memory_Tagging_Extension_Whitepaper.pdf)
- [AOSP android-17.0.0_r1：bionic MTE implementation](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/docs/mte.md)
- [AOSP android-17.0.0_r1：libc_init_mte.cpp](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/libc_init_mte.cpp)
- [AOSP android-17.0.0_r1：heap_tagging.cpp](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/heap_tagging.cpp)
- [AOSP android-17.0.0_r1：linker globals implementation](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/linker/linker.cpp)
- [AOSP android-17.0.0_r1：Zygote MTE decision](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/Zygote.java)
- [AOSP android-17.0.0_r1：arm64 ifuncs](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/arch-arm64/ifuncs.cpp)
- [Arm ABI：Memtag Extension to ELF for the Arm 64-bit Architecture](https://github.com/ARM-software/abi-aa/blob/main/memtagabielf64/memtagabielf64.rst)
- [TIKTAG research paper](https://arxiv.org/abs/2406.08719)
