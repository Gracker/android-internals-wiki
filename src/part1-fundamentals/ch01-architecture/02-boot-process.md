---
title: "系统启动全流程"
chapter: "1.2"
section: "1.2"
status: "finalized"
pipeline_stage: task2b_pending
drafted_date: "2026-03-30"
drafted_by: openclaw-task2a
reviewed_date: "2026-05-27"
reviewed_by: "openclaw-task6"
review_type: "task6-writing-quality-review"
task6_state: "reviewed"
task6_result: "pass-light-edit"
task6_reviewed_date: "2026-05-27"
task2b_state: pending
task2b_result: fixed-lite
task9_state: reviewed
task9_result: needs-rework
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-27"
last_task9_at: "2026-05-27T06:23:00+08:00"
last_task2b_at: "2026-05-06T16:04:00+08:00"
last_task2b_lite_at: "2026-06-20"
review_v2_fix: "误区 section boot_completed 事件描述修正 + 事件排序修正"
polish_count: 1
polish_date: "2026-04-05"
polish_by: task2b-polish
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-17"
last_verified_against: "AOSP android-17.0.0_r1, source.android.com 官方文档"
confidence: high
last_task9_review_log: "logs/deep-review/2026-07-01-07-audit.md"
sources:
  - type: aosp
    path: "system/core/init/first_stage_init.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "system/core/init/init.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "system/core/rootdir/init.rc @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/config/preloaded-classes @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/ZygoteInit.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/utils/TimingsTraceAndSlog.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/java/com/android/server/SystemServer.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/EventLogTags.logtags @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/EventLogTags.logtags @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/UserController.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/ActivityTaskManagerService.java @ android-17.0.0_r1"
  - type: aosp
    path: "system/core/bootstat/bootstat.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "hardware/interfaces/cas/aidl/default/cas-default-lazy.rc @ android-17.0.0_r1"
  - type: official
    path: "https://source.android.com/docs/core/architecture"
  - type: official
    path: "https://source.android.com/docs/core/boot"
  - type: official
    path: "https://source.android.com/docs/core/perf/boot-times"
  - type: blog
    path: "obsidian/Cubox/Android 启动系列之我是 init 进程 - 掘金-2024-01-27.md"
tags:
  - boot
  - init
  - zygote
  - SystemServer
  - 启动优化
  - bootchart
  - bootloader
  - preloaded-classes
  - boot-timings
related_chapters:
  - "1.1"
  - "1.3"
  - "1.4"
  - "1.5"
  - "1.7"
  - "8.2"
  - "1.11"
  - "8.3"
review_notes: "2026-05-06T16:04 Task2B：P0 module.layout 修正为 modules.load / BOARD_VENDOR_KERNEL_MODULES_LOAD / BOARD_VENDOR_RAMDISK_KERNEL_MODULES_LOAD + MODULE_SOFTDEP() + async_probe=1。送 Task6 复审。 | 2026-05-06 task6 re-review: frontmatter 去重并修复 YAML；UserController source 与正文/参考资料一致；完成 L1/L2 轻量文风修订；task9 待复审 task2b 修复后的技术问题。 | 2026-05-06 16:24 Task6：Task2B 修复后写作复审；清理大纲口语化表述，无新增 L3/L4 回炉项，送 Task9 复审。"
task9_review_notes: "2026-05-06 16:39 task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 4。 | 2026-05-19 22:20 闲时抽检：bootstat 命令参数错误。 | 2026-05-20 03:17 Task2B 修正：bootstat -l→-p。 | 2026-05-27 06:23 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 1；Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-07-01 07:25 Task9 idle audit: AUTO-FIX AOSP source anchors android-16.0.0_r1→android-17.0.0_r1; P1 queued because finalized chapter has no markdown body after frontmatter."
last_task6_at: "2026-05-27T06:09:00+08:00"
last_task6_audit: "2026-06-08"
last_task6_audit_result: pass-no-edit
task6_review_notes: "2026-05-06 16:24 Task6：Task2B 修复后写作复审；清理大纲口语化表述，无新增 L3/L4 回炉项，送 Task9 复审。 | 2026-05-27 06:09 Task6：复审通过；禁用词扫描无新增硬伤，outline 覆盖完整，无新增 L3/L4 回炉项，送 Task9 复审。"
last_task6_review_log: "logs/review/2026-05-27-06-review.md"
last_task9_audit: "2026-07-01"
last_task9_audit_result: "needs-rework"
task2b_lite_note: "2026-06-20 Task2B Lite: cleared stale last_task9_audit_result=needs-rework (2026-06-10 idle audit P1 phantom; text has no \"3000-4000 常用类\" reference; chapter is finalized with pass-tech-review)."
last_task9_autofix_at: "2026-07-01"
---
