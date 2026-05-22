---
title: "用户设置对能耗的影响：亮度、刷新率与深色模式"
chapter: "11.7"
status: draft
applicable_versions: "Android 11 (API 30) - Android 17 (API 37)"
tags: [power, battery, display, refresh-rate, dark-mode, empirical-study]
related_chapters: ["2.18", "2.19", "5.6", "11.1", "11.2", "15.6", "25.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-22"
gap_source: "每日信息/研究论文/官方文档"
sources:
  - type: paper
    path: "https://arxiv.org/abs/2604.25587"
  - type: official
    path: "https://developer.android.com/topic/performance/power/battery-historian"
  - type: local
    path: "intake/daily-info/2026-05-22.md"
---

# 11.7 用户设置对能耗的影响：亮度、刷新率与深色模式

<!-- outline-start -->
## 要点

### 🔹 用户可控设置为什么会进入功耗模型
把亮度、刷新率、深色模式、省电模式、网络状态、视频分辨率和消息长度拆成可观测变量，说明它们如何影响屏幕、显示链路、CPU/GPU、网络和应用负载。

### 🔹 亮度是最稳定的高权重变量
基于 2026 年 arXiv 论文的 12,000+ 数据点建立阅读顺序：先讲屏幕亮度在不同 App 和场景里的主导地位，再说明 OLED/LCD、自动亮度和户外高亮模式的边界。

### 🔹 刷新率的收益和代价要按场景拆开
把静态阅读、短视频、列表滑动、游戏和视频播放分开，说明 60Hz、90Hz、120Hz 与自适应刷新率对体验、帧预算和显示功耗的不同影响。

### 🔹 深色模式不能被写成通用省电开关
整理论文中深色模式收益偏低的观察，结合 OLED 像素发光、页面配色、亮度档位和内容类型，建立“什么时候有效、什么时候只是视觉偏好”的判断边界。

### 🔹 视频分辨率、消息长度和网络状态的场景化影响
区分解码、网络传输、缓存命中和 UI 渲染四类成本，避免把“降低分辨率”直接等同于整机功耗下降。

### 🔹 测试设计：把用户设置写进功耗实验条件
给出功耗测试的变量控制清单：亮度、刷新率、深色模式、省电模式、网络制式、温度、初始电量、充电状态、App 版本和采样窗口。

### 🔹 产品策略：省电提示要给出适用条件
将实验结果转成应用侧可执行策略：什么时候提示降低亮度、什么时候建议 60Hz、什么时候不该用“开启深色模式可显著省电”这类笼统话术。

## 扩展

### 🔸 与 Android 自适应刷新率策略联动
结合 2.18、2.19 节，把用户刷新率设置、App `Surface.setFrameRate()`、RecyclerView 速度上报和系统 ARR 策略放在一张对照表里。

### 🔸 与 Battery Historian / Perfetto 采样口径联动
补充如何在 Battery Historian、Perfetto counter 和 Android Studio Profiler 中记录屏幕亮度、刷新率、温度和电量变化。

### 🔸 论文复现实验模板
提供 UIAutomator / Macrobenchmark / 手工复现实验的变量矩阵，后续可落成可运行脚本。

<!-- outline-end -->

> 本节内容待加工。
