# AIW 自动 Review 任务报告

## 一、目标发现结果
- 扫描范围：`src/part3-tools/ch14-other-tools/09-camera-performance-analysis.md`
- 候选章节：`14.9 Android Camera 性能与 Perfetto 分析`
- 最终选择：`14.9 Android Camera 性能与 Perfetto 分析`
- 选择理由：Camera 是极高复杂度的子系统，该章节处于 needs-rework 状态，需深审。

## 二、总体结论
- 总体技术评分：4.2/5
- 是否建议回炉：是（针对 P1 知识盲区补充）
- 主要风险：CameraMetaDataNative 的内存泄漏归因不够精确，未提及具体的 Binder 传输与 GC 延迟交互机制。
- 评分理由：文章 SQL 分析非常精彩，Perfetto 落地性极强。但在 CameraMetaDataNative 内存回收的 Java Native 边界处理细节上有一处 P1 级缺失。
- 闭环建议：进入结构化修正队列，补充 Native Allocation Registry 和 GC 触发相关原理。
- 本轮 review 覆盖范围：Camera HAL3 管线流转，Perfetto SQL 查询，内存泄漏分析，启动耗时拆解。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 4.0/5 | 1 |
| 原理链完整性 | 4.5/5 | 0 |
| 版本差异覆盖 | 4.0/5 | 0 |
| 知识盲区 | 3.5/5 | 1 |
| 数据/案例支撑 | 4.5/5 | 0 |
| 交叉引用一致性 | 4.5/5 | 0 |

## 四、P0 问题（事实错误）
（无）

## 五、P1 问题（重要缺失）
- [P1][源码准确性/原理链完整性][CameraMetaDataNative 内存泄露]
- **原文问题**："解决方法是在使用完后主动调用 CameraMetadataNative.close()，不依赖 Finalizer"。
- **源码 / 一手资料锚点**：`frameworks/base/core/java/android/hardware/camera2/impl/CameraMetadataNative.java`。
- **关键代码逻辑**：`CameraMetadataNative` 在 AOSP 中实现了 `Parcelable`，内部通过 `mMetadataPtr` 持有 native 内存。它在现代 Android（Android 10+）中不再单纯依赖 `Finalizer`，而是使用 `NativeAllocationRegistry` 注册释放回调。
- **为什么错/缺失**：Native 内存泄露的本质是因为 Java 对象非常小，未达到触发 GC 的阈值，而 Native 内存增长极快。`NativeAllocationRegistry` 会在分配时向 VM 报告 native size，从而更快触发 GC。如果文中依然强调 Finalizer，说明参考的可能是 Android 8/9 之前的旧逻辑，或未讲清 `NativeAllocationRegistry` 的作用。并且，Camera API 中 App 层拿到的是 `TotalCaptureResult`，并没有直接暴露 `CameraMetadataNative.close()` 给 App 调用。
- **建议修正方向**：核实 `CameraMetadataNative` 的内存回收机制是否已切为 `NativeAllocationRegistry`，修正 App 层如何规避（通常是避免长期持有过多的 `CaptureResult` 强引用，而不是调 `close`）。

## 六、P2 问题（建议改进）
- [P2][知识盲区][HAL3 管线延迟的典型值]
- **原文问题**：文章标记了 `[待验证: 不同 SoC 平台（高通/联发科/三星）上 HAL3 管线延迟的典型值]`。
- **建议**：补充一个大致参考值：通常从 Request 下发到收到 Result，如果打开 ZSL，耗时约在 2-3 帧（66-100ms），如果关闭 ZSL 可能更长，ISP 处理时间通常在 10-20ms 量级。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|----------|--------------|
| CameraMetadataNative 的回收机制演进 | 高 | 查阅 AOSP 中 `CameraMetadataNative.java` 的 `NativeAllocationRegistry` 使用情况 |

## 八、外部核验建议
- 搜索关键词：`AOSP CameraMetadataNative NativeAllocationRegistry`

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **章节**：14.9
- **严重级别**：P1
- **问题类型**：源码逻辑过期
- **位置**：误区三：CameraMetaDataNative 的内存泄漏
- **问题描述**：将内存泄露归因为 Finalizer 及建议调用 `close()` 可能已不符合现代 AOSP 逻辑，App 层无法直接 close 它，且底层早已改用 `NativeAllocationRegistry`。
- **建议修正方向**：用 AOSP 源码核验 `CameraMetadataNative` 的回收机制，修正防泄漏的实战建议。

### 9.4 可复用知识资产（高价值新增知识）
- **章节**：14.9
- **可复用的技术结论**：文中的 Perfetto SQL（量化帧率和帧间隔、启动性能量化拆解）具有极高的直接复用价值，可以直接作为 Camera 性能分析的 SOP。