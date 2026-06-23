---
title: "Android 17 NetworkStatsService 与 NetworkPolicyManagerService 移动数据 quota 限速源码路径"
chapter: "24.20"
status: "draft"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [network, io, http]
---

# Android 17 NetworkStatsService 与 NetworkPolicyManagerService 移动数据 quota 限速源码路径

> **Android 17 网络配额管理深度解析**

## 1. 概述

Android 17 对移动数据配额管理进行了重要增强，主要通过 `NetworkStatsService` 和 `NetworkPolicyManagerService` 两个核心服务实现。这些服务提供了更精细的网络流量控制和配额管理机制，帮助开发者构建更智能的网络应用。

### 1.1 系统架构

Android 17 的网络配额管理采用双服务架构：

```
应用层
    ↓
NetworkPolicyManagerService (策略执行层)
    ↓
NetworkStatsService (数据采集层)
    ↓
BPF/eBPF (内核数据采集)
    ↓
netd (网络守护进程)
```

### 1.2 关键组件

- **NetworkStatsService**：负责网络流量数据的采集和统计
- **NetworkPolicyManagerService**：负责网络配额策略的执行和管理
- **BPF/eBPF**：内核层的数据采集点
- **FastDataInput**：快速数据输入接口，包含 4 个 BpfMap
- **netd**：网络守护进程，执行实际的限速操作

## 2. 源码深度解析

### 2.1 NetworkStatsService 实现

#### 2.1.1 核心数据结构

```cpp
// frameworks/base/services/core/java/com/android/server/net/NetworkStatsService.java
public class NetworkStatsService extends INetworkStatsService.Stub {
    // BPF 数据映射
    private BpfMap mUidRxBytesMap;
    private BpfMap mUidTxBytesMap;
    private BpfMap mUidPacketsMap;
    private BpfMap mUidTcpPacketsMap;
    
    // 配额管理
    private final NetworkQuotaManager mQuotaManager;
    
    // 统计数据快照
    private final ConcurrentHashMap<Integer, NetworkStatsSnapshot> mStatsSnapshots;
    
    @Override
    public NetworkStatsSummary getNetworkStatsSummary(int networkType, String subscriberId) {
        // 使用 FastDataInput 获取实时统计
        FastDataInput input = new FastDataInput();
        mUidRxBytesMap.read(input);
        
        NetworkStatsSummary summary = new NetworkStatsSummary();
        while (input.hasNext()) {
            int uid = input.readInt();
            long rxBytes = input.readLong();
            long txBytes = input.readLong();
            
            summary.addStats(uid, rxBytes, txBytes);
        }
        
        return summary;
    }
}
```

#### 2.1.2 BPF 数据采集

Android 17 使用 eBPF 技术进行高效的流量采集：

```cpp
// system/netd/server/bpf/NetworkStatsBpfHandler.cpp
class NetworkStatsBpfHandler {
public:
    void initBpfMaps() {
        // 初始化 4 个 BPF 映射
        mUidRxBytesMap = BpfMap(BPF_MAP_TYPE_HASH, 
                               "uid_rx_bytes", 
                               sizeof(UidKey), 
                               sizeof(uint64_t), 
                               MAX_UIDS);
        
        mUidTxBytesMap = BpfMap(BPF_MAP_TYPE_HASH, 
                               "uid_tx_bytes", 
                               sizeof(UidKey), 
                               sizeof(uint64_t), 
                               MAX_UIDS);
        
        mUidPacketsMap = BpfMap(BPF_MAP_TYPE_HASH, 
                              "uid_packets", 
                              sizeof(UidKey), 
                              sizeof(uint64_t), 
                              MAX_UIDS);
        
        mUidTcpPacketsMap = BpfMap(BPF_MAP_TYPE_HASH, 
                                  "uid_tcp_packets", 
                                  sizeof(UidKey), 
                                  sizeof(uint64_t), 
                                  MAX_UIDS);
    }
    
    void updateNetworkStats(int uid, int64_t rxBytes, int64_t txBytes) {
        UidKey key = {.uid = uid};
        
        // 更新各个统计映射
        mUidRxBytesMap.update(key, rxBytes);
        mUidTxBytesMap.update(key, txBytes);
        mUidPacketsMap.update(key, rxBytes + txBytes);
    }
};
```

### 2.2 NetworkPolicyManagerService 实现

#### 2.2.1 配额管理策略

```java
// frameworks/base/services/core/java/com/android/server/net/NetworkPolicyManagerService.java
public class NetworkPolicyManagerService extends INetworkPolicyManager.Stub {
    private final NetworkQuotaManager mQuotaManager;
    private final NetworkPolicyMonitor mPolicyMonitor;
    
    @Override
    public void enforceNetworkQuota(NetworkTemplate template, long quotaBytes) {
        // 检查配额是否超限
        long usedBytes = mQuotaManager.getUsedBytes(template);
        
        if (usedBytes >= quotaBytes) {
            // 触发配额超限处理
            handleQuotaExceeded(template, quotaBytes);
        }
    }
    
    private void handleQuotaExceeded(NetworkTemplate template, long quotaBytes) {
        // 1. 通知应用层
        notifyQuotaExceeded(template);
        
        // 2. 执行限速策略
        enforceRateLimiting(template);
        
        // 3. 记录日志
        logQuotaExceededEvent(template, quotaBytes);
    }
    
    private void enforceRateLimiting(NetworkTemplate template) {
        // 调用 netd 执行限速
        try {
            IBinder netdService = getNetdService();
            INetdService netd = INetdService.Stub.asInterface(netdService);
            
            // 设置限速规则
            netd.setNetworkQuota(template, 0); // 0 表示禁止访问
        } catch (RemoteException e) {
            Log.e(TAG, "Failed to enforce rate limiting", e);
        }
    }
}
```

