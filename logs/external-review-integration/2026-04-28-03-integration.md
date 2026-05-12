# External Review Integration Log — 2026-04-28 03:49

## 扫描结果
- 活跃文件数: 29
- 成功解析: 29
- 成功整合: 29
- 跳过: 0

## 写入结果
- queue.json: 新增 12 条, 合并 16 条
- research-gaps.md: 新增 16 条
- suggestions.md: 新增 28 条

## 涉及章节
- 2.2 帧率与刷新率
- **严重级别**：P1
- **位置**：App 参与决策 / 常见问题
- **问题描述**：未反映 2026 年 ARR API 及厂商高频注入逻辑。
- **建议修正方向**：同步 Android 16/17 最新 API 并补全高频注入的技术特征。

### 9.4 可复用知识资产
- **性能锚点**：Android 17 限帧检测 `getFrameRateOverride()`。
- **核心逻辑**：高频注入打破了“一个 VSync 处理一个输入”的旧律。
- **技术结论**：Android 16 实现了从“静态频率适配”到“动态意图适配（SuggestedRate）”的跨越。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch02-02-framerate-external-review.md`
- 2.3 VSync 机制
- **严重级别**：P1
- **位置**：算法、过滤及分发小节
- **问题描述**：常量定义过时且遗漏 Android 16 新增回调。
- **建议修正方向**：同步 20/20% 常量并加入回调机制说明。

### 9.4 可复用知识资产
- **调试锚点**：`debug.sf.vsp_trace`。
- **技术结论**：Android 16 的 VSync 策略更倾向于“容忍小抖动以换取模型稳定性”。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch02-03-vsync-external-review.md`
- 2.4 Choreographer 与渲染流水线
- **严重级别**：P1
- **位置**：监控指标与 Compose 适配
- **问题描述**：未反映 Android 16 的对齐 ID 及 Compose 1.10 新特征。
- **建议修正方向**：同步新增 FRAME_TIMELINE_VSYNC_ID 说明并补全 Compose resume Trace 细节。

### 9.4 可复用知识资产
- **性能锚点**：`FrameMetrics.FRAME_TIMELINE_VSYNC_ID` 是数据对齐的“金钥匙”。
- **核心切片**：`Compose:PausableComposition:resume`。
- **技术结论**：Android 16 标志着 Choreographer 观测性从“孤岛统计”向“联路协同”的跨越。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch02-04-choreographer-external-review.md`
- 2.5 Main Thread 与 RenderThread 协作
- **严重级别**：P1
- **位置**：线程职责与 GPU 渲染小节
- **问题描述**：未反映 2026 年 ADPF 闭环及分片并行提交特性。
- **建议修正方向**：同步 ADPF 反馈机制并加入分片架构并行提交说明。

### 9.4 可复用知识资产
- **性能锚点**：DeliQueue 提升系统流畅度约 7.7%。
- **核心逻辑**：RenderThread 已进化为具备负载感知与并行分片提交能力的智能管道。
- **技术结论**：Android 16 实现了渲染指令从“串行堆叠”向“硬件原生并发”的跨越。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch02-05-main-render-thread-external-review.md`
- 2.6 SurfaceFlinger 与合成
- **严重级别**：P1
- **位置**：主循环与合成模式小节
- **问题描述**：未反映 2026 年多屏同步架构及 AIDL V4 旁路机制。
- **建议修正方向**：同步 FrameTargeter 逻辑并加入 CLIENT_BYPASS 说明。

