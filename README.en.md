# Android Internal Wiki

[简体中文](README.md)

An AI-assisted, continuously evolving knowledge base for experienced Android
developers and system engineers. It connects mechanisms across App, Framework,
Native, and Kernel layers, with an emphasis on architecture, performance, and
practical tooling.

> The project is in alpha. This file provides an English project and ecosystem
> navigation summary; the complete current README and book content remain in
> Chinese, and a full English edition is planned after v1.0.

The canonical Chinese body now follows five parts and 26 chapters, plus a
preface and appendices. `src/SUMMARY.md` is the complete mdBook entry point; as
of 2026-08-06 it links all retained canonical material without missing or
duplicate local targets. Workflow maturity remains tracked separately in
`metadata/progress.json` and `metadata/queue.json`.

<!-- android-performance-ecosystem:start -->
## Android performance ecosystem

The [Android Performance Ecosystem](https://github.com/Gracker/android-performance-ecosystem) brings its navigation Hub and seven core projects into an optional path from instrumentation and capture to analysis, system knowledge, and reproducible cases.

| Stage | Project | Purpose | Address |
| --- | --- | --- | --- |
| Navigate | [Android Performance Ecosystem](https://github.com/Gracker/android-performance-ecosystem) | Maintain the shared project map, handoff metadata, generated README navigation, and drift checks. | [GitHub](https://github.com/Gracker/android-performance-ecosystem) |
| Instrument | [TraceFix](https://github.com/Gracker/TraceFix) | Inject app-side android.os.Trace sections at build time so method work is visible at runtime. | [GitHub](https://github.com/Gracker/TraceFix) |
| Capture and measure | [Perfetto Tools](https://github.com/Gracker/perfetto-tools) | Capture repeatable Perfetto traces and collect FPS or Simpleperf measurements. | [GitHub](https://github.com/Gracker/perfetto-tools) |
| Analyze | [SmartPerfetto](https://github.com/Gracker/SmartPerfetto) | Investigate traces with an AI-assisted Web UI, CLI, reports, sessions, comparisons, and evidence workflow. | [GitHub](https://github.com/Gracker/SmartPerfetto) |
| Agent analysis | [Perfetto Skills](https://github.com/Gracker/Perfetto-Skills) | Give agents a portable Perfetto analysis Skill for Android, Linux, and Chromium, with selected assets synchronized through pinned workflows. | [GitHub](https://github.com/Gracker/Perfetto-Skills) |
| Learn | [Android Performance Blog](https://github.com/Gracker/Gracker.github.io) | Teach Perfetto and Systrace analysis through articles, system explanations, and case studies. | [AndroidPerformance.com](https://www.androidperformance.com/) · [GitHub](https://github.com/Gracker/Gracker.github.io) |
| System knowledge | Android Internal Wiki | An alpha knowledge base for Android mechanisms from App to Framework, Native, and Kernel. | [GitHub](https://github.com/Gracker/android-internals-wiki) |
| Reproduce | [Trace for Blog (SystraceForBlog)](https://github.com/Gracker/SystraceForBlog) | Provide the Perfetto, Systrace, and related case files used by articles for hands-on reproduction. | [GitHub](https://github.com/Gracker/SystraceForBlog) |
<!-- android-performance-ecosystem:end -->

## Full documentation

Read the [Chinese README](README.md) for the chapter map, reading order,
licensing, and contribution workflow. Weekly EPUB snapshots are published on
[GitHub Releases](https://github.com/Gracker/android-internals-wiki/releases).

## Author

Gao Jianwu (Gracker). Chengdu. Android system and app performance (Framework, APM, smoothness / startup / stability / power). Bio: [src/preface/about-author.md](src/preface/about-author.md) (Chinese).

- Blog: <https://www.androidperformance.com/>
- Zhihu: <https://www.zhihu.com/people/gracker>
- Jike: <https://okjk.co/pJbjFa>
- WeChat official account: AndroidPerformance
- Juejin: <https://juejin.cn/user/1816846860560749>
- Bilibili: <https://space.bilibili.com/213254842>
- WeChat: 553000664
- Email: dreamtale.jg@gmail.com

## Support

Issues and pull requests help most. Tips (Alipay / WeChat) are in [src/preface/support.md](src/preface/support.md). Community contributions follow [CONTRIBUTING.md](CONTRIBUTING.md). A scheduled job triages open issues/PRs twice a day; it does not merge.

## Knowledge Pack and licensing

Every body Markdown file under the canonical 26 chapter directories can be
published in the versioned, read-only SmartPerfetto Knowledge Pack. Workflow
state, Task 6/Task 9 results, and review queues are audit metadata rather than
inclusion gates. Navigation README/SUMMARY files, obsolete paths, duplicates,
blank files, and generated reports are not article bodies. Local
private-path lines are redacted from the public projection, and secret findings
fail the release. The exact policy is defined by
[`knowledge-pack/policy.yaml`](knowledge-pack/policy.yaml).

Community reading and non-commercial reuse are under
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
Publishing a book, selling the text, paid courses, or bundling the body into a
paid product needs a written grant from Gao Jianwu (Gracker). Cloning the repo
or downloading the free EPUB does not grant publishing rights and does not
waive royalties. See [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md).

Possession of a Pack does not itself grant commercial-use rights. See
[`KNOWLEDGE-PACK-LICENSE.md`](KNOWLEDGE-PACK-LICENSE.md) for the exact
SmartPerfetto redistribution boundary.
