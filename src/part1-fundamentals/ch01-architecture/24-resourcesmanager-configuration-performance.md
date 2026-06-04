---
title: "ResourcesManager 与 Configuration 变更性能"
chapter: "1.24"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [resources, configuration, activity-recreation, performance, resourcesmanager]
related_chapters: ["1.8", "2.12", "8.2", "16.5"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-04"
gap_source: "研究素材+AOSP结构"
gap_score: 16
gap_score_detail: "素材丰富度 3 | 相关性 4 | 读者需求度 4 | 时效性 5"
---

# 1.24 ResourcesManager 与 Configuration 变更性能

<!-- outline-start -->
## 要点

### 🔹 锚点 1：ResourcesManager 的角色与资源加载管线
- ResourcesManager 是系统服务，管理所有应用的 Resources 实例
- 一个 Resources 对象绑定一个 Configuration，Config 变了需要重建 Resources
- ResourcesImpl 持有 AssetManager，AssetManager 通过 native 层加载 APK 资源
- 多进程共享同一个 ResourcesKey → 共享同一个 ResourcesImpl（缓存复用）

### 🔹 锚点 2：Configuration 变更的触发源与传播路径
- 系统级变更：locale、density、smallestWidth、orientation、uiMode、layoutDirection
- Android 17 新增：per-app language（AppLocaleConfig）、edge-to-edge 强制模式
- 传播路径：ActivityManagerService.updateConfiguration() → ResourceManager.applyConfigurationToResources() → Activity.onConfigurationChanged()
- 配置变更的"级联"效应：一个 Config 改变可能导致多个 Activity 的 recreate

### 🔹 锚点 3：Activity recreation 的性能代价
- recreate = destroy + create，完整走一遍生命周期
- 代价构成：onDestroy（释放旧引用）→ Intent 解析 → LayoutInflater 重建 View 树 → measure/layout/draw
- onSaveInstanceState/onRestoreInstanceState 的序列化/反序列化开销
- 典型数据：一个中等复杂度 Activity 的 recreate 耗时 50-200ms（取决于 View 树深度）

### 🔹 锚点 4：configChanges 清单与系统强制 recreate 的边界
- AndroidManifest 中 android:configChanges 声明可以阻止 recreate
- Android 13+ density 变更不再允许应用自行处理（系统强制 recreate）
- Android 15+ 屏幕尺寸变更（foldable）部分场景系统强制 recreate
- 各版本 configChanges 能力和限制的演进

### 🔹 锚点 5：避免 recreate 的策略与性能收益
- ViewModel + SavedStateHandle 保持状态不依赖 recreate
- onConfigurationChanged() 中手动处理 UI 更新
- 使用 ViewBinding/Compose 减少 LayoutInflater 开销
- 使用 Context.createConfigurationContext() 创建带 override Configuration 的 Context

### 🔹 锚点 6：Resources 缓存与内存占用
- ResourcesManager 维护 ResourcesKey → ResourcesImpl 的缓存
- 缓存命中条件：相同的 apkPaths + 配置兼容
- 大量不同 Configuration → 大量 ResourcesImpl 实例 → 内存膨胀
- 通过 dumpsys activity resources 查看 Resources 缓存状态

### 🔹 锚点 7：Android 17 新特性对 Configuration 性能的影响
- Per-app language：每个 Activity 可能有不同的 LocaleConfig
- 桌面模式下窗口 resize → Configuration 连续变更 → 防抖策略
- 16KB page size 对资源 APK mmap 的影响
- WebView 的 Configuration 独立性问题

## 扩展

### 🔸 扩展点 1：Compose 对 Configuration 变更的处理
- Compose 的 rememberSaveable 与 Configuration 变更
- Compose 中不依赖 Activity recreate 的状态管理

### 🔸 扩展点 2：多窗口/折叠屏场景下的连续 Configuration 变更
- 折叠/展开时的连续 Configuration 变更风暴
- 系统防抖机制与应用层应对策略

### 🔸 扩展点 3：ResourcesManager dumpsys 分析实战
- 通过 dumpsys activity resources 定位 Resources 泄漏
- Configuration diff 工具辅助分析

<!-- outline-end -->

> 本节内容待加工。
