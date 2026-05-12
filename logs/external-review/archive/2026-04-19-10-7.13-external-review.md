# AIW 自动 Review 任务报告

## 一、目标发现结果
- 扫描范围：`src/part2-performance/ch07-smoothness/`
- 候选章节：
  1. `13-systemui-performance.md` | 手动指定目标，且处于 `ready-for-review` 状态。
- 最终选择：`src/part2-performance/ch07-smoothness/13-systemui-performance.md`
- 选择理由：用户明确指令。

## 二、总体结论
- 总体技术评分：4.5/5
- 是否建议回炉：否（建议在后续 Task 2b 中进行微调，而非完全重写）
- 主要风险：架构命名虽然前瞻且准确，但缺乏对背景（Flexiglass/Scene Framework）的显式定义，可能导致读者在旧版本源码中搜索无果。
- 评分理由：文章深度极高，准确捕捉到了 Android 15/16 正在进行的 Flexiglass 重构类名，且对通知绑定和输入路径的分析非常符合实战性能排查视角。
- 闭环建议：无需回炉。建议直接进入 P1 级的微调，补齐架构背景说明。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 5/5 | 0 |
| 原理链完整性 | 4/5 | 1 |
| 版本差异覆盖 | 5/5 | 0 |
| 知识盲区 | 4/5 | 1 |
| 数据/案例支撑 | 4/5 | 0 |
| 交叉引用一致性 | 5/5 | 0 |

## 四、P0 问题（事实错误）
*暂无。文中的类名和路径经核验与 Android 15/16 AOSP main 分支一致。*

## 五、P1 问题（重要缺失）
- [P1][原理链完整性][先分清谁负责什么 / StatusBar 与通知更新]
- 原文问题：直接引入了 `NotificationIconContainerStatusBarViewModel` 等类，但未说明这是属于哪个架构代际的产物。
- 源码 / 一手资料锚点：`com.android.systemui.scene.domain.interactor.SceneInteractor` / Flexiglass (Scene Framework) Design Doc.
- 缺失内容：缺乏对 **Flexiglass (Scene Framework)** 这一重大架构重构的背景引入。
- 运行原理说明：从 Android 15 开始，SystemUI 正在从旧的 Fragment/Controller 模式迁移到基于状态机和 Scene 的响应式架构。
- 建议补充方向：在“先分清谁负责什么”小节中，增加一段关于 Flexiglass 架构的简单说明，告知读者如果找不到这些类，可能是因为 AOSP 版本过低或未开启该特性旗标。

## 六、P2 问题（建议改进）
- [P2][知识盲区][通知内容绑定]
- 原文问题：提到 `applyAsync()` / `reapplyAsync()`，但未区分两者的性能差异。
- 证据或观察依据：`RemoteViews.reapplyAsync` 在通知更新（而非新增）时通过 `diff` 算法仅更新变化的 View，开销远小于 `applyAsync`。
- 建议：补充说明在 Trace 中如果看到频繁的 `apply`（全量绑定）而非 `reapply`，通常意味着 App 侧发送的通知数据结构发生了不必要的剧变。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|----------|--------------|
| Flexiglass / Scene Framework | 高 | 了解 SystemUI 如何通过 `SceneInteractor` 管理状态栏、抽屉、锁屏的切换逻辑。 |
| Notification Pipeline v2 过滤机制 | 中 | 研究 `NotifFilter` 和 `NotifPromoter` 如何在绑定前影响性能。 |

## 八、外部核验建议
- 搜索关键词：`Android SystemUI Flexiglass architecture`, `NotificationIconInteractor AOSP`, `RemoteViews reapplyAsync performance`
- 建议查阅：`cs.android.com` 搜索 `com.android.systemui.scene` 包下的代码。

## 九、可闭环输出

### 9.1 回炉问题单（暂无 P0，建议微调）
*无*

### 9.2 知识盲区清单（供后续研究）
- **[重要]** 显式引入 **Flexiglass** 概念，并将其作为 Android 15-17 分析的基础背景。

### 9.3 一般建议清单（非阻断）
- 在 Perfetto 章节，补充 `repeatWhenAttached` 导致的协程调度开销观察点。

### 9.4 可复用知识资产
- **关键类名锚点**：
  - `NotificationIconContainerStatusBarViewModel`: 状态栏通知图标的新逻辑中枢。
  - `NotificationIconContainerStatusBarViewBinder`: 视图绑定器，替代了旧的 Controller。
- **关键路径**：`frameworks/base/packages/SystemUI/src/com/android/systemui/statusbar/notification/icon/ui/`
- **技术结论**：Android 15+ 的 SystemUI 性能分析必须考虑 **Kotlin Flow** 订阅带来的异步开销，而不仅仅是传统的 View 树遍历。

## 十、下一候选章节
- `src/part2-performance/ch07-smoothness/14-launcher-performance.md`（如有，建议顺着转场逻辑继续 review Launcher）

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-19-10-13-systemui-performance-external-review.md`
