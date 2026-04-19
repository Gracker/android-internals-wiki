# AIW 自动 Review 任务报告 (8.2 App 启动全流程)

## 一、目标发现结果
- **扫描范围**：`src/part2-performance/ch08-responsiveness/`
- **候选章节**：
  1. `02-app-launch.md` | 状态：ready-for-review, task9: pending
- **最终选择**：`02-app-launch.md`
- **选择理由**：响应速度核心章节，且已通过 Task 6，具备深度技术审计条件。

## 二、总体结论
- **总体技术评分**：3.0/5
- **是否建议回炉**：是
- **主要风险**：关于热启动 Logcat 日志的断言与 AOSP 实际行为矛盾 (P0)；严重缺失 Android 15 关键启动 API `ApplicationStartInfo` (P1)。
- **评分理由**：存在 P0 级事实错误，且版本演进覆盖（Android 15）存在重大缺失。
- **本轮 review 覆盖范围**：冷/温/热启动链路、度量指标、源码调用链、Android 15 新特性。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 2/5 | 1 (P0) |
| 原理链完整性 | 4/5 | 1 (P1) |
| 版本差异覆盖 | 2/5 | 1 (P1) |
| 知识盲区 | 3/5 | 2 |
| 数据/案例支撑 | 4/5 | 0 |
| 交叉引用一致性 | 5/5 | 0 |

## 四、P0 问题（事实错误）
- **[P0][源码准确性][热启动小节]**
- **原文问题**：原文称“logcat 中的 'Displayed' 信息在热启动时不会打印”。
- **源码锚点**：`ActivityMetricsLogger.java` -> `logAppTransitionFinished`。
- **核验结论**：只要满足 Activity 从 `STOPPED` 状态通过 Transition 回到 `RESUMED` 且完成绘制，系统**会**打印 `Displayed` 日志。只有当 Activity 仅在 Pause 态（仍可见）或启动被中止时才不打印。
- **建议修正方向**：修正断言，说明热启动同样有 `Displayed` 日志，但耗时通常在 50-200ms 级别。

## 五、P1 问题（重要缺失）
- **[P1][版本差异覆盖][度量方法小节]**
- **原文问题**：完全缺失 Android 15 `ApplicationStartInfo` 介绍。
- **缺失内容**：Android 15 引入了专门用于读取启动元数据的 API。
- **源码锚点**：`android.app.ApplicationStartInfo`。
- **重要性**：这是 Android 15 对开发者最有价值的性能 API，不应遗漏。
- **建议补充方向**：增加“Android 15+ 结构化启动监控”小节，介绍 `getHistoricalProcessStartReasons`。

- **[P1][知识盲区][度量方法小节]**
- **原文问题**：缺失对 Android 12+ SplashScreen 机制对“第一帧”定义的微调。
- **建议补充方向**：说明 SplashScreen 完成展示的时刻与 TTID 的关系。

## 六、P2 问题（建议改进）
- **[P2][原理链完整性][首帧绘制路径]**
- **原文问题**：将 TTID 终点等同于 `queueBuffer`。
- **描述**：系统内部计时终点是 WMS 的 `notifyWindowsDrawn` 回调。
- **建议**：在深度原理层补充 WMS 对“窗口绘制完成”的判定逻辑。

## 九、可闭环输出

### 9.1 回炉问题单
- **[P0]** 修正热启动 Logcat 日志打印的错误描述。
- **[P1]** 补充 Android 15 `ApplicationStartInfo` 相关度量手段。
- **[P1]** 补充 `ProfilingManager` 在 Android 15 启动分析中的应用。

### 9.4 可复用知识资产
- **源码锚点**：`com.android.server.wm.ActivityMetricsLogger` 负责计算 TTID/TTFD 并驱动日志输出。
- **技术结论**：在 Android 15 中，`reportFullyDrawn` 信号现在会同步写入 `ApplicationStartInfo` 的时间戳列表，供 App 自行回溯分析。
- **Perfetto 观察点**：寻找 `ActivityMetricsLogger:notifyWindowsDrawn` 标记点作为系统认可的 TTID 终点。

## 十、下一候选章节
- `03-launch-optimization.md`

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-19-10-02-app-launch-external-review.md`
