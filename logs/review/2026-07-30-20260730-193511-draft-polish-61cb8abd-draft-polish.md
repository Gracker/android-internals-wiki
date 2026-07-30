# Draft Polish Evidence Log · 2026-07-30

- **Run ID**: `20260730-193511-draft-polish-61cb8abd`
- **Lane**: draft-polish
- **Target**: `src/part3-tools/ch13-perfetto/22-perfetto-sql-cookbook-performance-analysis.md`
- **SHA16**: `cb1ded2960916b34`

## Pre-run flags

| flag | status |
|---|---|
| thin-source-marking | addressed (6 inline source anchors added) |
| missing-last_verified | fixed |
| missing-confidence | fixed |

## Assessment

Chapter body was already substantial (13 sections, ~27 KB, 18 reference links). Content is well-structured with clear version boundaries separating Android 17 platform (`android-17.0.0_r1`), on-device Perfetto (v54-era snapshot), and host analysis toolchain (v57.2). Technical claims about Trace Processor architecture, stdlib module semantics, data gating, and CI integration are accurate and properly cautious. No fabricated conclusions detected. The SQL templates follow consistent conventions (ns→ms conversion, `dur > 0` filtering, `NULLIF` for empty denominators).

The chapter already distinguishes `upid`/`utid` from `pid`/`tid`, warns against mixing `sched.dur`/`slice.dur`/FrameTimeline `dur`, and maintains the three-version-line discipline. No body content changes were needed — only frontmatter completion and inline source anchors.

## Changes applied

### Frontmatter (draft → ready-for-review)

- `status`: `draft` → `ready-for-review`
- `related_chapters`: `['13.20', '13.21', '14.32']` → `['13.10', '13.11', '13.14', '13.20', '13.21', '14.32']` (added the three chapters explicitly cross-referenced in the body intro paragraph)
- Added `task6_state: "pending"`, `task9_state: "pending"`, `pipeline_stage: "task6_pending"`
- Added `last_verified: "2026-07-30"`
- Added `last_verified_against: "AOSP android-17.0.0_r1 Perfetto stdlib + Perfetto v57.2 host toolchain"`
- Added `last_draft_polish_at`, `last_draft_polish_run_id`
- Added `confidence: "medium"` (claims are source-anchored to stdlib SQL and official docs; SQL outputs are templates, not device-measured results)
- Added structured `sources:` block (4 entries: AOSP stdlib, v57.2 release, official docs, kernel baseline)

### Inline source anchors (thin-source-marking fix)

Added `> 源码参照:` blockquotes to 6 sections that make module/plugin-specific claims:

- §3.1 `android.frames.timeline` — `android-17.0.0_r1` stdlib path
- §3.2 `android.cujs.sysui_cujs` — `android-17.0.0_r1` stdlib path, `InteractionJankMonitor` origin
- §4.2 `sched.latency` — `android-17.0.0_r1` stdlib path, Runnable/Running pairing dependency
- §5.3 `android.memory.dmabuf` — `android-17.0.0_r1` stdlib path, `dmabuf_allocs` ftrace dependency
- §6 `android.binder` — `android-17.0.0_r1` stdlib path, flow relationship dependency
- §7 Data Explorer plugin — `android-17.0.0_r1` plugin path, `dev.perfetto.DataExplorer` id

## Validation

```
check-metadata.py --files <target>: ✅ 1/1 passed, 0 failed, 0 warnings
check-summary-links.py: passed (164 links, 2 pre-existing duplicate warnings)
git diff --check: clean
```

## What downstream Task6/Task9 should verify

- Confirm `android.frames.timeline` output columns (`actual_frame_timeline_count`, `expected_frame_timeline_count`) match `android-17.0.0_r1` stdlib snapshot.
- Verify `android_binder_txns` column names (`client_dur`, `server_dur`, `aidl_name`, `is_sync`) against `android-17.0.0_r1` `android.binder` module.
- Confirm `sched_latency_for_running_interval` table name and `latency_dur` column in `android-17.0.0_r1`.
- Verify Data Explorer plugin id `dev.perfetto.DataExplorer` and feature claims (query graph, DataGrid) against the fixed tag's `ui/src/plugins/` tree.
- Verify `VALUE_AT_MAX_TS` function availability in v57.2 host Trace Processor.
