#!/usr/bin/env python3
"""Fuse chapter 7 framework-specific articles into the chapter 22 owners.

The transform keeps chapter 7 focused on jank concepts, evidence and system
boundaries.  View, RecyclerView and Compose implementation material moves to
the application-practice owners in chapter 22.  Unique source mechanisms are
rewritten into those owners; repeated tutorials are represented by an explicit
section-level route map instead of being concatenated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

VIEW_SOURCE = ROOT / "src/part2-performance/ch07-smoothness/03-view-layout-rendering-optimization.md"
COMPOSE_SOURCE = ROOT / "src/part2-performance/ch07-smoothness/04-compose-performance.md"
RV_SOURCE = ROOT / "src/part2-performance/ch07-smoothness/05-recyclerview-performance.md"

VIEW_TARGET = ROOT / "src/part5-app/ch22-rendering-practice/01-view-layout-custom-drawing.md"
RV_TARGET = ROOT / "src/part5-app/ch22-rendering-practice/02-recyclerview-compose-lazylist.md"
COMPOSE_TARGET = ROOT / "src/part5-app/ch22-rendering-practice/03-compose-compiler-modifier-diagnostics.md"

MAP_PATH = ROOT / "metadata/2026-08-24-editorial-fusion-v9-map.json"

REINDEX = [
    (
        ROOT / "src/part2-performance/ch07-smoothness/06-perceived-smoothness.md",
        ROOT / "src/part2-performance/ch07-smoothness/03-perceived-smoothness.md",
        "7.6",
        "7.3",
    ),
    (
        ROOT / "src/part2-performance/ch07-smoothness/07-systemui-performance.md",
        ROOT / "src/part2-performance/ch07-smoothness/04-systemui-performance.md",
        "7.7",
        "7.4",
    ),
    (
        ROOT / "src/part2-performance/ch07-smoothness/08-hwc-overlay-composition-downgrade.md",
        ROOT / "src/part2-performance/ch07-smoothness/05-hwc-overlay-composition-downgrade.md",
        "7.8",
        "7.5",
    ),
    (
        ROOT / "src/part2-performance/ch07-smoothness/09-accessibility-contentcapture-autofill.md",
        ROOT / "src/part2-performance/ch07-smoothness/06-accessibility-contentcapture-autofill.md",
        "7.9",
        "7.6",
    ),
]

MERGES = [
    (VIEW_SOURCE, VIEW_TARGET),
    (COMPOSE_SOURCE, COMPOSE_TARGET),
    (RV_SOURCE, RV_TARGET),
]

CHAPTER_REMAP = {
    "7.3": "22.1",
    "7.4": "22.3",
    "7.5": "22.2",
    "7.6": "7.3",
    "7.7": "7.4",
    "7.8": "7.5",
    "7.9": "7.6",
}


INFLATER_SECTION = r"""
### `LayoutInflater`：缓存构造器不等于消除创建成本

布局 XML 经 AAPT2 编译成 binary XML（编译后的二进制 XML），运行时仍要读取节点与属性、创建对象并组装 View 树。把整段工作都称为“XML 解析”会漏掉主题、资源和业务构造器的成本。一次 `inflate()` 可以按三段理解：

1. `Resources.getLayout()` 提供解析器，inflater 读取 `AttributeSet`，处理 `android:theme`、`<include>`、`<merge>`、`<tag>` 等特殊标签，并让父容器生成 `LayoutParams`；
2. `createViewFromTag()` 先经过 `Factory2 → Factory → private factory`。都未创建 View 时，才进入 `onCreateView()` 或按完整类名构造；AppCompat 的控件替换、Context 包装和 tint 也在这条 Factory 路径中；
3. `rInflateChildren()` 递归创建子节点、生成布局参数、加入父容器，并在子树完成后调用 `onFinishInflate()`。

`LayoutInflater` 的进程级构造器表可以省掉重复的类查找，却不会省掉 `Constructor.newInstance()`、View 构造函数、style、字体、Drawable 和自定义初始化。首次进入页面还可能包含类加载；因此冷启动与预热后的 trace 要分开比较，不能先假定反射就是主要耗时。

传入的 `root` 还决定 XML 根节点能否获得正确的父容器布局参数：

