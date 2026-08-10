---

title: "存储 Benchmark（AndroBench、A1 SD Bench）"
chapter: "19"
section: "19.22"
status: finalized
drafted_date: "2026-04-24"
drafted_by: "codex"
applicable_versions: "历史存储 Benchmark 参考；Android 10/11+ 路径权限需逐机验证；方法可用于 Android 8 (API 26) - Android 17 (API 37) 的设备基线分析"
last_verified: "2026-04-24"
last_verified_against: "AndroBench paper / A1 SD Bench public materials / Android 11 scoped storage docs"
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
pipeline_stage: ready-to-publish
task6_state: reviewed
reviewed_by: "openclaw-task6"
reviewed_date: "2026-04-25"
task6_result: pass-light-edit
last_task6_audit: "2026-07-11"
task9_state: reviewed
task9_result: pass-tech-review
task2b_state: fixed
task9_reviewed_date: "2026-04-25"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-04-25T17:41:15+08:00"
last_task9_audit: "2026-07-16"
task2b_result: fixed
last_task2b_at: "2026-04-25T02:45:50+08:00"
repaired_date: "2026-04-25"
repaired_by: openclaw-task2b
deepseek_polish_state: done
last_deepseek_polish_at: "2026-05-25"
---

# 存储 Benchmark（AndroBench、A1 SD Bench）

## 存储 Benchmark 只能给设备背景

存储 Benchmark 在固定路径中生成受控读写，用来描述“这台设备在这套工具和这组参数下”的 I/O 基线。它不能指出 App 哪个文件、线程或 SQL 慢，也不能证明一次 `read()` 已经访问闪存介质。

从跑分到 App 结论至少要跨过三层：

1. Benchmark 层：文件大小、块大小、读写模式、缓存和同步语义是什么。
2. Android 路径层：App 私有目录、共享存储、SAF、MediaStore 或可移除卷经过了哪些权限与挂载路径。
3. 业务层：调用栈、线程、文件名、事务、查询计划和用户场景是什么。

存储分数适合解释“为什么同一段同步 I/O 在某些低端设备上更容易放大”，不适合代替调用栈和 trace 做根因判断。

## 工具状态：AndroBench 与 A1 SD Bench 以历史口径为主

### AndroBench 的公开协议来自 2011 年

AndroBench 论文把测试分成两组：

- Micro benchmark：顺序读、顺序写、随机读、随机写。
- SQLite benchmark：对模拟消息表执行 insert、update、delete，并报告事务吞吐。

论文中的原始默认参数也暴露了它的年代边界：顺序读文件 32 MB、读 buffer 256 KB，顺序写文件 2 MB；随机读写使用 4 KB 操作，读文件 32 MB、写文件 2 MB，每项取三轮平均值。对拥有数 GB 内存和高速 UFS 的 Android 17 设备，这些文件很容易被页缓存、写缓冲和短时突发能力主导。

公开包记录显示后续 AndroBench 版本调整过 UI、SQLite 测试和文件加密兼容，但没有可公开审计的当前官方实现与 Android 17 验证报告。旧报告可以继续读，新设备库不应把默认 AndroBench 截图当作现代存储能力标准。若因历史连续性必须补测，要保存 APK 版本、hash 和设置页全部参数。

### A1 SD Bench 的模式名称不等于可审计协议

A1 SD Bench 的公开包描述列出 Quick、Longer、Accurate、Random I/O，以及内部存储、SD 卡、RAM、USB 和 custom location。仅凭这些名称无法知道每种模式是否绕过页缓存、何时同步数据、随机块多大、是否预分配文件或如何汇总结果。

因此，它更适合做路径可达性和历史介质对比：

- custom location 的结果是“API/路径 + 挂载 + 文件系统 + 介质”的组合。
- RAM 测试测内存或工具缓冲路径，不能与 UFS、eMMC 或 SD 卡比较。
- SD/USB 结果还受读卡器、总线、文件系统和授权方式影响，不能只归因于卡片。
- 不同模式不能只因单位相同就放在一张排名表中。