#### 2.2.2 配额超限处理链路

```java
// 配额超限处理流程
public class QuotaExceededHandler {
    public void onQuotaExceeded(NetworkTemplate template) {
        // 链式处理：BPF → netd → AlertObserver → firewall chain
        
        // 1. 更新 BPF 标记
        markQuotaExceededInBpf(template);
        
        // 2. 通知 netd
        notifyNetdOfQuotaExceeded(template);
        
        // 3. 发送 AlertObserver 事件
        sendAlertObserverEvent(template);
        
        // 4. 更新防火墙规则
        updateFirewallChain(template);
    }
    
    private void markQuotaExceededInBpf(NetworkTemplate template) {
        // 在 BPF 中标记配额超限状态
        UidKey key = getUidKeyForTemplate(template);
        mQuotaExceededMap.update(key, 1);
    }
    
    private void notifyNetdOfQuotaExceeded(NetworkTemplate template) {
        // 通知 netd 处理配额超限
        try {
            IBinder netdService = getNetdService();
            INetdService netd = INetdService.Stub.asInterface(netdService);
            
            // 添加配额超限规则
            netd.addNetworkQuotaRule(template, QUOTA_EXCEEDED_ACTION);
        } catch (RemoteException e) {
            Log.e(TAG, "Failed to notify netd of quota exceeded", e);
        }
    }
    
    private void sendAlertObserverEvent(NetworkTemplate template) {
        // 发送 AlertObserver 事件
        AlertManager alertManager = (AlertManager) mContext.getSystemService(
            Context.ALERT_SERVICE);
        
        if (alertManager != null) {
            AlertEntry entry = new AlertEntry();
            entry.setType(AlertEntry.TYPE_NETWORK_QUOTA_EXCEEDED);
            entry.setNetworkTemplate(template);
            alertManager.postAlert(entry);
        }
    }
    
    private void updateFirewallChain(NetworkTemplate template) {
        // 更新防火墙规则链
        try {
            IBinder netdService = getNetdService();
            INetdService netd = INetdService.Stub.asInterface(netdService);
            
            // 添加防火墙规则
            netd.addFirewallRule(FIREWALL_CHAIN_QUOTA, 
                               getFirewallRuleForTemplate(template), 
                               true);
        } catch (RemoteException e) {
            Log.e(TAG, "Failed to update firewall chain", e);
        }
    }
}
```

### 2.3 BPF 内核层实现

#### 2.3.1 FastDataInput 数据结构

```cpp
// system/netd/server/bpf/FastDataInput.cpp
class FastDataInput {
public:
    // 读取 BPF 数据
    template<typename T>
    T read() {
        T value;
        if (!mBuffer.empty()) {
            value = *reinterpret_cast<T*>(mBuffer.data());
            mBuffer.remove_prefix(sizeof(T));
        }
        return value;
    }
    
    bool hasNext() const {
        return !mBuffer.empty();
    }
    
    void readFromMap(const BpfMap& map) {
        size_t key_size, value_size;
        key_size = map.getKeySize();
        value_size = map.getValueSize();
        
        // 优化读取性能
        size_t total_size = key_size + value_size;
        mBuffer.reserve(total_size);
        
        // 批量读取数据
        map.forEachEntry([this, key_size, value_size](const void* key, const void* value) {
            mBuffer.append(reinterpret_cast<const char*>(key), key_size);
            mBuffer.append(reinterpret_cast<const char*>(value), value_size);
        });
    }
    
private:
    std::string_view mBuffer;
};

// BPF 数据采集 XDP 程序
struct quota_prog {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, MAX_UIDS);
    __type(key, UidKey);
    __type(value, QuotaState);
    __uint(pinning, LIBBPF_PIN_BY_NAME);
} quota_state SEC(".maps");

// 网络数据采集程序
SEC("xdp")
int network_quota_monitor(struct xdp_md *ctx) {
    // 获取数据包信息
    struct packet_info pkt = {};
    if (bpf_xdp_adjust_meta(ctx, 0) < 0) {
        return XDP_PASS;
    }
    
    if (bpf_load_bytes(ctx, 0, &pkt, sizeof(pkt)) < 0) {
        return XDP_PASS;
    }
    
    // 获取 UID
    int uid = get_packet_uid(&pkt);
    if (uid < 0) {
        return XDP_PASS;
    }
    
    // 更新网络统计
    UidKey key = {.uid = uid};
    
    // 更新接收和发送字节数
    uint64_t rx_bytes = pkt.len;
    uint64_t tx_bytes = (pkt.flags & PKT_FLAG_TX) ? pkt.len : 0;
    
    bpf_map_update_elem(&quota_state, &key, &rx_bytes, BPF_ANY);
    
    return XDP_PASS;
}
```

## 3. 配额限速实现

### 3.1 配额限速策略

Android 17 实现了多层次的配额限速策略：

