---
title: "ResourcesManager 与 Configuration 变更性能"
chapter: "1.24"
status: ready-for-review
drafted_date: "2026-06-04"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-06-04"
last_verified_against: "AOSP android-17.0.0_r1 frameworks/base/core/java/android/app/ResourcesManager.java + Android 17 behavior-changes-all/target-37 + Cubox/FixedRotation 源码分析"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/app/ResourcesManager.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ResourcesImpl.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/DisplayContent.java"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-17"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-all"
  - type: blog
    path: "Cubox/Android无缝旋转-Fixed Rotation - 掘金-2022-08-29.md"
tags: [resources, configuration, activity-recreation, performance, resourcesmanager, configChanges, edge-to-edge]
related_chapters: ["1.8", "2.12", "8.2", "16.5"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-04"
gap_source: "研究素材+AOSP结构"
gap_score: 16
gap_score_detail: "素材丰富度 3 | 相关性 4 | 读者需求度 4 | 时效性 5"
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: pending
task2b_result: fixed
task2b_state: fixed
last_task2b_lite_at: 2026-06-30
task9_result: needs-rework
last_task9_at: 2026-06-30
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: 2026-06-30
last_task6_at: 2026-06-30T09:06:00+08:00
last_task2b_at: 2026-06-30T10:55:44+08:00
---

# 1.24 ResourcesManager 与 Configuration 变更性能

Configuration 变更是 Android 里频率最高的"隐式性能事件"之一。旋转屏幕、切换语言、折叠/展开折叠屏、进入桌面模式——这些用户操作都会触发系统级 Configuration 变更，导致 Resources 重建、Activity 销毁重建、View 树重绘。如果 App 没有正确处理，一次 Configuration 变更的开销可以相当于一次完整的冷启动。

下面分析 Configuration 变更从触发到生效的完整链路：ResourcesManager 如何管理 Resources 实例、Configuration 变更的传播路径、Activity recreation 的性能代价、以及各版本的 configChanges 边界变化。

---

## ResourcesManager 的角色与资源加载管线

ResourcesManager 是 framework 层的单例（`ActivityThread` 持有），负责为整个进程创建和管理所有 `Resources` 实例。一个进程内的 Resources 实例数量取决于当前有多少种不同的 Configuration。

### Resources 的三层结构

```
Resources（对外接口）
  └── ResourcesImpl（持有 AssetManager + Configuration）
        └── AssetManager（native 层，持有 apkPaths + resources.arsc 的 mmap）
```

- `Resources` 是给 App 用的接口层，提供 `getString()`、`getDrawable()` 等方法
- `ResourcesImpl` 持有真正的状态：当前 Configuration、DisplayMetrics、AssetManager
- `AssetManager` 在 native 层通过 mmap 访问 APK 中的 `resources.arsc`，负责资源查找和解析

一个 `ResourcesKey`（由 apkPaths + configuration + displayId 等参数组成）决定了一个 `ResourcesImpl` 实例。两个 ResourcesKey 相同的 Resources 共享同一个 ResourcesImpl——这是 ResourcesManager 的缓存复用机制。

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/app/ResourcesManager.java — getResources() → findOrCreateResourcesImplForKeyLocked()]

### ResourcesManager 的缓存结构

ResourcesManager 内部维护两个映射：

```
ResourcesKey → ResourcesImpl（全局缓存，跨 Activity 共享）
IBinder (Activity token) → Resources（每个 Activity 独立）
```

`getResources()` 的查找顺序：
1. 用 Activity token 查已有的 Resources 实例
2. 用 ResourcesKey 查可复用的 ResourcesImpl
3. 都没有就创建新的 ResourcesImpl + Resources

缓存命中条件严格：apkPaths、orientation、locale、density、screenWidthDp、screenHeightDp 等字段必须完全一致。任何一个字段不同，就需要新建 ResourcesImpl。

[已验证: AOSP android-17.0.0_r1, ResourcesManager.findOrCreateResourcesImplForKeyLocked()]

