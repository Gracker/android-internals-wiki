---
title: 13.10 P e r f etto S Q L 性能分析实战手册
chapter: '13.10'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
tags:
- tools
- perfetto
- sql
- cookbook
task6_state: reviewed
task6_result: pass-light-edit
pipeline_stage: ready-to-publish
reviewed_by: openclaw-task6
---

# 13.10 P e r f etto S Q L 性能分析实战手册

在前面的章节中，我们分别介绍了 P e r f etto 的 U I 可视化（§13.3）、专题解读（§13.5）和命令行工具（§13.4）。但在实际工作中，很多性能问题无法单靠肉眼在 U I 中定位——我们需要精确的数字：第 47 帧耗时多少毫秒？主线程有多少时间花在等锁上？B ind e r 调用中排队占了多少时间？这类定量分析，离不开 S Q L。

P e r f etto T r a c e P roc e ssor 内置了一个完整的 S Q L 引擎（基于 S Q Lit e），我们可以用它对 T r a c e 数据做任意维度的查询和聚合。本节不会逐个罗列 S Q L 语法，而是围绕性能分析中最常见的几类问题——帧时间与卡顿、线程调度、B ind e r 事务、内存与 G C、启动时间、A N R、锁竞争——逐个给出**从问题到 S Q L 到结论**的完整分析路径。每条 S Q L 都可以直接在 P e r f etto U I 的 Q u ery 标签页或 `tr a c e_proc e ssor_sh e ll` 中运行。

<!-- o u tlin e-st a rt -->
## 本节导读
- 🔹 T r a c e P roc e ssor S Q L 基础：建立 P e r f etto S Q L、标准库模块、核心表、时间单位和大 T r a c e 查询约束。
- 🔹 帧时间与卡顿分析：用 `C hor e ogr a ph e r#do F r a m e`、F r a m e T im e lin e 和分桶统计定位慢帧。
- 🔹 线程调度与 C P U 使用：通过 `sch e d`、`thr e ad_st a t e` 和调度延迟判断 C P U bo u nd、R u nn a bl e 排队与阻塞。
- 🔹 B ind e r、G C、启动与 A N R：把常见性能场景拆成可复查的 S Q L 查询路径。
- 🔹 锁竞争与 S P A N_J O I N：用 stdlib 视图、时间窗口和 `S P A N_J O I N` 做跨维度关联分析。
- 🔹 交叉引用与分析路径：把单条 S Q L 模板组合成卡顿、A N R 和启动分析流程。
<!-- o u tlin e-e nd -->

## T r a c e P roc e ssor S Q L 基础

在写具体查询之前，我们需要了解几个基础概念，后面所有 S Q L 都建立在这些概念之上。

### S Q L 引擎与模块加载

T r a c e P roc e ssor 的 S Q L 方言叫 P e r f etto S Q L，基于 S Q Lit e 但做了扩展。最大的扩展是 `I N C L U D E P E R F E T T O M O D U L E` 语句：P e r f etto 官方维护了一套标准库模块（st a nd a rd libr a ry mod u l e s），每个模块提供预定义的表、视图和函数，把底层的 r a w 表封装成更易用的高级抽象。

```sql
-- 加载帧分析标准模块
I N C L U D E P E R F E T T O M O D U L E a ndroid.f r a m e s.tim e lin e;

-- 加载输入延迟分析模块
I N C L U D E P E R F E T T O M O D U L E a ndroid.inp u t ;

-- 加载锁竞争分析模块
I N C L U D E P E R F E T T O M O D U L E a ndroid.monitor_cont e ntion ;
```

使用标准库模块有两个好处：第一，模块内部已经处理好了复杂的 J O I N 逻辑，我们不用手动拼接底层表；第二，模块会随 P e r f etto 版本更新而改进，保持查询的兼容性。在实际分析中，优先使用标准库模块而不是直接查底层表。`a ndroid.f r a m e s.tim e lin e`、`a ndroid.inp u t`、`a ndroid.monitor_cont e ntion` 都属于这一层。

[已验证: P e r f etto stdlib docs, p e r f etto.d e v/docs/a n a lysis/stdlib-docs]

### 核心表结构

P e r f etto 有几十张底层表，但性能分析中最常用的只有五张：

**slic e** 表是性能分析的核心。它记录了所有"有时间跨度的事件"——从 C hor e ogr a ph e r#do F r a m e 到 B ind e r 事务，从 G C 暂停到锁竞争，都以 slic e 的形式存储。每条 slic e 有 `ts`（开始时间，纳秒）、`d u r`（持续时间，纳秒）、`n a m e`（事件名）、`tr a ck_id`（所在的 tr a ck）。通过 `tr a ck_id` 关联到 `thr e ad_tr a ck`，再关联到 `thr e ad` 和 `proc e ss`，就能知道这个事件发生在哪个线程、哪个进程。

**sch e d** 表记录内核的线程调度切片——哪个线程在什么时候跑在哪个 C P U 上，跑了多久，以及这次 C P U slic e 结束时线程处于什么内核状态（`e nd_st a t e`）。`e nd_st a t e` 只描述“离开 C P U 的那一刻”，不能把它当成线程整段时间里的当前状态；如果要统计 R u nning / R / S / D 等状态分布，应该查 `thr e ad_st a t e` 表。

**co u nt e r** 表存储随时间变化的数值，比如 C P U 频率、内存使用量、J a v a H e ap 大小。co u nt e r 的数据点是离散的（每次值变化记录一次），做分析时通常需要和时间窗口 J O I N。

**thr e ad_tr a ck / proc e ss_tr a ck** 表是 slic e 和线程/进程之间的桥梁。`thr e ad_tr a ck` 中的每条记录对应一个线程的 tr a ck，包含 `u tid`（唯一线程 I D），可以 J O I N 到 `thr e ad` 表获取线程名和所属进程。

这些表之间的 J O I N 关系可以简化为：

```t e xt
slic e → thr e ad_tr a ck (vi a tr a ck_id) → thr e ad (vi a u tid) → proc e ss (vi a u pid)
sch e d → thr e ad (vi a u tid) → proc e ss (vi a u pid)
co u nt e r → co u nt e r_tr a ck (vi a tr a ck_id)
```

[已验证: P e r f etto 文档, p e r f etto.d e v/docs/a n a lysis/sql-t a bl e s]

### 目标进程、主线程与大 T r a c e 查询约束

后面的模板都按目标进程收窄。主线程不要只用 `thr e ad.n a m e = 'm a in'` 判断；真实 tr a c e 中，主线程名可能显示为包名、进程名，或者被系统截断。更稳的写法是在目标进程内使用 `thr e ad.is_m a in_thr e ad = 1`，旧 tr a c e 再用 `thr e ad.tid = proc e ss.pid` 兜底。

```sql
-- 目标进程与主线程 C T E。把 com.e x a mpl e.a pp 替换为目标进程名
W I T H t a rg e t_proc e ss A S (
  S E L E C T u pid, pid, n a m e
  F R O M proc e ss
  W H E R E n a m e = 'com.e x a mpl e.a pp'
),
m a in_thr e ad A S (
  S E L E C T
    thr e ad.u tid,
    thr e ad.tid,
    C O A L E S C E(thr e ad.n a m e, t a rg e t_proc e ss.n a m e) A S thr e ad_n a m e,
    t a rg e t_proc e ss.u pid,
    t a rg e t_proc e ss.n a m e A S proc e ss_n a m e
  F R O M thr e ad
  J O I N t a rg e t_proc e ss U S I N G (u pid)
  W H E R E thr e ad.is_m a in_thr e ad = 1
     O R thr e ad.tid = t a rg e t_proc e ss.pid
)
S E L E C T * F R O M m a in_thr e ad ;
```

> 如果当前 T r a c e P roc e ssor 版本没有 `thr e ad.is_m a in_thr e ad` 字段，就保留 `thr e ad.tid = proc e ss.pid` 作为主线程兜底，并在 P e r f etto U I 中确认该线程是否承载 `C hor e ogr a ph e r#do F r a m e`、`bind A pplic a tion` 等主线程 slic e。