| 调用形态 | 返回值 | 已加入 `root` | 根节点 `LayoutParams` |
| --- | --- | ---: | --- |
| `inflate(res, root, true)` | `root` | 是 | 由 `root.generateLayoutParams()` 生成 |
| `inflate(res, root, false)` | XML 根 View | 否 | 仍由 `root.generateLayoutParams()` 生成 |
| `inflate(res, null, false)` | XML 根 View | 否 | 缺少父容器上下文，之后可能需要修正 |

所以“先传 `null`，稍后再 `addView()`”并不等价于传入真实 parent；而 `<merge>` 因为没有独立根节点，只能在已有 parent 且 `attachToRoot=true` 时展开。
""".strip()


VIEW_TREE_OBSERVER_SECTION = r"""
### `ViewTreeObserver`：布局回调不是显示完成信号

Android 17 的 `ViewRootImpl.performTraversals()` 会在本轮发生 layout，或全局属性需要重新计算时调用 `dispatchOnGlobalLayout()`。因此 `OnGlobalLayoutListener` 只说明 View 树的全局布局状态已经处理到这一点；它不能证明某个 `View.layout()` 刚执行完，更不能证明 buffer 已提交、被 SurfaceFlinger 选中并显示。

回调要按它实际观察的范围使用：

- 只关心一个 View 的位置或尺寸时，优先用 `View.OnLayoutChangeListener` 或 AndroidX `doOnLayout`；
- 一次性 global listener 在条件满足后立即移除，回调内避免 I/O、同步 Binder、整树扫描和无条件 `requestLayout()`；
- `OnPreDrawListener.onPreDraw()` 返回 `false` 会取消当前 draw 并重新调度，条件长期不满足会形成连续取消；
- 首帧显示应使用 FrameTimeline、`reportFullyDrawn()` 或与产品目标含义相符的信号，而不是 global layout 的结束时间。

`getViewTreeObserver()` 返回的对象也不是可跨整个 View 生命周期永久保存的句柄。未 attach 的 View 使用 floating observer；attach 时 listener 会合并到窗口 observer，旧对象随后失效。长期持有引用时要检查 `isAlive()`，移除 listener 时重新取得当前 observer 更稳妥。
""".strip()


RV_LAYOUT_SECTION = r"""
## RecyclerView 布局与缓存状态机

### `dispatchLayout()` 三步与 AutoMeasure

RecyclerView 1.4.0 的完整布局由三个内部步骤组织。它们是状态机中的方法，不是 Perfetto 保证出现的同名 slice：

| 内部步骤 | 主要职责 | Trace 解读 |
| --- | --- | --- |
| `dispatchLayoutStep1()` | 处理 Adapter 更新和动画标记，记录 pre-layout 信息；predictive animation 时还会执行预布局 | 位于外层更新或布局 slice 中，没有独立同名轨道 |
| `dispatchLayoutStep2()` | 消费更新，进入最终状态的 `LayoutManager.onLayoutChildren()`；非 `EXACT` 测量时可能执行多次 | 在 `RV OnLayout`、`RV FullInvalidate`、`RV PartialInvalidate` 的调用栈里找 layout、create、bind 和子 View measure |
| `dispatchLayoutStep3()` | 匹配 pre/post-layout 信息，启动 item animation，回收 scrap，恢复焦点并清理状态 | 仍属于外层布局 slice，不能用一条动画 slice 代替整个 step3 |

`RV FullInvalidate` 常覆盖首次布局、数据集整体失效或 add/remove/move 等结构更新；只有 `UPDATE` 的局部变化会先走 `RV PartialInvalidate`，可见 holder 受影响时才进入完整布局。这些名称描述外层入口，不等于 step1/2/3 的固定映射。

AutoMeasure 还会把成本移到 `onMeasure()`：宽高不都是 `EXACT` 时，测量阶段可以先执行 step1/step2，`onLayout()` 随后只补 step3，或因尺寸变化再次执行 step2；`shouldMeasureTwice()` 为真时还会多一轮。看到 `RV OnLayout` 很短，仍要检查同一帧 framework `measure` 和调用栈，不能据此断言列表布局很轻。
""".strip()


RV_CACHE_SECTION = r"""
#### 实际查找顺序不是固定“四级缓存”

`tryGetViewHolderForPositionByDeadline()` 的主要查找顺序还包括 changed scrap、hidden child 与 stable ID 二次查找：

