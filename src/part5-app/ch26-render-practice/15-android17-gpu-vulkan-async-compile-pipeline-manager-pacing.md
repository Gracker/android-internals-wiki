# Android 17 GPU Vulkan 异步编译管线管理器调度策略源码实现

> **Android 17 GPU 渲染管线异步编译优化详解**

## 1. 概述

Android 17 在 GPU 渲染管线管理方面引入了重大优化，通过 Vulkan 异步编译管线管理器实现了更高效的调度策略。这一机制显著提升了 GPU 渲染性能，特别是在复杂图形处理和游戏场景中。

### 1.1 架构演进

Android 17 的 GPU 渲染管线管理经历了重要演进：

```
Android 15: 同步管线编译
    ↓
Android 16: 基础异步支持
    ↓
Android 17: 完整异步管线管理器 + 调度策略
```

### 1.2 关键组件

- **PipelineManager** - 管线管理器
- **AsyncCompiler** - 异步编译器
- **PipelinePacer** - 管线调度器
- **PipelineCache** - 管线缓存
- **RenderThread** - 渲染线程池

## 2. 源码架构解析

### 2.1 PipelineManager 核心实现

```cpp
// frameworks/native/opengl/libs/RenderEngine/src/PipelineManager.cpp
class PipelineManager {
public:
    PipelineManager(IGpuService* gpuService) 
        : mGpuService(gpuService)
        , mAsyncCompiler(std::make_unique<AsyncCompiler>())
        , mPipelinePacer(std::make_unique<PipelinePacer>())
        , mPipelineCache(std::make_unique<PipelineCache>())
    {
        // 初始化各个组件
        initializeComponents();
    }
    
    ~PipelineManager() {
        shutdown();
    }
    
    // 异步管线编译
    bool compilePipelineAsync(const PipelineDesc& desc, 
                            PipelineCallback callback) {
        // 验证管线描述
        if (!validatePipelineDesc(desc)) {
            return false;
        }
        
        // 检查缓存
        PipelineHandle cachedHandle;
        if (mPipelineCache->find(desc, cachedHandle)) {
            callback(cachedHandle, true);
            return true;
        }
        
        // 提交到异步编译器
        mAsyncCompiler->submit(desc, std::move(callback));
        return true;
    }
    
    // 同步管线获取
    PipelineHandle getPipelineSync(const PipelineDesc& desc) {
        // 首先尝试从缓存获取
        PipelineHandle handle;
        if (mPipelineCache->find(desc, handle)) {
            return handle;
        }
        
        // 缓存未命中，需要同步编译
        return compilePipelineSync(desc);
    }
    
private:
    void initializeComponents() {
        // 初始化异步编译器
        mAsyncCompiler->initialize(mGpuService);
        
        // 初始化管线调度器
        mPipelinePacer->initialize();
        
        // 初始化管线缓存
        mPipelineCache->initialize();
        
        // 启动后台工作线程
        startBackgroundThreads();
    }
    
    void startBackgroundThreads() {
        // 编译线程
        mCompilerThread = std::thread([this]() {
            mAsyncCompiler->processQueue();
        });
        
        // 缓存管理线程
        mCacheThread = std::thread([this]() {
            mPipelineCache->processCacheEviction();
        });
    }
    
    PipelineHandle compilePipelineSync(const PipelineDesc& desc) {
        // 同步编译管线
        PipelineHandle handle = mGpuService->compilePipeline(desc);
        
        // 添加到缓存
        mPipelineCache->add(desc, handle);
        
        return handle;
    }
    
    std::unique_ptr<IGpuService> mGpuService;
    std::unique_ptr<AsyncCompiler> mAsyncCompiler;
    std::unique_ptr<PipelinePacer> mPipelinePacer;
    std::unique_ptr<PipelineCache> mPipelineCache;
    
    std::thread mCompilerThread;
    std::thread mCacheThread;
};

// Pipeline 描述符结构
struct PipelineDesc {
    uint32_t shaderCount;
    const ShaderDesc* shaders;
    uint32_t uniformCount;
    const UniformDesc* uniforms;
    uint32_t attributeCount;
    const AttributeDesc* attributes;
    uint32_t renderPassCount;
    const RenderPassDesc* renderPasses;
    
    // 哈希计算
    size_t hash() const {
        size_t seed = 0;
        boost::hash_combine(seed, shaderCount);
        for (uint32_t i = 0; i < shaderCount; ++i) {
            boost::hash_combine(seed, shaders[i].hash());
        }
        boost::hash_combine(seed, uniformCount);
        for (uint32_t i = 0; i < uniformCount; ++i) {
            boost::hash_combine(seed, uniforms[i].hash());
        }
        boost::hash_combine(seed, attributeCount);
        for (uint32_t i = 0; i < attributeCount; ++i) {
            boost::hash_combine(seed, attributes[i].hash());
        }
        boost::hash_combine(seed, renderPassCount);
        for (uint32_t i = 0; i < renderPassCount; ++i) {
            boost::hash_combine(seed, renderPasses[i].hash());
        }
        return seed;
    }
    
    bool operator==(const PipelineDesc& other) const {
        return shaderCount == other.shaderCount &&
               uniformCount == other.uniformCount &&
               attributeCount == other.attributeCount &&
               renderPassCount == other.renderPassCount &&
               std::equal(shaders, shaders + shaderCount, other.shaders) &&
               std::equal(uniforms, uniforms + uniformCount, other.uniforms) &&
               std::equal(attributes, attributes + attributeCount, other.attributes) &&
               std::equal(renderPasses, renderPasses + renderPassCount, other.renderPasses);
    }
};
```

### 2.2 AsyncCompiler 异步编译器

```cpp
// frameworks/native/opengl/libs/RenderEngine/src/AsyncCompiler.cpp
class AsyncCompiler {
public:
    AsyncCompiler() {
        // 初始化工作线程池
        mThreadPool = std::make_unique<ThreadPool>(
            std::thread::hardware_concurrency(),
            "AsyncCompiler");
        
        // 初始化结果队列
        mResultQueue = std::make_unique<LockFreeQueue<CompilerResult>>();
        
        // 启动结果处理线程
        mResultThread = std::thread([this]() {
            processResults();
        });
    }
    
    ~AsyncCompiler() {
        shutdown();
    }
    
    void submit(const PipelineDesc& desc, PipelineCallback callback) {
        // 创建编译任务
        auto task = std::make_shared<CompilerTask>();
        task->desc = desc;
        task->callback = std::move(callback);
        task->submissionTime = std::chrono::steady_clock::now();
        
        // 根据优先级选择队列
        auto& queue = selectQueue(desc.priority);
        
        // 提交到线程池
        mThreadPool->submit([this, task]() {
            compileTask(task);
        });
        
        // 记录任务信息
        mTaskMetrics.recordSubmission(desc.priority);
    }
    
    void processQueue() {
        while (!mShutdown) {
            // 处理多个队列
            for (auto& queue : mPriorityQueues) {
                processQueue(queue);
            }
            
            // 短暂休眠
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
    }
    
private:
    struct CompilerTask {
        PipelineDesc desc;
        PipelineCallback callback;
        std::chrono::steady_clock::time_point submissionTime;
        std::chrono::steady_clock::time_point startTime;
        std::chrono::steady_clock::time_point endTime;
        uint32_t retryCount;
        bool completed;
    };
    
    struct CompilerResult {
        PipelineDesc desc;
        PipelineHandle handle;
        bool success;
        std::chrono::steady_clock::time_point submissionTime;
        std::chrono::steady_clock::time_point completionTime;
        uint32_t retryCount;
    };
    
    void compileTask(std::shared_ptr<CompilerTask> task) {
        // 记录开始时间
        task->startTime = std::chrono::steady_clock::now();
        
        // 执行管线编译
        bool success = false;
        PipelineHandle handle;
        
        try {
            // 尝试编译
            handle = mGpuService->compilePipeline(task->desc);
            success = true;
        } catch (const GpuException& e) {
            // 编译失败，重试逻辑
            if (task->retryCount < MAX_RETRY_COUNT) {
                task->retryCount++;
                mThreadPool->submit([this, task]() {
                    compileTask(task);
                });
                return;
            }
        }
        
        // 创建结果
        CompilerResult result;
        result.desc = task->desc;
        result.handle = handle;
        result.success = success;
        result.submissionTime = task->submissionTime;
        result.completionTime = std::chrono::steady_clock::now();
        result.retryCount = task->retryCount;
        
        // 添加到结果队列
        mResultQueue->push(result);
        
        // 记录完成时间
        task->endTime = std::chrono::steady_clock::now();
        task->completed = true;
        
        // 更新统计信息
        mTaskMetrics.recordCompletion(task->desc.priority, 
                                     task->endTime - task->startTime,
                                     task->retryCount);
    }
    
    void processResults() {
        while (!mShutdown) {
            // 从结果队列取出结果
            CompilerResult result;
            if (mResultQueue->pop(result)) {
                // 调用回调
                if (result.success) {
                    result.callback(result.handle, true);
                } else {
                    result.callback(PipelineHandle{}, false);
                }
                
                // 记录性能指标
                mPerformanceMetrics.recordCompilationResult(result);
            } else {
                // 队列为空，短暂休眠
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
            }
        }
    }
    
    LockFreeQueue<CompilerTask>& selectQueue(Priority priority) {
        switch (priority) {
            case Priority::HIGH:
                return mPriorityQueues[0];
            case Priority::NORMAL:
                return mPriorityQueues[1];
            case Priority::LOW:
                return mPriorityQueues[2];
            default:
                return mPriorityQueues[1];
        }
    }
    
    void processQueue(LockFreeQueue<CompilerTask>& queue) {
        // 处理队列中的任务
        while (!queue.empty()) {
            std::shared_ptr<CompilerTask> task;
            if (queue.pop(task)) {
                compileTask(task);
            } else {
                break;
            }
        }
    }
    
    std::unique_ptr<ThreadPool> mThreadPool;
    std::unique_ptr<LockFreeQueue<CompilerResult>> mResultQueue;
    std::vector<LockFreeQueue<CompilerTask>> mPriorityQueues;
    std::thread mResultThread;
    
    IGpuService* mGpuService;
    CompilerMetrics mTaskMetrics;
    PerformanceMetrics mPerformanceMetrics;
    
    bool mShutdown = false;
};
```

### 2.3 PipelinePacer 管线调度器