---

## Configuration 变更的触发源与传播路径

### 系统级触发源

| 触发源 | 涉及的 Configuration 字段 | 典型场景 |
|--------|---------------------------|----------|
| 屏幕旋转 | orientation, screenWidthDp, screenHeightDp | 手机旋转 |
| 折叠/展开 | screenWidthDp, screenHeightDp, smallestScreenWidthDp | 折叠屏设备 |
| 语言切换 | locale | 设置中切换语言 |
| 深色模式 | uiMode (night mode) | 设置或自动切换 |
| 密度变更 | density | 接入外接显示器 |
| 桌面模式 | screenWidthDp, screenHeightDp, orientation | Chrome OS / Samsung DeX |
| Per-app language | locale | Android 13+ AppCompatDelegate.setApplicationLocales() |
| 窗口 resize | screenWidthDp, screenHeightDp, windowConfiguration | 多窗口拖拽 |

### 传播路径

Configuration 变更的系统侧传播路径：

```
触发源（Settings / WindowManager / PowerManager 等）
  → ActivityManagerService.updateConfiguration()
    → ActivityTaskManagerService.updateConfigurationLocked()
      → ResourcesManager.applyConfigurationToResources()
        → 重建或复用 ResourcesImpl
      → WindowProcessController / ActivityRecord.ensureActivityConfiguration()
        → 判断是否需要 relaunch（取决于 configChanges 声明）
        → 需要 relaunch → ClientTransaction → ActivityThread.handleRelaunchActivity()
        → 不需要 relaunch → ActivityThread.handleActivityConfigurationChanged()
```

服务端（system_server）做决策，客户端（App 进程）执行。`ActivityManagerService.updateConfiguration()` 委托 `ActivityTaskManagerService.updateConfigurationLocked()` 传播新 Configuration，通过 `WindowProcessController` 和 `ActivityRecord.ensureActivityConfiguration()` 逐个判断每个 Activity 是否需要 relaunch。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java updateConfiguration() → ActivityTaskManagerService.updateConfigurationLocked() → WindowProcessController / ActivityRecord.ensureActivityConfiguration()]

### FixedRotation：避免旋转时重建的特殊路径

Android 12 引入了 FixedRotation 机制。当启动一个方向不同的 Activity 时，系统不再触发完整的 Configuration 变更，而是通过 `DisplayAdjustments` 模拟旋转后的屏幕参数，让 App 在旧方向上以新方向的信息完成首次绘制，绘制完成后再执行真正的旋转动画。

关键调用链（Android 17，android-17.0.0_r1）：

```
DisplayContent.handleTopActivityLaunchingInDifferentOrientation()
  → setFixedRotationLaunchingApp()
    → startFixedRotationTransform()
      → WindowToken.applyFixedRotationTransform()
        → ActivityRecord.ensureActivityConfiguration()
```

FixedRotation 让 Activity 避免了一次完整的 recreate，但它只在 Activity 启动时生效。如果 App 已经在前台，用户旋转设备，FixedRotation 不适用，仍然走正常的 Configuration 变更流程。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/wm/DisplayContent.java — handleTopActivityLaunchingInDifferentOrientation() → setFixedRotationLaunchingApp() → startFixedRotationTransform(); 历史博客参考（Android 12 时期的分析，方法名在 android-17 中已有变化）: Cubox/Android无缝旋转-Fixed Rotation - 掘金-2022-08-29.md]

---

## Activity recreation 的性能代价

### recreate 的工作量

Activity recreate 的本质是 destroy + create，完整走一遍生命周期：

```
onSaveInstanceState()          // 序列化状态
onPause() → onStop() → onDestroy()  // 销毁旧实例
  ↓
Intent 解析 + 新 Activity 分配
  ↓
onCreate() → onStart() → onRestoreInstanceState() → onResume()
  ↓
LayoutInflater 重建 View 树 → measure → layout → draw
```