### 9.4 可复用知识资产
- **性能锚点**：AIDL Composer V4 `expectedPresentTime`。
- **核心类名**：`FrameTargeter`。
- **技术结论**：Android 16 实现了从“单时钟主从架构”向“动态 Pacesetter 同步架构”的跨越。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch02-06-surfaceflinger-external-review.md`
- 2.7 Hardware Layer
- **严重级别**：P1
- **位置**：RenderNode 自动化 / 内存代价 / Compose 适配
- **问题描述**：未反映 2026 年自动建层算法及 16KB 内存挑战。
- **建议修正方向**：同步复杂度评分逻辑并加入显存碎片化预警。

### 9.4 可复用知识资产
- **性能锚点**：16KB 系统下显存开销平均增加 9%。
- **核心机制**：RenderNode Auto-promotion (基于指令权重)。
- **技术结论**：Android 16 的 Hardware Layer 已从“手动挡”全面升级为“智能自动挡”。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch02-07-hardware-layer-external-review.md`
- 2.8 过度绘制与层级压平
- **严重级别**：P1
- **位置**：原理、工具及 Compose 适配
- **问题描述**：未反映 2026 年 Z-test 自动化及标准量化指标。
- **建议修正方向**：同步 Graphite 深度测试逻辑并加入标准化计数器读图法。

### 9.4 可复用知识资产
- **性能锚点**：Perfetto 标准计数器 `gpu.counters.pixels_drawn`。
- **技术结论**：Android 16 实现了过度绘制从“视觉猜测”向“硬件统计”的定性跨越。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch02-08-overdraw-external-review.md`
- 2.9 渲染机制的版本演进
- **严重级别**：P1
- **位置**：Android 16 演进与后端演进小节
- **问题描述**：未反映 2026 年 Vulkan 1.4 强制规范及 Graphite 算法革新。
- **建议修正方向**：同步 VPA16 规范并描述深度测试绘制模型。

### 9.4 可复用知识资产
- **性能锚点**：16KB 页带来的 9% 渲染带宽红利。
- **技术结论**：Android 16 标志着图形系统从“画家叠加”时代跨入“深度剔除”时代。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch02-09-rendering-evolution-external-review.md`
- 2.10 GPU 渲染深入
- **严重级别**：P1
- **位置**：Perfetto 表现、优化策略及内存管理小节
- **问题描述**：未反映 2026 年标准化 GPU 监控标准及动态负载调节机制。
- **建议修正方向**：同步标准化轨道名称并引入 Headroom API 指导。

### 9.4 可复用知识资产
- **性能锚点**：标准化 Counter `gpu_busy`。
- **核心 API**：`getGpuHeadroom()`。
- **技术结论**：Android 16 实现了 GPU 监控从“黑盒猜测”向“白盒标准化”的跨越。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch02-10-gpu-rendering-external-review.md`
- 2.11 Flutter 渲染管线与性能
- **严重级别**：P1
- **位置**：原生差异 / Impeller 细节 / 分析策略
- **问题描述**：未反映 16KB 合规死线及 Vulkan 1.4 / ADPF 深度优化。
- **建议修正方向**：同步 NDK 插件 16KB 适配指南并补全 Android 16 专属性能红利。

### 9.4 可复用知识资产
- **性能锚点**：Impeller 结合 Vulkan 1.4 消除纹理卡顿。
- **合规节点**：2025-11-01。
- **技术结论**：Flutter 在 2026 年已实现了从“旁路渲染”向“系统原生协同调度”的跨越。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch02-11-flutter-rendering-external-review.md`
- 2.12 Window Manager Service 与窗口管理
- **严重级别**：P1
- **位置**：配置变更与布局逻辑小节
- **问题描述**：未反映 Android 16/17 重建契约及局部布局优化。
- **建议修正方向**：同步最新 Flag 列表并引入局部遍历算法说明。

### 9.4 可复用知识资产
- **性能锚点**：Android 16 局部遍历减少了 30% 布局开销。
- **核心属性**：`android:recreateOnConfigChanges`。
- **技术结论**：WMS 已实现了从“全量遍历”向“脏区感知遍历”的跨越。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch02-12-window-manager-external-review.md`
- 2.13 图形缓冲区管理 (BufferQueue)
- **严重级别**：P1
- **位置**：默认值、阻塞分析及 Perfetto 观察小节
- **问题描述**：未反映 Android 16 默认 3 缓冲及 vsyncId 后缀。
- **建议修正方向**：更新核心常量并同步增强型追踪规范。

### 9.4 可复用知识资产
- **性能锚点**：Android 16 默认采用“三缓冲准备”策略。
- **核心签名**：`queueBuffer <vsyncId>`。
- **技术结论**：Android 16 彻底终结了跨进程帧对齐的“猜测时代”。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch02-13-buffer-queue-external-review.md`
- 2.14 图形 API 演进与选择策略
- **严重级别**：P1
- **位置**：Vulkan 1.4 / ANGLE / WebGPU 章节
- **问题描述**：未反映 2026 年强制规范及 API 性能收口趋势。
- **建议修正方向**：同步 VPA16 列表并更新 Android 17 ANGLE 强制化政策。