```cpp
// frameworks/native/opengl/libs/RenderEngine/src/PipelinePacer.cpp
class PipelinePacer {
public:
    PipelinePacer() {
        // 初始化调度参数
        mFrameTimeBudget = 16.0f; // 60fps, 16ms per frame
        mCompileTimeBudget = 4.0f; // 4ms for compilation per frame
        mMaxPendingCompiles = 10;
        
        // 启动调度线程
        mPacerThread = std::thread([this]() {
            runPacerLoop();
        });
    }
    
    ~PipelinePacer() {
        shutdown();
    }
    
    bool canCompileNow(const PipelineDesc& desc) {
        std::lock_guard<std::mutex> lock(mMutex);
        
        // 检查当前帧时间预算
        float currentTime = getCurrentTime();
        float frameTime = currentTime - mLastFrameTime;
        
        if (frameTime > mFrameTimeBudget) {
            // 当前帧已超时，不允许新编译
            return false;
        }
        
        // 检查编译时间预算
        float compileTime = getPendingCompileTime();
        if (compileTime > mCompileTimeBudget) {
            // 编译时间预算已用完
            return false;
        }
        
        // 检查待编译队列长度
        if (mPendingCompiles.size() >= mMaxPendingCompiles) {
            // 待编译队列已满
            return false;
        }
        
        return true;
    }
    
    void scheduleCompile(const PipelineDesc& desc, 
                        std::function<void(PipelineHandle)> callback) {
        std::lock_guard<std::mutex> lock(mMutex);
        
        // 创建调度任务
        PacerTask task;
        task.desc = desc;
        task.callback = callback;
        task.priority = desc.priority;
        task.submissionTime = std::chrono::steady_clock::now();
        
        // 根据优先级插入到调度队列
        insertByPriority(task);
        
        // 更新统计信息
        mScheduleMetrics.recordSubmission(task.priority);
    }
    
    void updateFrameMetrics(float frameTime) {
        std::lock_guard<std::mutex> lock(mMutex);
        
        mFrameMetrics.recordFrameTime(frameTime);
        
        // 更新帧时间预算
        updateFrameBudget(frameTime);
        
        // 检查是否需要调整编译策略
        adjustCompileStrategy(frameTime);
    }
    
private:
    struct PacerTask {
        PipelineDesc desc;
        std::function<void(PipelineHandle)> callback;
        Priority priority;
        std::chrono::steady_clock::time_point submissionTime;
        std::chrono::steady_clock::time_point scheduledTime;
    };
    
    void runPacerLoop() {
        while (!mShutdown) {
            // 更新调度状态
            updatePacerState();
            
            // 处理调度队列
            processScheduleQueue();
            
            // 动态调整参数
            adjustParameters();
            
            // 短暂休眠
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
    }
    
    void updatePacerState() {
        // 获取当前时间
        float currentTime = getCurrentTime();
        
        // 更新帧时间统计
        float frameTime = currentTime - mLastFrameTime;
        updateFrameMetrics(frameTime);
        
        // 检查帧率稳定性
        if (frameTime > mFrameTimeBudget * 1.5f) {
            // 帧率不稳定，降低编译优先级
            mPacerState = PacerState::CONSERVATIVE;
        } else if (frameTime < mFrameTimeBudget * 0.8f) {
            // 帧率良好，可以提高编译优先级
            mPacerState = PacerState::AGGRESSIVE;
        } else {
            // 帧率正常
            mPacerState = PacerState::NORMAL;
        }
    }
    
    void processScheduleQueue() {
        std::lock_guard<std::mutex> lock(mMutex);
        
        // 根据当前状态决定是否执行编译
        if (mPacerState == PacerState::AGGRESSIVE && !mScheduleQueue.empty()) {
            // 积极模式，执行高优先级编译
            executeHighPriorityCompiles();
        } else if (mPacerState == PacerState::NORMAL && !mScheduleQueue.empty()) {
            // 正常模式，执行中等优先级编译
            executeNormalPriorityCompiles();
        } else if (mPacerState == PacerState::CONSERVATIVE && !mScheduleQueue.empty()) {
            // 保守模式，仅执行紧急编译
            executeEmergencyCompiles();
        }
    }
    
    void executeHighPriorityCompiles() {
        // 执行高优先级编译
        while (!mScheduleQueue.empty() && 
               mScheduleQueue.top().priority == Priority::HIGH) {
            PacerTask task = mScheduleQueue.top();
            mScheduleQueue.pop();
            
            // 执行编译
            task.callback(task.desc);
            
            // 记录执行时间
            auto executionTime = std::chrono::steady_clock::now() - task.scheduledTime;
            mExecutionMetrics.recordExecutionTime(task.priority, 
                                                 std::chrono::duration_cast<std::chrono::microseconds>(executionTime));
        }
    }
    
    void executeNormalPriorityCompiles() {
        // 执行中等优先级编译
        while (!mScheduleQueue.empty() && 
               mScheduleQueue.top().priority == Priority::NORMAL) {
            PacerTask task = mScheduleQueue.top();
            mScheduleQueue.pop();
            
            // 执行编译
            task.callback(task.desc);
            
            // 记录执行时间
            auto executionTime = std::chrono::steady_clock::now() - task.scheduledTime;
            mExecutionMetrics.recordExecutionTime(task.priority, 
                                                 std::chrono::duration_cast<std::chrono::microseconds>(executionTime));
        }
    }
    
    void executeEmergencyCompiles() {
        // 仅执行紧急编译
        while (!mScheduleQueue.empty() && 
               mScheduleQueue.top().priority == Priority::EMERGENCY) {
            PacerTask task = mScheduleQueue.top();
            mScheduleQueue.pop();
            
            // 立即执行编译
            task.callback(task.desc);
            
            // 记录执行时间
            auto executionTime = std::chrono::steady_clock::now() - task.scheduledTime;
            mExecutionMetrics.recordExecutionTime(task.priority, 
                                                 std::chrono::duration_cast<std::chrono::microseconds>(executionTime));
        }
    }
    
    void insertByPriority(PacerTask& task) {
        // 根据优先级插入调度队列
        task.scheduledTime = std::chrono::steady_clock::now();
        
        switch (task.priority) {
            case Priority::EMERGENCY:
                mEmergencyQueue.push(task);
                break;
            case Priority::HIGH:
                mHighPriorityQueue.push(task);
                break;
            case Priority::NORMAL:
                mNormalPriorityQueue.push(task);
                break;
            case Priority::LOW:
                mLowPriorityQueue.push(task);
                break;
        }
        
        // 更新优先级队列
        updatePriorityQueues();
    }
    \n    void updatePriorityQueues() {
        // 将低优先级队列合并到高优先级队列
        while (!mLowPriorityQueue.empty()) {
            mNormalPriorityQueue.push(mLowPriorityQueue.top());
            mLowPriorityQueue.pop();
        }
        
        while (!mNormalPriorityQueue.empty()) {
            mHighPriorityQueue.push(mNormalPriorityQueue.top());
            mNormalPriorityQueue.pop();
        }
        
        while (!mEmergencyQueue.empty()) {
            mHighPriorityQueue.push(mEmergencyQueue.top());
            mEmergencyQueue.pop();
        }
    }
    
    void adjustParameters() {
        // 动态调整调度参数
        float avgFrameTime = mFrameMetrics.getAverageFrameTime();
        float frameTimeStdDev = mFrameMetrics.getFrameTimeStdDev();
        
        // 根据帧率稳定性调整参数
        if (frameTimeStdDev > 2.0f) {
            // 帧率波动较大，降低编译预算
            mCompileTimeBudget = std::max(2.0f, mCompileTimeBudget * 0.9f);
        } else {
            // 帧率稳定，增加编译预算
            mCompileTimeBudget = std::min(6.0f, mCompileTimeBudget * 1.1f);
        }
        
        // 根据平均帧率调整最大待编译数量
        if (avgFrameTime > 16.0f) {
            mMaxPendingCompiles = std::max(5, mMaxPendingCompiles - 1);
        } else {
            mMaxPendingCompiles = std::min(15, mMaxPendingCompiles + 1);
        }
    }
    
    // 成员变量
    float mFrameTimeBudget;
    float mCompileTimeBudget;
    int mMaxPendingCompiles;
    
    std::thread mPacerThread;
    std::mutex mMutex;
    
    std::priority_queue<PacerTask> mEmergencyQueue;
    std::priority_queue<PacerTask> mHighPriorityQueue;
    std::priority_queue<PacerTask> mNormalPriorityQueue;
    std::priority_queue<PacerTask> mLowPriorityQueue;
    
    PacerState mPacerState = PacerState::NORMAL;
    
    float mLastFrameTime = 0.0f;
    FrameMetrics mFrameMetrics;
    ScheduleMetrics mScheduleMetrics;
    ExecutionMetrics mExecutionMetrics;
    
    bool mShutdown = false;
};
```

## 3. PipelineCache 管线缓存实现

```cpp
// frameworks/native/opengl/libs/RenderEngine/src/PipelineCache.cpp
class PipelineCache {
public:
    PipelineCache() {
        // 初始化缓存参数
        mMaxCacheSize = 100;
        mMaxCacheMemory = 100 * 1024 * 1024; // 100MB
        mCacheTtl = 300000; // 5分钟
        
        // 初始化缓存
        initializeCache();
        
        // 启动缓存清理线程
        mCleanupThread = std::thread([this]() {
            runCleanupLoop();
        });
    }
    
    ~PipelineCache() {
        shutdown();
    }
    
    bool find(const PipelineDesc& desc, PipelineHandle& handle) {
        std::lock_guard<std::mutex> lock(mMutex);
        
        // 计算哈希值
        size_t hash = desc.hash();
        
        // 查找缓存
        auto it = mCache.find(hash);
        if (it != mCache.end()) {
            CacheEntry& entry = it->second;
            
            // 检查是否过期
            if (isExpired(entry)) {
                removeEntry(hash);
                return false;
            }
            
            // 检查描述符是否匹配
            if (entry.desc == desc) {
                handle = entry.handle;
                // 更新访问时间
                entry.lastAccessTime = std::chrono::steady_clock::now();
                return true;
            }
        }
        
        return false;
    }
    
    void add(const PipelineDesc& desc, PipelineHandle handle) {
        std::lock_guard<std::mutex> lock(mMutex);
        
        // 计算哈希值
        size_t hash = desc.hash();
        
        // 检查是否已存在
        if (mCache.find(hash) != mCache.end()) {
            // 已存在，更新
            updateEntry(hash, desc, handle);
            return;
        }
        
        // 创建新条目
        CacheEntry entry;
        entry.desc = desc;
        entry.handle = handle;
        entry.creationTime = std::chrono::steady_clock::now();
        entry.lastAccessTime = entry.creationTime;
        entry.memoryUsage = calculateMemoryUsage(desc);
        
        // 添加到缓存
        mCache[hash] = entry;
        
        // 更新统计信息
        mCacheStats.recordEntryAdded(entry.memoryUsage);
        
        // 检查缓存限制
        enforceCacheLimits();
    }
    
    void evictEntries(int count) {
        std::lock_guard<std::mutex> lock(mMutex);
        
        // 按访问时间排序
        std::vector<CacheEntry*> sortedEntries;
        for (auto& pair : mCache) {
            sortedEntries.push_back(&pair.second);
        }
        
        // 按最后访问时间排序
        std::sort(sortedEntries.begin(), sortedEntries.end(),
                 [](CacheEntry* a, CacheEntry* b) {
                     return a->lastAccessTime < b->lastAccessTime;
                 });
        
        // 删除指定数量的条目
        int evicted = 0;
        for (auto* entry : sortedEntries) {
            if (evicted >= count) {
                break;
            }
            
            // 删除缓存条目
            removeEntry(entry->handle);
            evicted++;
        }
        
        mCacheStats.recordEntriesEvicted(evicted);
    }
    
    void processCacheEviction() {
        while (!mShutdown) {
            // 检查缓存大小
            if (shouldEvictEntries()) {
                // 计算需要删除的条目数量
                int entriesToEvict = calculateEvictCount();
                evictEntries(entriesToEvict);
            }
            
            // 检查过期条目
            cleanExpiredEntries();
            
            // 短暂休眠
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
    }
    
private:
    struct CacheEntry {
        PipelineDesc desc;
        PipelineHandle handle;
        std::chrono::steady_clock::time_point creationTime;
        std::chrono::steady_clock::time_point lastAccessTime;
        size_t memoryUsage;
        uint32_t accessCount;
    };
    
    void initializeCache() {
        // 预分配缓存空间
        mCache.reserve(mMaxCacheSize);
        
        // 初始化缓存统计
        mCacheStats.initialize();
    }
    
    bool isExpired(const CacheEntry& entry) {
        auto now = std::chrono::steady_clock::now();
        auto age = std::chrono::duration_cast<std::chrono::milliseconds>(
            now - entry.creationTime).count();
        
        return age > mCacheTtl;
    }
    
    size_t calculateMemoryUsage(const PipelineDesc& desc) {
        // 计算管线内存使用量
        size_t memory = 0;
        
        // 着色器内存
        for (uint32_t i = 0; i < desc.shaderCount; ++i) {
            memory += desc.shaders[i].size;
        }
        
        // Uniform 内存
        for (uint32_t i = 0; i < desc.uniformCount; ++i) {
            memory += desc.uniforms[i].size;
        }
        
        // 属性内存
        for (uint32_t i = 0; i < desc.attributeCount; ++i) {
            memory += desc.attributes[i].size;
        }
        
        // 渲染通道内存
        for (uint32_t i = 0; i < desc.renderPassCount; ++i) {
            memory += desc.renderPasses[i].size;
        }
        
        return memory;
    }
    
    void removeEntry(size_t hash) {
        auto it = mCache.find(hash);
        if (it != mCache.end()) {
            CacheEntry& entry = it->second;
            
            // 释放管线资源
            mGpuService->releasePipeline(entry.handle);
            
            // 更新统计信息
            mCacheStats.recordEntryRemoved(entry.memoryUsage);
            
            // 删除条目
            mCache.erase(it);
        }
    }
    
    void removeEntry(PipelineHandle handle) {
        // 通过句柄查找并删除条目
        for (auto it = mCache.begin(); it != mCache.end(); ++it) {
            if (it->second.handle == handle) {
                removeEntry(it->first);
                break;
            }
        }
    }
    
    void updateEntry(size_t hash, const PipelineDesc& desc, PipelineHandle handle) {
        auto it = mCache.find(hash);
        if (it != mCache.end()) {
            CacheEntry& entry = it->second;
            
            // 更新描述符
            entry.desc = desc;
            entry.handle = handle;
            entry.lastAccessTime = std::chrono::steady_clock::now();
            entry.accessCount++;
            
            // 更新内存使用量
            entry.memoryUsage = calculateMemoryUsage(desc);
        }
    }
    
    bool shouldEvictEntries() {
        // 检查是否需要清理缓存条目
        return mCache.size() > mMaxCacheSize || 
               getTotalMemoryUsage() > mMaxCacheMemory;
    }
    
    int calculateEvictCount() {
        int count = 0;
        
        // 如果超过最大缓存数量，删除 20%
        if (mCache.size() > mMaxCacheSize) {
            count = mCache.size() * 0.2;
        }
        
        // 如果超过内存限制，删除足够的条目
        if (getTotalMemoryUsage() > mMaxCacheMemory) {
            size_t excess = getTotalMemoryUsage() - mMaxCacheMemory;
            count = calculateEvictCountForMemory(excess);
        }
        
        return count;
    }
    
    int calculateEvictCountForMemory(size_t excessMemory) {
        int count = 0;
        size_t freedMemory = 0;
        
        // 按最后访问时间排序
        std::vector<CacheEntry*> sortedEntries;
        for (auto& pair : mCache) {
            sortedEntries.push_back(&pair.second);
        }
        
        std::sort(sortedEntries.begin(), sortedEntries.end(),
                 [](CacheEntry* a, CacheEntry* b) {
                     return a->lastAccessTime < b->lastAccessTime;
                 });
        
        // 删除条目直到释放足够的内存
        for (auto* entry : sortedEntries) {
            if (freedMemory >= excessMemory) {
                break;
            }
            
            freedMemory += entry->memoryUsage;
            count++;
        }
        
        return count;
    }
    
    size_t getTotalMemoryUsage() {
        size_t total = 0;
        for (const auto& pair : mCache) {
            total += pair.second.memoryUsage;
        }
        return total;
    }
    
    void cleanExpiredEntries() {
        // 清理过期条目
        std::vector<size_t> expiredHashes;
        
        for (const auto& pair : mCache) {
            if (isExpired(pair.second)) {
                expiredHashes.push_back(pair.first);
            }
        }
        
        // 删除过期条目
        for (size_t hash : expiredHashes) {
            removeEntry(hash);
        }
    }
    
    void enforceCacheLimits() {
        // 确保缓存限制
        while (mCache.size() > mMaxCacheSize || 
               getTotalMemoryUsage() > mMaxCacheMemory) {
            
            // 计算需要删除的条目数量
            int entriesToEvict = calculateEvictCount();
            if (entriesToEvict <= 0) {
                break;
            }
            
            evictEntries(entriesToEvict);
        }
    }
    
    void runCleanupLoop() {
        while (!mShutdown) {
            // 执行缓存清理
            processCacheEviction();
            
            // 短暂休眠
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
    }
    
    // 成员变量
    std::unordered_map<size_t, CacheEntry> mCache;
    std::mutex mMutex;
    std::thread mCleanupThread;
    
    int mMaxCacheSize;
    size_t mMaxCacheMemory;
    uint64_t mCacheTtl;
    
    CacheStats mCacheStats;
    IGpuService* mGpuService;
    
    bool mShutdown = false;
};
```

