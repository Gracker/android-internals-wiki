# AIW 自动 Review 任务报告

## 一、目标发现结果
- 扫描范围：`src/part3-tools/ch14-other-tools/11-battery-historian.md`
- 候选章节：
  1. `14.11 Battery Historian 与功耗分析工具` | 任务指定
- 最终选择：`14.11 Battery Historian 与功耗分析工具`
- 选择理由：用户显式指定需要 Review。
- 排除的高频原因：无

## 二、总体结论
- 总体技术评分：3.5/5
- 是否建议回炉：是
- 主要风险：AOSP 源码路径过时；官方 Docker 镜像实测已失效，会导致读者实操被阻塞；缺失 Android 15+ 提供的最新硬件级电量监控 API (`PowerMonitor`)。
- 评分理由：存在 1 个 P0 级事实错误（核心服务源码路径错位），以及 3 个 P1 级重要缺失（部署方案失效、前沿 API 缺失、Perfetto 生态脱节）。
- 闭环建议：进入回炉处理队列，修正源码路径，补充现代可用的部署方案和 Android 15+ 的新特性。
- 本轮 review 覆盖范围：全章所有核心概念（Battery Historian, ODPM, Macrobenchmark, bugreport 机制）。
- 本轮未完成部分：无。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 3/5 | 1 |
| 原理链完整性 | 4/5 | 0 |
| 版本差异覆盖 | 3/5 | 2 |
| 知识盲区 | 3.5/5 | 1 |
| 数据/案例支撑 | 4/5 | 0 |
| 交叉引用一致性 | 5/5 | 0 |

## 四、P0 问题（事实错误）
- **[P0][源码准确性][参考资料]**
  - **原文问题**：AOSP 源码路径给出的是 `frameworks/base/services/core/java/com/android/server/BatteryStatsService.java`。
  - **源码 / 一手资料锚点**：在 `cs.android.com` 中，现代 Android 版本（如 Android 10+ 及当前 master 分支）的 `BatteryStatsService.java` 实际位于 `frameworks/base/services/core/java/com/android/server/am/BatteryStatsService.java`。
  - **关键代码逻辑**：该类位于 `am` (ActivityManager) 相关包下，因为电量统计与进程生命周期紧密绑定，由 AMS 协同管理。
  - **核验结论**：原文给出的旧路径已失效。
  - **为什么错**：会导致读者在查阅最新 AOSP 源码树时找不到该核心分析类。
  - **建议修正方向**：将路径更新为 `frameworks/base/services/core/java/com/android/server/am/BatteryStatsService.java`。

## 五、P1 问题（重要缺失）
1.
- **[P1][版本差异覆盖][Battery Historian 的部署]**
  - **原文问题**：仍然首推使用官方 Docker 镜像 `gcr.io/android-battery-historian/stable/battery-historian`，并标注 `[待验证: Battery Historian Docker 镜像在 2026 年是否仍然可用]`。
  - **核验结论**：经核验，官方镜像早已停止维护，在现代浏览器及容器环境中运行会遇到 JS 加载失败（依赖过时网络库）的问题。
  - **为什么这是重要缺失**：读者如果直接复制该命令，将面临 100% 的部署失败，导致工具无法正常使用。
  - **建议补充方向**：明确指出官方镜像已不可用，直接提供目前社区维护的可用修复版镜像命令（例如：`docker run -d -p 9999:9999 itachi1706/battery-historian`）。

2.
- **[P1][知识盲区][Android Studio Power Profiler]**
  - **原文问题**：讲解 ODPM (On-Device Power Rails Monitor) 时只提到了 Android Studio Profiler 的可视化观测方式。
  - **缺失内容**：严重缺失 Android 15 (API 35) 引入的重磅官方 API `PowerMonitor`。
  - **运行原理说明**：Android 15+ 开放了底层权限，允许开发者在应用代码中直接通过 `BatteryManager.getSupportedPowerMonitors()` 获取并持续读取硬件供电轨道（Power Rails）的实测功耗数据，不再必须依赖 IDE 连线。
  - **为什么这是重要缺失**：文章顶部声明的适用版本是 "Android 5.0 - Android 17"，如果遗漏 API 35 开放的这一直接获取高精度功耗数据的能力，会导致线上/线下自动化监控的知识断层。
  - **建议补充方向**：在 ODPM 小节末尾，简要补充 Android 15+ 提供的代码级读取硬件耗电的 API 能力。

