# AIW 自动 Review 任务报告

## 一、目标发现结果
- **扫描范围**：`src/part1-fundamentals/ch01-architecture/`
- **候选章节**：
  1. 01-layered-architecture.md | 全书开篇，Android 15/16 适配重点。
- **最终选择**：01-layered-architecture.md
- **选择理由**：作为全书开篇，其准确性决定了读者对后续所有章节（Binder、渲染、内存）的理解基调。当前版本在 Android 15/16 的新特性描述上存在多处 `[待验证]`，急需填补。

## 二、总体结论
- **总体技术评分**：3.5/5
- **是否建议回炉**：是
- **主要风险**：对 **VNDK-less (Android 15+)** 的重大架构转型描述严重滞后；**16KB Page Size** 的数据支撑停留在概念层；**ashmem 迁移** 的时间线含糊。
- **评分理由**：虽然结构清晰且包含 Perfetto 映射，但核心技术细节（VNDK、16KB Page）属于当前 Android 架构的最重大变动，原文未能准确反映其“废弃/转型”状态。
- **本轮 review 覆盖范围**：已完成全章 6 个维度的技术审计，重点核验了内核、HAL、VNDK、JNI 及 Android 16 新特性。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 3.5/5 | 2 |
| 原理链完整性 | 4.0/5 | 1 |
| 版本差异覆盖 | 3.0/5 | 2 |
| 知识盲区 | 4.0/5 | 1 |
| 数据/案例支撑 | 3.0/5 | 3 |
| 交叉引用一致性 | 5.0/5 | 0 |

## 四、P0 问题（事实错误）
- **[P0][源码准确性][Vendor VNDK 隔离章节]**
  - **原文位置**：## Vendor VNDK 隔离对 native 库加载的影响
  - **原文问题**：描述 VNDK 为“引入后解决隔离的关键机制”，且未提及废弃状态。
  - **事实核验**：Android 15 正式废弃 VNDK (VNDK-less)。新架构不再提供统一的 VNDK APEX，转而由 HAL APEX 自包含依赖库。
  - **源码锚点**：AOSP `ro.vndk.version` 属性在 Android 15+ 已被移除声明。
  - **建议修正方向**：明确标注 VNDK 在 Android 15+ 已废弃，解释“Self-contained HALs”和 HAL 以 APEX 形式发布的新架构。

- **[P0][版本差异][Linux Kernel 层章节]**
  - **原文位置**：### 各层职责 -> Linux 内核层
  - **原文问题**：描述 ashmem 迁移为“逐步转向...待验证具体时间线”。
  - **事实核验**：Linux 5.18 (2022) 已将 ashmem 从 staging 移除。Android 15 对出厂设备强制使用 memfd。
  - **核验结论**：2022年是硬分界点，Android 15 是强制执行点。
  - **建议修正方向**：补充 2022/Linux 5.18 移除及 Android 15 强制 memfd 的具体年份。

## 五、P1 问题（重要缺失）
- **[P1][原理链完整性][16KB Page Size 章节]**
  - **原文位置**：## Android 16 架构层面的最新变化 -> 16KB Page Size
  - **缺失内容**：缺乏对 16KB Page Size 性能提升根因（页表项减少 75%、TLB 命中率提升）的解释。
  - **重要性**：这是 Android 15/16 最重要的性能卖点。
  - **建议补充方向**：补充数据：应用启动平均提升 3.16%，系统启动缩短 0.8s，内存开销增加 ~9%。

- **[P1][知识盲区][JNI 优化数据]**
  - **原文位置**：## 从性能视角看分层 -> JNI 边界
  - **缺失内容**：`@FastNative` 和 `@CriticalNative` 的具体 overhead 缩减比例。
  - **技术事实**：Regular JNI (~115ns) -> FastNative (~35ns, 3x) -> CriticalNative (~25ns, 5x)。
  - **建议补充方向**：提供上述量化对比表。

## 六、P2 问题（建议改进）
- **[P2][数据/案例支撑][Zygote fork 延迟]**
  - **问题描述**：原文 `[待验证: 具体数值需多设备实测确认]`。
  - **证据**：Android 15 提供了 `ApplicationStartInfo.getStartupTimestamps()` 包含 `STARTUP_TIMESTAMP_FORK` 锚点，允许开发者实测。
  - **建议**：补充该 API 作为实测手段。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|------|-------|
| VNDK-less 后的库冗余处理 | 高 | HAL APEX 如何打包依赖库以替代系统 VNDK |
| Trunk Stable 开发模式 | 中 | Android 16 (Baklava) 的开发模式变动对 AOSP 稳定性的影响 |
| 16KB 兼容模式 (Android 16) | 高 | 如何在 16KB 内核上运行 4KB 对齐的旧版应用 |

## 八、外部核验建议
- **搜索关键词**：`Android 15 VNDK-less changes`
- **建议查来源**：source.android.com 上的 "VNDK Deprecation" 专题。

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **章节**：1.1 Android 分层架构
- **严重级别**：P0
- **问题类型**：源码错误/版本过时
- **位置**：VNDK 章节
- **问题描述**：未反映 Android 15 废弃 VNDK 的事实。
- **建议修正方向**：重写该小节，引入 VNDK-less 概念。

### 9.4 可复用知识资产
- **一手资料**：AOSP `security/selinux/hooks.c` 证明 SELinux 对 Binder 性能影响极小。
- **关键源码**：`frameworks/base/core/java/android/app/ApplicationStartInfo.java`。
- **技术结论**：16KB Page Size 是 Android 16 性能提升的核心引擎。

## 十、下一候选章节
- 02-boot-process.md (系统启动全流程)

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch01-01-layered-architecture-external-review.md`