## 4. 性能优化策略

### 4.1 编译优先级调度

```cpp
// 编译优先级调度实现
class PriorityScheduler {
public:
    enum class CompilationPriority {
        EMERGENCY,    // 紧急 - 立即编译
        HIGH,         // 高优先级
        NORMAL,       // 正常优先级
        LOW,          // 低优先级
        BACKGROUND    // 后台编译
    };
    
    struct CompilationTask {
        PipelineDesc desc;
        CompilationPriority priority;
        std::chrono::steady_clock::time_point submitTime;
        std::function<void(PipelineHandle)> callback;
        uint32_t retryCount;
        bool completed;
    };
    
    bool scheduleCompilation(const PipelineDesc& desc, 
                           CompilationPriority priority,
                           std::function<void(PipelineHandle)> callback) {
        // 创建编译任务
        CompilationTask task;
        task.desc = desc;
        task.priority = priority;
        task.submitTime = std::chrono::steady_clock::now();
        task.callback = callback;
        task.retryCount = 0;
        task.completed = false;
        
        // 根据优先级选择调度策略
        switch (priority) {
            case CompilationPriority::EMERGENCY:
                return scheduleEmergency(task);
            case CompilationPriority::HIGH:
                return scheduleHighPriority(task);
            case CompilationPriority::NORMAL:
                return scheduleNormal(task);
            case CompilationPriority::LOW:
                return scheduleLow(task);
            case CompilationPriority::BACKGROUND:
                return scheduleBackground(task);
        }
        
        return false;
    }
    
private:
    bool scheduleEmergency(CompilationTask& task) {
        // 紧急编译策略
        // 1. 立即编译
        // 2. 阻塞当前渲染线程
        // 3. 不考虑时间预算
        
        std::lock_guard<std::mutex> lock(mMutex);
        
        // 立即执行编译
        PipelineHandle handle = mGpuService->compilePipeline(task.desc);
        
        // 调用回调
        task.callback(handle);
        
        // 记录紧急编译
        mEmergencyCount++;
        
        return true;
    }
    
    bool scheduleHighPriority(CompilationTask& task) {
        // 高优先级编译策略
        // 1. 尝试立即编译
        // 2. 如果预算允许，优先编译
        // 3. 阻止低优先级编译
        
        std::lock_guard<std::mutex> lock(mMutex);
        
        // 检查编译预算
        if (mPacer->canCompileNow(task.desc)) {
            // 立即编译
            PipelineHandle handle = mGpuService->compilePipeline(task.desc);
            task.callback(handle);
            
            // 记录高优先级编译
            mHighPriorityCount++;
            
            return true;
        }
        
        // 添加到高优先级队列
        mHighPriorityQueue.push(task);
        
        return true;
    }
    
    bool scheduleNormal(CompilationTask& task) {
        // 正常优先级编译策略
        // 1. 等待预算
        // 2. 不阻塞渲染线程
        // 3. 可以被高优先级任务打断
        
        std::lock_guard<std::mutex> lock(mMutex);
        
        // 添加到正常队列
        mNormalPriorityQueue.push(task);
        
        return true;
    }
    
    bool scheduleLow(CompilationTask& task) {
        // 低优先级编译策略
        // 1. 仅在渲染线程空闲时编译
        // 2. 可以被高优先级任务抢占
        // 3. 最终可能被丢弃
        
        std::lock_guard<std::mutex> lock(mMutex);
        
        // 添加到低优先级队列
        mLowPriorityQueue.push(task);
        
        return true;
    }
    
    bool scheduleBackground(CompilationTask& task) {
        // 后台编译策略
        // 1. 仅在完全空闲时编译
        // 2. 可以被任何任务抢占
        // 3. 最优先级最低
        
        std::lock_guard<std::mutex> lock(mMutex);
        
        // 添加到后台队列
        mBackgroundQueue.push(task);
        
        return true;
    }
    
    // 队列处理
    void processQueues() {
        std::lock_guard<std::mutex> lock(mMutex);
        
        // 1. 处理紧急队列
        while (!mEmergencyQueue.empty()) {
            CompilationTask task = mEmergencyQueue.front();
            mEmergencyQueue.pop();
            
            PipelineHandle handle = mGpuService->compilePipeline(task.desc);
            task.callback(handle);
        }
        
        // 2. 处理高优先级队列
        while (!mHighPriorityQueue.empty()) {
            if (!mPacer->canCompileNow(mHighPriorityQueue.front().desc)) {
                break;
            }
            
            CompilationTask task = mHighPriorityQueue.front();
            mHighPriorityQueue.pop();
            
            PipelineHandle handle = mGpuService->compilePipeline(task.desc);
            task.callback(handle);
        }
        
        // 3. 处理正常队列
        while (!mNormalPriorityQueue.empty()) {
            if (!mPacer->canCompileNow(mNormalPriorityQueue.front().desc)) {
                break;
            }
            
            CompilationTask task = mNormalPriorityQueue.front();
            mNormalPriorityQueue.pop();
            
            PipelineHandle handle = mGpuService->compilePipeline(task.desc);
            task.callback(handle);
        }
        
        // 4. 处理低优先级队列
        while (!mLowPriorityQueue.empty()) {
            if (!mPacer->canCompileNow(mLowPriorityQueue.front().desc)) {
                break;
            }
            
            CompilationTask task = mLowPriorityQueue.front();
            mLowPriorityQueue.pop();
            
            PipelineHandle handle = mGpuService->compilePipeline(task.desc);
            task.callback(handle);
        }
        
        // 5. 处理后台队列
        while (!mBackgroundQueue.empty()) {
            if (!mPacer->canCompileNow(mBackgroundQueue.front().desc)) {
                break;
            }
            
            CompilationTask task = mBackgroundQueue.front();
            mBackgroundQueue.pop();
            
            PipelineHandle handle = mGpuService->compilePipeline(task.desc);
            task.callback(handle);
        }
    }
    
    // 成员变量
    std::mutex mMutex;
    std::queue<CompilationTask> mEmergencyQueue;
    std::queue<CompilationTask> mHighPriorityQueue;
    std::queue<CompilationTask> mNormalPriorityQueue;
    std::queue<CompilationTask> mLowPriorityQueue;
    std::queue<CompilationTask> mBackgroundQueue;
    
    IGpuService* mGpuService;
    std::unique_ptr<PipelinePacer> mPacer;
    
    uint32_t mEmergencyCount = 0;
    uint32_t mHighPriorityCount = 0;
    uint32_t mNormalPriorityCount = 0;
    uint32_t mLowPriorityCount = 0;
    uint32_t mBackgroundCount = 0;
};
```

### 4.2 内存管理优化

