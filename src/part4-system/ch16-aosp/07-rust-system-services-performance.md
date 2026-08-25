---
title: Android 17 平台 Rust 性能边界：Binder、CXX 与 Soong
chapter: '16.7'
section: '16.7'
status: ready-to-publish
applicable_versions: Android 12 (API 31) - Android 17 (API 37)
tags:
- rust
- ffi
- jni
- system-services
- keystore
- bluetooth
- dns-resolver
- bionic
- scudo
- monomorphization
related_chapters:
- '1.3'
- '1.18'
- '1.10'
- '3.6'
- '14.2'
- '20.10'
last_verified: '2026-08-14'
last_verified_against: AOSP android-17.0.0_r1 (Keystore2 / DnsResolver / UWB / Bluetooth / VirtualizationService / libbinder_rs / Soong Rust / android-crates-io / crate_tool); official Android Rust, AIDL backend, and Scudo documentation
confidence: high
pipeline_stage: ready-to-publish
task6_state: reviewed
sources:
- type: aosp
  path: https://android.googlesource.com/platform/system/security/+/refs/tags/android-17.0.0_r1/keystore2/
- type: aosp
  path: https://android.googlesource.com/platform/system/security/+/refs/tags/android-17.0.0_r1/keystore2/Android.bp
- type: aosp
  path: https://android.googlesource.com/platform/system/security/+/refs/tags/android-17.0.0_r1/keystore2/src/keystore2_main.rs
- type: aosp
  path: https://android.googlesource.com/platform/system/security/+/refs/tags/android-17.0.0_r1/keystore2/src/service.rs
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/DnsResolver/+/refs/tags/android-17.0.0_r1/
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/DnsResolver/+/refs/tags/android-17.0.0_r1/Android.bp
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/DnsResolver/+/refs/tags/android-17.0.0_r1/rust/Android.bp
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Uwb/+/refs/tags/android-17.0.0_r1/libuwb-uci/src/
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Uwb/+/refs/tags/android-17.0.0_r1/libuwb-uci/src/Android.bp
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/system/rust/
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/system/rust/Android.bp
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Virtualization/+/refs/tags/android-17.0.0_r1/android/virtualizationservice/
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Virtualization/+/refs/tags/android-17.0.0_r1/android/virtualizationservice/Android.bp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/binder/rust/Android.bp
- type: aosp
  path: https://android.googlesource.com/platform/build/soong/+/refs/tags/android-17.0.0_r1/rust/
- type: aosp
  path: https://android.googlesource.com/platform/build/soong/+/refs/tags/android-17.0.0_r1/rust/config/global.go
- type: aosp
  path: https://android.googlesource.com/platform/build/soong/+/refs/tags/android-17.0.0_r1/rust/compiler.go
- type: aosp
  path: https://android.googlesource.com/platform/build/soong/+/refs/tags/android-17.0.0_r1/rust/library.go
- type: aosp
  path: https://android.googlesource.com/platform/external/rust/android-crates-io/+/refs/tags/android-17.0.0_r1/README.md
- type: aosp
  path: https://android.googlesource.com/platform/development/+/refs/tags/android-17.0.0_r1/tools/external_crates/crate_tool/src/main.rs
- type: official
  path: https://source.android.com/docs/setup/build/rust/building-rust-modules/overview
- type: official
  path: https://source.android.com/docs/setup/build/rust/building-rust-modules/android-rust-modules
- type: official
  path: https://source.android.com/docs/core/architecture/aidl/aidl-backends
- type: official
  path: https://source.android.com/docs/security/test/scudo
- type: official
  path: https://security.googleblog.com/2021/04/rust-in-android-platform.html
- type: official
  path: https://security.googleblog.com/2022/12/memory-safe-languages-in-android-13.html
---

# Android 17 平台 Rust 性能边界：Binder、CXX 与 Soong

Rust 能减少部分内存安全风险，但不会自动消除 Binder、FFI、分配或调度成本。评估平台 Rust 服务时，应把语言运行时、CXX 边界、错误处理和 Soong 构建配置拆开，并以目标进程的实际调用路径验证。

## 结论

Rust 进入 Android 平台的主要目标，是减少新增 native（编译为设备机器码）代码中的内存安全缺陷。
语言迁移没有固定的性能方向：同进程 C ABI（C 二进制调用约定）边界可能只增加一次普通函数调用；跨进程 Binder 调用还要经过 Parcel 序列化、内核事务和线程调度。
字符串复制、所有权转换、锁竞争、分配器和代码体积也会改变结果。

AOSP `android-17.0.0_r1` 给出以下工程边界：

- Keystore2 与 VirtualizationService 是 Rust Binder 服务，直接使用 Rust AIDL backend（AIDL 的 Rust 代码生成后端）和 `libbinder_rs`，没有固定的 C++ AIDL 中转层。
- DnsResolver 仍是 C++ 与 Rust 混合模块。Rust 以 `libresolvrs_ffi` 静态 FFI（Foreign Function Interface，跨语言调用接口）库参与 DoH（DNS over HTTPS）、HTTP/3 和 DNS proxy 等部分，
  不能把整个 resolver 标成 Rust 服务。
