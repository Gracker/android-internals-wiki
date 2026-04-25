# AIW 自动 Review 任务报告 (19.15)

## 二、总体结论
- 总体技术评分：4.4/5
- 是否建议回炉：否
- 主要风险：非商店安装场景下的 Profile 生效链路描述存在缺环（依赖 ProfileInstaller）。
- 评分理由：清晰区分了 Baseline 与 Startup Profiles，并对 ProfileVerifier 的各种状态码做了精确解读。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 4.5/5 | 1 |
| 原理链完整性 | 4.0/5 | 1 |
| 版本差异覆盖 | 5.0/5 | 0 |
| 知识盲区 | 4.0/5 | 1 |
| 数据/案例支撑 | 4.5/5 | 0 |
| 交叉引用一致性 | 5.0/5 | 0 |

## 五、P1 问题
- [P1][源码准确性][ProfileInstaller 激活风险]
- 原文问题：提到非 Play 安装依赖 `ProfileInstaller`。
- 源码锚点：`androidx.profileinstaller.ProfileInstallReceiver`。
- 关键逻辑：`ProfileInstaller` 默认通过 `androidx.startup` 初始化。如果业务为了优化启动禁用了 `androidx.startup` 且未手动初始化 `ProfileInstaller`，或者混淆了 `ProfileInstallReceiver`，则 `adb shell cmd package compile -m speed-profile` 等命令将无法获取 profile 信号。
- 建议：增加“混淆与初始化检查”锚点。

- [P1][知识盲区][R8 混淆对 Profile 匹配的影响]
- 原文问题：未提及 R8 混淆后的规则匹配。
- 缺失内容：Baseline Profile 规则是在混淆前生成的。AGP 在打包时会自动将规则映射到混淆后的名称，但如果开发者手动移动 `.prof` 文件或使用了非标混淆流程，会导致 Profile 命中率为 0。
- 建议：提醒开发者检查 AAB 产物中解密后的 profile 记录是否与混淆后的 `mapping.txt` 一致。

## 九、可闭环输出
### 9.4 可复用知识资产
- 关键路径：`assets/dexopt/baseline.prof` 是 APK 内的存放位置。
- 技术结论：Startup Profiles 优化的是 DEX 布局（减少 IO Wait），Baseline Profiles 优化的是代码执行速度（减少 JIT 成本），两者互补。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-25-15-15-external-review.md`
