# AIW 自动 Review 任务报告

## 一、目标发现结果
- 扫描范围：`metadata/queue.json`、`src/` 目录。
- 候选章节：
  1. `src/part3-tools/ch14-other-tools/04-dumpsys.md` | 符合本轮外部审查指令，包含大量 AOSP 和底层机制断言。
- 最终选择：`src/part3-tools/ch14-other-tools/04-dumpsys.md`
- 选择理由：用户指令明确指定。
- 排除的高频原因：N/A

## 二、总体结论
- 总体技术评分：3.8/5
- 是否建议回炉：是（需修复 1 处 P0 和 1 处 P1）
- 主要风险：LMKD（低内存杀手）的行为逻辑描述存在严重事实错误，将调试指标（USS）与系统底层的运行时决策指标（RSS/oom_score_adj）混淆。
- 评分理由：整体结构清晰，覆盖了最核心的 dumpsys 命令，且对 Android 15 SurfaceFlinger Frontend 的最新变化跟进得很紧。但 PSS/USS 机制与 LMKD 的关联描述错误（P0），且在 dumpsys window 焦点排查中存在遗漏（P1），因此扣分。
- 闭环建议：进入结构化修正队列，修正 LMKD 运行原理，补充 input focus 细节。
- 本轮 review 覆盖范围：activity, meminfo, gfxinfo, window, batterystats, SurfaceFlinger 全量机制。
- 本轮未完成部分：自定义 dump 接口的代码示例（原文标有待补充，本轮未提供代写代码）。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 3/5 | 1 (P0) |
| 原理链完整性 | 4/5 | 1 (P1) |
| 版本差异覆盖 | 5/5 | 0 |
| 知识盲区 | 4/5 | 1 (P1) |
| 数据/案例支撑 | 4/5 | 0 |
| 交叉引用一致性 | 4/5 | 0 |

## 四、P0 问题（事实错误）
- [P0][源码准确性][dumpsys meminfo：关键指标]
- **原文问题**：“USS 帮助我们评估一个进程的"可回收价值"——LMK 在选择杀谁时，会参考这个值。”
- **源码 / 一手资料锚点**：AOSP `system/memory/lmkd/lmkd.cpp` (或内核 `drivers/staging/android/lowmemorykiller.c`)。
- **关键代码逻辑**：`lmkd` (Low Memory Killer Daemon) 在进行内存压力评估和目标选择时，读取的是 `/proc/<pid>/statm` 中的 `RSS`（Resident Set Size），并结合 `oom_score_adj` 来决定杀哪个进程。
- **运行原理说明**：计算 `USS` 需要遍历进程的所有页表（VMA，如读取 `/proc/<pid>/smaps`），这在系统内存压力极大、CPU 繁忙时开销过高，会产生明显延迟。因此，`lmkd` 在运行时**绝对不会**去计算或参考 `USS`。`USS` 纯粹是一个面向开发者的线下调试指标（用于查内存泄漏）。
- **核验结论**：将线下调试指标（USS）张冠李戴到了系统底层的实时调度机制（LMKD）上，这会给读者建立错误的系统运行模型。
- **建议修正方向**：明确指出 LMKD 依赖 `oom_score_adj` 选择目标，依赖 `RSS` (或 page cache 等内核统计) 判断阈值。`USS` 仅供开发者做内存泄漏排查参考，系统底层杀进程时并不使用它。

## 五、P1 问题（重要缺失）
- [P1][原理链完整性][dumpsys window：窗口层级与焦点]
- **原文问题**：“当用户报告"点了没反应"或"触摸不灵敏"时，可能是焦点不在预期的窗口上。`mCurrentFocus` 显示当前获得输入焦点的窗口”
- **源码 / 一手资料锚点**：AOSP `frameworks/base/services/core/java/com/android/server/wm/WindowManagerService.java` 以及 InputDispatcher。
- **缺失内容**：没有区分 Window Focus (`mCurrentFocus`) 和 Input Focus 的关系，也没有提到 `dumpsys input`。
- **运行原理说明**：遇到“点了没反应”，虽然 `dumpsys window` 能看 `mCurrentFocus`，但真正决定触摸事件去向的是 `InputDispatcher` 里的焦点窗口。虽然大多数时候两者一致，但在排查 Input ANR 或触摸穿透、拦截时，结合 `adb shell dumpsys input` 看 `FocusedWindow` 才是最完整的证据链。
- **为什么这是重要缺失**：只看 `dumpsys window` 往往无法解释“窗口明明有焦点但收不到触摸”的幽灵 Bug（如透明悬浮窗拦截了事件，或者 InputChannel 没注册好）。
- **建议补充方向**：在讲焦点排查时，补充一句联动 `dumpsys input` 查看输入系统真实焦点的建议，补齐事件分发的排查闭环。

