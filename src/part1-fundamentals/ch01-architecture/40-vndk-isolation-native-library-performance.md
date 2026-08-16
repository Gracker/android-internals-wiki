---
title: "Android 17 VNDK 隔离与 native 库加载性能影响"
chapter: "1.40"
section: "1.40"
status: finalized
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [vndk, linker, native-library, dlopen, namespace, performance, self-contained-hal]
related_chapters: ["1.1", "1.50"]
last_verified: "2026-08-06"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
last_body_apply_at: "2026-08-06T13:15:32+08:00"
last_body_apply_run_id: "20260806-131532-f1fcd970"
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
last_review_finalize_at: "2026-08-06T14:07:19+08:00"
last_review_finalize_run_id: "20260806-140539-50b252ca"
sources:
  - type: aosp
    path: "bionic/linker"
  - type: aosp
    path: "system/linkerconfig"
  - type: official
    path: "https://source.android.com/docs/core/architecture/vndk"
  - type: official
    path: "https://source.android.com/docs/core/architecture/vndk/linker-namespace"
---

# 1.40 Android 17 VNDK 隔离与 native 库加载性能影响

## 一、Android 17 的 VNDK 边界

VNDK（Vendor Native Development Kit）曾规定 vendor 原生代码可以使用哪些 framework 原生库，以便系统框架与厂商实现分别升级。VNDK 从 Android 15 开始弃用。`vendor` 或 `product` 分区面向 Android 15 及以上版本构建时，原 VNDK 库与其他可用库一样安装到对应分区，不再生成当前版本的 VNDK APEX，`ro.vndk.version` 与 `ro.product.vndk.version` 也被移除。

两类兼容边界仍要保留：

- VNDK 版本 14 及以下的 APEX 继续用于支持旧 vendor image，也就是保留旧厂商分区镜像运行所需的对应版本库；
- LL-NDK（底层原生接口库集合）不属于 VNDK，其稳定 ABI 仍用于 `system`/`vendor` 边界。ABI 指已经编译的二进制之间必须一致的函数调用、数据布局和符号约定。

因此，Android 17 新设备的库隔离不能继续描述为“当前 VNDK APEX 执行五级检查”。VNDK 的历史版本兼容、Soong 构建系统生成 `vendor` 变体的规则、动态链接器的 namespace 和 SELinux 是彼此相邻却各自独立的机制，生命周期也不同。

### “Self-contained HAL”不是新的 linker 模式

旧 VNDK 文档要求 VNDK-SP（可安全加载进 framework 进程的一组 VNDK 库）及 SP-HAL（同样会被 framework 进程加载的 vendor HAL）依赖集合满足自包含约束，避免加载 `vendor` HAL 时继续依赖不允许进入该进程的厂商私有库。Android 17 的 Bionic 中没有名为“Self-contained HAL”的新 namespace 类型、`dlopen()` 标志或预加载调度器。

把 HAL 及依赖放在 `vendor`/`product` 侧，是构建与部署约束。静态链接多少库、是否采用 AIDL HAL、哪些库由 LL-NDK 提供，要由模块定义、稳定接口要求和升级边界决定。“自包含”不会自动减少动态库数量，平台也没有承诺由此获得固定的启动收益。

## 二、linker namespace 仍是运行时隔离基础

Android 11 起，`linkerconfig` 根据分区、已安装 APEX、公开库和运行时环境生成 `/linkerconfig/ld.config.txt` 及相关配置。动态链接器读取配置后，为进程建立 default、APEX、`vendor`、SP-HAL 等所需 linker namespace。namespace 是一组库搜索和可见性规则；namespace link 则声明可以跨边界访问哪些 soname，soname 是 ELF 共享库记录的逻辑名称，例如 `libfoo.so`。

一个进程可以有多个 namespace。每个 namespace 保存自己的搜索路径、许可路径、允许库名和到其他 namespace 的链接。跨 namespace 的库查找只会沿配置好的 link 继续，且通常只允许指定的共享库 soname。

应用还会由 `libnativeloader` 为各 ClassLoader 创建对应的 native namespace。系统原生进程、应用 JNI、APEX 进程和 `vendor` 守护进程的 namespace 关系图并不相同，不能从一个进程的 `LD_LIBRARY_PATH` 推断整台设备的库可见性。

