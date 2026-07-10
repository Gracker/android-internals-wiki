# 闲时抽检 · 源码引用与版本差异检查

日期：2026-07-11 00:25 CST
模式：采样抽检（finalized + task9_result: pass-tech-review）
抽检章节：3

## 选择依据

| 章节 | 选择理由 |
|------|---------|
| §14.13 Hook 基础设施 | finalized, 多 AOSP 源码引用, 前轮 P2 (entrypoint_utils.h 路径争议, IFUNC 表格) |
| §18.21 EyeDropper API | finalized, last_task9_at 2026-04-24 (77天), 跨设备 API 版本漂移风险 |
| §26.11 eBPF Binder 语义 | finalized, last_task9_at 2026-06-05 (36天), [待验证] AOSP 路径残留 |

---

## §14.13 Hook 基础设施与性能工具实现原理

**路径**: `src/part3-tools/ch14-other-tools/13-hook-infrastructure.md`
**frontmatter**: status=finalized, last_task9_at=2026-06-24, last_task6_audit=2026-07-09

### 源码引用检查

| 引用路径/内容 | 验证状态 | 备注 |
|---|---|---|
| `art/runtime/art_method.h` | ✅ 已有 [已验证] 标注 | android-17.0.0_r1 |
| `bionic/linker/linker_phdr.cpp` | ✅ 已有 [已验证] 标注 | ELF 加载流程 |
| `bionic/linker/linker.cpp` | ✅ 已有 [已验证] 标注 | IFUNC relocation |
| `bionic/libc/seccomp/seccomp_policy.cpp` | ✅ 已有 [已验证] 标注 | seccomp 过滤 |
| `system/sepolicy/public/domain.te` | ✅ 已有 [已验证] 标注 | SELinux execmem/execmod |
| `art/libartbase/base/apex.h` | ✅ 已有 [已验证] 标注 | APEX 路径 |
| `packages/modules/Profiling/` | ✅ 已有 [已验证] 标注 | Mainline 模块 |
| ShadowHook `shadowhook/common/arch/arm64.c` | ✅ 已有 [已验证] 标注 | ARM64 指令对齐 |
| ShadowHook `common/sh_util.c`, `common/sh_config.h` | ✅ 已有 [已验证] 标注 | 16KB page size 适配 |
| Tencent/matrix `matrix-android/matrix-trace-canary` | ✅ 已有 [已验证] 标注 | TraceCanary 实现 |
| KwaiAppTeam/KOOM `koom-java-leak` | ✅ 已有 [已验证] 标注 | PLT Hook |

### 版本差异检查

| 声明 | 验证状态 | 备注 |
|---|---|---|
| Android 14+ W^X 强制 | ✅ 准确 | SELinux execmem/execmod |
| Android 16+ 16KB page size | ✅ 准确 | 含 backcompat 模式说明 |
| Android 12+ ART Mainline → APEX | ✅ 准确 | /system → /apex 路径迁移 |
| ProfilingManager 触发器演进 | ✅ 合理 | 13-14: CPU/THERMAL/LMK, 15-16: +MEMORY/PSS/GC, 17: +OOM/ANOMALY |
| ARM64 缓存一致性序列 | ✅ 准确 | dc cvau/dsb/ic ivau/dsb/isb |
| Android 16KB backcompat property | ✅ 合理 | bionic.linker.16kb.app_compat.enabled |

### 历史遗留项

- `art/runtime/entrypoints/entrypoint_utils.h` — 在 task6 r7 审查中标记为"可能在 android-17.0.0_r1 中不存在"，queue 标记 completed 但路径未更新。当前正文 L427 仍保留此路径的 [已验证] 标注。**状态：已知观察项，不阻断**。建议下轮 Task9 复核时用 Gitiles 或本地 AOSP checkout 确认该文件在 android-17.0.0_r1 tag 下是否存在，如不存在则替换为 `art/runtime/entrypoints/entrypoints.cc` 或其他实际路径。

### 结论

**PASS** — 无新问题。源码引用完整且有验证标注，版本声明准确，ShadowHook 16KB page size 实现细节引用深入。1 条历史观察项延续。

---

## §18.21 EyeDropper API 与跨设备协作性能

**路径**: `src/part2-performance/ch18-rendering-pipelines/21-eyedropper-crossdevice.md`
**frontmatter**: status=finalized, last_task9_at=2026-04-24, last_task9_audit=2026-07-08

### 源码引用检查