名称中的 “A1” 也不表示该 App 能完成 SD Association 的 Application Performance Class 认证。SD A1/A2 标识有专门的随机 IOPS 与持续顺序写入规范；手机、读卡器、文件系统和未公开的 App 测试协议都可能限制结果。跑分低于或高于某个数，均不能单独证明卡片真伪或认证是否有效。

### Android 17 新基线优先选择可审计工具

新设备实验室可以考虑两类替代：

- CPDT：项目开源，设置中公开文件大小、4 KB 随机测试、write buffering 和 in-memory caching 开关，并能导出时序或直方图。Google Play 当前记录停在 2024-09-12，Android 17 上仍要先做兼容与源码版本验证。
- PCMark Storage 2.0：适合内部存储、外部存储和 SQLite 的组合工作负载，但它是 workload 分数，不是裸 UFS 吞吐。

最接近业务的方案仍是自建受控测试：在目标 App 实际目录中使用相同文件格式、SQLite schema、事务、同步语义和线程模型。第三方工具负责横向设备背景，自建测试负责业务预测力。

## 四类 Micro 指标不能混看

| 指标 | 必须附带的参数 | 适合提出的假设 | 不能直接解释什么 |
|---|---|---|---|
| 顺序读吞吐 | 文件大小、buffer、缓存状态、并发数 | 大资源、视频、离线包连续读取上限 | 大量小文件冷启动 |
| 顺序写吞吐 | 文件大小、buffer、buffered/direct、`fsync`/`fdatasync` 语义 | 下载、导出、批量日志的持续写入 | 单条事务提交延迟 |
| 随机读 IOPS/latency | block size、文件范围、队列深度、线程数、访问分布 | 小块读取和索引访问的设备背景 | 目录扫描、SQL 规划或反序列化 CPU |
| 随机写 IOPS/latency | 同上，另加同步频率与预分配方式 | 小块写、数据库日志和元数据更新风险 | 业务事务是否合理 |

IOPS 没有 block size 就缺少工程意义。`40,000 IOPS @ 4 KiB, QD1` 与 `40,000 IOPS @ 16 KiB, QD8` 不是同一个能力。顺序和随机结果也不能相互换算。

### 单位与分位数的方向

- MB/s、IOPS、QPS 越高越好。报告中应保存工具原始单位；若能导出 bytes 和 elapsed time，还要说明 MB 是 `10^6` bytes 还是 MiB 的 `2^20` bytes。
- latency 越低越好。单次操作分布可报告 p50、p95、p99。
- 吞吐的坏尾位于低侧。多轮吞吐应报告 median 与 P10，不能把 P95 当作保守值；P95 吞吐更接近一次乐观高分。
- 只有 5 个轮次时，P10/P95 都不稳定，优先列出中位数、最小值、最大值和 MAD。工具能导出数千个 block latency 时，再计算延迟分位数。
- AndroBench SQLite 的 QPS 是一组事务的汇总吞吐，不是单条 SQL 的 p95 latency。

## 路径决定你测到什么

Android 官方将存储分为 app-specific internal、app-specific external、共享媒体和文档等用途。面向 Android 17 / API 37，报告不能只写 `/sdcard` 或“internal storage”。

| 测试路径 | Android 17 访问模型 | 结果边界 |
|---|---|---|
| `filesDir`、`cacheDir`、`databasePath` | App 私有内部存储，无需共享存储权限 | 最接近数据库、配置和私有缓存；仍包含文件系统、加密与内核缓存 |
| `getExternalFilesDir()` / `externalCacheDir` | App-specific external；Android 4.4+ 通常无需存储权限，卸载时删除 | 可能位于主共享卷或可移除卷；关键数据不能假设它永远可用 |
| MediaStore | 按媒体集合与授权访问共享内容 | 包含 provider、权限、元数据与介质成本，不等于直接文件 I/O |
| Storage Access Framework | 用户选择 document tree 或单个 URI | 包含 `DocumentsProvider`、Binder、provider 实现和底层介质 |
| 可移除 SD / USB | 卷、授权、厂商挂载和硬件支持共同决定 | 只代表对应外设场景，不代表 App 私有内部目录 |
| RAM | 内存复制或内存文件路径 | 用于观察内存上限，不能写入存储介质排名 |