## 三、`is_accessible()` 的准确语义

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

### 搜索路径和许可路径回答不同问题

`ld_library_paths_` 与 `default_library_paths_` 参与按 soname 搜索。`permitted_paths_` 允许 isolated namespace 通过绝对路径访问额外目录，但不会自动把目录加入 soname 搜索顺序。把路径加入 permitted 列表，只表示某个绝对路径可能通过可访问性检查，不表示 `dlopen("libfoo.so")` 会从那里找到库。

`LD_LIBRARY_PATH` 只在非 secure execution 环境读取；secure execution 指动态链接器因进程具有特殊权限等安全条件而忽略部分环境变量。该变量只作用于 default namespace 的对应搜索路径。Android 17 Bionic 没有名为 `LOADER_PATH` 的同类环境变量。系统进程和应用还受启动环境、namespace 配置与公开库规则限制。

## 四、符号可见性怎样限制

库文件能够装入某个 namespace，只说明它通过了路径层检查。重定位（把代码中的符号引用绑定到实际地址）与 `dlsym()` 查找还受下面几组范围影响：

- 本 namespace 的 global group（全局可参与解析的库）与 local dependency group（从当前库出发可达的局部依赖）；
- 共享或次级 namespace 的成员关系；
- namespace link 是否允许该 soname；
- ELF 符号可见性、控制导出符号的 version script、`RTLD_LOCAL`、`RTLD_GLOBAL` 与 `DF_1_GLOBAL`；
- 目标库的 `DT_NEEDED` 依赖能否继续解析。

同名库可以分别存在于不同 namespace，减少 framework/vendor 或 APEX 之间意外解析到对方符号的情况。namespace 也允许显式导出少量稳定库。`dlopen()` 和 `dlsym()` 仍是 Bionic API，没有额外的“安全包装器”自动解决 ABI 不兼容或对象跨版本传递问题。

## 五、`dlopen()` 时间花在哪里

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

## 六、如何测量加载性能

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

## 七、Android 17 排障顺序

遇到 `dlopen failed` 时，可按错误信息依次确认：

1. 请求从哪个 namespace 发起，调用方属于哪个 ClassLoader、APEX 或 vendor 进程；
2. soname 是否在当前 namespace 的搜索路径中，或被相连 namespace 的允许列表放行；
3. 绝对路径是否通过 allowed libs 与 permitted paths；
4. `DT_NEEDED` 中是否存在跨分区私有依赖；
5. ELF 位数、ABI、页大小对齐、符号版本和重定位类型是否兼容；
6. 文件权限、SELinux denial、分区挂载和 APEX 激活状态；
7. 库是否带有耗时或有线程约束的 constructor。

错误信息中的 “not accessible for the namespace” 属于 linker namespace 边界；“library not found” 也可能表示某个依赖库没有找到；“cannot locate symbol” 则说明已经进入符号解析阶段。三者需要不同修复，扩宽 `permitted_paths_` 不会修复缺失符号或 ABI 不兼容。

## 八、源码与官方边界

- [VNDK overview 与弃用说明](https://source.android.com/docs/core/architecture/vndk)：Android 15 起的弃用范围、旧 VNDK APEX 与 LL-NDK 例外。
- [linker namespace 官方说明](https://source.android.com/docs/core/architecture/vndk/linker-namespace)：namespace 图、search/permitted path 与 linkerconfig 的历史边界。
- [linker_namespaces.cpp @ android-17.0.0_r1](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/linker/linker_namespaces.cpp)：路径与符号可访问性。
- [linker.cpp @ android-17.0.0_r1](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/linker/linker.cpp)：库搜索、装载、namespace link、relocation 与 `dlopen()` trace。
- [linker_logger.cpp @ android-17.0.0_r1](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/linker/linker_logger.cpp)：`debug.ld.*` 选项及 dumpable 限制。
- [linkerconfig README @ android-17.0.0_r1](https://android.googlesource.com/platform/system/linkerconfig/+/android-17.0.0_r1/README.md)：运行时配置输入、APEX public libraries 与输出文件。

## 九、版本范围

版本边界固定为 Android 17/API 37 与 `android-17.0.0_r1`。Android 17 的 linker namespace、VNDK 弃用说明和 Perfetto/linker logger 行为不能外推为后续平台能力。