```java
// 配额限速策略实现
public class NetworkQuotaEnforcer {
    public enum QuotaAction {
        NONE,                // 无限制
        WARNING,             // 警告
        THROTTLE,            // 限速
        BLOCK                // 阻断
    }
    
    public static QuotaAction getQuotaAction(NetworkTemplate template, long usedBytes, long quotaBytes) {
        double usageRatio = (double) usedBytes / quotaBytes;
        
        if (usageRatio >= 1.0) {
            return QuotaAction.BLOCK;
        } else if (usageRatio >= 0.9) {
            return QuotaAction.THROTTLE;
        } else if (usageRatio >= 0.8) {
            return QuotaAction.WARNING;
        } else {
            return QuotaAction.NONE;
        }
    }
    
    public void applyQuotaAction(NetworkTemplate template, QuotaAction action) {
        switch (action) {
            case BLOCK:
                applyBlockingPolicy(template);
                break;
            case THROTTLE:
                applyThrottlingPolicy(template);
                break;
            case WARNING:
                applyWarningPolicy(template);
                break;
            case NONE:
                clearQuotaPolicy(template);
                break;
        }
    }
    
    private void applyBlockingPolicy(NetworkTemplate template) {
        // 阻断策略：禁止网络访问
        try {
            IBinder netdService = getNetdService();
            INetdService netd = INetdService.Stub.asInterface(netdService);
            
            // 设置配额为 0，表示禁止访问
            netd.setNetworkQuota(template, 0);
            
            // 添加防火墙规则
            netd.addFirewallRule(FIREWALL_CHAIN_QUOTA, 
                               getFirewallRuleForTemplate(template), 
                               true);
        } catch (RemoteException e) {
            Log.e(TAG, "Failed to apply blocking policy", e);
        }
    }
    
    private void applyThrottlingPolicy(NetworkTemplate template) {
        // 限速策略：降低带宽
        try {
            IBinder netdService = getNetdService();
            INetdService netd = INetdService.Stub.asInterface(netdService);
            
            // 设置限速为 50% 带宽
            long limitBytes = getThrottlingLimit(template);
            netd.setNetworkQuota(template, limitBytes);
        } catch (RemoteException e) {
            Log.e(TAG, "Failed to apply throttling policy", e);
        }
    }
}
```

### 3.2 AlertObserver 通知机制

```java
// AlertObserver 实现
public class NetworkAlertObserver extends AlertObserver {
    @Override
    public void onAlertPosted(AlertEntry entry) {
        if (entry.getType() == AlertEntry.TYPE_NETWORK_QUOTA_EXCEEDED) {
            handleQuotaExceededAlert(entry);
        }
    }
    
    private void handleQuotaExceededAlert(AlertEntry entry) {
        NetworkTemplate template = entry.getNetworkTemplate();
        
        // 1. 通知系统服务
        notifySystemService(template);
        
        // 2. 发送系统通知
        sendSystemNotification(template);
        
        // 3. 记录事件
        logQuotaExceededEvent(template);
        
        // 4. 执行后续处理
        postQuotaExceededJob(template);
    }
    
    private void notifySystemService(NetworkTemplate template) {
        try {
            IBinder service = ServiceManager.getService("network_policy");
            INetworkPolicyManager serviceImpl = INetworkPolicyManager.Stub.asInterface(service);
            
            serviceImpl.onQuotaExceeded(template);
        } catch (RemoteException e) {
            Log.e(TAG, "Failed to notify system service", e);
        }
    }
    
    private void sendSystemNotification(NetworkTemplate template) {
        Notification.Builder builder = new Notification.Builder(mContext)
            .setContentTitle("网络配额即将用尽")
            .setContentText(getQuotaWarningMessage(template))
            .setSmallIcon(R.drawable.ic_network_warning);
        
        NotificationManager nm = (NotificationManager) mContext.getSystemService(
            Context.NOTIFICATION_SERVICE);
        nm.notify(NETWORK_QUOTA_NOTIFICATION_ID, builder.build());
    }
}
```

### 3.3 防火墙链实现

```cpp
// netd 防火墙链实现
void FirewallController::updateQuotaFirewallChain(const NetworkTemplate& template) {
    std::string chain_name = "quota_" + template.toString();
    
    // 创建或更新防火墙链
    if (!mFirewallManager.chainExists(chain_name)) {
        mFirewallManager.createChain(chain_name);
    }
    
    // 添加基础规则
    mFirewallManager.addRule(chain_name, 
                           "INPUT -j " + chain_name);
    mFirewallManager.addRule(chain_name, 
                           "OUTPUT -j " + chain_name);
    
    // 根据配额状态添加规则
    switch (template.getQuotaState()) {
        case QuotaState::BLOCKED:
            mFirewallManager.addRule(chain_name, 
                                   "-m quota --quota 0 -j DROP");
            break;
        case QuotaState::THROTTLED:
            mFirewallManager.addRule(chain_name, 
                                   "-m limit --limit 50kb/s -j ACCEPT");
            mFirewallManager.addRule(chain_name, 
                                   "-j DROP");
            break;
        case QuotaState::WARNING:
            // 仅记录日志
            mFirewallManager.addRule(chain_name, 
                                   "-j LOG --log-prefix \"QUOTA_WARNING: \"");
            mFirewallManager.addRule(chain_name, 
                                   "-j ACCEPT");
            break;
        case QuotaState::NORMAL:
            // 正常访问
            mFirewallManager.addRule(chain_name, "-j ACCEPT");
            break;
    }
}
```

## 4. 应用集成指南

### 4.1 检查网络配额