Scoped storage 从 target Android 10 起约束共享存储；target Android 11 起，`WRITE_EXTERNAL_STORAGE` 不再扩大访问范围。Android 11 还限制 App 自行创建外部 app-specific 目录，应通过系统 API 获取路径。历史工具若依赖任意路径或旧式存储权限，在 Android 17 上可能测到不同目录、无法访问目标卷，或只剩内部路径。

## 页缓存、写回和持久化语义

### “写完”可能只表示数据进入内存

普通 buffered write 可以在数据进入内核页缓存后返回，脏页稍后写回。若测试没有明确的 `fsync`、`fdatasync` 或等价协议，它更接近“用户空间到页缓存”的突发吞吐，不等于数据已经安全到达非易失介质。

同步语义也有成本差异。Android SQLite 官方性能指南指出，WAL 模式下同步设置会在 durability 与 commit latency 之间取舍；`synchronous=NORMAL` 允许 commit 在数据到盘前返回，掉电或 kernel panic 时可能丢失最近提交，但数据库日志仍用于避免结构损坏。业务不能只为跑分修改 durability，要按数据丢失风险选择。

Android 17 平台源码中，`SharedPreferencesImpl.commit()` 会等待 `writtenToDiskLatch`，而 `apply()` 将磁盘写入入队。`apply()` 缩短调用者等待不等于取消 I/O；写入仍可能与启动、退出或其他任务竞争。对主线程问题应减少无必要更新、合并键值，并测量调用与落盘两个阶段。

### 冷读和热读是两个问题

Linux 页缓存让后续读取直接从内存满足。`android17-6.18-2026-06_r6` 的 `mm/filemap.c` 是通用 file cache 路径源码锚点；F2FS 文档还显示 garbage collection、discard 和 `fsync_mode` 都会改变写入与同步行为。

测试报告应把以下结果分开：

- cold-like：工具明确关闭 in-memory cache，或实验室有受控的 cache reset 协议。
- warm：相同数据已经读取，允许页缓存命中。
- first run after reboot：包含开机扫描、dexopt、同步和温控变化，不能自动等同于纯冷介质读取。

在量产 user build 上不要为了跑分尝试写 `/proc/sys/vm/drop_caches`。该操作通常需要 root，并会影响整机缓存。实验室 userdebug 设备若使用它，要单列实验组并记录命令；不能和普通用户设备结果混合。

### 剩余空间、温度和后台活动

闪存控制器缓存、磨损均衡、文件系统 GC、discard、加密、后台媒体扫描和系统更新都会改变结果。F2FS 在空间回收时可能触发前台或后台 GC，因此“同型号同工具”也会随剩余空间和使用历史波动。

不要把跑分反推成 “UFS 4.0” 或 “eMMC”。Android 公共 API 没有稳定的物理介质型号接口，`df` 或 `/proc/mounts` 只能告诉你文件系统与挂载信息。介质类型应来自厂商规格、硬件清单或可审计的设备节点证据；无法确认就写 `unknown`。

## 可复现测试规范

### 固定设备与运行条件

- 记录市场型号、SKU、SoC、RAM、容量、Android build fingerprint、安全补丁、实际 kernel release。
- 记录 Benchmark 包名、版本、APK hash、测试模式、目标路径与路径 API。
- 固定一段剩余空间区间，不把接近满盘和空盘设备放在同组；保存 free bytes 与 free ratio。
- 固定文件系统、挂载参数、文件大小、block/buffer、并发数、缓存开关、write buffering 和同步协议。
- 固定室温、起始 thermal status、电量、充电状态和性能/省电模式。
- 停止无关下载、媒体扫描、应用更新、云同步和录屏；发生通知、来电或后台安装的轮次作废。

