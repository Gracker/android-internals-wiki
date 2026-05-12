# AIW 自动 Review 任务报告

## 一、目标发现结果
- 扫描范围：`src/part3-tools/ch15-methodology/07-aosp-reading.md`
- 候选章节：`15.7 AOSP 代码阅读`
- 最终选择：`15.7 AOSP 代码阅读`
- 选择理由：本章是源码分析的方法论指引，对 cs.android.com 和本地 AOSP 浏览做了介绍，需核验实战可行性。

## 二、总体结论
- 总体技术评分：4.5/5
- 是否建议回炉：是（需补充一个 P1 级的 IDE 导入盲区）
- 主要风险：对 Android Studio 导入 AOSP 源码的步骤描述过于简化，可能误导读者直接用 AS 打开目录。
- 评分理由：文章非常棒地梳理了从 Perfetto Tag（`ATRACE_CALL` / `Trace.traceBegin`）反查源码的路径，这在日常分析中极具价值。但在本地 AOSP 导入 IDE 的实操上有重要缺失。
- 闭环建议：进入结构化修正队列，补充 AIDEGen 相关内容。
- 本轮 review 覆盖范围：cs.android.com 使用、核心源码目录字典、反查路径、IDE 导入、Gerrit 溯源。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 5.0/5 | 0 |
| 原理链完整性 | 4.5/5 | 0 |
| 版本差异覆盖 | 4.5/5 | 0 |
| 知识盲区 | 3.5/5 | 1 |
| 数据/案例支撑 | 4.5/5 | 0 |
| 交叉引用一致性 | 5.0/5 | 0 |

## 四、P0 问题（事实错误）
（无）

## 五、P1 问题（重要缺失）
- [P1][知识盲区][Android Studio 导入 AOSP 的机制]
- **原文问题**："用 Android Studio 打开 `frameworks/base` 目录。等待索引完成"。
- **核验结论**：如果直接用 Android Studio 打开 `frameworks/base`，由于缺乏 Gradle 或 CMake 构建脚本，AS 将无法正确解析依赖关系，大量代码会报红。官方推荐的做法是使用 AOSP 内置的 `AIDEGen` 工具（Android 10+ 引入），通过 `aidegen frameworks/base -i s` 命令自动生成 IDE 配置文件并启动 AS。
- **建议补充方向**：修正 AS 导入 AOSP 的步骤，说明 `AIDEGen` 或传统的 `idegen` 工具的必要性，防止读者在实操时卡住。

## 六、P2 问题（建议改进）
（无）

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|----------|--------------|
| AIDEGen 的使用方法 | 高 | 查阅 `source.android.com` 关于 AIDEGen 的最新文档，并补充其实战命令 |

## 八、外部核验建议
- 搜索关键词：`AOSP AIDEGen Android Studio code search`

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **章节**：15.7
- **严重级别**：P1
- **问题类型**：实操步骤缺失
- **位置**：IDE 配置建议
- **问题描述**：遗漏了 AIDEGen 工具，直接用 AS 打开目录无法获得正常语法跳转和补全体验。
- **建议修正方向**：补充使用 AIDEGen 导入 AOSP 到 Android Studio 的标准命令和步骤。

### 9.4 可复用知识资产（高价值新增知识）
- **章节**：15.7
- **可复用的技术结论**：文中关于“Perfetto 中的 slice 命名规则（如 `ClassName::methodName` 来自 `ATRACE_CALL`）与搜索方式”的总结，可以直接作为阅读 Trace 时的字典型知识复用。