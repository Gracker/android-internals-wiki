# 2026-07-01 Draft Duplicate Audit

## Scope

- Canonical repo: `/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki`
- User request: scan draft/new chapters for duplicate coverage and delete duplicates.
- Frontmatter scan before cleanup: `draft=38`, `drafted=1`, `superseded=14`.
- Progress metadata before cleanup was stale (`draft=32`) and did not match source frontmatter.

## Deleted

Deleted 53 tracked source files:

- 14 superseded duplicate files already marked as replaced.
- 28 draft files with exact title match, same section-number conflict, wrong-path chapter shell, or clear coverage by ready/finalized chapters.
- 11 `ch27-*` orphan/new chapter files not present in the normal `SUMMARY.md` flow and covered by existing AI/Camera/methodology chapters.

High-confidence coverage examples:

- `01.27 Android 17 Binder IPC 异步机制与批处理流水线` -> `1.25 Android 17 Binder IPC 异步机制与批处理流水线`
- `01.28 Android 17 MessageQueue 重构与 DeliQueue 无锁优化` -> `1.13/1.26 DeliQueue` coverage
- `2.28 Android 17 Adaptive Refresh Rate Implementation` -> `2.18/2.19 ARR` coverage
- `04.19 MemoryLimiter + cgroup memory.high` -> `4.17` and `part2-memory 4.19` coverage
- `4.20 LMKD v2` -> removed as duplicate/invalid against `4.4`, `4.10`, `4.17`, `16.8`; AOSP 17 does not expose an "LMKD v2" platform concept in the existing reviewed material.
- `16.19/16.20 bootanalyze` -> `16.7 Android 系统启动耗时优化与 bootanalyze`
- `22.1 Vulkan 多队列` / `26.15 Vulkan 异步编译管线` -> `18.26` and `22.29` coverage
- `23.12 Native DCL` -> `20.15 Android 17 Native DCL`
- `23.13 onTrimMemory` -> `4.18 Android 17 onTrimMemory`
- `ch27-ai-ecosystem` -> `20.1 Android AI 手机生态` plus `5.11/5.16/5.19/5.27`
- `ch27-app-distribution` -> `1.31` and `16.5 app distribution/sharing` coverage
- `ch27-camera-hal3` / `ch27-camerax-zsl` -> `2.29/2.30/2.31/2.32` camera coverage
- `ch27-performance-engineering` -> `15.1/15.10/14.6/26.x` methodology and governance coverage

## Metadata Cleanup

- Removed deleted links from `src/SUMMARY.md`.
- Removed duplicate queue entries from `metadata/queue.json`; `drafts` is now empty.
- Recomputed `metadata/progress.json` from current frontmatter:
  - `total=510`
  - `draft=10`
  - `ready-for-review=159`
  - `finalized=341`
  - `superseded=0`

## Remaining Drafts

Kept 10 draft files because this audit did not find a high-confidence replacement, or because the file is a legitimate existing slot needing later Task2A/Task6 handling:

- `src/part3-tools/ch15-methodology/07-aosp-reading.md`
- `src/part3-tools/ch19-apm/19.10-apm-tool-compatibility.md`
- `src/part2-performance/ch07-smoothness/04-typical-scenarios.md`
- `src/part1-fundamentals/ch05-cpu-power/25-low-power-standby-background-performance.md`
- `src/part5-app/ch22-rendering-practice/27-adaptive-layout-multi-form-factor-performance.md`
- `src/part5-app/ch22-rendering-practice/28-compose-compiler-metrics-recomposition-diagnostics.md`
- `src/part5-app/ch26-observability/26.14-android14-memory-tracking-integration.md`
- `src/part5-app/ch26-observability/26.23-xtrace-art-dynamic-method-tracing.md`
- `src/part5-app/ch21-startup/16-thread-pool-concurrency-performance.md`
- `src/part5-app/ch24-io-network/20-android17-network-quota-management.md`

## Policy Fix

Updated `openclaw-tasks/task2a-content-processing-new.md` to freeze new chapter creation:

- Task2A may only process existing empty `draft` chapters.
- If no empty `draft` exists, it must stop.
- It may not create files, append `SUMMARY.md`, or add progress/queue entries for new chapters.
- Gap dedup guard remains an audit/blocking tool, not permission to create.