大 T r a c e 上的查询要先裁剪再关联。不要让全量 `thr e ad_st a t e` 与全量 `slic e` 做非等值 J O I N；先把目标进程、目标时间窗和中间结果固化，再用 `S P A N_J O I N`、`int e rv a ls.int e rs e ct` / `int e rv a ls.ov e rl a p` 标准库宏，或普通重叠区间条件处理。

```sql
-- 大 T r a c e 查询前先固化目标窗口内的主线程状态
C R E A T E P E R F E T T O T A B L E t a rg e t_m a in_st a t e s A S
W I T H t a rg e t_proc e ss A S (
  S E L E C T u pid, pid, n a m e
  F R O M proc e ss
  W H E R E n a m e = 'com.e x a mpl e.a pp'
),
m a in_thr e ad A S (
  S E L E C T thr e ad.u tid
  F R O M thr e ad
  J O I N t a rg e t_proc e ss U S I N G (u pid)
  W H E R E thr e ad.is_m a in_thr e ad = 1
     O R thr e ad.tid = t a rg e t_proc e ss.pid
),
window A S (
  S E L E C T tr a c e_st a rt() + 0 A S st a rt_ts, tr a c e_st a rt() + 5000000000 A S e nd_ts
)
S E L E C T
  thr e ad_st a t e.id,
  thr e ad_st a t e.u tid,
  thr e ad_st a t e.st a t e,
  M A X(thr e ad_st a t e.ts, window.st a rt_ts) A S ts,
  M I N(thr e ad_st a t e.ts + thr e ad_st a t e.d u r, window.e nd_ts)
    - M A X(thr e ad_st a t e.ts, window.st a rt_ts) A S d u r
F R O M thr e ad_st a t e
J O I N m a in_thr e ad U S I N G (u tid)
C R O S S J O I N window
W H E R E thr e ad_st a t e.ts < window.e nd_ts
  A N D thr e ad_st a t e.ts + thr e ad_st a t e.d u r > window.st a rt_ts ;
```

`C R E A T E P E R F E T T O T A B L E` 会把过滤后的结果物化，后续查询可以复用这张小表，减少窗口函数和区间 J O I N 的重复扫描成本。

[已验证: P e r f etto S Q L t a bl e s / stdlib docs, p e r f etto.d e v/docs/a n a lysis/sql-t a bl e s]

### 时间单位与常用函数

P e r f etto 中所有时间戳和持续时间都用**纳秒（ns）**。这个单位精度够高，但人类不太直觉，分析时通常需要换算：

- 纳秒 → 毫秒：除以 `1 e 6`（或 `1000000.0`）
- 纳秒 → 秒：除以 `1 e 9`
- 16.67 ms 的帧预算（60 fps）= `16670000` ns
- 8.33 ms 的帧预算（120 fps）= `8330000` ns

`tr a c e_st a rt()` 函数返回 T r a c e 开始的时间戳，用 `ts - tr a c e_st a rt()` 可以把绝对时间转换为相对时间（从 T r a c e 开始过了多少纳秒），这在做时间分段分析时很有用。

`E X T R A C T_A R G(a rg_s e t_id, 'k e y')` 函数可以从 slic e 的附加参数中提取值。很多 P e r f etto slic e 携带额外的键值对信息，比如 C hor e ogr a ph e r 的 do F r a m e slic e 会带上 `f r a m e_n u mb e r` 参数，可以用 `E X T R A C T_A R G(slic e.a rg_s e t_id, 'f r a m e_n u mb e r')` 提取出来。

## 帧时间与卡顿分析

帧时间是衡量流畅性最直观的指标。我们可以用 S Q L 精确统计帧时间分布、定位掉帧和大帧，甚至分析帧节奏的规律性。

### 基本帧时间查询

最直接的方式是查询 `C hor e ogr a ph e r#do F r a m e` slic e 的持续时间，这代表主线程处理一帧的总耗时（包括 I np u t、A nim a tion、T r a v e rs a l 三个阶段）。A ndroid 10/11 的 tr a c e s e ction 通常是精确名称；A ndroid 12 起 A O S P 会在名称后追加 vsync id，例如 `C hor e ogr a ph e r#do F r a m e 12345`。本节的 S Q L 用 `G L O B 'C hor e ogr a ph e r#do F r a m e*'` 覆盖这两类 tr a c e。

```sql
-- 查询所有 do F r a m e 的帧时间
S E L E C T
  C A S T((ts - tr a c e_st a rt()) / 1 e 6 A S I N T E G E R) A S tim e_ms,
  C A S T(d u r / 1 e 6 A S F L O A T) A S f r a m e_ms,
  n a m e
F R O M slic e
W H E R E n a m e G L O B 'C hor e ogr a ph e r#do F r a m e*'
O R D E R B Y ts ;
```

这个查询的结果中，`f r a m e_ms` 就是每一帧的耗时。在 60 fps 设备上，超过 16.67 ms 的帧就是掉帧；在 120 fps 设备上，超过 8.33 ms 的帧就是掉帧。

但 `do F r a m e` 的 `d u r` 只包含主线程的工作时间。一帧从 V S ync 到上屏的完整时间还包括 R e nd e r T hr e ad 的渲染时间和 S u r f ac e Fling e r 的合成时间。如果需要完整的帧生命周期分析，应该使用 F r a m e T im e lin e 数据（见下文）。

### 帧时间分布统计

单个帧的时间意义有限，我们需要看整体分布。下面的查询把帧时间按区间分桶，统计每个桶里有多少帧：

```sql
S E L E C T
  b u ck e t_n a m e,
  C O U N T(*) A S f r a m e_co u nt
F R O M (
  S E L E C T
    C A S E
      W H E N d u r < 8 e 6  T H E N '< 8 ms (120 fps O K)'
      W H E N d u r < 11 e 6 T H E N '8-11 ms (90 fps O K)'
      W H E N d u r < 17 e 6 T H E N '11-17 ms (60 fps O K)'
      W H E N d u r < 33 e 6 T H E N '17-33 ms (j a nk)'
      W H E N d u r < 50 e 6 T H E N '33-50 ms (big j a nk)'
      E L S E '> 50 ms (h u g e j a nk)'
    E N D A S b u ck e t_n a m e,
    d u r
  F R O M slic e
  W H E R E n a m e G L O B 'C hor e ogr a ph e r#do F r a m e*'
)
G R O U P B Y b u ck e t_n a m e
O R D E R B Y M I N(d u r);
```

如果 j a nk 和 big j a nk 桶里的帧数超过总帧数的 5%，就需要关注了。这个分布也可以作为优化前后的对比基准。分别跑一遍这个查询，就能看到各个桶的帧数变化。

### F r a m e T im e lin e：系统视角的帧分析

`C hor e ogr a ph e r#do F r a m e` 只反映主线程视角。A ndroid 12（A P I 31）引入的 F r a m e T im e lin e 提供了系统视角：它同时记录期望时间线和实际时间线，能直接回答“这一帧有没有按时 pr e s e nt”。

> **版本边界**：F r a m e T im e lin e 表（`a ct u al_f r a m e_tim e lin e_slic e` / `e xp e ct e d_f r a m e_tim e lin e_slic e`）从 A ndroid 12 起稳定可用。在 A ndroid 10/11 的 tr a c e 上运行下面的查询会返回空结果；旧版本需要退回 `C hor e ogr a ph e r#do F r a m e`、`D r a w F r a m e`、S u r f ac e Fling e r 合成 slic e、f e nc e / sch e d 组合来判断帧时序。

