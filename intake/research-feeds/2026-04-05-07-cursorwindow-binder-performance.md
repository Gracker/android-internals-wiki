## [研究] CursorWindow 2MB 限制与 Binder 传输的内部机制

- **来源**：AOSP + StackOverflow 高票回答 + Medium 技术分析
- **作者/机构**：AOSP / Android 技术社区
- **日期**：2026-04-05
- **四维评分**：相关性 4/5 · 技术深度 5/5 · 时效性 4/5 · 可验证性 5/5 · **总分 18/20**
- **映射章节**：1.10 ContentProvider 性能与优化 / 1.4 Binder IPC 机制与性能影响
- **映射锚点**：CursorWindow 大小限制/SQLiteCursor 内部分页机制/Binder 事务缓冲区/大数据传输优化
- **摘要**：CursorWindow 默认 2MB，通过 Binder 共享内存传输。SQLiteCursor 内部分页机制在翻页时会从头重新查询并跳行，类似 SQL OFFSET，随偏移量增大性能急剧下降。Binder 事务缓冲区 1MB 共享所有并发事务，实际 0.5MB 即可能触发 TransactionTooLargeException。

### 关键发现
1. **CursorWindow 内部机制**：默认大小 2MB（CursorWindow.CURSOR_WINDOW_SIZE）。SQLiteCursor 在请求行不在当前窗口时，会从头重新执行查询并跳过已读行——这意味着第 N 页的查询实际是 `SELECT ... LIMIT windowSize OFFSET (N * windowSize / 3)`，复杂度随页数线性增长。
2. **Binder 事务缓冲区**：整个进程共享 1MB Binder 缓冲区，所有并发事务共享此额度。即使单个事务只有 0.5MB，多个并发 ContentProvider 调用也可能触发 `TransactionTooLargeException`。
3. **Android P (API 28) 改进**：新增 API 允许禁用 "1/3 窗口预读" 启发式、可配置 CursorWindow 大小。但最佳实践仍是小查询 + 分页。
4. **优化策略**：使用 Paging Library + Room、避免大 BLOB/JSON 存为单列、始终指定 projection、大数据走文件描述符或共享内存而非 CursorWindow。

### 可直接引用段落
> CursorWindow 是 ContentProvider 跨进程数据传输的核心载体。它底层使用 Binder 共享内存，默认大小 2MB。当查询结果超过窗口容量时，SQLiteCursor 会从头重新执行查询并跳过已读行——这是一种类似 `SQL OFFSET` 的低效翻页机制，偏移量越大性能越差。

> 更隐蔽的问题是 Binder 事务缓冲区。整个进程的 Binder 缓冲区只有 1MB，且所有并发事务共享。在高并发场景下，多个 ContentProvider 调用可能累积超过缓冲区上限，触发 `TransactionTooLargeException`。在实践中，数据载荷达到 0.5MB 时就可能触发此异常。

### 与 queue.json 联动
- 优先级调整建议：无
- 素材路径建议：同时补充到 §1.4 Binder IPC