```java
// 应用层网络配额检查
public class NetworkQuotaChecker {
    private final NetworkStatsManager mStatsManager;
    private final NetworkPolicyManager mPolicyManager;
    
    public boolean checkQuotaStatus(NetworkTemplate template) {
        try {
            // 获取已用流量
            NetworkStats stats = mStatsManager.querySummaryForNetwork(
                template.getNetworkType(), 
                template.getSubscriberId());
            
            long usedBytes = stats.getTotalBytes();
            long quotaBytes = mPolicyManager.getNetworkQuota(template);
            
            double usageRatio = (double) usedBytes / quotaBytes;
            
            return usageRatio >= 0.8; // 超过 80% 时警告
        } catch (RemoteException e) {
            Log.e(TAG, "Failed to check network quota", e);
            return false;
        }
    }
    
    public void startQuotaMonitoring(NetworkTemplate template, 
                                   QuotaCallback callback) {
        // 注册配额监控
        NetworkQuotaMonitor monitor = new NetworkQuotaMonitor(template, callback);
        monitor.startMonitoring();
    }
    
    public void requestQuotaExtension(NetworkTemplate template, 
                                    long additionalBytes) {
        try {
            // 请求配额扩展
            mPolicyManager.requestNetworkQuotaExtension(
                template, additionalBytes);
        } catch (RemoteException e) {
            Log.e(TAG, "Failed to request quota extension", e);
        }
    }
}
```

### 4.2 优化网络使用

```java
// 网络使用优化
public class NetworkOptimizer {
    private final NetworkQuotaChecker mQuotaChecker;
    
    public void optimizeNetworkUsage(Context context) {
        // 检查配额状态
        NetworkTemplate mobileTemplate = NetworkTemplate.buildTemplateMobileAll();
        boolean isQuotaCritical = mQuotaChecker.checkQuotaStatus(mobileTemplate);
        
        if (isQuotaCritical) {
            // 启用严格网络优化
            enableStrictNetworkOptimization(context);
        } else {
            // 正常网络优化
            enableNormalNetworkOptimization(context);
        }
    }
    
    private void enableStrictNetworkOptimization(Context context) {
        // 1. 降低图片质量
        reduceImageQuality(context);
        
        // 2. 禁用自动播放
        disableAutoPlay(context);
        
        // 3. 压缩视频质量
        compressVideoQuality(context);
        
        // 4. 限制后台下载
        limitBackgroundDownloads(context);
    }
    
    private void reduceImageQuality(Context context) {
        // 使用 Glide 或其他图片加载库设置低质量
        Glide.with(context)
            .setDefaultRequestOptions(new RequestOptions()
                .onlyRetrieveFromCache(true)
                .skipMemoryCache(false));
    }
    
    private void disableAutoPlay(Context context) {
        // 禁用自动播放
        VideoView videoView = findViewById(R.id.video_view);
        videoView.setMediaController(null);
    }
    
    private void compressVideoQuality(Context context) {
        // 降低视频质量
        VideoCompressor compressor = new VideoCompressor();
        compressor.setTargetBitRate(500_000); // 500kbps
        compressor.compressVideo(context, R.raw.video_input);
    }
    
    private void limitBackgroundDownloads(Context context) {
        // 限制后台下载
        DownloadManager downloadManager = 
            (DownloadManager) context.getSystemService(Context.DOWNLOAD_SERVICE);
        
        DownloadManager.Request request = new DownloadManager.Request(
            Uri.parse("http://example.com/file"));
        
        request.setAllowedNetworkTypes(
            DownloadManager.Request.NETWORK_WIFI);
        request.setAllowedOverRoaming(false);
        
        downloadManager.enqueue(request);
    }
}
```

### 4.3 配额管理 API

```java
// 配额管理 API
public class NetworkQuotaManager {
    public interface QuotaCallback {
        void onQuotaWarning(long usedBytes, long totalBytes);
        void onQuotaExceeded(long usedBytes, long totalBytes);
        void onQuotaReset();
    }
    
    public void startQuotaMonitoring(NetworkTemplate template, 
                                   QuotaCallback callback) {
        // 创建监控任务
        QuotaMonitorTask task = new QuotaMonitorTask(template, callback);
        task.execute();
    }
    
    public void pauseQuotaMonitoring(NetworkTemplate template) {
        // 暂停监控
        QuotaMonitorTask.pause(template);
    }
    
    public void setQuotaThreshold(NetworkTemplate template, 
                                double warningThreshold,
                                double exceededThreshold) {
        // 设置配额阈值
        QuotaThresholds thresholds = new QuotaThresholds();
        thresholds.warning = warningThreshold;
        thresholds.exceeded = exceededThreshold;
        
        mThresholdManager.setThresholds(template, thresholds);
    }
    
    public void requestQuotaAlerts(NetworkTemplate template) {
        // 请求配额警报
        try {
            INetworkPolicyManager service = INetworkPolicyManager.Stub.asInterface(
                ServiceManager.getService("network_policy"));
            
            service.requestQuotaAlerts(template);
        } catch (RemoteException e) {
            Log.e(TAG, "Failed to request quota alerts", e);
        }
    }
}
```

## 5. 性能优化

### 5.1 BPF 优化

