# Android 信息漏斗（FUNNEL）

## 触发条件

本任务由各信息采集类 cron task 在完成自身主任务后调用。**不是独立 task**。

## 目的

将分散在各信息采集 task 中的 Android/Linux 内核/系统性能/Perfetto 相关内容，汇总到一个统一的每日文件中，供 AIW 下游消费。

## 执行步骤

### 1. 判断相关性

检查本 task 本次产出的所有条目（文章、论文、推文、提交、报告等），判断是否与以下领域相关：

- **Android 系统开发**：Framework、ART、Binder、Zygote、SystemServer、PackageManager 等
- **Android 性能优化**：启动速度、滑动流畅度、内存管理、功耗、ANR/Crash、存储 I/O、网络优化
- **Linux 内核**：调度器（CFS/EAS）、内存管理（lmk/zRAM/memcg）、文件系统（f2fs/ext4）、驱动
- **渲染与图形**：SurfaceFlinger、BufferQueue、VSync、Choreographer、Vulkan、OpenGL ES、GPU
- **Perfetto 与工具**：Perfetto、Simpleperf、Systrace、Android Studio Profiler
- **Android 新版本特性**：Android 16/17 API 变更、行为变更、新功能
- **AI × 手机**：端侧 AI 推理、NPU 优化、AI Agent 在手机上的应用
- **手机厂商技术**：OEM 定制优化、芯片平台（MTK/Qualcomm/Exynos）

### 2. 追加写入

如果存在相关内容，使用 `exec + python3 + pathlib + 绝对路径` 追加写入当日汇总文件：

**文件路径**：`/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki/intake/daily-info/YYYY-MM-DD.md`

**格式**（每条一个条目）：

```markdown
## [来源 Task] 标题
- **来源**：{来源 Task 名称}
- **时间**：{YYYY-MM-DD HH:mm}
- **链接**：{URL}
- **摘要**：{80-180字详细摘要，包含：背景说明、核心变化、设计目的、数据支撑、影响分析}
- **推荐映射章节**：{ch01-ch17 中的具体章节，如不确定写"待分类"}
- **内容类型**：{论文/技术文章/代码提交/行业动态/官方文档}
- **相关标签**：{#渲染 #内存 #功耗 #启动 #ANR #Perfetto 等}
```

**文件头部**（如果当天文件不存在，创建时加）：

```markdown
# Android Daily Info · YYYY-MM-DD

> 本文件由各信息采集 task 自动追加，供 AIW task8 消费归类。
```

### 3. 不相关则跳过

如果本 task 本次产出中没有 Android/Linux 相关内容，跳过，不创建空文件。

## 约束

- **严禁使用 write/edit 直接写 Obsidian/iCloud/~/Library 路径**，必须使用 exec + python3 + pathlib + 绝对路径
- 追加写入，不覆盖已有内容
- 摘要必须足够详细，让读者不点链接也能知道内容核心
- 推荐映射章节参考 AIW 的 `src/` 目录结构（ch01-architecture 到 ch17-oem）
- 如果同一条内容已被之前的 task 写入（按链接去重），跳过
