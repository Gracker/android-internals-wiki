#!/usr/bin/env python3
"""
Task 12: External Review Auto-Integration Script
Reads current state, integrates all 25 external review files, writes results.
"""

import json
from pathlib import Path
from datetime import datetime

BASE = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki")
QUEUE_PATH = BASE / "metadata" / "queue.json"
GAPS_PATH = BASE / "intake" / "research-gaps.md"
SUGGESTIONS_PATH = BASE / "intake" / "suggestions.md"
INTEGRATION_LOG_DIR = BASE / "logs" / "external-review-integration"

now = datetime.now()
TIMESTAMP = now.strftime("%Y-%m-%dT%H:%M:%S")
DATE = now.strftime("%Y-%m-%d")
TIME = now.strftime("%H:%M")

# ============================================================
# DATA: All 25 external reviews pre-extracted
# ============================================================

# section_key -> (section_path, section_title)
SECTION_MAP = {
    "4.0": ("src/part1-fundamentals/ch04-memory/README.md", "4.0 内存章节导读"),
    "4.5": ("src/part1-fundamentals/ch04-memory/05-app-memory-optimization.md", "4.5 App 内存优化"),
    "4.6": ("src/part1-fundamentals/ch04-memory/06-16kb-page-size.md", "4.6 16 KB Page Size"),
    "4.7": ("src/part1-fundamentals/ch04-memory/07-art-generational-gc.md", "4.7 ART 分代 GC、Region 碎片与暂停分析"),
    "5.0": ("src/part1-fundamentals/ch05-cpu-power/README.md", "5.0 CPU 与功耗章节导读"),
    "5.1": ("src/part1-fundamentals/ch05-cpu-power/01-linux-scheduling.md", "5.1 Linux 进程调度基础"),
    "5.2": ("src/part1-fundamentals/ch05-cpu-power/02-eas.md", "5.2 EAS 能量感知调度"),
    "5.3": ("src/part1-fundamentals/ch05-cpu-power/03-big-little.md", "5.3 大小核架构"),
    "5.4": ("src/part1-fundamentals/ch05-cpu-power/04-dvfs.md", "5.4 DVFS 动态调频"),
    "5.8": ("src/part1-fundamentals/ch05-cpu-power/08-background-execution.md", "5.8 后台执行限制"),
    "5.9": ("src/part1-fundamentals/ch05-cpu-power/09-adpf.md", "5.9 ADPF 自适应性能框架"),
    "5.10": ("src/part1-fundamentals/ch05-cpu-power/10-jobscheduler-workmanager-performance.md", "5.10 JobScheduler/WorkManager 性能"),
    "5.11": ("src/part1-fundamentals/ch05-cpu-power/11-ondevice-ml-inference-performance.md", "5.11 端侧 AI 推理性能"),
    "5.12": ("src/part1-fundamentals/ch05-cpu-power/12-thermal-management-deep-dive.md", "5.12 热管理深度分析"),
    "6.0": ("src/part1-fundamentals/ch06-storage/README.md", "6.0 存储章节导读"),
    "6.1": ("src/part1-fundamentals/ch06-storage/01-storage-architecture.md", "6.1 存储架构"),
    "6.2": ("src/part1-fundamentals/ch06-storage/02-filesystem.md", "6.2 文件系统"),
    "6.4": ("src/part1-fundamentals/ch06-storage/04-sharedpreferences-datastore.md", "6.4 SharedPreferences/DataStore"),
    "6.5": ("src/part1-fundamentals/ch06-storage/05-vold-mediaprovider-fuse.md", "6.5 vold/MediaProvider/FUSE"),
    "7.2": ("src/part2-performance/ch07-smoothness/02-jank-causes.md", "7.2 卡顿原因体系"),
    "7.3": ("src/part2-performance/ch07-smoothness/03-jank-methodology.md", "7.3 卡顿分析方法论"),
    "7.4": ("src/part2-performance/ch07-smoothness/04-typical-scenarios.md", "7.4 典型场景卡顿根因"),
    "7.6": ("src/part2-performance/ch07-smoothness/06-case-studies.md", "7.6 案例实战分析"),
    "7.7": ("src/part2-performance/ch07-smoothness/07-compose-performance.md", "7.7 Compose 性能优化"),
    "7.8": ("src/part2-performance/ch07-smoothness/08-recyclerview-performance.md", "7.8 RecyclerView 深度优化"),
}