```cpp
// BPF 优化策略
class BpfQuotaOptimizer {
public:
    void optimizeBpfPerformance() {
        // 1. 使用批量更新
        useBatchUpdates();
        
        // 2. 减少内存分配
        reduceMemoryAllocation();
        
        // 3. 使用无锁数据结构
        useLockFreeDataStructures();
        
        // 4. 优化数据布局
        optimizeDataLayout();
    }
    
private:
    void useBatchUpdates() {
        // 批量更新 BPF 映射
        std::vector<QuotaUpdate> updates;
        
        // 预分配内存
        updates.reserve(1000);
        
        // 批量收集更新
        for (int uid = 0; uid < MAX_UIDS; uid++) {
            QuotaUpdate update;
            update.uid = uid;
            update.rx_bytes = getRxBytesForUid(uid);
            update.tx_bytes = getTxBytesForUid(uid);
            updates.push_back(update);
        }
        
        // 批量应用更新
        applyBatchUpdates(updates);
    }
    
    void reduceMemoryAllocation() {
        // 使用内存池
        static std::vector<uint8_t> memory_pool;
        memory_pool.resize(MAX_BPF_MEMORY);
        
        // 重用内存
        for (auto& update : pending_updates) {
            if (update.needs_memory) {
                update.buffer = memory_pool.data();
            }
        }
    }
    
    void useLockFreeDataStructures() {
        // 使用原子操作
        std::atomic<uint64_t> total_bytes{0};
        
        // 无锁计数器
        auto update_counter = [](uint64_t delta) {
            total_bytes.fetch_add(delta, std::memory_order_relaxed);
        };
    }
    
    void optimizeDataLayout() {
        // 优化数据布局以提高缓存局部性
        struct alignas(64) OptimizedQuotaData {
            uint64_t rx_bytes;
            uint64_t tx_bytes;
            uint32_t uid;
            uint32_t flags;
            // 填充到缓存行大小
            uint8_t padding[24];
        };
        
        // 使用对齐的数据结构
        std::vector<OptimizedQuotaData> optimized_data;
        optimized_data.reserve(MAX_UIDS);
    }
};
```

### 5.2 用户态优化

```java
// 用户态性能优化
public class UserSpaceQuotaOptimizer {
    private final LruCache<Integer, QuotaStats> mStatsCache;
    private final ScheduledExecutorService mStatsExecutor;
    
    public UserSpaceQuotaOptimizer() {
        // 使用 LRU 缓存减少重复计算
        mStatsCache = new LruCache<>(100);
        
        // 使用调度线程池定期更新统计数据
        mStatsExecutor = Executors.newScheduledThreadPool(2);
        
        // 定期清理缓存
        mStatsExecutor.scheduleAtFixedRate(this::cleanCache, 
                                          1, 1, TimeUnit.HOURS);
    }
    
    public QuotaStats getQuotaStats(NetworkTemplate template) {
        // 检查缓存
        int cacheKey = template.hashCode();
        QuotaStats cached = mStatsCache.get(cacheKey);
        
        if (cached != null && !cached.isExpired()) {
            return cached;
        }
        
        // 计算新的统计数据
        QuotaStats stats = calculateQuotaStats(template);
        
        // 更新缓存
        mStatsCache.put(cacheKey, stats);
        
        return stats;
    }
    
    private QuotaStats calculateQuotaStats(NetworkTemplate template) {
        QuotaStats stats = new QuotaStats();
        
        // 批量获取统计数据
        NetworkStats summary = mStatsManager.querySummaryForNetwork(
            template.getNetworkType(),
            template.getSubscriberId());
        
        stats.totalBytes = summary.getTotalBytes();
        stats.totalPackets = summary.getPackets();
        stats.startTime = summary.getStartTimeStamp();
        stats.lastUpdateTime = System.currentTimeMillis();
        
        // 计算使用率
        long quota = mPolicyManager.getNetworkQuota(template);
        stats.usageRatio = (double) stats.totalBytes / quota;
        
        return stats;
    }
    
    private void cleanCache() {
        // 清理过期缓存
        mStatsExecutor.submit(() -> {
            List<Integer> keysToRemove = new ArrayList<>();
            
            for (int i = 0; i < mStatsCache.size(); i++) {
                Integer key = mStatsCache.keyAt(i);
                QuotaStats stats = mStatsCache.get(key);
                
                if (stats != null && stats.isExpired()) {
                    keysToRemove.add(key);
                }
            }
            
            for (Integer key : keysToRemove) {
                mStatsCache.remove(key);
            }
        });
    }
}
```

## 6. 监控与诊断

### 6.1 配额监控

```java
// 配额监控系统
public class QuotaMonitor {
    private final NetworkQuotaManager mQuotaManager;
    private final List<QuotaMetric> mMetrics;
    
    public void startMonitoring() {
        // 定期检查配额状态
        ScheduledExecutorService executor = Executors.newScheduledThreadPool(1);
        executor.scheduleAtFixedRate(this::checkQuotaStatus, 
                                  0, 5, TimeUnit.MINUTES);
        
        // 监控网络事件
        registerNetworkEventListener();
    }
    
    private void checkQuotaStatus() {
        for (NetworkType type : NetworkType.values()) {
            NetworkTemplate template = NetworkTemplate.buildTemplateForNetwork(type);
            
            QuotaStats stats = mQuotaManager.getQuotaStats(template);
            
            // 上报监控指标
            reportQuotaMetrics(stats);
            
            // 检查警告阈值
            checkQuotaWarnings(stats);
        }
    }
    
    private void reportQuotaMetrics(QuotaStats stats) {
        // 上报配额使用情况
        MetricBuilder builder = Metric.builder()
            .setDomain("network.quota")
            .setType(Metric.TYPE_COUNTER)
            .setTimestamp(stats.lastUpdateTime);
        
        builder.add("used_bytes", stats.totalBytes)
               .add("usage_ratio", stats.usageRatio)
               .add("packets", stats.totalPackets);
        
        // 上报到监控系统
        MetricRecorder.record(builder.build());
    }
    
    private void checkQuotaWarnings(QuotaStats stats) {
        if (stats.usageRatio > 0.9) {
            // 配额即将用完
            notifyQuotaWarning(stats);
        } else if (stats.usageRatio > 1.0) {
            // 配额已用完
            notifyQuotaExceeded(stats);
        }
    }
    
    private void notifyQuotaWarning(QuotaStats stats) {
        // 发送警告通知
        Notification notification = new NotificationCompat.Builder(mContext)
            .setContentTitle("网络配额警告")
            .setContentText(String.format("已使用 %.1f%% 的网络配额", 
                                       stats.usageRatio * 100))
            .setSmallIcon(R.drawable.ic_network_warning)
            .build();
        
        NotificationManager nm = (NotificationManager) mContext.getSystemService(
            Context.NOTIFICATION_SERVICE);
        nm.notify(QUOTA_WARNING_NOTIFICATION_ID, notification);
    }
    
    private void notifyQuotaExceeded(QuotaStats stats) {
        // 发送配额超限通知
        Notification notification = new NotificationCompat.Builder(mContext)
            .setContentTitle("网络配额已用完")
            .setContentText("网络访问已被限制")
            .setSmallIcon(R.drawable.ic_network_error)
            .build();
        
        NotificationManager nm = (NotificationManager) mContext.getSystemService(
            Context.NOTIFICATION_SERVICE);
        nm.notify(QUOTA_EXCEEDED_NOTIFICATION_ID, notification);
    }
}
```

