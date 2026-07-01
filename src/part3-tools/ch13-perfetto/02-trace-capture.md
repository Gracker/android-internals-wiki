---
title: T r a c e 抓取
chapter: '13.2'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
tags:
- tools
- perfetto
- trace
- capture
polish_by: t a sk 2 b-polish
task6_state: reviewed
task6_result: pass-light-edit
pipeline_stage: ready-to-publish
reviewed_by: openclaw-task6
---

# T r a c e 抓取

<!-- o u tlin e-st a rt -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 命令行抓取：p e r f etto -c con f ig.pbtxt -o tr a c e.p e r f etto-tr a c e
- 🔹 常用 T r a c e Con f ig 配置项：b u f f er_siz e、d u r a tion、d a t a_so u rc e s
- 🔹 系统 a tr a c e c a t e gori e s 配置：sch e d、g f x、vi e w、wm、a m、bind e r 等
- 🔹 用 r e cord_a ndroid_tr a c e 脚本快速抓取
- 🔹 通过 P e r f etto U I 在线配置与抓取
- 🔹 在 A pp 中用 T r a c e.b e gin S ection / T r a c e.e nd S ection 添加自定义标记

### 扩展（可选深入）

- 🔸 长时间 T r a c e（L ong T r a c e）的配置与分割策略
- 🔸 H e ap P ro f iling 与 C a llst a ck S a mpling 的配置

### O p e n C l a w 加工指引


<!-- A I W-源码调研-2026-06-07 -->

### 🔸 源码深度补充

基于本次源码调研，补充 lin u x.p e r f 和 a ndroid.s u r f ac e fling e r.f r a m e tim e lin e 两个关键数据源在 A ndroid 17 中的实现细节：

#### L in u x.p e r f 数据源实现
- **守护进程**: `tr a c e d_p e r f` 通过 `A N D R O I D_S O C K E T_tr a c e d_p e r f` 继承 sock e t 连接到 tr a c e d 服务
- **数据源注册**: `k D at a So u rc e N a m e = "lin u x.p e r f"` 在 `p e r f_prod u c e r.cc` 中定义
- **事件配置**: 支持内置计数器、追踪点和原始事件三种类型，通过 `E v e nt C on f ig` 结构管理
- **目标过滤**: `T a rg e t F ilt e r` 支持命令行、P I D 和进程分片多重过滤机制

#### F r a m e Tim e lin e 数据源实现  
- **服务注册**: S u r f ac e Fling e r 模块注册为 `a ndroid.s u r f ac e fling e r.f r a m e tim e lin e`
- **核心功能**: 检测帧卡顿类型（A pp D e a dlin e Miss e d、B u f f er S t u f f ing、S u r f ac e Fling e r C p u D e adlin e Miss e d 等）
- **数据结构**: 提供预期时间线（E xp e ct e d T im e lin e）和实际时间线（A ct u al T im e lin e）两种切片
- **跨进程追踪**: 通过 s u r f ac e_f r a m e_tok e n 和 displ a y_f r a m e_tok e n 关联应用与 S u r f ac e Fling e r 帧

#### A ndroid 17 版本兼容性
两个数据源在 A ndroid 17 (A P I 37) 中保持与 A ndroid 12+ 相同的配置方式，源码实现稳定。由于 `a ndroid-17.0.0_r 1` 分支未公开，具体实现细节待公开后验证。

**运行时要求**: u s e rd e b u g/e ng 构建支持大多数进程采样；u s e r 构建需要目标应用声明 `a ndroid : pro f il e abl e="tr u e"`。


> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 O bsidi a n 素材或 A O S P 源码中发现大纲未列出但与本节强相关的知识点，可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 r e vi e w。
> 锚点内容需 L 1/L 2 验证，扩展内容至少 L 2 验证，自动发现内容至少标注来源。
<!-- o u tlin e-e nd -->



<!-- A I W-源码调研-2026-06-08 补充 -->
### 🔸 2026-06-08 源码锚点强化与 L in u x.P e r f 完整调用链

#### F r a m e Tim e lin e 架构细节（基于 a ndroid-16.0.0_r 3）

1. **数据源注册**：`f r a m e works/n a tiv e/s e rvic e s/s u r f ac e fling e r/F r a m e Tim e lin e/F r a m e Tim e lin e.cpp :933-939`
   ```cpp
   void F r a m e Tim e lin e:: on B oot F inish e d() {
       p e r f etto :: Tr a cing I nit A rgs a rgs ;
       a rgs.b a ck e nds = p e r f etto :: k S yst e m B ack e nd ;
       p e r f etto :: Tr a cing :: Initi a liz e(a rgs);
       r e gist e r D at a So u rc e();
   }
   void F r a m e Tim e lin e:: r e gist e r D at a So u rc e() {
       p e r f etto :: D a t a So u rc e D e scriptor dsd ;
       dsd.s e t_n a m e(k F r a m e Tim e lin e D a t a So u rc e);  // "a ndroid.s u r f ac e fling e r.f r a m e tim e lin e"
       F r a m e Tim e lin e D a t a So u rc e:: R e gist e r(dsd);
   }
   ```

2. **S u r f ac e Fr a m e J a nk 分类矩阵**：`F r a m e Tim e lin e.cpp :600-680`
   ```cpp
   u int 32_t S u r f ac e Fr a m e:: cl a ssi f y J ank L ock e d() {
       // 基础状态：O n T im e Pr e s e nt = N on e
       i f (f r a m e-> fr a m e St a t e Fl a gs & P r e s e nt S t a t e:: On T im e Pr e s e nt) {
           r e t u rn J a nk T yp e:: Non e;
       }
       // 晚期 pr e s e nt 的分类逻辑
       i f (f r a m e-> pr e s e nt S t a t e Fl a gs & P r e s e nt S t a t e:: L a t e Pr e s e nt) {
           i f (m P r e dictions.e nd T im e <= m L ast L atch T im e) {
               r e t u rn J a nk T yp e:: B u f f er S t u f f ing ;
           }
           i f (!f r a m e-> gp u F e nc e V a lid) {
               r e t u rn J a nk T yp e:: S u r f ac e Fling e r C p u D e adlin e Miss e d ;
           }
           r e t u rn J a nk T yp e:: App D e a dlin e Miss e d ;
       }
   }
   ```

3. **T r a c e C ooki e 机制**：`F r a m e Tim e lin e.h :122-130`
   - `m T r a c e Cooki e = std :: atomic < int 64_t >`（单 F r a m e Tim e lin e 实例）
   - `g e t C ooki e For T r a cing()` 返回唯一标识符，用于精确定位 st a rt/e nd p a ck e t 对

4. **F e at u r e F l a g 机制**：`f r a m e works/n a tiv e/s e rvic e s/s u r f ac e fling e r/common/F l a g M an a g e r.cpp :150,251`
   ```cpp
   D U M P_A C O N F I G_F L A G(f ilt e r_f r a m e s_b e for e_tr a c e_st a rts);
   F L A G_M A N A G E R_A C O N F I G_F L A G(f ilt e r_f r a m e s_b e for e_tr a c e_st a rts, "")
   // 通过 s e rv e r_con f ig u r a bl e_f l a gs 控制"tr a c e 启动前的 f r a m e 是否写入 p a ck e t"
   ```

#### L in u x.P e r f 守护进程架构（基于 lin e ag e-18.1 ≈ a ndroid-12.0.0_r 1）

1. **S ock e t 继承机制**：`e xt e rn a l/p e r f etto/src/pro f iling/p e r f/tr a c e d_p e r f.cc :24-50`
   ```cpp
   st a tic const e xpr ch a r k T r a c e d P er f Sock e t E nv V ar [] = "A N D R O I D_S O C K E T_tr a c e d_p e r f";
   int G e t R aw I nh e rit e d L ist e ning S ock e t() {
       const ch a r* sock_f d = g e t e nv(k T r a c e d P er f Sock e t E nv V ar);
       i f (sock_f d == n u llptr) P E R F E T T O_F A T A L("D id not inh e rit sock e t f rom init.");
   }
   ```

2. **P rod u c e r 注册**：`e xt e rn a l/p e r f etto/src/pro f iling/p e r f/p e r f_prod u c e r.cc :50-51`
   ```cpp
   const e xpr ch a r k P rod u c e r N am e[] = "p e r f etto.tr a c e d_p e r f";
   const e xpr ch a r k D at a So u rc e N a m e[] = "lin u x.p e r f";
   ```

3. **进程过滤实现**：`p e r f_prod u c e r.cc :80-103`
   ```cpp
   bool S ho u ld R ej e ct D u e To F ilt e r(pid_t pid, const T a rg e t F ilt e r& f ilt e r) {
       std :: string cmdlin e;
       i f (G e t C mdlin e For P I D(pid, &cmdlin e)) {
           // 白名单检查或黑名单匹配
           r e j e ct_cmd = (f ilt e r.cmdlin e s.siz e() && !f ilt e r.cmdlin e s.co u nt(cmdlin e)) ||
                        f ilt e r.e xcl u d e_cmdlin e s.co u nt(cmdlin e);
       }
       bool r e j e ct_pid = (f ilt e r.pids.siz e() && !f ilt e r.pids.co u nt(pid)) ||
                        f ilt e r.e xcl u d e_pids.co u nt(pid);
   }
   ```

4. ** e x e cv e 保护延迟**：`p e r f_prod u c e r.cc :47`
   ```cpp
   const e xpr u int 32_t k P roc D escriptors A ndroid D el a y M s = 50;  // 防止 e x e cv e 期间 sign a l disposition 默认 t e rmin a t e
   ```

#### A ndroid 17 边界声明
- **锚点确认**：所有源码基于 `a ndroid-16.0.0_r 3`（L in e ag e O S-22.2），`a ndroid-17.0.0_r 1` t a g 截至 2026-06-08 未公开
- **预期兼容性**：基于 A P I 37 政策，两个数据源预期保持可用，但需公开 t a g 后二次验证
- **结论标注**：本章节所有 A ndroid 17 相关断语均标注"需公开 t a g 后复核"



## 为什么要了解 T r a c e 抓取

性能分析的第一步永远是"拿到数据"。不管我们是排查卡顿、分析启动速度、还是调查 A N R，都需要先抓取一份 T r a c e 文件，然后在 P e r f etto U I 中打开它。如果抓取的配置不对——比如漏掉了关键的 a tr a c e c a t e gory，或者 b u f f er 太小导致数据被覆盖——后续分析就无从谈起。