## 六、P2 问题（建议改进）
- [P2][原理链完整性][dumpsys activity：进程优先级与 ANR]
- **原文问题**：文章提到了 `ProcessList.java` 中的 `FOREGROUND_APP_ADJ=0`，`VISIBLE_APP_ADJ=100`。
- **证据或观察依据**：AOSP `frameworks/base/services/core/java/com/android/server/am/ProcessList.java`。
- **问题描述**：文章没有交代 Android 10 (API 29) 之前，`VISIBLE_APP_ADJ` 是 `1`，而现在是 `100`。虽然这不算大错，但由于有很多老文章还在说 `adj=1`，可能会让读者困惑。
- **建议**：加一句话说明 Android 10+ 为了更细粒度的控制，将 ADJ 数值整体放大了（例如从 1 变成了 100），但逻辑优先级顺序（前台 > 可见 > 感知 > 后台）保持不变。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|---------|-------------|
| lmkd 与 PSI (Pressure Stall Information) | 高 | Android 10 之后 lmkd 大量使用 PSI 替代旧的 minfree 机制进行内存压力监控，建议未来单开一节讲解 PSI 机制与 lmkd 的联动。 |

## 八、外部核验建议
- 搜索关键词：`Android 15 SurfaceFlinger Frontend LayerSnapshot dumpsys`
- 建议查 AOSP / 官方文档：虽然文中正确指出了 Android 15 Frontend 架构引入了 `Composition list`，但建议在实际 AOSP 15 分支中再验证一下 `dumpsys SurfaceFlinger --list` 命令是否在新架构下仍然可用，或是否被其他参数取代。

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **章节**：14.4
- **严重级别**：P0
- **问题类型**：原理断裂 / 事实错误
- **位置**：dumpsys meminfo：关键指标 -> USS 段落
- **问题描述**：原文称 LMK 在选择杀进程时会参考 USS，这是严重的事实错误。LMKD 运行时只看 oom_score_adj 和 RSS，计算 USS 的代价太高，不会被内核或 lmkd 采用。
- **建议修正方向**：删掉“LMK 在选择杀谁时，会参考这个值”的说法。改为：USS 是帮助开发者精确定位内存泄漏的最准确指标。
- **建议补充的验证来源**：AOSP `system/memory/lmkd/lmkd.cpp`

### 9.2 知识盲区清单（供后续研究）
- **章节**：14.4
- **盲区描述**：现代 Android (10+) 中 LMKD 依赖内核的 PSI (Pressure Stall Information) 指标来触发杀进程，而不是单纯看内存水位。
- **重要程度**：高
- **建议研究方向**：研究 `psi` 节点在 dumpsys 或 lmkd 日志中的体现，这在分析最新的“无故杀进程”问题时非常关键。
- **可能关联章节**：系统内存管理 / LMKD 专门章节

### 9.3 一般建议清单（非阻断）
- **章节**：14.4
- **问题类型**：内容补充
- **位置**：dumpsys window 段落
- **问题描述**：只靠 dumpsys window 排查“点了没反应”不够，可能会遗漏 input 层面的拦截。
- **建议**：在排查焦点时，提及 `dumpsys input`，因为这才是事件投递的最终真理。

### 9.4 可复用知识资产（高价值新增知识）
- **章节**：14.4
- **一手资料链接**：AOSP `frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp`
- **关键源码路径**：Frontend 架构相关的 `Composition list`。
- **可直接复用的技术结论**：Android 15 的 SurfaceFlinger 采用了新的 Frontend 架构，将图层可见性计算和合成解耦。`dumpsys SurfaceFlinger` 的输出变成了 `Composition list` 和 `Input list`，每个 Layer 的信息更加结构化（包含 bounds, input 标志, toDisplayTransform），不再是以前的扁平结构。
- **为什么这条知识值得保留**：这是最新的 AOSP 架构变更，对那些还在用老版本经验看 SF 树的开发者具有极大的提示价值。

## 十、下一候选章节
- 建议优先审查与内存泄漏或 Jank 相关的章节（如 `ch14-other-tools/03-heapprofd.md`，如果有的话）。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-21-14-04-dumpsys-external-review.md`