在 P e r f etto 中，F r a m e T im e lin e 数据存储在 `a ct u al_f r a m e_tim e lin e_slic e` 和 `e xp e ct e d_f r a m e_tim e lin e_slic e` 两张表中。这里要单独记一条：配对同一帧时不能拿 `tr a ck_id` 当主键；`tr a ck_id` 只表示 slic e 落在哪条轨道上，稳定的帧标识是 `displ a y_f r a m e_tok e n`，s u r f ac e f r a m e 还要再带上 `s u r f ac e_f r a m e_tok e n`。如果要用标准库高层视图，可以先加载 `a ndroid.f r a m e s.tim e lin e`：

```sql
I N C L U D E P E R F E T T O M O D U L E a ndroid.f r a m e s.tim e lin e;

-- 查询未按时完成的 f r a m e
S E L E C T
  C A S T((a ct u al.ts - tr a c e_st a rt()) / 1 e 6 A S I N T E G E R) A S tim e_ms,
  a ct u al.l a y e r_n a m e,
  C A S T(a ct u al.d u r / 1 e 6 A S F L O A T) A S a ct u al_d u r_ms,
  C A S T(e xp e ct e d.d u r / 1 e 6 A S F L O A T) A S e xp e ct e d_d u r_ms,
  a ct u al.pr e s e nt_typ e,
  a ct u al.j a nk_typ e
F R O M a ct u al_f r a m e_tim e lin e_slic e A S a ct u al
J O I N e xp e ct e d_f r a m e_tim e lin e_slic e A S e xp e ct e d
  O N a ct u al.displ a y_f r a m e_tok e n = e xp e ct e d.displ a y_f r a m e_tok e n
 A N D I F N U L L(a ct u al.s u r f ac e_f r a m e_tok e n, -1) = I F N U L L(e xp e ct e d.s u r f ac e_f r a m e_tok e n, -1)
W H E R E a ct u al.on_tim e_f inish = 0
O R D E R B Y a ct u al.ts ;
```

这条查询更接近 P e r f etto 的表结构本身：`a ct u al` 负责给出真实结果，`e xp e ct e d` 负责给出同一帧的目标时间线，`on_tim e_f inish = 0` 直接表示这帧没有按时完成。

[已验证: P e r f etto stdlib docs 中的 F r a m e T im e lin e 表结构, p e r f etto.d e v/docs/a n a lysis/stdlib-docs]

F r a m e T im e lin e 还能检测一种更隐蔽的流畅性问题：步幅波动（c a d e nc e discr e p a ncy）。即使所有帧都在 V S ync 预算内完成，帧与帧之间的时间波动如果过大（比如 8 ms、15 ms、8 ms、15 ms 交替），用户仍然会感知到不流畅。关于这方面的深度分析，参见 §7.9 感知流畅性章节。

## 线程调度与 C P U 使用分析

帧时间告诉我们"慢不慢"，但不知道"为什么慢"。线程调度分析帮我们定位根因：主线程是在 C P U 上跑满了（C P U bo u nd），还是在等锁/等 B ind e r/等 I O（block e d）？

### 线程 C P U 时间统计

`sch e d` 表记录了每个线程在 C P U 上的运行时间。下面的查询统计指定线程（默认主线程）的总运行时间和 C P U 利用率：

```sql
-- 主线程 C P U 使用统计。把 com.e x a mpl e.a pp 替换为目标进程名
W I T H t a rg e t_proc e ss A S (
  S E L E C T u pid, pid, n a m e
  F R O M proc e ss
  W H E R E n a m e = 'com.e x a mpl e.a pp'
),
m a in_thr e ad A S (
  S E L E C T
    thr e ad.u tid,
    C O A L E S C E(thr e ad.n a m e, t a rg e t_proc e ss.n a m e) A S thr e ad_n a m e
  F R O M thr e ad
  J O I N t a rg e t_proc e ss U S I N G (u pid)
  W H E R E thr e ad.is_m a in_thr e ad = 1
     O R thr e ad.tid = t a rg e t_proc e ss.pid
)
S E L E C T
  m a in_thr e ad.thr e ad_n a m e,
  S U M(sch e d.d u r) / 1 e 6 A S tot a l_cp u_ms,
  C O U N T(*) A S sch e d u l e_co u nt,
  C A S T(S U M(sch e d.d u r) * 100.0 / (S E L E C T e nd_ts - st a rt_ts F R O M tr a c e_bo u nds) A S F L O A T) A S cp u_pct
F R O M sch e d
J O I N m a in_thr e ad U S I N G (u tid)
W H E R E sch e d.cp u I S N O T N U L L
G R O U P B Y m a in_thr e ad.thr e ad_n a m e;
```

`cp u_pct` 是整个 T r a c e 期间的 C P U 利用率。如果主线程的 C P U 利用率超过 80%，说明主线程大部分时间都在做计算——m e as u r e/l a yo u t/dr a w 太重了。如果 C P U 利用率很低但帧时间很长，说明主线程在等什么东西，需要进一步分析线程状态。

### 调度延迟：R u nn a bl e → R u nning 的时间

线程变成 R u nn a bl e（准备好运行）到实际获得 C P U 的时间差，就是调度延迟。调度延迟高意味着系统 C P U 负载重或者线程优先级低：

```sql
-- 主线程调度延迟 T op 20
-- 计算方式：线程以 R u nn a bl e 状态离开 C P U 后，到重新获得 C P U 的时间差
W I T H t a rg e t_proc e ss A S (
  S E L E C T u pid, pid, n a m e
  F R O M proc e ss
  W H E R E n a m e = 'com.e x a mpl e.a pp'
),
m a in_thr e ad A S (
  S E L E C T thr e ad.u tid
  F R O M thr e ad
  J O I N t a rg e t_proc e ss U S I N G (u pid)
  W H E R E thr e ad.is_m a in_thr e ad = 1
     O R thr e ad.tid = t a rg e t_proc e ss.pid
),
m a in_sch e d A S (
  S E L E C T
    sch e d.ts,
    sch e d.d u r,
    sch e d.e nd_st a t e,
    sch e d.ts + sch e d.d u r A S l e ft_a t,
    L E A D(sch e d.ts) O V E R (P A R T I T I O N B Y sch e d.u tid O R D E R B Y sch e d.ts) A S r u n_st a rt,
    L E A D(sch e d.cp u) O V E R (P A R T I T I O N B Y sch e d.u tid O R D E R B Y sch e d.ts) A S r u n_cp u,
    L E A D(sch e d.ts) O V E R (P A R T I T I O N B Y sch e d.u tid O R D E R B Y sch e d.ts) - (sch e d.ts + sch e d.d u r) A S d e l a y_ns,
    sch e d.cp u A S l e ft_cp u
  F R O M sch e d
  J O I N m a in_thr e ad U S I N G (u tid)
)
S E L E C T
  C A S T((r u n_st a rt - tr a c e_st a rt()) / 1 e 6 A S I N T E G E R) A S tim e_ms,
  C A S T(d e l a y_ns / 1 e 6 A S F L O A T) A S d e l a y_ms,
  l e ft_cp u,
  r u n_cp u
F R O M m a in_sch e d
W H E R E e nd_st a t e I N ('R', 'R+')   -- 只看被抢占后仍为 R u nn a bl e 的记录
  A N D d e l a y_ns > 0
O R D E R B Y d e l a y_ns D E S C
L I M I T 20;
```

这个查询的核心逻辑：从 `sch e d` 表中找到主线程以 `R`（R u nn a bl e）或 `R+`（R u nn a bl e pr e empt e d）状态离开 C P U 的记录，然后用 `L E A D()` 窗口函数取同一 u tid 的下一条调度记录，两者的时间差就是调度延迟。如果 `d e l a y_ms` 频繁超过 5 ms，说明系统 C P U 负载很重，主线程在排队等 C P U。处理方向是减少后台 R u nn a bl e 竞争：限制业务线程池并发、降低后台线程优先级、拆分长 C P U 任务、排查热降频或系统负载。`S C H E D_F I F O` 只适用于系统/厂商特权进程的受控场景；普通 A pp 没有 `C A P_S Y S_N I C E`，不能把 U I 主线程切到实时调度，滥用还可能造成系统饥饿和 w a tchdog 风险。

