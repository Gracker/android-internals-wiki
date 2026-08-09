# Draft polish log

- run_id: `20260809-113547-draft-polish-becb58eb`
- lane: `aiw-polish-draft-polish`
- target: `src/part3-tools/ch14-other-tools/14.31-android17-ftrace-atrace-perfetto-bridge.md`
- base_sha: `5f9a863bab6b10c309e7d70f8de59ba891856b94`

## Preflight

- HEAD matched base_sha.
- Working tree had no pre-existing dirty paths before editing.
- Target UTF-8 SHA-256 first 16 hex matched manifest: `cb3f5ca62f3bbf52`.

## Source evidence checked

- AOSP `android-17.0.0_r1` `frameworks/native/cmds/atrace/atrace.cpp`: fetched and counted 45 built-in `k_categories[]` entries; confirmed `findTraceFiles`, vendor `atrace_categories.txt`, HIDL `IAtraceDevice`, `debug.atrace.tags.enableflags`, and `prefer_sdk` references.
- AOSP `android-17.0.0_r1` Perfetto `ftrace_config.proto`: confirmed `drain_buffer_percent`, `atrace_userspace_only`, `buffer_size_lower_bound`, `kprobe_events`, `compact_sched`, and `preserve_ftrace_buffer` fields.
- AOSP `android-17.0.0_r1` Perfetto `ftrace_config_muxer.cc`, `ftrace_controller.cc`, `compact_sched.cc`, `src/android_internal/atrace_hal.cc`: confirmed muxer/controller/compact sched/HIDL HAL implementation anchors used by the chapter.
- AOSP `android-17.0.0_r1` libcutils `trace-dev.cpp`: confirmed `trace_marker` path.
- Android common kernel `android17-6.18-2026-06_r6` `Documentation/trace/ftrace.rst`: fetched successfully as tracefs/ftrace documentation anchor.
- AOSP official ftrace doc `https://source.android.com/docs/core/tests/debug/ftrace`: fetched successfully as operational documentation anchor.

## Changes

- Advanced frontmatter from `draft` to `ready-for-review` because sources are non-empty, Android 17 boundaries are explicit, no unresolved marker was found, and source evidence was checked.
- Added review pipeline frontmatter fields: `pipeline_stage`, `task6_state`, `task9_state`, `draft_polish_at`, `draft_polish_run_id`.
- Updated `last_verified` and `android17_review_notes` to reflect the checked Android 17 source set.
- Reworded the DeepResearch note to remove run-specific wording while preserving the evidence boundary.

## Findings

No open P0/P1 finding was created. No finding was closed.

## Validation

- `python3 scripts/check-metadata.py --files src/part3-tools/ch14-other-tools/14.31-android17-ftrace-atrace-perfetto-bridge.md` → pass.
- `python3 scripts/check-summary-links.py` → pass.
- `git diff --check` → pass.
- Gracker Writing hard gate on final reader-visible body → no added/prohibited pattern hits.