```cpp
// 内存管理优化
class MemoryManager {
public:
    MemoryManager() {
        // 初始化内存池
        mShaderPool = std::make_unique<MemoryPool>(SHADER_POOL_SIZE);
        mUniformPool = std::make_unique<MemoryPool>(UNIFORM_POOL_SIZE);
        mAttributePool = std::make_unique<MemoryPool>(ATTRIBUTE_POOL_SIZE);
        
        // 初始化内存分配器
        mShaderAllocator = std::make_unique<PoolAllocator>(mShaderPool.get());
        mUniformAllocator = std::make_unique<PoolAllocator>(mUniformPool.get());
        mAttributeAllocator = std::make_unique<PoolAllocator>(mAttributePool.get());
        
        // 启动内存监控
        mMemoryMonitor = std::thread([this]() {
            runMemoryMonitor();
        });
    }
    
    ~MemoryManager() {
        shutdown();
    }
    
    void* allocateShader(size_t size) {
        return mShaderAllocator->allocate(size);
    }
    
    void* allocateUniform(size_t size) {
        return mUniformAllocator->allocate(size);
    }
    
    void* allocateAttribute(size_t size) {
        return mAttributeAllocator->allocate(size);
    }
    
    void deallocateShader(void* ptr, size_t size) {
        mShaderAllocator->deallocate(ptr, size);
    }
    
    void deallocateUniform(void* ptr, size_t size) {
        mUniformAllocator->deallocate(ptr, size);
    }
    
    void deallocateAttribute(void* ptr, size_t size) {
        mAttributeAllocator->deallocate(ptr, size);
    }
    
    void optimizeMemoryUsage() {
        // 1. 合并碎片
        mShaderAllocator->defragment();
        mUniformAllocator->defragment();
        mAttributeAllocator->defragment();
        
        // 2. 释放未使用的内存
        releaseUnusedMemory();
        
        // 3. 调整内存池大小
        adjustMemoryPools();
    }
    
private:
    struct MemoryPool {
        MemoryPool(size_t size) : mSize(size), mUsed(0), mPeak(0) {
            mMemory = std::make_unique<uint8_t[]>(size);
        }
        
        void* allocate(size_t size) {
            std::lock_guard<std::mutex> lock(mMutex);
            
            if (mUsed + size > mSize) {
                return nullptr;
            }
            
            void* ptr = mMemory.get() + mUsed;
            mUsed += size;
            
            if (mUsed > mPeak) {
                mPeak = mUsed;
            }
            
            return ptr;
        }
        
        void deallocate(void* ptr, size_t size) {
            std::lock_guard<std::mutex> lock(mMutex);
            
            // 简单的释放策略（实际实现可能需要更复杂的逻辑）
            if (ptr >= mMemory.get() && ptr < mMemory.get() + mSize) {
                // 记录释放的内存
                mReleased += size;
            }
        }
        
        void defragment() {
            std::lock_guard<std::mutex> lock(mMutex);
            
            // 实现内存碎片整理
            // 这里简化处理，实际可能需要移动内存块
        }
        
        size_t getUsed() const { return mUsed; }
        size_t getPeak() const { return mPeak; }
        size_t getFree() const { return mSize - mUsed; }
        
    private:
        std::unique_ptr<uint8_t[]> mMemory;
        size_t mSize;
        size_t mUsed;
        size_t mPeak;
        size_t mReleased = 0;
        std::mutex mMutex;
    };
    
    struct PoolAllocator {
        PoolAllocator(MemoryPool* pool) : mPool(pool) {}
        
        void* allocate(size_t size) {
            // 对齐分配
            size_t alignedSize = (size + ALIGNMENT - 1) & ~(ALIGNMENT - 1);
            return mPool->allocate(alignedSize);
        }
        
        void deallocate(void* ptr, size_t size) {
            mPool->deallocate(ptr, size);
        }
        
        void defragment() {
            mPool->defragment();
        }
        
    private:
        MemoryPool* mPool;
        static constexpr size_t ALIGNMENT = 16;
    };
    
    void releaseUnusedMemory() {
        // 1. 释放未使用的着色器内存
        releaseUnusedShaderMemory();
        
        // 2. 释放未使用的 Uniform 内存
        releaseUnusedUniformMemory();
        
        // 3. 释放未使用的属性内存
        releaseUnusedAttributeMemory();
    }
    
    void releaseUnusedShaderMemory() {
        // 扫描所有着色器，释放未使用的
        std::vector<ShaderHandle> shadersToRelease;
        
        for (const auto& shader : mShaderRegistry) {
            if (shader.second->refCount == 0) {
                shadersToRelease.push_back(shader.first);
            }
        }
        
        for (auto handle : shadersToRelease) {
            mShaderRegistry.erase(handle);
            mShaderAllocator->deallocate(handle.memory, handle.size);
        }
    }
    
    void releaseUnusedUniformMemory() {
        // 类似着色器的处理
        std::vector<UniformHandle> uniformsToRelease;
        
        for (const auto& uniform : mUniformRegistry) {
            if (uniform.second->refCount == 0) {
                uniformsToRelease.push_back(uniform.first);
            }
        }
        
        for (auto handle : uniformsToRelease) {
            mUniformRegistry.erase(handle);
            mUniformAllocator->deallocate(handle.memory, handle.size);
        }
    }
    
    void releaseUnusedAttributeMemory() {
        // 类似着色器的处理
        std::vector<AttributeHandle> attributesToRelease;
        
        for (const auto& attribute : mAttributeRegistry) {
            if (attribute.second->refCount == 0) {
                attributesToRelease.push_back(attribute.first);
            }
        }
        
        for (auto handle : attributesToRelease) {
            mAttributeRegistry.erase(handle);
            mAttributeAllocator->deallocate(handle.memory, handle.size);
        }
    }
    
    void adjustMemoryPools() {
        // 根据使用情况调整内存池大小
        adjustShaderPool();
        adjustUniformPool();
        adjustAttributePool();
    }
    
    void adjustShaderPool() {
        size_t used = mShaderPool->getUsed();
        size_t peak = mShaderPool->getPeak();
        size_t free = mShaderPool->getFree();
        
        // 如果使用率低于 20%，缩小内存池
        if (used > 0 && (double)used / peak < 0.2) {
            size_t newSize = peak * 0.8;
            resizeShaderPool(newSize);
        }
        
        // 如果使用率高于 80%，扩大内存池
        else if ((double)used / (used + free) > 0.8) {
            size_t newSize = peak * 1.2;
            resizeShaderPool(newSize);
        }
    }
    
    void adjustUniformPool() {
        // 类似的调整逻辑
        size_t used = mUniformPool->getUsed();
        size_t peak = mUniformPool->getPeak();
        
        if (used > 0 && (double)used / peak < 0.2) {
            size_t newSize = peak * 0.8;
            resizeUniformPool(newSize);
        } else if ((double)used / (peak + mUniformPool->getFree()) > 0.8) {
            size_t newSize = peak * 1.2;
            resizeUniformPool(newSize);
        }
    }
    
    void adjustAttributePool() {
        // 类似的调整逻辑
        size_t used = mAttributePool->getUsed();
        size_t peak = mAttributePool->getPeak();
        
        if (used > 0 && (double)used / peak < 0.2) {
            size_t newSize = peak * 0.8;
            resizeAttributePool(newSize);
        } else if ((double)used / (peak + mAttributePool->getFree()) > 0.8) {
            size_t newSize = peak * 1.2;
            resizeAttributePool(newSize);
        }
    }
    
    void resizeShaderPool(size_t newSize) {
        // 创建新的内存池
        auto newPool = std::make_unique<MemoryPool>(newSize);
        
        // 迁移现有数据
        for (const auto& shader : mShaderRegistry) {
            void* newMemory = newPool->allocate(shader.second->size);
            if (newMemory) {
                memcpy(newMemory, shader.second->memory, shader.second->size);
                mShaderAllocator->deallocate(shader.second->memory, shader.second->size);
                shader.second->memory = newMemory;
            }
        }
        
        // 替换内存池
        mShaderPool = std::move(newPool);
    }
    
    void resizeUniformPool(size_t newSize) {
        // 类似的调整逻辑
        auto newPool = std::make_unique<MemoryPool>(newSize);
        
        for (const auto& uniform : mUniformRegistry) {
            void* newMemory = newPool->allocate(uniform.second->size);
            if (newMemory) {
                memcpy(newMemory, uniform.second->memory, uniform.second->size);
                mUniformAllocator->deallocate(uniform.second->memory, uniform.second->size);
                uniform.second->memory = newMemory;
            }
        }
        
        mUniformPool = std::move(newPool);
    }
    
    void resizeAttributePool(size_t newSize) {
        // 类似的调整逻辑
        auto newPool = std::make_unique<MemoryPool>(newSize);
        
        for (const auto& attribute : mAttributeRegistry) {
            void* newMemory = newPool->allocate(attribute.second->size);
            if (newMemory) {
                memcpy(newMemory, attribute.second->memory, attribute.second->size);
                mAttributeAllocator->deallocate(attribute.second->memory, attribute.second->size);
                attribute.second->memory = newMemory;
            }
        }
        
        mAttributePool = std::move(newPool);
    }
    
    void runMemoryMonitor() {
        while (!mShutdown) {
            // 定期监控内存使用情况
            monitorMemoryUsage();
            
            // 短暂休眠
            std::this_thread::sleep_for(std::chrono::seconds(5));
        }
    }
    
    void monitorMemoryUsage() {
        // 记录内存使用情况
        MemorySnapshot snapshot;
        snapshot.shaderMemory = mShaderPool->getUsed();
        snapshot.uniformMemory = mUniformPool->getUsed();
        snapshot.attributeMemory = mAttributePool->getUsed();
        snapshot.timestamp = std::chrono::steady_clock::now();
        
        // 添加到快照列表
        mMemorySnapshots.push_back(snapshot);
        
        // 保持快照数量在合理范围内
        if (mMemorySnapshots.size() > 100) {
            mMemorySnapshots.pop_front();
        }
        
        // 检查内存泄漏
        checkMemoryLeaks();
        
        // 检查内存压力
        checkMemoryPressure();
    }
    
    void checkMemoryLeaks() {
        // 检查是否有内存泄漏
        for (const auto& shader : mShaderRegistry) {
            if (shader.second->refCount == 0 && shader.second->lastUsedTime + std::chrono::hours(24) < std::chrono::steady_clock::now()) {
                // 着色器内存可能泄漏
                LOG(WARNING) << "Potential shader memory leak detected";
            }
        }
        
        for (const auto& uniform : mUniformRegistry) {
            if (uniform.second->refCount == 0 && uniform.second->lastUsedTime + std::chrono::hours(24) < std::chrono::steady_clock::now()) {
                // Uniform 内存可能泄漏
                LOG(WARNING) << "Potential uniform memory leak detected";
            }
        }
        
        for (const auto& attribute : mAttributeRegistry) {
            if (attribute.second->refCount == 0 && attribute.second->lastUsedTime + std::chrono::hours(24) < std::chrono::steady_clock::now()) {
                // 属性内存可能泄漏
                LOG(WARNING) << "Potential attribute memory leak detected";
            }
        }
    }
    
    void checkMemoryPressure() {
        size_t totalMemory = mShaderPool->getUsed() + 
                           mUniformPool->getUsed() + 
                           mAttributePool->getUsed();
        
        if (totalMemory > mMemoryPressureThreshold) {
            // 内存压力大，触发优化
            optimizeMemoryUsage();
        }
    }
    
    // 成员变量
    std::unique_ptr<MemoryPool> mShaderPool;
    std::unique_ptr<MemoryPool> mUniformPool;
    std::unique_ptr<MemoryPool> mAttributePool;
    
    std::unique_ptr<PoolAllocator> mShaderAllocator;
    std::unique_ptr<PoolAllocator> mUniformAllocator;
    std::unique_ptr<PoolAllocator> mAttributeAllocator;
    
    std::unordered_map<ShaderHandle, std::unique_ptr<ShaderInfo>> mShaderRegistry;
    std::unordered_map<UniformHandle, std::unique_ptr<UniformInfo>> mUniformRegistry;
    std::unordered_map<AttributeHandle, std::unique_ptr<AttributeInfo>> mAttributeRegistry;
    
    std::thread mMemoryMonitor;
    std::deque<MemorySnapshot> mMemorySnapshots;
    
    size_t mMemoryPressureThreshold = 100 * 1024 * 1024; // 100MB
    
    bool mShutdown = false;
};
```

## 5. 调试与性能分析

### 5.1 性能监控