### 9.4 可复用知识资产
- **性能锚点**：WebGPU 计算性能达 Vulkan 95%。
- **核心机制**：VK_EXT_shader_object (Android 16 PSO 优化)。
- **技术结论**：Android 图形栈已完成从“多元共存”向“Vulkan/ANGLE 单核化”的完全演进。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch02-14-graphics-api-evolution-external-review.md`
- 2.15 DMA-BUF、Gralloc 与跨进程图形内存共享
- **严重级别**：P1
- **位置**：HAL 接口、分配策略及传输封装小节
- **问题描述**：未反映 2026 年对齐协商、用户态池化及批量传输特性。
- **建议修正方向**：同步 IAllocator V2 规范并补全池化与 FDA 优化细节。

### 9.4 可复用知识资产
- **性能锚点**：Binder FDA 提速 SurfaceFlinger 约 30%。
- **核心接口**：`AHardwareBuffer_allocateWithOptions`。
- **技术结论**：Android 16 实现了图形内存从“简单分配”向“高效池化与批量传输”的跨越。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch02-15-dmabuf-gralloc-external-review.md`
- 2.16 Sync Fence 框架与帧同步机制
- **严重级别**：P1
- **位置**：核心机制、渲染路径及版本演进小节
- **问题描述**：未反映 2026 年时间轴信号量及 16KB 页同步红利。
- **建议修正方向**：引入状态化同步模型并同步 16KB 加速原理。

### 9.4 可复用知识资产
- **性能锚点**：16KB 页减少 75% 的同步路径 TLB Miss。
- **核心逻辑**：Timeline Semaphores 实现了图形同步的“确定性步进”。
- **技术结论**：Android 16 标志着图形同步进入了“ fd-less 时代”的序幕。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch02-16-sync-fence-external-review.md`
- 2.17 Frame Pacing Library 与帧节奏控制
- **严重级别**：P1
- **位置**：提交链、接入细节及演进趋势小节
- **问题描述**：未反映 2026 年 ADPF 闭环调控及 Vulkan 1.4 硬件加速特性。
- **建议修正方向**：引入负载反馈逻辑并同步 present_id 硬件确认机制。

### 9.4 可复用知识资产
- **性能锚点**：Vulkan 1.4 `present_id` 降低帧抖动 30%。
- **技术结论**：2026 年的 Frame Pacing 已经从“尽力而为的预测”进化为“软硬协同的闭环裁决”。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch02-17-frame-pacing-external-review.md`
- 2.18 Adaptive Refresh Rate 与动态帧率控制
- **严重级别**：P1
- **位置**：功耗取舍、SF 打分及 Perfetto 观察小节
- **问题描述**：未反映 2026 年低频防闪烁技术及打分算法加速。
- **建议修正方向**：同步 Gamma 补偿机制并补全 16KB 环境下的打分性能红利。