- UWB 包含 Rust UCI（UWB Command Interface）core、packet 与 HAL adapter（硬件抽象层适配器）。Bluetooth 在 `system/rust` 下提供 `libbluetooth_rs`，
  并通过 CXX bridge（由 `cxx` 生成的 Rust/C++ 桥接层）接入现有 C++ 代码。它们都采用渐进式替换。
- 设备端 Rust 全局启用 `panic=abort`、整数溢出检查、强栈保护与 unwind table；ThinLTO（链接期的轻量级全程序优化）默认开启。这些配置比通用 Rust 项目的经验数字更适合解释 Android 17。
- 未自定义全局 allocator（内存分配器）的 Rust 标准库代码，通常经 libc `malloc/free` 进入设备配置的 native allocator。
  常规 Android 设备使用 Scudo，低内存产品仍可能采用其他实现；改用 Rust 不会消除分配器的安全成本。

文中不提供 “FFI 固定几十纳秒”“Rust 比 C++ 快或慢 5%”“二进制必然大 20%” 一类数字。
这些值取决于 CPU、工具链、优化级别、参数形态、调用频率、进程边界和负载，脱离可复现实验没有工程意义。

## 1. Android 平台怎样采用 Rust

### 1.1 版本目标

Android 12 开始在 AOSP 平台构建中正式支持 Rust，并同时引入 Rust AIDL backend。
Google 在 2021 年发布 Rust 支持时提到，内存不安全问题长期约占 Android 高严重性安全漏洞的 70%；这是当时漏洞结构的历史数据，不能直接当作 Android 17 的现状统计。

迁移策略侧重新增 native 代码，以及能够独立替换的组件。大规模逐行重写成熟 C/C++ 模块会增加功能回归、兼容性和验证成本，AOSP 因而长期保留混合语言结构。
FFI、Binder 与生成代码都是这种演进方式的组成部分。

Rust 的安全保证也包含运行时工作。所有权、生命周期与大部分借用规则在编译期检查；数组边界、整数溢出以及某些状态约束可能在运行期检查。
Android 17 Soong 对设备端 Rust 显式开启 `-C overflow-checks=on`，所以“安全检查全部在编译期完成”的说法与 r1 构建配置不符。

### 1.2 r1 中可核对的代表组件

| 组件 | r1 形态 | 主要跨语言或跨进程边界 |
|---|---|---|
| Keystore2 | `system/security/keystore2` 下的 `rust_binary` | Java/Native 客户端经 Binder 到 Rust AIDL 服务；Rust 再经 Binder 调 KeyMint 等 HAL |
| VirtualizationService | `packages/modules/Virtualization/android/virtualizationservice` 下的 `rust_binary` | Java/native 管理端经 Binder 到 Rust AIDL 服务，服务再管理 crosvm、VM 与内核接口 |
| DnsResolver | C++ resolver + `rust_ffi_static` 的 `libresolvrs_ffi` | CXX bridge 连接 C++ resolver 与 Rust DoH/HTTP3、DNS proxy 代码 |
| UWB | `packages/modules/Uwb/libuwb-uci` 中的 Rust packet、core 与 HAL adapter | Rust AIDL、Binder、JNI（Java Native Interface）与厂商 UCI HAL |
| Bluetooth | `packages/modules/Bluetooth/system/rust` 中的 `rust_ffi_static` | CXX bridge 连接 Rust LE Audio（低功耗蓝牙音频）/协议模块与既有 C++ stack |

这张表描述源码形态，不代表整项功能已经全部改为 Rust。
比如 DnsResolver 根目录仍有 `DnsResolverService.cpp`、`ResolverController.cpp`、`res_send.cpp` 等大量 C++；Bluetooth 的 Rust 库也作为现有 stack 的静态 FFI 组件构建。

r1 的 UWB 仓库位于 `packages/modules/Uwb`，Bluetooth Rust 代码位于 `packages/modules/Bluetooth/system/rust`。
`system/uwb`、`system/bt/gd/rust`、Rust 主体的 DnsResolver、Rust HTTP engine 与 Rust bpfloader 在 r1 源码树中找不到对应路径，不能计入“已完成重写”。

### 1.3 Keystore2 没有额外的 C++ AIDL 跳板

Keystore2 的 `Android.bp` 依赖 `libbinder_rs`，`KeystoreService` 在 Rust 中实现 `IKeystoreService`，进程启动后直接注册 native Binder 对象。下面两行展示服务创建和注册位置：

```rust
let ks_service = KeystoreService::new_native_binder(id_rotation_state)?;
binder::add_service(KS2_SERVICE_NAME, ks_service.as_binder())?;
```