```cpp
// 性能监控系统
class PerformanceMonitor {
public:
    PerformanceMonitor() {
        // 启动性能监控线程
        mMonitorThread = std::thread([this]() {
            runMonitorLoop();
        });
    }
    
    ~PerformanceMonitor() {
        shutdown();
    }
    
    void recordCompilationTime(Priority priority, std::chrono::microseconds duration) {
        mCompilationTimes.record(priority, duration);
    }
    
    void recordCacheHit(bool hit) {
        mCacheStats.recordHit(hit);
    }
    
    void recordFrameTime(std::chrono::microseconds frameTime) {
        mFrameTimes.record(frameTime);
    }
    
    void reportPerformanceMetrics() {
        // 生成性能报告
        PerformanceReport report;
        
        // 编译时间统计
        report.compilationStats = mCompilationStats.generateReport();
        
        // 缓存统计
        report.cacheStats = mCacheStats.generateReport();
        
        // 帧时间统计
        report.frameStats = mFrameStats.generateReport();
        
        // 上下文切换统计
        report.contextSwitchStats = mContextSwitchStats.generateReport();
        
        // 内存使用统计
        report.memoryStats = mMemoryStats.generateReport();
        
        // 上报性能数据
        reportPerformanceData(report);
    }
    
private:
    struct CompilationStats {
        struct TimeRecord {
            Priority priority;
            std::chrono::microseconds duration;
            std::chrono::steady_clock::time_point timestamp;
        };
        
        void record(Priority priority, std::chrono::microseconds duration) {
            TimeRecord record;
            record.priority = priority;
            record.duration = duration;
            record.timestamp = std::chrono::steady_clock::now();
            
            mRecords.push_back(record);
            
            // 更新统计信息
            updateStats(priority, duration);
        }
        
        void updateStats(Priority priority, std::chrono::microseconds duration) {
            mTotalCount[priority]++;
            mTotalTime[priority] += duration;
            mAverageTime[priority] = mTotalTime[priority] / mTotalCount[priority];
            
            // 更新最大时间
            if (duration > mMaxTime[priority]) {
                mMaxTime[priority] = duration;
            }
            
            // 更新最小时间
            if (mMinTime[priority] == std::chrono::microseconds::zero() || 
                duration < mMinTime[priority]) {
                mMinTime[priority] = duration;
            }
        }
        
        PerformanceReport::CompilationStats generateReport() {
            PerformanceReport::CompilationStats report;
            
            for (int i = 0; i < static_cast<int>(Priority::COUNT); ++i) {
                Priority priority = static_cast<Priority>(i);
                report.totalCount[i] = mTotalCount[priority];
                report.averageTime[i] = mAverageTime[priority];
                report.maxTime[i] = mMaxTime[priority];
                report.minTime[i] = mMinTime[priority];
            }
            
            return report;
        }
        
    private:
        std::vector<TimeRecord> mRecords;
        std::array<uint64_t, static_cast<int>(Priority::COUNT)> mTotalCount{};
        std::array<std::chrono::microseconds, static_cast<int>(Priority::COUNT)> mTotalTime{};
        std::array<std::chrono::microseconds, static_cast<int>(Priority::COUNT)> mAverageTime{};
        std::array<std::chrono::microseconds, static_cast<int>(Priority::COUNT)> mMaxTime{};
        std::array<std::chrono::microseconds, static_cast<int>(Priority::COUNT)> mMinTime{};
    };
    
    struct CacheStats {
        void recordHit(bool hit) {
            mTotalRequests++;
            if (hit) {
                mHits++;
                mHitRate = static_cast<double>(mHits) / mTotalRequests;
            } else {
                mMisses++;
                mMissRate = static_cast<double>(mMisses) / mTotalRequests;
            }
        }
        
        PerformanceReport::CacheStats generateReport() {
            PerformanceReport::CacheStats report;
            report.totalRequests = mTotalRequests;
            report.hits = mHits;
            report.misses = mMisses;
            report.hitRate = mHitRate;
            report.missRate = mMissRate;
            return report;
        }
        
    private:
        uint64_t mTotalRequests = 0;
        uint64_t mHits = 0;
        uint64_t mMisses = 0;
        double mHitRate = 0.0;
        double mMissRate = 0.0;
    };
    
    struct FrameStats {
        void record(std::chrono::microseconds frameTime) {
            mFrameTimes.push_back(frameTime);
            mTotalFrames++;
            
            // 更新统计信息
            updateStats(frameTime);
        }
        
        void updateStats(std::chrono::microseconds frameTime) {
            // 更新平均帧时间
            if (mFrameTimes.empty()) {
                mAverageFrameTime = frameTime;
            } else {
                mAverageFrameTime = std::accumulate(
                    mFrameTimes.begin(), mFrameTimes.end(), 
                    std::chrono::microseconds::zero()) / mFrameTimes.size();
            }
            
            // 更新帧率
            mFps = 1000000.0 / mAverageFrameTime.count();
            
            // 更新最大/最小帧时间
            if (mMaxFrameTime < frameTime) {
                mMaxFrameTime = frameTime;
            }
            
            if (mMinFrameTime > frameTime || mMinFrameTime == std::chrono::microseconds::zero()) {
                mMinFrameTime = frameTime;
            }
            
            // 检查帧率稳定性
            if (frameTime > 25000) { // 超过 25ms
                mJankCount++;
                mJankRate = static_cast<double>(mJankCount) / mTotalFrames;
            }
        }
        
        PerformanceReport::FrameStats generateReport() {
            PerformanceReport::FrameStats report;
            report.totalFrames = mTotalFrames;
            report.averageFrameTime = mAverageFrameTime;
            report.fps = mFps;
            report.maxFrameTime = mMaxFrameTime;
            report.minFrameTime = mMinFrameTime;
            report.jankCount = mJankCount;
            report.jankRate = mJankRate;
            return report;
        }
        
    private:
        std::vector<std::chrono::microseconds> mFrameTimes;
        uint64_t mTotalFrames = 0;
        std::chrono::microseconds mAverageFrameTime = std::chrono::microseconds::zero();
        double mFps = 0.0;
        std::chrono::microseconds mMaxFrameTime = std::chrono::microseconds::zero();
        std::chrono::microseconds mMinFrameTime = std::chrono::microseconds::zero();
        uint64_t mJankCount = 0;
        double mJankRate = 0.0;
    };
    
    void runMonitorLoop() {
        while (!mShutdown) {
            // 定期收集性能数据
            collectPerformanceData();
            
            // 生成性能报告
            if (mReportInterval > 0 && 
                std::chrono::steady_clock::now() - mLastReportTime >= mReportInterval) {
                reportPerformanceMetrics();
                mLastReportTime = std::chrono::steady_clock::now();
            }
            
            // 短暂休眠
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    }
    
    void collectPerformanceData() {
        // 收集编译时间数据
        collectCompilationData();
        
        // 收集缓存数据
        collectCacheData();
        
        // 收集帧时间数据
        collectFrameData();
        
        // 收集内存使用数据
        collectMemoryData();
    }
    
    void collectCompilationData() {
        // 从编译器收集数据
        while (!mCompilationQueue.empty()) {
            auto record = mCompilationQueue.front();
            mCompilationQueue.pop();
            
            mCompilationStats.record(record.priority, record.duration);
        }
    }
    
    void collectCacheData() {
        // 从缓存收集数据
        while (!mCacheQueue.empty()) {
            auto record = mCacheQueue.front();
            mCacheQueue.pop();
            
            mCacheStats.recordHit(record.hit);
        }
    }
    
    void collectFrameData() {
        // 从渲染线程收集数据
        while (!mFrameQueue.empty()) {
            auto record = mFrameQueue.front();
            mFrameQueue.pop();
            
            mFrameStats.record(record.frameTime);
        }
    }
    
    void collectMemoryData() {
        // 从内存管理器收集数据
        MemoryUsage usage;
        
        // 获取着色器内存使用
        usage.shaderMemory = getShaderMemoryUsage();
        
        // 获取 Uniform 内存使用
        usage.uniformMemory = getUniformMemoryUsage();
        
        // 获取属性内存使用
        usage.attributeMemory = getAttributeMemoryUsage();
        
        // 记录内存使用
        mMemoryStats.record(usage);
    }
    
    void reportPerformanceData(const PerformanceReport& report) {
        // 上报性能数据到监控系统
        // 这里可以连接到 APM 系统或者写入日志
        
        LOG(INFO) << "Performance Report:";
        LOG(INFO) << "  Compilation:";
        for (int i = 0; i < static_cast<int>(Priority::COUNT); ++i) {
            Priority priority = static_cast<Priority>(i);
            LOG(INFO) << "    " << toString(priority) << ": "
                      << "avg=" << report.compilationStats.averageTime[i].count() << "μs, "
                      << "max=" << report.compilationStats.maxTime[i].count() << "μs, "
                      << "count=" << report.compilationStats.totalCount[i];
        }
        
        LOG(INFO) << "  Cache: hit_rate=" << (report.cacheStats.hitRate * 100) << "%";
        LOG(INFO) << "  Frame: fps=" << report.frameStats.fps 
                  << ", avg=" << report.frameStats.averageFrameTime.count() << "μs";
        LOG(INFO) << "  Memory: shader=" << report.memoryStats.shaderMemory 
                  << ", uniform=" << report.memoryStats.uniformMemory
                  << ", attribute=" << report.memoryStats.attributeMemory;
    }
    
    // 成员变量
    std::thread mMonitorThread;
    
    CompilationStats mCompilationStats;
    CacheStats mCacheStats;
    FrameStats mFrameStats;
    ContextSwitchStats mContextSwitchStats;
    MemoryStats mMemoryStats;
    
    std::queue<CompilationRecord> mCompilationQueue;
    std::queue<CacheRecord> mCacheQueue;
    std::queue<FrameRecord> mFrameQueue;
    std::queue<MemoryUsage> mMemoryQueue;
    
    std::chrono::steady_clock::time_point mLastReportTime;
    std::chrono::milliseconds mReportInterval = std::chrono::seconds(30);
    
    bool mShutdown = false;
};
```

### 5.2 调试工具

