## [2026-06-25] 2.14 图形 API 演进与选择策略 — 知识盲区

### 盲区描述
WebGPU 在 Android 上的实际性能数据和限制细节，包括不同设备上的吞吐量对比、内存开销、与原生 Vulkan 实现的性能差异等具体量化数据。

### 重要程度
高

### 建议研究方向
- 收集 Jetpack WebGPU 在主流 Android 设备上的基准测试数据
- 分析 WebGPU vs Vulkan 在图像处理、ML inference、数据可视化等场景的性能差异
- 研究 WebGPU 在 Android 17 上的新特性和限制变化
- 收集 WebGPU 在不同 GPU 架构（Adreno、Mali、Immortalis）上的表现差异

### 关联章节
2.14, 14.8

---

## [2026-06-25] 25.4 WorkManager 实战与后台任务调度 — 知识盲区

### 盲区描述
Android 16/17 具体的 job quota 数量和配额调整算法，包括不同 standby bucket 下的可用 job 数量上限、quota 耗尽后的恢复机制、以及前台服务对 quota 的影响等实现细节。

### 重要程度
高

### 建议研究方向
- 分析 AOSP JobSchedulerService 中的 quota 管理源码实现
- 收集不同 standby bucket 下的实际 job 数量限制数据
- 研究 long-running worker 与普通 job 的 quota 消耗差异
- 分析 Android 17 WIU 权限对前台服务 quota 的影响机制

### 关联章节
25.2, 25.4, 5.10

---

## [2026-06-25] 25.4 WorkManager 实战与后台任务调度 — 知识盲区（本轮新增）

### 盲区描述
Android 16/17 具体的 job quota 数量和配额调整算法，包括不同 standby bucket 下的可用 job 数量上限、quota 耗尽后的恢复机制、以及前台服务对 quota 的影响等实现细节。

### 重要程度
高

### 建议研究方向
- 分析 AOSP JobSchedulerService 中的 quota 管理源码实现
- 收集不同 standby bucket 下的实际 job 数量限制数据
- 研究 long-running worker 与普通 job 的 quota 消耗差异
- 分析 Android 17 WIU 权限对前台服务 quota 的影响机制

### 关联章节
25.2, 25.4, 5.10

---

## [2026-06-25] 19.19 PerfDog — 知识盲区

### 盲区描述
PerfDog工具在Android 8-17各版本间的功能变化、API兼容性差异、采集指标完整性变化等具体信息，包括不同Android版本下权限要求、数据采集方式、指标可用性的变化细节。

### 重要程度
中

### 建议研究方向
- 分析PerfDog官方文档中各Android版本的功能变化说明
- 收集Android 13-17版本间权限限制对数据采集的影响数据
- 研究不同Android版本下GPU温度、功耗等指标的采集准确性差异
- 对比PerfDog在高通、联发科、三星等不同SoC上的表现一致性

### 关联章节
19.0, 19.19