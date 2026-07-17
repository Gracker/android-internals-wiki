---
title: "Native SO 体积优化实战"
chapter: "25.30"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [native, so, elf, strip, ndk, abi, 16kb-page-size, apk-size]
related_chapters: ["25.6", "25.8", "1.55", "1.58", "20.13"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-17"
gap_source: "Clippings参考书驱动"
confidence: medium
---

# 25.30 Native SO 体积优化实战

<!-- outline-start -->
## 要点

### 🔹 SO 文件结构与体积来源
- ELF 格式概览：ELF header、program headers、section headers、symbol table、string table
- `.text`（代码段）、`.rodata`（只读数据）、`.data`/`.bss`（可写数据）、`.debug_*`（调试段）
- 体积分布分析工具：`readelf -S`、`objdump -h`、`size` 命令
- [结构参考: Clippings/Android 应用稳定性剖析与优化 - ELF 文件与 readelf & objdump.md]

### 🔹 Strip 与符号表管理
- `strip` 移除 `.symtab` / `.strtab` 的体积收益
- `--strip-debug` vs `--strip-all`：保留动态符号 vs 全部移除
- 本地保留 unstripped SO 用于 Crash 符号化（`ndk-stack` / `addr2line` 依赖）
- 构建系统配置：`Android.mk` / `CMakeLists.txt` 中 `STRIP` 选项
- [待验证: NDK r28 默认 strip 行为]

### 🔹 ABI 过滤与按需下发
- `abiFilters` 配置：只打包目标架构（arm64-v8a 为主）
- 主流架构取舍：arm64-v8a 覆盖 99%+ 设备，是否保留 armeabi-v7a
- App Bundle 按 ABI 拆分 + 动态下发
- APK 瘦身收益量化：单 ABI vs 多 ABI 的体积差异
- 详见 25.8 节

### 🔹 编译器体积优化选项
- `-Os`（优化体积）vs `-O2`（优化速度）vs `-O3`
- `-ffunction-sections` + `-fdata-sections` + `--gc-sections`：剔除未引用的函数和数据
- `-fvisibility=hidden`：隐藏非导出符号，减小导出表
- `-flto`（Link-Time Optimization）：跨文件内联与死代码消除
- LTO 对体积的实际收益与编译时间代价
- [待验证: Clang 18 在 Android NDK r28 中的默认优化级别]

### 🔹 Version Script 与符号导出控制
- `--version-script` 限定动态导出符号清单
- 只导出 JNI 入口函数（`Java_*`）和必要的 C API
- 对 `.dynsym` 表大小的直接影响
- 示例：从全量导出到白名单导出的体积差异

### 🔹 16KB Page Size 对齐对 SO 体积的影响
- Android 17 强制要求 Native 库 16KB 对齐 [已验证: 官方文档, developer.android.com/guide/practices/page-sizes]
- `ALIGN` 增大导致 `.text` 段尾部 padding 增加
- 小型 SO 的 padding 占比可高达 5-15%
- `-Wl,-z,max-page-size=16384` 配置
- 对现有 SO 的影响评估与迁移策略
- 详见 20.13 节

### 🔹 重复 SO 检测与去重
- 多 SDK 依赖相同 Native 库（如 libc++_shared.so）的重复打包
- `checkDup SOs` 工具与 Gradle 插件检测
- `pickFirst` 策略与版本兼容风险
- Native 依赖统一管理方案

### 🔹 动态加载与按需加载策略
- `System.loadLibrary` 与 `dlopen` 延迟加载
- 功能模块化：将低频功能拆分为独立 SO 按需下载
- 插件化方案中 SO 的加载路径管理
- 安全限制：Android 17 对动态加载 SO 的安全约束 [待验证]

### 🔹 包体积监控中的 SO 治理
- SO 体积 CI 门禁：单 SO 超阈值告警
- SO 依赖树可视化：`readelf -d` 分析 NEEDED 依赖
- SO 变更追踪：版本间体积 diff 报告

## 扩展

### 🔸 Assembly 代码体积优化
- ARM64 NEON 指令对代码体积的影响
- 内联汇编 vs 独立 `.S` 文件的体积差异
- Thumb-2 vs ARM64 指令编码密度对比（仅历史参考）

### 🔸 Debug 符号分离与远程符号化
- 构建产物分离：stripped SO 打入 APK，unstripped SO 上传符号服务器
- Crash 堆栈符号化流程：`ndk-stack` + mapping
- `llvm-symbolizer` 与 `addr2line` 的选择

### 🔸 LLVM / Clang 工具链进阶
- `opt` 优化管线与 Pass 管理
- `BOLT`（Binary Optimization and Layout Tool）后链接优化
- Post-link 优化的体积收益 [待验证: Android NDK 可用性]

<!-- outline-end -->

> 本节内容待加工。