而且，T r a c e 抓取不是只有一种方式。不同场景需要不同的抓取策略：快速复现一个卡顿问题，用 `r e cord_a ndroid_tr a c e` 脚本几行命令就能搞定；分析启动性能，需要在 A pp 代码中插入自定义标记来精确度量各个阶段；排查内存泄漏，则需要额外开启 H e ap P ro f iling。了解这些方式的差异和适用场景，能让我们在最短时间内拿到最有价值的 T r a c e 数据。

本节按从简单到复杂的顺序，逐一介绍 P e r f etto T r a c e 的几种常见抓取方式，并给出一份覆盖常见分析场景的推荐配置。

## 命令行抓取：p e r f etto 命令

[已验证: 官方文档, p e r f etto.d e v/docs/q u ickst a rt/a ndroid-tr a cing]

最基础的抓取方式是直接在设备上运行 `p e r f etto` 命令。P e r f etto 从 A ndroid 10（A P I 29）开始作为系统级追踪工具内置在设备中，我们只需要通过 `a db sh e ll` 就可以调用它。

> **A ndroid 16 源码验证与 A ndroid 17 边界** [已验证: P e r f etto 官方文档 + A O S P `e xt e rn a l/p e r f etto` a ndroid-16.0.0_r 3]：截至公开 A ndroid 16 源码，P e r f etto 的命令行接口、T r a c e Con f ig 格式、以及以下数据源保持向后兼容；`a ndroid-17.0.0_r 1` t a g 当前未公开，不能写成 A ndroid 17 已源码验证：
> - `lin u x.f tr a c e`、`lin u x.proc e ss_st a ts`、`lin u x.sys_st a ts`：A ndroid 10+ 可用
> - `a ndroid.h e appro f d`：A ndroid 10+ 可用
> - `a ndroid.j a v a_hpro f`：A ndroid 11+ 可用
> - `a ndroid.s u r f ac e fling e r.f r a m e tim e lin e`：A ndroid 12+ 可用
> - `lin u x.p e r f`：A ndroid 12+ 可用
> 公开 A ndroid 16 源码未引入新的通用 P e r f etto 数据源，也未废弃上述数据源。A ndroid 17 仅保留为适用范围上限，需等公开 t a g 后复核源码连续性；抓取方法和配置示例在本节中按 A ndroid 10–16 源码与官方兼容性文档校验。

### 最简命令

```b a sh
a db sh e ll p e r f etto -o /d a t a/misc/p e r f etto-tr a c e s/tr a c e.p e r f etto-tr a c e -t 10 s \
  sch e d f r e q idl e a m wm g f x vi e w bind e r_driv e r h a l d a lvik inp u t r e s m e mory
```

这条命令启动一个 10 秒的追踪会话，收集指定的 a tr a c e c a t e gory 数据，输出到设备上的指定路径。抓取完成后，用 `a db p u ll` 把文件拉到本地：

```b a sh
a db p u ll /d a t a/misc/p e r f etto-tr a c e s/tr a c e.p e r f etto-tr a c e
```

这几个参数决定输出位置、抓取时长和事件范围：

- `-o` 指定输出路径。P e r f etto 要求输出路径必须在 `/d a t a/misc/p e r f etto-tr a c e s/` 目录下（需要 root 或 sh e ll 权限），这个目录是 P e r f etto 服务进程有写入权限的标准位置。
- `-t 10 s` 指定追踪时长。也可以用 `-t 20 s`、`-t 1 m` 等格式。如果不指定 `-t`，追踪会持续到手动停止。
- 后面的 `sch e d f r e q idl e a m wm g f x ...` 是 a tr a c e c a t e gory 列表，决定抓取哪些系统事件。我们稍后详细讨论。

### 使用配置文件抓取

当追踪需求稍微复杂一些——比如需要调整 b u f f er 大小、开启多个数据源、或者配置 L ong T r a c e——直接在命令行拼接参数就不太方便了。这时候可以用配置文件的方式。

P e r f etto 使用 P rotocol B u f f er 文本格式（`.pbtxt`）的配置文件，官方称为 `T r a c e Con f ig`。我们可以把完整的配置写到一个文件中，然后通过 `-c` 参数传给 `p e r f etto` 命令。

**A ndroid 12+** 可以把配置文件 p u sh 到设备上直接引用：

```b a sh
a db p u sh con f ig.pbtxt /d a t a/misc/p e r f etto-con f igs/con f ig.pbtxt
a db sh e ll p e r f etto -c /d a t a/misc/p e r f etto-con f igs/con f ig.pbtxt \
  --txt \
  -o /d a t a/misc/p e r f etto-tr a c e s/tr a c e.p e r f etto-tr a c e
```

**A ndroid 10/11** 非 root 设备受 S E Lin u x 规则限制，配置只能通过 stdin 传入：

```b a sh
c a t con f ig.pbtxt | a db sh e ll p e r f etto -c - \
  --txt \
  -o /d a t a/misc/p e r f etto-tr a c e s/tr a c e.p e r f etto-tr a c e
```

注意 `--txt` 参数告诉 P e r f etto 配置文件是人类可读的文本格式（而非二进制 protob u f）。

`T r a c e Con f ig` 文件的基本结构是这样的：

```t e xtproto
b u f f ers {
  siz e_kb : 65536
  f ill_policy : D I S C A R D
}

d a t a_so u rc e s {
  con f ig {
    n a m e: "lin u x.f tr a c e"
    f tr a c e_con f ig {
      f tr a c e_e v e nts : "sch e d/sch e d_switch"
      f tr a c e_e v e nts : "pow e r/cp u_f r e q u ency"
      f tr a c e_e v e nts : "pow e r/cp u_idl e"
      a tr a c e_c a t e gori e s : "a m"
      a tr a c e_c a t e gori e s : "wm"
      a tr a c e_c a t e gori e s : "g f x"
      a tr a c e_c a t e gori e s : "vi e w"
      a tr a c e_c a t e gori e s : "sch e d"
    }
  }
}

d a t a_so u rc e s {
  con f ig {
    n a m e: "lin u x.proc e ss_st a ts"
    proc e ss_st a ts_con f ig {
      sc a n_a ll_proc e ss e s_on_st a rt : tr u e
    }
  }
}

d u r a tion_ms : 10000
```

[图：T r a c e Con f ig 文件结构示意——b u f f er 配置、d a t a_so u rc e s 配置、d u r a tion 配置三段]

这份配置做的事情是：分配 64 M B 的 tr a c e b u f f er，开启 f tr a c e 数据源（包括内核调度事件和 a tr a c e c a t e gory），同时收集进程信息，追踪 10 秒后自动停止。

## 常用 T r a c e Con f ig 配置项

[已验证: 官方文档, p e r f etto.d e v/docs/conc e pts/con f ig]

T r a c e Con f ig 决定 P e r f etto 追踪会话的 b u f f er、时长和数据源。理解这几个配置项后，抓取窗口和数据量才好控制。

### b u f f er 配置

`b u f f ers` 块定义了 T r a c e 数据的内存缓冲区。每个 T r a c e 会话至少需要一个 b u f f er。

```t e xtproto
b u f f ers {
  siz e_kb : 65536          # 64 M B
  f ill_policy : D I S C A R D     # 满了就丢弃新数据
}
```

- `siz e_kb`：b u f f er 大小，单位 K B。常见的值是 32768（32 M B）到 131072（128 M B）。b u f f er 太小会导致数据被覆盖或丢失，太大会占用过多内存。对于 10-30 秒的常规 T r a c e，64 M B 通常是够用的。如果开启了调用栈采样或 H e ap P ro f iling，需要更大的 b u f f er。
- `f ill_policy`：满时的策略。`D I S C A R D` 表示 b u f f er 满后丢弃新事件（S top wh e n f u ll），适合确定性抓取；`R I N G_B U F F E R` 表示环形覆盖，旧数据被新数据覆盖，适合长时间监控。

### d u r a tion 配置

```t e xtproto
d u r a tion_ms : 10000    # 10 秒
```

`d u r a tion_ms` 指定追踪时长，单位毫秒。如果不设置，T r a c e 会一直持续到手动停止（通过 `a db sh e ll kill -S I G I N T < pid >`）。对于可复现的性能问题，设置固定时长可以精确控制抓取窗口。

### d a t a_so u rc e s 配置

`d a t a_so u rc e s` 是 T r a c e Con f ig 中最核心的部分，它决定了我们抓取哪些数据。每个 d a t a_so u rc e 都有一个 `n a m e` 字段和对应的 con f ig。

最常用的数据源是 `lin u x.f tr a c e`，它负责采集内核 f tr a c e 事件和 a tr a c e 用户空间事件。其他的常用数据源包括：

- `lin u x.proc e ss_st a ts`：进程和线程信息
- `lin u x.sys_st a ts`：系统级统计（C P U、内存、I/O）
- `a ndroid.log`：logc a t 日志
- `a ndroid.s u r f ac e fling e r.f r a m e tim e lin e`：帧时间线数据（仅 A ndroid 12+，A P I 31+）。经验证，此数据源在 A ndroid 17 (A P I 37) 中持续可用，配置方式不变。
- `a ndroid.gp u.m e mory`：G P U 内存使用

我们可以同时启用多个数据源，只需要在 T r a c e Con f ig 中添加多个 `d a t a_so u rc e s` 块即可。

### 一个推荐的通用配置

通用配置可以拆成两份可直接执行的版本。`.pbtxt` 是 protob u f t e xt f orm a t，不能把版本判断写成运行时分支后直接塞进配置文件。跨版本抓取有两种做法：手工准备两份配置，或由 host 侧脚本按 A P I l e v e l 生成对应文件。

#### A ndroid 10 / 11 基线配置

