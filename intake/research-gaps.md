## [2026-07-14] 1.11 Zygote 机制与启动性能优化 — 知识盲区

### 盲区描述
缺少 Zygote 在低内存设备上的特殊处理机制，如 Zygote 如何配合 LMK、内存压力下的预加载策略调整、以及不同内存容量设备上的 fork 性能差异等关键场景。

### 重要程度
高

### 建议研究方向
- Zygote 与 low memory killer (lmkd) 的交互机制和协同策略
- 内存压力下 Zygote 预加载的动态调整机制
- 不同内存容量设备（1GB、2GB、4GB+）上的 fork 性能对比
- Zygote 在低内存场景下的资源优化和牺牲机制

### 关联章节
["1.1", "1.2", "2.1", "8.2"]

## [2026-07-14] 1.1 Android 分层架构 — 知识盲区

### 盲区描述
缺少分层架构在多设备形态（折叠屏、车载系统、Android Auto）上的适配差异，不同屏幕尺寸、输入方式、使用场景对架构分层的影响和优化需求。

### 重要程度
中

### 建议研究方向
- 折叠屏设备上 SurfaceFlinger 和窗口管理的架构适配
- 车载系统（Android Auto）的分层架构特点和性能优化方向
- 多形态设备（手机/平板/手表）间的架构差异和统一策略
- 新兴设备形态对传统五层架构的挑战和演进方向

### 关联章节
["1.2", "3.1", "4.1", "7.1"]

## [2026-07-15] 13.25 源码调研：PerfDog 的 Android 平台 GPU/性能采集底层数据源 — 知识盲区

### 盲区描述
缺少 GPU 计算单元负载分析，对不同计算单元（vertex/fragment/tessellation）负载分离的讨论。同时也缺少对 GPU 驱动厂商特有扩展接口（如高通 Adreno Profiler API）的系统性介绍。

### 重要程度
高

### 建议研究方向
- GPU 不同计算单元（vertex/fragment/tessellation）级别的负载分离分析方法
- 主流 GPU 厂商（高通 Adreno、ARM Mali、Samsung Xclipse）的性能扩展接口研究
- GPU 计算单元负载分析在性能优化中的实际应用案例
- 厂商特有 GPU 性能扩展与 AOSP 统一 API 的兼容性分析

### 关联章节
["13-perfetto-chapters", "3.1", "13.1"]## [2026-07-15] 18.21 EyeDropper API 与跨设备协作性能 — 知识盲区

### 盲区描述
1. **EyeDropper 与 MediaProjection 的内部权限隔离机制** - EyeDropper 如何在系统内部实现与 MediaProjection 不同的权限隔离，特别是对系统界面、第三方应用内容的安全边界识别
2. **系统取色器的安全实现机制** - secure window 和 protected buffer 的具体识别算法和裁剪实现，系统如何判断哪些内容需要保护

### 重要程度
高

### 建议研究方向
- 通过分析 AOSP 源码追踪 EyeDropper 宿主组件的实现
- 研究 MediaProjection 和 EyeDropper 在 SurfaceFlinger 层的差异处理
- 分析系统界面的隐私保护机制实现
- 测试不同安全场景下的实际行为表现

### 关联章节
[2.6, 8.2, 18.20]