### 9.4 可复用知识资产
- **性能锚点**：ARR 打分耗时降低 12% (16KB)。
- **核心逻辑**：防闪烁补偿实现了“功耗下探、品质不降”。
- **技术结论**：Android 16 标志着 ARR 从“逻辑正确”向“显示完美”的跨越。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch02-18-adaptive-refresh-rate-external-review.md`
- 2.19 刷新率切换与帧率适配性能
- **严重级别**：P1
- **位置**：硬件过渡、仲裁策略及过渡期分析小节
- **问题描述**：未反映 2026 年 HWC 4.0 预判机制及原子偏移切换。
- **建议修正方向**：同步预案式切换逻辑并补全 VsyncModulator 原子重构细节。

### 9.4 可复用知识资产
- **性能锚点**：Android 16 下无缝切换延迟降至 <16ms。
- **核心机制**：expectedPresentTime (HWC 4.0 核心字段)。
- **技术结论**：2026 年的刷新率管理已从“响应式”切换进化为“预见式”切换。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch02-19-refresh-rate-switching-external-review.md`
- 2.20 多窗口与桌面模式渲染性能
- **严重级别**：P1
- **位置**：SF 工作负载 / 优化策略 / 内存影响小节
- **问题描述**：未反映 2026 年掉帧隔离数据、状态缓存红利及内存累加压力。
- **建议修正方向**：同步 Android 17 性能指标并加入 16KB 页多任务预警。

### 9.4 可复用知识资产
- **性能锚点**：Android 17 多屏场景下应用掉帧下降 4%。
- **核心机制**：Desktop State Caching (瞬时恢复)。
- **技术结论**：2026 年的桌面模式已从“模拟多窗”进化为“物理性能隔离”的成熟架构。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch02-20-multiwindow-desktop-rendering-external-review.md`
- 2.21 文字渲染性能
- **严重级别**：P1
- **位置**：引擎原理、优化实践及 API 演进小节
- **问题描述**：未反映 2026 年引擎提速、轴向缓存及排版 API 突破。
- **建议修正方向**：同步 HarfBuzz 10.x 收益并加入 Android 17 新特性说明。

### 9.4 可复用知识资产
- **性能锚点**：阿拉伯语塑形提速达 45% (Android 16+)。
- **核心 API**：`shiftDrawingOffsetForStartOverhang`。
- **技术结论**：2026 年的 Android 文本系统已实现从“基础显示”向“高品质动态排版”的完全跨越。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch02-21-text-rendering-performance-external-review.md`
- 3.1 Input 事件分发全流程
- **严重级别**：P1
- **位置**：分发策略、协作机制及接收端分析小节
- **问题描述**：未反映 2026 年 AOT 返回模型及判定逻辑下沉特性。
- **建议修正方向**：同步返回分发新契约并补全 Native 排除区域判定说明。

### 9.4 可复用知识资产
- **性能锚点**：Native 手势排除判定缩短 10ms 延迟。
- **技术结论**：Android 16 实现了输入拦截从“App 决定”向“系统 AOT 裁决”的定性跨越。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch03-01-input-dispatch-external-review.md`
- 3.2 触控性能优化
- **严重级别**：P1
- **位置**：原理组成、预测机制及 16KB 适配小节
- **问题描述**：未反映 HCI 科学研究阈值及 Android 16 的 AI 预测模型。
- **建议修正方向**：同步 11ms 科学基准并引入 TFLite 预测模型实现。

### 9.4 可复用知识资产
- **性能锚点**：拖拽感知阈值 11ms。
- **核心机制**：TFLite MotionPredictor (NPU 推理)。
- **技术结论**：Android 16 标志着输入系统从“线性外推”跨入了“特征感知预测”的新阶段。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch03-02-touch-performance-external-review.md`
- 3.3 手势导航与系统交互
- **严重级别**：P1
- **位置**：回调模型、演进趋势及 Monitor 原理小节
- **问题描述**：未反映 2026 年 AOT 强制拦截、观察者优先级及设备级隔离优化。
- **建议修正方向**：同步返回键 AOT 模型及优先级新常数，补全多窗口指针窃取隔离逻辑。

