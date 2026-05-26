# 源码调研：Android 17 NPU / AICore / LiteRT 能力边界分析

📅 2026-05-26 | AIW · 每日源码调研

## 盲区来源

**关联章节**：§5.11 端侧 AI 推理性能
**推荐来源**：daily-topics.json id=3
**原始描述**：厘清Android 17 NPU公开能力边界，拆分公开API、厂商预览、私有分发路径，为端侧AI推理开发提供准确技术支撑
**研究价值**：验证 AICore/LiteRT/NNAPI 在 Android 17 的能力边界与调用路径

---

## 核心发现

Android 17 (API 36) 对 NPU 访问引入了强制声明机制， apps targeting Android 17 必须显式声明 `FEATURE_NEURAL_PROCESSING_UNIT` 才能直接访问 NPU。NNAPI 在 Android 15 已进入废弃流程，官方推荐迁移路径为 **LiteRT in Google Play Services + GPU Delegate**。AICore 是 Google 的 GenAI 模型运行时，不属于 AOSP，通过 Google Play services 分发，依赖底层硬件加速器（Google/联发科/高通 AI 加速器）。

---

## 源码分析

### 1. NNAPI 废弃与迁移路径

**关键源码**：
- `hardware/interfaces/neuralnetworks/1.3/` — NNAPI HIDL 接口定义
- `frameworks/base/core/java/android/content/pm/PackageManager.java` — 硬件特性声明

**关键结论**：
- NNAPI 从 Android 15 (API 35) 开始标记为废弃
- 官方迁移文档（developer.android.com/ndk/guides/neuralnetworks/migration-guide）明确指出：
  > "NNAPI was deprecated in Android 15. To migrate from NNAPI, see the instructions for TensorFlow Lite in Google Play Services and optionally TFLite GPU delegate for hardware acceleration."

**版本差异**：
- Android 14 (API 34)：NNAPI 可正常使用，ANeuralNetworks* API 稳定
- Android 15 (API 35)：NNAPI 标记废弃，但扔可用
- Android 17 (API 36)：强制 NPU feature 声明，直接访问 NPU 必须声明

### 2. Android 17 NPU Feature 强制声明

**关键源码**：
- `frameworks/base/core/java/android/content/pm/PackageManager.java` — `FEATURE_NEURAL_PROCESSING_UNIT` 定义
- `device/google/coral/manifest.xml` — 设备级 feature 声明示例

**关键发现**：Android 17 Release Notes 明确：
> "Apps targeting Android 17 must declare the FEATURE_NEURAL_PROCESSING_UNIT hardware feature to directly access the NPU"

**调用链**：
```
PackageManager.hasSystemFeature(FEATURE_NEURAL_PROCESSING_UNIT)
  → PackageManagerService.hasSystemFeature()
  → device-specific feature decl (manifest.xml or ro.hardware)
```

**这意味着**：App 需要在 AndroidManifest.xml 中声明：
```xml
<uses-feature android:name="android.hardware.neural_processing_unit" android:required="false" />
```
然后通过 `PackageManager.hasSystemFeature()` 检测可用性。

### 3. AICore 定位与分发机制

**关键源码**（非 AOSP，为 Google Play services）：
- `com.google.ai.edge.aicore` — AICore package
- 源码位于 Google 私有仓库，非 AOSP 主干

**核心架构**：
- AICore 是 Android 系统级 AI 运行时，为 Gemini Nano、Gemma 等 GenAI 模型提供 on-device inference 能力
- 通过 Google Play services 更新，与系统绑定（不可卸载）
- 依赖底层 AI 加速器：Google AI accelerator / MediaTek AI processor / Qualcomm AI Engine

**版本信息**：
- 最新版本：0.0.1-exp01（开发者预览版）
- minSdkVersion：31（Android 12）
- 2026年4月2日：AICore Developer Preview 支持 Gemma 4

**源码锚点**（来自 cs.android.com 搜索）：
- `packages/modules/Neuralnetworks/` — NPU 驱动接口
- `hardware/interfaces/neuralnetworks/1.3/types.hal` — HAL 类型定义
- `system/sepolicy/apex/com.android.neuralnetworks-file_contexts` — SELinux 策略

### 4. LiteRT 架构与 Delegation 机制