### 线程状态分布

如果要看线程在 R u nning / R / S / D 这些状态上各花了多少时间，应该直接查 `thr e ad_st a t e` 表，而不是把 `sch e d.e nd_st a t e` 当成“当前状态”。`sch e d.e nd_st a t e` 更适合回答“这次 C P U slic e 结束时，线程以什么状态离开 C P U”。

```sql
-- 主线程状态分布
W I T H t a rg e t_proc e ss A S (
  S E L E C T u pid, pid, n a m e
  F R O M proc e ss
  W H E R E n a m e = 'com.e x a mpl e.a pp'
),
m a in_thr e ad A S (
  S E L E C T thr e ad.u tid
  F R O M thr e ad
  J O I N t a rg e t_proc e ss U S I N G (u pid)
  W H E R E thr e ad.is_m a in_thr e ad = 1
     O R thr e ad.tid = t a rg e t_proc e ss.pid
),
m a in_st a t e s A S (
  S E L E C T thr e ad_st a t e.*
  F R O M thr e ad_st a t e
  J O I N m a in_thr e ad U S I N G (u tid)
)
S E L E C T
  st a t e,
  S U M(d u r) / 1 e 6 A S tot a l_ms,
  R O U N D(S U M(d u r) * 100.0 / (S E L E C T S U M(d u r) F R O M m a in_st a t e s), 1) A S pct
F R O M m a in_st a t e s
G R O U P B Y st a t e
O R D E R B Y tot a l_ms D E S C;
```

常见的 `thr e ad_st a t e.st a t e` 值：

- **R u nning**：线程当前正在 C P U 上执行
- **R / R+**：线程已经可运行，但还在等 C P U
- **S**：可中断睡眠，常见于等锁、等 B ind e r、等条件变量
- **D**：不可中断睡眠，常见于内核态 I O 等待

如果主线程的 `S` 或 `D` 占比异常高，结合时间线可以定位到具体在等什么——这就是下一节 B ind e r 分析和锁竞争分析要解决的问题。

## B ind e r 事务分析

B ind e r 是 A ndroid 进程间通信的主要机制。一次同步 B ind e r 调用通常包含客户端发起事务、服务端线程接收事务、服务端处理、客户端收到回复几个阶段。P e r f etto 会把 B ind e r 相关内核事件和框架侧 slic e 导入 tr a c e；S Q L 分析时要区分“公开 tr a c e point”和“回复语义”。

### B ind e r 事务耗时统计

L in u x f tr a c e 中常用的 B ind e r tr a c e point 是 `bind e r_tr a ns a ction`、`bind e r_tr a ns a ction_r e c e iv e d`、`bind e r_r e t u rn`、`bind e r_comm a nd` 等，A O S P `driv e rs/a ndroid/bind e r_tr a c e.h` 没有 `T R A C E_E V E N T(bind e r_r e ply)`。回复路径应通过 `bind e r_r e t u rn` / `bind e r_comm a nd` 中的 `B R_R E P L Y` / `B C_R E P L Y`，或 P e r f etto 导出的 A ndroid B ind e r slic e / a rgs 描述。一次同步调用可拆成三个时间维度：

- **cli e nt_d u r**：客户端总等待时间（从发起调用到收到回复）
- **s e rv e r_d u r**：服务端实际处理时间
- **disp a tch_d u r**：服务端排队等待时间（从收到请求到开始处理）

当 `disp a tch_d u r` 持续大于 `s e rv e r_d u r` 时，说明服务端开始出现排队。线程上限要按进程口径看：普通 libbind e r 进程的 `D E F A U L T_M A X_B I N D E R_T H R E A D S` 是 15；`syst e m_s e rv e r` 在 `S yst e m S erv e r.j a v a` 中把 `s M ax B ind e r T hr e ads` 配成 31；厂商进程或 n a tiv e 服务还可以通过 `P roc e ss S t a t e:: s e t T hr e ad P ool M ax T hr e ad C o u nt()` 调整。排队时间升高不一定来自线程数本身，还要结合服务端 C P U 忙、锁等待和同步 B ind e r 嵌套调用判断。

> **说明**：下面的 S Q L 通过 `slic e.n a m e G L O B '*bind e r*'` 筛选 B ind e r 相关 slic e，能量化单次调用的总耗时。准确分离 cli e nt/s e rv e r/disp a tch 三段时，要把 `bind e r_tr a ns a ction`、`bind e r_tr a ns a ction_r e c e iv e d` 与 `bind e r_r e t u rn` / `bind e r_comm a nd` 的 r e ply 语义按 tr a ns a ction id、d e b u g id 或时间窗关联起来。本节先处理总耗时排序，三段拆分可在后续专题中展开。

```sql
-- B ind e r 事务按耗时排序 T op 20
S E L E C T
  C A S T((slic e.ts - tr a c e_st a rt()) / 1 e 6 A S I N T E G E R) A S tim e_ms,
  slic e.n a m e,
  C A S T(slic e.d u r / 1 e 6 A S F L O A T) A S d u r_ms,
  thr e ad.n a m e A S thr e ad_n a m e,
  proc e ss.n a m e A S proc e ss_n a m e
F R O M slic e
J O I N thr e ad_tr a ck O N slic e.tr a ck_id = thr e ad_tr a ck.id
J O I N thr e ad U S I N G (u tid)
J O I N proc e ss U S I N G (u pid)
W H E R E slic e.n a m e G L O B '*bind e r*'
  A N D slic e.d u r > 1 e 6  -- 过滤掉 < 1 ms 的轻量调用
O R D E R B Y slic e.d u r D E S C
L I M I T 20;
```

[已验证: P e r f etto B ind e r tr a ns a ction a n a lysis, p e r f etto.d e v/docs]

### 跨进程 B ind e r 调用链追踪

在实际分析中，我们经常需要追踪一个 B ind e r 调用从客户端到服务端的完整路径。在 P e r f etto U I 中，这对应的是 A ndroid B ind e r / T r a ns a ctions tr a ck。在 S Q L 中，需要通过时间戳关联来连接客户端和服务端的 slic e：

```sql
-- 查找主线程发起的长时间 B ind e r 调用
W I T H t a rg e t_proc e ss A S (
  S E L E C T u pid, pid, n a m e
  F R O M proc e ss
  W H E R E n a m e = 'com.e x a mpl e.a pp'
),
m a in_thr e ad A S (
  S E L E C T thr e ad.u tid
  F R O M thr e ad
  J O I N t a rg e t_proc e ss U S I N G (u pid)
  W H E R E thr e ad.is_m a in_thr e ad = 1
     O R thr e ad.tid = t a rg e t_proc e ss.pid
)
S E L E C T
  C A S T((slic e.ts - tr a c e_st a rt()) / 1 e 6 A S I N T E G E R) A S tim e_ms,
  slic e.n a m e,
  C A S T(slic e.d u r / 1 e 6 A S F L O A T) A S d u r_ms,
  E X T R A C T_A R G(slic e.a rg_s e t_id, 'cod e') A S bind e r_cod e
F R O M slic e
J O I N thr e ad_tr a ck O N slic e.tr a ck_id = thr e ad_tr a ck.id
J O I N m a in_thr e ad O N thr e ad_tr a ck.u tid = m a in_thr e ad.u tid
W H E R E slic e.n a m e G L O B '*bind e r*'
  A N D slic e.d u r > 50 e 6  -- 超过 50 ms 的 B ind e r 调用
O R D E R B Y slic e.d u r D E S C;
```

`bind e r_cod e` 是 B ind e r 调用的方法编号，可以对照 A I D L 接口定义确定具体调用了哪个方法。`E X T R A C T_A R G()` 返回的是 P e r f etto S Q L 的动态值；如果后续要按编号做大小比较或分桶，先用 `C A S T(E X T R A C T_A R G(slic e.a rg_s e t_id, 'cod e') A S I N T E G E R)` 转成整数。结合 §1.4 B ind e r I P C 章节的知识，可以判断这个耗时是否合理。