# Queue entries: section_key -> {priority, issues: [{type, location, detail, suggestion, evidence}]}
QUEUE_DATA = {
    "4.0": {
        "priority": 85,
        "issues": [
            {
                "type": "交叉引用缺失",
                "location": "本章内容列表",
                "detail": "章节导读需要覆盖 4.1-4.17 的当前主文",
                "suggestion": "按当前连续编号核对索引，确保与目录文件一致",
                "evidence": ["磁盘文件存在 06-16kb-page-size.md 和 07-art-generational-gc.md"]
            },
            {
                "type": "版本差异缺失",
                "location": "导言段落",
                "detail": "导言未提及 MGLRU 和 16KB Page Size 等架构级演进",
                "suggestion": "在导言中点出底层架构演进对系统表现的重塑",
                "evidence": ["Android 14+ 默认启用 MGLRU (/sys/kernel/mm/lru_gen/)", "Android 15+ 强制 16KB Page Size 兼容性"]
            }
        ]
    },
    "4.5": {
        "priority": 85,
        "issues": [
            {
                "type": "原理描述不准",
                "location": "Hardware Bitmap 节",
                "detail": "称硬件 Bitmap 不计入 App PSS，但实际计入 Gfx dev/EGL mtrack 栏目",
                "suggestion": "明确 Hardware Bitmap 在 meminfo 中归属栏目 Gfx dev/EGL mtrack",
                "evidence": ["Hardware Bitmap 仍占进程 PSS 总量"]
            },
            {
                "type": "版本错误",
                "location": "heapprofd 节",
                "detail": "heapprofd --java 应为 Android 11+ 而非 Android 12+",
                "suggestion": "修正版本要求为 Android 11+",
                "evidence": ["Perfetto 官方文档和 AOSP 提交记录确认"]
            },
            {
                "type": "知识盲区",
                "location": "16KB 迁移小节",
                "detail": "缺少底层开发者核验手段 readelf 命令",
                "suggestion": "补充 readelf -l <so_file> | grep ALIGN 验证 0x4000 对齐",
                "evidence": []
            },
            {
                "type": "原理缺失",
                "location": "onTrimMemory 节",
                "detail": "缺失 App 主动查询内存压力的 ActivityManager.getMyMemoryState 机制",
                "suggestion": "补充 getMyMemoryState 作为主动防御手段",
                "evidence": ["ActivityManager.getMyMemoryState(RunningAppProcessInfo)"]
            }
        ]
    },
    "4.6": {
        "priority": 85,
        "issues": [
            {
                "type": "知识盲区",
                "location": "Native 代码小节",
                "detail": "只提及 C/C++ sysconf，未提及 Java 层 Os.sysconf 获取 Page Size",
                "suggestion": "补充 Java/Kotlin 层 Os.sysconf(OsConstants._SC_PAGESIZE) API 范例",
                "evidence": ["libcore/luni/src/main/native/libcore_io_Linux.cpp"]
            },
            {
                "type": "知识盲区",
                "location": "核心机制",
                "detail": "未提及 Bionic Linker 兼容模式 (Compat Mode)",
                "suggestion": "增加 Bionic 如何处理旧应用的短段落",
                "evidence": ["bionic/linker/linker.cpp 中 bionic.linker.16kb.app_compat.enabled"]
            }
        ]
    },
    "4.7": {
        "priority": 85,
        "issues": [
            {
                "type": "版本差异",
                "location": "版本演进表格",
                "detail": "分代 CMC 起始版本应为 Android 14 而非 15",
                "suggestion": "修正表格：Android 14 引入框架，Android 17 工程化增强",
                "evidence": ["art/runtime/gc/collector/mark_compact.h (Android 14 tag)"]
            },
            {
                "type": "原理缺失",
                "location": "Android 17 分代 GC 内部实现",
                "detail": "缺少 Sticky-bit 标记机制解释",
                "suggestion": "补充 CMC 如何利用对象头标志位实现 Sticky-bit 收集",
                "evidence": ["art/runtime/gc/collector/mark_compact.cc minor_gc 逻辑"]
            }
        ]
    },
    "5.0": {
        "priority": 85,
        "issues": [
            {
                "type": "交叉引用缺失",
                "location": "本章内容",
                "detail": "目录列表仅包含 5.1-5.7，遗漏 5.8-5.12 近 40% 章节",
                "suggestion": "按 SUMMARY.md 补全目录，重写阅读建议覆盖全章",
                "evidence": ["核对 SUMMARY.md 和 ls 结果确认缺失 5.8-5.12"]
            },
            {
                "type": "原理断裂",
                "location": "引言部分",
                "detail": "缺乏对 Kernel 与 Framework 交互机制（EAS/PowerHAL/ADPF）的顶层概括",
                "suggestion": "增加从 Kernel EAS 到 Framework Power/Thermal 到 App ADPF 的全链路导引",
                "evidence": ["kernel/sched/fair.c", "PowerManagerService", "hardware/interfaces/power/"]
            }
        ]
    },
    "5.1": {
        "priority": 85,
        "issues": [
            {
                "type": "源码逻辑不准",
                "location": "红黑树调度队列描述",
                "detail": "混淆 CFS(取最左节点) 与 EEVDF(基于 deadline 树搜索) 选人机制",
                "suggestion": "补充 EEVDF 增强红黑树的搜索逻辑，说明 entity_eligible 和 deadline 机制",
                "evidence": ["kernel/sched/fair.c pick_eevdf() (Linux 6.6+)"]
            },
            {
                "type": "版本差异缺失",
                "location": "Bionic API 37 变更",
                "detail": "未明确 sched_setattr 包装器在 API 37 引入",
                "suggestion": "标注 API 37 版本分界点，区分系统调用、EEVDF、Bionic 包装函数",
                "evidence": ["Bionic libc/include/sched.h __INTRODUCED_IN(37)"]
            }
        ]
    },
    "5.2": {
        "priority": 85,
        "issues": [
            {
                "type": "原理缺失",
                "location": "EAS 的前提条件",
                "detail": "未明确 EAS 仅作用于 CFS 调度类任务，RT/DL 不受节能逻辑约束",
                "suggestion": "补充说明 EAS 管辖范围限于 Fair 任务，RT 任务会干扰 EAS 能效预测",
                "evidence": ["kernel/sched/fair.c find_energy_efficient_cpu 仅在 select_task_rq_fair 中调用"]
            }
        ]
    },
    "5.3": {
        "priority": 85,
        "issues": [
            {
                "type": "源码错误",
                "location": "schedutil 工作流程源码片段",
                "detail": "effective_cpu_util 签名与 Linux 6.6 不符，使用的是 6.1 旧签名",
                "suggestion": "更新源码至 6.6 版本，说明参数从 type/p 变为 min/max 的变化",
                "evidence": ["kernel/sched/fair.c (Linux 6.6.89+)"]
            },
            {
                "type": "原理描述偏差",
                "location": "RTG (Related Thread Group) 机制描述",
                "detail": "RTG 实为高通 WALT 私有实现，描述为 Android 通用机制易误导",
                "suggestion": "明确标注 RTG 为高通平台定制机制，简述 GKI 时代 Vendor Hook 存在形式",
                "evidence": ["RTG 在 Pixel(Tensor) 设备上不存在"]
            }
        ]
    },
    "5.4": {
        "priority": 95,
        "issues": [
            {
                "type": "源码错误(P0)",
                "location": "schedutil 频率计算",
                "detail": "公式忽略 uclamp 钳位和 iowait boost，实际有效利用率由三者竞争产生",
                "suggestion": "更新为有效利用率概念：PELT + uclamp + iowait_boost",
                "evidence": ["kernel/sched/cpufreq_schedutil.c sugov_get_util()"]
            },
            {
                "type": "版本差异缺失",
                "location": "ADPF 介绍",
                "detail": "仅覆盖 Android 12 CPU，遗漏 Android 15/16 GPU 支持",
                "suggestion": "补充 GPU WorkDuration 和 GpuHeadroom API",
                "evidence": ["Android 15 WorkDuration 类", "Android 16 GpuHeadroom API"]
            },
            {
                "type": "架构缺失",
                "location": "OPP Table 章节",
                "detail": "缺失 SCMI/CPPC 现代架构说明，OS 不再直接请求频率而是请求性能等级",
                "suggestion": "增加抽象性能等级概念，说明 OPP 正从 OS 下沉到固件",
                "evidence": ["ARMv8.4+ SCMI Fastchannels 实现"]
            }
        ]
    },
    "5.8": {
        "priority": 95,
        "issues": [
            {
                "type": "源码错误(P0)",
                "location": "参考资料/正文",
                "detail": "DeviceIdleController、AppStandbyController、JobSchedulerService 路径错误",
                "suggestion": "修正为 services/core 和 services/usage 下的准确路径",
                "evidence": ["frameworks/base/services/core/java/com/android/server/DeviceIdleController.java"]
            },
            {
                "type": "API 存疑(P0)",
                "location": "11.2 节",
                "detail": "getPendingJobReasonStats(int) 未在 AOSP 中发现，实际应为 getPendingJobReasons",
                "suggestion": "确认 API 存在性，若无则删除",
                "evidence": ["Android 16 API 实际为 getPendingJobReasons 和 getPendingJobReasonsHistory"]
            },
            {
                "type": "知识盲区",
                "location": "Android 16 机制",
                "detail": "Freezer 10s Debounce 和 FrozenStateChangeCallback 缺失",
                "suggestion": "补齐系统层冻结逻辑",
                "evidence": ["CachedAppOptimizer 10 秒去抖动", "Binder FrozenStateChangeCallback"]
            }
        ]
    },
    "5.9": {
        "priority": 85,
        "issues": [
            {
                "type": "代码示例缺失",
                "location": "Android 15 WorkDuration",
                "detail": "提到 GPU 时长上报但代码示例仍使用旧 reportActualWorkDuration(long) 接口",
                "suggestion": "增加 WorkDuration 类 Java 代码示范",
                "evidence": ["frameworks/base/core/java/android/os/WorkDuration.java (API 35)"]
            },
            {
                "type": "API 文档缺失",
                "location": "SystemHealthManager",
                "detail": "getCpuHeadroom 返回值 [0,100] 刻度未说明",
                "suggestion": "明确标注 [0, 100] 取值范围及 Float.NaN 处理",
                "evidence": ["android.os.health.SystemHealthManager#getCpuHeadroom"]
            }
        ]
    },
    "5.10": {
        "priority": 85,
        "issues": [
            {
                "type": "原理缺失",
                "location": "UIDT Job 描述",
                "detail": "未强调不调用 setNotification 会导致 Job 被系统强杀",
                "suggestion": "增加警告：不调用 setNotification 的运行时崩溃风险",
                "evidence": ["JobServiceContext.java 中 setNotification 状态检查"]
            },
            {
                "type": "版本差异缺失",
                "location": "合规方案/版本差异",
                "detail": "未提及 Android 15 FGS dataSync/mediaProcessing 6h/24h 配额",
                "suggestion": "补充 FGS 时长配额对长任务选型的决定性影响",
                "evidence": ["Android 15 FGS Hardening"]
            }
        ]
    },
    "5.11": {
        "priority": 85,
        "issues": [
            {
                "type": "架构缺失",
                "location": "LiteRT 管线",
                "detail": "仅描述 Interpreter+Delegate V1 架构，遗漏 CompiledModel V2 API",
                "suggestion": "补充 CompiledModel API，对比与传统 Interpreter+Delegate 的区别",
                "evidence": ["com.google.ai.edge.litert.CompiledModel"]
            },
            {
                "type": "知识盲区",
                "location": "模型优化技术",
                "detail": "未提 AOT 编译机制，NPU 加载成本常达 500ms+",
                "suggestion": "增加推理冷启动优化：从 JIT 到 AOT 小节",
                "evidence": ["CompiledModel 支持安装时预编译为 Vendor-specific Binary"]
            }
        ]
    },
    "5.12": {
        "priority": 85,
        "issues": [
            {
                "type": "API 文档补强",
                "location": "ADPF Headroom",
                "detail": "getCpuHeadroom 返回值量纲需明确说明受 Throttling 影响",
                "suggestion": "补充 Headroom 计算公式说明",
                "evidence": ["Android 16 API 36 预览版文档"]
            },
            {
                "type": "Perfetto 实战",
                "location": "Perfetto SQL",
                "detail": "部分 OEM 平台 thermal_zone track_id 可能因传感器离线偏移",
                "suggestion": "增加先确认轨道 ID 的 SQL 说明",
                "evidence": []
            }
        ]
    },
    "6.0": {
        "priority": 85,
        "issues": [
            {
                "type": "交叉引用缺失",
                "location": "本章内容",
                "detail": "遗漏 6.4(版本演进) 和 6.5(SP/DataStore) 章节索引",
                "suggestion": "补齐清单，特别是 6.5 是解决 SP ANR 最实用章节",
                "evidence": ["核对 src/part1-fundamentals/ch06-storage/ 目录确认文件存在"]
            },
            {
                "type": "引导缺失",
                "location": "阅读建议",
                "detail": "未针对主线程卡顿场景指引至 6.5",
                "suggestion": "增加 SP 引起 ANR/启动卡顿请参考 6.5 的导引",
                "evidence": []
            }
        ]
    },
    "6.1": {
        "priority": 85,
        "issues": [
            {
                "type": "原理缺失",
                "location": "Virtual A/B snapuserd",
                "detail": "仅提到写入放大，遗漏最重要的上下文切换延迟",
                "suggestion": "明确 snapuserd 内核/用户态通信开销，对比 io_uring 优化效果",
                "evidence": ["system/core/fs_mgr/libsnapshot/snapuserd 实现"]
            }
        ]
    },
    "6.2": {
        "priority": 95,
        "issues": [
            {
                "type": "事实错误(P0)",
                "location": "EROFS 段落",
                "detail": "称 Android 13 强制所有只读分区使用 EROFS，实为 CDD 强制内核支持",
                "suggestion": "修正为内核强制支持 EROFS，GMS/VTS 推动为事实标准",
                "evidence": ["Android 13 CDD 7.6.1 要求内核支持 EROFS"]
            },
            {
                "type": "版本差异(P0)",
                "location": "Android 15 部分",
                "detail": "16KB 页下 f2fs 无法挂载 4KB 镜像，必须重新格式化 /data",
                "suggestion": "增加 16KB 页面下文件系统约束专项说明",
                "evidence": ["f2fs block_size 必须等于 Page Size"]
            },
            {
                "type": "架构缺失",
                "location": "全文",
                "detail": "完全缺失 Project Quota、Casefolding、fscrypt/Inline Encryption 三大特性",
                "suggestion": "补充存储配额、大小写折叠、内联加密章节",
                "evidence": ["kernel/common/fs/f2fs/node.c", "f2fs/dir.c", "fs/crypto/"]
            }
        ]
    },
    "6.4": {
        "priority": 85,
        "issues": [
            {
                "type": "知识补强",
                "location": "sLoadExecutor 描述",
                "detail": "未强调全进程唯一单线程池导致的级联效应",
                "suggestion": "明确多 SP 文件全局串行化，小文件被大文件卡住的风险",
                "evidence": ["AOSP Android 15+ sLoadExecutor 为静态单线程池"]
            }
        ]
    },
    "6.5": {
        "priority": 85,
        "issues": [
            {
                "type": "源码缺失",
                "location": "FUSE 回归部分",
                "detail": "未点出 MediaProvider 进程中 FuseDaemon.cpp 的核心角色",
                "suggestion": "明确 MediaProvider 即 FUSE 进程，实现文件操作与媒体数据库原子同步",
                "evidence": ["packages/providers/MediaProvider/jni/FuseDaemon.cpp"]
            },
            {
                "type": "版本差异缺失",
                "location": "版本演进表格",
                "detail": "仅覆盖到 Android 14，遗漏 15 的 16KB Page Size 和 Storage Health API",
                "suggestion": "增加 Android 15 行，强调 16KB 对齐对 NDK 和底层驱动影响",
                "evidence": ["StorageManager 扩展 API"]
            },
            {
                "type": "实战缺失",
                "location": "UFS 4.0 MCQ",
                "detail": "未给出确认 MCQ 激活状态的 sysfs 方法",
                "suggestion": "增加 /sys/devices/platform/soc/*.ufshc/mcq_active 检查命令",
                "evidence": []
            }
        ]
    },
    "7.2": {
        "priority": 85,
        "issues": [
            {
                "type": "源码准确性",
                "location": "Binder 线程池描述",
                "detail": "默认线程数描述模糊，应为 15 worker + 1 main = 16",
                "suggestion": "明确 15+1 结构，补充 system_server 可调至 31+",
                "evidence": ["DEFAULT_MAX_BINDER_THREADS = 15"]
            },
            {
                "type": "知识盲区",
                "location": "分析树 JankType",
                "detail": "缺失 SurfaceFlingerGpuDeadlineMissed 归因",
                "suggestion": "补充该 JankType：SF CPU 任务完成但 GPU 合成超时",
                "evidence": ["Android 12+ FrameTimeline 核心归因之一"]
            }
        ]
    },
    "7.3": {
        "priority": 85,
        "issues": [
            {
                "type": "版本差异缺失",
                "location": "FrameTimeline SurfaceView",
                "detail": "称 FrameTimeline 不覆盖 SurfaceView，但 Android 15 已引入支持",
                "suggestion": "说明 12-14 局限性并给出 15+ 的 SurfaceControl.Transaction.setFrameTimelineVsyncId 方案",
                "evidence": ["Android 15 API 35 SurfaceControl.Transaction"]
            },
            {
                "type": "版本差异缺失",
                "location": "SF Trace Marker",
                "detail": "引用 onMessageReceived，但 Android 11+ 已拆分为 onMessageInvalidate/onMessageRefresh",
                "suggestion": "增加版本说明，提示读者在 11+ Trace 中寻找 onMessageInvalidate",
                "evidence": ["SurfaceFlinger MessageQueue 分发 INVALIDATE/REFRESH"]
            }
        ]
    },
    "7.4": {
        "priority": 85,
        "issues": [
            {
                "type": "架构演进",
                "location": "3.1 App 启动窗口",
                "detail": "Android 12+ SplashScreen 绘制已从 SystemServer 移至 Shell 进程",
                "suggestion": "区分决策层(ATMS)与绘制层(Shell)，解释 SystemUI 负载影响",
                "evidence": ["StartingWindowController.java in WindowManager/Shell"]
            },
            {
                "type": "知识闭环",
                "location": "setHasFixedSize",
                "detail": "核心作用是跳过容器 requestLayout 而非阻止子 View 内部刷新",
                "suggestion": "明确解决的是列表内容增减导致的容器重测开销",
                "evidence": []
            }
        ]
    },
    "7.6": {
        "priority": 85,
        "issues": [
            {
                "type": "原理缺失",
                "location": "Case 4 RenderThread sync",
                "detail": "遗漏 DrawFrameTask syncFrameState 后的提前唤醒 unblockUiThread 机制",
                "suggestion": "区分同步等待与渲染等待，说明哪些操作会延长阻塞",
                "evidence": ["DrawFrameTask.cpp syncFrameState -> unblockUiThread"]
            },
            {
                "type": "版本差异缺失",
                "location": "Case 5 内存回调",
                "detail": "Android 14 缓存应用冻结导致 onTrimMemory 失效未解释原因",
                "suggestion": "补充 Cached App Freezer 背景，强调向降低常驻内存转型",
                "evidence": ["Android 14 Cached App Freezer 机制"]
            },
            {
                "type": "知识盲区",
                "location": "Case 5 低内存",
                "detail": "缺失 MGLRU (CONFIG_LRU_GEN) 内核级优化方案",
                "suggestion": "将 MGLRU 作为系统开发者视角首选推荐",
                "evidence": ["Android 13+ MGLRU 降低 kswapd CPU ~40%"]
            }
        ]
    },
    "7.7": {
        "priority": 85,
        "issues": [
            {
                "type": "原理缺失",
                "location": "Strong Skipping 章节",
                "detail": "未指明不稳定参数使用 === 引用相等性比较",
                "suggestion": "对比稳定参数 equals() 与不稳定参数 === 的差异",
                "evidence": ["Strong Skipping Mode - developer.android.com"]
            },
            {
                "type": "实战缺失",
                "location": "Perfetto 章节",
                "detail": "缺少手动激活 Trace 的 adb broadcast 指令",
                "suggestion": "添加 am broadcast -a androidx.tracing.perfetto.action.ENABLE_TRACING 激活命令",
                "evidence": ["androidx.tracing.perfetto.TracingReceiver"]
            },
            {
                "type": "知识盲区",
                "location": "重组机制",
                "detail": "未提及 inline Composable 不产生独立重组范围(startReplaceableGroup)",
                "suggestion": "补充 Row/Column/Box 寄生在调用者重组作用域中的机制",
                "evidence": ["inline 函数生成 startReplaceableGroup 而非 startRestartGroup"]
            }
        ]
    },
    "7.8": {
        "priority": 85,
        "issues": [
            {
                "type": "API 差异",
                "location": "嵌套滑动章节",
                "detail": "setRecycleChildrenOnDetach(true) 不适用于 StaggeredGridLayoutManager",
                "suggestion": "明确标注仅适用于 LinearLayoutManager 系，瀑布流需手动处理",
                "evidence": ["StaggeredGridLayoutManager 不继承 LinearLayoutManager"]
            }
        ]
    },
}

