
## [2026-04-08] 1.1 Android 分层架构 — Zygote 预加载机制源码路径缺失

### 盲区描述
正文描述了"Zygote 进程预加载了 ART 运行时、常用 Java 类、系统资源"，但未给出 `preload()` 方法的源码路径和关键片段。性能分析中，理解 Zygote 预加载了哪些类（`preloadClasses()` / `preloadResources()` 的具体内容和大小）对分析冷启动瓶颈至关重要——如果某个 App 依赖的类不在预加载列表中，就会导致额外的初始化时间。

### 重要程度
高

### 建议研究方向
- 找到 Zygote.java 中 `preloadClasses()` 和 `preloadResources()` 的完整实现
- 确认 Android 16 中预加载列表的变化（是否有新增/删除的预加载类）
- 量化预加载资源的大小（通常在 30-50MB 范围）
- 分析 App 冷启动中 Zygote fork 后、App 代码执行前这段时间的初始化来源（ART 初始化 vs 资源加载）

### 关联章节
1.2（boot-process）、1.11（zygote-startup）、1.7（art-compilation）、8.3（launch-optimization）

## [2026-04-08] 1.2 系统启动全流程 — 知识盲区

### 盲区描述
Zygote fork SystemServer 的触发机制：当前章节描述"Zygote 预加载完成后 fork SystemServer"，但未说明这个 fork 是 ZygoteInit.main() 的主动行为（ZygoteInit.main() 内部调用 startSystemServer()）还是被动等待信号。实际上这是 ZygoteInit 的硬编码流程，不需要外部触发，但正文没有明确这一点，导致读者可能误以为 SystemServer fork 是被某种 IPC 触发的。

### 重要程度
高

### 建议研究方向
- 追溯 ZygoteInit.main() → startSystemServer() 的调用链，确认 Zygote.java vs ZygoteInit.java 的方法归属
- 调研 Zygote fork SystemServer 后，Zygote 主进程（孵蛋进程）和 SystemServer 的角色分化细节
- 对比 Zygote fork app 进程 vs fork SystemServer 的异同

### 关联章节
1.1（Zygote 在分层架构中的定位）、1.3（Zygote 预加载机制细节）、8.2（Zygote 进程监控）

---

## [2026-04-08] 1.2 系统启动全流程 — 知识盲区（SELinux）

### 盲区描述
init 阶段的安全初始化流程（SELinux 策略加载、restorecon）完全缺失。SELinux 加载时机、策略类型（enforcing/permissive）、对 init 阶段耗时的实际影响均未覆盖。这是 Android 安全启动链的重要组成部分，直接影响开机时间分析。

### 重要程度
中

### 建议研究方向
- 调研 init.rc 中 `restorecon` / `restorecon_recursive` 命令的执行时机
- 分析 SELinux 策略加载与 init 阶段耗时的关系
- 调研 Perfetto 中如何追踪 SELinux 加载（sched_wakeup 无法覆盖，需要 ftrace selinux 事件）

### 关联章节
1.1（Linux Kernel 启动）、14.1（Android 16 架构变化中可能有安全部分）