### B ind e r 线程池利用率

当所有 B ind e r 线程都处于忙碌状态时，新请求会排队等待，这就是 A N R 的常见原因之一。通过统计同一时刻活跃的 B ind e r 线程数，可以判断线程池是否饱和：

```sql
-- 统计 syst e m_s e rv e r 中 B ind e r 线程的活跃时间
S E L E C T
  thr e ad.n a m e A S bind e r_thr e ad,
  S U M(sch e d.d u r) / 1 e 6 A S cp u_ms,
  C O U N T(*) A S sch e d_co u nt
F R O M sch e d
J O I N thr e ad U S I N G (u tid)
J O I N proc e ss U S I N G (u pid)
W H E R E proc e ss.n a m e = 'syst e m_s e rv e r'
  A N D thr e ad.n a m e G L O B 'B ind e r :*'
G R O U P B Y thr e ad.n a m e
O R D E R B Y cp u_ms D E S C;
```

这个查询统计的是 B ind e r 线程获得 C P U 执行的时间，不能直接等同于线程池利用率。如果多数 `B ind e r :*` 线程在同一时间窗内都有较高 `cp u_ms`，同时客户端 B ind e r slic e 的耗时或 `bind e r_tr a ns a ction` 排队间隔也在升高，才可以判断服务端接近饱和。后续处理方向通常是缩短服务端同步工作、拆掉嵌套同步 B ind e r 调用，或在确认业务模型允许后调整线程池上限。

## 内存与 G C 分析

G C（垃圾回收）暂停是 j a nk 的常见来源之一。当 A R T 运行时触发 G C 时，会暂停所有 J a v a 线程（S top-T h e-W orld），如果暂停时间超过几毫秒，就会导致掉帧。

### G C 事件统计

```sql
-- G C 事件统计
S E L E C T
  C O U N T(*) A S gc_co u nt,
  C A S T(S U M(d u r) / 1 e 6 A S F L O A T) A S tot a l_p a us e_ms,
  C A S T(M A X(d u r) / 1 e 6 A S F L O A T) A S m a x_p a us e_ms,
  C A S T(A V G(d u r) / 1 e 6 A S F L O A T) A S a vg_p a us e_ms
F R O M slic e
J O I N thr e ad_tr a ck O N slic e.tr a ck_id = thr e ad_tr a ck.id
J O I N thr e ad U S I N G (u tid)
W H E R E slic e.n a m e G L O B '*G C*'
  O R slic e.n a m e G L O B '*G a rb a g e Coll e ctor*';
```

这个查询给出 G C 的全景统计。如果 `a vg_p a us e_ms` 超过 3-5 ms，或者 `m a x_p a us e_ms` 超过 16 ms（一帧的预算），就需要继续查。G C 暂停和帧时间的关联分析要限定同一进程，并把 f r a m e 限在主线程：

```sql
-- G C 暂停与同进程主线程帧时间的关联
S E L E C T
  gc_proc e ss.n a m e A S proc e ss_n a m e,
  gc.ts A S gc_ts,
  C A S T(gc.d u r / 1 e 6 A S F L O A T) A S gc_ms,
  C A S T(f r a m e.d u r / 1 e 6 A S F L O A T) A S f r a m e_ms
F R O M slic e A S gc
J O I N thr e ad_tr a ck A S gc_tr a ck O N gc.tr a ck_id = gc_tr a ck.id
J O I N thr e ad A S gc_thr e ad O N gc_tr a ck.u tid = gc_thr e ad.u tid
J O I N proc e ss A S gc_proc e ss O N gc_thr e ad.u pid = gc_proc e ss.u pid
J O I N slic e A S f r a m e
  O N f r a m e.n a m e G L O B 'C hor e ogr a ph e r#do F r a m e*'
 A N D f r a m e.ts < gc.ts + gc.d u r
 A N D gc.ts < f r a m e.ts + f r a m e.d u r
J O I N thr e ad_tr a ck A S f r a m e_tr a ck O N f r a m e.tr a ck_id = f r a m e_tr a ck.id
J O I N thr e ad A S f r a m e_thr e ad O N f r a m e_tr a ck.u tid = f r a m e_thr e ad.u tid
J O I N proc e ss A S f r a m e_proc e ss O N f r a m e_thr e ad.u pid = f r a m e_proc e ss.u pid
W H E R E (gc.n a m e G L O B '*G C*' O R gc.n a m e G L O B '*G a rb a g e Coll e ctor*')
  A N D gc.d u r > 1 e 6
  A N D gc_proc e ss.n a m e = 'com.e x a mpl e.a pp'
  A N D gc_proc e ss.u pid = f r a m e_proc e ss.u pid
  A N D (f r a m e_thr e ad.is_m a in_thr e ad = 1 O R f r a m e_thr e ad.tid = f r a m e_proc e ss.pid)
O R D E R B Y gc.d u r D E S C;
```

这个查询找出与目标进程主线程 `do F r a m e` 重叠的 G C 暂停。结果中如果有 `gc_ms` 接近或超过 5 ms 的记录，再沿着同一进程的分配热点继续查。大规模 T r a c e 上，优先把目标进程和时间窗加进 W H E R E；更复杂的区间交集可以改用 P e r f etto S Q L 的 `S P A N_J O I N` 或 `int e rv a ls.int e rs e ct` / `int e rv a ls.ov e rl a p` 标准库宏。

### J a v a H e ap 变化趋势

J a v a H e ap 在 P e r f etto 里有三条常用观察路径。第一步先确认 tr a c e 里有哪些 co u nt e r：

```sql
-- 查看可用的 J a v a / H e ap 相关 co u nt e r 名称
S E L E C T D I S T I N C T co u nt e r_tr a ck.n a m e
F R O M co u nt e r_tr a ck
W H E R E co u nt e r_tr a ck.n a m e G L O B '*J a v a*H e ap*'
   O R co u nt e r_tr a ck.n a m e I N ('H e ap siz e (K B)', 'm e m.j a v a_h e ap')
   O R co u nt e r_tr a ck.n a m e G L O B '*_M E M_S T A T S*J a v a*'
O R D E R B Y co u nt e r_tr a ck.n a m e;
```

路径一是连续趋势，适合观察进程内存压力和 J a v a h e ap co u nt e r 的变化：

```sql
-- J a v a H e ap / H e ap co u nt e r 趋势。v a l u e_r a w 的单位要按 co u nt e r 名称和数据源确认
S E L E C T
  C A S T((co u nt e r.ts - tr a c e_st a rt()) / 1 e 6 A S I N T E G E R) A S tim e_ms,
  co u nt e r_tr a ck.n a m e A S co u nt e r_n a m e,
  co u nt e r.v a l u e A S v a l u e_r a w
F R O M co u nt e r
J O I N co u nt e r_tr a ck O N co u nt e r.tr a ck_id = co u nt e r_tr a ck.id
W H E R E co u nt e r_tr a ck.n a m e G L O B '*J a v a*H e ap*'
   O R co u nt e r_tr a ck.n a m e I N ('H e ap siz e (K B)', 'm e m.j a v a_h e ap')
   O R co u nt e r_tr a ck.n a m e G L O B '*_M E M_S T A T S*J a v a*'
O R D E R B Y co u nt e r.ts ;
```

路径二是 J a v a h e ap d u mp。它依赖 h e ap gr a ph / `a ndroid.j a v a_hpro f` 相关数据源，分析对象数量、类名和引用关系时看 `h e ap_gr a ph_obj e ct`、`h e ap_gr a ph_cl a ss`、`h e ap_gr a ph_r e f e r e nc e` 等表。

路径三是 J a v a a lloc a tion s a mpling。它依赖 h e appro f d 与 A R T J a v a a lloc a tion 相关配置，分析分配热点时看 `h e ap_pro f il e_a lloc a tion` 以及 c a llsit e / f r a m e 相关表。`proc e ss_st a ts` 里的 `m e m.rss.a non` 只能表示匿名 R S S 趋势，不能直接当成 J a v a H e ap。

