## [研究] Android 17 (API 37) Static Final Field 强制不可变与编译优化影响
- **来源**：https://developer.android.com/about/versions/17/behavior-changes-37
- **作者/机构**：Google / Android Developer Documentation
- **日期**：2026 (API 37 Developer Preview)
- **四维评分**：相关性 4/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 4/5 · **总分 17/20**
- **映射章节**：§4.3 ART虚拟机内存管理 + §1.6 Android版本演进中的架构变化
- **映射锚点**：ART 编译优化、dex2oat 常量折叠、AOT 编译策略、版本行为变更
- **摘要**：Android 17 (API 37) 强制禁止通过反射或 JNI 修改 static final 字段。这一行为变更使得 ART 的 dex2oat 编译器可以更激进地进行常量折叠和内联优化，因为编译器可以确信这些字段的值不会在运行时被修改。此前，部分框架和库（如 Mockito、序列化工具）依赖反射修改 static final 字段的行为，需要迁移。

### 关键发现
1. **反射限制**：targetSdkVersion ≥ 37 的应用，通过 `Field.setAccessible(true)` + `Field.set()` 修改 static final 字段将抛出 `IllegalAccessException`。此前虽然 Java 规范不鼓励这种行为，但 Android 运行时并未严格执行。
2. **JNI 崩溃**：通过 JNI API（如 `SetStaticLongField()`）尝试修改 static final 字段将导致应用崩溃（硬失败），而非静默失败。这比反射路径更严格。
3. **编译优化收益**：static final 字段的不可变性保证使 dex2oat 可以安全地进行常量折叠（constant folding）——直接将字段值内联到编译后的机器码中，避免每次访问的字段查找开销。这与 Java 编译器对 `static final` String 和基本类型的内联行为一致。
4. **对框架的影响**：使用 Mockito mock static final 字段、依赖反射注入的 DI 框架、通过反射修改 BuildConfig 字段的构建工具等都需要适配。Mockito 团队已提前发布了兼容方案（使用 inline mock maker）。
5. **与 AutoFDO 的协同**：结合 Android 16/17 引入的内核级 AutoFDO 优化，static final 的强制不可变使 profile-guided 优化可以更准确地预测热路径中的常量值，进一步提升 AOT 编译质量。

### 可直接引用段落
> For apps targeting Android 17 (API level 37) or higher, modifying static final fields using reflection will throw an IllegalAccessException. Using JNI APIs like SetStaticLongField() on these fields will cause the app to crash. This enables more aggressive compilation optimizations since the compiler can guarantee the immutability of these fields.
> — Android 17 Behavior Changes, developer.android.com

> When dex2oat compiles static final fields, their values can be "inlined" directly into the native code during optimization. If a value is inlined, attempting to change it at runtime via reflection might not have the desired effect, as the compiled code would still use the original, inlined value. The new enforcement in API 37 formalizes this behavior.
> — Android Developer Documentation

### 与 queue.json 联动
- 优先级调整建议：§4.3 ART虚拟机内存管理 的编译优化部分可补充此素材
- 素材路径建议：§1.6 版本演进中 Android 17 行为变更章节可直接引用