一次 recreate 的耗时构成（以下数值为工程估算框架，缺少设备型号、ROM 版本、布局规模、Perfetto trace 等可复现条件，不应作为跨设备可比的性能结论）：

| 阶段 | 估算量级 | 影响因素 |
|------|----------|----------|
| onSaveInstanceState 序列化 | 数 ms | 状态数据量（Parcel 序列化开销） |
| onDestroy 清理 | 数 ms | 释放的引用数量 |
| Activity 对象创建 + onCreate | 数 ms-数十 ms | 初始化逻辑复杂度 |
| LayoutInflater 重建 View 树 | 数十 ms-上百 ms | 布局层级深度和 View 数量 |
| measure + layout | 数十 ms | 布局复杂度、ConstraintLayout vs LinearLayout |
| draw（首帧） | 数 ms-数十 ms | View 数量、是否启用硬件加速 |

对于一个有 200+ 个 View 节点的 Activity，recreate 耗时通常在数十到上百毫秒量级。在折叠屏设备上展开/折叠时，如果触发了 recreate，耗时可能进一步增加（screenWidthDp、screenHeightDp、smallestScreenWidthDp 同时变化，Resources 和 View 树均需重建）。

> ⚠️ **数据待验证**：上述量级基于工程经验估算，非可复现实验。建议用 Perfetto 在目标设备上采集（设备型号、ROM 版本、APK 规模、采样次数记录完整）后替换为实测数据。

### 序列化/反序列化的隐含开销

`onSaveInstanceState()` 的开销经常被低估。几个常见的高成本操作：

- `Parcel.writeParcelable()` 写入大型对象（如包含 Bitmap 的自定义 Parcelable）
- `Parcel.writeList()` 写入长列表
- `Bundle.putParcelableArrayList()` 序列化列表中的每个元素

在 Perfetto 中，recreate 期间如果主线程出现 `Parcel.writeParcelable` 的长耗时 slice，说明状态序列化是瓶颈。

### View 树重建的瓶颈

LayoutInflater 重建是 recreate 中最重的操作。`LayoutInflater.inflate()` 会：
1. 解析 XML 中的每个 View 标签
2. 通过反射调用 View 的构造函数
3. 解析 `layout_*` 属性

如果布局层级深（超过 10 层）或包含大量 `include`/`merge`/`ViewStub`，inflate 耗时会显著增加。详见 22.1 节的布局优化策略。

---

## configChanges 清单与系统强制 recreate 的边界

### AndroidManifest 中的 configChanges 声明

在 `<activity>` 标签中声明 `android:configChanges` 可以阻止系统在对应 Configuration 变更时 recreate Activity，改为回调 `onConfigurationChanged()`：

```xml
<activity
    android:name=".MainActivity"
    android:configChanges="orientation|screenSize|screenLayout|smallestScreenSize|uiMode|locale|layoutDirection|density" />
```

常见 configChanges 值及其适用场景：

| 值 | 触发场景 | 处理难度 |
|----|----------|----------|
| `orientation` | 屏幕旋转 | 中——需要重新布局 |
| `screenSize` | 屏幕尺寸变化（旋转、折叠） | 中——需要重新布局 |
| `smallestScreenSize` | 物理屏幕尺寸变化 | 高——可能需要切换布局 |
| `screenLayout` | 屏幕布局变化 | 中 |
| `uiMode` | 日间/夜间模式切换 | 低——主题切换 |
| `locale` | 语言切换 | 高——需要刷新所有文本 |
| `layoutDirection` | RTL/LTR 切换 | 中 |
| `density` | 显示密度变化 | 高——需要重新加载资源 |

### 各版本的 configChanges 演进

**Android 17 (API 37)**：在 smallest width ≥ 600dp 的设备上（平板、折叠屏展开态），系统忽略 `android:screenOrientation`、`android:resizeableActivity="false"` 和宽高比限制。targetSdk ≥ 37 的 App 在大屏设备上因此必须处理连续的 Configuration 变更——不能再通过锁屏方向来规避。

