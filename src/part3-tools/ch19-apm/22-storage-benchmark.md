---
title: "存储 Benchmark（AndroBench、A1 SD Bench）"
chapter: "19"
section: "19.22"
status: draft
drafted_date: "2026-04-24"
drafted_by: "codex"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-24"
last_verified_against: "AndroBench paper / public app descriptions / A1 SD Bench public app descriptions"
confidence: medium
tags: [apm]
related_chapters: ["19.0"]
sources:
  - type: paper
    path: "https://doi.org/10.1007/978-3-642-27552-4_89"
  - type: blog
    path: "https://apkpure.com/androbench-storage-benchmark/com.andromeda.androbench2"
  - type: blog
    path: "https://apkpure.com/a1-sd-bench/com.a1dev.sdbench"
pipeline_stage: drafted
---

# 存储 Benchmark（AndroBench、A1 SD Bench）

## 存储 Benchmark 看的是 I/O 基线

AndroBench、A1 SD Bench 这类工具用于测 Android 设备存储读写能力。它们和 App 内部 I/O 分析不同：Benchmark 给的是设备或存储介质基线，App 分析要看具体文件、线程、调用路径和缓存策略。

存储基线很有用。启动慢、数据库慢、图片缓存慢、解压慢、日志写入慢，都可能和低端设备的随机 I/O 能力有关。

## AndroBench：Micro 和 SQLite

AndroBench 的论文和应用说明都把它定位为 Android 存储性能 benchmark。它测两类内容：

- **Micro benchmark**：顺序读写、随机读写等基础 I/O。
- **SQLite benchmark**：模拟数据库表上的 insert、update、delete 等事务吞吐。

这两个维度要分开看。顺序读取高，说明大文件读取能力不错；随机写差，说明小文件、数据库、日志、缓存索引可能更容易慢。SQLite 事务差，则更贴近聊天、列表、缓存元数据这类数据库密集场景。

## A1 SD Bench：更偏介质和路径测试

A1 SD Bench 公开说明中列出 Quick、Longer、Accurate、Random I/O 等模式，支持 SD 卡、内部存储、RAM、USB 存储等介质，并可测试自定义路径。

它适合回答：

- 内置存储和外置 SD 卡差多少。
- 某个自定义目录读写速度是否异常。
- SD 卡或 USB 存储是否满足业务文件写入需求。
- 简单读写测试是否受缓存影响。

对 Android App 来说，外置存储测试现在没有早期那么常见，但在相机、离线地图、文件管理、车机、工业设备和大媒体文件场景里仍然有意义。

## 顺序和随机不能混看

存储测试里最容易误读的是只看顺序读写。很多设备顺序读取数字很好看，但随机写入很差。App 日常更容易碰到的是随机小 I/O：

- SQLite 写事务。
- SharedPreferences 或 DataStore 更新。
- 图片缓存索引。
- 日志追加和切片。
- 启动阶段大量小文件读取。

所以存储 Benchmark 报告里至少要保留四个数：顺序读、顺序写、随机读、随机写。数据库场景再加 SQLite insert / update / delete。

## 测试条件

存储 Benchmark 对环境很敏感：

- 剩余空间不足会影响写入表现。
- 文件系统缓存会让第二次测试变快。
- 温度、后台写入、系统扫描会干扰结果。
- F2FS、ext4、UFS、eMMC、SD 卡等级都会改变结果。
- 加密、用户空间文件系统和厂商 ROM 策略会改变 App 侧实际体验。

测试时要连续多轮，并记录首次和稳定后的差异。只取最好的一次，通常会高估存储能力。

## 和 App I/O 分析的连接方式

存储 Benchmark 只能告诉你设备基线。要修 App I/O 问题，还要回到具体调用：

- Perfetto 看主线程是否被 I/O 阻塞，线程是否进入 D 状态。
- Matrix IO Canary 或自研 Hook 看哪个文件被读写、buffer 多大、是否重复读。
- SQLite tracing 看事务是否过长、是否缺索引、是否主线程执行。
- Benchmark 数据用于解释为什么某些低端机更容易放大问题。