**关键源码**：
- `external/XNNPACK/` — XNNPACK 量化执行引擎（AOSP）
- Play Services 中的 LiteRT 运行时（私有，非 AOSP）

**核心架构**：
```
App (LiteRT Model) 
  → LiteRT Runtime (Google Play Services)
    → GPU Delegate / NPU Delegate (Play Services extension)
      → Hardware (GPU/NPU)
```

**分发路径**：
- LiteRT 核心：内置于 Google Play services
- Delegates（GPU/NPU）：通过 Google Play services 独立分发
- 官方文档（developer.android.com/ai/custom）明确：
  > "Use LiteRT Delegates distributed using Google Play services to run accelerated ML on specialized hardware such as GPUs or NPUs."

**AOSP 相关组件**：
- `frameworks/base/core/java/android/content/pm/PackageManager.java` — feature 检测
- `packages/modules/Neuralnetworks/` — NPU HAL 服务

### 5. NPU 硬件抽象层

**关键源码**：
- `hardware/interfaces/neuralnetworks/1.3/IDevice.h` — NPU 设备接口
- `hardware/interfaces/neuralnetworks/1.3/types.hal` — 操作数类型定义

**能力边界**：
- NNAPI 提供 4 类操作：Elementwise, Activation, Convolution, Pooling
- Operation flushed to driver via HIDL
- AICore 内部调用 NNAPI 或私有接口（厂商特定）

---

## 版本差异总结

| 特性 | Android 14 (API 34) | Android 15 (API 35) | Android 17 (API 36) |
|------|---------------------|---------------------|---------------------|
| NNAPI 状态 | 稳定 | 废弃（仍可用） | 废弃+强制声明 |
| NPU Feature 声明 | 可选 | 可选 | 必须声明 |
| LiteRT 分发 | Play Services | Play Services | Play Services |
| AICore | 预览版 | 稳定版 | Developer Preview (Gemma 4) |
| GPU Delegate | 支持 | 支持 | 支持 |

---

## 性能影响

1. **NNAPI → LiteRT 迁移**：TensorFlow Lite 在 Play Services 中运行，delegate 更新与 OS 解耦，更新更频繁
2. **NPU Feature 强制声明**：影响 App 对 NPU 资源的直接访问，间接推动通过 LiteRT Delegate 间接访问
3. **AICore 硬件依赖**：在非优化硬件上退化为 CPU 实现，性能不代表最终产品

---

## 信息源

| 信息 | 来源 | 类型 |
|------|------|------|
| NNAPI 废弃声明 | developer.android.com/ndk/guides/neuralnetworks | 官方文档（一手） |
| Android 17 NPU 声明要求 | developer.android.com/about/versions/17/release-notes | 官方文档（一手） |
| AICore 包结构 | developer.android.com/ai/reference/com/google/ai/edge/aicore | 官方文档（一手） |
| LiteRT Delegate 说明 | developer.android.com/ai/custom | 官方文档（一手） |
| NPU HAL 接口 | cs.android.com hardware/interfaces/neuralnetworks/1.3 | AOSP 源码（一手） |
| NNAPI 迁移指南 | developer.android.com/ndk/guides/neuralnetworks/migration-guide | 官方文档（一手） |
| AICore Developer Preview 公告 | android-developers.googleblog.com 2026/04/02 | 官方博客（一手） |

---

## 未验证/待深入

1. **AICore 私有接口**：AICore 调用 NPU 的私有接口路径未找到 AOSP 源码
2. **厂商 NPU 实现差异**：联发科/高通 NPU 驱动实现细节未验证
3. **LiteRT NPU Delegate 具体 API**：需验证 com.google.android.gms 下的具体 delegate 接口
4. **FEATURE_NEURAL_PROCESSING_UNIT 具体检测逻辑**：需找到 PackageManager 中对应常量定义
5. **Generational CMC 与 NPU 交互**：§5.11 与 §4.3 的交叉影响未验证

---

## 反哺 AIW 章节建议

在 §5.11 端侧 AI 推理性能 中补充：
- NNAPI 废弃时间线（Android 15 废弃，Android 17 强制声明）
- LiteRT + Delegate 替代方案
- AICore 定位（系统级 GenAI 模型，非通用推理）
- NPU feature 检测与声明要求