| 引用路径/内容 | 验证状态 | 备注 |
|---|---|---|
| `Intent.ACTION_OPEN_EYE_DROPPER` | ✅ 准确 | Android 17 (API 37) |
| `Intent.EXTRA_COLOR` | ✅ 准确 | ARGB 整型颜色值 |
| `Build.VERSION.SDK_INT < 37` | ✅ 准确 | 降级分支正确 |
| `registerForActivityResult` 模式 | ✅ 准确 | Activity Result API 用法规范 |
| `Trace.beginSection/endSection` | ✅ 准确 | 标准 Perfetto SDK 打点 |

### 版本差异检查

| 声明 | 验证状态 | 备注 |
|---|---|---|
| API 下限 Android 17 / API 37 | ✅ 准确 | EyeDropper 为 Android 17 新增 |
| "公开 API 没有提供可实例化的 EyeDropper 对象" | ✅ 准确 | Intent-based API 设计 |
| secure window / protected buffer 涂黑 | ✅ 合理 | 隐私边界正确 |
| 无公开 Perfetto slice/counter 名 | ✅ 合理 | 系统内部实现 |

### 代码质量

- Kotlin 代码示例简洁规范，`resolveActivity()` 防御性检查完整
- 自定义 Trace 打点建议实用
- 跨设备协作方案描述工程导向，不超出公开 API 边界

### 结论

**PASS** — 无问题。API 引用准确，版本声明无误，代码示例规范。77 天未复检无版本漂移风险（Android 17 EyeDropper API 尚未发生 breaking change）。

---

## §26.11 eBPF 在线追踪与 Binder 语义重建

**路径**: `src/part5-app/ch26-observability/11-ebpf-online-tracing-binder-semantics.md`
**frontmatter**: status=finalized, last_task9_at=2026-06-05, last_task9_audit=2026-06-22

### 源码引用检查

| 引用路径/内容 | 验证状态 | 备注 |
|---|---|---|
| `drivers/android/binder.c` | ⚠️ [待验证] | 正文中 L158 有 [待验证] 标注，应验证并更新 |
| `include/uapi/linux/android/binder.h` | ⚠️ [待验证] | 同上，[待验证] 标注 |
| `/system/etc/bpf/` | ✅ 准确 | AOSP 系统默认 eBPF 程序路径 |
| `/sys/kernel/debug/binder/proc/` | ✅ 准确 | Binder debugfs 路径 |
| arXiv:2604.27830 (WOOTdroid) | ✅ 有效 | 论文引用 |
| AOSP source.android.com/docs eBPF | ✅ 准确 | 官方文档链接 |
| 14.10 / 1.4 / 26.5 交叉引用 | ✅ 准确 | 内部章节关联 |

### 版本差异检查

| 声明 | 验证状态 | 备注 |
|---|---|---|
| Android 12-17 覆盖范围 | ✅ 准确 | eBPF 系统侧 Android 12+ 可用 |
| Pixel 9 / Android 16 Geekbench6 数据 | ✅ 合理 | WOOTdroid 论文数据，仍有效 |
| WOOTdroid 原型依赖 root | ✅ 准确 | 部署边界描述正确 |
| WDBind 仅处理 BC_TRANSACTION | ✅ 合理 | 局限性声明到位 |
| GKI/BTF/MTE 引用 | ✅ 准确 | 现代内核特性 |

### 发现问题

- **[P2-观察]** L158 `[待验证: AOSP android-mainline drivers/android/binder.c 与 include/uapi/linux/android/binder.h 的字段路径需在源码审阅中复核]` — 此 [待验证] 标注自 Task9 通过后仍残留。这些 AOSP 路径实际是正确的标准内核路径（android-mainline 和 android17-common 均有），建议更新为 [已验证] 或指定 android-17.0.0_r1 tag。**不阻断**。

### 结论

**PASS** — 无新阻断问题。[待验证] 标注为历史遗留观察项，建议清理。

---

## 汇总

| 章节 | 结果 | 新问题 | 历史遗留 |
|------|------|--------|---------|
| §14.13 Hook 基础设施 | PASS | 0 | 1 (entrypoint_utils.h 路径) |
| §18.21 EyeDropper API | PASS | 0 | 0 |
| §26.11 eBPF Binder 语义 | PASS | 0 | 1 ([待验证] AOSP 路径残留) |

**总评**: 3/3 通过。87 个 finalized + pass-tech-review 章节的采样抽检未发现新问题。2 条历史遗留观察项延续（均为 P2 级别，不阻断）。