# Research gaps: section_key -> [{description, importance, direction, related_sections}]
GAPS_DATA = {
    "4.0": [
        {"description": "16KB Page Size 对现有三方库的破坏性影响评估", "importance": "高", "direction": "整理受影响常见三方库清单", "related": "4.6"},
        {"description": "MGLRU 运行时监控方法", "importance": "中", "direction": "通过 sysfs 接口观察多代 LRU 实际回收效率", "related": "4.0"},
        {"description": "MTE 硬件级防御机制细节", "importance": "中", "direction": "硬件 Tag 与物理内存 1/32 映射关系及性能代价", "related": "4.15"},
    ],
    "4.5": [
        {"description": "dmabuf 追踪", "importance": "中", "direction": "Perfetto 中 dmabuf track 如何反映 GPU 内存分配", "related": "4.5"},
        {"description": "ActivityManager.getMyMemoryState 性能开销", "importance": "中", "direction": "主动获取 trimLevel 的性能开销与适用场景", "related": "4.5"},
        {"description": "16KB 对齐下内存浪费量化", "importance": "低", "direction": "大量小图场景内部碎片增量估算", "related": "4.5, 4.6"},
    ],
    "4.6": [
        {"description": "Bionic Linker 16KB Compat Mode 内存重映射逻辑", "importance": "高", "direction": "阅读 bionic/linker/linker.cpp 中 Linker 类对页大小对齐失败的处理", "related": "4.6"},
        {"description": "RELRO 填充 Bug 对 16KB 系统的影响", "importance": "中", "direction": "研究旧版 lld 链接器产生的 RELRO 对齐错误", "related": "4.6"},
    ],
    "4.7": [
        {"description": "userfaultfd 在 CMC 中的页错误开销", "importance": "中", "direction": "深入研究 SIGBUS 处理器在 CMC 中的性能损耗", "related": "4.7"},
        {"description": "mid_generation 具体晋升阈值", "importance": "高", "direction": "确认是否硬编码为 1 次或存在动态调整逻辑", "related": "4.7"},
        {"description": "Android 17 DeliQueue 与 GC 优化协同", "importance": "中", "direction": "ART 调度器如何利用 DeliQueue 规避 GC 高峰", "related": "4.7"},
    ],
    "5.0": [
        {"description": "ADPF (Adaptive Performance Framework) 架构", "importance": "高", "direction": "PerformanceHintManager 如何通过 PowerHAL 影响 CPU 频率", "related": "5.9"},
        {"description": "UClamp (Utilization Clamping) 应用逻辑", "importance": "中", "direction": "Android 12+ 如何使用 uclamp 替代 SchedTune", "related": "5.2"},
        {"description": "WALT vs PELT 负载追踪差异", "importance": "中", "direction": "高通平台 WALT 与 AOSP 标准 PELT 的差异", "related": "5.1"},
    ],
    "5.1": [
        {"description": "EEVDF lag 衰减细节", "importance": "中", "direction": "reweight_entity 逻辑如何防止任务通过睡眠重置 lag", "related": "5.1"},
        {"description": "Android 16 调度新特性", "importance": "高", "direction": "API 36/37 是否引入针对 EEVDF 的专门 NDK 接口", "related": "5.1"},
    ],
    "5.2": [
        {"description": "CPU 唤醒成本 (Waking vs Using already awake CPU)", "importance": "中", "direction": "find_energy_efficient_cpu 是否考虑唤醒 Deep Idle CPU 的静态能量开销", "related": "5.2"},
        {"description": "厂商自定义 Boost Hook", "importance": "高", "direction": "高通 sched_boost 标志位如何强制绕过 EAS 逻辑", "related": "5.2, 5.3"},
    ],
    "5.3": [
        {"description": "EEVDF 调度器对调频的影响", "importance": "中", "direction": "Linux 6.6 EEVDF 后 util 信号平滑处理变化", "related": "5.3"},
        {"description": "ADPF 与大小核联动", "importance": "高", "direction": "ADPF 如何影响任务在超大核上的停留时间", "related": "5.3, 5.9"},
    ],
    "5.4": [
        {"description": "uclamp_min 对启动耗时的影响", "importance": "高", "direction": "Android Framework 如何通过 CPUSet/CGroup 设置 uclamp_min", "related": "5.4"},
        {"description": "SCMI Fastchannels", "importance": "中", "direction": "ARM 官方 SCMI 规范 MMIO 调频通道", "related": "5.4"},
    ],
    "5.8": [
        {"description": "Binder Freezer Driver 协同机制", "importance": "高", "direction": "FrozenStateChangeCallback 在 AOSP 中的具体应用场景", "related": "5.8"},
        {"description": "Android 16 UIDT 额度详情", "importance": "中", "direction": "UIDT 是否受 App Standby Bucket 进一步限制", "related": "5.8, 5.10"},
    ],
    "5.9": [
        {"description": "GPU 目标设定的 WorkDuration 分拆版本", "importance": "中", "direction": "updateTargetWorkDuration 是否也有类似 WorkDuration 的分拆", "related": "5.9"},
        {"description": "ADPF 非游戏场景策略", "importance": "高", "direction": "ProfilingManager TRIGGER_TYPE_ANOMALY 如何利用 ADPF 信号", "related": "5.9, 5.11"},
    ],
    "5.10": [
        {"description": "updateEstimatedNetworkBytes API", "importance": "中", "direction": "Android 14+ 估算带宽 API 对调度优先级的影响", "related": "5.10"},
        {"description": "TRANSFER_THROUGHPUT_UTILIZATION", "importance": "中", "direction": "Android 16+ 对大文件传输 job 的吞吐量监测逻辑", "related": "5.10"},
    ],
    "5.11": [
        {"description": "PODAI (Play for On-device AI) 动态分发", "importance": "高", "direction": "通过 Play Services 动态分发 NPU 加速库解决 APK 体积", "related": "5.11"},
        {"description": "零拷贝 TensorBuffer", "importance": "中", "direction": "HardwareBuffer 与 LiteRT NPU 直接内存共享", "related": "5.11"},
    ],
    "5.12": [
        {"description": "皮肤温度估算模型 (Thermal Model)", "importance": "中", "direction": "OEM 如何利用 power_allocator tzp 在 sysfs 中暴露物理参数", "related": "5.12"},
        {"description": "Android 16 NDK AThermal_getThermalHeadroomThresholds", "importance": "高", "direction": "原生代码直接获取 Throttling 状态切换精确数值", "related": "5.12"},
    ],
    "6.0": [
        {"description": "16KB Page Size 对底层存储性能的变革", "importance": "中", "direction": "结合 Android 15 行为变更，评估对 I/O 吞吐量的影响", "related": "6.0, 4.7"},
    ],
    "6.1": [
        {"description": "F2FS 前台 GC 触发水位线", "importance": "中", "direction": "研究 f2fs/segment.c 中 has_not_enough_free_secs 逻辑", "related": "6.1"},
        {"description": "Metadata Encryption Inline Crypto 映射", "importance": "中", "direction": "blk-crypto 如何在不同 SoC 上落地", "related": "6.1"},
    ],
    "6.2": [
        {"description": "Project Quota (存储配额) 工作原理", "importance": "高", "direction": "内核 PRID 映射与 StorageStatsService 交互", "related": "6.2"},
        {"description": "Casefolding (大小写折叠) 性能影响", "importance": "高", "direction": "Unicode 折叠算法在内核层的性能影响", "related": "6.2"},
        {"description": "Inline Encryption (fscrypt) 与 UFS Keyslot", "importance": "高", "direction": "blk-crypto 与 UFS Keyslot 管理", "related": "6.2"},
    ],
    "6.4": [
        {"description": "16KB Page Size 对 I/O 密集型存储的影响", "importance": "中", "direction": "Android 15 强制 16KB 页对 XML 解析和文件落盘的性能提升", "related": "6.4, 4.7"},
        {"description": "MultiProcessDataStoreFactory 锁机制", "importance": "中", "direction": "核实基于 FileLock 的实现及极端竞争下性能", "related": "6.4"},
    ],
    "6.5": [
        {"description": "16KB 页对 F2FS 挂载参数的影响", "importance": "高", "direction": "Android 15 16KB 模式下 F2FS block_size 限制", "related": "6.5, 4.7"},
        {"description": "MediaProvider 位置脱敏 (Redaction) 对 FUSE 读延迟的量化影响", "importance": "中", "direction": "对比有/无位置信息照片的 CPU 周期消耗", "related": "6.5"},
    ],
    "7.2": [
        {"description": "Android 17 Generational GC STW 表现", "importance": "高", "direction": "验证 ART Mainline 演进对 UI 线程暂停时间的实际压制效果", "related": "7.2, 4.8"},
        {"description": "SkiaVulkan 在 RenderThread 的 Trace 表现", "importance": "中", "direction": "Android 15 默认 SkiaVulkan 的 drawOp 细分 Slice 差异", "related": "7.2"},
    ],
    "7.3": [
        {"description": "Android 16 AppJankStats 监控新范式", "importance": "中", "direction": "调研 android.app.jank 软件包", "related": "7.3"},
        {"description": "ADPF 与 FrameTimeline 反馈闭环", "importance": "高", "direction": "ADPF 如何根据 FrameTimeline Expected Deadline 动态调整 CPU 频率", "related": "7.3, 5.9"},
    ],
    "7.6": [
        {"description": "Cached App Freezer 完整机制", "importance": "高", "direction": "Android 14+ 后台进程管理策略详解", "related": "7.6, 5.8"},
        {"description": "MGLRU vs 传统双级 LRU 锁竞争差异", "importance": "中", "direction": "对比 pgdat->lru_lock 竞争解决效果", "related": "7.6, 4.0"},
    ],
    "7.7": [
        {"description": "Inline Composable 重组穿透机制", "importance": "高", "direction": "startReplaceableGroup vs startRestartGroup IR 转换差异", "related": "7.7"},
        {"description": "SlotTable Gap Buffer 机制", "importance": "中", "direction": "SlotTable.kt insert/move 操作对性能的实际影响", "related": "7.7"},
    ],
    "7.8": [
        {"description": "hasTransientState 导致的 ViewHolder 回收阻断", "importance": "中", "direction": "哪些三方动画库会意外触发该状态导致 RV 缓存失效", "related": "7.8"},
    ],
}

