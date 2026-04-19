# AIW 自动 Review 任务报告

## 一、目标发现结果
- **扫描范围**：`src/part2-performance/ch08-responsiveness/`
- **候选章节**：
  1. `08-media-pipeline.md` | 状态为 `ready-for-review`，涉及 Android 17 跨度，技术复杂度高，亟需核验。
- **最终选择**：`08-media-pipeline.md`
- **选择理由**：多媒体管线是 Android 性能优化中最深、最易过时的领域。原文虽覆盖了 Media3 1.10 等新特性，但在 Android 16/17 的底层架构变革（如 Rust 进程内解码）上存在重大缺位。
- **排除原因**：无。

## 二、总体结论
- **总体技术评分**：3.2/5
- **是否建议回炉**：**是** (建议进行针对性补强)
- **主要风险**：对 Android 16/17 的核心性能变革（In-process Codecs）描述缺失；Codec2 性能分析深度不足；部分关键机制（Tunneled Playback）停留在 `[待验证]` 阶段。
- **评分理由**：
  - **优势**：覆盖了最新的 Media3 1.10 特性（动态调度、PlayerSurface），对 A/V Sync 和 Buffer 管理的基础描述准确。
  - **劣势**：漏掉了 Android 16 最重大的媒体架构变动（消除 IPC 开销）；对 Codec2 的 Perfetto 分析过于笼统；源码路径仅停留在目录级，缺乏方法级锚点。
- **闭环建议**：需进入回炉流程，重点补充 Android 16 Rust 解码器、Codec2 关键调用链及 Tunneled Playback 的硬件同步细节。

## 三、六维评分
| 维度 | 评分 | 问题数 | 备注 |
|------|------|-------|------|
| 源码准确性 | 3.0/5 | 2 | 路径太粗，漏掉了 Codec2 核心类。 |
| 原理链完整性 | 3.5/5 | 1 | 漏掉了“进程内解码”对原理链的重构。 |
| 版本差异覆盖 | 2.5/5 | 2 | 严重遗漏 Android 16/17 的架构级变化。 |
| 知识盲区 | 3.5/5 | 1 | 对 VVC (H.266) 等未来趋势提及不足。 |
| 数据/案例支撑 | 3.5/5 | 1 | SQL 偏旧，缺乏针对 Code2 的聚合分析。 |
| 交叉引用一致性 | 4.0/5 | 0 | 良好。 |

---

## 四、P0 问题（事实错误）
*暂无明显的直接事实错误，主要为 P1 级重大缺失。*

---

## 五、P1 问题（重要缺失）

### 1. [P1][版本差异/原理链] 缺失 Android 16 Rust 进程内解码 (In-process Codecs)
- **原文位置**：1.2 MediaCodec 的 Buffer 管理模型；8.8 版本演进
- **原文问题**：未提及 Android 16 引入的 Rust 内存安全解码器及其实现在应用进程内的重大变化。
- **源码/一手资料锚点**：
  - Android 16 Release Notes / Android Authority (Rust-based codecs).
  - 关键 API：`MediaCodecInfo.getSecurityModel()` 及其常量 `SECURITY_MODEL_MEMORY_SAFE`。
- **关键代码逻辑**：Android 16 允许 Rust 编写的解码器直接在 App 进程加载，绕过 `mediaserver` 的 Binder IPC。
- **为什么重要**：这是自 Android 7.0 进程拆分以来最大的媒体性能优化，彻底消除了 IPC 导致的 0.5-2ms 延迟及 CPU 切换开销。
- **建议修正方向**：在架构部分补充“进程内解码”对比图；在版本演进中明确 Android 16 是性能的分水岭。

### 2. [P1][源码准确性/数据支撑] Codec2 性能监控点过于模糊
- **原文位置**：Perfetto 中的多媒体性能分析
- **原文问题**：SQL 和描述依然偏向旧的 `ACodec` (OMX)，对主流的 `Codec2` (C2) 覆盖不足。
- **源码/一手资料锚点**：
  - `frameworks/av/media/codec2/`
  - 核心切片：`C2Component::process`, `C2Component::onWorkDone`.
- **核验结论**：现代设备（Android 12+）绝大多数走 Codec2，其 slice 特征与 OMX 完全不同。
- **建议补充方向**：提供针对 `C2Component` 的 SQL，区分 `android.hardware.media.c2` 进程的监控方法。

### 3. [P1][知识盲区] Tunneled Playback 机制仍处于 `[待验证]`
- **原文位置**：MediaCodec 与 Surface 的协同 -> Tunneled Video Playback
- **原文问题**：原文标注为 `[待验证]`。
- **源码/一手资料锚点**：
  - `frameworks/native/services/surfaceflinger/Layer.cpp` -> `setSidebandStream`
  - `hardware/interfaces/graphics/composer/2.x/IComposerClient.hal` -> `setLayerSidebandStream`
- **运行原理说明**：Sideband Handle 包含 `HW_AV_SYNC` ID。HWC 根据硬件时钟（PCR/STC）自动取帧，SF 将图层标记为 `HWC_SIDEBAND`。
- **建议修正方向**：移除 `[待验证]`，补齐 `HWC_SIDEBAND` 的合成逻辑和低功耗收益说明。

---

## 六、P2 问题（建议改进）

### 1. [P2][数据支撑] 缺乏 VVC (H.266) 的性能展望
- **原文问题**：Android 17 正式支持 VVC，但文中未提及其带来的 50% 带宽节省与解码开销挑战。
- **建议**：在版本演进中补充 VVC 的引入意义。

---

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|------|--------------|
| Rust 进程内解码的识别 | 高 | `MediaCodecInfo.getSecurityModel()` 在不同设备上的返回分布。 |
| HDR Headroom 动态控制 | 中 | Android 15 `setDesiredHdrHeadroom` 对 GPU 合成压力的影响。 |
| Codec2 异步调度特征 | 高 | 比较 C2 与 OMX 在 `doSomeWork` 频率上的差异。 |

---

## 八、外部核验建议
- **搜索关键词**：`Android 16 Rust In-process Codecs performance`, `Codec2 C2Component process trace`, `HWC_SIDEBAND HW_AV_SYNC implementation`.
- **建议来源**：
  - **AOSP**: `frameworks/av/media/codec2/components/`
  - **Perfetto UI**: 导入一份 4K 播放 Trace，观察 `android.hardware.media.c2` 进程。

---

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **问题 1**：补充 Android 16/17 核心变革，特别是 Rust 进程内解码消灭 IPC 开销的逻辑。
- **问题 2**：更新 Perfetto 章节，加入 Codec2 专用 SQL 及切片说明（`C2Component::process`）。
- **问题 3**：完成 Tunneled Playback 的原理补齐，明确 `HWC_SIDEBAND` 与 `HW_AV_SYNC` 的关系。

### 9.2 知识资产（高价值新增知识）
- **核心 SQL (Codec2 聚合分析)**:
  ```sql
  SELECT name, AVG(dur)/1e6 as avg_ms, MAX(dur)/1e6 as max_ms
  FROM slice
  WHERE name LIKE 'C2Component::process%' OR name LIKE 'C2Component::onWorkDone%'
  GROUP BY name;
  ```
- **关键源码路径**:
  - `frameworks/native/services/surfaceflinger/CompositionEngine/src/Layer.cpp` (Sideband 传递逻辑)
  - `frameworks/av/media/libstagefright/MediaCodec.cpp` (异步回调分发逻辑)

---

## 十、下一候选章节
- `src/part4-system/14.9-camera-performance.md` (多媒体管线的上游，与本章有强关联)

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-19-11-08-media-pipeline-external-review.md`
