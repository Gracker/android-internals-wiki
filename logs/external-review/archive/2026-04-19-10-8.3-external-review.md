# AIW 自动 Review 任务报告

## 一、目标发现结果
- **扫描范围**：`src/part2-performance/ch08-responsiveness/`
- **最终选择**：`03-launch-optimization.md`
- **选择理由**：该章节处于 `ready-for-review` 状态，且涉及 Android 15/16/17 等大量前沿特性，极需源码级核验。

## 二、总体结论
- **总体技术评分**：3.5/5
- **是否建议回炉**：是
- **主要风险**：对 Android 12+ 关键度量行为的修正逻辑描述缺失；对 Android 15/16/17 的新技术（如内核级 AutoFDO、ApplicationStartInfo）描述不够深入。
- **评分理由**：存在 1 个 P0 级事实描述不完整（影响性能度量准确性），以及 3 个 P1 级重要知识缺失。
- **本轮 review 覆盖范围**：冷启动度量指标、SplashScreen API、并行初始化框架、ContentProvider 优化、Baseline Profile、Android 15-17 演进。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 3.5/5 | 1 (P0) |
| 原理链完整性 | 4.0/5 | 1 (P1) |
| 版本差异覆盖 | 3.0/5 | 2 (P1) |
| 知识盲区 | 3.5/5 | 1 (P1) |
| 数据/案例支撑 | 4.0/5 | 1 (P2) |
| 交叉引用一致性 | 5.0/5 | 0 |

## 四、P0 问题（事实错误）
- **[P0][源码准确性][TTFD 度量部分]**
- **原文问题**：未提及 Android 12+ 系统会对 `reportFullyDrawn()` 进行强制修正。
- **源码锚点**：`frameworks/base/services/core/java/com/android/server/wm/ActivityMetricsLogger.java`
- **核验结论**：自 Android 12 起，如果应用在系统判定为 TTID 之前调用 `reportFullyDrawn()`，系统会记录 TTFD = TTID。
- **为什么错**：如果开发者在 `onCreate` 立即调用，会误以为启动极快，掩盖真实的异步加载耗时。
- **建议修正方向**：明确指出 Android 12+ 的这一修正行为，建议开发者必须在首帧绘制后再根据业务逻辑上报 TTFD。

## 五、P1 问题（重要缺失）
- **[P1][版本差异覆盖][Android 15/16/17 演进]**
- **原文问题**：对 AutoFDO 的描述停留在表面。
- **核验结论**：Android 16 引入了 **Kernel-level AutoFDO**（针对 `android16-6.12` 内核分支），利用真实负载优化系统调用。
- **缺失内容**：内核级优化对启动时进程创建、资源分配的巨大提升。
- **建议补充方向**：区分“用户态 AutoFDO (Android 15)”和“内核级 AutoFDO (Android 16)”。

- **[P1][知识盲区][启动监控]**
- **原文问题**：缺失 Android 15 `ApplicationStartInfo` API。
- **核验结论**：该 API 允许应用查询详细的启动元数据（启动原因、温度、是否被强杀等）。
- **缺失内容**：它是线上启动归因分析的“银弹”，能极大减少“启动慢”的误报（如因为系统刚开机导致的慢）。
- **建议补充方向**：在“线上监控”小节增加对该 API 的介绍。

- **[P1][源码准确性][ContentProvider 优化]**
- **原文问题**：对 ContentProvider 加载时机描述不够细致。
- **源码锚点**：`frameworks/base/core/java/android/app/ActivityThread.java#handleBindApplication`
- **运行原理说明**：在 `handleBindApplication` 中，`installContentProviders` 发生在 `makeApplication` 之后，但紧接着就会调用 `mInstrumentation.callApplicationOnCreate`。这意味着 Provider 的 `onCreate` 会阻塞主线程进入 `Application.onCreate`。
- **建议补充方向**：补充这一调用链的关键节点，强调 Provider 实际上是在 Application 对象创建后、但 `onCreate` 执行前加载的。

## 六、P2 问题（建议改进）
- **[P2][实战落地][reportFullyDrawn]**
- **原文问题**：建议手动调用 `reportFullyDrawn()`。
- **建议**：推荐使用 Jetpack 库中的 `FullyDrawnReporter`（通过 `ComponentActivity.fullyDrawnReporter` 获取），它支持多异步任务聚合上报，更符合现代开发习惯。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|------|-------|
| 启动画面的 Edge-to-Edge 适配 | 中 | Android 15 强制全屏对 SplashScreen 图标布局的影响 |
| Baseline Profile 在 AAB 模式下的延迟生效 | 高 | Play Store 分发 Profile 的具体耗时窗口（通常 24h 内） |
| AutoFDO 与内核 I/O 调度的关系 | 低 | 探讨 AutoFDO 是否能优化启动时的预读取（Read-ahead） |

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
1. **[P0][源码错误]** 补充 Android 12+ 对 `reportFullyDrawn` 的自动修正逻辑。
2. **[P1][原理缺失]** 补充 Android 16 内核级 AutoFDO 的技术细节。
3. **[P1][版本差异]** 补充 Android 15 `ApplicationStartInfo` API 及其在启动归因中的作用。
4. **[P1][源码细化]** 细化 `ActivityThread` 中 ContentProvider 的加载顺序细节。

### 9.4 可复用知识资产
- **源码路径**：`frameworks/base/core/java/android/app/ApplicationStartInfo.java` (Android 15+)
- **技术结论**：`ApplicationStartInfo` 可通过 `getStartReason()` 获取启动诱因，是解决“启动劣化误报”的关键。
- **版本差异**：Android 15 强制 Edge-to-Edge 模式下，SplashScreen 的退出动画可能需要重新计算 `View.TRANSLATION_Y` 的偏移量以适配导航栏。

## 十、下一候选章节
- `src/part2-performance/ch08-responsiveness/07-baseline-profiles.md` (针对编译优化的深度专项)

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-19-10-03-launch-optimization-external-review.md`
