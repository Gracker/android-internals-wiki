## [Task9 Deep Review] 1.6 Android 版本演进中的架构变化 — 2026-05-09
- **类型**：原理断裂
- **位置**：ARMv8 寄存器描述部分
- **问题**：ARMv8 的通用整数寄存器从 16 个增加到 31 个，但 SIM 前缀的 V 寄存器未明确说明是否增加，缺少 NEON 寄存器从 16 个增加到 32 个的完整变化描述
- **建议**：补充 "SIMD/NEON 寄存器也从 16 个 Q 寄存器增加到 32 个 V 寄存器" 的说明，完善 ARMv8 架构变化的完整描述

## [Task9 Deep Review] 1.6 Android 版本演进中的架构变化 — 2026-05-09
- **类型**：版本差异
- **位置**：Perfetto 表格提示部分
- **问题**：Perfetto 表格中把 ART Mainline 写成 Android 11+，应修正为 Android 12+ 或拆分 8-11/12+ 的版本口径
- **建议**：将表格中的 "Android 11+" 修正为 "Android 12+"，并添加注释说明 Android 10/11 已有 Mainline 架构但 ART 成为可独立更新的模块要到 Android 12

## [Task9 Deep Review] 1.6 Android 版本演进中的架构变化 — 2026-05-09
- **类型**：知识盲区
- **位置**：后台限制收紧部分
- **问题**：未覆盖 Android 16 新增的 JobScheduler 配额动态调整机制
- **建议**：补充 Android 16 中 JobScheduler 配额根据 App 的 standby bucket 和启动时的状态动态调整的详细说明

## [Task9 Deep Review] 1.6 Android 版本演进中的架构变化 — 2026-05-09
- **类型**：数据缺失
- **位置**：16K Page Size 性能提升部分
- **问题**：引用官方博客但未提供具体测试条件，缺少上下文信息
- **建议**：补充设备型号、测试场景、样本数量等测试条件，使数据更有说服力

## [Task9 Deep Review] 4.3 ART 虚拟机内存管理 — 2026-05-09
- **类型**：源码错误
- **位置**：BumpPointerSpace 部分描述
- **问题**：Android 15 的 `gPageSize` 动态获取应在注释中说明默认值仍为 4KB 的兼容逻辑，避免误判所有 15+ 都已适配 16KB
- **建议**：在描述中补充 "尽管 Android 15 支持动态获取页大小，但默认情况下仍使用 4KB，需要显式配置才能启用 16KB" 的说明

## [Task9 Deep Review] 4.3 ART 虚拟机内存管理 — 2026-05-09
- **类型**：源码错误
- **位置**：Large Object Space 部分描述
- **问题**：误将 Android 15 的 `kMinLargeObjectThreshold` 12KB 写成通用事实，未说明这是 arm64 设备的特定值
- **建议**：修正为 "在 arm64 设备上，`Heap::kMinLargeObjectThreshold` 的默认值是 12KB"，并补充其他架构的默认值说明

## [Task9 Deep Review] 4.3 ART 虚拟机内存管理 — 2026-05-09
- **类型**：源码错误
- **位置**：DeliQueue/ConcurrentMessageQueue 部分
- **问题**：当前公开 AOSP 源码中未出现 `DeliQueue` 类名，不应作为已确认的 API 引用
- **建议**：删除 `DeliQueue` 命名，只保留 `ConcurrentMessageQueue` 的官方命名，避免使用未公开的 API 名称

## [Task9 Deep Review] 4.3 ART 虚拟机内存管理 — 2026-05-09
- **类型**：原理断裂
- **位置**：GC 策略演进部分
- **问题**：Android 14/15 的 UFFD 驱动 CMC 与 Android 16 QPR2 的 Generational CMC 混淆，应明确区分两条时间线
- **建议**：重新梳理 GC 演进时间线：Android 8.0-13 看 CC，Android 14/15 看 UFFD 驱动的 CMC 路径，Android 16 QPR2 / Android 17 再谈 Generational CMC

## [Task9 Deep Review] 4.3 ART 虚拟机内存管理 — 2026-05-09
- **类型**：原理断裂
- **位置**：Young vs Full GC 部分
- **问题**：分代回收的触发条件阈值未具体说明，缺少量化标准
- **建议**：补充年轻对象晋升的具体触发条件，如 "当年轻对象占用超过堆大小的 50% 或对象数量超过阈值时触发晋升"

## [Task9 Deep Review] 4.3 ART 虚拟机内存管理 — 2026-05-09
- **类型**：版本差异
- **位置**：Baseline Profiles 部分
- **问题**：未区分 Android 7-8.1 与 Android 9+ 的 Baseline Profile 交付路径差异
- **建议**：补充说明 "Android 7-8.1 有 ProfileInstaller 驱动的 Baseline Profile，Android 9+ 进入 Baseline + Cloud Profile 的安装期 AOT 路径"

## [Task9 Deep Review] 4.3 ART 虚拟机内存管理 — 2026-05-09
- **类型**：版本差异
- **位置**：Android 16 QPR2 部分
- **问题**：Generational CMC 的官方发布说明与平台实现存在时间差，未标注正式发布日期
- **建议**：明确标注 "Generational CMC 正式发布于 Android 16 QPR2 (2025年12月)"，区分发布声明和实际可用性

## [Task9 Deep Review] 4.3 ART 虚拟机内存管理 — 2026-05-09
- **类型**：数据缺失
- **位置**：Cloud Profiles 部分
- **问题**：Cloud Profiles 的性能收益未提供具体 benchmark 数字
- **建议**：补充 Cloud Profiles 带来的具体性能提升数据，如 "通过 Play Store 分发的应用首次启动速度提升 15-25%" 等

## [Task9 Deep Review] 4.3 ART 虚拟机内存管理 — 2026-05-09
- **类型**：交叉引用错误
- **位置**：交叉引用部分
- **问题**：7.7 Jetpack Compose 的 recomposition 触发对象创建的关联性未详细说明
- **建议**：补充说明 "Jetpack Compose 的 recomposition 可能产生大量临时对象，触发频繁 Young GC，具体详见 7.7 章节" 的详细关联分析