```cpp
// 调试工具
class DebugTools {
public:
    DebugTools(PipelineManager* manager) 
        : mManager(manager) 
        , mDebugMode(false)
        , mVerboseLogging(false) {
        // 初始化调试配置
        initializeDebugConfig();
    }
    
    void enableDebugMode() {
        mDebugMode = true;
        LOG(INFO) << "Debug mode enabled";
    }
    
    void disableDebugMode() {
        mDebugMode = false;
        LOG(INFO) << "Debug mode disabled";
    }
    
    void setVerboseLogging(bool verbose) {
        mVerboseLogging = verbose;
        LOG(INFO) << "Verbose logging " << (verbose ? "enabled" : "disabled");
    }
    
    void capturePipelineInfo(const PipelineDesc& desc) {
        if (!mDebugMode) {
            return;
        }
        
        PipelineInfo info;
        info.desc = desc;
        info.captureTime = std::chrono::steady_clock::now();
        
        // 捕获管线信息
        captureShaderInfo(info);
        captureUniformInfo(info);
        captureAttributeInfo(info);
        captureRenderPassInfo(info);
        
        // 添加到调试记录
        mPipelineRecords.push_back(info);
        
        if (mVerboseLogging) {
            logPipelineInfo(info);
        }
    }
    
    void dumpCompilationStats() {
        LOG(INFO) << "=== Compilation Statistics ===";
        
        // 编译统计
        for (const auto& stat : mCompilationStats) {
            LOG(INFO) << "Priority " << toString(stat.first) << ": "
                      << "count=" << stat.second.count << ", "
                      << "avg=" << stat.second.avgDuration.count() << "μs, "
                      << "max=" << stat.second.maxDuration.count() << "μs";
        }
        
        // 缓存统计
        LOG(INFO) << "Cache Statistics:";
        LOG(INFO) << "  Hits: " << mCacheStats.hits;
        LOG(INFO) << "  Misses: " << mCacheStats.misses;
        LOG(INFO) << "  Hit Rate: " << (mCacheStats.getHitRate() * 100) << "%";
        
        // 内存统计
        LOG(INFO) << "Memory Statistics:";
        LOG(INFO) << "  Shader Memory: " << mMemoryStats.shaderMemory << " bytes";
        LOG(INFO) << "  Uniform Memory: " << mMemoryStats.uniformMemory << " bytes";
        LOG(INFO) << "  Attribute Memory: " << mMemoryStats.attributeMemory << " bytes";
        LOG(INFO) << "  Total Memory: " << mMemoryStats.getTotalMemory() << " bytes";
    }
    
    void generateMemoryReport() {
        LOG(INFO) << "=== Memory Report ===";
        
        // 内存使用分析
        std::unordered_map<std::string, size_t> memoryByType;
        
        for (const auto& pipeline : mPipelineRecords) {
            memoryByType["shaders"] += pipeline.shaderMemory;
            memoryByType["uniforms"] += pipeline.uniformMemory;
            memoryByType["attributes"] += pipeline.attributeMemory;
        }
        
        // 输出内存使用情况
        for (const auto& entry : memoryByType) {
            LOG(INFO) << entry.first << ": " << entry.second << " bytes";
        }
        
        // 内存泄漏检测
        detectMemoryLeaks();
    }
    
    void detectMemoryLeaks() {
        LOG(INFO) << "=== Memory Leak Detection ===";
        
        // 检查长时间未使用的管线
        auto now = std::chrono::steady_clock::now();
        std::vector<std::string> leakedPipelines;
        
        for (const auto& pipeline : mPipelineRecords) {
            auto age = std::chrono::duration_cast<std::chrono::minutes>(
                now - pipeline.captureTime);
            
            if (age > std::chrono::hours(1)) { // 超过1小时未使用
                leakedPipelines.push_back(pipeline.desc.name);
            }
        }
        
        if (!leakedPipelines.empty()) {
            LOG(WARNING) << "Potential memory leaks detected:";
            for (const auto& name : leakedPipelines) {
                LOG(WARNING) << "  " << name;
            }
        } else {
            LOG(INFO) << "No memory leaks detected";
        }
    }
    
    void exportDebugData(const std::string& filename) {
        // 导出调试数据到文件
        std::ofstream file(filename);
        
        if (!file.is_open()) {
            LOG(ERROR) << "Failed to open debug file: " << filename;
            return;
        }
        
        // 写入管线记录
        file << "Pipeline Records:\n";
        for (const auto& pipeline : mPipelineRecords) {
            file << "  Pipeline: " << pipeline.desc.name << "\n";
            file << "    Shader Memory: " << pipeline.shaderMemory << "\n";
            file << "    Uniform Memory: " << pipeline.uniformMemory << "\n";
            file << "    Attribute Memory: " << pipeline.attributeMemory << "\n";
            file << "    Capture Time: " << pipeline.captureTime.time_since_epoch().count() << "\n";
        }
        
        // 写入编译统计
        file << "\nCompilation Statistics:\n";
        for (const auto& stat : mCompilationStats) {
            file << "  Priority " << toString(stat.first) << ":\n";
            file << "    Count: " << stat.second.count << "\n";
            file << "    Average Duration: " << stat.second.avgDuration.count() << "\n";
            file << "    Max Duration: " << stat.second.maxDuration.count() << "\n";
        }
        
        // 写入缓存统计
        file << "\nCache Statistics:\n";
        file << "  Hits: " << mCacheStats.hits << "\n";
        file << "  Misses: " << mCacheStats.misses << "\n";
        
        // 写入内存统计
        file << "\nMemory Statistics:\n";
        file << "  Shader Memory: " << mMemoryStats.shaderMemory << "\n";
        file << "  Uniform Memory: " << mMemoryStats.uniformMemory << "\n";
        file << "  Attribute Memory: " << mMemoryStats.attributeMemory << "\n";
        
        file.close();
        LOG(INFO) << "Debug data exported to: " << filename;
    }
    
private:
    struct PipelineInfo {
        PipelineDesc desc;
        std::chrono::steady_clock::time_point captureTime;
        size_t shaderMemory;
        size_t uniformMemory;
        size_t attributeMemory;
        
        std::vector<ShaderInfo> shaders;
        std::vector<UniformInfo> uniforms;
        std::vector<AttributeInfo> attributes;
        std::vector<RenderPassInfo> renderPasses;
    };
    
    struct CompilationStat {
        uint64_t count = 0;
        std::chrono::microseconds avgDuration{0};
        std::chrono::microseconds maxDuration{0};
        std::chrono::microseconds minDuration{std::numeric_limits<uint64_t>::max()};
    };
    
    struct CacheStat {
        uint64_t hits = 0;
        uint64_t misses = 0;
        
        double getHitRate() const {
            if (hits + misses == 0) return 0.0;
            return static_cast<double>(hits) / (hits + misses);
        }
    };
    
    struct MemoryStat {
        size_t shaderMemory = 0;
        size_t uniformMemory = 0;
        size_t attributeMemory = 0;
        
        size_t getTotalMemory() const {
            return shaderMemory + uniformMemory + attributeMemory;
        }
    };
    
    void initializeDebugConfig() {
        // 从配置文件加载调试设置
        loadDebugConfig();
        
        // 注册调试回调
        registerDebugCallbacks();
    }
    
    void loadDebugConfig() {
        // 加载调试配置
        mDebugConfig.debugMode = false;
        mDebugConfig.verboseLogging = false;
        mDebugConfig.maxPipelineRecords = 1000;
        mDebugConfig.memoryLeakDetection = true;
        mDebugConfig.autoExport = false;
        mDebugConfig.exportInterval = std::chrono::hours(1);
    }
    
    void registerDebugCallbacks() {
        // 注册调试回调
        mManager->setDebugCallback([this](const DebugEvent& event) {
            handleDebugEvent(event);
        });
    }
    
    void handleDebugEvent(const DebugEvent& event) {
        switch (event.type) {
            case DebugEvent::Type::PIPELINE_CREATED:
                handlePipelineCreated(event);
                break;
            case DebugEvent::Type::PIPELINE_DESTROYED:
                handlePipelineDestroyed(event);
                break;
            case DebugEvent::Type::COMPILATION_STARTED:
                handleCompilationStarted(event);
                break;
            case DebugEvent::Type::COMPILATION_COMPLETED:
                handleCompilationCompleted(event);
                break;
            case DebugEvent::Type::CACHE_HIT:
                handleCacheHit(event);
                break;
            case DebugEvent::Type::CACHE_MISS:
                handleCacheMiss(event);
                break;
        }
    }
    
    void handlePipelineCreated(const DebugEvent& event) {
        // 处理管线创建事件
        PipelineInfo info;
        info.desc = event.pipelineDesc;
        info.captureTime = std::chrono::steady_clock::now();
        
        captureShaderInfo(info);
        captureUniformInfo(info);
        captureAttributeInfo(info);
        captureRenderPassInfo(info);
        
        mPipelineRecords.push_back(info);
        
        // 限制记录数量
        if (mPipelineRecords.size() > mDebugConfig.maxPipelineRecords) {
            mPipelineRecords.pop_front();
        }
    }
    
    void handlePipelineDestroyed(const DebugEvent& event) {
        // 处理管线销毁事件
        auto it = std::find_if(mPipelineRecords.begin(), mPipelineRecords.end(),
                              [&event](const PipelineInfo& info) {
                                  return info.desc.name == event.pipelineDesc.name;
                              });
        
        if (it != mPipelineRecords.end()) {
            it->destructionTime = std::chrono::steady_clock::now();
        }
    }
    
    void handleCompilationStarted(const DebugEvent& event) {
        // 处理编译开始事件
        CompilationRecord record;
        record.pipelineName = event.pipelineDesc.name;
        record.priority = event.priority;
        record.startTime = std::chrono::steady_clock::now();
        
        mCompilationQueue.push(record);
    }
    
    void handleCompilationCompleted(const DebugEvent& event) {
        // 处理编译完成事件
        while (!mCompilationQueue.empty()) {
            auto record = mCompilationQueue.front();
            mCompilationQueue.pop();
            
            if (record.pipelineName == event.pipelineDesc.name) {
                auto duration = std::chrono::steady_clock::now() - record.startTime;
                
                // 更新编译统计
                mCompilationStats[record.priority].count++;
                mCompilationStats[record.priority].avgDuration = 
                    (mCompilationStats[record.priority].avgDuration * 
                     (mCompilationStats[record.priority].count - 1) + duration) / 
                    mCompilationStats[record.priority].count;
                
                if (duration > mCompilationStats[record.priority].maxDuration) {
                    mCompilationStats[record.priority].maxDuration = duration;
                }
                
                if (duration < mCompilationStats[record.priority].minDuration) {
                    mCompilationStats[record.priority].minDuration = duration;
                }
                
                break;
            }
        }
    }
    
    void handleCacheHit(const DebugEvent& event) {
        // 处理缓存命中事件
        mCacheStats.hits++;
    }
    
    void handleCacheMiss(const DebugEvent& event) {
        // 处理缓存未命中事件
        mCacheStats.misses++;
    }
    
    void captureShaderInfo(PipelineInfo& info) {
        // 捕获着色器信息
        for (uint32_t i = 0; i < info.desc.shaderCount; ++i) {
            ShaderInfo shader;
            shader.name = info.desc.shaders[i].name;
            shader.type = info.desc.shaders[i].type;
            shader.size = info.desc.shaders[i].size;
            shader.compileTime = std::chrono::steady_clock::now();
            
            info.shaders.push_back(shader);
            info.shaderMemory += shader.size;
        }
    }
    
    void captureUniformInfo(PipelineInfo& info) {
        // 捕获 Uniform 信息
        for (uint32_t i = 0; i < info.desc.uniformCount; ++i) {
            UniformInfo uniform;
            uniform.name = info.desc.uniforms[i].name;
            uniform.type = info.desc.uniforms[i].type;
            uniform.size = info.desc.uniforms[i].size;
            uniform.location = info.desc.uniforms[i].location;
            
            info.uniforms.push_back(uniform);
            info.uniformMemory += uniform.size;
        }
    }
    
    void captureAttributeInfo(PipelineInfo& info) {
        // 捕获属性信息
        for (uint32_t i = 0; i < info.desc.attributeCount; ++i) {
            AttributeInfo attribute;
            attribute.name = info.desc.attributes[i].name;
            attribute.type = info.desc.attributes[i].type;
            attribute.size = info.desc.attributes[i].size;
            attribute.location = info.desc.attributes[i].location;
            
            info.attributes.push_back(attribute);
            info.attributeMemory += attribute.size;
        }
    }
    
    void captureRenderPassInfo(PipelineInfo& info) {
        // 捕获渲染通道信息
        for (uint32_t i = 0; i < info.desc.renderPassCount; ++i) {
            RenderPassInfo renderPass;
            renderPass.name = info.desc.renderPasses[i].name;
            renderPass.width = info.desc.renderPasses[i].width;
            renderPass.height = info.desc.renderPasses[i].height;
            renderPass.format = info.desc.renderPasses[i].format;
            
            info.renderPasses.push_back(renderPass);
        }
    }
    
    void logPipelineInfo(const PipelineInfo& info) {
        LOG(INFO) << "Pipeline Info: " << info.desc.name;
        LOG(INFO) << "  Shader Count: " << info.shaders.size();
        LOG(INFO) << "  Uniform Count: " << info.uniforms.size();
        LOG(INFO) << "  Attribute Count: " << info.attributes.size();
        LOG(INFO) << "  Render Pass Count: " << info.renderPasses.size();
        LOG(INFO) << "  Total Memory: " << info.shaderMemory + info.uniformMemory + info.attributeMemory;
    }
    
    // 成员变量
    PipelineManager* mManager;
    
    bool mDebugMode;
    bool mVerboseLogging;
    
    DebugConfig mDebugConfig;
    
    std::deque<PipelineInfo> mPipelineRecords;
    std::unordered_map<Priority, CompilationStat> mCompilationStats;
    CacheStat mCacheStats;
    MemoryStat mMemoryStats;
    
    std::queue<CompilationRecord> mCompilationQueue;
    std::queue<CacheRecord> mCacheQueue;
    std::queue<FrameRecord> mFrameQueue;
    
    std::chrono::steady_clock::time_point mLastExportTime;
};
```

## 6. 应用集成指南

### 6.1 简单集成示例