### 6.2 诊断工具

```java
// 网络配额诊断工具
public class QuotaDiagnosticTool {
    public DiagnosticReport runDiagnostics(Context context) {
        DiagnosticReport report = new DiagnosticReport();
        
        // 检查系统服务
        checkSystemServices(report);
        
        // 检查 BPF 支持
        checkBpfSupport(report);
        
        // 检查网络策略
        checkNetworkPolicies(report);
        
        // 检查配额状态
        checkQuotaStatus(report);
        
        return report;
    }
    
    private void checkSystemServices(DiagnosticReport report) {
        try {
            // 检查 NetworkStatsService
            NetworkStatsManager statsManager = (NetworkStatsManager) 
                context.getSystemService(Context.NETWORK_STATS_SERVICE);
            if (statsManager != null) {
                report.addServiceStatus("NetworkStatsService", ServiceStatus.OK);
            } else {
                report.addServiceStatus("NetworkStatsService", ServiceStatus.NOT_AVAILABLE);
            }
            
            // 检查 NetworkPolicyManager
            NetworkPolicyManager policyManager = (NetworkPolicyManager) 
                context.getSystemService(Context.NETWORK_POLICY_SERVICE);
            if (policyManager != null) {
                report.addServiceStatus("NetworkPolicyManager", ServiceStatus.OK);
            } else {
                report.addServiceStatus("NetworkPolicyManager", ServiceStatus.NOT_AVAILABLE);
            }
        } catch (Exception e) {
            report.addError("System services check failed", e);
        }
    }
    
    private void checkBpfSupport(DiagnosticReport report) {
        try {
            // 检查 BPF 支持
            Process process = Runtime.getRuntime().exec("sysctl net.bpf.enable");
            BufferedReader reader = new BufferedReader(
                new InputStreamReader(process.getInputStream()));
            
            String line = reader.readLine();
            if (line != null && line.contains("1")) {
                report.addFeatureStatus("BPF Support", FeatureStatus.SUPPORTED);
            } else {
                report.addFeatureStatus("BPF Support", FeatureStatus.NOT_SUPPORTED);
            }
            
            int exitCode = process.waitFor();
            if (exitCode != 0) {
                report.addError("BPF support check failed", 
                             new Exception("Exit code: " + exitCode));
            }
        } catch (Exception e) {
            report.addError("BPF support check failed", e);
        }
    }
    
    private void checkNetworkPolicies(DiagnosticReport report) {
        try {
            NetworkPolicyManager policyManager = (NetworkPolicyManager) 
                context.getSystemService(Context.NETWORK_POLICY_SERVICE);
            
            for (NetworkType type : NetworkType.values()) {
                NetworkTemplate template = NetworkTemplate.buildTemplateForNetwork(type);
                long quota = policyManager.getNetworkQuota(template);
                
                report.addQuotaInfo(type, quota);
            }
        } catch (Exception e) {
            report.addError("Network policies check failed", e);
        }
    }
    
    private void checkQuotaStatus(DiagnosticReport report) {
        try {
            NetworkStatsManager statsManager = (NetworkStatsManager) 
                context.getSystemService(Context.NETWORK_STATS_SERVICE);
            
            for (NetworkType type : NetworkType.values()) {
                NetworkTemplate template = NetworkTemplate.buildTemplateForNetwork(type);
                
                NetworkStats stats = statsManager.querySummaryForNetwork(
                    type, template.getSubscriberId());
                
                long usedBytes = stats.getTotalBytes();
                long quota = getNetworkQuota(template);
                
                report.addQuotaUsage(type, usedBytes, quota);
            }
        } catch (Exception e) {
            report.addError("Quota status check failed", e);
        }
    }
}
```

## 7. 最佳实践

### 7.1 开发者指南

#### 7.1.1 配额感知设计