以下命令用于保存 Android 17 设备与 `/data` 的只读快照：

```bash
adb shell getprop ro.build.fingerprint
adb shell getprop ro.build.version.security_patch
adb shell uname -r
adb shell df -h /data
adb shell cat /proc/mounts
adb shell dumpsys diskstats
adb shell dumpsys battery
adb shell dumpsys thermalservice
```

`/proc/mounts` 可帮助确认 `/data` 是否为 F2FS、ext4 或其他文件系统，但不能可靠识别 UFS/eMMC 型号。`dumpsys diskstats` 是系统统计背景，也不是 Benchmark 结果。

### 设计轮次

- 文件大小要足以暴露缓存影响，同时避免填满设备；先做预实验，再冻结每个设备组的统一设置。
- 冷样与热样分开。重启后要等待开机后台任务稳定，并记录等待条件。
- 至少保留 5 轮短测试；用中位数、最小值、最大值和 MAD 描述轮间波动。
- 能导出每次 block latency 时，保存原始 CSV，再计算 p50/p95/p99。
- 第一次运行、预热轮和正式轮不要混在一个汇总值里。
- 工具版本、设置或 Android OTA 变化时切分时间序列。

测试的目标是获得稳定、可解释的分布，不是寻找最高截图。某轮比中位数高 20% 时，应检查缓存、温度和后台任务，不能直接把它选作设备成绩。

## 从指标映射到 App 场景

| App 场景 | 相关设备基线 | 还要补的业务证据 |
|---|---|---|
| 冷启动读取配置、资源索引 | cold-like 小块随机读、目录元数据 | 启动 trace、文件路径、读取次数、反序列化 CPU |
| 图片/视频缓存回读 | 顺序读与随机读，按对象大小选择 | 命中率、解码时间、网络回源、缓存淘汰 |
| 下载和导出 | 持续顺序写、同步频率 | 网络、解密、校验、rename 与最终 durability |
| 离线包解压 | 顺序读写与小文件创建 | 解压 CPU、文件数量、校验和目录更新 |
| 日志追加与切片 | 小块写、`fsync`/flush 模式 | 主线程调用栈、批量大小、丢日志容忍度 |
| SQLite 消息或缓存 | 随机读写和 SQLite workload | schema、索引、事务、WAL、checkpoint、query plan |
| 目录扫描 | 元数据与小文件访问 | `getdents/stat` 次数、排序与业务过滤 CPU |

一项业务常同时受 CPU、锁和 I/O 影响。资源解压慢可能来自解压算法；目录扫描慢可能来自几十万个 `stat` 与排序；数据库慢可能是全表扫描。不能因设备随机读低就跳过业务分析。

## SQLite：测试设备，也要测试数据库设计

AndroBench 的 insert/update/delete QPS 使用它自己的表、事务数量、journal mode 和索引。它能描述固定 SQLite workload 的设备背景，不能预测业务数据库的单条查询。

业务排查至少覆盖：

- 一批写入是否放进同一事务。Android 官方指南建议批量 insert 使用事务，并指出同一时间只能有一个 write transaction。
- 是否启用 WAL，`synchronous` 级别是什么，checkpoint 是否在关键交互窗口发生。
- 查询是否只读必要的行和列，是否存在 N+1 查询。
- WHERE、ORDER BY、GROUP BY 的索引是否匹配，索引维护成本是否值得。
- 大 BLOB、数据库页、外部文件与缓存策略是否合理。
- 业务 p50/p95 latency 和 rows scanned，而非只有总 QPS。

下面的查询用于检查会话消息列表是否发生全表扫描或额外排序：

```sql
EXPLAIN QUERY PLAN
SELECT id, sender_id, created_at, body
FROM messages
WHERE conversation_id = 42
ORDER BY created_at DESC
LIMIT 50;
```

结果中的 `SCAN`、`SEARCH ... USING INDEX` 和 `USE TEMP B-TREE` 分别提示扫描、索引访问与临时排序方向。查询计划只是诊断入口，还要在目标 Android SQLite 版本、真实数据量和绑定参数上计时。