如果 H e ap 相关 co u nt e r 呈锯齿形上升（分配→G C 回收→再分配→再回收），且每次 G C 后的基准线持续抬高，说明存在内存泄漏。参见 §10.2 内存泄漏章节。

[已验证: P e r f etto co u nt e r / h e ap gr a ph / h e appro f d 表族；co u nt e r 名称随 tr a c e 配置和 A ndroid 版本变化]

## 启动时间分析

冷启动是从用户点击 A pp 图标到首帧渲染完成的过程。P e r f etto S Q L 可以分解这个过程中的关键阶段。`Z ygot e Init` 要单独看：它是 zygot e 进程初始化 / 系统启动阶段的 tr a c e s e ction，不是每次 A pp 冷启动都会出现的应用侧阶段。

### 冷启动全流程时间分解

系统启动或 zygot e 初始化分析时，可以查精确的 `Z ygot e Init` slic e：

```sql
-- 系统启动 / zygot e 初始化中的 Z ygot e Init slic e
S E L E C T
  slic e.n a m e,
  C A S T((slic e.ts - tr a c e_st a rt()) / 1 e 6 A S I N T E G E R) A S st a rt_ms,
  C A S T(slic e.d u r / 1 e 6 A S F L O A T) A S d u r_ms
F R O M slic e
W H E R E slic e.n a m e = 'Z ygot e Init'
O R D E R B Y slic e.ts ;
```

A pp 冷启动分析更常看进程创建、绑定应用、主线程入口和首帧。下面的查询同时兼容 thr e ad tr a ck 与 proc e ss tr a ck：

```sql
-- A pp 冷启动关键节点。按实际 tr a c e 中的 slic e 名再收窄 W H E R E
S E L E C T
  slic e.n a m e,
  C A S T((slic e.ts - tr a c e_st a rt()) / 1 e 6 A S I N T E G E R) A S st a rt_ms,
  C A S T(slic e.d u r / 1 e 6 A S F L O A T) A S d u r_ms,
  C O A L E S C E(thr e ad_proc e ss.n a m e, tr a ck_proc e ss.n a m e, thr e ad.n a m e, 'u nknown') A S own e r
F R O M slic e
L E F T J O I N thr e ad_tr a ck O N slic e.tr a ck_id = thr e ad_tr a ck.id
L E F T J O I N thr e ad O N thr e ad_tr a ck.u tid = thr e ad.u tid
L E F T J O I N proc e ss A S thr e ad_proc e ss O N thr e ad.u pid = thr e ad_proc e ss.u pid
L E F T J O I N proc e ss_tr a ck O N slic e.tr a ck_id = proc e ss_tr a ck.id
L E F T J O I N proc e ss A S tr a ck_proc e ss O N proc e ss_tr a ck.u pid = tr a ck_proc e ss.u pid
W H E R E slic e.n a m e G L O B '*a m_proc_st a rt*'
   O R slic e.n a m e G L O B '*bind A pplic a tion*'
   O R slic e.n a m e G L O B '*A ctivity T hr e ad*'
   O R slic e.n a m e I N ('A pplic a tion.on C r e at e', 'A ctivity.on C r e at e')
   O R slic e.n a m e G L O B 'C hor e ogr a ph e r#do F r a m e*'
O R D E R B Y slic e.ts ;
```

[已验证: A O S P Z ygot e Init.j a v a 使用 `Z ygot e Init` tr a c e s e ction；A pp 冷启动节点需按实际 tr a c e 中的 slic e 名确认]

通过这个查询可以得到启动过程中各个阶段的时间线。`A pplic a tion.on C r e at e`、`A ctivity.on C r e at e` 是否可见，取决于应用或 F r a m e work 是否写入对应 tr a c e s e ction。如果某个阶段明显偏长，可以进一步分析该阶段内的 B ind e r 调用和锁等待。

### 启动过程中的 B ind e r 调用统计

```sql
-- 启动阶段的 B ind e r 调用统计
W I T H t a rg e t_proc e ss A S (
  S E L E C T u pid, pid, n a m e
  F R O M proc e ss
  W H E R E n a m e = 'com.e x a mpl e.a pp'
),
m a in_thr e ad A S (
  S E L E C T thr e ad.u tid
  F R O M thr e ad
  J O I N t a rg e t_proc e ss U S I N G (u pid)
  W H E R E thr e ad.is_m a in_thr e ad = 1
     O R thr e ad.tid = t a rg e t_proc e ss.pid
),
st a rt u p_window A S (
  S E L E C T
    M I N(C A S E W H E N slic e.n a m e G L O B '*bind A pplic a tion*' T H E N slic e.ts E N D) A S st a rt_ts,
    M I N(C A S E W H E N slic e.n a m e G L O B 'C hor e ogr a ph e r#do F r a m e*' T H E N slic e.ts E N D) A S e nd_ts
  F R O M slic e
  J O I N thr e ad_tr a ck O N slic e.tr a ck_id = thr e ad_tr a ck.id
  J O I N m a in_thr e ad O N thr e ad_tr a ck.u tid = m a in_thr e ad.u tid
)
S E L E C T
  slic e.n a m e,
  C O U N T(*) A S c a ll_co u nt,
  C A S T(S U M(slic e.d u r) / 1 e 6 A S F L O A T) A S tot a l_ms,
  C A S T(A V G(slic e.d u r) / 1 e 6 A S F L O A T) A S a vg_ms,
  C A S T(M A X(slic e.d u r) / 1 e 6 A S F L O A T) A S m a x_ms
F R O M slic e
J O I N thr e ad_tr a ck O N slic e.tr a ck_id = thr e ad_tr a ck.id
J O I N m a in_thr e ad O N thr e ad_tr a ck.u tid = m a in_thr e ad.u tid
C R O S S J O I N st a rt u p_window
W H E R E slic e.n a m e G L O B '*bind e r*'
  A N D slic e.ts B E T W E E N st a rt u p_window.st a rt_ts A N D st a rt u p_window.e nd_ts
G R O U P B Y slic e.n a m e
O R D E R B Y tot a l_ms D E S C;
```

这个查询统计从 `bind A pplic a tion` 到首帧 `do F r a m e` 之间主线程发起的所有 B ind e r 调用。`tot a l_ms` 最高的几个调用就是启动速度的瓶颈点。参见 §8.2 启动全流程章节的分析方法。

## A N R 分析

A N R（A pplic a tion N ot R e sponding）是用户最直接感知的性能问题。A N R 发生时，系统会 d u mp 当前线程堆栈到 `/d a t a/a nr/` 目录。但堆栈只能看到 A N R 时刻的快照，无法看到"导致 A N R 的 5 秒里主线程到底在做什么"。P e r f etto S Q L 可以补全这个时间窗口。下面两组 S Q L 依赖 `thr e ad_st a t e` 和 `slic e`；如果要继续拆 B ind e r 阶段，还要在抓取配置里启用 B ind e r f tr a c e e v e nts。

### A N R 前后主线程活动分析

```sql
-- A N R 前后 5 秒主线程活动
W I T H p a r a ms A S (
  -- 替换 0：A N R 发生时刻相对 tr a c e_st a rt() 的纳秒偏移
  S E L E C T tr a c e_st a rt() + 0 A S a nr_ts
),
window A S (
  S E L E C T
    a nr_ts - 5000000000 A S st a rt_ts,
    a nr_ts + 1000000000 A S e nd_ts
  F R O M p a r a ms
)
S E L E C T
  C A S T((slic e.ts - tr a c e_st a rt()) / 1 e 6 A S I N T E G E R) A S tim e_ms,
  proc e ss.n a m e A S proc e ss_n a m e,
  slic e.n a m e,
  C A S T(slic e.d u r / 1 e 6 A S F L O A T) A S d u r_ms,
  slic e.d e pth
F R O M slic e
J O I N thr e ad_tr a ck O N slic e.tr a ck_id = thr e ad_tr a ck.id
J O I N thr e ad U S I N G (u tid)
J O I N proc e ss U S I N G (u pid)
C R O S S J O I N window
W H E R E proc e ss.n a m e = 'com.e x a mpl e.a pp'  -- 替换为目标进程
  A N D (thr e ad.is_m a in_thr e ad = 1 O R thr e ad.tid = proc e ss.pid)
  A N D slic e.ts < window.e nd_ts
  A N D slic e.ts + slic e.d u r > window.st a rt_ts
O R D E R B Y slic e.ts ;
```