```java
// 配额感知设计
public class QuotaAwareApplication extends Application {
    private NetworkQuotaManager mQuotaManager;
    private NetworkOptimizer mOptimizer;
    
    @Override
    public void onCreate() {
        super.onCreate();
        
        // 初始化配额管理器
        mQuotaManager = new NetworkQuotaManager();
        mOptimizer = new NetworkOptimizer();
        
        // 注册配额监控
        mQuotaManager.startQuotaMonitoring(
            NetworkTemplate.buildTemplateMobileAll(),
            new QuotaCallback() {
                @Override
                public void onQuotaWarning(long usedBytes, long totalBytes) {
                    handleQuotaWarning(usedBytes, totalBytes);
                }
                
                @Override
                public void onQuotaExceeded(long usedBytes, long totalBytes) {
                    handleQuotaExceeded(usedBytes, totalBytes);
                }
            });
    }
    
    private void handleQuotaWarning(long usedBytes, long totalBytes) {
        // 配额警告处理
        double usageRatio = (double) usedBytes / totalBytes;
        
        if (usageRatio > 0.8) {
            // 启用严格模式
            mOptimizer.enableStrictMode(this);
        }
    }
    
    private void handleQuotaExceeded(long usedBytes, long totalBytes) {
        // 配额超限处理
        // 1. 禁用后台数据同步
        disableBackgroundSync();
        
        // 2. 降低更新频率
        reduceUpdateFrequency();
        
        // 3. 显示用户提示
        showQuotaExceededDialog();
    }
    
    private void disableBackgroundSync() {
        // 禁用后台数据同步
        ContentResolver.setMasterSyncAutomatically(false);
    }
    
    private void reduceUpdateFrequency() {
        // 降低更新频率
        UpdateScheduler scheduler = new UpdateScheduler();
        scheduler.setUpdateInterval(24 * 60 * 60 * 1000L); // 24小时
    }
    
    private void showQuotaExceededDialog() {
        // 显示配额超限对话框
        new AlertDialog.Builder(this)
            .setTitle("网络配额已用完")
            .setMessage("您的移动数据配额已用完，请连接 WiFi 或购买更多流量")
            .setPositiveButton("连接 WiFi", (dialog, which) -> {
                // 打开 WiFi 设置
                Intent intent = new Intent(Settings.ACTION_WIFI_SETTINGS);
                startActivity(intent);
            })
            .setNegativeButton("忽略", null)
            .show();
    }
}
```

#### 7.1.2 性能优化策略

```java
// 性能优化策略
public class NetworkPerformanceOptimizer {
    public void optimizeForQuota(Context context) {
        // 根据配额状态优化性能
        NetworkQuotaChecker checker = new NetworkQuotaChecker();
        boolean isQuotaCritical = checker.isQuotaCritical();
        
        if (isQuotaCritical) {
            applyCriticalQuotaOptimizations(context);
        } else {
            applyNormalOptimizations(context);
        }
    }
    
    private void applyCriticalQuotaOptimizations(Context context) {
        // 严格优化策略
        // 1. 图片加载优化
        optimizeImageLoading(context);
        
        // 2. 视频播放优化
        optimizeVideoPlayback(context);
        
        // 3. 网络请求优化
        optimizeNetworkRequests(context);
        
        // 4. 缓存策略优化
        optimizeCaching(context);
    }
    
    private void optimizeImageLoading(Context context) {
        // 使用低质量图片加载
        RequestOptions options = new RequestOptions()
            .onlyRetrieveFromCache(true)
            .skipMemoryCache(false)
            .diskCacheStrategy(DiskCacheStrategy.NONE);
        
        Glide.with(context)
            .setDefaultRequestOptions(options);
    }
    
    private void optimizeVideoPlayback(Context context) {
        // 降低视频质量
        ExoPlayer player = new ExoPlayer.Builder(context).build();
        
        MediaItem mediaItem = MediaItem.fromUri(Uri.parse("http://example.com/video.mp4"));
        
        player.setMediaItem(mediaItem);
        player.prepare();
        
        // 设置低比特率
        player.setVideoScalingMode(ExoPlayer.VIDEO_SCALING_MODE_SCALE_TO_FIT_WITH_CROPPING);
    }
    
    private void optimizeNetworkRequests(Context context) {
        // 优化网络请求
        OkHttpClient client = new OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(10, TimeUnit.SECONDS)
            .writeTimeout(10, TimeUnit.SECONDS)
            .addInterceptor(new NetworkQuotaInterceptor())
            .build();
    }
    
    private void optimizeCaching(Context context) {
        // 优化缓存策略
        Cache cache = new Cache(context.getCacheDir(), 10 * 1024 * 1024); // 10MB
        
        OkHttpClient client = new OkHttpClient.Builder()
            .cache(cache)
            .addInterceptor(new CacheInterceptor())
            .build();
    }
}
```

### 7.2 测试策略

#### 7.2.1 配额测试

