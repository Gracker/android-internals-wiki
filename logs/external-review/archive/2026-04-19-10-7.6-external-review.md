# AIW 自动 Review 任务报告

## 一、目标发现结果
- 扫描范围：`src/part2-performance/ch07-smoothness/`
- 候选章节：
  1. `06-case-studies.md` | 本章为案例集，是前几章理论的落地，技术准确性至关重要。
- 最终选择：`src/part2-performance/ch07-smoothness/06-case-studies.md`
- 选择理由：用户明确指定，且该章节处于 `task6_reviewed` 阶段，急需技术深审以进入 `task9`。

## 二、总体结论
- 总体技术评分：3.5/5
- 是否建议回炉：是
- 主要风险：案例中的部分技术断言过于简化，忽略了 Android 14/15 的关键行为变更；部分源码级逻辑描述存在偏差（如 AVD 运行线程）；缺少对常见“隐形”IO 阻塞（如 SP）的覆盖。
- 评分理由：存在 1 处 P0（Android 15 弃用 API 误导），2 处 P1（渲染同步逻辑简略、AVD 运行线程偏差），及多处知识盲区。
- 本轮 review 覆盖范围：全章 5 个案例、厂商优化、硬件差异及方法论。
- 本轮未完成部分：无。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 3/5 | 2 |
| 原理链完整性 | 4/5 | 1 |
| 版本差异覆盖 | 2/5 | 1 |
| 知识盲区 | 3/5 | 2 |
| 数据/案例支撑 | 4/5 | 0 |
| 交叉引用一致性 | 5/5 | 0 |

## 四、P0 问题（事实错误）
- [P0][版本差异覆盖][案例五：系统低内存]
- **原文问题**：建议开发者响应 `onTrimMemory`，并未明确指出 `TRIM_MEMORY_RUNNING_*` 的状态。
- **一手资料锚点**：`android.content.ComponentCallbacks2` API 35 (Android 15)。
- **核验结论**：Android 15 正式弃用了 `TRIM_MEMORY_RUNNING_MODERATE/LOW/CRITICAL` 以及 `TRIM_MEMORY_MODERATE/COMPLETE`。系统不再保证发送这些信号，应用应依赖 `onLowMemory()` 或 `TRIM_MEMORY_UI_HIDDEN`。
- **为什么错**：原文虽提到了 Android 14 的变化，但给出的代码示例和建议仍带有旧时代的惯性，未明确告知开发者这些常量在最新版本中已不可靠。
- **建议修正方向**：明确标注 API 35 的弃用，将建议导向 `onLowMemory()` 和 `ActivityManager.MemoryInfo.lowMemory`。

## 五、P1 问题（重要缺失）
- [P1][源码准确性][案例四：RenderThread sync]
- **原文问题**：描述“多表情叠加时 GPU 工作量激增，sync 等待时间增加”。
- **源码锚点**：`frameworks/base/libs/hwui/renderthread/DrawFrameTask.cpp` 中的 `DrawFrameTask::run()`。
- **关键代码逻辑**：UI 线程在 `syncFrameState` 阶段被阻塞，直到 RenderThread 调用 `unblockUiThread()`。如果 RenderThread 忙于执行上一帧的 `context->draw()`（特别是 `eglSwapBuffers` 阶段因 VSync 阻塞或 GPU 繁忙），它将无法及时处理队列中的下一个 `DrawFrameTask`，导致 UI 线程在 `nSyncAndDrawFrame` 处长时间等待。
- **缺失内容**：原文未点出“UI 线程阻塞是在等待 RT 空闲”这一本质，也未提到 `canUnblockUiThread` 受纹理上传（Texture Upload）影响的细节。
- **建议补充方向**：说明 UI 线程阻塞的本质是 **RenderThread 任务队列积压**，并区分 `syncFrameState` 本身耗时（如位图上传）与 RT 忙碌导致的等待耗时。

