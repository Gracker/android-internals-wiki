# 手动干预指令（高爷专用）

> 在这里写指令，由对应的活动任务解析并执行。当前章节路径与编号以
> `metadata/v1.0-definition.md` 和 `src/SUMMARY.md` 为准；禁止创建新章节。
> 每条指令一行，以 `- ` 开头。
> task1 处理后会在该行末尾追加 `[已处理 YYYY-MM-DD]` 标记。

## 指令格式

### 重新加工某章节（Task2A / Task2B 按正文状态执行）
```
- 加工 1.1（原因：需要补充xxx）
- 重写 2.4（原因：内容过时）
- 重加工 7.3（原因：review 后需修复文体）
```

### 重新审校某章节（task6 执行）
```
- 审校 1.1（原因：想再看一遍）
- 审校 3.2（原因：补充了新内容）
```

### 指定研究方向（task5 执行）
```
- 研究 Choreographer 与 VSync（章节 2.4）
- 搜索 Android 16 Binder 新变更（章节 1.4）
```

### 忽略/跳过某章节
```
- 跳过 12.3（原因：暂时不需要写）
```

### 标记定稿
```
- 定稿 1.1（确认可以发布）
```

---

## 未处理指令（写在这里）


- 补充 14.8 Mali Graphics Debugger（原因：高爷博客工具对比表提及，MTK 芯片使用 Mali GPU，与实际工作直接相关）
- 融入 14.10 eBPF 性能分析（原因：内核级性能分析重要性递增；现有正文已覆盖，不新增章节）
- 融入 14.31 FTrace / atrace / Perfetto 桥接（原因：现有正文已独立覆盖，不新增章节）
- 融入 26.1 与 15.9 可观测性框架（原因：补强 Log/Metric/Trace 三维度、数据获取方法和治理闭环）

- 融入 13.10 Perfetto SQL 分析（原因：官方 docs/analysis/ 有完整 SQL 语法/表/函数/标准库文档，是现有 SQL 实战文章的重要素材来源）
- 补充 附录A Android 版本变更（原因：官方 reference/android-version-notes 持续更新，是目前版本变更速查的最佳来源）
- 融入 15.5 线上监控（原因：Android Vitals 11 篇官方文档是线上监控最权威素材，目前覆盖最薄）
- 融入 15.6 性能测试（原因：Benchmark Tools 14 篇完整覆盖 Micro/Macro benchmark + JankStats + Baseline Profiles）
- 补充 11.1 Energy Profiler（原因：功耗分析覆盖较浅）
- 补充 14.1 AS Profiler 完整工具链（原因：官方 7 篇文档覆盖 CPU/Memory/Energy/Jank/APK Profiler）

- 融入 7.2 帧率切换卡顿（原因：高爷补充——相机60Hz切换到多任务120Hz导致可感知卡顿，素材见 intake/research-feeds/2026-04-06-gracker-jank-insights.md 素材1）
- 融入 7.1 步幅波动卡顿（原因：高爷补充——Trace无掉帧但感官卡顿，步幅不均匀问题，素材见 intake/research-feeds/2026-04-06-gracker-jank-insights.md 素材2）
- 融入 7.2 列表滑动VSync时间计算（原因：高爷补充——VSync时间取ms导致帧间隔波动，素材见 intake/research-feeds/2026-04-06-gracker-jank-insights.md 素材3）

---

## 已处理指令（自动归档）

（task1 处理后会移到这里）