```java
// 配额测试
public class QuotaTestRunner {
    public void runQuotaTests() {
        // 1. 基本配额功能测试
        testBasicQuotaFunctionality();
        
        // 2. 配额超限处理测试
        testQuotaExceededHandling();
        
        // 3. 配额恢复测试
        testQuotaRecovery();
        
        // 4. 性能影响测试
        testPerformanceImpact();
    }
    
    private void testBasicQuotaFunctionality() {
        // 测试基本配额功能
        NetworkTemplate template = NetworkTemplate.buildTemplateMobileAll();
        
        // 设置配额
        long quota = 100 * 1024 * 1024; // 100MB
        setNetworkQuota(template, quota);
        
        // 模拟网络使用
        simulateNetworkUsage(template, 50 * 1024 * 1024); // 50MB
        
        // 验证配额状态
        NetworkStats stats = getNetworkStats(template);
        assertEquals(50 * 1024 * 1024, stats.getTotalBytes());
    }
    
    private void testQuotaExceededHandling() {
        // 测试配额超限处理
        NetworkTemplate template = NetworkTemplate.buildTemplateMobileAll();
        
        // 设置小配额
        long quota = 1 * 1024 * 1024; // 1MB
        setNetworkQuota(template, quota);
        
        // 模拟网络使用
        simulateNetworkUsage(template, 2 * 1024 * 1024); // 2MB
        
        // 验证访问被阻止
        boolean accessBlocked = isNetworkAccessBlocked(template);
        assertTrue(accessBlocked);
    }
    
    private void testQuotaRecovery() {
        // 测试配额恢复
        NetworkTemplate template = NetworkTemplate.buildTemplateMobileAll();
        
        // 设置配额
        long quota = 100 * 1024 * 1024; // 100MB
        setNetworkQuota(template, quota);
        
        // 使用部分配额
        simulateNetworkUsage(template, 80 * 1024 * 1024); // 80MB
        
        // 重置配额
        resetNetworkQuota(template);
        
        // 验证配额重置
        NetworkStats stats = getNetworkStats(template);
        assertEquals(0, stats.getTotalBytes());
    }
    
    private void testPerformanceImpact() {
        // 测试性能影响
        long startTime = System.currentTimeMillis();
        
        // 执行网络操作
        performNetworkOperations();
        
        long endTime = System.currentTimeMillis();
        long duration = endTime - startTime;
        
        // 验证性能影响在可接受范围内
        assertTrue(duration < 1000); // 应该在 1 秒内完成
    }
}
```

#### 7.2.2 压力测试

```java
// 压力测试
public class QuotaStressTest {
    public void runStressTests() {
        // 1. 高频配额检查测试
        testHighFrequencyQuotaChecks();
        
        // 2. 大量网络请求测试
        testHighVolumeNetworkRequests();
        
        // 3. 内存压力测试
        testMemoryPressure();
        
        // 4. 并发访问测试
        testConcurrentAccess();
    }
    
    private void testHighFrequencyQuotaChecks() {
        // 测试高频配额检查的性能影响
        NetworkTemplate template = NetworkTemplate.buildTemplateMobileAll();
        
        long startTime = System.currentTimeMillis();
        
        // 执行 1000 次配额检查
        for (int i = 0; i < 1000; i++) {
            checkQuotaStatus(template);
        }
        
        long endTime = System.currentTimeMillis();
        long duration = endTime - startTime;
        
        // 验证性能影响
        assertTrue(duration < 5000); // 应该在 5 秒内完成
    }
    
    private void testHighVolumeNetworkRequests() {
        // 测试大量网络请求的处理能力
        NetworkTemplate template = NetworkTemplate.buildTemplateMobileAll();
        
        // 设置大配额
        long quota = 1000 * 1024 * 1024; // 1GB
        setNetworkQuota(template, quota);
        
        long startTime = System.currentTimeMillis();
        
        // 执行 1000 次网络请求
        for (int i = 0; i < 1000; i++) {
            performNetworkRequest(template);
        }
        
        long endTime = System.currentTimeMillis();
        long duration = endTime - startTime;
        
        // 验证性能影响
        assertTrue(duration < 10000); // 应该在 10 秒内完成
    }
    
    private void testMemoryPressure() {
        // 测试内存压力下的表现
        NetworkTemplate template = NetworkTemplate.buildTemplateMobileAll();
        
        // 模拟内存压力
        simulateMemoryPressure();
        
        // 执行配额检查
        boolean success = checkQuotaStatus(template);
        
        // 验证仍然能够正常工作
        assertTrue(success);
    }
    
    private void testConcurrentAccess() {
        // 测试并发访问
        NetworkTemplate template = NetworkTemplate.buildTemplateMobileAll();
        
        ExecutorService executor = Executors.newFixedThreadPool(10);
        
        // 提交 100 个并发任务
        List<Future<?>> futures = new ArrayList<>();
        
        for (int i = 0; i < 100; i++) {
            Future<?> future = executor.submit(() -> {
                performQuotaOperation(template);
            });
            futures.add(future);
        }
        
        // 等待所有任务完成
        for (Future<?> future : futures) {
            try {
                future.get();
            } catch (Exception e) {
                fail("Concurrent access failed: " + e.getMessage());
            }
        }
        
        executor.shutdown();
    }
}
```

## 8. 总结

Android 17 的 NetworkStatsService 和 NetworkPolicyManagerService 为网络配额管理提供了强大的基础设施。通过深入理解这些服务的实现机制，开发者可以构建更智能、更高效的网络应用。

### 8.1 关键要点

1. **双服务架构**：NetworkStatsService 负责数据采集，NetworkPolicyManagerService 负责策略执行
2. **BPF 高效采集**：使用 eBPF 技术进行高效的流量数据采集
3. **多层次限速**：支持警告、限速、阻断等多种配额管理策略
4. **AlertObserver 通知**：提供及时的用户通知机制
5. **防火墙链集成**：与 netd 的防火墙系统集成实现精确控制

### 8.2 实施建议

1. **配置配额监控**：为应用实现配额状态监控和预警机制
2. **优化网络使用**：根据配额状态智能调整网络使用策略
3. **提供用户反馈**：及时向用户提供配额使用情况和预警
4. **实施压力测试**：确保在高负载情况下配额管理的稳定性
5. **建立监控体系**：建立完善的配额使用监控和分析体系

通过系统的配额管理，开发者可以更好地保护用户利益，同时提供更好的用户体验。