存储性能优化不能只靠“换设备跑分”。业务侧要减少启动阶段小文件数量，合并写入，避免主线程 I/O，给数据库事务和缓存设计明确边界。Benchmark 提供下限，代码分析负责定位。

## 指标怎么对应 App 场景

存储 Benchmark 的几个指标和 App 场景可以这样对应：

| 指标 | 对应场景 | 典型问题 |
|---|---|---|
| 顺序读 | 读取大图片、视频片段、离线包 | 首次打开大资源慢 |
| 顺序写 | 下载文件、日志批量写入、导出数据 | 下载完成落盘慢 |
| 随机读 | 启动阶段读多个小文件、缓存索引 | 冷启动慢、页面打开慢 |
| 随机写 | SharedPreferences、SQLite、日志追加 | 主线程 I/O、事务慢 |
| SQLite insert | 批量写入消息、缓存元数据 | 数据导入慢 |
| SQLite update/delete | 会话状态、历史记录、缓存清理 | 页面退出或同步时卡顿 |

这张表能帮助读者把跑分和业务问题连接起来。顺序读写高不代表 SQLite 快，SQLite 快也不代表启动小文件读取快。

## 测试文件大小和缓存效应

存储测试必须考虑缓存。小文件测试可能命中文件系统缓存，第二次结果明显变好；大文件测试可能超过缓存，更接近真实介质速度。

建议报告里写清：

- 测试文件大小。
- 测试轮次。
- 首轮结果和稳定结果。
- 是否清缓存或重启设备。
- 剩余存储空间。

如果只给一个“读取 800MB/s”，读者不知道它来自缓存、顺序读取，还是介质真实性能。

## SQLite benchmark 的解释

SQLite benchmark 更贴近 App 日常。很多性能问题来自数据库使用方式放大了磁盘成本，不能简单归因于“磁盘慢”：

- 每条数据单独事务提交。
- 主线程执行查询或写入。
- 缺索引导致全表扫描。
- 大字段和小字段混在同一张表。
- WAL、checkpoint、vacuum 时机不受控。

AndroBench 的 SQLite 分数只能说明设备数据库 I/O 基线。业务数据库慢，还要用 SQLite tracing、`EXPLAIN QUERY PLAN`、Perfetto 和应用日志继续查。

## 低端存储上的优化策略

当线上问题集中在低随机 I/O 设备时，优化方向通常是：

- 启动阶段减少小文件数量，把配置合并或延迟读取。
- SharedPreferences 改批量写入，避免 `commit()` 在主线程执行。
- 数据库写入合并事务，避免逐条提交。
- 图片和离线资源用索引文件减少目录扫描。
- 日志写入放后台，限制 flush 频率。
- 大文件解压和校验放到首屏后。

这些优化要用 Perfetto 验证。看主线程是否还会进入 D 状态，启动关键窗口内是否仍有密集小 I/O。

## 与 Matrix IO Canary 的分工

存储 Benchmark 和 Matrix IO Canary 刚好互补：

- Benchmark 告诉你设备 I/O 下限。
- IO Canary 告诉你 App 哪些文件、哪些线程、哪些调用在使用 I/O。

如果低端机随机写差，IO Canary 又显示启动期间主线程重复写日志，那就是明确优化点。如果 Benchmark 显示设备很强，但 App 仍然 I/O 慢，更可能是业务代码重复读写、锁竞争或数据库设计问题。

## 建议的存储测试报告

一份可用报告应包含：

```text
device: Redmi Note 12
storage: UFS/eMMC/unknown
free_space: 38GB / 128GB
filesystem: F2FS
rounds: 5
sequential_read_mb_s: median / p95
sequential_write_mb_s: median / p95
random_read_iops: median / p95
random_write_iops: median / p95
sqlite_insert_qps: median
sqlite_update_qps: median
temperature_start/end: 34C / 39C
notes: airplane mode, background apps cleared
```

有了这些条件，存储数据才能用于机型分层和版本对比。否则它只是一次不可复现的跑分截图。