> **关于 density 和 foldable 强制 recreate 的说明**：坊间流传 "Android 13 density 变更不再允许应用自行处理""Android 14 foldable 场景强制 recreate" 等说法，但 Android 17 `ActivityRecord#shouldRelaunchLocked()` 在 PiP 场景下会把 `CONFIG_DENSITY` 加入 skip mask（不触发 relaunch），且官方 manifest 文档仍列出 `density` 为 `configChanges` 的有效值。这些说法缺少公开源码和官方行为变更文档的支撑，不作为确定性结论。

[已验证: 官方文档, developer.android.com/about/versions/17/behavior-changes-17 — targetSdk 37 大屏适配]

### configChanges 的正确用法

声明了 `configChanges` 不等于"什么都不用做"。`onConfigurationChanged()` 回调中必须手动处理 UI 更新：

```java
@Override
public void onConfigurationChanged(Configuration newConfig) {
    super.onConfigurationChanged(newConfig);
    // 1. 更新 Resources（系统已自动更新）
    // 2. 重新布局 View 树
    // 3. 更新受 Configuration 影响的自定义状态
}
```

常见错误：声明了 `orientation|screenSize` 的 configChanges，但 `onConfigurationChanged()` 中没有重新调整布局，导致 UI 在新方向上显示不正确。

---

## 避免 recreate 的策略与性能收益

### ViewModel + SavedStateHandle

最根本的策略是让状态不依赖 Activity 实例。`ViewModel` 在 Configuration 变更时不会被销毁，`SavedStateHandle` 处理进程被杀后的状态恢复。

```
Activity recreate 前的状态保存路径：
  onSaveInstanceState → SavedStateHandle (自动同步)
  ViewModel (内存中保留，不参与序列化)

Activity recreate 后的恢复路径：
  ViewModel 直接可用（同一个实例）
  SavedStateHandle 自动恢复（从 Bundle 反序列化）
```

性能收益：省掉了自定义 `onSaveInstanceState()` 的序列化开销，同时 ViewModel 中的缓存数据（如网络请求结果）不需要重新获取。

### Context.createConfigurationContext()

创建一个带 override Configuration 的 Context，避免影响进程级的 Resources：

```java
Configuration override = new Configuration(baseContext.getResources().getConfiguration());
override.setLocale(newLocale);
Context localizedContext = baseContext.createConfigurationContext(override);
// 用 localizedContext 加载资源，不影响其他 Activity
```

这个方法适用于 Per-app language 场景：每个 Activity 可以有独立的 Locale，不需要变更进程级 Configuration。

### Compose 对 Configuration 变更的处理

Compose 默认不依赖 Activity recreate 来更新 UI——`LocalConfiguration` 作为 CompositionLocal 提供，Configuration 变更时触发 recomposition，将新配置反映到 UI 树中。但 **recomposition 不等于 Activity recreate**：`remember` 仅在 recomposition 间保留状态，Activity recreate（以及更严重的 process death）会清空所有 `remember` 值——需要使用 `rememberSaveable`（依赖 `Bundle` 序列化）或 `ViewModel` + `SavedStateHandle` 才能在跨 recreate 或跨进程死亡时恢复状态。

Compose 的状态在三个不同边界有不同行为：

- **Recomposition（最常见）**：`remember` 保留，`LocalConfiguration` 变更触发 recomposition。这是 Compose 的默认工作方式，不需要额外声明。
- **Activity recreate（Configuration 变更触发）**：`remember` 丢失——Compose 函数重新执行，所有未用 `rememberSaveable` 保存的值重置。需要用 `rememberSaveable`（`Bundle` 序列化）或 `ViewModel` + `SavedStateHandle` 跨 recreate 保留状态。
- **Process death**：只有 `rememberSaveable` 和 `ViewModel` 的 `SavedStateHandle` 能通过系统保存的 `Bundle` 恢复；`remember` 和 `derivedStateOf` 的值全部丢失。