Android 官方文档还提供 `database` atrace category，可在 Perfetto 配置中加入查询轨道。它能把 SQL 与线程时间对齐，但仍要结合事务边界、文件事件和调度状态解释。

## Perfetto、Matrix IO Canary 与业务日志的证据分工

| 证据 | 能回答的问题 | 边界 |
|---|---|---|
| 存储 Benchmark | 设备在固定 workload 下的相对下限与波动 | 没有 App 文件和调用栈 |
| Perfetto `database`、ftrace 文件系统/块事件 | 哪段时间发生查询、调度等待或内核 I/O | user build 可用事件受权限与配置限制 |
| Matrix IO Canary | 当前实现可检测主线程文件 I/O、小 buffer、重复读和 closeable 泄漏，并上报路径、线程和 stack 等信息 | Hook 覆盖受 Matrix 版本、ABI、Android/Bionic 与调用路径影响 |
| StrictMode / 自研埋点 | 主线程磁盘访问、业务阶段和文件语义 | 采样与插桩本身需要控制开销 |
| SQLite query plan / trace | SQL、索引、事务和执行时间 | 不描述全部文件系统与闪存行为 |

Matrix 当前公开仓库的 IO Canary 核心在启用相关 detector 时安装 native hook；JNI 源码列出了 `open/open64/read/write/close` 等 POSIX 入口，并将 path、buffer、operation cost、thread name 和 stack 组装成 issue。仓库 master 最近提交停在 2023 年，Android 17 上使用前要验证目标 ABI、16 KB page-size 设备、Bionic 路径和 Hook 成功率，不能假设它捕获所有 Java、native、mmap 或 provider I/O。

线程进入 `D` 状态只表示不可中断等待，可能来自块 I/O，也可能来自其他内核等待。只有当它与文件系统/块事件、文件调用栈或数据库事件对齐时，才能写成存储阻塞证据。

## 一个低随机写设备上的分析示例

下面是虚构的排查过程，用于展示证据如何组合：

1. 设备库显示某档设备的 4 KiB QD1 random-write median 和 P10 都明显低于主流档，但顺序读正常。
2. 同一 App 版本的冷启动 P95 只在该档设备恶化，网络与启动页面保持一致。
3. Matrix IO Canary 在启动窗口捕获主线程对日志文件的重复小 buffer 写入；Perfetto 中对应时间段出现文件系统写入与主线程阻塞。
4. 将日志改为后台批量写入，去掉每条日志的同步持久化后，目标档冷启动 P95 改善，高档设备变化较小。

这里的结论是“同步小写入放大了弱随机写设备的启动成本”。Benchmark 提供设备背景，调用栈和 trace 确定代码位置，A/B 或受控回归证明修改有效。任意一项证据都不能独立完成这条推理。

## 低端设备的优化方向

- 启动关键路径只读取首屏必需数据，其余配置和离线资源延后。
- 减少无意义的小文件；是否合并为数据库 BLOB、索引文件或归档，要用真实读写与更新模式验证。
- `SharedPreferences` 避免主线程 `commit()`；`apply()` 仍会写盘，更新频率和键值合并也要控制。
- SQLite 批量写入使用事务，查询只取必要列与行，并用 `EXPLAIN QUERY PLAN` 检查索引。
- 日志、统计和缓存元数据按容错要求批量写入。审计、支付等必须持久化的数据不能只为性能减少同步。
- 图片和离线资源维护可增量更新的索引，避免每次启动全目录扫描。
- 解压、校验、checkpoint、vacuum 和大批量删除避开首屏与动画窗口。
- 优化后在低存储档设备上重跑 App 场景，不用第三方总分代替验收。

## 存储测试报告模板

下面的模板区分环境、协议、原始指标与 App 证据：