代码省略了源码中的错误包装，只保留服务创建和注册结构。
Java framework 侧使用 AIDL proxy（客户端代理）发出一笔 Binder transaction，服务端由 Rust AIDL stub（服务端分发代码）接收。
`libbinder_rs` 构建在 `libbinder_ndk` 上，内部会经过 Rust/C ABI，但不会增加第二笔 Binder IPC，也不要求业务层先进入 C++ stub。

Keystore 操作常见的耗时来源包括 Binder 排队、数据库事务、SELinux 权限检查、KeyMint HAL、TEE（可信执行环境）/StrongBox 和远程密钥供应。
只测一个空 FFI 函数的纳秒值，无法解释生成密钥或签名请求的端到端时延。

## 2. 三类边界要分开分析

### 2.1 Rust AIDL 与 Binder

Rust AIDL backend 生成包含 proxy/stub 的 Rust crate（Rust 编译与依赖单元），并通过 `libbinder_rs` 使用稳定的 NDK Binder API。典型调用路径如下：

Java 或 native client → 语言对应的 AIDL proxy → Binder driver → Rust AIDL stub → Rust service

这条路径中的主要成本通常来自：

- Parcel 编码、对象与文件描述符处理；
- 用户态与内核态切换；
- 目标 Binder 线程被唤醒和排队；
- 大参数复制或共享内存映射；
- 服务端锁、数据库、文件系统或硬件调用；
- 回包与调用方重新调度。

Rust backend 的价值，是让服务端保留 Rust 类型和所有权模型，同时遵守 AIDL wire format（跨进程传输时的字段编码规则）。
它没有给 Binder transaction 增加新的进程跳转。性能分析应先测 transaction 的排队与执行，再判断生成代码和对象转换是否成为高占比路径。

### 2.2 Rust 与 C/C++ 的同进程 FFI

`extern "C"` 使用 C ABI，标量参数和 ABI 兼容结构体可按普通 native call 传递。成本风险来自边界两侧的工作：

- Rust 与 C/C++ 编译单元之间通常无法内联；
- 所有权、生命周期与异常约束需要人工设计；
- 字符串、容器、trait object（通过动态分派调用 trait 的对象）和 C++ 对象需要表示转换；
- 生成桥接代码可能做分支、长度校验、分配或析构；
- 回调频率过高会放大每次固定成本。

Soong `compiler.go` 对 `lto` 属性的注释明确写着：它控制最终 Rust 链接的 LTO，不影响 cross-language LTO（跨语言链接期优化）。
因此 r1 默认 ThinLTO 能优化 Rust crate 依赖图，却不能据此宣称 Rust/C++ 边界会被跨语言内联。

数据是否复制取决于接口形态。下面的 CXX bridge 例子用借用 slice 传递指针和长度：

```rust
#[cxx::bridge]
mod ffi {
    extern "Rust" {
        fn checksum(data: &[u8]) -> u64;
    }
}
```

这种接口可以避免为 payload（实际传入的数据）建立第二份字节数组，但调用期间 Rust 借用的内存必须保持有效。
若接口改成拥有所有权的 `String`、`Vec`、C++ `std::vector`，或要求以 NUL（值为 0 的终止字节）结尾的 `CString`，分配与复制策略会变化。

| 参数形态 | 常见实现 | 主要风险 |
|---|---|---|
| 整数、浮点、指针 | 直接按 ABI 传递 | 对齐、空指针与有效期 |
| `&[u8]` / `rust::Slice` | 指针 + 长度，通常可借用 | 生命周期与调用期并发修改 |
| `&str` / 字符串 view | 指针 + 长度 | UTF-8 与所有权约束 |
| `CString` / `const char *` | 检查内部 NUL，按构造方式决定是否分配 | 隐藏扫描、复制与释放方不一致 |
| Rust/C++ 容器 | bridge wrapper、逐项转换或转移所有权 | 循环调用、重复分配和异常语义 |
| opaque object（调用方看不到内部布局的对象） | `Box`、`UniquePtr` 或 handle | 析构方、线程安全与 use-after-free |

“字符串一定执行一次 malloc + memcpy”同样过度绝对。借用已有 `CStr` 可以不复制，`CString::new` 对拥有的数据则要检查内部 NUL，并可能产生新的分配。

### 2.3 Rust 与 Java 的 JNI

JNI 适合把同进程 Rust library 暴露给 Java/Kotlin。Soong 用 `rust_ffi_shared` 生成可动态加载的 `cdylib`（面向 C ABI 的共享库）。
Rust 可以借助 `jni` crate 直接导出 JNI symbol；只有既有接口或依赖要求时才需要 C++ wrapper。

JNI 成本应拆成：

- managed/native transition（Java 运行时与本机代码之间的切换）；
- local/global reference（JNI 局部/全局引用）管理；
- Java 字符串、数组与 Rust 类型的转换；
- native thread attach/detach（把本机线程接入或移出 Java VM）；
- Java exception 查询与转换；
- Rust 函数自身的工作。