`derivedStateOf`、`produceState` 在不同边界的保留能力取决于上游数据源：基于 `remember` 的数据在 Activity recreate 后丢失，基于 `ViewModel` 或持久化存储的数据在对应边界内保留。

详见 7.7 节和 22.3 节。

---

## Resources 缓存与内存占用

### ResourcesImpl 缓存膨胀

ResourcesManager 维护 `ResourcesKey → ResourcesImpl` 的全局缓存。Android 17 中 `mResourceImpls` 使用 `WeakReference<ResourcesImpl>`，通过 `ReferenceQueue` 和 `cleanupResourceImplsLocked()` 清理已无外部强引用的实例。ResourcesImpl 对象本身不会因为留在缓存容器中而无法 GC——根源在于外部强引用阻止 GC（如静态变量持有 Resources、单例持有 Activity Context 等），导致弱引用无法被回收。

在以下高频 Configuration 变更场景中，多个存活 ResourcesImpl 会被同时持有，增加弱引用缓存键数量和原生资源开销：

- 多窗口模式下频繁拖拽 resize：每次 resize 产生新的 screenWidthDp/screenHeightDp 组合
- 折叠屏反复折叠/展开：产生多组 Configuration
- Per-app language 场景下频繁切换语言：每种 locale + 其他 Configuration 参数的组合都是独立的 ResourcesKey

每个 ResourcesImpl 持有一个 AssetManager 实例，AssetManager 在 native 层 mmap 了 APK 的 `resources.arsc`。多个 ResourcesImpl 不会重复 mmap 同一个 APK（内核的页面缓存共享），但每个 AssetManager 有自己的 native 内存分配（查找表、字符串缓存等）。

### dumpsys activity resources 分析

```bash
adb shell dumpsys activity resources <package_name>
```

输出中关注：

- `ResourcesKey` 的数量——如果远大于当前 Activity 数量，说明可能存在外部强引用阻止 GC 导致弱引用无法被清理
- `ResourcesImpl` 的数量——应该等于 ResourcesKey 的去重数量
- 最近创建的 ResourcesImpl 的时间戳——如果频繁创建，说明 Configuration 在高频变化

### 内存估算

一个 ResourcesImpl 实例的内存占用量级（工程估算，非实测）：

- Java 层：数十到上百 KB（取决于 Configuration 复杂度和 Resources 缓存状态）
- Native 层：AssetManager 查找表和字符串缓存，量级受 APK resources.arsc 大小影响

如果进程中有 20+ 个 ResourcesImpl 实例同时被强引用持有（在多窗口 + 折叠屏场景下可能出现），额外的内存开销可能在数 MB 量级。

> ⚠️ **数据待验证**：上述量级基于工程经验估算，缺少设备型号、APK 规模和 native heap dump 等可复现条件。建议用 `dumpsys meminfo` + native heap profiler 在目标设备上实测后替换。

---

## Android 17 对 Configuration 性能的影响

### Per-app language

Android 13 引入了 Per-app language API（`LocaleManager.setApplicationLocales()`），Android 17 进一步完善。每个 Activity 可以有独立的 Locale，通过 `AppCompatDelegate.setApplicationLocales()` 设置。

对 ResourcesManager 的影响：不同的 locale 产生不同的 ResourcesKey，如果 App 内有多个 Activity 使用不同的语言设置，ResourcesImpl 实例数量会翻倍。不过在大多数 App 中，所有 Activity 共享同一个 locale 设置，影响有限。

### 大屏强制多方向（targetSdk 37）

Android 17 要求 targetSdk ≥ 37 的 App 在 smallest width ≥ 600dp 的设备上支持所有方向和 resize。系统会忽略 `android:screenOrientation` 和 `android:resizeableActivity="false"`。

对性能的影响：
- 折叠屏展开/折叠时，Configuration 可能连续变更多次（先 orientation 变、再 screenWidthDp/screenHeightDp 变），每次变更都可能触发 recreate
- 多窗口模式下拖拽 resize 不再触发 recreate（Android 12+ 的桌面模式通过 `onConfigurationChanged()` 处理），但初次进入多窗口时会触发

