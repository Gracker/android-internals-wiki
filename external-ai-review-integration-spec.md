# 外部 AI Review 结果整合规范

> 用途：定义如何消费 Gemini 等外部 AI 的 review 结果，并把结果整合进 AIW 流水线。
> 目标：外部 review 结果不只是“指出问题”，还要沉淀为可复用知识资产，并能被后续 AI 或人工直接闭环。

---

## 1. 设计原则

默认由 `openclaw-tasks/task12-external-review-integration.md` 定时扫描并自动整合外部 review 结果。

外部 AI 的 review 结果按四路处理：

1. **回炉问题单**
   - 用于必须修复的技术问题
   - 去向：`metadata/queue.json`

2. **知识盲区 / 后续研究项**
   - 用于需要继续补研究的一类问题
   - 去向：`intake/research-gaps.md`

3. **一般修正建议**
   - 用于非阻断但值得补强的建议
   - 去向：`intake/suggestions.md`

4. **可复用知识资产**
   - 用于外部 AI review 中发现的高价值一手结论、源码锚点、版本差异、trace 观察点、资料索引
   - 去向：
     - 优先写入章节旁注 / review 日志 / 专门的外部 review 归档
     - 若价值高，可进一步进入 wiki / 章节参考资料 / 研究素材池

外部 AI review 的价值不应止于“发现错”，还应尽量贡献：
- 一手资料索引
- 源码级证据链
- 可直接复用的技术结论
- 可指导后续加工的研究方向

---

## 2. 外部 Review 结果的标准拆解

当收到外部 AI 的 review 报告时，整合 AI 必须先把结果拆成以下 4 类：

### 2.1 回炉问题单（必须修）
判定条件：
- P0 事实错误
- P1 重要缺失
- 会直接影响章节技术可信度
- 会导致读者学错 / 用错 / 分析错

典型问题：
- AOSP 路径错误
- 方法签名错误
- 原理链关键缺环
- 用旧版本行为解释新版本
- 声称的机制无法被源码或官方资料支撑

### 2.2 知识盲区 / 后续研究项
判定条件：
- 当前章节不一定错，但覆盖明显不足
- 后续继续研究会显著增强章节价值
- 更适合进入“研究补强”而非立刻改稿

典型问题：
- Android 14/15/16/17 的版本差异未梳理完整
- OEM 差异、边界条件、特殊场景未覆盖
- Perfetto / trace 观察点未沉淀为方法

### 2.3 一般修正建议
判定条件：
- 不会直接导致技术错误
- 但补完后质量更强
- 更适合轻量修正或顺手补齐

典型问题：
- 缺少 benchmark / trace 案例
- 交叉引用不一致
- 某处结论可以补更强证据

### 2.4 可复用知识资产
判定条件：
- 外部 AI 在 review 中给出了高价值新增知识
- 不只是“这有问题”，而是给出了：
  - 一手资料路径
  - 关键源码调用链
  - 新版本行为差异
  - Trace 观察方法
  - 对某个机制更强的理解框架

典型例子：
- `InputDispatcher.cpp` 在 Android 14 中的 timeout 路径变化
- `Choreographer` 某个行为在 Android 17 中的具体源码锚点
- `Perfetto` 中识别某类卡顿的稳定观察模式
- 某个系统机制的真实上下游调用链

这类内容不能只丢进 suggestions，应该尽量被沉淀下来复用。

---

## 3. 四路落盘规范

所有章节号、标题和路径必须以 `metadata/v1.0-definition.md`、`src/SUMMARY.md` 及目标文章 frontmatter 为准。活动 queue 条目必须包含可解析到现有正文的 `target_path`；无法唯一定位时只记录待人工映射，不得猜测路径或创建章节。

## 3.1 回炉问题单 → `metadata/queue.json`

写入字段建议：

```json
{
  "section": "3.3",
  "target_path": "src/part1-fundamentals/ch03-input/03-gesture-navigation.md",
  "section_title": "InputDispatcher ANR 机制",
  "priority": 95,
  "reason": "[External Review] 源码路径与 ANR 判定链路存在技术风险，需回炉修正",
  "review_issues": [
    {
      "type": "源码错误",
      "location": "源码引用段落",
      "detail": "InputDispatcher 相关路径/锚点不准确",
      "suggestion": "基于 cs.android.com 重新核对 InputDispatcher / InputManagerService 调用链",
      "evidence": [
        "cs.android.com 路径",
        "source.android.com 相关文档"
      ]
    }
  ],
  "added_by": "external-ai-review",
  "status": "pending"
}
```

### 去重规则
- 同章节已有 P95 / P90 回炉项时：合并 `review_issues`
- 同类问题重复出现时：保留证据更强、描述更具体的一条，其他作为补充 evidence

---

## 3.2 知识盲区 → `intake/research-gaps.md`

模板：

```markdown
## [YYYY-MM-DD] 3.3 InputDispatcher ANR 机制 — 知识盲区

### 盲区描述
Android 14 之后 Input timeout 相关实现与历史版本差异未覆盖。

### 重要程度
高

### 建议研究方向
- Android 13/14/15 中 InputDispatcher timeout 判定逻辑变化
- system_server 与 app 视角下的 Input ANR 差异
- Perfetto 中可观测的 Input timeout 链路

### 关联章节
- 3.1
- 3.2
- 3.3

### 外部 review 来源
- Gemini 外部 review
```

---

