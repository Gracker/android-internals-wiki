# AIW Draft Polish Evidence · 2026-08-08

- lane: draft-polish
- run_id: 20260808-233650-draft-polish-48bffde1
- target: `src/part1-fundamentals/ch05-cpu-power/5.29-android17-gpu-dvfs-headroom-power-advisor.md`
- quality_flags: thin-source-marking
- baseline: Android 17 / `android-17.0.0_r1`
- materials: empty from pre-run JSON; used existing chapter content and existing AOSP source index only.

## Actions

1. Advanced frontmatter from `status: draft` to `status: ready-for-review` because the chapter already contains a substantial source-anchored review body and the polish pass only needed bounded corrections.
2. Added draft-polish pipeline metadata:
   - `task6_state: pending`
   - `task9_state: pending`
   - `pipeline_stage: task6_pending`
   - `last_draft_polish_at: 2026-08-08T23:36:50+08:00`
   - `last_draft_polish_run_id: 20260808-233650-draft-polish-48bffde1`
3. Updated `last_verified` to `2026-08-08` while keeping `last_verified_against: AOSP android-17.0.0_r1`.
4. Reconciled protected outline bullets with the reviewed body:
   - separated Android API level from Power HAL AIDL version;
   - corrected `HeadroomCache` from fixed two-slot LRU to expiring parameter cache;
   - removed unsupported fixed Binder/RPC savings claims;
   - downgraded `sendCompositionData()` from active SurfaceFlinger main path to AIDL/framework scaffolding present in r1;
   - clarified 65Hz kernel idle timer as display synchronization behavior, not direct GPU DVFS control;
   - converted unsupported OEM/game/Perfetto placeholders to explicit `[待验证]` notes.

## Scope Guard

- Modified exactly one existing `src/**/*.md` chapter.
- Did not create any new chapter file.
- Did not edit `src/SUMMARY.md`.
- Did not introduce Android 18/API38+ conclusions.
- Did not run `aiw-git-sync.py`.

## Validation

All required validation passed after the chapter polish and report writes:

```text
python3 scripts/check-metadata.py --files src/part1-fundamentals/ch05-cpu-power/5.29-android17-gpu-dvfs-headroom-power-advisor.md
→ 1 file passed, 0 failed, 0 warnings

python3 scripts/check-summary-links.py
→ SUMMARY link check passed: 661 local link(s), 0 duplicate warning(s).

git diff --check
→ passed (no output)
```
