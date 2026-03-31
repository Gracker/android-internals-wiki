# Android 15/16 16KB Page Size 迁移对 App 内存的影响

> 研究素材 · 2026-03-31 19:00 · task5-research-discovery · 目标章节: 4.5 App 内存优化

## 来源

- Google Android Developers 官方文档: Build apps for 16 KB page sizes (developer.android.com)
- Google Blog: Android 15 16KB page size announcement
- Samsung Remote Test Lab: 16KB 测试文档

## 核心发现

### 1. 16KB Page Size 的性能收益（已验证数据）

| 指标 | 平均提升 | 最佳案例 |
|------|---------|---------|
| 冷启动时间 | 3.16% | 最高 30% |
| 功耗（启动期间） | 4.56% | - |
| 相机热启动 | 4.48% | - |
| 相机冷启动 | 6.60% | - |
| 系统启动时间 | 8% (~950ms) | - |

### 2. 对 App 内存模型的实际影响

- **Java/Kotlin 纯应用**：几乎无需改动，ART 自动处理
- **NDK/C++ 应用**：需要重新编译，否则 `.so` 对齐不正确导致浪费内存
  - 每个 `.so` 段从 4KB 边界变为 16KB 边界 → 小段浪费更多空间
  - 硬编码 `PAGE_SIZE=4096` 的代码会出错
- **第三方 SDK**：React Native、Flutter 等框架已提供兼容版本

### 3. 迁移技术要点

```
# AGP 8.5.1+ 自动 16KB 对齐
android {
    // 无需手动配置，AGP 自动处理

    # NDK r28+ 默认 16KB ELF alignment
    # 旧版 NDK 需添加：
    # -Wl,-z,max-page-size=16384
}

# 检测硬编码页大小
# 错误: #define PAGE_SIZE 4096
# 正确: sysconf(_SC_PAGESIZE)
```

### 4. Google Play 强制时间线

- **2025-11-01**：新应用和更新必须支持 16KB page size
- 可能延期到 **2026-03**
- 单一二进制兼容 4KB 和 16KB 设备

### 5. 测试方法

- Pixel 8/9 开发者选项 "Boot with 16KB page size"
- Android Studio AVD (API 35 "16KB" 镜像)
- APK Analyzer 检查 ELF 段对齐

## 与 4.5 章节的关联

- 4.5 应涵盖 "App 级内存优化策略"，16KB page size 是 2025-2026 最大的平台级内存变更
- 需要强调：不是"可选优化"而是"强制迁移"
- 与 4.3 (ART 内存管理) 中 16KB page 对 ART 分配器的影响形成呼应

## 可验证性

- [已验证] 性能数据来自 Google 官方博客
- [已验证] 迁移步骤来自 developer.android.com 官方文档
- [待验证] Google Play 延期到 2026-03 的说法

## 原始链接

- https://developer.android.com/build/apps/16kb-page-size
- https://android-developers.googleblog.com/2024/10/16kb-page-size-android-15.html
