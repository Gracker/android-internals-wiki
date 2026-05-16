---
title: "移动端 LLM 推理的 DVFS 与能效边界"
chapter: "5.13"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [android, dvfs, eas, adpf, llm, on-device-ai, power]
related_chapters: ["5.2", "5.4", "5.9", "5.11", "5.12", "11.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-16"
gap_source: "素材驱动/研究素材/官方文档"
gap_score: 17
sources:
  - type: paper
    path: "https://arxiv.org/abs/2507.02135"
  - type: material
    path: "论文/Android-2026-05-15-DVFS-LLM-Performance/03-精读.md"
  - type: official
    path: "https://source.android.com/docs/core/power/performance"
  - type: official
    path: "https://developer.android.com/games/optimize/adpf"
---

# 5.13 移动端 LLM 推理的 DVFS 与能效边界

<!-- outline-start -->
## 要点

### 🔹 LLM 推理负载与传统交互负载的差异
{待加工：区分 prefill、decode、CPU 调度、GPU/NN 加速与内存带宽压力。}

### 🔹 DVFS governor 在 CPU、GPU、内存之间的独立决策
{待加工：说明 EAS、cpufreq、GPU governor 与内存频率策略如何分别响应利用率。}

### 🔹 decode 阶段的频率误判与延迟放大
{待加工：基于 FUSE 论文整理 Pixel 7/7 Pro 上 GPU 降频、CPU 喂数不足、TPOT 上升的证据。}

### 🔹 能效目标下的频率组合选择
{待加工：整理 TTFT、TPOT、energy-per-token、热余量和频率锁定策略的取舍。}

### 🔹 ADPF、Power HAL 与应用可控边界
{待加工：区分公开 ADPF API、Power HAL 厂商实现、root/实验环境 frequency pinning 与普通 App 可用能力。}

### 🔹 端侧 AI 推理的验证方法
{待加工：给出 Perfetto、simpleperf、PowerStats、Monsoon/外接功耗仪、token 级日志的采集口径。}

## 扩展

### 🔸 FUSE 与 llama.cpp 的实验复现边界
{待补充：确认开源实现、设备约束、模型大小、输入长度分布和 SoC 泛化问题。}

### 🔸 NPU / GPU delegate 与 DVFS 联动
{待补充：结合 LiteRT、NNAPI / vendor delegate，整理不同执行后端的频率观测点。}

### 🔸 持续推理下的热衰减与用户感知指标
{待补充：把 token 延迟、温升、表面温度、帧率干扰和后台任务影响放入同一套验证表。}

<!-- outline-end -->

> 本节内容待加工。