大 payload 可以评估 direct `ByteBuffer`（Java 与 native 共享的直接缓冲区）、共享内存、文件描述符或批量接口。
纯 JNI 接口要限制对象生存期、单次延迟和取消粒度；数据还要继续跨 Binder 传输时，才需要额外考虑 Binder transaction 大小上限。

Keystore2 不是“Rust JNI 服务”的例子。它的公开系统服务入口是 Binder。把所有 Java→Rust 交互都画成 JNI，会把 IPC 成本和语言转换成本混为一项。

## 3. panic、错误与资源所有权

### 3.1 Android 17 设备端使用 `panic=abort`

`build/soong/rust/config/global.go` 为 device Rust 添加 `-C panic=abort`。
panic 触发时进程会直接终止，不会沿 C/C++ stack frame（调用栈帧）展开；`catch_unwind` 因此不能为这类设备构建提供进程内恢复策略。

FFI API 应把可预期失败编码为 `Result`、错误码、AIDL `Status` 或明确的 nullable/optional 返回值。
panic 只保留给违反内部不变量等不可恢复错误。C++ exception 也不应穿过未声明可 unwind 的 Rust ABI 边界。

`panic=abort` 没有让 r1 去掉所有 unwind metadata（描述怎样还原调用栈的信息）。
Soong 同时设置 `-C force-unwind-tables=yes`，用于栈回溯、采样和诊断，不能根据 panic 策略直接推算二进制缩小比例。

### 3.2 谁分配，谁释放

跨 FFI 传递拥有所有权的内存时，应明确：

- 分配使用哪个 allocator；
- 由哪一侧调用析构或 free；
- 对象能否跨线程；
- callback（反向回调）结束后引用是否失效；
- panic、early return（提前返回）或进程退出时怎样清理。

即便 Rust 与 C++ 最终都走同一份 Scudo，`Vec`、`String`、`std::vector` 和 C++ class 的析构规则仍不同。
常见做法是让创建对象的一侧导出配套 destroy 函数，或使用 CXX 的 `Box`/`UniquePtr` 约束所有权。

### 3.3 `unsafe` 是审核边界

Rust 无法证明裸指针、C ABI、设备寄存器与外部库满足安全条件。每个 `unsafe` block 或 `unsafe impl Send/Sync`（由开发者承诺类型可跨线程传递或共享）都应写明：

- 指针非空、对齐和长度的来源；
- 别名规则；
- 对象有效期；
- 调用线程要求；
- 回调重入条件；
- 外部函数可能修改哪些内存。

边界设计良好时，少量 `unsafe` 被封装在窄接口中，其余业务代码继续使用 safe Rust。把大段逻辑放入 `unsafe` 会减少迁移带来的安全收益，也会增加性能回归定位难度。

## 4. 运行时成本

### 4.1 分配器与 Scudo

没有设置 `#[global_allocator]` 的 Android Rust 标准库代码，默认通过系统分配器路径调用 libc `malloc/free`。
Android 官方 Scudo 文档说明，Android 11 起常规设备的 native 分配由 Scudo 提供，low-memory 设备仍使用 jemalloc；Android 17 的具体产品配置应以进程映射和设备构建为准。

Scudo 是 hardened allocator（强化防护的堆分配器），提供 chunk metadata 校验、隔离和 quarantine（延迟复用已释放内存块）等措施，发现可疑 heap 状态时可以终止进程。
它不是完整的 ASan（AddressSanitizer，内存错误检测器），也不会为每个小对象配置独立 guard page（不可访问的保护页）。
因此，“每块分配前后都有 guard page”和“释放后统一填随机 pattern”都不适合作为通用成本模型。

Rust 和 C++ 共用 native allocator 时，malloc 热点可以用 heapprofd 统一观察。以下情况需要单独处理：

- crate 使用自定义 `#[global_allocator]`；
- `no_std` 组件使用静态 arena（预留内存池）或专用 allocator；
- 对象来自共享内存、mmap 或硬件 buffer；
- 编译器优化消除了短命分配；
- 采样率太低，漏掉小而频繁的对象。

选择自定义 allocator 前要核对安全策略、APEX（可独立更新的系统模块容器）/进程边界、malloc 调试工具、heap profiler（堆采样器）与所有权协议。
若只因为一次 benchmark 中的 malloc 时延就替换系统 allocator，可能损失平台防护、诊断能力和跨模块一致性。

### 4.2 边界检查与溢出检查

Rust slice 索引可能生成 bounds check（越界检查），Android device build 还开启整数 overflow check（溢出检查）。LLVM 能在循环边界清晰时消除部分检查，但结果依赖代码形态。优化方向包括：

- 使用 iterator 或一次验证后的 slice 分段；
- 避免循环体内重复计算长度；
- 对确需 wrapping/saturating（回绕/饱和）语义的运算显式调用对应 API；
- 用 benchmark 和反汇编确认检查是否留在热点；
- 不用 unchecked 访问替代尚未量化的检查成本。

