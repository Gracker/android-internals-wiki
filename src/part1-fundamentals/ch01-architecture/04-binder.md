---
status: draft
title: Binder IPC 机制与性能影响
chapter: '1.4'
section: '1.4'
applicable_versions: Android 8 (API 26) - Android 16 (API 36)
drafted_date: '2026-04-10'
drafted_by: openclaw-task2a
last_verified: '2026-05-09'
last_verified_against: AOSP android-16.0.0_r1, source.android / developer.android
  官方文档
task2b_result: fixed
last_task2b_at: '2026-05-11T03:18:49'
task2b_state: fixed
task6_result: pass-light-edit
task6_state: revisiting
pipeline_stage: draft
confidence: medium
sources:
- type: blog
  path: Personal-Knowlodge/source/Android-Systrace-Binder.md
- type: blog
  path: Personal-Knowlodge/source/Android-Perfetto-10-Binder.md
- type: blog
  path: Personal-Knowlodge/source/2026-03-06_wechat_Binder驱动中的流程详解.md
- type: official
  path: developer.android.com/reference/android/os/IBinder
- type: official
  path: developer.android.com/guide/components/aidl
- type: official
  path: https://source.android.com/docs/core/architecture/aidl/aidl-hals
- type: official
  path: https://source.android.com/docs/core/architecture/ipc/priority-inheritance
- type: official
  path: https://source.android.com/docs/core/architecture/ipc/binder-freezer
- type: official
  path: https://source.android.com/docs/core/perf/cached-apps-freezer
tags:
- binder
- ipc
- aidl
- oneway
- 线程池
- 锁竞争
- perfetto
related_chapters:
- '1.1'
- '2.5'
- '7.2'
- '8.2'
- '9.1'
last_task9_at: '2026-05-09T08:20:00+08:00'
task9_review_notes: '2026-05-09 task9 deep-review: needs-rework。P1 1，P2 2。oneway spam
  detection/async buffer 语义仍需回炉；Perfetto android.binder 标准库版本口径需澄清；冷启动 Binder 次数与服务方法耗时数据缺口沿用既有
  P2。'
last_task9_review_log: logs/deep-review/2026-05-09-08-deep-review.md
reviewed_by: openclaw-task6
reviewed_date: '2026-05-09'
task6_reviewed_date: '2026-05-09'
last_task6_at: '2026-05-09T08:05:00+08:00'
last_task6_review_log: logs/review/2026-05-09-08-review.md
review_round: 8
review_notes: '2026-05-09 task6 revisit: pass-light-edit。完成 Task2B 回炉后复审；修复 frontmatter
  重复键，轻修结构性引导、否定-纠正式句式和翻译腔表述；L1/L2 通过，无新增 B 类回炉项；转入 Task9 复审。'
task9_state: reviewed
task9_result: needs-rework
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-05-11
---