# Suggestions: section_key -> [{type, location, problem, suggestion}]
SUGGESTIONS_DATA = {
    "4.0": [
        {"type": "阅读建议", "location": "阅读建议段落", "problem": "未提及 Native 内存安全", "suggestion": "增加对 MTE 和 16KB 适配的推荐链接"},
    ],
    "4.5": [
        {"type": "数据支撑", "location": "120Hz 掉帧计算", "problem": "描述精彩但可更量化", "suggestion": "给出公式示例: Vsync(8.33ms) < UI Work(4ms) + GC Pause(5ms) = Frame Drop"},
        {"type": "源码准确性", "location": "Bitmap.java 路径", "problem": "路径对应旧分支", "suggestion": "标注此路径对应 AOSP 现代版本 android-15.0.0_r1+"},
    ],
    "4.6": [
        {"type": "内容优化", "location": "构建工具链要求", "problem": "AGP 8.5 描述冗长", "suggestion": "直接强调 AGP 8.5.1+ 是修复 bundletool 16KB 对齐 Bug 的关键版本"},
    ],
    "4.7": [
        {"type": "Perfetto 优化", "location": "SQL 示例", "problem": "使用 process_name 较慢", "suggestion": "推荐使用 upid 替代 process_name 以利用索引"},
    ],
    "5.0": [
        {"type": "阅读建议", "location": "阅读建议", "problem": "未区分内核开发与应用优化", "suggestion": "App 开发者关注 5.8/5.9/5.10，系统工程师关注 5.1-5.5"},
    ],
    "5.1": [
        {"type": "Perfetto SQL", "location": "EEVDF 排队", "problem": "缺少前瞻性 SQL", "suggestion": "增加识别 EEVDF Lag 限制导致排队的示例 SQL"},
    ],
    "5.2": [
        {"type": "源码更新", "location": "能量模型函数名", "problem": "em_pd_energy 为旧名", "suggestion": "补充 v5.10+ 更名为 em_cpu_energy"},
        {"type": "版本差异", "location": "Cgroup V2 状态", "problem": "CPU 控制器状态未说明", "suggestion": "补充 Android 12 CPU 控制器仍保留在 Cgroup V1"},
    ],
    "5.3": [
        {"type": "数学描述", "location": "PELT 32ms", "problem": "32ms = 1024us × 32 不严谨", "suggestion": "修正为半衰期约 32ms，负载每 1024us 更新一次"},
        {"type": "公式优化", "location": "schedutil 公式", "problem": "过于理想化", "suggestion": "体现 1.25 SCHED_CAPACITY_SCALE 裕量概念"},
    ],
    "5.4": [
        {"type": "延迟构成", "location": "升频延迟", "problem": "200ms 延迟未拆解", "suggestion": "区分硬件物理切换(us 级)与 PELT 衰减惯性(32-64ms)"},
    ],
    "5.8": [
        {"type": "数据支撑", "location": "App Standby", "problem": "Active 桶限额背景缺失", "suggestion": "补充 Android 16 Active 桶引入限额背景"},
        {"type": "交叉引用", "location": "后台执行对前台性能", "problem": "未引用 LMK", "suggestion": "显式引用 4.4 节关于 LMK 的描述"},
    ],
    "5.9": [
        {"type": "版本差异", "location": "Thermal API", "problem": "仅描述 NDK 监听器", "suggestion": "补充 Android 16 Java 层预测回调 forecastHeadroom"},
        {"type": "版本差异", "location": "版本演进表", "problem": "Android 17 为[待验证]", "suggestion": "填充 ADPF 扩展至非游戏场景内容"},
    ],
    "5.10": [
        {"type": "源码准确性", "location": "JobScheduler 内部架构", "problem": "assignJobToContext 应为 assignJobsToContextsLocked", "suggestion": "修正方法名"},
        {"type": "边界说明", "location": "WorkManager 持久化", "problem": "未提强制停止后的行为", "suggestion": "补充 Force Stop 后 WorkManager 也不执行"},
    ],
    "5.11": [
        {"type": "版本差异", "location": "GPU Delegate", "problem": "未提 Android 15 优化", "suggestion": "标注 LiteRT GPU Delegate 在 Android 15 通过 OpenCL 优化实现 1.4x 提速"},
    ],
    "5.12": [
        {"type": "最佳实践", "location": "getThermalHeadroom", "problem": "调用频率无建议", "suggestion": "建议每秒调用不超过 1 次，避免 Binder 开销"},
    ],
    "6.0": [
        {"type": "引导优化", "location": "阅读建议", "problem": "弱化了 6.1 硬件基线重要性", "suggestion": "平衡 6.1 与 6.2/6.3 阅读推荐权重"},
    ],
    "6.1": [
        {"type": "边界说明", "location": "FUSE Passthrough", "problem": "未强调元数据操作无效", "suggestion": "补充 open/create/readdir 仍由 MediaProvider 处理"},
    ],
    "6.2": [
        {"type": "源码补强", "location": "SQLite 原子写", "problem": "只提 START ioctl", "suggestion": "补充 COMMIT 和 ABORT ioctl 完整闭环"},
    ],
    "6.4": [
        {"type": "实战建议", "location": "sLoadExecutor", "problem": "级联效应警示不足", "suggestion": "明确多 SP 文件全局串行化风险"},
        {"type": "版本差异", "location": "MMKV vs DataStore", "problem": "未提 16KB 适配差异", "suggestion": "MMKV mmap 在 16KB 页设备需 native 适配"},
    ],
    "6.5": [
        {"type": "版本门槛", "location": "FUSE Passthrough", "problem": "未标注内核门槛", "suggestion": "补充需要 Kernel 5.4+ 且 CONFIG_FUSE_PASSTHROUGH=y"},
    ],
    "7.2": [
        {"type": "背景说明", "location": "华为 VSync 异常", "problem": "描述为错误注入", "suggestion": "补充 OEM 功耗平衡 Smart Refresh Rate 策略背景"},
    ],
    "7.3": [
        {"type": "实战价值", "location": "doFrame 回调", "problem": "未说明 CALLBACK_INSETS_ANIMATION", "suggestion": "补充 IME 弹出分析价值"},
        {"type": "SQL 精度", "location": "抢占分析", "problem": "未区分 R+ 和 R", "suggestion": "区分 Preempted (R+) 和 Runnable (R)"},
    ],
    "7.4": [
        {"type": "源码准确性", "location": "TaskSnapshot", "problem": "未提及 HardwareBuffer", "suggestion": "明确 Android 8.0+ 使用 GraphicBuffer FD 零拷贝传递"},
    ],
    "7.6": [
        {"type": "数学解释", "location": "嵌套布局", "problem": "层级嵌套导致多次 measure 未量化", "suggestion": "补充指数级增长（乘法关系）说明"},
        {"type": "Binder 差异", "location": "onBindViewHolder", "problem": "未区分冷/热调用", "suggestion": "补充首次系统服务调用的权限校验开销"},
    ],
    "7.7": [
        {"type": "版本更新", "location": "ReuseComposeView", "problem": "标注为待验证", "suggestion": "Compose 1.8.0 稳定版已正式发布，直接更新"},
        {"type": "实现细节", "location": "ScopeUpdateScope", "problem": "未说明实际实现类", "suggestion": "明确实际实现类是 RecomposeScopeImpl"},
    ],
    "7.8": [
        {"type": "实战建议", "location": "hasTransientState", "problem": "未提及对回收影响", "suggestion": "补充非框架属性动画导致 hasTransientState=true 阻断回收"},
        {"type": "可视化", "location": "VSync 精度", "problem": "缺少像素偏移示例", "suggestion": "补充 120Hz 1ms 误差在 2000px/s 下对应 2 像素偏移"},
    ],
}

