---
title: 进程模型与生命周期管理
chapter: '1.3'
section: '1.3'
status: ready-for-review
reviewed_date: '2026-05-05'
reviewed_by: openclaw-task6
review_type: task6-writing-quality-review
task6_result: pass-light-edit
drafted_date: '2026-03-31'
applicable_versions: Android 10 (API 29) - Android 16 (API 36)
last_verified: '2026-04-09'
last_verified_against: AOSP android-16.0.0_r1
confidence: high
polish_count: 1
polish_date: '2026-04-05'
polish_by: task2b-polish
sources:
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ProcessList.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ProcessStateRecord.java
- type: aosp
  path: frameworks/base/core/java/android/os/Binder.java
- type: aosp
  path: frameworks/base/core/java/android/os/Process.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/PhantomProcessList.java
- type: aosp
  path: frameworks/base/core/java/android/util/FeatureFlagUtils.java
- type: aosp
  path: system/memory/lmkd/lmkd.cpp
- type: aosp
  path: system/core/libprocessgroup/profiles/task_profiles.json
- type: aosp
  path: system/core/libprocessgroup/processgroup.cpp
- type: aosp
  path: system/core/libcutils/include/private/android_filesystem_config.h
- type: official
  path: developer.android.com/guide/components/processes-and-threads
- type: official
  path: developer.android.com/guide/topics/manifest/application-element
- type: official
  path: developer.android.com/guide/topics/manifest/service-element
- type: official
  path: source.android.com/docs/core/perf/lmkd
tags:
- process
- ams
- oom_adj
- lmkd
- zygote
- process-lifecycle
- binder
related_chapters:
- '1.1'
- '1.2'
- '1.4'
- '1.5'
- '4.4'
- '5.1'
- '5.8'
task6_state: revisiting
review_notes: '2026-04-29 task6 re-review (revisiting): pass-light-edit, 3 L1 fixes.
  | 2026-05-05 task6 re-confirm: fixed L1/L2 wording and punctuation; task9_result=needs-rework,
  pipeline kept task2b_pending.'
task2b_result: fixed
pipeline_stage: task6_pending
task6_reviewed_date: '2026-05-05'
task2b_state: fixed
last_task2b_at: '2026-05-11T03:18:49'
last_task9_at: '2026-05-01T05:32:43+08:00'
task9_state: reviewed
task9_result: needs-rework
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-05-11
---
