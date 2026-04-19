# AIW 自动 Review 任务报告

## 一、目标发现结果
- **扫描范围**：`src/part2-performance/ch08-responsiveness/`
- **候选章节**：`07-baseline-profiles.md`
- **最终选择**：`07-baseline-profiles.md`
- **选择理由**：该章节处于 `ready-for-review` 状态，且涉及 Android 14+ ART Service、Android 16 Cloud Compilation 等前沿变化，急需源码级和官方一手资料核验以确保时效性。

## 二、总体结论
- **总体技术评分**：3.8/5
- **是否建议回炉**：是
- **主要风险**：对 Android 14+ ART Service 带来的路径变更覆盖不全；对 Startup Profiles 的“编译时优化”本质描述不够深入；Android 16 的新机制尚停留于“待验证”。
- **评分理由**：虽然文章结构完整、案例丰富，但在关键的 Android 版本演进（14/15/16）细节上存在信息滞后或模糊点。
- **闭环建议**：需针对 P1 问题单进行专项补强，特别是 SDM 机制和 Dexlayout 的底层逻辑。
- **本轮 review 覆盖范围**：ART 编译演进、Baseline/Cloud/JIT Profile 关系、Android 14 ART Service 命令、Android 16 SDM、Startup Profiles 与 Dexlayout、AutoFDO 硬件背景。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 3.5/5 | 1 (P1) |
| 原理链完整性 | 4.0/5 | 1 (P1) |
| 版本差异覆盖 | 3.5/5 | 2 (P1) |
| 知识盲区 | 4.0/5 | 1 (P2) |
| 数据/案例支撑 | 4.5/5 | 0 |
| 交叉引用一致性 | 4.0/5 | 0 |

## 四、P0 问题（事实错误）
*暂无显式 P0 错误，主要为版本滞后导致的 P1 级缺失。*

## 五、P1 问题（重要缺失）

### 1. [P1][源码准确性/版本差异][Android 14+ 产物路径]
- **原文位置**：`Baseline Profiles 的工作机制` -> `Profile 格式与打包` -> "安装后的 `base.odex` 在 `/data/app/.../oat/arm64/`"
- **源码 / 一手资料锚点**：AOSP `art/libartservice`；Android 14 Release Notes。
- **关键代码逻辑**：从 Android 14 开始，ART Service 接管了 dexopt。对于很多通过 ART Service 编译的产物，其路径已迁移。
- **运行原理说明**：为了更好的 APEX 模块化管理，ART 产物现在主要存放在 `/data/misc/apexdata/com.android.art/dalvik-cache/`。
- **版本差异**：Android 13 及以前主要在 `/data/app/.../oat/`；Android 14+ 优先看 `apexdata` 路径。
- **建议修正方向**：明确说明 Android 14 后的路径变更，避免读者在实战调试时找不到文件。

### 2. [P1][原理链完整性][Startup Profiles 与 Dexlayout 的编译时属性]
- **原文位置**：`生成与维护 Baseline Profiles` -> `AGP 自动化`
- **关键代码逻辑**：Startup Profiles 会被 D8/R8 消费，通过 `dexlayout` 工具（或 R8 内部实现）重新排列 DEX 中的类。
- **缺失内容**：文中虽然提到了 Startup Profiles，但没有讲透它是在 **构建时（Build Time）** 发生的优化，而 Baseline Profiles 是在 **安装/运行时（Install/Runtime）**。
- **为什么这是重要缺失**：这决定了开发者在 CI 流程中如何验证两者。Startup Profiles 的验证是看 DEX 结构，Baseline Profiles 是看 `dexopt` 状态。
- **建议补充方向**：在“定位”小节补齐“构建时 vs 运行时”的对比。

### 3. [P1][版本差异/证据][Android 16 SDM 机制确认]
- **原文位置**：`[待验证] Android 16 的云端预编译分发`
- **核验结论**：已确认该机制官方术语为 **Secure Dex Metadata (SDM)**。
- **运行原理说明**：Google Play 预先为目标架构生成机器码并封装在 SDM 文件中，安装时直接加载，跳过本地 `dex2oat`。
- **建议修正方向**：将 `[待验证]` 标记移除，更新为确定性描述，并补充 SDM 术语。

## 六、P2 问题（建议改进）

### 1. [P2][知识盲区][ARMv9 AutoFDO 演进]
- **原文位置**：`与 AutoFDO 的关系与区别`
- **证据或观察依据**：Pixel 8/9 (ARMv9) 引入了 ETE (Embedded Trace Extension) 和 TRBE。
- **问题描述**：文中只提到了 ETM，对于追求极致性能的 OEM 读者，缺少对最新硬件采样技术的提及。
- **建议**：补充一句关于 ETE/TRBE 的说明，作为 AutoFDO 采样在 Android 15/16 上的主要硬件演进。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|------|-------|
| 国内应用商店是否支持 `.dm` 分发 | 高 | 调研华为、小米、OPPO 商店对 Profile 加速的支持现状 |
| SDM 与传统 `.dm` 文件的二进制差异 | 中 | 研究 Google Play 新分发协议中的 Artifact 结构 |

## 八、外部核验建议
- **搜索关键词**：`Android ART Service ArtManagerLocal API`
- **搜索关键词**：`Secure Dex Metadata SDM format spec`
- **建议查阅**：`cs.android.com` 搜索 `com.android.art` APEX 下的 `service` 目录，重点看编译产物路径分发逻辑。

## 九、可闭环输出

### 9.1 回炉问题单
1. **[P1][Android 14 路径]**：修正 OAT 产物在 Android 14+ 下的真实路径描述，补充 `apexdata` 目录。
2. **[P1][原理区分]**：深度区分 Startup Profile (Build-time Dexlayout) 与 Baseline Profile (Install-time AOT)。
3. **[P1][SDM 确认]**：转正 Android 16 Cloud Compilation 的描述，引入 SDM 概念。

### 9.2 可复用知识资产
- **关键路径**：`/data/misc/apexdata/com.android.art/dalvik-cache/` (Android 14+ ART Service 产物路径)。
- **核心术语**：**Secure Dex Metadata (SDM)** —— Android 16 云端预编译文件格式。
- **技术结论**：Startup Profiles 主要用于 D8/R8 的 **Dexlayout** 优化，减少 Page Fault；Baseline Profiles 主要用于 ART 的 **AOT** 编译，提升执行速度。
- **源码参考**：`androidx.profileinstaller.ProfileVerifier` 的 `RESULT_CODE_COMPILED_WITH_PROFILE` 状态码是验证 Baseline Profiles 是否落地的标准 API 证据。

## 十、下一候选章节
- `src/part2-performance/ch08-responsiveness/08-vitals-monitoring.md`（待技术复审）

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-19-11-07-baseline-profiles-external-review.md`