`get_unchecked` 可以移除 bounds check，也把越界责任交给调用者。只有 profiler 和反汇编都证明检查位于高占比热点、且不变量能被测试与审核覆盖时，才有评估价值。

### 4.3 锁、原子与 async

`Arc<Mutex<T>>` 组合了跨线程引用计数与互斥锁，它的成本没有统一纳秒值。
未竞争锁、跨核竞争、优先级反转和持锁 I/O 是不同问题；`std::sync::Mutex`、Tokio async mutex 与 Binder thread pool（处理 Binder 请求的线程池）的调度语义也不同。

分析系统服务时应关注：

- 锁等待时间和持锁区间；
- Binder thread pool 是否耗尽；
- async executor（异步任务执行器）是否被阻塞式 syscall（系统调用）卡住；
- callback 是否回到持锁对象；
- atomic refcount（原子引用计数）是否在跨核高频路径中反复争用同一 cache line；
- channel（任务间消息队列）是否积压并造成内存增长。

safe Rust 的类型规则可以阻止数据 race（多个线程无同步地读写同一内存），无法自动消除业务层死锁、队头阻塞和优先级反转。

### 4.4 代码体积与 i-cache

泛型单态化（为每个具体类型生成一份代码）、内联、async state machine、格式化和错误上下文都可能扩大 ELF 的 `.text` 代码段。

动态链接可以共享代码页；静态 rlib（Rust 静态依赖格式）则让 ThinLTO 删除未使用代码并跨 crate 优化。
两种策略的文件体积、PSS（按比例分摊共享页的进程内存指标）、启动 relocation（动态重定位）和 i-cache（指令缓存）行为需要分别测量。

Android 17 r1 的 Soong 默认开启 Rust ThinLTO。Keystore2 又显式设置 `prefer_rlib: true`，源码注释给出的理由是：当时 `/system` 上使用动态 Rust 的进程数量不足，动态共享未产生预期收益。
这是按组件计算的取舍，不能推广成所有 Rust 服务都应静态或动态链接。

r1 的几个全局编译选项可从 `build/soong/rust/config/global.go` 直接核对。下面只列与本节相关的四项：

```text
-C opt-level=3
-C overflow-checks=on
-C force-unwind-tables=yes
-C panic=abort
```

优化级别、溢出检查和回溯信息会同时影响性能与体积。发布设备模块默认 strip（移除）大部分符号并保留 mini debuginfo。
分析产物大小时要区分 unstripped、stripped、磁盘文件页和运行时私有页。

## 5. Soong 中容易写错的部分

### 5.1 模块类型

| 模块 | 产物与用途 |
|---|---|
| `rust_binary` | Rust 可执行文件 |
| `rust_library` | 同时提供 rlib 与 dylib variant，供 Rust 模块依赖 |
| `rust_ffi` | 同时构建 shared `cdylib` 与供后续静态 FFI 链接使用的 `rlib` variant |
| `rust_ffi_shared` | 只构建 shared `cdylib`，适合 JNI 等需要动态加载的场景 |
| `rust_ffi_static` | 只构建 `rlib`，供最终 C/C++ 静态链接步骤使用 |
| `rust_bindgen` | 从 C header 生成 Rust binding crate |
| `rust_proc_macro` | 过程宏 |
| `aidl_interface` 的 Rust backend | 生成 Rust AIDL crate，供 `rustlibs` 引用 |

`rust_ffi_static` 并不直接产出通用 Rust `staticlib`。
r1 的 `library.go` 实际把它注册到 `RustLibraryRlibFactory`，注释也写明该 rlib 会留到最终 C/C++ 静态链接步骤处理。这是 Soong 的实现约定。

`rust_dylib` 不是 r1 注册的 Soong 模块类型。需要强制使用 Rust dylib variant 时可使用 `rust_library_dylib`；一般 Rust 依赖优先写入 `rustlibs`，由构建系统选择兼容的 linkage（静态或动态链接方式）。

### 5.2 ThinLTO 语法与默认值

`lto` 是一个属性组，合法形式是 `lto: { thin: true }` 或 `lto: { thin: false }`。r1 默认值已经是 `true`，常规生产模块无须重复声明。`lto: "thin"` 与该 tag 的属性类型不符。

Soong 注释指出 ThinLTO 对 Rust code size 收益很大，生产构建若要关闭需要清楚理由。
sanitizer（运行时错误检测）、fuzz（模糊测试）、构建时间或工具兼容性可能要求例外；应通过最终 rustc command 和产物指标确认，不能只读一段 Blueprint（`Android.bp` 使用的描述语言）。

### 5.3 第三方 crate 管理

Android 17 的 crates.io 导入集中在 `external/rust/android-crates-io` 仓库，各 crate 位于 `crates/<name>/` 子目录。每个目录可包含 `cargo_embargo.json`、Android 补丁、许可证元数据和生成的 `Android.bp`。