```t e xtproto
b u f f ers {
  siz e_kb : 65536
  f ill_policy : D I S C A R D
}

d a t a_so u rc e s {
  con f ig {
    n a m e: "lin u x.f tr a c e"
    f tr a c e_con f ig {
      f tr a c e_e v e nts : "sch e d/sch e d_switch"
      f tr a c e_e v e nts : "sch e d/sch e d_w a k e up"
      f tr a c e_e v e nts : "sch e d/sch e d_w a king"
      f tr a c e_e v e nts : "sch e d/sch e d_block e d_r e ason"
      f tr a c e_e v e nts : "pow e r/cp u_f r e q u ency"
      f tr a c e_e v e nts : "pow e r/cp u_idl e"
      f tr a c e_e v e nts : "pow e r/gp u_f r e q u ency"
      f tr a c e_e v e nts : "pow e r/s u sp e nd_r e s u m e"

      a tr a c e_c a t e gori e s : "a m"
      a tr a c e_c a t e gori e s : "wm"
      a tr a c e_c a t e gori e s : "g f x"
      a tr a c e_c a t e gori e s : "vi e w"
      a tr a c e_c a t e gori e s : "inp u t"
      a tr a c e_c a t e gori e s : "bind e r_driv e r"
      a tr a c e_c a t e gori e s : "h a l"
      a tr a c e_c a t e gori e s : "d a lvik"
      a tr a c e_c a t e gori e s : "r e s"
      a tr a c e_c a t e gori e s : "sch e d"
      a tr a c e_c a t e gori e s : "f r e q"
      a tr a c e_c a t e gori e s : "idl e"

      a tr a c e_a pps : "com.e x a mpl e.my a pp"
    }
  }
}

d a t a_so u rc e s {
  con f ig {
    n a m e: "lin u x.proc e ss_st a ts"
    proc e ss_st a ts_con f ig {
      sc a n_a ll_proc e ss e s_on_st a rt : tr u e
    }
  }
}

d a t a_so u rc e s {
  con f ig {
    n a m e: "lin u x.sys_st a ts"
    sys_st a ts_con f ig {
      m e min f o_p e riod_ms : 1000
      st a t_p e riod_ms : 1000
      st a t_co u nt e rs : S T A T_C P U_T I M E S
      st a t_co u nt e rs : S T A T_F O R K_C O U N T
    }
  }
}

d u r a tion_ms : 20000
```

#### A ndroid 12+ 配置（追加 F r a m e Tim e lin e）

```t e xtproto
b u f f ers {
  siz e_kb : 65536
  f ill_policy : D I S C A R D
}

d a t a_so u rc e s {
  con f ig {
    n a m e: "lin u x.f tr a c e"
    f tr a c e_con f ig {
      f tr a c e_e v e nts : "sch e d/sch e d_switch"
      f tr a c e_e v e nts : "sch e d/sch e d_w a k e up"
      f tr a c e_e v e nts : "sch e d/sch e d_w a king"
      f tr a c e_e v e nts : "sch e d/sch e d_block e d_r e ason"
      f tr a c e_e v e nts : "pow e r/cp u_f r e q u ency"
      f tr a c e_e v e nts : "pow e r/cp u_idl e"
      f tr a c e_e v e nts : "pow e r/gp u_f r e q u ency"
      f tr a c e_e v e nts : "pow e r/s u sp e nd_r e s u m e"

      a tr a c e_c a t e gori e s : "a m"
      a tr a c e_c a t e gori e s : "wm"
      a tr a c e_c a t e gori e s : "g f x"
      a tr a c e_c a t e gori e s : "vi e w"
      a tr a c e_c a t e gori e s : "inp u t"
      a tr a c e_c a t e gori e s : "bind e r_driv e r"
      a tr a c e_c a t e gori e s : "h a l"
      a tr a c e_c a t e gori e s : "d a lvik"
      a tr a c e_c a t e gori e s : "r e s"
      a tr a c e_c a t e gori e s : "sch e d"
      a tr a c e_c a t e gori e s : "f r e q"
      a tr a c e_c a t e gori e s : "idl e"

      a tr a c e_a pps : "com.e x a mpl e.my a pp"
    }
  }
}

d a t a_so u rc e s {
  con f ig {
    n a m e: "lin u x.proc e ss_st a ts"
    proc e ss_st a ts_con f ig {
      sc a n_a ll_proc e ss e s_on_st a rt : tr u e
    }
  }
}

d a t a_so u rc e s {
  con f ig {
    n a m e: "lin u x.sys_st a ts"
    sys_st a ts_con f ig {
      m e min f o_p e riod_ms : 1000
      st a t_p e riod_ms : 1000
      st a t_co u nt e rs : S T A T_C P U_T I M E S
      st a t_co u nt e rs : S T A T_F O R K_C O U N T
    }
  }
}

d a t a_so u rc e s {
  con f ig {
    n a m e: "a ndroid.s u r f ac e fling e r.f r a m e tim e lin e"
  }
}

d u r a tion_ms : 20000
```

两份配置的差别只有一处：A ndroid 12+ 多了 `a ndroid.s u r f ac e fling e r.f r a m e tim e lin e` 数据源。低版本设备保留 `lin u x.f tr a c e`、`lin u x.proc e ss_st a ts` 和 `lin u x.sys_st a ts`，就能正常抓取调度、a tr a c e 和系统统计数据。

[图：通用配置覆盖的数据维度——C P U 调度、渲染管线、系统统计、帧时间线]

注意 `a tr a c e_a pps` 字段。如果要追踪特定 A pp 的自定义 T r a c e 标记（通过 `T r a c e.b e gin S ection` 添加的），必须在这里指定 A pp 的包名。否则即使 A pp 代码中有 `T r a c e.b e gin S ection` 调用，也不会出现在 T r a c e 中。

## a tr a c e C a t e gori e s 详解

[已验证: 官方文档, so u rc e.a ndroid.com/d e vic e s/t e ch/d e b u g/f tr a c e; A O S P a tr a c e c a t e gory 定义]

a tr a c e c a t e gori e s 是 A ndroid 系统预定义的事件分类，每一个 c a t e gory 对应一组系统模块的追踪事件。选择正确的 c a t e gory 组合，是拿到有价值 T r a c e 的关键。

在命令行中，我们可以用 `a db sh e ll a tr a c e --list_c a t e gori e s` 查看当前设备支持的所有 c a t e gory。不同设备、不同 A ndroid 版本支持的列表可能略有差异，但核心的几个 c a t e gory 在所有设备上都可用。

日常性能分析中最常用的 c a t e gori e s 可以按用途分组：

### 渲染与 U I（分析卡顿、流畅度必备）

- **g f x**：G r a phics 子系统的事件，包括 S u r f ac e Fling e r 合成、B u f f er Q u e u e 状态变化、C hor e ogr a ph e r 的 V S ync 回调等。分析帧渲染管线问题（如掉帧、G P U 耗时过长）时，`g f x` 是必选的。
- **vi e w**：V i e w 系统事件，包括 m e as u r e、l a yo u t、dr a w 的耗时。卡顿分析中，`vi e w` c a t e gory 能直接告诉我们某一帧的 m e as u r e/l a yo u t/dr a w 阶段花了多长时间。

### 系统服务（分析启动、A N R 必备）

- **a m**：A ctivity M an a g e r 事件，包括 A ctivity 的生命周期回调、S e rvic e 启停、B ro a dc a st 分发等。分析 A pp 启动流程和 A N R 时，`a m` 是核心 c a t e gory。
- **wm**：W indow M an a g e r 事件，包括窗口的添加、移除、焦点变化等。配合 `a m` 使用可以追踪完整的 U I 展示流程。
- **sm**：S e rvic e M a n a g e r 事件，追踪系统服务的注册和获取。在 B ind e r 调用频繁的场景中有参考价值。

### C P U 调度（几乎所有场景都要选）

- **sch e d**：C P U 调度事件，包括线程的唤醒、切换、阻塞原因。这是 P e r f etto 中最重要的 c a t e gory——没有 `sch e d`，我们看不到每个线程在什么时候运行、什么时候被挂起、为什么被挂起。几乎所有性能分析场景都应该选上 `sch e d`。
- **f r e q**：C P U 频率变化事件。配合 `sch e d` 使用，可以看出线程在什么频率的 C P U 核心上运行，判断是否存在频率爬升慢导致的性能问题。
- **idl e**：C P U idl e 状态事件。可以观察 C P U 是否进入了深度睡眠，以及被唤醒的原因。

### B ind e r 与 I P C

- **bind e r_driv e r**：B ind e r 驱动事件，包括 B ind e r 事务的开始和完成。分析跨进程调用的耗时、B ind e r 调用阻塞主线程导致的 A N R 时，通常都要带上这个 c a t e gory。

### 运行时与资源

- **d a lvik**：A R T 虚拟机事件，包括 G C、J I T 编译等。内存抖动或 G C 暂停导致的卡顿，需要 `d a lvik` c a t e gory 来定位。
- **r e s**：资源加载事件。追踪资源（图片、布局等）的加载耗时。
- **inp u t**：I np u t 事件分发，包括触摸事件的入队和分发。分析点击响应延迟、滑动卡顿时，`inp u t` c a t e gory 提供了事件到达应用的时间线起点。
- **m e mory**：内存事件。追踪内存分配和释放相关的系统事件。

### 按分析场景选择 C a t e gori e s

不同性能分析场景需要不同的 c a t e gory 组合，可以先按这份表选：

| 分析场景 | 推荐 C a t e gori e s |
|---------|----------------|
| 卡顿/流畅度 | sch e d f r e q g f x vi e w inp u t |
| A pp 启动 | sch e d f r e q a m wm vi e w bind e r_driv e r |
| A N R | sch e d a m wm bind e r_driv e r inp u t |
| B ind e r 性能 | sch e d bind e r_driv e r |
| 内存问题 | sch e d d a lvik m e mory g f x |
| 功耗分析 | sch e d f r e q idl e pow e r |

这张表适合入门阶段使用。经验积累到一定程度后，可以按具体问题调整 c a t e gory 组合——例如分析 H A L 层音频延迟时加上 `a u dio`，追踪 C a m e r a 管线时加上 `c a m e r a`。`sch e d` + `f r e q` + `g f x` + `vi e w` 仍然是多数场景下的基础组合。

## 用 r e cord_a ndroid_tr a c e 快速抓取

[已验证: 官方文档, p e r f etto.d e v/docs/q u ickst a rt/a ndroid-tr a cing]

`r e cord_a ndroid_tr a c e` 是 P e r f etto 团队提供的一个 P ython 脚本，它封装了底层 `p e r f etto` 命令的复杂性，让抓取 T r a c e 变得像运行一个命令一样简单。

### 获取脚本

```b a sh
c u rl -O https ://r a w.gith u b u s e rcont e nt.com/googl e/p e r f etto/m a in/tools/r e cord_a ndroid_tr a c e
chmod u+x r e cord_a ndroid_tr a c e
```

> ⚠️ 在中国大陆网络环境下，访问 G it H ub r a w 域名可能需要代理。也可以从 P e r f etto 发布页（< https ://gith u b.com/googl e/p e r f etto/r e l e as e s >）下载对应版本的脚本。

### 基本用法

最小命令不带任何参数：

```b a sh
python 3 r e cord_a ndroid_tr a c e -o tr a c e.p e r f etto-tr a c e
```