### 9.4 可复用知识资产
- **性能锚点**：预测性返回通过 Shell 托管动画减少了 App 主线程的每帧负担。
- **核心类名**：`OnBackInvokedDispatcher.PRIORITY_SYSTEM_NAVIGATION_OBSERVER`。
- **技术结论**：Android 16 实现了手势导航从“简单的输入捕获”向“精准的设备流管理”的飞跃。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch03-03-gesture-navigation-external-review.md`
- 3.4 输入延迟与预测输入技术
- **严重级别**：P1
- **位置**：调度优化、量化工具及采样策略小节
- **问题描述**：未反映 2026 年 ADPF 闭环、HWC 4.0 标准及动态高频采样。
- **建议修正方向**：同步最新闭环调度逻辑并引入标准化光子时间线。

### 9.4 可复用知识资产
- **性能锚点**：HWC 4.0 实现了端到端延迟的软件级精准度量。
- **核心机制**：ADPF 动态线程提升。
- **技术结论**：2026 年的输入优化已从“单点提速”进化为“全链路反馈闭环”。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch03-04-input-latency-prediction-external-review.md`
- 3.5 输入事件拦截与安全机制
- **严重级别**：P1
- **位置**：安全边界、拦截机制及演进趋势小节
- **问题描述**：未反映 2026 年敏感隔离属性、物理分发切断及通话保护策略。
- **建议修正方向**：同步 API 36 敏感视图规范并引入 Android 17 的 InputMonitor 物理切断逻辑。

### 9.4 可复用知识资产
- **性能锚点**：密码输入触发 InputDispatcher 零延迟分发挂起。
- **核心属性**：`accessibilityDataSensitive`。
- **技术结论**：Android 16 标志着输入系统进入了“意图敏感型分发保护”阶段。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch03-05-input-interception-security-external-review.md`
- 4.1 Android 内存模型全景
- **严重级别**：P1
- **位置：**内核管理、物理内存及指标分析小节
- **问题描述**：未反映 2026 年内存限额契约及 MTE/16KB 硬件开销。
- **建议修正方向**：引入配额制说明并更新 MTE/16KB 的内存基准损耗。

### 9.4 可复用知识资产
- **性能锚点**：MTE 系统开销 5%，16KB 膨胀系数 1.1x。
- **核心类名**：`ProfilingManager.TRIGGER_TYPE_ANOMALY`。
- **技术结论**：2026 年的内存管理已从“策略建议”演进为“硬性配额审计”。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch04-01-memory-overview-external-review.md`
- 4.2 Linux 内核内存管理
- **严重级别**：P1
- **位置**：页面回收、16KB 页适配及协同优化小节
- **问题描述**：未反映 2026 年 MGLRU 默认化、内核-GC 协同细节及 75% 缺页降幅。
- **建议修正方向**：同步最新内核策略并补全 Silk 论文落地后的架构逻辑。

### 9.4 可复用知识资产
- **性能锚点**：16KB 页模式下 page_fault 减少 75%。
- **核心指令**：`madvise(MADV_COLD)`。
- **技术结论**：Android 16 标志着内存治理进入了“由虚拟机驱动内核回收”的精细化阶段。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch04-02-linux-memory-external-review.md`
- 4.3 ART 虚拟机内存管理
- **严重级别**：P1
- **位置**：分代回收、分配器原理及性能分析小节
- **问题描述**：未反映 2026 年分代 CMC 收益、16KB 动态对齐及无锁队列红利。
- **建议修正方向**：更新性能基准数据，引入运行时对齐逻辑，并加入稳定性优化说明。

### 9.4 可复用知识资产
- **性能锚点**：分代 CMC 使 OpenCL 计算能效提升 32.6%。
- **核心逻辑**：运行时 GetPageSize() 取代硬编码对齐。
- **技术结论**：Android 16 实现了虚拟机层与硬件层（大页/多核）的深度自适应对齐。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch04-03-art-memory-external-review.md`
- 4.4 Low Memory Killer
- **严重级别**：P1
- **位置**：回收策略、厂商定制及版本演进小节
- **问题描述**：未反映 2026 年可见性保护、内存限额及相机场景优化。
- **建议修正方向**：引入可见性感知逻辑，描述配额制影响并补全相机清场细节。

### 9.4 可复用知识资产
- **性能锚点**：16KB 页加速内存释放约 4 倍。
- **核心机制**：Visibility-aware Kill (桌面模式稳定性保障)。
- **技术结论**：Android 16 标志着内存管理从“单纯看数字”向“理解交互状态”的跨越。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-28-15-ch04-04-lmk-external-review.md`

## 警告
无