| 来源 | 参与条件 | 取得后是否可能 bind |
| --- | --- | --- |
| changed scrap | pre-layout 按 position 或 stable ID 查找变化前 holder | 取决于 pre-layout 状态和标记 |
| attached scrap / hidden child / `mCachedViews` | 先按 position 查找，再校验 viewType 与 ID | 有效且未标记 update/invalid 时可直接复用；scrap 也可能重新 bind |
| stable ID 二次查找 | Adapter 开启 stable IDs 时，按 ID 与 viewType 再查 scrap/cache | 状态需要更新时仍会 bind |
| `ViewCacheExtension` | 应用显式提供扩展时 | 由返回 holder 的状态决定 |
| `RecycledViewPool` | 前面都没有兼容 holder | 重置内部状态后通常要 bind |
| 新建 holder | Pool 也未命中且 deadline 允许 | create 后继续 bind |

Attached scrap 只是布局期间暂时分离的 holder，并不保证“只复用、不 bind”。`mCachedViews` 的请求上限默认是 2，实际 `mViewCacheMax` 还会加上 LayoutManager 观察到的预取数量；Pool 则默认每个 `viewType` 保存 5 个。看到 bind 只能说明当前 holder 需要绑定，不能反推出它一定来自 Pool。
""".strip()


RV_EXTENSION_SECTION = r"""
### SnapHelper、LayoutManager 与 ItemDecoration 的热路径边界

扩展组件容易把线性列表的局部工作重新放大成整表工作：

- 自定义 `SnapHelper` 只检查可见或邻近候选项，几何计算要覆盖 `reverseLayout`、RTL、padding、ItemDecoration 和可变尺寸 item；不要在 fling 目标计算中遍历完整数据集或触发新布局。
- 自定义 `LayoutManager` 必须正确处理 Adapter 更新、pre-layout、焦点、无障碍、滚动边界和回收规则。`onLayoutChildren()` 与 fill 路径不应从头扫描全部数据，prefetch position 和 distance 要从布局几何推导。
- `ItemDecoration.getItemOffsets()` 位于布局计算，`onDraw()` / `onDrawOver()` 位于绘制阶段。这里应避免对象分配、复杂 Path 和整表扫描；缓存要使用稳定输入作为 key，防止 position 移动后复用旧结果。