建议在 Perfetto 中对比折叠/展开前后的帧时间分布。如果 `Choreographer#doFrame` 下的 `performTraversal` 耗时在 Configuration 变更后明显增加，说明布局需要针对大屏优化（减少嵌套层级、使用 `ConstraintLayout` 替代多层 `LinearLayout`）。

[已验证: 官方文档, developer.android.com/about/versions/17/behavior-changes-17]

### IME 状态不再恢复

Android 17 开始，Configuration 变更后系统不再自动恢复之前的 IME（软键盘）显示状态。如果 App 依赖系统恢复键盘弹出状态，需要在 `onConfigurationChanged()` 或 `onCreate()` 中主动调用 `windowSoftInputMode` 设置或 `showSoftInput()`。

### 16KB Page Size 对资源 mmap 的影响

Android 15 引入 16KB page size 支持（详见 4.7 节）。对资源加载的影响：
- `resources.arsc` 通过 mmap 加载，16KB page size 下 mmap 的最小粒度增大
- 对于小 APK（resources.arsc < 1MB），内存浪费增加约 8-16KB（从一个 4KB 页变为一个 16KB 页的浪费上限）
- 对于大 APK，影响可以忽略——mmap 的页面对齐开销在整体内存中占比很小

---

## 扩展

### 折叠屏/多窗口场景下的连续 Configuration 变更

折叠屏展开/折叠时，系统可能在短时间内连续发送多个 Configuration 变更。Android 的处理策略：

- ATMS 在 `updateConfigurationLocked()` 中会合并同一批次内的 Configuration 变更，一次 propagate
- 但折叠/展开涉及 orientation + screenWidthDp + screenHeightDp + smallestScreenWidthDp 四个字段同时变化，系统会将它们打包成一次 Configuration 变更，而非多次
- FixedRotation 机制（见上文）只在 Activity 启动时生效，已经在前台的 Activity 走正常流程

应对策略：
1. 声明 `configChanges="orientation|screenSize|smallestScreenSize|screenLayout"`，在 `onConfigurationChanged()` 中处理
2. 使用 Jetpack WindowManager 的 `WindowInfoTracker` 监听窗口状态变化
3. 在布局中避免硬编码尺寸，使用 `dimens.xml` 的 sw600dp/sw720dp 限定符

### dumpsys 实战：定位 Resources 泄漏

```bash
# 查看 App 的 Resources 缓存状态
adb shell dumpsys activity resources <package_name>

# 对比两个时间点的 ResourcesImpl 数量
adb shell dumpsys activity resources <package_name> | grep "ResourcesImpl" | wc -l
# ... 操作 App（旋转、切换语言、进入多窗口）...
adb shell dumpsys activity resources <package_name> | grep "ResourcesImpl" | wc -l
```

如果 ResourcesImpl 数量持续增长且不回落，说明有 Configuration 泄漏——某些 ResourcesImpl 被持有但不再使用。常见原因：
- 静态变量持有对旧 Resources 的引用
- Singleton 持有对 Activity Context 的引用（应该用 ApplicationContext）
- Handler/Runnable 持有对旧 Activity 的隐式引用

定位方法：通过 Android Studio Profiler 的 Heap Dump，搜索 `ResourcesImpl` 实例，查看 GC Root 引用链。

### Compose 与 Configuration 变更

Compose 的状态管理天然适合 Configuration 变更场景：

- `rememberSaveable`：跨 Configuration 变更保持状态，内部使用 `Bundle` 序列化
- `LocalConfiguration`：Configuration 变更时自动触发 recomposition
- `LocalContext`：随 Configuration 变更更新，不需要手动切换 Context

Compose 中不需要声明 `configChanges`——Compose 的状态在 Configuration 变更时不会丢失。但如果 Compose 内容嵌套在 View 体系中（`ComposeView`），外层 Activity 的 recreate 行为仍然取决于 Manifest 声明。