```java
// Android 应用集成示例
public class VulkanPipelineManager {
    private PipelineManager mPipelineManager;
    private DebugTools mDebugTools;
    
    public void initialize(Context context) {
        // 初始化管线管理器
        mPipelineManager = new PipelineManager(context);
        
        // 启用调试模式
        mDebugTools = new DebugTools(mPipelineManager);
        mDebugTools.enableDebugMode();
        
        // 设置管线回调
        mPipelineManager.setPipelineCallback(this::onPipelineReady);
    }
    
    public void createPipeline(PipelineDesc desc) {
        // 异步创建管线
        mPipelineManager.compilePipelineAsync(desc, this::onPipelineCreated);
    }
    
    private void onPipelineCreated(PipelineHandle handle, boolean success) {
        if (success) {
            // 管线创建成功
            mDebugTools.capturePipelineInfo(handle.getDesc());
            
            // 使用管线进行渲染
            renderWithPipeline(handle);
        } else {
            // 管线创建失败
            handlePipelineCreationFailed(handle.getDesc());
        }
    }
    
    private void renderWithPipeline(PipelineHandle handle) {
        // 使用管线进行渲染
        RenderCommand cmd = new RenderCommand();
        cmd.pipeline = handle;
        
        // 添加渲染命令
        mPipelineManager.submitRenderCommand(cmd);
    }
    
    private void handlePipelineCreationFailed(PipelineDesc desc) {
        // 处理管线创建失败
        Log.e("VulkanPipelineManager", "Pipeline creation failed: " + desc.name);
        
        // 尝试降级处理
        PipelineDesc fallbackDesc = createFallbackPipeline(desc);
        createPipeline(fallbackDesc);
    }
    
    private PipelineDesc createFallbackPipeline(PipelineDesc original) {
        // 创建降级管线
        PipelineDesc fallback = new PipelineDesc();
        fallback.name = original.name + "_fallback";
        fallback.priority = Priority.LOW;
        
        // 使用简化的着色器和材质
        fallback.shaderCount = 1;
        fallback.shaders = new ShaderDesc[] {
            createSimpleShader()
        };
        
        return fallback;
    }
    
    private ShaderDesc createSimpleShader() {
        // 创建简单的着色器
        ShaderDesc shader = new ShaderDesc();
        shader.name = "simple_vertex";
        shader.type = ShaderType.VERTEX;
        shader.source = "simple_shader.glsl";
        shader.priority = Priority.HIGH;
        
        return shader;
    }
}
```

### 6.2 性能优化集成

```java
// 性能优化集成
public class PerformanceOptimizedPipelineManager {
    private PipelineManager mPipelineManager;
    private PriorityScheduler mPriorityScheduler;
    private MemoryManager mMemoryManager;
    private PerformanceMonitor mPerformanceMonitor;
    
    public void initialize(Context context) {
        // 初始化各个组件
        mPipelineManager = new PipelineManager(context);
        mPriorityScheduler = new PriorityScheduler();
        mMemoryManager = new MemoryManager();
        mPerformanceMonitor = new PerformanceMonitor();
        
        // 设置性能回调
        mPerformanceMonitor.setPerformanceCallback(this::onPerformanceEvent);
    }
    
    public void submitRenderTask(RenderTask task) {
        // 根据任务类型选择优先级
        Priority priority = determinePriority(task);
        
        // 提交到优先级调度器
        mPriorityScheduler.scheduleCompilation(
            task.pipelineDesc,
            priority,
            handle -> onPipelineReady(handle, task)
        );
    }
    
    private Priority determinePriority(RenderTask task) {
        // 根据任务类型确定优先级
        switch (task.type) {
            case RenderTask.Type.CRITICAL:
                return Priority.EMERGENCY;
            case RenderTask.Type.IMPORTANT:
                return Priority.HIGH;
            case RenderTask.Type.NORMAL:
                return Priority.NORMAL;
            case RenderTask.Type.OPTIONAL:
                return Priority.LOW;
            case RenderTask.Type.BACKGROUND:
                return Priority.BACKGROUND;
            default:
                return Priority.NORMAL;
        }
    }
    
    private void onPipelineReady(PipelineHandle handle, RenderTask task) {
        if (handle.isValid()) {
            // 管线就绪，执行渲染任务
            executeRenderTask(task);
        } else {
            // 管线失败，重试或降级
            handlePipelineFailure(task);
        }
    }
    
    private void executeRenderTask(RenderTask task) {
        // 执行渲染任务
        RenderCommand cmd = createRenderCommand(task);
        mPipelineManager.submitRenderCommand(cmd);
        
        // 记录性能数据
        mPerformanceMonitor.recordFrameTime(System.nanoTime());
    }
    
    private void handlePipelineFailure(RenderTask task) {
        // 处理管线失败
        if (task.retryCount < task.maxRetries) {
            // 重试
            task.retryCount++;
            submitRenderTask(task);
        } else {
            // 降级处理
            RenderTask fallbackTask = createFallbackTask(task);
            submitRenderTask(fallbackTask);
        }
    }
    
    private RenderTask createFallbackTask(RenderTask original) {
        // 创建降级任务
        RenderTask fallback = new RenderTask();
        fallback.type = RenderTask.Type.OPTIONAL;
        fallback.pipelineDesc = createFallbackPipeline(original.pipelineDesc);
        fallback.retryCount = 0;
        fallback.maxRetries = original.maxRetries;
        
        return fallback;
    }
    
    private PipelineDesc createFallbackPipeline(PipelineDesc original) {
        // 创建降级管线描述
        PipelineDesc fallback = new PipelineDesc();
        fallback.name = original.name + "_fallback";
        fallback.priority = Priority.LOW;
        
        // 使用简化的着色器
        fallback.shaderCount = 1;
        fallback.shaders = new ShaderDesc[] {
            createLowComplexityShader()
        };
        
        // 使用简化的材质
        fallback.uniformCount = 2;
        fallback.uniforms = new UniformDesc[] {
            createSimpleUniform(),
            createViewProjectionUniform()
        };
        
        return fallback;
    }
    
    private void onPerformanceEvent(PerformanceEvent event) {
        // 处理性能事件
        switch (event.type) {
            case PerformanceEvent.Type.FRAME_RATE_DROP:
                handleFrameRateDrop(event);
                break;
            case PerformanceEvent.Type.MEMORY_PRESSURE:
                handleMemoryPressure(event);
                break;
            case PerformanceEvent.Type.PIPELINE_CACHE_MISS:
                handleCacheMiss(event);
                break;
        }
    }
    
    private void handleFrameRateDrop(PerformanceEvent event) {
        // 处理帧率下降
        Log.w("PerformanceOptimizedPipelineManager", 
              "Frame rate dropped: " + event.frameRate + " fps");
        
        // 降低管线复杂度
        reducePipelineComplexity();
    }
    
    private void handleMemoryPressure(PerformanceEvent event) {
        // 处理内存压力
        Log.w("PerformanceOptimizedPipelineManager", 
              "Memory pressure detected: " + event.memoryUsage + " MB");
        
        // 释放未使用的管线
        releaseUnusedPipelines();
        
        // 压缩内存使用
        mMemoryManager.optimizeMemoryUsage();
    }
    
    private void handleCacheMiss(PerformanceEvent event) {
        // 处理缓存未命中
        Log.i("PerformanceOptimizedPipelineManager", 
              "Cache miss for pipeline: " + event.pipelineName);
        
        // 预编译常用管线
        precompileCommonPipelines();
    }
    
    private void reducePipelineComplexity() {
        // 降低管线复杂度
        // 1. 减少着色器复杂度
        reduceShaderComplexity();
        
        // 2. 降低材质质量
        reduceMaterialQuality();
        
        // 3. 简化渲染通道
        simplifyRenderPasses();
    }
    
    private void reduceShaderComplexity() {
        // 减少着色器复杂度
        // 实现略...
    }
    
    private void reduceMaterialQuality() {
        // 降低材质质量
        // 实现略...
    }
    
    private void simplifyRenderPasses() {
        // 简化渲染通道
        // 实现略...
    }
    
    private void releaseUnusedPipelines() {
        // 释放未使用的管线
        // 实现略...
    }
    
    private void precompileCommonPipelines() {
        // 预编译常用管线
        // 实现略...
    }
}
```

## 7. 最佳实践

### 7.1 开发最佳实践

#### 7.1.1 管线复用策略

```cpp
// 管线复用策略
class PipelineReuseStrategy {
public:
    enum class ReusePolicy {
        ALWAYS,           // 总是复用
        WHEN_POSSIBLE,    // 可能时复用
        NEVER            // 不复用
    };
    
    bool shouldReusePipeline(const PipelineDesc& desc) {
        // 根据策略决定是否复用管线
        switch (mReusePolicy) {
            case ReusePolicy::ALWAYS:
                return true;
            case ReusePolicy::WHEN_POSSIBLE:
                return isReusePossible(desc);
            case ReusePolicy::NEVER:
                return false;
        }
    }
    
    PipelineHandle getPipeline(const PipelineDesc& desc) {
        // 首先尝试从缓存获取
        PipelineHandle handle;
        if (mPipelineCache->find(desc, handle)) {
            return handle;
        }
        
        // 缓存未命中，创建新管线
        handle = mPipelineManager->createPipeline(desc);
        
        // 添加到缓存
        mPipelineCache->add(desc, handle);
        
        return handle;
    }
    
private:
    bool isReusePossible(const PipelineDesc& desc) {
        // 检查是否可以复用管线
        // 1. 检查兼容性
        if (!isCompatible(desc)) {
            return false;
        }
        
        // 2. 检查性能影响
        if (wouldCausePerformancePenalty(desc)) {
            return false;
        }
        
        // 3. 检查内存使用
        if (wouldExceedMemoryLimit(desc)) {
            return false;
        }
        
        return true;
    }
    
    bool isCompatible(const PipelineDesc& desc) {
        // 检查管线兼容性
        for (const auto& existing : mCompatiblePipelines) {
            if (arePipelinesCompatible(desc, existing)) {
                return true;
            }
        }
        return false;
    }
    
    bool wouldCausePerformancePenalty(const PipelineDesc& desc) {
        // 检查是否会造成性能损失
        auto compilationTime = estimateCompilationTime(desc);
        
        // 如果编译时间超过帧时间的 10%，可能造成性能损失
        float frameBudget = 16.0f; // 16ms
        return compilationTime > frameBudget * 0.1f;
    }
    
    bool wouldExceedMemoryLimit(const PipelineDesc& desc) {
        // 检查是否会超出内存限制
        size_t memoryUsage = calculateMemoryUsage(desc);
        size_t currentUsage = mPipelineCache->getTotalMemoryUsage();
        
        return currentUsage + memoryUsage > mMemoryLimit;
    }
    
    bool arePipelinesCompatible(const PipelineDesc& a, const PipelineDesc& b) {
        // 检查两个管线是否兼容
        // 实现兼容性检查逻辑
        return false; // 简化实现
    }
    
    std::chrono::milliseconds estimateCompilationTime(const PipelineDesc& desc) {
        // 估计管线编译时间
        std::chrono::milliseconds time(0);
        
        // 着色器编译时间
        for (uint32_t i = 0; i < desc.shaderCount; ++i) {
            time += mShaderCompiler->estimateCompileTime(desc.shaders[i]);
        }
        
        // 其他编译时间...
        return time;
    }
    
    size_t calculateMemoryUsage(const PipelineDesc& desc) {
        // 计算管线内存使用量
        size_t memory = 0;
        
        // 着色器内存
        for (uint32_t i = 0; i < desc.shaderCount; ++i) {
            memory += desc.shaders[i].size;
        }
        
        // 其他内存计算...
        return memory;
    }
    
    // 成员变量
    ReusePolicy mReusePolicy = ReusePolicy::WHEN_POSSIBLE;
    std::unique_ptr<PipelineCache> mPipelineCache;
    std::unique_ptr<PipelineManager> mPipelineManager;
    std::vector<PipelineDesc> mCompatiblePipelines;
    
    size_t mMemoryLimit = 100 * 1024 * 1024; // 100MB
};
```

#### 7.1.2 内存管理最佳实践