仓库根目录的 `crate_tool` 是入口脚本：它通过 AOSP 预置 Cargo 调用 `development/tools/external_crates` 中的 Rust CLI。
该工具的 `import`/`regenerate` 子命令负责 vendor crate（把依赖源码固定复制进受管仓库）、按顺序应用补丁、检查许可证，并调用 `cargo_embargo` 生成或更新 `Android.bp`。

这套流程不使用 `external/upstream` 与 `development/tools/regex_gen_cargo2android.py`。
平台开发不能把 `cargo build` 的依赖解析结果直接带入系统镜像；crate 版本、license、patch、Soong rule、APEX 可用性和测试都要进入 AOSP 管理。

## 6. 怎样测 Rust 边界

### 6.1 先定义要回答的问题

一个有效实验只回答一个主要问题，例如：

- 一次 CXX bridge 的固定成本是多少？
- 1 KiB、64 KiB、1 MiB payload 的转换是否复制？
- Java→Rust Binder 与 Java→C++ Binder 在等价空服务中的差异是多少？
- Rust 服务的 CPU 时间花在 bridge、锁、allocator、Binder 或业务代码中的哪一项？
- static Rust std 与 dynamic linkage 对文件体积、PSS 和启动 relocation 有什么影响？

“Rust 服务快不快”缺少可操作边界。先固定业务语义、输入、线程数、CPU affinity（把线程限制到指定 CPU）、编译配置和设备温度，再决定工具。

### 6.2 同进程 FFI microbenchmark

为 C++→Rust 与纯 C++/纯 Rust 各写语义相同的 benchmark，至少覆盖：

- 标量空调用；
- 借用 slice；
- owned string/vector；
- Rust→C++ callback；
- 错误返回；
- 单线程与并发；
- 多种 payload 大小。

统计每次调用的 cycles（CPU 周期）、instructions、branch misses（分支预测失败）、allocation count 和复制字节。
空调用用于估计每次调用的固定开销，业务 payload 用于判断固定开销在总耗时中的占比。

两侧产物要使用相同优化级别，不能让一侧保留断言或日志、另一侧关闭。

### 6.3 Binder 端到端

Perfetto 中建议同时抓：

- `sched_switch` / thread state（线程运行、可运行与睡眠状态）；
- Binder transaction 与目标线程；
- CPU frequency、idle 与 thermal；
- process/thread runtime；
- 服务内部自定义 trace slice；
- 文件系统或硬件调用。

Binder 测试要记录五段时间：client 发起请求、driver 排队、server 进入 runnable（可运行但仍可能等待 CPU）、server 执行，以及 reply 返回。
只在服务函数入口计时会漏掉调用方阻塞和调度延迟。

### 6.4 CPU 采样

在 userdebug/eng 或具备相应 profiling 权限的设备上，可用下面的命令观察 Keystore2 的事件计数与调用栈：

```bash
keystore_pid=$(adb shell pidof keystore2)
adb shell simpleperf stat -p "$keystore_pid" \
  --duration 10 -e task-clock,cpu-cycles,instructions,branch-instructions,branch-misses
adb shell simpleperf record -p "$keystore_pid" \
  --duration 10 --call-graph fp -o /data/local/tmp/keystore2.data
```

`keystore_pid` 保存在主机 shell 中，再作为 `simpleperf` 参数传入设备。
系统服务的 attach（附加采样）权限受 build type、SELinux 和 simpleperf 策略限制；user build 上附加失败，只能说明权限或构建条件不满足。

Soong 使用 Rust v0 symbol mangling（把函数签名编码进链接符号名），并保留 unwind table。
Simpleperf/Perfetto 报告仍要核对是否成功加载对应符号。
看见大量十六进制地址时，应先修正 symbol path 和 build ID（唯一标识该 ELF 构建的值），不能把采样归到“unknown”后继续比较语言。

### 6.5 文件体积、链接与 PSS

下面的主机和设备命令分别检查 ELF section、动态依赖与进程映射：

```bash
llvm-size -A out/target/product/<product>/system/bin/keystore2
llvm-readelf -d out/target/product/<product>/system/bin/keystore2
keystore_pid=$(adb shell pidof keystore2)
adb shell showmap "$keystore_pid"
```

`llvm-size` 反映 ELF section（代码、数据等分段）大小，`llvm-readelf` 可确认 Rust std 与其他库采用何种 linkage，`showmap` 反映运行时映射。

三者不能互相替代：磁盘文件更大不等同于私有 RSS 更大，动态库页也可能在多个进程间共享。PSS（Proportional Set Size）会按比例分摊共享页，更适合与 RSS 一起报告。
读取系统服务映射可能需要 userdebug/eng、root 或额外调试权限。

### 6.6 native heap

heapprofd 能观察经过 malloc/free 的 Rust 分配。配置采样时要记录 interval（每次采样覆盖的分配字节间隔）、持续时间、进程启动阶段和符号版本，并确认目标没有使用自定义 allocator。

对高频小对象可同时加入源码计数器或 allocator benchmark，避免采样误差掩盖短命分配。

