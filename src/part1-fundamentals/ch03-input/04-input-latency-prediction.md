---
status: draft
title: 输入延迟与预测输入技术
chapter: '3.4'
section: '3.4'
drafted_date: '2026-04-05'
drafted_by: openclaw-task2a
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-04-11'
last_verified_against: AOSP android-16.0.0_r1 + developer.android.com + perfetto stdlib
  docs
confidence: medium
reviewed_date: '2026-05-11'
reviewed_by: 'openclaw-task6'
task6_result: 'pass-light-edit'
task6_state: 'reviewed'
task2b_state: 'pending'
pipeline_stage: draft
sources:
- type: official
  path: source.android.com/docs/core/interaction/input
- type: official
  path: developer.android.com/reference/androidx/input/motionprediction/MotionEventPredictor
- type: official
  path: https://developer.android.com/reference/android/view/MotionPredictor
- type: official
  path: https://perfetto.dev/docs/analysis/stdlib-docs#android_input_events
- type: blog
  path: https://kernel.meizu.com/2023/10/27/Android-inputTuning-and-Optimizing/
- type: blog
  path: intake/research-feeds/2026-04-05-15-input-pipeline-latency-breakdown.md
- type: blog
  path: intake/research-feeds/2026-04-05-15-motionprediction-low-latency-graphics.md
- type: blog
  path: intake/research-feeds/2026-04-05-15-perfetto-input-latency-sql.md
- type: blog
  path: intake/research-feeds/2026-04-02-11-ch02-android17-deltique-lockfree-messagequeue.md
tags:
- input
- latency
- touch
- prediction
- motioneventpredictor
- front-buffer
- kalman-filter
- perfetto
- input-latency
related_chapters:
- '1.13'
- '3.1'
- '3.2'
- '2.3'
- '2.4'
- '2.5'
- '8.1'
- '13.3'
- '13.5'
pipeline_stage: task6_pending
task6_state: pending
task2b_state: fixed
task2b_result: fixed
last_task2b_at: '2026-05-09T19:40:00+08:00'
review_notes: '2026-05-09 task2b rework: InputThread 调度策略验证、ADPF 输入反馈回路、HWC 4.0 标准化光子时间线。'
task9_state: reviewed
task9_result: needs-rework
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-05-11
---