# ============================================================
# INTEGRATION LOGIC
# ============================================================

def load_queue():
    with open(QUEUE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_queue(data):
    with open(QUEUE_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_md(path):
    if path.exists():
        return path.read_text(encoding='utf-8')
    return ""

def save_md(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')

def section_exists_in_queue(queue, section_path):
    for entry in queue:
        if entry.get('section') == section_path:
            return entry
    return None

def integrate_queue(queue_data):
    queue = load_queue()
    new_count = 0
    merged_count = 0

    for sec_key, data in queue_data.items():
        section_path, section_title = SECTION_MAP[sec_key]
        priority = data["priority"]
        issues = data["issues"]

        existing = section_exists_in_queue(queue.get('queue', []), section_path)

        if existing and existing.get('added_by') == 'external-ai-review':
            # Merge: append new issues to existing review_issues
            existing_issues = existing.get('review_issues', [])
            for issue in issues:
                # Check for duplicate by detail text
                is_dup = any(ei.get('detail') == issue['detail'] for ei in existing_issues)
                if not is_dup:
                    existing_issues.append(issue)
            existing['review_issues'] = existing_issues
            # Update priority if higher
            if priority > existing.get('priority', 0):
                existing['priority'] = priority
            merged_count += 1
        else:
            # New entry
            entry = {
                "section": section_path,
                "section_title": section_title,
                "priority": priority,
                "reason": f"[External Review] 外部 review 结果整合 ({sec_key})",
                "review_issues": issues,
                "added_by": "external-ai-review",
                "added_at": TIMESTAMP,
                "status": "pending"
            }
            queue.setdefault('queue', []).append(entry)
            new_count += 1

    save_queue(queue)
    return new_count, merged_count

def integrate_gaps():
    existing = load_md(GAPS_PATH)
    new_entries = []

    for sec_key, gaps in GAPS_DATA.items():
        for gap in gaps:
            section_path, section_title = SECTION_MAP[sec_key]
            entry_text = f"## [{DATE}] {sec_key} {section_title} — 知识盲区\n\n"
            entry_text += f"### 盲区描述\n{gap['description']}\n\n"
            entry_text += f"### 重要程度\n{gap['importance']}\n\n"
            entry_text += f"### 建议研究方向\n{gap['direction']}\n\n"
            entry_text += f"### 关联章节\n{gap['related']}\n\n"
            entry_text += f"### 外部 review 来源\nGemini 外部 review ({sec_key})\n"

            # Simple dedup: check if description already exists
            if gap['description'] not in existing:
                new_entries.append(entry_text)

    if new_entries:
        separator = "\n---\n\n"
        if existing.strip():
            content = existing.rstrip() + "\n\n---\n\n" + "\n---\n\n".join(new_entries) + "\n"
        else:
            content = "# 知识盲区 / 后续研究项\n\n" + "\n---\n\n".join(new_entries) + "\n"
        save_md(GAPS_PATH, content)

    return len(new_entries)

def integrate_suggestions():
    existing = load_md(SUGGESTIONS_PATH)
    new_entries = []

    for sec_key, suggestions in SUGGESTIONS_DATA.items():
        section_path, section_title = SECTION_MAP[sec_key]
        for sug in suggestions:
            entry_text = f"## [External Review] {sec_key} {section_title} — {DATE}\n"
            entry_text += f"- **类型**：{sug['type']}\n"
            entry_text += f"- **位置**：{sug['location']}\n"
            entry_text += f"- **问题**：{sug['problem']}\n"
            entry_text += f"- **建议**：{sug['suggestion']}\n"
            entry_text += f"- **来源**：Gemini 外部 review ({sec_key})\n"

            # Dedup by problem+location
            dedup_key = f"{sug['problem']}|{sug['location']}"
            if dedup_key not in existing and sug['problem'] not in existing:
                new_entries.append(entry_text)

    if new_entries:
        separator = "\n---\n\n"
        if existing.strip():
            content = existing.rstrip() + "\n\n---\n\n" + "\n---\n\n".join(new_entries) + "\n"
        else:
            content = "# 一般修正建议\n\n" + "\n---\n\n".join(new_entries) + "\n"
        save_md(SUGGESTIONS_PATH, content)

    return len(new_entries)

def write_integration_log(new_queue, merged_queue, new_gaps, new_suggestions):
    INTEGRATION_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = INTEGRATION_LOG_DIR / f"{now.strftime('%Y-%m-%d-%H')}-integration.md"

    sections = sorted(SECTION_MAP.keys())
    log = f"# External Review Integration Log\n\n"
    log += f"- **时间**: {DATE} {TIME}\n"
    log += f"- **处理文件数**: 25\n"
    log += f"- **Queue 新增**: {new_queue}\n"
    log += f"- **Queue 合并**: {merged_queue}\n"
    log += f"- **Research gaps 新增**: {new_gaps}\n"
    log += f"- **Suggestions 新增**: {new_suggestions}\n\n"
    log += f"## 处理章节\n\n"
    for sec in sections:
        sp, st = SECTION_MAP[sec]
        log += f"- {sec} {st}\n"
    log += f"\n## 状态\n\n- 全部 25 个文件已完成整合\n- 可安全归档\n"

    save_md(log_path, log)
    return log_path

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=== Task 12: External Review Integration ===")
    print(f"Time: {DATE} {TIME}")

    print("\n[1/4] Integrating queue.json...")
    new_q, merged_q = integrate_queue(QUEUE_DATA)
    print(f"  New entries: {new_q}, Merged entries: {merged_q}")

    print("\n[2/4] Integrating research-gaps.md...")
    new_g = integrate_gaps()
    print(f"  New gaps: {new_g}")

    print("\n[3/4] Integrating suggestions.md...")
    new_s = integrate_suggestions()
    print(f"  New suggestions: {new_s}")

    print("\n[4/4] Writing integration log...")
    log_path = write_integration_log(new_q, merged_q, new_g, new_s)
    print(f"  Log: {log_path}")

    print("\n=== Integration Complete ===")
    print(f"Queue: {new_q} new + {merged_q} merged")
    print(f"Gaps: {new_g} new")
    print(f"Suggestions: {new_s} new")
    print(f"Total sections: 25")