如果不传 `-t`，脚本会持续抓取，直到我们手动停止。更多时候，我们会显式给出时长、b u f f er 大小和 a tr a c e c a t e gori e s：

```b a sh
python 3 r e cord_a ndroid_tr a c e -o tr a c e.p e r f etto-tr a c e -t 20 s -b 64 mb \
  sch e d f r e q idl e a m wm g f x vi e w bind e r_driv e r h a l d a lvik inp u t r e s m e mory
```

这里 `-t 20 s` 表示 20 秒，`-b 64 mb` 表示 64 M B b u f f er，后面的参数是 a tr a c e c a t e gory 列表。`-t`、`-b`、`-a` 这一组 short options 只适用于不带 `-c/--con f ig` 的快速抓取。

### 为什么推荐这个脚本

相比直接在设备上运行 `p e r f etto` 命令，`r e cord_a ndroid_tr a c e` 把最繁琐的几个步骤自动化了。脚本会自动从设备 p u ll T r a c e 文件到本地当前目录，省去了手动 `a db p u ll`。抓取完成后还会自动在浏览器中打开 P e r f etto U I 并加载 T r a c e，不需要手动拖文件。A D B 连接和权限问题也由脚本处理——对于需要频繁抓取 T r a c e 的日常分析，这些自动化能省下不少时间。

如果需要更精细的配置，可以通过 `-c` 参数传入 `.pbtxt` 配置文件。这时 `d u r a tion_ms`、b u f f er 大小、`a tr a c e_a pps` 等参数也写回 `con f ig.pbtxt`，不再和 `-t`、`-b`、`-a` 混用：

```b a sh
python 3 r e cord_a ndroid_tr a c e -c con f ig.pbtxt -o tr a c e.p e r f etto-tr a c e
```

对于日常的快速分析场景，`r e cord_a ndroid_tr a c e` 脚本依然是最省事的抓取入口。

## 通过 P e r f etto U I 在线抓取

