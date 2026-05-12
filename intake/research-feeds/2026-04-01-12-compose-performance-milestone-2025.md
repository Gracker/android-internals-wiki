---
source: web-search-synthesis
query: "Jetpack Compose performance optimization 2025 2026 recomposition lazy column pausable composition strong skipping"
date: 2026-04-01
target_sections:
  - "7.7"
  - "2.1"
  - "2.4"
relevance: 9
technical_depth: 8
timeliness: 10
verifiability: 8
total_score: 35
status: candidate
---

# Jetpack Compose 性能里程碑（2025 年底达成 View 系统性能对等）

## 核心发现

### 1. Compose 1.10 — Pausable Composition 成为默认行为（2025.12）

Compose 1.10（2025 年 12 月，BOM 2025.12.00）引入了一个根本性的运行时改进：**Pausable Composition**（可暂停组合）成为默认行为。

**机制**：当一帧内的组合（composition）工作量超过帧时间预算时，Compose 运行时可以暂停当前组合工作，将控制权交还主线程处理其他事件（如 input、animation），然后在下一帧继续完成剩余的组合。这实质上是对组合工作做了**时间切片（time-slicing）**。

**效果**：在 Google 内部滚动基准测试中，长列表滚动的卡顿率降到了 **0.2%**，官方宣布 Compose 达到了与 View 系统的性能对等（performance parity）。

**适用场景**：动态表单、分析面板、大量 feature flag 导致的大范围 UI 树更新等场景。

**在 Perfetto 中的表现**：[待验证] Pausable composition 可能在主线程 track 中表现为被切分的 composition slice，中间穿插了其他系统回调。

### 2. Strong Skipping Mode — Kotlin 2.2 默认启用

Kotlin 2.2 编译器（配合 Compose compiler）**默认启用 Strong Skipping Mode**：

- 所有 `@Composable` 函数都会被标记为 skippable，即使参数类型不是 Stable
- **所有 lambda 都会被自动 memoize**，不再需要手动 `remember { }` 包裹
- 权衡：内存占用可能增加（更多的 remember 缓存），但大幅减少不必要的重组（recomposition）

**对开发者的影响**：以前需要大量 `@Stable` / `@Immutable` 注解和 `remember` 优化的场景，现在编译器自动处理了。但仍然需要理解底层机制来判断是否有异常的重组行为。

### 3. Lazy Layout 预取优化

- **智能预取**：LazyColumn / LazyRow 根据滚动速度预测性预取 item，将组合工作分散到空闲帧
- **LazyLayoutCacheWindow**：开发者可以精确控制预取的 item 数量
- 配合 Pausable Composition，预取工作也可以被暂停

### 4. 后台文本预取（Compose 1.9+）

从 Compose 1.9 开始，文本布局缓存可以在后台线程预热（pre-warm），减少主线程文本渲染的耗时。

### 5. 其他最佳实践（2025 年确认仍然有效）

- 提供 stable key 给 LazyColumn items
- `derivedStateOf` 限制重组范围
- 延迟读取状态（defer state reads）
- Lambda-based modifier（`Modifier.offset {}`、`Modifier.graphicsLayer {}`）绕过 composition 阶段
- Baseline Profiles 对 Compose 性能尤其重要
- 始终使用 Release + R8 构建

## 对 Wiki 的价值

### 映射到 §7.7 Jetpack Compose 性能优化

这些发现提供了 2025 年底 Compose 性能演进的完整图景：
1. **性能对等里程碑**：标志着 Compose 从"性能劣于 View"到"性能持平"的转变
2. **Pausable Composition**：这是全新的运行时机制，之前版本不存在，需要在 Wiki 中详细讲解
3. **Strong Skipping Mode**：改变了 Compose 性能优化的最佳实践（很多手动优化不再必要）
4. **Lazy Layout 预取**：补充 LazyColumn 性能优化部分

### 版本演进

| Compose 版本 | 性能改进 | 时间 |
|---|---|---|
| 1.7 | Strong Skipping Mode 实验性引入 | 2024 Q3 |
| 1.9 | 后台文本预取、lazy prefetch 改进 | 2025 Q3 |
| 1.10 | Pausable Composition 默认、性能对等 | 2025 Q4 |
| Kotlin 2.2 | Strong Skipping 默认启用 | 2025 Q4 |

## 验证状态

- [已验证: Google 官方博客宣布 Compose BOM 2025.12.00 达到性能对等]
- [已验证: Pausable Composition 在 Compose 1.10 release notes 中确认]
- [已验证: Strong Skipping Mode 在 Kotlin 2.2 中默认启用]
- [待验证: Pausable Composition 在 Perfetto 中的具体表现]
- [待验证: 0.2% 卡顿率的具体测试条件（设备、列表长度等）]