## 7. 优化顺序

### 7.1 先处理架构级成本

优先级通常如下：

1. 减少不必要的 Binder transaction 与 callback 往返。
2. 缩短持锁区，移出数据库、文件和硬件 I/O。
3. 避免 payload 的重复编码与复制。
4. 控制 executor、Binder pool 和 channel 背压（生产速度超过消费速度时限制继续入队）。
5. 减少热点分配和跨核原子写。
6. 在证据充分时调整 bridge 表示、linkage 或 compiler 配置。

如果 Binder 排队或硬件操作占据大部分端到端时间，减少一次普通 call instruction 对总耗时的影响会很小。
只有 profiler 已显示 bridge 占比高时，才值得评估批量调用、借用数据或 ownership transfer（跨边界移交对象所有权）；其余情况先处理占比更高的部分。

### 7.2 接口设计

- 用稳定的 C ABI、AIDL 或 CXX 明确边界，不暴露 Rust 私有布局。
- 对 buffer 使用 pointer+length 或受支持的 slice wrapper，并写清生命周期。
- 让创建对象的一侧负责销毁，导出显式 destroy API。
- 批量 API 要设置大小上限、取消语义和背压策略。
- callback 中避免持有外层锁。
- 预期错误使用 `Result`/Status，panic 留给内部不变量破坏。
- 为所有 `unsafe` 前置条件写测试、fuzz case 与注释。

### 7.3 构建与观测

- 保留 Soong 默认 ThinLTO，除非构建或测量证明需要关闭。
- 用 `rustlibs` 让 Soong 选择 linkage；`prefer_rlib` 应带组件级体积/PSS 依据。
- 保留 build ID 和对应符号文件，验证 Rust v0 demangle（把编码符号还原为可读函数名）。
- 将二进制体积、PSS、启动时延、CPU、allocator 与 Binder 指标分开。
- 对版本升级重新测量，rustc、LLVM、Scudo 与 crate 更新都会改变结果。

## 8. 常见误判

| 说法 | r1 证据下的修正 |
|---|---|
| Rust FFI 是零成本 | C ABI 调用可很轻，跨语言内联、转换、析构和 callback 仍有成本 |
| Keystore2 每次调用经过 JNI→C++ AIDL→Rust | Java AIDL proxy 经一笔 Binder IPC 到 Rust AIDL 服务；业务层没有固定 C++ stub |
| DnsResolver 已由 Rust 完整重写 | r1 是 C++ resolver 与 `libresolvrs_ffi` 混合 |
| 所有字符串跨 FFI 都 malloc + memcpy | 借用 view 可以零复制，owned/NUL-terminated 转换按接口决定 |
| panic 可以在 FFI 入口用 `catch_unwind` 恢复 | device Rust 全局 `panic=abort`，panic 会终止进程 |
| `panic=abort` 会删除 unwind table | r1 同时强制生成 unwind table |
| Rust 分配不受 Scudo 影响 | 默认 System allocator 经 libc malloc，仍由设备 native allocator 服务 |
| Scudo 给每个对象放 guard page | Scudo 使用多种 hardened heap 机制，不等于逐对象 guard page |
| ThinLTO 需要写 `lto: "thin"` 才开启 | r1 默认开启，属性结构为 `lto: { thin: ... }` |
| Rust 服务性能可用固定百分比概括 | 需要按 IPC、FFI、分配、锁、代码体积和业务 I/O 分项测量 |

## 9. 版本边界

| Android 版本 | 与平台 Rust 相关的节点 |
|---|---|
| Android 12 / API 31 | AOSP 正式支持平台 Rust；Rust AIDL backend 引入；Keystore2 成为代表组件 |
| Android 13 / API 33 | 官方当时报告约 21% 的新增 native 代码使用 Rust，AOSP Rust 约 150 万行；案例包括 Keystore2、UWB、DNS-over-HTTP/3 与 AVF |
| Android 14～16 / API 34～36 | Rust 在 Mainline（可独立更新的系统模块）、虚拟化、连接与底层组件中继续扩展，混合语言边界仍然存在 |
| Android 17 / API 37 | `android-17.0.0_r1` 中可核对 Rust Binder 服务、CXX 混合模块、默认 ThinLTO、panic/overflow/unwind 配置与新 Bluetooth Rust 组件 |

这里不讨论内核 Rust 配置或驱动，也不能从平台用户态模块推导 `android17-6.18-2026-06_r6` 的内核能力。
分析 Rust for Linux 时，需要另行核对该 kernel tag 的 Kconfig（内核配置）、toolchain、bindings 和具体驱动。

## 源码与官方资料

固定 tag 的目录索引：

