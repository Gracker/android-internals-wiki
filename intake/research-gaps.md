# 知识盲区与待验证问题

## 11.4 案例集（案例集）知识盲区

### 🔍 待验证问题

#### 源码引用准确性
1. **JobScheduler 常量来源错误** - 当前路径错误
   - 文件：`src/part2-performance/ch11-power/04-case-studies.md`
   - 当前引用：`frameworks/base/core/java/android/app/JobServiceContext.java`
   - 正确路径：`frameworks/base/services/core/java/com/android/server/job/JobSchedulerService.java`
   - 严重程度：P0 - 源码错误
   - 状态：待修正

2. **PowerManager.java API 版本对应关系** - 缺少版本兼容性说明
   - 文件：`src/part2-performance/ch11-power/04-case-studies.md`
   - 问题描述：未明确标注使用的 PowerManager.WakeLock API 在不同 Android 版本中的兼容性
   - 严重程度：P1 - 重要信息缺失
   - 状态：待补充

#### 原理链完整性
1. **Radio 状态机功耗原理不完整** - 仅说明各状态电流值
   - 文件：`src/part2-performance/ch11-power/04-case-studies.md`
   - 问题描述：仅说明各状态电流值，未解释状态转换本身的功耗开销
   - 严重程度：P1 - 重要原理缺失
   - 状态：待补充

#### 版本差异覆盖
1. **前台服务超时机制版本差异** - Android 15+ FGS 差异不明
   - 文件：`src/part2-performance/ch11-power/04-case-studies.md`
   - 问题描述：Android 15+ FGS 超时机制与之前的差异描述不够明确
   - 严重程度：P1 - 版本差异覆盖不足
   - 状态：待补充

2. **厂商工具版本兼容性** - 版本范围未明确
   - 文件：`src/part2-performance/ch11-power/04-case-studies.md`
   - 问题描述：未明确各厂商功耗检测工具支持的 Android 版本范围
   - 严重程度：P2 - 建议改进
   - 状态：待补充

#### 知识盲区
1. **省电模式与热节流协同** - Battery Saver 模式影响未知
   - 文件：`src/part2-performance/ch11-power/04-case-studies.md`
   - 问题描述：未讨论 Battery Saver 模式如何影响省电策略实施效果
   - 严重程度：P1 - 知识盲区
   - 状态：待补充

2. **隐私沙盒对位置功耗影响** - Android 12+ 未知影响
   - 文件：`src/part2-performance/ch11-power/04-case-studies.md`
   - 问题描述：Android 12+ 隐私沙盒对位置服务功耗的影响未覆盖
   - 严重程度：P1 - 知识盲区
   - 状态：待补充

3. **自适应电池整合** - App Standby 与自适应电池协同机制未知
   - 文件：`src/part2-performance/ch11-power/04-case-studies.md`
   - 问题描述：未说明 App Standby 与自适应电池的协同工作机制
   - 严重程度：P2 - 知识盲区
   - 状态：待补充

#### 数据与案例支撑
1. **功耗数据测试条件缺失** - GPS (50-100mA)、Radio 状态功耗等数据未标注测试设备和具体条件
   - 文件：`src/part2-performance/ch11-power/04-case-studies.md`
   - 问题描述：功耗数据未标注测试设备和具体条件
   - 严重程度：P2 - 数据支撑不足
   - 状态：待补充

## 新增盲区
- 上次更新：2026-06-17 20:27
- 盲区总数：3
- P1 盲区：2
- P2 盲区：1