```yaml
report_id: storage-2026-07-25-001
device:
  brand: ""
  model: ""
  sku: ""
  soc: ""
  ram_gb: 0
  storage_capacity_gb: 0
  storage_type: "unknown"
  storage_type_evidence: ""
platform:
  android_release: "17"
  api_level: 37
  build_fingerprint: ""
  security_patch: ""
  kernel_release: ""
  filesystem: ""
  mount_options: ""
space:
  total_bytes: 0
  free_bytes: 0
  free_ratio: 0.0
benchmark:
  package: ""
  app_version: ""
  apk_sha256: ""
  test_name: ""
  target_path: ""
  path_api: ""
protocol:
  file_size_bytes: 0
  block_size_bytes: 0
  buffer_size_bytes: 0
  queue_depth: 1
  threads: 1
  random_pattern: ""
  in_memory_cache: ""
  write_buffering: ""
  sync_semantics: ""
  warmup_runs: 0
  valid_runs: 5
conditions:
  room_temperature_c: null
  surface_temperature_start_c: null
  thermal_status_start: ""
  battery_percent: null
  charging: false
results:
  sequential_read_mb_s:
    median: null
    min: null
    max: null
    mad: null
  random_write_iops:
    median: null
    min: null
    max: null
    mad: null
  operation_latency_ms:
    p50: null
    p95: null
    p99: null
  sqlite_qps: {}
artifacts:
  raw_export: ""
  perfetto_trace: ""
  matrix_issue: ""
app_validation:
  app_version: ""
  scenario: ""
  metric: ""
  result: ""
notes: ""
```

`storage_type` 没有可靠证据时保留 `unknown`。吞吐与 IOPS 的 P10 可在轮次足够时从原始数据计算；模板默认保存更适合 5 轮实验的中位数、极值和 MAD。App 验证字段用于防止报告把设备跑分误写成业务结论。

## 源码与资料

- [AndroBench 论文 DOI](https://doi.org/10.1007/978-3-642-27552-4_89)
- [SNU AndroBench 论文记录](https://snu.elsevierpure.com/en/publications/androbench-benchmarking-the-storage-performance-of-android-based-/)
- [A1 SD Bench 公共包记录（仅用于核对功能描述）](https://www.apkmirror.com/apk/tuxera-inc/a1-sd-bench/)
- [SD Association Application Performance Class](https://www.sdcard.org/consumers/about-sd-memory-card-choices/application-performance-class-for-running-smartphone-apps/)
- [CPDT Google Play 说明](https://play.google.com/store/apps/details?id=com.Saplin.CPDT)
- [CPDT 源码（a507cda）](https://github.com/maxim-saplin/CrossPlatformDiskTest/tree/a507cda4f487afc9334e0f02673af34a366961d9)
- [PCMark Storage 2.0](https://benchmarks.ul.com/pcmark-android)
- [Android 数据与文件存储概览](https://developer.android.com/training/data-storage)
- [Android app-specific 文件](https://developer.android.com/training/data-storage/app-specific)
- [Android 11 scoped storage 变更](https://developer.android.com/about/versions/11/privacy/storage)
- [Android SQLite 性能指南](https://developer.android.com/topic/performance/sqlite-performance-best-practices)
- [AOSP `SharedPreferencesImpl`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/SharedPreferencesImpl.java)
- [AOSP `SQLiteDatabase`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/database/sqlite/SQLiteDatabase.java)
- [AOSP `ContextImpl` 存储路径（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ContextImpl.java)
- [Matrix IO Canary 源码（3b8293b）](https://github.com/Tencent/matrix/tree/3b8293bd65d47eeea7caf1f32a3a5d4d5eab60e7/matrix/matrix-android/matrix-io-canary)
- [Matrix POSIX I/O Hook（3b8293b）](https://github.com/Tencent/matrix/blob/3b8293bd65d47eeea7caf1f32a3a5d4d5eab60e7/matrix/matrix-android/matrix-io-canary/src/main/cpp/io_canary_jni.cc)
- [Linux F2FS 文档（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/filesystems/f2fs.rst)
- [Linux file cache 源码（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/filemap.c)
- [Linux `fsync` 源码（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/sync.c)
