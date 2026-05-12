

## 参考资料

### Android17 为什么重写 MessageQueue
- 来源：https://juejin.cn/post/7612812060795093002
- 类型：技术文章
- 摘要：Android 17 用 DeliQueue 替换了运行二十年的 MessageQueue 架构。核心变化：无锁数据结构（写入端用 Treiber Stack + CAS，消费端用 Min-Heap）、移除 synchronized 锁、用墓碑标记处理消息取消。Google Perfetto 分析确认锁竞争是系统级普遍问题（Launcher 拍照返回卡顿 18ms 超过帧预算）。ARM LSE 硬件指令加持下高竞争场景快约 3 倍。Breaking change：mMessages 字段永远返回 null，Espresso 和 Robolectric 需要升级。
- 入库时间：2026-05-10
- 评分：20/20
