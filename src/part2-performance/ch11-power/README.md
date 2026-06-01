# 第 11 章：功耗

功耗问题和卡顿、启动慢不同，它更像一种“慢慢积累出来的坏体验”。

用户不一定会说“这个应用的调度策略不好”，但会说“怎么这么费电”“为什么挂后台也掉电”“为什么一发热就开始卡”。  
所以功耗从来不是孤立维度，它和调度、thermal、后台限制、WakeLock、网络行为经常是绑在一起的。

这一章会从用户真正感知到的耗电问题切入，再回到系统和应用分别能做什么。

## 本章内容

- Android 功耗模型
- App 耗电优化
- 系统级功耗优化
- 案例集

## 阅读建议

- 如果你是 App 开发者，先看功耗模型和 App 侧优化。
- 如果你更靠近系统或整机分析，系统级功耗优化和案例会更有价值。

## 延伸阅读

### 面向 SmartPerfetto 的 Android 功耗全链路分析研究报告
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/ 面向 SmartPerfetto 的 Android 功耗（Power:Battery:Energy）全链路分析研究报告.md
- 类型：DeepResearch 调研结果
- 摘要：面向 SmartPerfetto 功耗分析能力建设全链路参考，梳理 6 类 Perfetto 功耗信号（power rails/ODPM、battery counters、CPU freq/idle、suspend/wakelock、sched+Wattson、network_packets），提出 power_analysis strategy+8-10 个技能设计，含 Android vitals 官方阈值。
- 注入时间：2026-06-01
- 价值：首次系统化将 Perfetto 功耗观测信号映射为可执行 SQL 规则集，对功耗自动化分析有方法论级贡献