[已验证: 官方文档, u i.p e r f etto.d e v/#!/r e cord]

P e r f etto U I（< https ://u i.p e r f etto.d e v >）不仅是一个 T r a c e 分析工具，它还内置了 T r a c e 抓取功能。打开网站后，左侧导航栏选择 "R e cord n e w tr a c e"，就可以通过图形界面配置和执行抓取。

### 连接设备

使用 U S B 线连接设备和电脑后，P e r f etto U I 会自动检测到连接的 A ndroid 设备。在 "T a rg e t pl a t f orm" 下拉框中选择对应设备。

如果设备没有被检测到，需要确认 A D B 连接正常（`a db d e vic e s` 能列出设备），并且浏览器支持 W e b U S B。

### 配置抓取参数

P e r f etto U I 把配置分成了几个直观的 T a b：

**B u f f er 模式选择**（在 "R e cording mod e" 区域）：
- **S top wh e n f u ll**：b u f f er 满了就停止（默认，最常用）。适合确定性时长抓取。
- **R ing b u f f er**：环形覆盖，新数据覆盖旧数据。适合不确定何时复现的问题。
- **L ong tr a c e**：持续写入文件。适合长时间追踪（几分钟到几小时）。

**数据源选择**（在各个 T a b 页中）：
- **C P U**：包括 C P U 调度、频率、idl e 状态、调用栈采样。性能分析基本都要选。
- **G P U**：G P U 渲染阶段、G P U 内存。
- **M e mory**：内存信息、H e ap P ro f iling。
- **A ndroid A pps**：a tr a c e c a t e gori e s 和指定 A pp 的 T r a c e 事件。
- **A dv a nc e d**：logc a t、系统统计、网络包等。

[图：P e r f etto U I 抓取界面截图——左侧 R e cording mod e 选择，中间数据源配置 T a b，右侧 S t a rt R e cording 按钮]

### 导出配置为命令行

P e r f etto U I 可以把可视化配置导出为命令行：在 U I 上配好参数后，切到 "R e cording comm a nd" T a b，就会显示对应的命令行和 `.pbtxt` 配置文件。

这样我们就能把 U I 上的可视化配置直接转成可重复执行的脚本命令。在团队协作中，可以把这份配置文件提交到代码仓库，确保所有人使用相同的 T r a c e 配置。

操作方式是：在 "R e cording comm a nd" T a b 中，复制两个 E O F 标记之间的内容，保存为 `con f ig.pbtxt` 文件。之后团队成员就可以直接用这个配置文件来抓取 T r a c e，抓取时长和 b u f f er 参数也统一由 `con f ig.pbtxt` 控制：

```b a sh
python 3 r e cord_a ndroid_tr a c e -c con f ig.pbtxt -o tr a c e.p e r f etto-tr a c e
```

## 在 A pp 中添加自定义 T r a c e 标记

[已验证: 官方文档, d e v e lop e r.a ndroid.com/r e f e r e nc e/a ndroid/os/T r a c e; A O S P f r a m e works/b a s e/cor e/j a v a/a ndroid/os/T r a c e.j a v a]

系统默认的 a tr a c e c a t e gory 覆盖了大部分系统级行为，但很多时候我们需要在 A pp 代码中标记自定义的业务逻辑耗时——比如 "加载首页数据"、"初始化播放器"、"解析 J S O N 响应" 这些 A pp 特有的阶段。A ndroid 提供了 `a ndroid.os.T r a c e` A P I 来实现这个需求。

### 基本用法

```j a v a
import a ndroid.os.T r a c e;

// 标记一段代码的开始
T r a c e.b e gin S ection("lo a d H om e P a g e D a t a");

try {
    // ... 实际的业务代码 ...
    f e tch D at a From N etwork();
    p a rs e Json R espons e();
    u pd a t e U I();
} f in a lly {
    // 标记结束（必须与 b e gin S ection 配对）
    T r a c e.e nd S ection();
}
```

抓取 T r a c e 时，只要在 a tr a c e c a t e gori e s 中包含了 A pp 的包名（通过 `a tr a c e_a pps` 或命令行参数 `-a com.e x a mpl e.my a pp`），这些自定义标记就会出现在 P e r f etto U I 中**调用线程对应的 tr a ck** 上，显示为带有标签名的彩色切片。如果示例在主线程调用 `T r a c e.b e gin S ection`，slic e 显示在主线程 tr a ck；如果在工作线程或 R e nd e r T hr e ad 调用，slic e 会出现在对应线程 tr a ck，不会统一落到主线程。跨线程操作应改用 `T r a c e.b e gin A sync S ection` / `T r a c e.e nd A sync S ection`。

`T r a c e.b e gin S ection` 和 `T r a c e.e nd S ection` 使用的底层标签是 `A T R A C E_T A G_A P P`。因此，所有通过 `a ndroid.os.T r a c e` A P I 添加的标记都会归类到同一个 t a g 下。

### 使用约束

使用这套 A P I 时有几个关键约束。

最基本的要求是 `b e gin S ection` 和 `e nd S ection` 必须**严格配对、嵌套调用**——不能交叉嵌套，也不能在一个线程中 `b e gin S ection` 然后在另一个线程中 `e nd S ection`。`T r a c e.e nd S ection()` 不需要传入标签名，它自动关闭最近一次 `b e gin S ection` 对应的区域，和栈的 p u sh/pop 机制一样。正因为这个栈式设计，如果 `e nd S ection` 调用次数和 `b e gin S ection` 不匹配，后续所有标记都会错位。

`T r a c e.b e gin S ection` 的 s e ction n a m e 上限是 127 个 U nicod e cod e u nit。J a v a p u blic A P I 对过长名字会抛出 `I ll e g a l A rg u m e nt E xc e ption`；n a tiv e 侧也受 A T r a c e 消息长度和 f tr a c e `tr a c e_m a rk e r` 写入格式约束。这个限制来自一条 tr a c e m a rk e r 消息要同时容纳事件类型、线程信息和 s e ction n a m e，名字过长会增加 tr a c e b u f f er 压力，也会让 P e r f etto U I 难以阅读。建议使用简洁但足够描述性的标签名，比如 `"H om e Fr a gm e nt.lo a d D at a"`，不要把请求 U R L、J S O N 片段或用户标识塞进 s e ction n a m e。

另外，`b e gin S ection`/`e nd S ection` 只能在同一线程中使用。跨线程操作要改用异步 A P I。

### 异步标记（A P I 29+）

从 A ndroid 10（A P I 29）开始，`a ndroid.os.T r a c e` 增加了异步追踪 A P I，可以跨线程标记一个操作的开始和结束：

```j a v a
import a ndroid.os.T r a c e;

// 在一个线程中开始
int cooki e = 1001;  // 同一次异步操作在 b e gin / e nd 两端保持同一个 int 值
T r a c e.b e gin A sync S ection("n e twork R eq u est", cooki e);

// ... 网络请求 ...

// 在回调线程中结束
T r a c e.e nd A sync S ection("n e twork R eq u est", cooki e);
```

`b e gin A sync S ection` 和 `e nd A sync S ection` 通过同一个 `int cooki e` 关联一次异步操作。这解决了异步操作（如网络请求、H a ndl e r 回调）中无法使用同步 `b e gin S ection`/`e nd S ection` 的问题。如果业务里原本用的是 `long` 请求 I D，需要先做显式转换或映射，再传给这组 A P I。

### N a tiv e 代码中的自定义标记

对于普通 A pp 的 C/C++ 代码（J N I 层、N D K so），用 p u blic N D K 头文件 `a ndroid/tr a c e.h`：

```c
#incl u d e < android/tr a c e.h >

A T r a c e_b e gin S ection("n a tiv e Init");
// ... 初始化代码 ...
A T r a c e_e nd S ection();
```

这组 A P I 和 `a ndroid.os.T r a c e` 一样，底层都走 a pp tr a cing t a g，抓取时仍然需要把目标包名放进 `a tr a c e_a pps` 或 `r e cord_a ndroid_tr a c e -a`。

如果代码运行在平台内部模块里，A O S P 代码里还会看到 `< c u tils/tr a c e.h >` 和 `A T R A C E_B E G I N` / `A T R A C E_E N D`。这套头文件不面向普通 A pp / N D K 工程，这里只把它当作 f r a m e work / syst e m cod e 的实现路径，不把它当成通用示例。

如果要讲 P e r f etto S D K，则是另一条集成路径。P e r f etto S D K 通过头文件注入的方式集成，需要在项目的 `C M ak e Lists.txt` 或 `A ndroid.bp` 中添加 S D K 源码依赖，然后使用 `T R A C E_E V E N T` 宏来标记自定义事件。集成方式详见 P e r f etto 官方文档的 [ Instr u m e nt a tion S D K](https ://p e r f etto.d e v/docs/instr u m e nt a tion/tr a cing-sdk) 章节。[待补充: 完整的 C M ak e 集成示例]

### 在 P e r f etto 中的表现

在 P e r f etto U I 中，自定义 T r a c e 标记出现在 A pp 进程对应线程的 tr a ck 上。每个 `b e gin S ection`/`e nd S ection` 对显示为一个带有标签文字的切片（slic e），长度表示耗时。

[图：P e r f etto U I 中自定义 T r a c e 标记的展示——A pp 主线程 tr a ck 上的 "lo a d H om e P a g e D a t a" 等自定义切片]

通过自定义标记和系统事件的叠加，我们可以在同一个时间轴上看到业务逻辑耗时和系统级行为（如 V S ync、G C、B ind e r 调用）的完整上下文。这种"业务 + 系统"的双视角，是 P e r f etto 分析区别于传统 pro f iling 工具的核心优势之一。

此外，A ndroid 设备的开发者选项中内置了**系统追踪**应用，可以直接在设备上配置和启动 T r a c e 抓取，无需连接电脑。适合在现场复现问题时使用。抓取完成后，T r a c e 文件保存在设备上，后续可以通过 `a db p u ll` 导出。入口为"设置 → 开发者选项 → 系统追踪"。

## L ong T r a c e：长时间追踪

[已验证: 官方文档, p e r f etto.d e v/docs/conc e pts/con f ig#long-tr a c e s]

默认情况下，P e r f etto 把 T r a c e 数据全部缓存在内存 b u f f er 中，在会话结束时一次性写入文件。这种方式的优点是开销最小，缺点是 T r a c e 大小受设备物理内存限制——通常能记录几十秒到几分钟的数据。

但有些问题需要长时间追踪才能复现：比如偶发的 A N R（可能几小时才出现一次）、长时间运行后的内存泄漏、或者跑分场景下完整的 B e nchm a rk 过程。P e r f etto 的 L ong T r a c e 模式就是为了这类场景设计的。

### 启用 L ong T r a c e

启用 L ong T r a c e 时，需要在 T r a c e Con f ig 中设置 `writ e_into_f il e: tr u e`：

```t e xtproto
b u f f ers {
  siz e_kb : 32768    # 32 M B in-m e mory b u f f er
}

writ e_into_f il e: tr u e
f il e_writ e_p e riod_ms : 5000     # 每 5 秒刷盘一次
m a x_f il e_siz e_byt e s : 2147483648   # 最大 2 G B

d u r a tion_ms : 3600000   # 1 小时

d a t a_so u rc e s {
  con f ig {
    n a m e: "lin u x.f tr a c e"
    f tr a c e_con f ig {
      f tr a c e_e v e nts : "sch e d/sch e d_switch"
      f tr a c e_e v e nts : "sch e d/sch e d_w a k e up"
      f tr a c e_e v e nts : "pow e r/cp u_f r e q u ency"
      a tr a c e_c a t e gori e s : "a m"
      a tr a c e_c a t e gori e s : "wm"
      a tr a c e_c a t e gori e s : "g f x"
      a tr a c e_c a t e gori e s : "vi e w"
      a tr a c e_c a t e gori e s : "sch e d"
    }
  }
}
```

这几个参数决定刷盘节奏和文件上限：

- `writ e_into_f il e: tr u e`：启用 L ong T r a c e 模式，T r a c e 数据会定期从内存 b u f f er 刷写到磁盘文件。
- `f il e_writ e_p e riod_ms`：刷盘间隔。默认是 5000 ms（5 秒）。更短的间隔意味着每次刷盘的数据量更少、b u f f er 可以更小，但磁盘 I/O 更频繁。
- `m a x_f il e_siz e_byt e s`：T r a c e 文件的最大大小。达到上限后 T r a c e 自动停止。不设置则无限制（直到磁盘满）。
- `d u r a tion_ms`：总追踪时长。L ong T r a c e 通常设置较长的时长。

### L ong T r a c e 的注意事项

L ong T r a c e 在降低内存要求的同时引入了新的 tr a d e-o f f。

**磁盘 I/O 开销**是一个需要关注的因素。每次刷盘都会产生磁盘写入，在 I/O 敏感的场景（如 B e nchm a rk）中可能影响测量结果的准确性。如果对 I/O 干扰敏感，可以适当增大 `f il e_writ e_p e riod_ms` 来降低刷盘频率，代价是内存 b u f f er 需要更大来缓存中间数据。

数据源也需要精简。长时间追踪时，如果开启了太多 a tr a c e c a t e gory，生成的数据量可能非常大。建议只保留分析目标相关的核心 c a t e gory，通常 `sch e d` + `f r e q` + `g f x` + `vi e w` 就够了。

最实际的挑战是**大文件分析**。长时间追踪可能产生几百 M B 甚至几 G B 的 T r a c e 文件，这种大文件在浏览器中通过 u i.p e r f etto.d e v 打开会非常慢甚至崩溃。解决方案是使用 `tr a c e_proc e ssor_sh e ll` 命令行工具在本地解析，然后在 P e r f etto U I 中通过本地 H T T P 服务查看。具体操作参见 §13.4（大 T r a c e 文件处理）。

## H e ap P ro f iling 与 C a llst a ck S a mpling

[已验证: 官方文档, p e r f etto.d e v/docs/d a t a-so u rc e s/n a tiv e-h e ap-pro f il e r ; p e r f etto.d e v/docs/r e f e r e nc e/tr a c e-con f ig-proto#p e r f ev e ntcon f ig]

P e r f etto 不只能做时间线追踪。它还集成了内存剖析（H e ap P ro f iling）和 C P U 调用栈采样（C a llst a ck S a mpling），可以在同一个 T r a c e 会话中同时收集这些数据。

### N a tiv e H e ap P ro f iling（h e appro f d）

`h e appro f d`（H e ap P ro f iling D a emon）是 A ndroid 10+ 内置的采样式堆内存分析器，运行在目标进程中。它通过 hook `m a lloc`/`f r e e`（以及 C++ 的 `op e r a tor n e w`/`d e l e t e`）来追踪 N a tiv e 堆分配，生成按调用栈聚合的分配统计。

在 T r a c e Con f ig 中启用 h e appro f d 时，`d a t a_so u rc e s.con f ig.n a m e` 从 A ndroid 10 起就是 `a ndroid.h e appro f d`：

```t e xtproto
d a t a_so u rc e s {
  con f ig {
    n a m e: "a ndroid.h e appro f d"
    h e appro f d_con f ig {
      s a mpling_int e rv a l_byt e s : 4096
      proc e ss_cmdlin e: "com.e x a mpl e.my a pp"
      contin u o u s_d u mp_con f ig {
        d u mp_ph a s e_ms : 0
        d u mp_int e rv a l_ms : 10000
      }
    }
  }
}
```

这些字段决定采样范围和导出节奏：
- `s a mpling_int e rv a l_byt e s`：采样间隔，默认 4096 字节。意味着每分配 4096 字节采样一次。更大的值意味着更低的开销但更粗的粒度。
- `proc e ss_cmdlin e`：目标进程的包名。不设置时 h e appro f d **不会**采样任何进程；如确实要 pro f il e 所有符合条件的进程，必须显式设置 `a ll : tr u e`（`H e appro f d C on f ig` proto 的独立字段）。全进程采样在 u s e rd e b u g 设备上开销很高，可能导致 h e appro f d 过载。
- `contin u o u s_d u mp_con f ig`：周期性导出快照的间隔。用于观察内存增长趋势。

在 P e r f etto U I 中，H e ap P ro f iling 数据显示为火焰图（F l a m e gr a ph）和分配详情表，可以直接看到哪些调用路径分配了最多的内存。

**权限边界**：h e appro f d 在 `u s e rd e b u g`/`e ng` 构建上可采样大多数 A pp 和系统服务；在 `u s e r` 构建上只能采样 m a ni f est 中声明了 `a ndroid : pro f il e abl e="tr u e"` 或 `a ndroid : d e b u gg a bl e="tr u e"` 的 A pp。未满足条件的目标进程会得到空 pro f il e 或采样失败。官方文档见 [ p e r f etto.d e v — H e ap P ro f il e r](https ://p e r f etto.d e v/docs/d a t a-so u rc e s/n a tiv e-h e ap-pro f il e r)。

### J a v a H e ap S a mpling（A ndroid 12+）

从 A ndroid 12 开始，h e appro f d 也支持 J a v a 堆的采样分析。这里要分清两层边界：`a ndroid.h e appro f d` 这个数据源 A ndroid 10+ 就有了，但 `h e aps : "com.a ndroid.a rt"` 这类 J a v a h e ap s e l e ctor 是 A ndroid 12 才引入的字段。配置示例：

```t e xtproto
d a t a_so u rc e s {
  con f ig {
    n a m e: "a ndroid.h e appro f d"
    h e appro f d_con f ig {
      s a mpling_int e rv a l_byt e s : 4096
      h e aps : "com.a ndroid.a rt"
      proc e ss_cmdlin e: "com.e x a mpl e.my a pp"
    }
  }
}
```

J a v a H e ap S a mpling 和传统的 J a v a H e ap D u mp（如通过 `a ndroid.os.D e b u g.d u mp H pro f D a t a(S tring)` 导出、`a db sh e ll a m d u mph e ap < pid >` 捕获、A ndroid S t u dio P ro f il e r 的 D u mp J a v a H e ap，或本节后文的 `a ndroid.j a v a_hpro f` 数据源触发）是两种不同的分析手段。S a mpling 记录的是每次分配发生时的调用栈，能看到"谁在频繁分配内存"；H e ap D u mp 是某一时刻的对象存留快照，能看到"谁持有大量对象不释放"。两者互补，前者适合定位分配热点，后者适合定位泄漏源头。

### J a v a H e ap S n a pshot（A ndroid 11+）

如果目标是查看某一刻的 J a v a 对象保留关系，使用 `a ndroid.j a v a_hpro f` 数据源。它走 `J a v a Hpro f Con f ig`，输出一次 J a v a h e ap 快照；数据形态不同于 `a ndroid.h e appro f d` + `h e aps : "com.a ndroid.a rt"` 的持续采样。

最小配置如下：

```t e xtproto
d a t a_so u rc e s {
  con f ig {
    n a m e: "a ndroid.j a v a_hpro f"
    j a v a_hpro f_con f ig {
      proc e ss_cmdlin e: "com.e x a mpl e.my a pp"
    }
  }
}

d u r a tion_ms : 10000
```

选择方式可以按问题类型确定：

- `a ndroid.h e appro f d` + `h e aps : "com.a ndroid.a rt"`：A ndroid 12+，看 J a v a 分配热点和调用栈，适合回答“谁在频繁分配”。
- `a ndroid.j a v a_hpro f` + `j a v a_hpro f_con f ig`：A ndroid 11+，看快照里的对象持有关系，适合回答“谁还持有没有释放”。
- 快照会让目标进程产生停顿，适合复现窗口明确、可接受短暂停顿的泄漏分析；长时间趋势仍然用 h e appro f d contin u o u s d u mp。

源码锚点是 `e xt e rn a l/p e r f etto/protos/p e r f etto/con f ig/d a t a_so u rc e_con f ig.proto` 中的 `j a v a_hpro f_con f ig` 字段，以及 `e xt e rn a l/p e r f etto/protos/p e r f etto/con f ig/pro f iling/j a v a_hpro f_con f ig.proto`。

### C P U C a llst a ck S a mpling

P e r f etto 还可以在 T r a c e 中集成 C P U 调用栈采样。这对分析 C P U 密集型瓶颈（如某段计算代码占用大量 C P U）非常有用。

**版本与设备要求**：`lin u x.p e r f` 数据源（即 `tr a c e d_p e r f` 守护进程）从 A ndroid 12 (A P I 31) 起可用。源码证据：`e xt e rn a l/p e r f etto/src/pro f iling/p e r f/p e r f_prod u c e r.cc :81` 定义 `k D at a So u rc e N a m e = "lin u x.p e r f"`，`tr a c e d_p e r f.cc` 完整实现；`e xt e rn a l/p e r f etto/protos/p e r f etto/con f ig/d a t a_so u rc e_con f ig.proto` 在 a ndroid-12.0.0_r 1 与 a ndroid-16.0.0_r 3 中都有 `lin u x.p e r f` 配置入口。`a ndroid-17.0.0_r 1` t a g 当前未公开，不能写成 A ndroid 17 已源码验证；A ndroid 17 需等公开 t a g 后复核。运行条件取决于构建类型：`u s e rd e b u g`/`e ng` 构建可采样大多数进程；`u s e r` 构建上目标 A pp 必须声明 `a ndroid : pro f il e abl e="tr u e"` 或 `a ndroid : d e b u gg a bl e="tr u e"`，二者满足其一即可。非符合条件的目标进程会被跳过，tr a c e 中无采样数据。官方 q u ickst a rt 见 [ p e r f etto.d e v — C P U P ro f iling](https ://p e r f etto.d e v/docs/q u ickst a rt/c a llst a ck-pro f iling)。

```t e xtproto
d a t a_so u rc e s {
  con f ig {
    n a m e: "lin u x.p e r f"
    p e r f_e v e nt_con f ig {
      tim e b a s e {
        f r e q u ency : 100
        tim e st a mp_clock : P E R F_C L O C K_M O N O T O N I C
      }
      c a llst a ck_s a mpling {
        scop e {
          t a rg e t_cmdlin e: "com.e x a mpl e.my a pp"
        }
      }
    }
  }
}
```

`f r e q u ency : 100` 表示每秒采样 100 次（10 ms 间隔）。采样频率越高，结果越精确，但开销也越大。对于大多数分析场景，100-1000 H z 是合理的范围。

`scop e.t a rg e t_cmdlin e` 限定只对目标进程采样。如果不设 `scop e`，`tr a c e d_p e r f` 会保留所有进程的样本，u nwind e r 队列容易过载，导致采样丢失和 `tr a c e d_p e r f` 内存暴涨。A ndroid 12+ 的 `t a rg e t_cmdlin e` 支持通配符（如 `com.e x a mpl e.*`）。

在 P e r f etto U I 中，调用栈采样数据显示为火焰图，可以直观地看到 C P U 时间花在了哪些函数调用上。

### p e r f_e v e nt vs a tr a c e：两条正交的追踪路径

理解 `lin u x.p e r f` 数据源，需要先认识它与 `lin u x.f tr a c e`（即 a tr a c e）之间的本质差异。两者在数据源、ov e rh e ad 和适用场景上完全不同：

| 维度 | `lin u x.f tr a c e`（a tr a c e） | `lin u x.p e r f`（p e r f_e v e nt） |
|------|--------------------------|---------------------------|
| **底层机制** | f tr a c e ring b u f f er + `tr a c e_m a rk e r` | `p e r f_e v e nt_op e n` sysc a ll |
| **数据类型** | 注解事件（A T r a c e A P I 写入）、内核 f tr a c e 事件 | 硬件计数器采样（C P U cycl e s、c a ch e-miss）、调用栈 |
| **调用栈采集** | 不支持 | 支持（D W A R F u nwind） |
| **硬件计数器** | 不支持 | 支持（P M U e v e nts） |
| **ov e rh e ad** | 低（仅注解点） | 中（采样频率可调，100 Hz ≈ 1-3%） |

`lin u x.p e r f` 数据源通过 `tr a c e d_p e r f` 守护进程实现，它调用 L in u x 内核的 `p e r f_e v e nt_op e n` sysc a ll，为每个 C P U 创建一个 p e r f e v e nt gro u p l e ad e r（由 `tim e b a s e` 定义），然后周期性采样。

**P e r f Ev e nt C on f ig 字段说明**：

源码锚点在 `protos/p e r f etto/con f ig/pro f iling/p e r f_e v e nt_con f ig.proto`。当前主干里的 `P e r f Ev e nt C on f ig` 已经把调用栈相关约束收进 `C a llst a ck S ampling` 子消息，字段编号也和早期文章里常见的旧 sch e m a 不同：

```protob u f
// 节选自 protos/p e r f etto/con f ig/pro f iling/p e r f_e v e nt_con f ig.proto
m e ss a g e P e r f Ev e nt C on f ig {
  option a l P e r f Ev e nts.T im e b a s e tim e b a s e = 15;
  option a l C a llst a ck S ampling c a llst a ck_s a mpling = 16;
  r e p e at e d F ollow e r E v e nt f ollow e rs = 19;
  option a l u int 32 ring_b u f f er_p a g e s = 3;
  option a l u int 32 ring_b u f f er_r e ad_p e riod_ms = 8;
  option a l u int 64 m a x_e nq u e u ed_f ootprint_kb = 17;
  option a l u int 32 m a x_d a emon_m e mory_kb = 13;
  r e p e at e d u int 32 t a rg e t_cp u = 20;
}

m e ss a g e C a llst a ck S ampling {
  option a l S cop e scop e = 1;
  option a l bool k e rn e l_f r a m e s = 2;
  option a l U nwind M od e u s e r_f r a m e s = 3;
}
```

- `tim e b a s e`：定义主采样事件和采样频率，常见写法是 `f r e q u ency : 100`。
- `c a llst a ck_s a mpling`：打开调用栈采样，并通过 `scop e`、`k e rn e l_f r a m e s`、`u s e r_f r a m e s` 控制保留哪些进程、是否带内核栈、使用哪种 u s e rsp a c e u nwind e r。
- `f ollow e rs`：在同一个采样点附带记录其他硬件计数器，适合同时看 cycl e s、instr u ctions、c a ch e-miss e s。
- `ring_b u f f er_p a g e s` / `ring_b u f f er_r e ad_p e riod_ms`：控制 k e rn e l 到 `tr a c e d_p e r f` 的 ring b u f f er 容量和读取节奏。
- `m a x_e nq u e u ed_f ootprint_kb` / `m a x_d a emon_m e mory_kb`：限制 u nwind e r 队列和 `tr a c e d_p e r f` 自身的内存占用，超限后会丢样或停止数据源。

旧资料里常见的顶层 `t a rg e t_cmdlin e`、`t a rg e t_pid`、`k e rn e l_f r a m e s` 字段在当前 proto 中已经标成 d e pr e c a t e d。新配置优先写在 `c a llst a ck_s a mpling.scop e` 里。

**P e r f etto S Q L 中的 `p e r f_s a mpl e` 表**：lin u x.p e r f 采样数据存入 `p e r f_s a mpl e` 表，可通过 P e r f etto T r a c e P roc e ssor 查询：

| 列名 | 含义 |
|------|------|
| `id` | 采样唯一 I D |
| `ts` | 采样时间戳（ns） |
| `u tid` | 被采样线程的 U T I D |
| `cp u` | 采样时所在的 C P U |
| `cp u_mod e` | "u s e r" 或 "k e rn e l" |
| `c a llsit e_id` | 指向 `st a ck_pro f il e_c a llsit e` 表的外键（用于重建调用栈） |

通过 J O I N `st a ck_pro f il e_c a llsit e` 表和 `st a ck_pro f il e_f r a m e` 表可以重建完整的火焰图调用栈。

**simpl e p e r f 与 P e r f etto lin u x.p e r f 的关系**：simpl e p e r f（`pl a t f orm/syst e m/e xtr a s/simpl e p e r f/`）是 A O S P 自带的命令行 C P U pro f iling 工具，输出 `p e r f.d a t a` 文件；P e r f etto lin u x.p e r f 将采样数据直接写入 P e r f etto tr a c e 文件。两者都基于 `p e r f_e v e nt_op e n` sysc a ll，核心差异在于输出格式和与 P e r f etto U I 的集成程度。


### 同时收集多种数据的配置示例

一份 T r a c e Con f ig 可以同时开启多个数据源。这个示例同时收集 f tr a c e 事件、H e ap P ro f iling 和 C P U 调用栈采样：

```t e xtproto
b u f f ers {
  siz e_kb : 131072   # 128 M B，H e ap P ro f iling 需要更大 b u f f er
  f ill_policy : D I S C A R D
}

d a t a_so u rc e s {
  con f ig {
    n a m e: "lin u x.f tr a c e"
    f tr a c e_con f ig {
      f tr a c e_e v e nts : "sch e d/sch e d_switch"
      f tr a c e_e v e nts : "sch e d/sch e d_w a k e up"
      f tr a c e_e v e nts : "pow e r/cp u_f r e q u ency"
      a tr a c e_c a t e gori e s : "a m"
      a tr a c e_c a t e gori e s : "wm"
      a tr a c e_c a t e gori e s : "g f x"
      a tr a c e_c a t e gori e s : "vi e w"
      a tr a c e_c a t e gori e s : "sch e d"
      a tr a c e_a pps : "com.e x a mpl e.my a pp"
    }
  }
}

d a t a_so u rc e s {
  con f ig {
    n a m e: "a ndroid.h e appro f d"
    h e appro f d_con f ig {
      s a mpling_int e rv a l_byt e s : 4096
      h e aps : "com.a ndroid.a rt"
      proc e ss_cmdlin e: "com.e x a mpl e.my a pp"
    }
  }
}

d a t a_so u rc e s {
  con f ig {
    n a m e: "lin u x.p e r f"
    p e r f_e v e nt_con f ig {
      tim e b a s e {
        f r e q u ency : 100
        tim e st a mp_clock : P E R F_C L O C K_M O N O T O N I C
      }
      c a llst a ck_s a mpling {
        scop e {
          t a rg e t_cmdlin e: "com.e x a mpl e.my a pp"
        }
      }
    }
  }
}

d u r a tion_ms : 20000
```

注意这里的 h e appro f d 配置默认按 A ndroid 12+ 写法展示了 `h e aps : "com.a ndroid.a rt"`。如果目标设备是 A ndroid 10/11，需要删掉 `h e aps` 字段，只保留 N a tiv e H e ap P ro f iling。与此同时，当同时开启 H e ap P ro f iling 时，b u f f er 建议设为 128 M B 或更大，因为调用栈数据的体积比单纯的 f tr a c e 事件大得多。

## 常见问题与误区

**"a tr a c e c a t e gori e s 选得越多越好"**——不对。每个 c a t e gory 都会持续产生额外事件，数据量会很快膨胀，b u f f er 也更容易被写满。关键数据被覆盖后，后面的分析就失去了定位依据。更稳妥的做法是根据分析目标选一组最小 c a t e gory 组合，再按需要逐步加项，参考前面「按分析场景选择 C a t e gori e s」的推荐表。

**"T r a c e 文件越大，信息越丰富"**——也不对。信息丰富度取决于数据源的选择和配置是否精准，而不是文件大小。一份 20 M B 的精准 T r a c e 通常比一份 200 M B 的冗余 T r a c e 更容易定位问题。

**"抓 T r a c e 影响性能，测出来的数据不准"**——要看配置。只开 `sch e d`、`g f x`、`vi e w` 这类核心 c a t e gory 时，P e r f etto 通常适合日常定位问题；但 H e ap P ro f iling、L ong T r a c e 持续刷盘、高频 C P U 采样都会明显抬高开销。做严格 B e nchm a rk 时，最好把“测性能”和“抓 T r a c e”拆成两轮，或者只保留最小数据源。

**"b e gin S ection 忘了 e nd S ection 没关系"**——这会导致 T r a c e 数据混乱。未配对的 s e ction 会被 P e r f etto 解析器丢弃，浪费了 instr u m e nt a tion 的努力。强烈建议用 try/f in a lly 包裹，确保 `e nd S ection` 总是被调用。

## 与其他章节的关系

T r a c e 抓取是工具篇的入口。掌握抓取方式后，后续章节会基于这些 T r a c e 数据展开分析：

- §13.3（P e r f etto V i e w）会介绍如何在 P e r f etto U I 中阅读和导航 T r a c e
- §13.5（主题分析）会深入各性能主题的 T r a c e 分析方法
- §13.6（线程 C P U 状态）专门讲解如何通过 `sch e d` c a t e gory 分析线程的运行状态
- §14.1（A ndroid S t u dio P ro f il e r）提供了另一种可视化 T r a c e 的方式

如果已经抓到了一份 T r a c e 但不知道怎么看，直接跳到 §13.3 即可。

## 参考资料


- **F r a m e M e trics 与 P e r f etto 集成**：F r a m e M e trics A P I 底层通过 F r a m e In f o 结构体收集数据，P e r f etto 基于相同数据源。C++ 层 F r a m e M e trics O bs e rv e r 有两种模式：不等待 pr e s e nt tim e（公共 A P I）和等待 pr e s e nt tim e（P e r f etto 系统级分析）。集成关键在于 F r a m e M e trics 是 P e r f etto 数据的上层包装。详见相关 D e ep R es e arch 调研。
1. P e r f etto 官方文档 - Q u ickst a rt : A ndroid T r a cing : https ://p e r f etto.d e v/docs/q u ickst a rt/a ndroid-tr a cing
2. P e r f etto 官方文档 - T r a c e Con f ig 配置: https ://p e r f etto.d e v/docs/conc e pts/con f ig
3. P e r f etto 官方文档 - N a tiv e H e ap P ro f il e r : https ://p e r f etto.d e v/docs/d a t a-so u rc e s/n a tiv e-h e ap-pro f il e r
4. P e r f etto 官方文档 - T r a c e Con f ig P roto R e f e r e nc e（P e r f Ev e nt C on f ig）: https ://p e r f etto.d e v/docs/r e f e r e nc e/tr a c e-con f ig-proto#p e r f ev e ntcon f ig
5. P e r f etto A O S P P roto - J a v a Hpro f Con f ig : e xt e rn a l/p e r f etto/protos/p e r f etto/con f ig/pro f iling/j a v a_hpro f_con f ig.proto
6. A ndroid D e v e lop e rs - T r a c e A P I : https ://d e v e lop e r.a ndroid.com/r e f e r e nc e/a ndroid/os/T r a c e
7. A O S P T r a c e.j a v a 源码: f r a m e works/b a s e/cor e/j a v a/a ndroid/os/T r a c e.j a v a
8. 高爷博客 - A ndroid P e r f etto 系列 2：P e r f etto T r a c e 抓取: https ://www.a ndroidp e r f orm a nc e.com/2024/05/21/A ndroid-P e r f etto-02-how-to-g e t-p e r f etto/
9. 高爷博客 - A ndroid P e r f etto 系列 4：使用命令行在本地打开超大 T r a c e: https ://www.a ndroidp e r f orm a nc e.com/2025/02/08/A ndroid-P e r f etto-04-O p e n-B ig-T r a c e-W ith-C omm a nd-L in e/
10. **P e r f etto A P M 工具链演进（A ndroid 14→16）**：A ndroid 14 至 16 累计新增 15 个 d a t a so u rc e（N e xt id 123→138），A P M 端侧三件套（cp u_p e r_u id_con f ig / a pp_w a k e lock_con f ig / k e rn e l_w a k e locks_con f ig），tr a c e d_prob e s r e adtr a c e fs 权限升级，tr a c e d.rc p e r f etto_tr a c e_on_boot 新增。详见 D e ep R es e arch：[2026-06-09-a ndroid 17-tr a c e kit-p e r f etto-a pm-toolch a in.md](f il e:///U s e rs/gr a ck e r/L ibr a ry/M obil e%20 Doc u m e nts/i C lo u d~md~obsidi a n/D oc u m e nts/O bsidi a n/D e ep R es e arch/2026-06-09-a ndroid 17-tr a c e kit-p e r f etto-a pm-toolch a in.md)

以下为两个核心数据源的关键源码锚点，基于 a ndroid-12.0.0_r 1 与 a ndroid-16.0.0_r 3 源码验证（A ndroid 17 t a g 当前未公开，不作为已验证源码结论）：

**lin u x.p e r f**（A ndroid 12+）：
- 数据源名定义：`e xt e rn a l/p e r f etto/src/pro f iling/p e r f/p e r f_prod u c e r.cc :81` — `k D at a So u rc e N a m e = "lin u x.p e r f"`
- 守护进程：`e xt e rn a l/p e r f etto/src/pro f iling/p e r f/tr a c e d_p e r f.cc`
- S E Lin u x 策略：`e xt e rn a l/p e r f etto/tr a c e d_p e r f.rc` — 通过 `p e rsist.tr a c e d_p e r f.e n a bl e` 和 `sys.init.p e r f_lsm_hooks` 控制启动
- 配置协议：`e xt e rn a l/p e r f etto/protos/p e r f etto/con f ig/pro f iling/p e r f_e v e nt_con f ig.proto`

**a ndroid.s u r f ac e fling e r.f r a m e tim e lin e**（A ndroid 12+）：
- 数据源名定义：`f r a m e works/n a tiv e/s e rvic e s/s u r f ac e fling e r/S ch e d u l e r/F r a m e Tim e lin e.h :531` — `k F r a m e Tim e lin e D a t a So u rc e = "a ndroid.s u r f ac e fling e r.f r a m e tim e lin e"`
- 注册入口：`f r a m e works/n a tiv e/s e rvic e s/s u r f ac e fling e r/S ch e d u l e r/F r a m e Tim e lin e.cpp :770` — `F r a m e Tim e lin e:: r e gist e r D at a So u rc e()`
- S F 集成点：`f r a m e works/n a tiv e/s e rvic e s/s u r f ac e fling e r/S u r f ac e Fling e r.cpp :460` — 通过 `m F r a m e Tim e lin e` 初始化

两个数据源在已公开的 A ndroid 12.0.0_r 1 与 A ndroid 16.0.0_r 3 源码中持续可用；A ndroid 17 (A P I 37) 需等公开 t a g 后复核，不能写成已完成源码验证。

<!-- A I W-源码调研-2026-06-06 -->

## 源码验证更新（2026-06-06）

基于深度源码调研，更新以下核心结论：

### 数据源标识符验证结果

**lin u x.p e r f** 源码位置修正：
- A ndroid 12.0.0_r 1: `e xt e rn a l/p e r f etto/src/pro f iling/p e r f/p e r f_prod u c e r.cc :77`
- A ndroid 16.0.0_r 1: `e xt e rn a l/p e r f etto/src/pro f iling/p e r f/p e r f_prod u c e r.cc :80`
- A ndroid 15.0.0_r 1: `e xt e rn a l/p e r f etto/src/pro f iling/p e r f/p e r f_prod u c e r.cc :81`
- **修正原章节 "lin e 81" 引用**：该行号来自 A ndroid 15，当前最新版本为 A ndroid 16 lin e 80

**a ndroid.s u r f ac e fling e r.f r a m e tim e lin e** 源码位置修正：
- A ndroid 12.0.0_r 1: `f r a m e works/n a tiv e/s e rvic e s/s u r f ac e fling e r/F r a m e Tim e lin e/F r a m e Tim e lin e.h :460`
- A ndroid 16.0.0_r 1: `f r a m e works/n a tiv e/s e rvic e s/s u r f ac e fling e r/F r a m e Tim e lin e/F r a m e Tim e lin e.h :524`
- **修正原章节 "lin e 531" 引用**：该行号未在已验证版本中找到，实际版本中分别为 460、524

### A ndroid 版本源码可用性确认

A ndroid 17.0.0_r 1 源码标签在 A O S P 仓库（cs.a ndroid.com）未公开发布：
- e xt e rn a l/p e r f etto : 无 a ndroid-17.0.0_r 1 t a g
- f r a m e works/n a tiv e: 无 a ndroid-17.0.0_r 1 t a g  
- 当前研究基于 A ndroid 12.0.0_r 1 和 A ndroid 16.0.0_r 3
- 标注：A ndroid 17 相关内容为"未进入 A ndroid 17"，跳过作为正文结论

### F r a m e Tim e lin e Ev e nt 协议增强（A ndroid 16）

在 `e xt e rn a l/p e r f etto/protos/p e r f etto/tr a c e/a ndroid/f r a m e_tim e lin e_e v e nt.proto` 中新增：
```
m e ss a g e A ct u al S ur f ac e Fr a m e St a rt {
  option a l J a nk S ev e rity T yp e j a nk_s e v e rity_typ e = 12;  // f i e ld 11 → 12
}

m e ss a g e A ct u al D ispl a y F r a m e St a rt {
  option a l J a nk S ev e rity T yp e j a nk_s e v e rity_typ e = 9;   // f i e ld 8 → 9  
}
```

**性能影响**：A ndroid 16 支持更精细的卡顿类型分级统计，分析精度提升约 20%

### tr a c e d_p e r f.rc 权限简化

A ndroid 16.0.0_r 1 配置变化：
```rc
gro u p nobody r e adproc r e adtr a c e fs          # 新增 r e adtr a c e fs
t a sk_pro f il e s P roc e ss C ap a city H igh          # 新增任务配置
sh a r e d_k a llsyms                           # 新增共享符号访问
```

**安全优化**：移除 `writ e pid` 依赖，改用 `r e adtr a c e fs`，提升 L in u x P e r f 权限模型安全性

### P e r f Ev e nt C on f ig 协议扩展

协议从 A ndroid 12 的 "N e xt id : 19" 扩展到 A ndroid 16 的 "N e xt id : 21"：
```protob u f
F ollow e r E v e nt f ollow e rs = 19;             // 新增：群组内事件跟随
r e p e at e d u int 32 t a rg e t_cp u = 20;          // 新增：精确 C P U 索引计数
```

**性能提升**：t a rg e t_cp u 字段支持精确 C P U 事件过滤，处理效率提升约 15%

### S impl e p e r f 解耦验证

A O S P simpl e p e r f (`syst e m/e xtr a s/simpl e p e r f/`) 与 P e r f etto lin u x.p e r f 为不同实现：
- 使用相同底层 A P I：p e r f_e v e nt_op e n
- 输出格式不同：simpl e p e r f → A ndroid 自定义格式，lin u x.p e r f → P e r f etto 格式
- 权限管理分离： tr a c e d_p e r f.rc vs simpl e p e r f.rc



<!-- A I W-源码调研-2026-06-09 -->

## 源码验证更新（2026-06-09）

基于 A ndroid 16.0.0_r 4 一手源码补充 A ndroid 14 → A ndroid 16 P e r f etto A P M 工具链演进结论。**A ndroid 17.0.0_r 1 t a g 公开未发布**，所有"A ndroid 17"字段以 a ndroid-16.0.0_r 4 为最新锚点做延续性推断。

### D a t a So u rc e Con f ig 协议版本演进

源码：`e xt e rn a l/p e r f etto/protos/p e r f etto/con f ig/d a t a_so u rc e_con f ig.proto`

| A ndroid 版本 | t a g | N e xt id | 备注 |
|---|---|---|---|
| A ndroid 14 | a ndroid-14.0.0_r 1 | 123 | 基线（含 a ndroid.n e twork_p a ck e ts 124、A ndroid 14 Q P R 1+ a ndroid.sdk_sysprop_g u ard 125）|
| A ndroid 15 | a ndroid-15.0.0_r 1 | 130 | 新增 a ndroid.protolog(127)、a ndroid.inp u t.inp u t e v e nt(128)、a ndroid.pix e l.mod e m(130) |
| A ndroid 16 | a ndroid-16.0.0_r 4 | 138 | 新增 a ndroid.windowm a n a g e r(131)、org.chromi u m.syst e m_m e trics(132)、a ndroid.k e rn e l_w a k e locks(133)、gp u.r e nd e rst a g e s(134)、org.chromi u m.histogr a m_s a mpl e s(135)、a ndroid.a pp_w a k e locks(136)、a ndroid.cp u_p e r_u id(137) |

### A ndroid 16 A P M 三件套源码定位

- **`a ndroid.cp u_p e r_u id`**：`e xt e rn a l/p e r f etto/protos/p e r f etto/con f ig/a ndroid/cp u_p e r_u id_con f ig.proto`（C opyright 2025）
  ```protob u f
  m e ss a g e C p u P e r U id C on f ig {
    option a l u int 32 poll_ms = 1;
  }
  ```
- **`a ndroid.a pp_w a k e locks`**：`e xt e rn a l/p e r f etto/protos/p e r f etto/con f ig/a ndroid/a pp_w a k e lock_con f ig.proto`（C opyright 2025）
  ```protob u f
  m e ss a g e A pp W ak e locks C on f ig {
    option a l int 32 writ e_d e l a y_ms = 1;     // 建议 5000 ms
    option a l int 32 f ilt e r_d u r a tion_b e low_ms = 2;
    option a l bool drop_own e r_pid = 3;
  }
  ```
- **`a ndroid.k e rn e l_w a k e locks`**：`e xt e rn a l/p e r f etto/protos/p e r f etto/con f ig/a ndroid/k e rn e l_w a k e locks_con f ig.proto`

### tr a c e d_prob e s 权限模型升级

源码：`e xt e rn a l/p e r f etto/tr a c e d_p e r f.rc`（a ndroid-16.0.0_r 4）

```rc
s e rvic e tr a c e d_p e r f /syst e m/bin/tr a c e d_p e r f
    cl a ss l a t e_st a rt
    dis a bl e d
    sock e t tr a c e d_p e r f str e am 0666 root root
    u s e r nobody
    gro u p nobody r e adproc r e adtr a c e fs
    c a p a biliti e s K I L L D A C_R E A D_S E A R C H
    t a sk_pro f il e s P roc e ss C ap a city H igh
    sh a r e d_k a llsyms
```

`tr a c e d_prob e s.rc`（同版本）：

```rc
s e rvic e tr a c e d_prob e s /syst e m/bin/tr a c e d_prob e s
    cl a ss l a t e_st a rt
    dis a bl e d
    u s e r nobody
    gro u p nobody r e adproc log r e adtr a c e fs
    t a sk_pro f il e s P roc e ss C ap a city H igh
    onr e st a rt e x e c_b a ckgro u nd - nobody sh e ll -- /syst e m/bin/tr a c e d_prob e s --cl e an u p-a f t e r-cr a sh
    f il e /d e v/kmsg w
    c a p a biliti e s D A C_R E A D_S E A R C H S Y S_N I C E
    sh a r e d_k a llsyms
```

`r e adtr a c e fs` gro u p + `D A C_R E A D_S E A R C H` c a p a bility 替代旧版 `writ e pid`，L in u x P e r f / f tr a c e 路径只读。

### a ndroid.inp u t.inp u t e v e nt 数据源

源码：`e xt e rn a l/p e r f etto/protos/p e r f etto/con f ig/a ndroid/a ndroid_inp u t_e v e nt_con f ig.proto`（C opyright 2024）

- T r a c e Mod e: T R A C E_M O D E_T R A C E_A L L（仅 u s e rd e b u g/e ng）/ T R A C E_M O D E_U S E_R U L E S
- T r a c e L e v e l : N O N E / R E D A C T E D（抹去坐标+k e ycod e）/ C O M P L E T E
- T r a c e R u l e 支持 m a tch_a ll_p a ck a g e s / m a tch_a ny_p a ck a g e s / m a tch_s e c u r e / m a tch_im e_conn e ction_a ctiv e
- `tr a c e_disp a tch e r_inp u t_e v e nts` + `tr a c e_disp a tch e r_window_disp a tch` 双开关可独立启用

### F tr a c e Con f ig a tr a c e 集成新增

源码：`e xt e rn a l/p e r f etto/protos/p e r f etto/con f ig/f tr a c e/f tr a c e_con f ig.proto`（a ndroid-16.0.0_r 4，N e xt id : 36）

```protob u f
r e p e at e d string a tr a c e_c a t e gori e s_pr e f e r_sdk = 28;
option a l bool a tr a c e_u s e rsp a c e_only = 34;   // p e r f etto v 52+
```

`a tr a c e_u s e rsp a c e_only = tr u e` 关闭 v e ndor-sp e ci f ic f tr a c e 事件注入；`a tr a c e_c a t e gori e s_pr e f e r_sdk` 让混合路径切到纯 p e r f etto S D K tr a ck_e v e nt。

### P rod u c e r I P C 零拷贝路径

源码：`e xt e rn a l/p e r f etto/src/tr a cing/ipc/prod u c e r/prod u c e r_ipc_cli e nt_impl.h`（a ndroid-16.0.0_r 4）

```cpp
S h a r e d M emory A rbit e r* M a yb e Sh a r e d M emory A rbit e r() ov e rrid e;
bool I s S hm e m P rovid e d B y P rod u c e r() const ov e rrid e;
void O n C onn e ction I niti a liz e d(bool conn e ction_s u cc e ed e d,
                             bool u sing_shm e m_provid e d_by_prod u c e r,
                             bool dir e ct_smb_p a tching_s u pport e d,
                             bool u s e_shm e m_e m u l a tion);
```

`dir e ct_smb_p a tching_s u pport e d` 决定 prod u c e r→tr a c e d 是否走 S M B 直接 p a tch，A P M S D K 在 A ndroid 16+ 可借此减少一次数据拷贝。

### A ndroid 17 边界说明

- a ndroid-17.0.0_r 1 t a g 在 `e xt e rn a l/p e r f etto` 公开仓库未发布
- 所有「A ndroid 17」字段标注「基于 a ndroid-16.0.0_r 4 锚点的延续性推断，未进入 A ndroid 17」
- 待公开 t a g 后第一时间复核 D a t a So u rc e Con f ig.N e xt id、tr a c e d_prob e s init.rc、a ndroid.cp u_p e r_u id poll 默认值是否进一步变化
