---
title: "Baseline Profiles 与编译优化"
chapter: "19"
section: "19.15"
status: draft
drafted_date: "2026-04-24"
drafted_by: "codex"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-24"
last_verified_against: "Android Developers Baseline Profiles docs"
confidence: medium
tags: [apm]
related_chapters: ["19.0"]
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/overview"
pipeline_stage: drafted
---

# Baseline Profiles 与编译优化

## Baseline Profiles 是发布前优化，不是监控

Baseline Profiles 让应用或库随包发布一组常用代码路径，Android Runtime 可以据此提前做 AOT 编译。官方文档给出的目标很直接：优化启动、降低交互 jank，并让新用户和每次更新后的首次运行都受益。

它不属于 APM 采集工具，但和性能监控关系很近。线上启动慢或交互慢被发现后，Baseline Profiles 常常是修复手段之一；修复是否生效，再用 Macrobenchmark 和线上指标验证。

## 它解决的是首次运行性能

没有 profile 时，应用安装或更新后，很多代码路径要等运行中解释执行、JIT 编译或后台 profile 引导优化。用户首次打开时，关键路径可能还没被编译好。

Baseline Profiles 把“哪些类和方法值得提前优化”提前打包进去。ART 在安装或后台优化阶段可以根据这些规则编译指定代码，让启动和高频交互更早进入较好状态。

适合纳入 profile 的路径包括：

- 冷启动到首屏。
- 首页列表首次展示和滚动。
- 主导航切换。
- 搜索、详情页、支付等高频路径。
- 库作者提供的库初始化或热点 API。

不适合把全 App 都塞进去。profile 过宽会增加编译成本，也会稀释优化重点。

## 生成方式

应用通常用 Macrobenchmark 或 Baseline Profile Gradle Plugin 生成 profile。测试代码驱动 App 执行关键路径，工具记录触发到的类和方法，再输出 profile 文件。

常见流程是：

1. 写一组用户关键路径的 UI 自动化操作。
2. 运行 profile generation。
3. 把生成的 profile 合入源码。
4. 用 Macrobenchmark 分别测有 profile 和无 profile 的启动或交互。
5. 在 CI 中持续验证 profile 没有失效。

这个流程里的难点不在 API，而在路径选择。只录“打开首页”会漏掉很多高频交互；录太多路径，又会让 profile 变得臃肿。

## Baseline Profiles 和 Startup Profiles

Baseline Profiles 用于指定更广的热点代码路径，启动和交互都可以覆盖。Startup Profiles 更集中在 DEX layout 优化，目标是减少启动阶段需要加载的 DEX 页面和类加载成本。

简单区分：

- Baseline Profiles：让 ART 预先编译常用方法。
- Startup Profiles：帮助启动路径相关代码在 DEX 中布局得更利于加载。

两者可以配合，但不要把它们理解成同一个文件的两个名字。调启动时，既要看编译状态，也要看 DEX 布局、类加载、资源加载和业务初始化。

## 和 APM 的连接方式

线上 APM 里，Baseline Profiles 最常见的观测指标是：

- 冷启动 TTID / TTFD 是否下降。
- 首次安装或更新后首开是否变快。
- 首页首屏慢帧率是否下降。
- 关键交互 P95 是否下降。

这里要把用户群切清楚。老用户、刚更新用户、全新安装用户、清数据用户的编译状态不一样。只看全量平均启动耗时，容易把 profile 效果冲淡。

## 使用建议

Baseline Profiles 最适合和 Macrobenchmark 一起纳入发布流程。每次新增关键启动路径、重构首页、改动导航或接入大 SDK，都应该重新检查 profile。

如果线上启动慢来自网络等待、服务端接口、主线程 I/O、同步锁或厂商 ROM 调度，Baseline Profiles 只能改善代码执行和加载相关成本，不能解决所有慢启动。它是性能工具箱里很有效的一件工具，但不是万能修复开关。

## Profile 规则长什么样

Baseline Profile 最终会生成一组 ART profile 规则，描述哪些类和方法应该被优先优化。开发者通常不手写这些规则，但读得懂格式有助于排查。

规则大致会包含类、方法和 flag。示意如下：

```text
HSPLcom/example/app/MainActivity;->onCreate(Landroid/os/Bundle;)V
HLcom/example/app/HomeRepository;
Lcom/example/app/FeedItem;
```

实际生成内容由工具决定。书稿里需要记住的是：profile 不是“性能配置开关”，它是一组热点类和方法提示。它覆盖不到的路径，不会因为文件存在而自动变快。

## 生成场景要覆盖用户路径

Baseline Profile 的质量取决于生成脚本。只启动 App 一次，通常只能覆盖 `Application`、入口 Activity 和首屏一小段。更完整的生成脚本应该覆盖：

- 冷启动到首页首屏。
- 首页列表滚动一小段。
- 主导航切到核心 tab。
- 打开详情页。
- 触发一次核心业务操作，例如搜索或播放。

不要录太多低频路径。Profile 越宽，安装后编译成本越高，也越难维护。

## 验证 profile 是否生效

验证不能只看文件是否生成。要看三个层面：

1. APK / AAB 中是否包含 profile。
2. 安装后 ART 是否使用 profile 编译目标代码。
3. Macrobenchmark 指标是否改善。

常见问题：

- 生成脚本跑的是 Debug 包，profile 对 Release 路径覆盖不足。
- R8 后方法变化，旧 profile 命中率下降。
- 多模块或动态特性模块的关键路径没有被录到。
- CI 没有重新生成 profile，文件长期滞后。

所以 Baseline Profiles 应该和关键路径测试一起维护，而不是生成一次就放着。

## 启动优化中的位置

启动优化可以按三类成本看：

| 成本 | Baseline Profiles 是否能处理 | 其他工具 |
|---|---|---|
| 代码解释执行 / JIT 预热 | 能改善 | Macrobenchmark 验证 |
| 类加载和 DEX 布局 | 部分改善，配合 Startup Profiles | Perfetto、ART 日志 |
| 主线程 I/O、网络、锁等待、SDK 初始化 | 不能直接解决 | Perfetto、Matrix、StrictMode |

如果启动慢主要来自同步网络请求或主线程读大文件，profile 再好也只能改善一小部分。先用 Perfetto 判断启动时间花在哪，再决定是否用 Baseline Profiles。

## Library 作者的责任

库也可以提供 Baseline Profiles。对 UI 库、图片库、数据库库、序列化库来说，这能让使用方从首次运行就受益。

库作者生成 profile 时要覆盖公开 API 的典型路径，而不是只覆盖 sample App 的演示页面。并且要避免把 sample 业务代码录进库 profile。

应用方接入库 profile 后，仍然需要自己的应用 profile。库 profile 只能覆盖库内部热点，不能覆盖 App 启动和业务页面。

## 回归判断

Baseline Profiles 的回归通常表现为：

- 新版本冷启动 P50/P95 上升。
- 首次安装后前几次打开变慢。
- Macrobenchmark 中 profile-enabled 和 profile-disabled 差异缩小。
- trace 中解释执行、类加载或编译相关成本变多。

一旦发现回归，先检查生成脚本是否还能走到关键路径，再看最近是否做了包名、模块、R8、导航或启动流程调整。