这些规则与 ItemAnimator 要一起验收：局部 payload 降低 bind 范围后，change animation 仍可能同时保留新旧 holder。只有 A/B trace 证明关闭 `supportsChangeAnimations` 能减少 `RV OnLayout`、bind 或慢帧，且视觉不受损时，才在对应页面缩小关闭范围。
""".strip()


COMPOSE_SLOT_PARAGRAPH = (
    "这条窗口链路与 Compose Runtime 的内部结构是两层概念。`SlotTable` 保存 composition 的 group、key、`remember` 值和调用结构，它不是 UI 节点树；`LayoutNode` 才承载 Compose 的测量、摆放与绘制节点。recomposition 只重新执行失效的 restart scope，不等于重建整个页面；大多数普通 `LayoutNode` 也不会各自创建一个 Android `RenderNode`，绘制通常记录到最近的图层边界。"
)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one marker, found {count}")
    return text.replace(old, new, 1)


def build_view(text: str) -> str:
    text = replace_once(
        text,
        "applicable_versions: Android 10 (API 29) - Android 17 (API 37)",
        "applicable_versions: Android 5.0 (API 21) - Android 17 (API 37)",
        "View applicable versions",
    )
    text = replace_once(
        text,
        "last_verified_against: AOSP android-17.0.0_r1 ViewRootImpl/ViewGroup/LayoutInflater/ViewStub/FrameMetrics; current Android Developers layout guidance; AndroidX AsyncLayoutInflater 1.1.0 API and release notes; AIW 7.10/22.3",
        "last_verified_against: AOSP android-17.0.0_r1 ViewRootImpl/ViewGroup/LayoutInflater/ViewStub/ViewTreeObserver/FrameMetrics; current Android Developers layout guidance; AndroidX AsyncLayoutInflater 1.1.0 API and release notes",
        "View verification provenance",
    )
    for block in (
        "- type: aiw\n  path: src/part2-performance/ch07-smoothness/10-view-layout-performance.md\n",
        "- type: aiw\n  path: src/part1-fundamentals/ch02-rendering/05-main-render-thread.md\n",
        "- type: aiw\n  path: src/part5-app/ch22-rendering-practice/03-compose-performance.md\n",
    ):
        text = replace_once(text, block, "", "View stale AIW source")
    source_marker = (
        "- type: aosp\n"
        "  path: frameworks/base/graphics/java/android/graphics/RenderNode.java\n"
    )
    extra_sources = (
        "- type: aosp\n"
        "  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/LayoutInflater.java\n"
        "- type: aosp\n"
        "  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewTreeObserver.java\n"
        "- type: aosp\n"
        "  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java\n"
    )
    text = replace_once(text, source_marker, source_marker + extra_sources, "View source evidence")
    text = replace_once(text, "- '7.3'\n", "", "View obsolete self relation")
    provenance = "- src/part5-app/ch22-rendering-practice/04-custom-view-optimization.md\n"
    text = replace_once(
        text,
        provenance,
        provenance + "- src/part2-performance/ch07-smoothness/03-view-layout-rendering-optimization.md\n",
        "View provenance",
    )
    old_opening = (
        "应用侧布局优化要把 View 体系的递归测量、`LayoutInflater` 流程和 `requestLayout()` 触发路径转成页面改造、代码选型和 trace 验收方法；相关机制见 [7.3 View 布局与通用渲染优化](../../part2-performance/ch07-smoothness/03-view-layout-rendering-optimization.md)。这里的 trace 指 Perfetto 等工具记录的线程与渲染时间线，deadline 是一帧按时完成的截止时间。目标很具体：减少首帧和页面切换里的主线程 Measure / Layout 时间，为同一帧的其他工作留出预算。"
    )
    new_opening = (
        "应用侧布局优化要把 View 体系的递归测量、`LayoutInflater` 对象创建、`requestLayout()` 传播与绘制失效放进同一帧时间线。本文统一维护这些机制、页面改造、代码选型和 trace 验收方法；这里的 trace 指 Perfetto 等工具记录的线程与渲染时间线，deadline 是一帧按时完成提交的截止点。目标很具体：减少首帧、页面切换和高频更新里的主线程 Measure / Layout / Draw 工作，为同一帧的输入、业务逻辑和渲染提交留出预算。"
    )
    text = replace_once(text, old_opening, new_opening, "View opening")
    text = replace_once(
        text,
        "节点越多、嵌套越深、父容器规则越复杂，主线程执行的代码通常越多；多轮测量会进一步放大这部分成本。详见前述 7.3 节。",
        "节点越多、嵌套越深、父容器规则越复杂，主线程执行的代码通常越多；多轮测量会进一步放大这部分成本。结论仍要回到当前页面的调用次数、单节点工作量和 FrameTimeline deadline。",
        "View stale prose reference",
    )
    marker = "### 布局预加载与异步 Inflate"
    text = replace_once(text, marker, INFLATER_SECTION + "\n\n" + marker, "View inflater insertion")
    marker = "### Compose 与 View 混合布局的性能陷阱"
    text = replace_once(
        text,
        marker,
        VIEW_TREE_OBSERVER_SECTION + "\n\n" + marker,
        "View observer insertion",
    )
    return text


def build_recycler(text: str) -> str:
    text = replace_once(
        text,
        "last_verified_against: AndroidX current-version table (updated 2026-08-12); RecyclerView 1.4.0 sources.jar and API docs; Android 17 MessageQueue guidance (updated 2026-08-13); AIW 7.8/22.1/2.4",
        "last_verified_against: AndroidX current-version table (updated 2026-08-12); RecyclerView 1.4.0 sources.jar and API docs; Android 17 MessageQueue guidance (updated 2026-08-13)",
        "Recycler verification provenance",
    )
    for block in (
        "- type: aiw\n  path: src/part2-performance/ch07-smoothness/08-recyclerview-performance.md\n",
        "- type: aiw\n  path: src/part5-app/ch22-rendering-practice/01-layout-optimization.md\n",
        "- type: aiw\n  path: src/part1-fundamentals/ch02-rendering/04-choreographer.md\n",
    ):
        text = replace_once(text, block, "", "Recycler stale AIW source")
    text = replace_once(text, "- '7.5'\n", "", "Recycler obsolete self relation")
    provenance = "- src/part5-app/ch22-rendering-practice/16-compose-lazylist-performance.md\n"
    text = replace_once(
        text,
        provenance,
        provenance + "- src/part2-performance/ch07-smoothness/05-recyclerview-performance.md\n",
        "Recycler provenance",
    )
    old_opening = (
        "RecyclerView 优化不应从“调几个参数”开始，而要先定位滑动路径里的成本：创建 `ViewHolder`、绑定数据、计算列表差异、预取下一屏，以及处理嵌套滑动。`ViewHolder` 是持有一条 item 的根 View 和子 View 引用的复用单元；GapWorker 则是 RecyclerView 在主线程执行的预取任务。缓存查找顺序和 GapWorker 源码见 [7.5 RecyclerView 列表滑动性能深度优化](../../part2-performance/ch07-smoothness/05-recyclerview-performance.md)，本节侧重应用写法、验收方法和取舍边界。"
    )
    new_opening = (
        "RecyclerView 优化不应从“调几个参数”开始，而要先定位滑动路径里的成本：布局状态机、`ViewHolder` 获取与绑定、列表差异、预取下一屏，以及嵌套滑动。本文统一维护 RecyclerView 1.4.0 的布局、缓存、GapWorker 源码边界与应用写法，再与 Compose LazyList 的组合和预取模型对照；机制结论和改动收益都要回到同一条慢帧证据。"
    )
    text = replace_once(text, old_opening, new_opening, "Recycler opening")
    marker = "## ViewHolder 复用、绑定与 GapWorker 预取"
    text = replace_once(text, marker, RV_LAYOUT_SECTION + "\n\n" + marker, "Recycler layout insertion")
    cache_marker = (
        "ViewHolder 设计的目标是让滑动过程尽量命中缓存，减少反复 `inflate`（解析 XML 并创建 View 树）和完整绑定。`RecycledViewPool` 可以在多个 RecyclerView 之间共享 ViewHolder，并按 `viewType`（可复用的视图类型）分桶；1.4.0 中每种类型默认最多保留 5 个，应用可用 `setMaxRecycledViews()` 调整。RecyclerView 自身的 `mCachedViews` 会保留仍带绑定状态的 holder：请求大小默认是 2；启用 item prefetch（条目预取）时，实际最大值 `mViewCacheMax` 还会加上 LayoutManager 观察到的预取数量，因此不能把“2”理解为始终固定的总数。"
    )
    text = replace_once(
        text,
        cache_marker,
        cache_marker + "\n\n" + RV_CACHE_SECTION,
        "Recycler cache insertion",
    )
    marker = "### Android 17 DeliQueue：只改变消息入队，不替代列表优化"
    text = replace_once(
        text,
        marker,
        RV_EXTENSION_SECTION + "\n\n" + marker,
        "Recycler extension insertion",
    )
    return text


def build_compose(text: str) -> str:
    text = replace_once(text, "- '7.4'\n", "", "Compose obsolete self relation")
    provenance = "- src/part5-app/ch22-rendering-practice/25-compose-modifier-node.md\n"
    text = replace_once(
        text,
        provenance,
        provenance + "- src/part2-performance/ch07-smoothness/04-compose-performance.md\n",
        "Compose provenance",
    )
    window_marker = (
        "普通 `ComposeView` 不会单独创建 Surface。内容仍由当前应用窗口的 HWUI（Android 硬件加速 UI 渲染器）路径输出：UI 线程完成 Composition（根据状态生成或更新 UI 树）、Layout（测量与摆放）和 Drawing（记录绘制命令），经 `HardwareRenderer.syncAndDrawFrame()` 交给 RenderThread（执行渲染命令的专用线程），再通过 BLAST BufferQueue 提交图形缓冲区，由 SurfaceFlinger 合成，并交给 HWC（Hardware Composer，硬件合成器），最终显示到屏幕。页面嵌入 `SurfaceView`、`TextureView`、WebView 或视频组件后，还要跟踪这些组件自己的图像生产者（producer）和 Surface layer（合成图层）。完整管线可结合 [Compose 渲染管线架构](../../part2-performance/ch18-rendering-pipelines/09-compose-rendering-pipeline.md) 阅读。"
    )
    text = replace_once(
        text,
        window_marker,
        window_marker + "\n\n" + COMPOSE_SLOT_PARAGRAPH,
        "Compose SlotTable insertion",
    )
    return text


def relpath(target: Path, source_file: Path) -> str:
    return Path(os.path.relpath(target, source_file.parent)).as_posix()


def protect_consolidated_paths(text: str, paths: list[str]) -> tuple[str, dict[str, str]]:
    """Protect historical provenance while rewriting live links and sources."""

    restored: dict[str, str] = {}
    match = re.search(r"(?m)^consolidated_from:\n(?:- .*\n)+", text)
    if not match:
        return text, restored
    block = match.group(0)
    protected = block
    for index, value in enumerate(paths):
        if value not in protected:
            continue
        placeholder = f"__AIW_HISTORICAL_PATH_{index}__"
        protected = protected.replace(value, placeholder)
        restored[placeholder] = value
    return text[: match.start()] + protected + text[match.end() :], restored


def remap_related_chapters(text: str) -> str:
    pattern = re.compile(r"(?m)^(\s*-\s*['\"])(7\.[3-9])(['\"]\s*)$")
    text = pattern.sub(lambda m: f"{m.group(1)}{CHAPTER_REMAP[m.group(2)]}{m.group(3)}", text)

    # Deduplicate only the YAML related_chapters block.  Several predecessor
    # references can legitimately converge on one new owner.
    match = re.search(r"(?m)^related_chapters:\n((?:- .*\n)+)", text)
    if not match:
        return text
    seen: set[str] = set()
    kept: list[str] = []
    for line in match.group(1).splitlines(keepends=True):
        key = line.strip()
        if key in seen:
            continue
        seen.add(key)
        kept.append(line)
    return text[: match.start(1)] + "".join(kept) + text[match.end(1) :]


def update_references(path: Path, text: str) -> str:
    navigation_files = {
        ROOT / "src/SUMMARY.md",
        ROOT / "src/part2-performance/ch07-smoothness/README.md",
    }
    retired_names = {source.name for source, _ in MERGES}
    if path in navigation_files:
        old_lines = text.splitlines()
        new_lines = [line for line in old_lines if not any(name in line for name in retired_names)]
        if new_lines != old_lines:
            text = "\n".join(new_lines) + ("\n" if text.endswith("\n") else "")

    historical_paths = [str(old.relative_to(ROOT)) for old, _ in MERGES]
    historical_paths += [str(old.relative_to(ROOT)) for old, _, _, _ in REINDEX]
    text, placeholders = protect_consolidated_paths(text, historical_paths)

    for old, new in MERGES:
        text = text.replace(relpath(old, path), relpath(new, path))
        text = text.replace(str(old.relative_to(ROOT)), str(new.relative_to(ROOT)))
    for old, new, _, _ in REINDEX:
        text = text.replace(relpath(old, path), relpath(new, path))
        text = text.replace(str(old.relative_to(ROOT)), str(new.relative_to(ROOT)))

    for placeholder, value in placeholders.items():
        text = text.replace(placeholder, value)

    text = remap_related_chapters(text)

    prose_replacements = {
        "7.1-7.7（流畅性）": "7.1-7.6（流畅性）",
        "7.1 → 7.2 → 7.5": "7.1 → 7.2 → 22.2",
        "§7.3（View 体系性能优化）": "§22.1（View 布局与自定义绘制优化）",
        "7.9 Accessibility、ContentCapture 与 Autofill": "7.6 Accessibility、ContentCapture 与 Autofill",
        "**§7.5 RecyclerView**": "**§22.2 RecyclerView**",
        "**§7.3 View 体系**": "**§22.1 View 体系**",
        "**§7.3 优化策略**": "**§7.2 卡顿分析方法**",
        "`7.8`": "`7.5`",
        "`7.9`": "`7.6`",
    }
    for old, new in prose_replacements.items():
        text = text.replace(old, new)

    if path == ROOT / "src/part2-performance/ch07-smoothness/README.md":
        guidance = (
            "- 排查线上卡顿时，从 `7.2`、`7.3` 和 `7.6` 选择与现场最接近的入口。",
            "- 排查线上卡顿时，从 `7.2` 的证据流程与 `7.3` 的感知节奏选择入口；若已定位到具体 UI 组件，再进入 22.1～22.3。",
            "chapter 7 investigation guidance",
        )
        if guidance[0] in text:
            text = replace_once(text, *guidance)
        ui_ownership = (
            "- 分析具体 UI 技术体系时，进入 `7.3`～`7.7`，分别检查 View、Compose、RecyclerView、感知节奏和 SystemUI。",
            "- 分析具体 UI 技术体系时，View、Compose 与 RecyclerView 分别进入 22.1、22.3、22.2；第 7 章保留 `7.3` 的感知节奏和 `7.4` 的 SystemUI 系统链路。",
            "chapter 7 UI ownership guidance",
        )
        if ui_ownership[0] in text:
            text = replace_once(text, *ui_ownership)
    if path == ROOT / "src/part1-fundamentals/ch05-cpu-power/04-adpf.md":
        # The retired 7.3 mixed View implementation with general optimization
        # strategy.  ADPF's dynamic quality policy belongs to the jank method,
        # not to the View-specific 22.1 owner.
        text = text.replace("- '22.1'", "- '7.2'")
        text = remap_related_chapters(text)
    return text


def headings(text: str, level: int = 2) -> list[str]:
    prefix = "#" * level + " "
    return [line[len(prefix) :].strip() for line in text.splitlines() if line.startswith(prefix)]


def validate_built(changed: dict[Path, str]) -> None:
    assertions = {
        VIEW_TARGET: ["Factory2 → Factory → private factory", "ViewTreeObserver", "isAlive()", "attachToRoot=true"],
        RV_TARGET: ["dispatchLayoutStep1()", "AutoMeasure", "ViewCacheExtension", "SnapHelper", "ItemDecoration"],
        COMPOSE_TARGET: ["`SlotTable` 保存 composition", "它不是 UI 节点树", "大多数普通 `LayoutNode`"],
    }
    for path, needles in assertions.items():
        missing = [needle for needle in needles if needle not in changed[path]]
        if missing:
            raise RuntimeError(f"{path.name}: missing routed concepts: {missing}")

    for path in (VIEW_TARGET, RV_TARGET, COMPOSE_TARGET):
        h2 = headings(changed[path])
        if len(h2) != len(set(h2)):
            raise RuntimeError(f"{path.name}: duplicate H2 headings after fusion")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    required = [source for source, _ in MERGES]
    required += [target for _, target in MERGES]
    required += [old for old, _, _, _ in REINDEX]
    if not all(path.exists() for path in required):
        missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
        raise SystemExit(f"Expected predecessor files are missing: {missing}")
    collisions = [new for _, new, _, _ in REINDEX if new.exists()]
    if collisions:
        raise SystemExit(f"Reindex destinations already exist: {collisions}")

    originals = {path: path.read_text(encoding="utf-8") for path in required}
    changed: dict[Path, str] = {
        VIEW_TARGET: build_view(originals[VIEW_TARGET]),
        RV_TARGET: build_recycler(originals[RV_TARGET]),
        COMPOSE_TARGET: build_compose(originals[COMPOSE_TARGET]),
    }

    for old, new, old_number, new_number in REINDEX:
        body = originals[old]
        body = replace_once(body, f"chapter: '{old_number}'", f"chapter: '{new_number}'", f"{old.name} chapter")
        body = replace_once(body, f"section: '{old_number}'", f"section: '{new_number}'", f"{old.name} section")
        changed[new] = body

    skip = {source for source, _ in MERGES}
    skip.update(target for _, target in MERGES)
    skip.update(old for old, _, _, _ in REINDEX)
    for path in sorted((ROOT / "src").rglob("*.md")):
        if path in skip:
            continue
        original = path.read_text(encoding="utf-8")
        updated = update_references(path, original)
        if updated != original:
            changed[path] = updated

    for path in list(changed):
        changed[path] = update_references(path, changed[path])

    for relative in (
        "metadata/queue.json",
        "metadata/queue_backup.json",
        "metadata/queue.backup.2026-07-08T10-53-47.json",
    ):
        path = ROOT / relative
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8")
        updated = original
        for old, new in MERGES:
            updated = updated.replace(str(old.relative_to(ROOT)), str(new.relative_to(ROOT)))
        for old, new, _, _ in REINDEX:
            updated = updated.replace(str(old.relative_to(ROOT)), str(new.relative_to(ROOT)))
        if updated != original:
            changed[path] = updated

    validate_built(changed)

    section_routes = [
        {
            "source": "7.3 减少工作量、缩短关键路径与控制频率",
            "destination": "22.1 layout/draw; 22.2 RecyclerView; 22.3 Compose; 22.4/22.8 effects; 7.2/15.1 methodology",
            "treatment": "distributed_to_existing_deeper_owners",
        },
        {
            "source": "7.3 View 创建、测量、布局与绘制 / LayoutInflater",
            "destination": "22.1 LayoutInflater：缓存构造器不等于消除创建成本",
            "treatment": "unique_mechanism_rewritten_and_embedded",
        },
        {
            "source": "7.3 View 创建、测量、布局与绘制 / ViewTreeObserver",
            "destination": "22.1 ViewTreeObserver：布局回调不是显示完成信号",
            "treatment": "unique_mechanism_rewritten_and_embedded",
        },
        {
            "source": "7.4 帧模型、Recomposition、Stability、状态与计算",
            "destination": "22.3 状态、重组、布局与绘制基线 + Compiler 诊断",
            "treatment": "deduplicated_into_deeper_owner",
        },
        {
            "source": "7.4 SlotTable 不是 UI 树",
            "destination": "22.3 opening pipeline boundary",
            "treatment": "unique_boundary_rewritten_and_embedded",
        },
        {
            "source": "7.4 Lazy 列表性能",
            "destination": "22.2 LazyList 组合、测量与预取 + 22.3 Lazy 列表基线",
            "treatment": "deduplicated_into_deeper_owners",
        },
        {
            "source": "7.4 绘制、图层、互操作、工具、Baseline Profile、排查清单",
            "destination": "22.3 drawing/interop/diagnostics; 22.4 effects; 21.4 Baseline Profile",
            "treatment": "distributed_to_existing_deeper_owners",
        },
        {
            "source": "7.5 RecyclerView 布局流程与 AutoMeasure",
            "destination": "22.2 RecyclerView 布局与缓存状态机",
            "treatment": "unique_mechanism_rewritten_and_embedded",
        },
        {
            "source": "7.5 ViewHolder 缓存真实查找顺序",
            "destination": "22.2 实际查找顺序不是固定四级缓存",
            "treatment": "unique_mechanism_rewritten_and_embedded",
        },
        {
            "source": "7.5 GapWorker、DiffUtil、嵌套滑动、ARR 与 Perfetto",
            "destination": "22.2 existing ViewHolder/GapWorker/DiffUtil/nested/ARR/measurement sections",
            "treatment": "deduplicated_into_deeper_owner",
        },
        {
            "source": "7.3 SnapHelper + 7.5 custom LayoutManager/ItemDecoration/ItemAnimator",
            "destination": "22.2 extension hot-path boundary",
            "treatment": "unique_boundaries_rewritten_and_embedded",
        },
        {
            "source": "three predecessor reference sections",
            "destination": "22.1/22.2/22.3 source metadata and source indexes",
            "treatment": "evidence_reconciled; stale_internal_sources_removed",
        },
    ]

    result = {
        "version": 9,
        "operation": "framework_owner_editorial_fusion",
        "count_change": {"before": 283, "after": 280},
        "merged_paths": [
            {
                "source": str(VIEW_SOURCE.relative_to(ROOT)),
                "target": str(VIEW_TARGET.relative_to(ROOT)),
                "role": "view_layout_drawing_owner",
            },
            {
                "source": str(COMPOSE_SOURCE.relative_to(ROOT)),
                "target": str(COMPOSE_TARGET.relative_to(ROOT)),
                "role": "compose_runtime_compiler_owner",
            },
            {
                "source": str(RV_SOURCE.relative_to(ROOT)),
                "target": str(RV_TARGET.relative_to(ROOT)),
                "role": "recyclerview_lazylist_owner",
            },
        ],
        "rewritten_paths": [
            str(VIEW_TARGET.relative_to(ROOT)),
            str(RV_TARGET.relative_to(ROOT)),
            str(COMPOSE_TARGET.relative_to(ROOT)),
        ],
        "reindexed_paths": [
            {"from": str(old.relative_to(ROOT)), "to": str(new.relative_to(ROOT))}
            for old, new, _, _ in REINDEX
        ],
        "source_bytes": {
            str(path.relative_to(ROOT)): len(body.encode("utf-8"))
            for path, body in originals.items()
        },
        "result_bytes": {
            str(path.relative_to(ROOT)): len(changed[path].encode("utf-8"))
            for path in (VIEW_TARGET, RV_TARGET, COMPOSE_TARGET)
        },
        "source_sha256": {
            str(path.relative_to(ROOT)): digest(body) for path, body in originals.items()
        },
        "result_sha256": {
            str(path.relative_to(ROOT)): digest(changed[path])
            for path in (VIEW_TARGET, RV_TARGET, COMPOSE_TARGET)
        },
        "source_h2_inventory": {
            str(source.relative_to(ROOT)): headings(originals[source]) for source, _ in MERGES
        },
        "content_routes": section_routes,
        "updated_reference_files": [
            str(path.relative_to(ROOT))
            for path in sorted(changed)
            if path not in {VIEW_TARGET, RV_TARGET, COMPOSE_TARGET, *[row[1] for row in REINDEX]}
        ],
        "applied": args.apply,
    }

    if args.apply:
        for path, body in changed.items():
            path.write_text(body, encoding="utf-8")
        for source, _ in MERGES:
            source.unlink()
        for old, _, _, _ in REINDEX:
            old.unlink()
        MAP_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
