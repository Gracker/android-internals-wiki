---
title: "sched_ext 与 OEM BPF 调度器"
chapter: "17.4"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: ["sched-ext", "bpf", "oem", "scheduler", "kernel-6.12"]
related_chapters: ["5.1", "5.2", "5.7", "14.10", "17.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-15"
gap_source: "素材驱动/AOSP结构"
sources:
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-04-sched-ext-oplus-impl.md"
  - type: official
    path: "https://cs.android.com/android/platform/superproject/+/master:kernel/configs"
  - type: official
    path: "https://cs.android.com/android/_/android/kernel/common/+/8d5dd0a5a458f951f0fdc25aba0cb8329b121d51"
---

# 17.4 sched_ext 与 OEM BPF 调度器

<!-- outline-start -->
## 要点

### 🔹 sched_ext 在调度体系里的位置
- Linux 6.12 引入的 BPF 调度框架
- 与 CFS / EEVDF / EAS 的分工
- Android GKI 与 OEM vendor kernel 的边界

### 🔹 BPF 调度器入口与生命周期
- struct sched_ext_ops 的回调集合
- select_cpu / enqueue / dispatch 的职责
- 任务在 SCX core 与 BPF 调度器之间的状态迁移

### 🔹 OEM 落地形态
- OPPO / OnePlus hmbird_sched 的公开线索
- proc 开关、partial enable、CPU 控制参数
- 高通与联发科平台公开信息不足的边界

### 🔹 对前台交互性能的影响
- 帧率 boost 与任务分组
- RenderThread / binder / worker 线程的 CPU 选择
- 误配后可能出现的延迟和能耗代价

### 🔹 可观测与验证方法
- 确认内核配置和 proc 节点
- Perfetto sched / cpufreq / binder 联合观测
- 对比开启前后的延迟分布

### 🔹 工程使用边界
- AOSP 默认路径与 OEM 实验路径区分
- root / vendor kernel / SELinux 限制
- 不能把单一厂商策略写成 Android 通用机制

## 扩展

### 🔸 sched_ext 与 uclamp / cpuset 的关系
[待补充]

### 🔸 Android 17 Kernel 6.12 之后的默认启用可能性
[待补充]

### 🔸 厂商游戏模式与 BPF 调度器的验证清单
[待补充]

<!-- outline-end -->

> 本节内容待加工。