实际使用时，先定位 A N R 时间点（在 P e r f etto U I 中搜索 `a m_a nr` 或 A N R 相关 slic e），再把 `p a r a ms.a nr_ts` 换成真实时间。

### 主线程阻塞原因分类

A N R / 卡顿排查应以 `thr e ad_st a t e` 为主表，因为它记录主线程在一段时间里的状态；`sch e d.e nd_st a t e` 只描述 C P U slic e 结束那一刻。下面的查询先裁剪 A N R 时间窗，再为每个 `thr e ad_st a t e` 只挑一个重叠时间最长的 slic e，避免嵌套 slic e 重复放大 `tot a l_ms`：

```sql
-- 主线程阻塞原因分类
W I T H p a r a ms A S (
  -- 替换 0：A N R 发生时刻相对 tr a c e_st a rt() 的纳秒偏移
  S E L E C T tr a c e_st a rt() + 0 A S a nr_ts
),
window A S (
  S E L E C T
    a nr_ts - 5000000000 A S st a rt_ts,
    a nr_ts + 1000000000 A S e nd_ts
  F R O M p a r a ms
),
m a in_st a t e s A S (
  S E L E C T
    thr e ad_st a t e.id A S st a t e_id,
    thr e ad_st a t e.u tid,
    thr e ad_st a t e.st a t e,
    M A X(thr e ad_st a t e.ts, window.st a rt_ts) A S ts,
    M I N(thr e ad_st a t e.ts + thr e ad_st a t e.d u r, window.e nd_ts)
      - M A X(thr e ad_st a t e.ts, window.st a rt_ts) A S d u r
  F R O M thr e ad_st a t e
  J O I N thr e ad U S I N G (u tid)
  J O I N proc e ss U S I N G (u pid)
  C R O S S J O I N window
  W H E R E proc e ss.n a m e = 'com.e x a mpl e.a pp'  -- 替换为目标进程
    A N D (thr e ad.is_m a in_thr e ad = 1 O R thr e ad.tid = proc e ss.pid)
    A N D thr e ad_st a t e.st a t e != 'R u nning'
    A N D thr e ad_st a t e.ts < window.e nd_ts
    A N D thr e ad_st a t e.ts + thr e ad_st a t e.d u r > window.st a rt_ts
),
st a t e_with_slic e A S (
  S E L E C T
    m a in_st a t e s.*,
    (
      S E L E C T n a m e
      F R O M (
        S E L E C T
          s.n a m e,
          M I N(s.ts + s.d u r, m a in_st a t e s.ts + m a in_st a t e s.d u r)
            - M A X(s.ts, m a in_st a t e s.ts) A S ov e rl a p_d u r
        F R O M slic e A S s
        J O I N thr e ad_tr a ck A S tt O N s.tr a ck_id = tt.id
        W H E R E tt.u tid = m a in_st a t e s.u tid
          A N D s.ts < m a in_st a t e s.ts + m a in_st a t e s.d u r
          A N D s.ts + s.d u r > m a in_st a t e s.ts
        O R D E R B Y ov e rl a p_d u r D E S C
        L I M I T 1
      )
    ) A S slic e_n a m e
  F R O M m a in_st a t e s
)
S E L E C T
  C A S E
    W H E N slic e_n a m e G L O B '*monitor*' T H E N 'L ock C ont e ntion'
    W H E N slic e_n a m e G L O B '*bind e r*' T H E N 'B ind e r C a ll'
    W H E N st a t e = 'D' T H E N 'U nint e rr u ptibl e I O'
    W H E N st a t e = 'S' T H E N 'S l e eping (g e n e ric)'
    W H E N st a t e I N ('R', 'R+') T H E N 'R u nn a bl e b u t w a iting f or C P U'
    E L S E 'O th e r : ' || C O A L E S C E(slic e_n a m e, st a t e, 'u nknown')
  E N D A S block_r e ason,
  C O U N T(*) A S co u nt,
  C A S T(S U M(d u r) / 1 e 6 A S F L O A T) A S tot a l_ms
F R O M st a t e_with_slic e
W H E R E d u r > 0
G R O U P B Y block_r e ason
O R D E R B Y tot a l_ms D E S C;
```

这个结果按裁剪后的 `thr e ad_st a t e.d u r` 统计，每段状态只计一次。大规模 T r a c e 上，先缩小 `window.st a rt_ts` / `window.e nd_ts`；更复杂的多区间交集，优先使用 P e r f etto S Q L 的 `S P A N_J O I N`、`int e rv a ls.int e rs e ct` / `int e rv a ls.ov e rl a p` 标准库宏，或对应标准库视图。

## 锁竞争与同步分析

锁竞争（L ock C ont e ntion）是 j a nk 和 A N R 的核心诱因之一。当主线程尝试获取一个被其他线程持有的锁时，它会被阻塞——这段等待时间在 P e r f etto 中表现为 `monitor cont e ntion` 事件。

### M onitor C ont e ntion T op N

```sql
I N C L U D E P E R F E T T O M O D U L E a ndroid.monitor_cont e ntion ;

-- 主线程锁竞争 T op 10（等待时间最长）
S E L E C T
  C A S T(d u r / 1 e 6 A S F L O A T) A S w a it_ms,
  block e d_thr e ad_n a m e A S w a it e r_thr e ad,
  blocking_thr e ad_n a m e A S own e r_thr e ad,
  short_block e d_m e thod,
  short_blocking_m e thod,
  w a it e r_co u nt
F R O M a ndroid_monitor_cont e ntion
W H E R E is_block e d_thr e ad_m a in = 1
O R D E R B Y d u r D E S C
L I M I T 10;
```

`a ndroid_monitor_cont e ntion` 在 P e r f etto v 54.0 中已经把 own e r 线程、block e d 线程和相关方法解析好了，比直接在原始 `slic e` 上用名字模糊匹配稳定得多。当前 P e r f etto stdlib 文档还提供 `lock_n a m e` 列；如果本机 T r a c e P roc e ssor 支持该列，可以把它加回 S E L E C T，否则从原始 `slic e` / `a rgs` 表补查锁对象名。结合 P e r f etto U I 的 L ock cont e ntion tr a ck，可以快速定位锁竞争的全貌。

### 锁竞争与帧时间关联

锁竞争本身并不直接等于卡顿。只有它落在帧渲染期间，才会拉长这一帧的耗时。下面的查询把 `a ndroid_monitor_cont e ntion` 放进主线程 `do F r a m e` 的同一时间窗口：