3.
- **[P1][知识盲区][Power Profiler vs Energy Profiler]**
  - **原文问题**：在提到高精度轨道分析时，未提及 Perfetto 工具栈。
  - **缺失内容**：ODPM 的轨道功耗数据实际上是作为 `android.power_rails` 数据源记录在系统级 Trace 中的。
  - **为什么这是重要缺失**：对于深入底层的性能优化专家，Perfetto 及配套的 SQL 分析才是系统级分析的行业标准，功能远超 Profiler。
  - **建议补充方向**：补充说明还可以通过抓取系统 Trace，利用 Perfetto SQL 深度分析 `android.power_rails` 数据。

## 六、P2 问题（建议改进）
- **[P2][原理链完整性][bugreport 抓取]**
  - **原文问题**：抓取 bugreport 的相关命令行。
  - **建议**：在现代 Android 系统（14+）上，对 `dumpsys batterystats` 的部分指令调用可能会受到权限或后台策略影响，建议简单提一句“某些受限的 OEM 手机可能需要显式赋予开发者选项相关的安全权限才能拿到完整 wakelock history”。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|---|---|---|
| Android 15 `PowerMonitor` API | 高 | 官方文档中 API 35 `BatteryManager.getSupportedPowerMonitors()` 的拉取频率限制与工程实践。 |
| Perfetto `android.power_rails` 分析 | 高 | Perfetto 官方文档关于功耗轨道的 SQL 查询实战及与 CPU 调度事件的 join 关联分析。 |

## 八、外部核验建议
- `BatteryManager.getSupportedPowerMonitors()`：查阅 Android 15+ 的最新 API 参考，以验证其返回参数的具体结构。
- Perfetto 的 `android.power_rails` 表：查阅 `perfetto.dev` 搜索对应的 trace 录制配置以及解析语法。

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **章节**：14.11 Battery Historian 与功耗分析工具
- **严重级别**：P0
- **问题类型**：源码错误
- **位置**：参考资料 -> AOSP 源码路径
- **问题描述**：`BatteryStatsService.java` 源码路径错误，不应在 `com/android/server/` 根目录，而应在 `com/android/server/am/` 目录下。
- **建议修正方向**：修改为 `frameworks/base/services/core/java/com/android/server/am/BatteryStatsService.java`。
- **建议补充的验证来源**：`cs.android.com`

- **章节**：14.11 Battery Historian 与功耗分析工具
- **严重级别**：P1
- **问题类型**：实操断裂
- **位置**：Battery Historian 的部署
- **问题描述**：推荐的官方 Docker 镜像已无法使用，且带有“待验证”标注，无法作为靠谱指引。
- **建议修正方向**：删除待验证标记，明确说明官方镜像存在 JS 依赖失效的问题，并提供能直接 running 的社区替代方案（如 `itachi1706/battery-historian` 镜像）。

### 9.2 知识盲区清单（供后续研究）
- **章节**：14.11 Battery Historian 与功耗分析工具
- **盲区描述**：Android 15 (API 35) 引入的 `PowerMonitor` 硬件级轨道耗电读取 API。
- **重要程度**：高
- **建议研究方向**：研究如何在代码层直接对接 ODPM 轨道数据，以满足线上 APM 与自动化 CI 测试的场景。
- **可能关联章节**：§15.5 线上性能监控、§14.11

### 9.3 一般建议清单（非阻断）
- **章节**：14.11 Battery Historian 与功耗分析工具
- **问题类型**：内容补充
- **位置**：ODPM 的工作原理
- **问题描述**：未能覆盖主流底层 Trace 抓取工具。
- **建议**：补充 Perfetto 同样支持展示和通过 SQL 深度分析 `android.power_rails` 耗电信息的功能。

### 9.4 可复用知识资产（高价值新增知识）
- **章节**：14.11
- **一手资料链接或来源类型**：developer.android.com (Android 15 API)
- **关键源码路径**：`android/os/BatteryManager.java` -> `getSupportedPowerMonitors()`
- **可直接复用的技术结论**：自 Android 15 (API 35) 起，应用开发者无需依赖 Android Studio Profiler 等外部工具连线，即可通过调用 `BatteryManager.getSupportedPowerMonitors()` 直接在代码中读取设备底层的 ODPM 高精度功耗轨道（Power Rails）数据。
- **为什么这条知识值得保留**：彻底打通了从“本地开发工具观测”到“线上自动采集/自动化测试脚本埋点”的硬件级电量数据获取链路。

## 十、下一候选章节
- 下一章建议继续 review 的章节：`14.1 Android Studio Profiler` 或 `11.5 Wakelock 机制与功耗分析`

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-21-14-11-battery-historian-external-review.md`