```cpp
// 内存管理最佳实践
class MemoryBestPractices {
public:
    void optimizeMemoryUsage() {
        // 1. 管线池化
        implementPipelinePooling();
        
        // 2. 内存预分配
        implementMemoryPreallocation();
        
        // 3. 内存监控
        implementMemoryMonitoring();
        
        // 4. 内存压缩
        implementMemoryCompression();
    }
    
private:
    void implementPipelinePooling() {
        // 实现管线池化
        PipelinePool pool;
        
        // 创建常用管线
        auto commonPipelines = createCommonPipelines();
        for (const auto& desc : commonPipelines) {
            pool.add(desc);
        }
        
        // 使用管线池
        PipelineHandle handle = pool.get(desc);
        if (!handle.isValid()) {
            handle = createNewPipeline(desc);
            pool.add(desc, handle);
        }
    }
    
    void implementMemoryPreallocation() {
        // 实现内存预分配
        MemoryPreallocator preallocator;
        
        // 预分配着色器内存
        preallocator.preallocateShaderMemory(100 * 1024 * 1024); // 100MB
        
        // 预分配 Uniform 内存
        preallocator.preallocateUniformMemory(50 * 1024 * 1024); // 50MB
        
        // 预分配属性内存
        preallocator.preallocateAttributeMemory(20 * 1024 * 1024); // 20MB
    }
    
    void implementMemoryMonitoring() {
        // 实现内存监控
        MemoryMonitor monitor;
        
        // 注册内存监控回调
        monitor.setMemoryCallback([this](size_t used, size_t total) {
            onMemoryUsageChanged(used, total);
        });
        
        // 启动内存监控
        monitor.start();
    }
    
    void implementMemoryCompression() {
        // 实现内存压缩
        MemoryCompressor compressor;
        
        // 压缩不常用的管线
        compressor.compressUnusedPipelines();
        
        // 压缩重复的着色器
        compressor.compressDuplicateShaders();
        
        // 压缩重复的 Uniform
        compressor.compressDuplicateUniforms();
    }
    
    void onMemoryUsageChanged(size_t used, size_t total) {
        // 内存使用变化回调
        double usageRatio = static_cast<double>(used) / total;
        
        if (usageRatio > 0.8) {
            // 内存使用过高，触发清理
            performMemoryCleanup();
        }
    }
    
    void performMemoryCleanup() {
        // 执行内存清理
        // 1. 释放不常用的管线
        releaseUnusedPipelines();
        
        // 2. 压缩内存
        compressMemory();
        
        // 3. 调整内存池大小
        adjustMemoryPools();
    }
};
```

### 7.2 调试与优化技巧

#### 7.2.1 性能分析方法

```java
// 性能分析方法
class PerformanceAnalyzer {
    public void analyzePipelinePerformance() {
        // 1. 收集性能数据
        PerformanceData data = collectPerformanceData();
        
        // 2. 分析性能瓶颈
        PerformanceBottleneck[] bottlenecks = analyzeBottlenecks(data);
        
        // 3. 提出优化建议
        OptimizationSuggestion[] suggestions = generateOptimizationSuggestions(bottlenecks);
        
        // 4. 执行优化
        executeOptimizations(suggestions);
    }
    
    private PerformanceData collectPerformanceData() {
        // 收集性能数据
        PerformanceData data = new PerformanceData();
        
        // 收集编译时间数据
        data.compilationTimes = collectCompilationTimes();
        
        // 收集缓存数据
        data.cacheStats = collectCacheStats();
        
        // 收集内存数据
        data.memoryStats = collectMemoryStats();
        
        // 收集帧时间数据
        data.frameTimes = collectFrameTimes();
        
        return data;
    }
    
    private CompilationTime[] collectCompilationTimes() {
        // 收集编译时间数据
        List<CompilationTime> times = new ArrayList<>();
        
        // 从性能监控获取数据
        PerformanceMonitor monitor = getPerformanceMonitor();
        times = monitor.getCompilationTimes();
        
        return times.toArray(new CompilationTime[0]);
    }
    
    private CacheStats collectCacheStats() {
        // 收集缓存统计
        CacheStats stats = new CacheStats();
        
        // 从缓存管理器获取数据
        PipelineCache cache = getPipelineCache();
        stats.hitRate = cache.getHitRate();
        stats.missRate = cache.getMissRate();
        stats.averageCacheTime = cache.getAverageCacheTime();
        
        return stats;
    }
    
    private MemoryStats collectMemoryStats() {
        // 收集内存统计
        MemoryStats stats = new MemoryStats();
        
        // 从内存管理器获取数据
        MemoryManager memory = getMemoryManager();
        stats.totalMemory = memory.getTotalMemory();
        stats.usedMemory = memory.getUsedMemory();
        stats.shaderMemory = memory.getShaderMemory();
        stats.uniformMemory = memory.getUniformMemory();
        stats.attributeMemory = memory.getAttributeMemory();
        
        return stats;
    }
    
    private FrameTime[] collectFrameTimes() {
        // 收集帧时间数据
        List<FrameTime> times = new ArrayList<>();
        
        // 从性能监控获取数据
        PerformanceMonitor monitor = getPerformanceMonitor();
        times = monitor.getFrameTimes();
        
        return times.toArray(new FrameTime[0]);
    }
    
    private PerformanceBottleneck[] analyzeBottlenecks(PerformanceData data) {
        // 分析性能瓶颈
        List<PerformanceBottleneck> bottlenecks = new ArrayList<>();
        
        // 1. 分析编译时间瓶颈
        if (data.compilationTimes.length > 0) {
            long avgCompilationTime = Arrays.stream(data.compilationTimes)
                .mapToLong(CompilationTime::getDuration)
                .average()
                .orElse(0);
            
            if (avgCompilationTime > 10000) { // 10ms
                bottlenecks.add(new PerformanceBottleneck(
                    "编译时间过长", 
                    avgCompilationTime, 
                    "考虑优化着色器编译或使用异步编译"
                ));
            }
        }
        
        // 2. 分析缓存瓶颈
        if (data.cacheStats.missRate > 0.5) { // 50%
            bottlenecks.add(new PerformanceBottleneck(
                "缓存命中率低", 
                data.cacheStats.missRate * 100, 
                "考虑增加缓存大小或优化缓存策略"
            ));
        }
        
        // 3. 分析内存瓶颈
        if (data.memoryStats.usedMemory > data.memoryStats.totalMemory * 0.8) { // 80%
            bottlenecks.add(new PerformanceBottleneck(
                "内存使用过高", 
                data.memoryStats.usedMemory, 
                "考虑释放不使用的管线或压缩内存"
            ));
        }
        
        // 4. 分析帧时间瓶颈
        if (data.frameTimes.length > 0) {
            long avgFrameTime = Arrays.stream(data.frameTimes)
                .mapToLong(FrameTime::getDuration)
                .average()
                .orElse(0);
            
            if (avgFrameTime > 16667) { // 超过 60fps 的帧时间
                bottlenecks.add(new PerformanceBottleneck(
                    "帧时间过长", 
                    avgFrameTime, 
                    "考虑降低管线复杂度或优化渲染算法"
                ));
            }
        }
        
        return bottlenecks.toArray(new PerformanceBottleneck[0]);
    }
    
    private OptimizationSuggestion[] generateOptimizationSuggestions(PerformanceBottleneck[] bottlenecks) {
        // 生成优化建议
        List<OptimizationSuggestion> suggestions = new ArrayList<>();
        
        for (PerformanceBottleneck bottleneck : bottlenecks) {
            switch (bottleneck.getType()) {
                case "编译时间过长":
                    suggestions.addAll(generateCompilationOptimizationSuggestions());
                    break;
                case "缓存命中率低":
                    suggestions.addAll(generateCacheOptimizationSuggestions());
                    break;
                case "内存使用过高":
                    suggestions.addAll(generateMemoryOptimizationSuggestions());
                    break;
                case "帧时间过长":
                    suggestions.addAll(generateFrameTimeOptimizationSuggestions());
                    break;
            }
        }
        
        return suggestions.toArray(new OptimizationSuggestion[0]);
    }
    
    private List<OptimizationSuggestion> generateCompilationOptimizationSuggestions() {
        // 生成编译优化建议
        List<OptimizationSuggestion> suggestions = new ArrayList<>();
        
        suggestions.add(new OptimizationSuggestion(
            "使用异步编译",
            "启用 PipelineManager 的异步编译功能",
            "mPipelineManager.enableAsyncCompilation(true);"
        ));
        
        suggestions.add(new OptimizationSuggestion(
            "预编译常用管线",
            "预编译常用的着色器和管线",
            "mPipelineManager.precompileCommonPipelines();"
        ));
        
        suggestions.add(new OptimizationSuggestion(
            "简化着色器复杂度",
            "减少着色器的复杂度和依赖",
            "使用简化的着色器变体"
        ));
        
        return suggestions;
    }
    
    private List<OptimizationSuggestion> generateCacheOptimizationSuggestions() {
        // 生成缓存优化建议
        List<OptimizationSuggestion> suggestions = new ArrayList<>();
        
        suggestions.add(new OptimizationSuggestion(
            "增加缓存大小",
            "扩大管线缓存的大小",
            "mPipelineManager.setCacheSize(200);"
        ));
        
        suggestions.add(new OptimizationSuggestion(
            "优化缓存策略",
            "使用 LRU 缓存策略",
            "mPipelineManager.setCacheStrategy(CacheStrategy.LRU);"
        ));
        
        suggestions.add(new OptimizationSuggestion(
            "启用内存缓存",
            "启用内存中的管线缓存",
            "mPipelineManager.enableMemoryCache(true);"
        ));
        
        return suggestions;
    }
    
    private List<OptimizationSuggestion> generateMemoryOptimizationSuggestions() {
        // 生成内存优化建议
        List<OptimizationSuggestion> suggestions = new ArrayList<>();
        
        suggestions.add(new OptimizationSuggestion(
            "释放不使用的管线",
            "定期清理不使用的管线",
            "mPipelineManager.cleanupUnusedPipelines();"
        ));
        
        suggestions.add(new OptimizationSuggestion(
            "使用内存池",
            "实现内存池来减少频繁分配",
            "mMemoryManager.useMemoryPool(true);"
        ));
        
        suggestions.add(new OptimizationSuggestion(
            "压缩重复数据",
            "压缩重复的着色器和材质",
            "mMemoryManager.compressDuplicateData();"
        ));
        
        return suggestions;
    }
    
    private List<OptimizationSuggestion> generateFrameTimeOptimizationSuggestions() {
        // 生成帧时间优化建议
        List<OptimizationSuggestion> suggestions = new ArrayList<>();
        
        suggestions.add(new OptimizationSuggestion(
            "降低渲染分辨率",
            "在性能敏感时降低渲染分辨率",
            "mRenderer.setRenderScale(0.8f);"
        ));
        
        suggestions.add(new OptimizationSuggestion(
            "简化材质",
            "使用简化版本的材质",
            "mMaterial.useSimplifiedVersion(true);"
        ));
        
        suggestions.add(new OptimizationSuggestion(
            "减少绘制调用",
            "合并多个绘制调用",
            "mRenderer.batchDrawCalls();"
        ));
        
        return suggestions;
    }
    
    private void executeOptimizations(OptimizationSuggestion[] suggestions) {
        // 执行优化建议
        for (OptimizationSuggestion suggestion : suggestions) {
            try {
                // 执行优化代码
                eval(suggestion.getCode());
                
                // 记录优化日志
                Log.i("PerformanceAnalyzer", 
                      "Applied optimization: " + suggestion.getDescription());
            } catch (Exception e) {
                Log.e("PerformanceAnalyzer", 
                      "Failed to apply optimization: " + e.getMessage());
            }
        }
    }
}
```

## 8. 总结

Android 17 的 GPU Vulkan 异步编译管线管理器为开发者提供了强大的渲染管线管理能力。通过深入理解其架构和实现机制，开发者可以构建更高效、更稳定的图形应用。

### 8.1 关键要点

1. **异步编译架构**：通过 PipelineManager、AsyncCompiler、PipelinePacer 和 PipelineCache 四个核心组件实现高效的管线管理
2. **优先级调度策略**：支持紧急、高、正常、低、后台五个优先级的调度策略
3. **内存管理优化**：通过内存池、预分配、碎片整理等技术优化内存使用
4. **性能监控系统**：提供全面的性能监控和调试工具
5. **灵活的集成方式**：支持简单的集成和高级的性能优化集成

### 8.2 实施建议

1. **选择合适的管线复用策略**：根据应用场景选择 ALWAYS、WHEN_POSSIBLE 或 NEVER 策略
2. **实现内存监控和优化**：建立内存使用监控，及时释放不使用的资源
3. **使用性能分析工具**：定期分析性能瓶颈，制定优化策略
4. **处理管线失败情况**：实现合理的降级和重试机制
5. **保持调试能力**：启用调试模式，及时发现问题

通过系统地应用这些技术和策略，开发者可以充分利用 Android 17 的 GPU 渲染管线管理能力，构建高性能的图形应用。