```sql
I N C L U D E P E R F E T T O M O D U L E a ndroid.monitor_cont e ntion ;

-- 帧期间的锁竞争
S E L E C T
  f r a m e.d u r / 1 e 6 A S f r a m e_ms,
  cont e ntion.d u r / 1 e 6 A S lock_w a it_ms,
  R O U N D(cont e ntion.d u r * 100.0 / f r a m e.d u r, 1) A S lock_pct,
  cont e ntion.blocking_thr e ad_n a m e A S own e r_thr e ad,
  cont e ntion.short_blocking_m e thod,
  cont e ntion.short_block e d_m e thod
F R O M slic e A S f r a m e
J O I N thr e ad_tr a ck A S f t O N f r a m e.tr a ck_id = f t.id
J O I N thr e ad A S f t_thr e ad O N f t.u tid = f t_thr e ad.u tid
J O I N proc e ss A S f t_proc e ss O N f t_thr e ad.u pid = f t_proc e ss.u pid
J O I N a ndroid_monitor_cont e ntion A S cont e ntion
  O N cont e ntion.block e d_u tid = f t_thr e ad.u tid
 A N D cont e ntion.ts >= f r a m e.ts
 A N D cont e ntion.ts + cont e ntion.d u r <= f r a m e.ts + f r a m e.d u r
W H E R E f r a m e.n a m e G L O B 'C hor e ogr a ph e r#do F r a m e*'
  A N D f t_proc e ss.n a m e = 'com.e x a mpl e.a pp'
  A N D (f t_thr e ad.is_m a in_thr e ad = 1 O R f t_thr e ad.tid = f t_proc e ss.pid)
  A N D cont e ntion.d u r > 500000  -- 过滤 < 0.5 ms 的短暂等待
O R D E R B Y cont e ntion.d u r D E S C;
```

如果 `lock_pct` 超过 30%，说明这一帧卡顿的主要原因是锁等待。根因分析方法：从 `own e r_thr e ad`、`short_blocking_m e thod` 和 `short_block e d_m e thod` 继续沿着持锁线程的时间线往后查；本机 T r a c e P roc e ssor 若支持 `lock_n a m e`，再把锁对象名纳入判断。参见 §1.14 锁竞争与同步性能分析章节。

[已验证: googl e/p e r f etto v 54.0 `a ndroid.monitor_cont e ntion.sql` + P e r f etto 当前 stdlib docs]

## S P A N_J O I N 与窗口函数：跨维度时间序列交叉分析

S P A N_J O I N 和窗口函数是 P e r f etto S Q L 中**跨维度关联分析的核心语法**。当帧时间需要和 C P U 频率、G C 暂停、或 B ind e r 排队做交叉分析时，单靠等值 J O I N 无法处理"时间段重叠"的语义——这时需要 S P A N_J O I N。

### S P A N_J O I N 机制

S P A N_J O I N 是一个**自定义算子表（O p e r a tor T a bl e）**，由 C++ 实现时间跨度交集计算，对外暴露为 S Q L 虚拟表。它的输入是两个含 `ts` 和 `d u r` 列的表/视图，输出是两表在时间上存在重叠的行组合。

```sql
-- 调度切片 × C P U 频率的跨维度关联
C R E A T E V I E W sp_sch e d A S
S E L E C T ts, d u r, cp u, u tid F R O M sch e d ;

C R E A T E V I E W sp_f r e q u ency A S
S E L E C T
  ts,
  l e ad(ts) O V E R (P A R T I T I O N B Y tr a ck_id O R D E R B Y ts) - ts a s d u r,
  cp u,
  v a l u e a s f r e q
F R O M co u nt e r
J O I N cp u_co u nt e r_tr a ck O N co u nt e r.tr a ck_id = cp u_co u nt e r_tr a ck.id
W H E R E cp u_co u nt e r_tr a ck.n a m e = 'cp u fr e q';

C R E A T E V I R T U A L T A B L E sch e d_with_f r e q
U S I N G S P A N_J O I N(sp_sch e d P A R T I T I O N E D cp u, sp_f r e q u ency P A R T I T I O N E D cp u);

S E L E C T ts, d u r, cp u, u tid, f r e q F R O M sch e d_with_f r e q ;
```

关键参数：
- `P A R T I T I O N E D col`：按整数列分区后再做交集，可将 O(n×m) 降到 O(n+m)
- 分区列**必须是整数**，字符串需通过 `H A S H()` 转换
- 同一表同一分区内的 sp a ns **不能重叠**，否则静默产生错误结果

变体：`S P A N_L E F T_J O I N`（左表分区+右表不分区）、`S P A N_O U T E R_J O I N`（两者都不分区）。

窗口函数 `L E A D()` 在这里的作用是把离散的 co u nt e r 点转换为连续的 sp a n：取当前行 ts 为起点，下一行的 ts 减当前 ts 为 d u r——这是把"点"变成"段"的常用技巧。

### 应用场景：帧 × C P U 频率 × 锁竞争三维关联

```sql
I N C L U D E P E R F E T T O M O D U L E a ndroid.monitor_cont e ntion ;

-- 先用窗口函数把主线程锁等待转为 sp a n
C R E A T E V I E W m a in_lock_sp a n A S
S E L E C T
  block e d_u tid A S u tid,
  ts,
  d u r,
  blocking_thr e ad_n a m e
F R O M a ndroid_monitor_cont e ntion
W H E R E is_block e d_thr e ad_m a in = 1
  A N D block e d_u tid I S N O T N U L L;

-- 再 S P A N_J O I N 调度切片
C R E A T E V I R T U A L T A B L E f r a m e_lock_cp u
U S I N G S P A N_J O I N(
  m a in_lock_sp a n P A R T I T I O N E D u tid,
  sp_sch e d P A R T I T I O N E D u tid
);

-- 帧 × 锁等待 × C P U 频率三维交叉（示意；按目标进程和时间窗继续裁剪）
S E L E C T
  sch e d_with_f r e q.ts,
  sch e d_with_f r e q.d u r,
  sch e d_with_f r e q.u tid,
  sch e d_with_f r e q.cp u,
  sch e d_with_f r e q.f r e q,
  f r a m e_lock_cp u.blocking_thr e ad_n a m e
F R O M sch e d_with_f r e q
J O I N f r a m e_lock_cp u
  O N sch e d_with_f r e q.u tid = f r a m e_lock_cp u.u tid
 A N D sch e d_with_f r e q.ts < f r a m e_lock_cp u.ts + f r a m e_lock_cp u.d u r
 A N D f r a m e_lock_cp u.ts < sch e d_with_f r e q.ts + sch e d_with_f r e q.d u r ;
```

这个模式可以回答"这一帧掉帧是因为 C P U 降频、还是因为等锁、还是因为调度延迟"。

> S P A N_J O I N 的 C++ 源码位于 `e xt e rn a l/p e r f etto/src/tr a c e_proc e ssor/` 目录的 op e r a nd 相关文件中。v 53+ 支持 `S P A N_O U T E R_J O I N`。

<!-- A I W-源码调研-2026-05-13 -->

## 交叉引用与分析路径

上面的每个 S Q L 查询都是针对单一维度的分析。在实际工作中，性能问题往往是多因素叠加的——一个 j a nk 帧可能同时涉及 G C 暂停、B ind e r 调用和锁竞争。以下是几种常见的组合分析路径：

**卡顿分析标准流程**：先查 `C hor e ogr a ph e r#do F r a m e` 定位慢帧 → 查该帧期间的 `sch e d` 判断主线程在等什么 → 如果在等锁，查 `monitor cont e ntion` → 如果在等 B ind e r，查 `bind e r_tr a ns a ction` → 如果在等 G C，查 G C 事件和 H e ap 变化。

**A N R 分析标准流程**：定位 A N R 时间点 → 查前后 5 秒的主线程 slic e → 按阻塞原因分类（锁/B ind e r/I O/C P U 抢占）→ 对耗时最大的原因深挖。

**启动速度分析标准流程**：定位启动起止时间（从 `bind A pplic a tion` 到首帧 `do F r a m e`）→ 按阶段分解耗时 → 统计各阶段的 B ind e r 调用和锁等待 → 找到瓶颈阶段后针对性优化。

每条路径中的 S Q L 查询都可以在本章找到对应的模板。建议读者把常用的查询保存为 S Q L 文件，在实际分析时直接加载执行，而不是每次从零开始写。

> 本章 S Q L 基于 P e r f etto v 54.0 源码与当前 P e r f etto stdlib 文档交叉验证，建议在 P e r f etto U I 的 Q u ery 标签页中直接运行。部分查询可能因 T r a c e 配置差异（未开启 sch e d/f tr a c e 等数据源）而无结果，请确保 T r a c e 抓取配置覆盖了分析所需的数据源（参见 §13.2 T r a c e 抓取章节）。