- [P1][知识盲区][案例四：RenderThread sync]
- **原文问题**：提到“向量路径数据变化导致 RenderThread 承担了大量的绘制”。
- **核验结论**：`AnimatedVectorDrawable` 在 API 25+ 默认运行在 RenderThread（利用 `RenderNodeAnimator`）。这意味着 path 变化是在 Native 层计算并更新 DisplayList 属性的，**不一定会触发 UI 线程的重录制**。
- **为什么重要**：如果开发者误以为 AVD 每一帧都会卡主线程，会得出错误的优化结论。真正的瓶颈往往是 AVD 触发了过多的 `invalidate()` 到 UI 线程，或者 RT 自身栅格化过于沉重。
- **建议补充方向**：区分 AVD 的 RT 运行模式，强调 AVD 如何解耦 UI 线程，并指出其“反向压制”UI 线程的真实路径。

## 六、P2 问题（建议改进）
- [P2][知识盲区][案例二：Binder 调用]
- **问题描述**：原文列举了 I/O 阻塞来源，但遗漏了最隐蔽的 `SharedPreferences.getString()`。
- **证据依据**：`SharedPreferencesImpl.awaitLoadedLocked` 在冷启动或 SP 文件过大时会直接导致主线程 `wait()`，这是极高频的卡顿根因。
- **建议**：在“举一反三”中加入 SP 阻塞的说明，并推荐 MMKV 或 DataStore。

- [P2][源码准确性][案例三：内存压力]
- **原文问题**：代码示例 `LruCache<String, Bitmap>(Int.MAX_VALUE)`。
- **问题描述**：`LruCache` 的构造函数必须传入一个合理的 `maxSize`，传入 `MAX_VALUE` 虽技术可行但属于极差实践，且未说明 `sizeOf` 的计算逻辑。
- **建议**：修正示例代码，强调 `maxSize` 应基于 `Runtime.maxMemory()` 动态计算。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|------|-------|
| 16 KB 页支持 (Android 15) | 中 | 研究其对内存分配效率及 NDK 应用的影响 |
| Variable Refresh Rate (VRR) | 高 | 120Hz 下 8.3ms 预算对 `sync` 阻塞的放大效应 |
| Bitmap.prepareToDraw() | 中 | 异步上传纹理以缓解 `syncFrameState` 阻塞 |

## 八、外部核验建议
- 搜索关键词：`Android 15 ComponentCallbacks2 deprecation`
- 建议查：官方 API 文档及 Android 15 Release Notes。
- 搜索关键词：`DrawFrameTask::syncFrameState unblockUiThread logic`
- 建议查：`cs.android.com` 中 `DrawFrameTask.cpp` 的 `run()` 方法。

## 九、可闭环输出

### 9.1 回炉问题单
1. **章节**：7.6 案例五
   **级别**：P0
   **描述**：`onTrimMemory` 常量在 API 35 已弃用。
   **建议**：移除对 `RUNNING_*` 的依赖描述，改为推荐 `onLowMemory()` 及 `ActivityManager` 查询。

2. **章节**：7.6 案例四
   **级别**：P1
   **描述**：RenderThread 阻塞 UI 线程的机理描述不全。
   **建议**：补全“RT 忙碌导致任务队列积压”的逻辑，区分 `sync` 等待与 `sync` 执行。

3. **章节**：7.6 案例四
   **级别**：P1
   **描述**：AVD 运行线程描述存在偏差。
   **建议**：明确 API 25+ AVD 在 RT 运行的机制，解释其为何仍可能通过 RT 拥塞影响 UI 线程。

### 9.2 知识盲区清单
- **章节**：7.6 案例二
  **盲区**：`SharedPreferences` 启动阻塞。
  **建议研究**：在案例二补强 SP 阻塞的分析，提供 `awaitLoadedLocked` 的 Trace 特征。

### 9.3 一般建议清单
- **章节**：7.6 案例三
  **描述**：`LruCache` 示例代码不严谨。
  **建议**：给出基于百分比内存分配的正确示例。

### 9.4 可复用知识资产
- **源码路径**：`frameworks/base/libs/hwui/renderthread/DrawFrameTask.cpp`
- **关键结论**：UI 线程被唤醒的时机（`unblockUiThread`）不仅取决于同步是否完成，还取决于 RenderThread 是否能及时开始执行同步。
- **版本差异**：Android 15 简化了内存回收信号，开发者应从“被动响应信号”转向“主动检查状态”或“依赖关键状态变化（UI_HIDDEN）”。

## 十、下一候选章节
- `src/part2-performance/ch07-smoothness/01-concepts.md` (回顾核心概念是否与案例冲突)

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-19-10-06-case-studies-external-review.md`
