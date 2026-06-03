# Task 9 Suggestions - 2026-06-03 07:20

## Blocked by Task2B Verifier (2026-06-03)

### Task2B 阻塞章节

**09-finalizer-referencequeue.md**
- **Issue**: Task9 标记 needs-rework 但 queue 中无对应条目
- **Current**: pipeline_stage=task6_pending, task9_result=needs-rework
- **Status**: blocked-need-rework-evidence
- **Action**: 待 Task2B 处理返工需求

**27-apm-client-architecture.md**
- **Issue**: Task9 标记 needs-rework 但 queue 中无对应条目
- **Current**: pipeline_stage=task6_pending, task9_result=needs-rework
- **Status**: blocked-need-rework-evidence
- **Action**: 待 Task2B 处理返工需求

## P0 Priority Suggestions

### Measure (19.09)
**SUGG-MEASURE-P0-001**
- **Issue**: Native crash capability incorrectly described as supported
- **Current**: "包含 native crash reporting" 
- **Fix**: "当前 Android native crash reporting 尚未完全支持，仅支持 Java/Kotlin crash"
- **Impact**: Critical - prevents misinformation about capability boundaries

### Measure (19.09)
**SUGG-MEASURE-P0-002** 
- **Issue**: ANR boundary description incomplete
- **Current**: Only mentions "API 10 以下没有 ApplicationExitInfo"
- **Fix**: Supplement with "Android 10-11 仅有 ApplicationExitInfo 但无完整 ANR 支持直到 API 31+"
- **Impact**: Critical - clarifies version support timeline

### Measure (19.09)
**SUGG-MEASURE-P0-003**
- **Issue**: HTTP body configuration not properly explained
- **Current**: Claims "默认不采集 body" but doesn't explain configuration
- **Fix**: Add explicit configuration parameters and enablement conditions
- **Impact**: Medium - affects data collection accuracy

### Measure (19.09)
**SUGG-MEASURE-P0-004**
- **Issue**: Retention endpoint path clarification needed
- **Current**: "GET/PATCH /apps/:id/retention is针对的是 apps，不是全局配置"
- **Fix**: Clarify API scope and parameter structure
- **Impact**: Medium - affects API usage understanding

## P1 Priority Suggestions

### 崩溃与 ANR 捕获机制 (19.24)
**SUGG-ANR-P1-001**
- **Issue**: ProfilingTrigger API 37 capabilities incomplete
- **Current**: Missing TRIGGER_TYPE_OOM, TRIGGER_TYPE_ANOMALY, TRIGGER_TYPE_APP_COMPAT
- **Fix**: Add complete trigger type list and usage scenarios for API 37
- **Impact**: High - covers latest Android capabilities

### Measure (19.09)
**SUGG-MEASURE-P1-001**
- **Issue**: Android 12-14 ANR capture evolution not documented
- **Current**: No version-specific ANR handling differences
- **Fix**: Document ANR capture capabilities across Android 12-14
- **Impact**: High - affects version-specific implementation

### Measure (19.09)
**SUGG-MEASURE-P1-002**
- **Issue**: Android 15+ native crash support not addressed
- **Current**: No mention of newer native crash capabilities
- **Fix**: Document Android 15+ native crash reporting evolution
- **Impact**: Medium - future-proofing the content

### 崩溃与 ANR 捕获机制 (19.24)
**SUGG-ANR-P1-002**
- **Issue**: KOOM fork-dump boundaries not clarified for Android 17
- **Current**: No mention of Android 17 compatibility
- **Fix**: Document Android 17 applicability and limitations
- **Impact**: Medium - affects low-tier device strategy

### TextureView 合成链路 (18.7)
**SUGG-TV-P1-001**
- **Issue**: BLAST submit chain not detailed enough
- **Current**: BLAST adapter to SurfaceFlinger interaction unclear
- **Fix**: Add detailed BLAST Transaction and Buffer flow description
- **Impact**: High - understanding performance bottlenecks

### TextureView 合成链路 (18.7)
**SUGG-TV-P1-002**
- **Issue**: Double fence mechanism synchronization unclear
- **Current**: Two-layer fence synchronization timing not explained
- **Fix**: Clarify acquire fence and composition fence dependency relationships
- **Impact**: Medium - important for debugging

## P2 Priority Suggestions

### All Chapters
**SUGG-ALL-P2-001**
- **Issue**: Missing performance benchmark data
- **Current**: No concrete performance metrics or benchmarks
- **Fix**: Add specific GPU sampling time, memory usage, and processing time data
- **Impact**: Medium - enables quantitative optimization decisions

### Measure (19.09)
**SUGG-MEASURE-P2-001**
- **Issue**: Data model chain flow unclear
- **Current**: Event production to backend aggregation process not described
- **Fix**: Add complete data flow diagram and pipeline description
- **Impact**: Medium - improves implementation understanding

### Measure (19.09)
**SUGG-MEASURE-P2-002**
- **Issue**: Session timeline construction principles missing
- **Current**: No technical details on how events relate to session_id
- **Fix**: Add session association mechanism explanation
- **Impact**: Low - completeness improvement

### TextureView 合成链路 (18.7)
**SUGG-TV-P2-001**
- **Issue**: Metal/Vulkan backend differences missing
- **Current**: Only covers OpenGL ES performance characteristics
- **Fix**: Add Metal/Vulkan vs OpenGL ES performance comparison
- **Impact**: Medium - future-proofing for modern devices

### TextureView 合成链路 (18.7)
**SUGG-TV-P2-002**
- **Issue**: BufferQueue reference path incorrect
- **Current**: Cross-reference path doesn't match actual file structure
- **Fix**: Correct the chapter reference to [2.13 图形缓冲区管理]
- **Impact**: Low - reference accuracy
## [Task6 Review] 25.6 APK 体积分析与瘦身 — 2026-06-03
- **类型**：需确认
- **位置**：`.so` 库瘦身节 — AOSP master 源码锚点（PackageAbiHelperImpl.java、NativeLibraryHelper.java、ResourceTypes.h）
- **问题**：三处源码引用标注为 "AOSP master"，按 AIW Android 版本边界规则（AIW_ANDROID_VERSION_CAP_2026_05_29），应替换为 android-17.0.0_r1 或更低版本标签，或标注"未进入 Android 17"并跳过正文结论。
- **建议**：Task9 验证三处源码锚点的版本归属，替换为已验证版本标签或改为"未进入 Android 17"背景说明。
- **review 日志**：logs/review/2026-06-03-14-review.md
