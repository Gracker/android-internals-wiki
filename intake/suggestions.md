## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-07-04
- **类型**：源码准确性
- **位置**：IPCThreadState::transact() 行号引用（第2节）
- **问题**：android-17.0.0_r1 中函数体在 `IPCThreadState.cpp:921-994`，但实际 `transact` 方法签名和分支逻辑与引用行号不符。正确位置应在 `IPCThreadState.cpp:948-996`（TF_ONE_WAY 分支判断）。
- **建议**：更新源码引用行号，确保与 actual AOSP android-17.0.0_r1 代码一致

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-07-04
- **类型**：源码准确性
- **位置**：binder_node_release() 函数引用（第15节）
- **问题**：android17-6.18-2026-06_r1 中 `binder_node_release()` 函数位于 `drivers/android/binder.c:6460-6534`，但实际函数体是 `binder_node_release()` 而不是引用的 `binder_thread_release()`。
- **建议**：修正函数名称和行号引用，确保准确性

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-07-04
- **类型**：版本差异
- **位置**：冻结回执机制（第3节）
- **问题**：未明确说明 Android 17 与 Android 16 在冻结回执机制上的差异，特别是 `enableFrozenObjectErrorCode()` aconfig flag 的默认配置未说明。
- **建议**：补充 Android 17 与 Android 16 在冻结回执机制上的具体差异，特别是 aconfig flag 的默认值变化

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-07-04
- **类型**：数据支撑
- **位置**：批处理性能数据（第5节）
- **问题**：文中标注 "[待补充]" 的 oneway vs 同步调用的端到端延迟对比、批处理模式下 syscall 减少量、frozen sync 立即返回错误 vs 普通同步等待卡住的 ANR 次数对比数据缺失。
- **建议**：补充具体的性能测试数据，包括延迟对比、syscall 减少量、ANR 次数对比等量化数据
## [Task2A Gap Mining Round 11] 2026-07-04 17:10 — Coverage Saturated

### Checked Directions (this round)
- 4 new DeepResearch files (2026-07-04): modular startup dependency graph, heapprofd production deployment permissions, LMKD procs_prio batch + thrashing, binder death notification batch dispatch
- All 4 are supplements to existing chapters (§21.x, §14.x, §16.8, §1.25/§14.6), not new chapter candidates
- TASK2B_BACKLOG=0, all 14 draft files have substantial content (81-1602 effective lines)

### Cumulative Coverage (rounds 1-11)
All of the following have been checked and either covered or scored <14:
- AOSP frameworks/base services: WindowManager, ActivityManager, TelephonyManager, ConnectivityManager, PowerManager, NotificationManager, PackageManager, InputManager, DisplayManager, SensorManager, LocationManager, AudioManager, WindowManager, KeyboardShortcutManager
- AOSP packages/modules: Bluetooth, WiFi, Media, DNS resolver, IPsec, NetworkStack, OnDevicePersonalization, RemoteAccess, Scheduler
- AOSP system/: vold, netd, lmkd, installd, gatekeeperd, keystore2, traced, heapprofd
- Android 17 features: ML Scheduler, Staged Install, Binder priority inheritance, AppFlow/LMKD v2, ARM MTE, FrameTimeline, eBPF observability, Compose Pausable, ADPF, simpleperf microarch
- Clippings 108 articles: all mapped to existing chapters
- Daily info topics: Desktop Experience, Compose Pager, NSD/Wi-Fi Direct, Repository patterns, Clean Architecture
- Niche candidates: AppFunctions, Credential Manager, Health Connect, Safety Center, Predictive Back, Photo Picker, AVF, Compose Compiler/stability, FGS Type, RRO, Backup, SystemProperty, Lazy Layout, sched_ext, LE Audio, Vulkan, Desktop Mode
- Chapter extension points: all checked, no expansion candidates ≥14

### Conclusion
Coverage saturated. 11th consecutive no-candidate round. Book structure is comprehensive.