## 3.3 一般建议 → `intake/suggestions.md`

模板：

```markdown
## [External Review] 3.3 InputDispatcher ANR 机制 — YYYY-MM-DD
- **类型**：数据支撑
- **位置**：ANR 现象分析段
- **问题**：缺少 Perfetto / trace 片段支撑
- **建议**：补一个 Input timeout 触发前后的 trace 观察说明
- **来源**：Gemini 外部 review
```

---

## 3.4 可复用知识资产 → 推荐两种落点

### 方案 A：外部 review 归档文件（推荐）
目录建议：
- 活跃区：`logs/external-review/`
- 已消费归档区：`logs/external-review/archive/`
- 文件名：`YYYY-MM-DD-HH-{章节号}-external-review.md`

模板：

```markdown
# 外部 AI Review 归档 · 3.3 InputDispatcher ANR 机制

## 可复用知识资产

### 1. 一手资料索引
- cs.android.com: {路径}
- source.android.com: {链接}
- perfetto.dev: {链接}

### 2. 源码锚点
- 文件：{路径}
- 类：{类名}
- 方法：{方法名}
- 作用：{为什么重要}

### 3. 版本差异摘要
- Android 13：...
- Android 14：...
- Android 15：...

### 4. 可直接复用的技术结论
- 结论 1：...
- 结论 2：...

### 5. Trace / Perfetto 观察点
- 观察点 1：...
- 观察点 2：...
```

### 方案 B：沉淀到章节参考资料 / wiki
如果某条知识价值足够高，可以进一步进入：
- 对应章节的参考资料段
- wiki / 研究笔记 / Android 机制知识库

---

## 4. 为什么要保留“知识资产”这一路

如果只把 Gemini 的结果当成“问题清单”，价值会损失很大。

理想情况是：
- 它发现问题
- 它还顺手贡献一手资料索引
- 它还提供源码级锚点
- 它还提炼版本差异和 trace 观察方法

这些东西不该只用于“修这一次稿”，还应该成为 AIW 后续可反复利用的素材。

所以整合 AI 必须把外部 review 的产出看成：
- 一部分是“错误修复驱动”
- 一部分是“知识增量输入”

---

## 4.1 消费后的归档规则

当一份 external-review 的核心内容已经被拆解并写入：
- `queue.json`
- `research-gaps.md`
- `suggestions.md`
- 或已经驱动过对应章节的一轮修稿 / 重审

则应将该 external-review 文件从：
- `logs/external-review/`
移动到：
- `logs/external-review/archive/`

目的：
- 避免后续 task 把同一份 review 当成新输入重复消费
- 保持活跃区只包含真正待处理的 external-review

如果只是部分消费，且仍希望后续 task 继续参考，则暂不归档。

### 4.2 归档执行者

默认由**后续整合 / 消费环节**执行归档，而不是由外部 AI 在生成 review 时立刻归档。

推荐时机：
1. external-review 结果已被写入 queue / research-gaps / suggestions 之后
2. 或某章节已经完成一轮基于 external-review 的回炉 / 重审之后

### 4.3 归档辅助脚本

可使用：
`/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki/scripts/external_review_archive_helper.py`

用法：
- 查看状态：
  `python3 scripts/external_review_archive_helper.py status`
- 归档已消费文件：
  `python3 scripts/external_review_archive_helper.py archive`

## 5. 整合优先级

整合时按以下顺序处理：

1. **先抽取 P0 / P1** → queue
2. **再抽取知识盲区** → research-gaps
3. **再抽取一般建议** → suggestions
4. **最后抽取高价值知识资产** → external-review archive / wiki

原因：
- 先保证硬问题闭环
- 再保证研究增量不丢
- 最后把高价值结论沉淀下来

---

## 6. 模拟闭环示例

### 假设 Gemini review 发现：
- `InputDispatcher.cpp` 路径引用不准（P0）
- ANR timeout 版本差异没讲清（P1）
- Perfetto 观察点缺失（P2）
- Android 14 之后 timeout 行为变化值得深入研究（知识盲区）
- 给出了 `cs.android.com` 关键源码路径和 Android 14 相关一手资料（知识资产）

### 后续整合结果：
- `queue.json`：写入源码错误 + 原理链 + 版本差异回炉项
- `research-gaps.md`：写入 Android 14 timeout 差异研究项
- `suggestions.md`：写入 Perfetto 观察点补强建议
- `logs/external-review/...`：保存一手资料链接、源码锚点、版本差异摘要

### 然后后续 AI：
- 回炉 AI 修正文
- 研究 AI 补素材
- 精修 AI 顺手补 trace / 交叉引用
- 修完后重新进入 review

这就形成闭环。

---

## 7. 整合 AI 的硬规则

1. 不要把所有外部 review 结果都塞进 suggestions
2. 不要让高价值源码锚点在整合时丢失
3. 不要只保留“问题”，要尽量保留“证据”和“新知识”
4. 同一个外部 review 的结果，允许同时进入多路：
   - 既进 queue
   - 又进 research-gaps
   - 同时保留知识资产归档
5. 外部 AI 不需要知道内部 task 名称，整合 AI 负责做最后映射

---

## 8. 推荐配套动作

为了让这条链更稳，建议：
- 给外部 AI review 规范新增“可复用知识资产输出”要求
- 新建 `logs/external-review/` 目录作为归档池
- 后续加工 AI 在修稿时优先参考对应 external-review 归档
