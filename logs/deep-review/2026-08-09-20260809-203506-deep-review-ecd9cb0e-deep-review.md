# AIW Deep Review Log

- run_id: `20260809-203506-deep-review-ecd9cb0e`
- lane: `aiw-polish-deep-review`
- target: `src/part2-performance/ch18-rendering-pipelines/24-advanced-professional-video-apv.md`
- base_sha: `14d544b8593d88c5bf186e78ef81da700aba279a`
- target_sha_before: `1e5fb111b1afb64d`
- target_sha_after: `180fd9f9916f602a`

## Finding

### finding-apv-level-band-order-20260809

- severity: P2
- type: source-boundary
- status: fixed
- claim: APV 探测代码旁的说明把 `pl.level >= requestedLevel` 写成适用于 APV 常量集合，容易被读成 APV level/band 的规格覆盖证明。
- evidence: Android 17 `MediaCodecInfo.java` 的 legacy `isFormatSupported()` 先调用 `supportsProfileLevel(profile, level)`，随后用同 profile 的最高公布 level 生成 `levelCaps` 检查关键参数；`supportsProfileLevel()` 的实现是同 profile 下 `pl.level >= level` 的数值准入，并未为 APV band 单独建立采样率和码率表语义。
- target_range: 正文 “能力探测要检查完整 MediaFormat” 小节，代码块后的 `requestedLevelCovered` 解释段。
- recommended_action: 将该比较限定为 framework capability 的近似入口，并明确严格 level/band 约束还要按 APV 表独立核算采样率与码率。

## Patch Summary

- 更新 frontmatter `last_verified`，增加本轮 deep review 日期和 run id。
- 重写 `requestedLevelCovered` 说明，把 Android 17 Java legacy capability 的数值比较与 APV level/band 规格证明分开。

## Source Evidence

- `android-17.0.0_r1/frameworks/base/media/java/android/media/MediaCodecInfo.java` lines 1052-1098: profile/level 检查后用同 profile 的最高公布 level 继续检查关键 format 参数。
- `android-17.0.0_r1/frameworks/base/media/java/android/media/MediaCodecInfo.java` lines 1132-1195: `supportsProfileLevel()` 对多数视频 codec 使用 `pl.level >= level` 数值判断。
- `android-17.0.0_r1/frameworks/base/media/java/android/media/MediaCodecInfo.java` lines 4394-4537: APV level/band 表分别映射 luma sample rate 与 bitrate。

## Verification

- `python3 scripts/check-metadata.py --files src/part2-performance/ch18-rendering-pipelines/24-advanced-professional-video-apv.md` passed.
- `python3 scripts/check-summary-links.py` passed.
- Gracker Writing hard gate search returned 0 hits.
- `git diff --check` passed.