- [Keystore2](https://android.googlesource.com/platform/system/security/+/refs/tags/android-17.0.0_r1/keystore2/)
- [DnsResolver](https://android.googlesource.com/platform/packages/modules/DnsResolver/+/refs/tags/android-17.0.0_r1/)
- [UWB Rust](https://android.googlesource.com/platform/packages/modules/Uwb/+/refs/tags/android-17.0.0_r1/libuwb-uci/src/)
- [Bluetooth Rust](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/system/rust/)
- [VirtualizationService](https://android.googlesource.com/platform/packages/modules/Virtualization/+/refs/tags/android-17.0.0_r1/android/virtualizationservice/)
- [Soong Rust](https://android.googlesource.com/platform/build/soong/+/refs/tags/android-17.0.0_r1/rust/)
- [Keystore2 Android.bp：Rust binary、libbinder_rs、prefer_rlib 与 AFDO](https://android.googlesource.com/platform/system/security/+/refs/tags/android-17.0.0_r1/keystore2/Android.bp)
- [Keystore2 main：Rust Binder 服务注册](https://android.googlesource.com/platform/system/security/+/refs/tags/android-17.0.0_r1/keystore2/src/keystore2_main.rs)
- [Keystore2 service：Rust 实现 IKeystoreService](https://android.googlesource.com/platform/system/security/+/refs/tags/android-17.0.0_r1/keystore2/src/service.rs)
- [DnsResolver root Android.bp：C++ resolver 使用 Rust FFI defaults](https://android.googlesource.com/platform/packages/modules/DnsResolver/+/refs/tags/android-17.0.0_r1/Android.bp)
- [DnsResolver rust Android.bp：libresolvrs_ffi 与 CXX bridge](https://android.googlesource.com/platform/packages/modules/DnsResolver/+/refs/tags/android-17.0.0_r1/rust/Android.bp)
- [UWB Rust core 与 HAL adapter](https://android.googlesource.com/platform/packages/modules/Uwb/+/refs/tags/android-17.0.0_r1/libuwb-uci/src/Android.bp)
- [Bluetooth Rust library 与 FFI module](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/system/rust/Android.bp)
- [VirtualizationService Rust binary](https://android.googlesource.com/platform/packages/modules/Virtualization/+/refs/tags/android-17.0.0_r1/android/virtualizationservice/Android.bp)
- [libbinder_rs：Rust Binder 对 libbinder_ndk 的依赖](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/binder/rust/Android.bp)
- [Soong Rust global flags](https://android.googlesource.com/platform/build/soong/+/refs/tags/android-17.0.0_r1/rust/config/global.go)
- [Soong Rust LTO 属性与默认值](https://android.googlesource.com/platform/build/soong/+/refs/tags/android-17.0.0_r1/rust/compiler.go)
- [Soong Rust library 模块类型](https://android.googlesource.com/platform/build/soong/+/refs/tags/android-17.0.0_r1/rust/library.go)
- [Android Rust introduction](https://source.android.com/docs/setup/build/rust/building-rust-modules/overview)
- [Android Rust modules](https://source.android.com/docs/setup/build/rust/building-rust-modules/android-rust-modules)
- [AIDL backends](https://source.android.com/docs/core/architecture/aidl/aidl-backends)
- [Scudo](https://source.android.com/docs/security/test/scudo)
- [Rust in the Android platform](https://security.googleblog.com/2021/04/rust-in-android-platform.html)
- [Memory Safe Languages in Android 13](https://security.googleblog.com/2022/12/memory-safe-languages-in-android-13.html)
- [android-crates-io 与 crate_tool](https://android.googlesource.com/platform/external/rust/android-crates-io/+/refs/tags/android-17.0.0_r1/README.md)
- [crate_tool 子命令与调度入口](https://android.googlesource.com/platform/development/+/refs/tags/android-17.0.0_r1/tools/external_crates/crate_tool/src/main.rs)

## 相关章节

- [1.3 Android IPC 全景与 Binder 性能](../../part1-fundamentals/ch01-architecture/03-ipc-binder-performance.md)：补充 Binder transaction、线程池与 Parcel 成本。
- [1.18 Android 17 AVF 架构与 pKVM 隔离性能边界](../../part1-fundamentals/ch01-architecture/18-virtualization-framework-pkvm-performance.md)：补充 VirtualizationService 与内核虚拟化边界。
- [3.6 键盘、鼠标与指针输入性能 — 桌面模式交互管线](../../part1-fundamentals/ch03-input/06-keyboard-mouse-pointer-input-performance.md)：其中的 InputFlinger Rust 键盘 filter 是另一个渐进式 Rust 组件案例。
- [1.10 JNI、NDK 与 Bionic 原生运行时性能](../../part1-fundamentals/ch01-architecture/10-jni-ndk-bionic-performance.md)：补充 libc malloc、动态链接与 Scudo 接口。
- [14.2 Simpleperf 与 ARM Topdown 微架构分析](../../part3-tools/ch14-other-tools/02-simpleperf-arm-topdown.md)：补充 native CPU 采样和 PMU 事件。
- [20.10 Android 17 Keystore 密钥配额与登录恢复](../../part5-app/ch20-stability/10-keystore-quota-login-stability.md)：补充 Keystore2 业务与稳定性诊断。
