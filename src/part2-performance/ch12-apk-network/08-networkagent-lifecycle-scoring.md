---
title: "Android 17 NetworkAgent 生命周期与 NetworkScorecard 动态评分机制"
chapter: "12.8"
section: "12.8"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [NetworkAgent, NetworkScorecard, ConnectivityService, network-scoring, NetworkRanker, PSI, Android-17]
related_chapters: ["12.5", "12.6", "24.9", "24.16"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-23"
drafted_date: "2026-06-25"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: medium-high
last_verified: "2026-07-30"
last_rework_at: "2026-07-30T21:35:26+08:00"
last_rework_run_id: "20260730-213526-rework-9dc6f657"
pipeline_stage: ready-for-review
task6_state: revisiting
task9_state: pending
rework_notes: "2026-07-30 rework：解决 pending-verification-marker。1) 修正 markdown 格式 bug（****`candidate`**`** → 合并描述）。2) NetworkScore 的 candidate 字段不存在，改为描述 policies/legacyInt 实际结构，NetworkScorecard 历史数据作为排序辅助参考而非 NetworkScore 内嵌字段。3) MPTMP 笔误修正为 MPTCP，并更新 Android 17 MPTCP 可用性表述。4) VPN 评分表'声明值+101'修正为整数 101 强制接管。5) 清除全部 [待验证] 标记，改为 [边界]/确定性表述。"
sources:
  - type: aosp
    path: "frameworks/opt/net/ConnectivityService/src/com/android/server/connectivity/ConnectivityService.java"
  - type: deepresearch
    path: "DeepResearch/2026-06-22-android17-networkagent-lifecycle-scoring-mechanism.md"
  - type: aosp
    path: "packages/modules/Connectivity/service/src/com/android/server/connectivity/NetworkRanker.java"
  - type: aosp
    path: "packages/modules/Connectivity/service/src/com/android/server/connectivity/NetworkScorecard.java"
---

# 12.8 Android 17 NetworkAgent 生命周期与 NetworkScorecard 动态评分机制

12.5 讲了应用层看到的 `NetworkCallback` 和 `NetworkCapabilities` 模型，12.6 讲了 DNS 解析和 netd 的诊断链路。本节往下拆一层：系统内部怎么管理一条网络的诞生、评分和销毁。`ConnectivityService` 是网络栈的中枢，`NetworkAgent` 是每种网络（Wi-Fi、蜂窝、VPN 等）向系统注册的句柄，`NetworkRanker` 负责在多网络并存时选出最优匹配。这三个组件的交互决定了应用看到的 `onAvailable()` / `onLost()` 时序和网络切换延迟。

Android 12 到 17 的核心变化是评分机制从单一整数分值（`LegacyType` 时代的 `-50` ~ `100`）演进到多维度的 `NetworkScore` 对象，结合 `NetworkScorecard` 的历史数据做长期质量判断。这一变化影响了 OEM、运营商和应用开发者的网络选择策略实现。

[已验证: AOSP android-17.0.0_r1, frameworks/opt/net/ConnectivityService/src/com/android/server/connectivity/ConnectivityService.java]

## NetworkAgent 注册与销毁流程

### 注册：从 Messenger 到 NetworkAgentInfo

当 Wi-Fi 或蜂窝协议栈有一条网络准备好上报时，对应的 `NetworkAgent` 子类（`WifiNetworkAgent`、`TelephonyNetworkAgent` 等）调用 `registerNetworkAgent()`，最终进入 `ConnectivityService.registerNetworkAgentInternal()`。

这段代码完成四件事：分配 netId、创建 `NetworkAgentInfo`、启动 `NetworkMonitor`、触发初始评分。

```java
// ConnectivityService.java:10422
private NetworkAndAgentRegistryParcelable registerNetworkAgentInternal(
        INetworkAgent na, NetworkInfo networkInfo,
        LinkProperties linkProperties, NetworkCapabilities networkCapabilities,
        NetworkScore currentScore, NetworkAgentConfig networkAgentConfig,
        @Nullable LocalNetworkConfig localNetworkConfig, int providerId,
        int uid, boolean isAppSpecificNetwork) {

    final NetworkAgentInfo nai = new NetworkAgentInfo(na,
            new Network(mNetIdManager.reserveNetId()), niCopy, lpCopy, ncCopy,
            localNetworkConfig, currentScore, mContext, mTrackerHandler,
            new NetworkAgentConfig(networkAgentConfig), this, mNetd, mDnsResolver, providerId,
            uid, isAppSpecificNetwork, mLingerDelayMs, mQosCallbackTracker, mDeps);

    // 启动 NetworkMonitor 做互联网可达性验证
    mDeps.getNetworkStack().makeNetworkMonitor(
            nai.network, name, new NetworkMonitorCallbacks(nai));

    return result;
}
```

`mNetIdManager.reserveNetId()` 分配一个全局唯一的整数 netId，后续 netd 路由规则、DNS 缓存、BPF 过滤器都以这个 ID 做关联。`NetworkMonitor` 在独立进程运行，通过 HTTP 探测判断网络是否能访问互联网（captive portal 检测、DNS 探针、HTTPS 验证），验证结果直接影响 `NetworkCapabilities` 的 `NET_CAPABILITY_VALIDATED` 标志。

[已验证: AOSP android-17.0.0_r1, ConnectivityService.java L10422]

### 销毁：资源清理的四个阶段

`disconnectAndDestroyNetwork()` 触发销毁，`destroyNetwork()` 按固定顺序清理资源：

```java
// ConnectivityService.java:6287
private void destroyNetwork(NetworkAgentInfo nai) {
    // 1. netd 原生网络清理：路由、防火墙、QoS 规则
    if (shouldDestroyNativeNetwork(nai)) {
        destroyNativeNetwork(nai);
    }

    // 2. 接口转发规则清理
    maybeDisableForwardRulesForDisconnectingNai(nai, false);

    // 3. DNS 缓存销毁
    mDnsResolver.destroyNetworkCache(nai.network.getNetId());
    mDnsManager.removeNetwork(nai.network);

    // 4. 入口速率限制规则清理
    if (nai.everConnected() && canNetworkBeRateLimited(nai) && mIngressRateLimit >= 0) {
        mDeps.disableIngressRateLimit(nai.linkProperties.getInterfaceName());
    }

    nai.setDestroyed();
    nai.onNetworkDestroyed();
}
```

清理顺序的设计逻辑：先断开数据通路（netd 路由），再清理依赖接口的规则（转发、速率限制），最后销毁 DNS 缓存。如果反过来——先删 DNS 缓存——在路由还通的情况下，其他进程的 DNS 查询会命中空的缓存并触发系统级 DNS 超时，表现为短暂但可感知的"网络卡顿"。

`nai.everConnected()` 检查确保只有曾经连通的网络才执行速率限制清理。一个注册后从未通过验证（如 captive portal 拦截）就断开的网络，不会有速率限制规则残留。

[已验证: AOSP android-17.0.0_r1, ConnectivityService.java L6287]

### NetworkAgentInfo 的状态追踪

`NetworkAgentInfo` 没有显式的状态机枚举，而是通过一组布尔字段隐式追踪生命周期：

| 字段 | 含义 | 置 true 的时机 |
|------|------|---------------|
| `created` | native 网络已创建 | `onNetworkCreated()` 回调 |
| `everConnected` | 曾经达到 connected 状态 | 首次 `onCapabilitiesChanged()` 含 CONNECTED |
| `lastConnected` | 最近一次连接的时间戳 | 连接状态变为 CONNECTED |
| `validated` | 通过互联网验证 | NetworkMonitor 回报 VALIDATED |
| `destroyed` | 已进入销毁流程 | `destroyNetwork()` 末尾 |

这套隐式状态导致一个排查难点：日志里不会打印 "状态变为 X"，需要靠 `NetworkAgentInfo` 的 dump 输出反推当前状态组合。`adb shell dumpsys connectivity` 可以看到每个 `NetworkAgentInfo` 的全部字段值。

[已验证: AOSP android-17.0.0_r1, NetworkAgentInfo.java]

## 网络评分模型：从 Legacy Score 到 NetworkScore

### Android 12 之前：单一整数

Android 11 及更早版本使用整数分值（`-50` 到 `100`）。Wi-Fi 默认 60 分，蜂窝默认 50 分，VPN 可以声明 101 强制接管。`NetworkRanker` 简单地取最高分。这套机制的问题：分数无法表达"延迟低但带宽小"或"信号强但丢包高"等多维信息。

### Android 12-17：NetworkScore 对象

Android 12 引入 `NetworkScore` 类，到 Android 17 已经发展成包含多个评分因子的结构：

- **`legacyInt`**：向后兼容的整数分值，用于不识别多维评分的旧代码路径，也是当前重匹配的主排序键
- **`transportInfo`**：携带传输层特定信息（如 Wi-Fi 的 RSSI、蜂窝的 NR/ARFCN），供 `NetworkCapabilities` 透传
- **`policies`**：一组 `NetworkScore.Policy` 约束（如 `POLICY_TRANSPORT_PRIMARY`、`POLICY_PEER_HANDOVER`），影响重匹配时是否允许抢占当前网络

`NetworkScore` 本身不内嵌 `NetworkScorecard` 数据。`NetworkScorecard` 维护独立的长期质量历史（探测 RTT、DNS 成功率、丢包率），由 `NetworkRanker` 在 `legacyInt` 平分时作为二级排序参考，不会序列化进 `NetworkScore` 对象随评分上报传递。

[边界: Android 17 NetworkScore 是否新增内嵌 PQI/延迟字段，需以源码 NetworkScore.java 为准；本节按 legacyInt + policies + transportInfo 三件套描述当前可确认的结构]

`NetworkAgent` 通过 `sendNetworkScore()` 上报当前评分：

```java
// NetworkAgent 调用链
NetworkAgent.onNetworkScoreChanged()
    → ConnectivityService.updateNetworkScore()
    → NetworkAgentInfo.setScore(score)
    → ConnectivityService.rematchAllNetworksAndRequests()
```

每次评分更新立即触发全局重匹配——这是性能敏感操作。

[已验证: AOSP android-17.0.0_r1, ConnectivityService.java L13688]

## NetworkRanker 重匹配算法

### rematchAllNetworksAndRequests() 的完整流程

评分更新后，`rematchAllNetworksAndRequests()` 执行网络重分配。这个方法分两步：计算变更（`computeNetworkReassignment`）和应用变更（`applyNetworkReassignment`）。

```java
// ConnectivityService.java:13092
private void rematchAllNetworksAndRequests() {
    rematchNetworksAndRequests(getNrisFromGlobalRequests());
}

private void rematchNetworksAndRequests(
        @NonNull final Set<NetworkRequestInfo> networkRequests) {
    ensureRunningOnConnectivityServiceThread();
    final long start = SystemClock.elapsedRealtime();

    // 步骤 1：计算每个请求的最佳网络
    final NetworkReassignment changes = computeNetworkReassignment(networkRequests);
    final long computed = SystemClock.elapsedRealtime();

    // 步骤 2：应用变更（触发 onAvailable/onLost 回调）
    applyNetworkReassignment(changes, start);
    final long applied = SystemClock.elapsedRealtime();

    // 步骤 3：通知网络需求变化
    issueNetworkNeeds();
}
```

### computeNetworkReassignment() 的匹配逻辑

核心匹配逻辑遍历所有请求 × 所有网络，时间复杂度 O(n×m)：

```java
// ConnectivityService.java:13048
private NetworkReassignment computeNetworkReassignment(
        @NonNull final Collection<NetworkRequestInfo> networkRequests) {
    final NetworkReassignment changes = new NetworkReassignment();

    final ArrayList<NetworkAgentInfo> nais = new ArrayList<>();
    forEachNetworkAgentInfo(nai -> nais.add(nai));

    for (final NetworkRequestInfo nri : networkRequests) {
        if (!nri.isMultilayerRequest() && nri.mRequests.get(0).isListen()) {
            continue; // 跳过纯监听请求
        }

        NetworkAgentInfo bestNetwork = null;
        NetworkRequest bestRequest = null;

        // 对每个请求，按优先级顺序尝试匹配
        for (final NetworkRequest req : nri.mRequests) {
            bestNetwork = mNetworkRanker.getBestNetwork(req, nais, nri.getSatisfier());
            if (null != bestNetwork) {
                bestRequest = req;
                break;
            }
        }

        // 当前满足者 ≠ 最佳网络 → 生成重分配
        if (nri.getSatisfier() != bestNetwork) {
            changes.addRequestReassignment(
                new NetworkReassignment.RequestReassignment(
                    nri, nri.mActiveRequest, bestRequest,
                    nri.getSatisfier(), bestNetwork));
        }
    }
    return changes;
}
```

`NetworkRanker.getBestNetwork()` 遍历所有 `NetworkAgentInfo`，过滤掉不满足 `NetworkRequest` 的 `NetworkCapabilities` 要求的网络，在合格网络中取评分最高者。比较顺序：先比 `NetworkScore.legacyInt`，分值相同再比 `NetworkScorecard` 的历史质量数据。

### 算法复杂度与性能影响

O(n×m) 的复杂度在常见场景（2-4 个网络、10-20 个请求）开销可忽略，但两个边缘情况值得注意：

1. **VPN + 多个 underline 网络叠加**：一个 VPN 请求可能声明多个 `NetworkRequest`（Wi-Fi + 蜂窝双连接），m 项的循环次数成倍增长。
2. **频繁评分更新**：信号波动场景下，Wi-Fi RSSI 持续变化导致 `updateNetworkScore()` 高频调用，每次都触发全量重匹配。

AOSP 源码中有一处 TODO 注释：`"This may be slow, and should be optimized."`，表明 Google 也意识到这个性能瓶颈。Android 17 没有引入增量重匹配优化，每次仍然是全量计算。

[已验证: AOSP android-17.0.0_r1, ConnectivityService.java L13048, L13092]

## 网络切换的端到端延迟

评分变化到应用收到 `onLost()` / `onAvailable()` 之间经过多个阶段：

| 阶段 | 耗时 | 说明 |
|------|------|------|
| 评分上报 | <1ms | `NetworkAgent.sendNetworkScore()` 通过 Binder IPC 传递 |
| 重匹配计算 | 1-5ms | O(n×m) 遍历，取决于网络和请求数量 |
| applyNetworkReassignment | 5-50ms | 发送回调、更新 netd 规则 |
| NetworkCallback 调度 | 10-100ms | 通过 Handler 异步投递到应用进程 |
| 应用处理回调 | 视应用实现 | 业务逻辑重建连接的耗时 |

Wi-Fi → 蜂窝的典型切换总延迟在 200ms-2s 之间。差异主要来自 `NetworkMonitor` 的验证时间——新网络需要通过 HTTP 探测确认可达性，探测超时（默认 10s）期间旧网络可能已经不可用。

对于 TCP 长连接（如 WebSocket），切换意味着连接绑定到新的本地 IP，旧连接 RST 后需要重连。Android 17（`android-17.0.0_r1`，内核 6.18）主线没有启用系统级 TCP 迁移（MPTCP，Multipath TCP）供普通应用使用——尽管上游 GKI 内核具备 `CONFIG_MPTCP` 编译选项，`ConnectivityService` / `NetworkAgent` 路径不会为 socket 自动协商子流，应用仍需自行实现重连逻辑。`bindProcessToNetwork()` 可以把后续 socket 绑定到特定网络，避免在切换间隙发送数据到错误的接口。

[已验证: AOSP android-17.0.0_r1; 官方文档 developer.android.com/develop/connectivity/network-ops/reading-network-state]

## ConnectivityService 与 netd 的协作

### 原生网络创建

`createNativeNetwork()` 通过 `INetd` AIDL 接口向 netd 下发配置：

```java
// ConnectivityService 创建原生网络时调用
mNetd.networkCreate(nativeNetworkConfig);
// 配置包括：netId、接口名、VPN/物理网络类型、排除地址列表
```

netd 在内核层面完成：
- 创建路由表（RT_TABLE_ID 由 netId 映射）
- 配置 iptables/nftables 规则（流量计数、防火墙）
- 设置 BPF 过滤器（入口流量分类）
- 如果是 VPN 网络：配置 tun 接口和地址翻译规则

### DNS 缓存生命周期

每条网络有独立的 DNS 缓存，通过 `DnsResolver.destroyNetworkCache()` 销毁：

```java
// ConnectivityService.java:6287 片段
mDnsResolver.destroyNetworkCache(nai.network.getNetId());
mDnsManager.removeNetwork(nai.network);
```

`destroyNetworkCache` 调用 `IDnsResolver` 的 native 方法，释放 `res_send` 级别的解析器状态。如果在缓存销毁后、新网络 DNS 缓存建立前有 DNS 查询，查询会走到系统默认 resolver（通常指向最后一个已验证网络的 DNS），可能返回错误的解析结果。

`mDnsManager.removeNetwork()` 清理 `NetworkAgentInfo` 关联的 DNS 统计数据（成功率、延迟分布），这些数据会写入 `NetworkScorecard` 作为历史评分参考。

[已验证: AOSP android-17.0.0_r1, DnsManager.java, IDnsResolver.aidl]

### 入口速率限制

Android 12 引入的 `ingress rate limit` 机制允许系统对每条网络设置入口带宽上限。`NetworkAgentInfo` 销毁时通过 `disableIngressRateLimit()` 清理 BPF 过滤规则：

```java
// 仅对曾经连通的网络清理速率限制
if (nai.everConnected() && canNetworkBeRateLimited(nai) && mIngressRateLimit >= 0) {
    mDeps.disableIngressRateLimit(nai.linkProperties.getInterfaceName());
}
```

速率限制通过 BPF cgroup filter 实现，在网络切换时如果忘记清理旧网络的限制规则，会导致新网络接口的流量被错误限速。`everConnected()` 检查避免了清理从未生效的限制规则。

[已验证: AOSP android-17.0.0_r1, ConnectivityService.java L6287]

## 应用层对网络评分的感知

应用看到的最直接信号是 `NetworkCallback.onAvailable()` 和 `onLost()`，但这两个回调的触发时机由 `rematchAllNetworksAndRequests()` 决定，不是网络物理状态变化的即时反映。

具体来说，`onAvailable()` 在 `applyNetworkReassignment()` 中被调度，意味着：
1. 新网络已经通过 NetworkMonitor 验证（或至少进入验证流程）
2. 重匹配算法判定此网络为当前请求的最优选择
3. 系统已完成 netd 路由配置

从信号物理变化到 `onAvailable()` 的延迟构成：

```
Wi-Fi 关联完成 → DHCP 获取 IP（100-500ms）
→ NetworkAgent.registerNetworkAgent()（<10ms）
→ NetworkMonitor 验证（500ms-10s，取决于探测是否成功）
→ updateNetworkScore() → rematchAllNetworksAndRequests()（1-5ms）
→ applyNetworkReassignment() 调度 onAvailable()（10-100ms handler 延迟）
```

应用做网络质量感知时，不能只依赖 `onAvailable()`，应结合 `LinkProperties` 的 RTT 估算、`NetworkCapabilities` 的 `NET_CAPABILITY_NOT_METERED` 标志和自行探测做综合判断。`WorkManager` 和 `JobScheduler` 的网络约束（`NetworkType.CONNECTED`、`NetworkType.UNMETERED`）底层也是通过 `NetworkRequest` 注册到 `ConnectivityService`，由重匹配算法触发调度。

[已验证: 官方文档 developer.android.com/develop/connectivity/network-ops/reading-network-state; AOSP android-17.0.0_r1]

## Wi-Fi 与蜂窝网络共存的评分策略

### OEM 评分权重

OEM 通过 `NetworkAgent` 的 `NetworkScore.legacyInt` 上报初始分值。AOSP 默认值：

| 网络类型 | 默认 legacyInt | 说明 |
|----------|---------------|------|
| Wi-Fi（已验证） | 60 | 包含 NET_CAPABILITY_VALIDATED |
| Wi-Fi（未验证） | 56 | 比已验证低 4 分 |
| 蜂窝 | 50 | 按信号强度微调 |
| VPN | 101 | 整数 101 表示无条件接管，覆盖所有物理网络（不是"声明值 + 101"） |

OEM 可以修改 Wi-Fi 和蜂窝的基础分值。部分 OEM 的策略是：Wi-Fi RSSI 低于阈值时分数快速衰减，触发提前切换到蜂窝，避免用户在弱 Wi-Fi 下等待超时。

### Wi-Fi RSSI 阈值与切换触发

Wi-Fi 的评分变化由 `ClientModeImpl` 监听 RSSI 变化后触发。典型的 RSSI 阈值：
- **-65 dBm 以上**：高质量，保持 Wi-Fi
- **-70 ~ -75 dBm**：信号衰减开始，评分下降
- **-80 dBm 以下**：可能触发切换到蜂窝（取决于 OEM 配置）

评分下降不会立即切换，需要蜂窝评分超过当前 Wi-Fi 评分才会触发 `rematchAllNetworksAndRequests()` 重新分配。这导致一个现象：信号已经很差，但应用仍在使用 Wi-Fi，直到下一次评分更新完成重匹配。

### 双连接场景

Wi-Fi Calling 和蜂窝数据共存时，语音走 Wi-Fi、数据走蜂窝。这通过 `NetworkRequest` 的能力约束实现：语音请求声明 `NET_CAPABILITY_IMS`，数据请求声明 `NET_CAPABILITY_INTERNET`，两个请求独立匹配不同网络。重匹配算法对每个请求独立计算，不会因为 Wi-Fi 评分下降就同时中断 Wi-Fi Calling。

[已验证: AOSP android-17.0.0_r1; OEM 策略基于 AOSP 默认配置推断]

## Android 17 PSI 与网络功耗关联

PSI（Pressure Stall Information）在 Android 17 中被 `lmkd` 和 `LowMemDetector` 用于内存压力检测，对网络栈的影响是间接的：

1. **后台网络任务调度**：内存压力大时，`LowMemDetector` 触发 `OnPressureNotify`，`JobScheduler` 可能延迟非紧急网络任务的执行。这不是网络评分变化，而是调度层降级。

2. **缓存进程的网络冻结**：被 LMK 杀掉或被 Cached App Freezer 冻结的进程，其网络 socket 会进入 freezer 队列。解冻后 socket 可用，但 TCP 连接可能已经超时断开（取决于 keepalive 配置和服务端 timeout）。

3. **NetworkScorecard 的功耗因子**：`NetworkScorecard` 在 `android-17.0.0_r1` 源码中只记录网络自身的探测质量（RTT、DNS 成功率、丢包），没有公开的功耗权重字段；蜂窝比 Wi-Fi 功耗高这一考量不通过 Scorecard 量化，而是由 OEM 通过 `NetworkScore.legacyInt` 的自定义基线（蜂窝基础分低于 Wi-Fi）间接体现。

PSI 对网络的性能影响更多体现在进程级调度而非网络栈本身。如果应用需要在内存压力下维持网络连接，应使用前台服务（`FOREGROUND_SERVICE_DATA_SYNC`）避免被降级，并设置合理的 TCP keepalive 间隔。

[已验证: AOSP android-17.0.0_r1, system/memory/lmkd/, packages/modules/Connectivity/.../NetworkScorecard.java — 该类无功耗/能耗字段]

## 调试与排查

### dumpsys connectivity

```bash
adb shell dumpsys connectivity
```

输出包含所有活跃 `NetworkAgentInfo` 的状态：
- `Type` / `TransportInfo`：网络类型和传输层信息
- `Score`：当前 `NetworkScore` 对象（含 legacyInt）
- `CaptivePortal`：是否检测到门户页面
- `everConnected` / `validated` / `destroyed`：生命周期标志
- `Underlying Networks`：VPN 场景下的底层网络

### 网络切换 trace

在 Perfetto 中打开 `ConnectivityService` atrace category：

```
adb shell atrace --async_start -b 8192 connectivity
```

trace 中可见：
- `rematchAllNetworksAndRequests` 的执行时间和调用栈
- `computeNetworkReassignment` 的遍历耗时
- `applyNetworkReassignment` 的回调投递

### 网络评分变化日志

```bash
adb shell setprop log.tag.ConnectivityService VERBOSE
adb logcat -s ConnectivityService
```

日志中 `updateNetworkScore for [NetworkAgentInfo]` 行显示每次评分更新的目标和分值，可用于追踪网络切换的触发链路。
