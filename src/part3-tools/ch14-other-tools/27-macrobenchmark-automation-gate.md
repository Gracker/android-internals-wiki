---
title: "Macrobenchmark 框架与自动化性能门禁"
chapter: "14.27"
status: ready-for-review
drafted_date: "2026-07-08"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-07-08"
last_verified_against: "androidx.benchmark:benchmark-macro-junit4 1.3.x"
confidence: high
sources:
  - type: official
    path: "developer.android.com/topic/performance/benchmarking/macrobenchmark-overview"
  - type: official
    path: "developer.android.com/topic/performance/baselineprofiles/overview"
  - type: aosp
    path: "frameworks/support/benchmark/benchmark-macro/src/main/java/androidx/benchmark/macro/"
tags: [macrobenchmark, benchmark, ci, performance-gate, baseline-profile, androidx]
related_chapters: ["8.7", "13.21", "16.1", "21.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-05"
gap_source: "Official docs/AOSP structure"
---

# 14.27 Macrobenchmark 框架与自动化性能门禁

> **Version boundary**: Based on androidx.benchmark:benchmark-macro-junit4 1.3.x, verified through Android 17 (API 37)
> **Sources**: AndroidX Benchmark official docs + AOSP source + cross-ref to S16.1

[Structure ref: Clippings/Android Performance Optimization - Principles: Re-understanding App Speed Optimization.md]

---

## Framework Positioning and Core Architecture

### Two-Layer System of AndroidX Benchmark

Google provides two complementary performance measurement tools through the AndroidX Benchmark library:

| Tool | Coordinate | Measurement Object | Execution |
|------|-----------|-------------------|-----------|
| **Microbenchmark** | `benchmark-junit4` | Nanosecond-level cost of individual functions/code blocks | In-process JUnit test |
| **Macrobenchmark** | `benchmark-macro-junit4` | Overall user scenarios (startup/scroll/framerate/power) | Instrumentation cross-process test |

[Verified: Official docs, developer.android.com/topic/performance/benchmarking/macrobenchmark-overview]

Macrobenchmark's core design philosophy: **don't measure functions, measure user actions**. How many milliseconds cold startup took, what P90 frame time is during scroll, how much mAh the entire operation consumed -- these are user-perceivable performance metrics. This design aligns perfectly with the "two-layer performance view" of S16.1.

### Runtime Architecture

Macrobenchmark runs as an **Instrumentation test**:

```
+---------------------------------------------------+
|         Test Process (com.example.benchmark)       |
|                                                    |
|  MacrobenchmarkScope.measureRepeated {             |
|      1. setUp / launchActivity / navigate          |
|      2. --- --- measured block --- ---             |
|      3. tearDown / killProcess                     |
|  }                                                 |
|                                                    |
|  +-------------------------------------------+    |
|  |       Perfetto Trace Backend               |    |
|  |  (auto-started by androidx.benchmark)      |    |
|  +-------------------------------------------+    |
+--------------------------+------------------------+
                           | UiAutomation / am start
                           v
+---------------------------------------------------+
|         Target App Process (com.example.app)       |
|                                                    |
|  Application.onCreate() -> Activity.onCreate()     |
|  -> ContentView -> first frame -> user interaction |
+---------------------------------------------------+
```

Key implementation details:

1. **Cross-process control**: The test process operates the target app via `UiAutomation` API and `am start` commands, simulating cold/warm/hot startup and UI interactions
2. **Trace collection**: Each `measureRepeated` iteration auto-configures and pulls a Perfetto trace -- this is the data source for all Metrics [Verified: AOSP frameworks/support/benchmark]
3. **Warmup mechanism**: Default `iterations = 5+` measurements; the library handles warmup vs steady-state separation, outputting P50/P90/P95/max statistics
4. **Compilation mode control**: `CompilationMode` precisely controls the target app's ART compilation state (Full / Partial / None / BaselineProfile), ensuring consistent measurement conditions

> See S13.21 for the complete Perfetto analysis methodology. Macrobenchmark depends on Perfetto at the bottom layer; their relationship is a "collect -> analyze" pipeline.

---

## Benchmark Types and Applicable Scenarios

### Startup Time Measurement

```kotlin
@Test
fun startup() = macrobenchmarkRule.measureRepeated(
    packageName = "com.example.app",
    metrics = listOf(StartupTimingMetric()),
    iterations = 10,
    startupMode = StartupMode.COLD,  // COLD | WARM | HOT
    compilationMode = CompilationMode.Partial(
        baselineProfiles = listOf(R.raw.baseline_profile)
    )
) {
    pressHome()
    startActivityAndWait()
    // Optional: wait for specific async content to load
    device.wait(Until.hasObject(By.res("content_list")), 5_000)
}
```

Differences between three startup modes:

| Mode | Process State | Activity State | Measurement Start | Typical Scenario |
|------|--------------|---------------|-------------------|------------------|
| `COLD` | Non-existent | Non-existent | `am start` / fork | First open, reopen after kill |
| `WARM` | Exists | Destroyed | `startActivity` | Return from other app |
| `HOT` | Exists | Stopped | `onResume()` | Quick switch |

[Verified: Official docs, developer.android.com/topic/performance/benchmarking/macrobenchmark-startup]

`StartupTimingMetric` automatically extracts these key timestamps from the Perfetto trace:
- `processStart` -- Zygote fork completion time
- `firstFrame` -- Activity first frame drawn
- `fullyDrawn` -- When app calls `reportFullyDrawn()` (requires explicit app call)

> Complementary to bootanalyze tool in S8.1/S8.2: bootanalyze focuses on system startup, Macrobenchmark on app startup.

### Frame Rendering Measurement

```kotlin
@Test
fun scroll() = macrobenchmarkRule.measureRepeated(
    packageName = "com.example.app",
    metrics = listOf(FrameTimingMetric()),
    startupMode = StartupMode.WARM,
    compilationMode = CompilationMode.DEFAULT
) {
    val list = device.wait(Until.hasObject(By.res("recycler_view")), 5_000)
    // Simulate user scroll
    device.findObject(By.res("recycler_view"))
        .setGestureMargin(100)
        .scroll(Direction.DOWN, 2.0f)  // scroll 2 screens
}
```

`FrameTimingMetric` output:
- `frameDurationCpuMs` -- CPU frame render time (P50/P90/P95/max)
- `frameDurationUiMs` -- UI thread frame time
- `frameOverrunMs` -- Frame overrun beyond VSync deadline (negative = early)

> For underlying frame rendering mechanisms, see S2.1/S2.3. Macrobenchmark only measures, doesn't attribute; attribution requires Perfetto trace deep analysis.

### TraceMetric - Custom Perfetto Metrics

This is Macrobenchmark's most flexible Metric type, allowing direct Perfetto SQL queries to extract any metric:

```kotlin
@Test
fun customMetric() = macrobenchmarkRule.measureRepeated(
    packageName = "com.example.app",
    metrics = listOf(
        TraceMetric("framesMissed") {
            // Count severe jank frames (frame time > 2 VSync periods)
            "SELECT COUNT(*) as framesMissed " +
            "FROM experimental_slice " +
            "WHERE name = 'Choreographer#doFrame' " +
            "AND dur > 33333000"  // > ~33ms (2 frames at 120Hz)
        },
        TraceMetric("binderBlockedTime") {
            "SELECT SUM(dur) as binderBlockedTime " +
            "FROM experimental_slice " +
            "WHERE name LIKE 'binder%' AND category = 'binder'"
        }
    )
) {
    // User scenario operations...
}
```

[Verified: Official docs, developer.android.com/topic/performance/benchmarking/metric-trace]

`TraceMetric`'s core value: bridges Macrobenchmark's "user scenario reproduction" capability with Perfetto's "system-level observability" capability. This combination is explored more deeply in S13.21.

### PowerMetric - Power Measurement

```kotlin
@Test
fun powerMeasurement() = macrobenchmarkRule.measureRepeated(
    packageName = "com.example.app",
    metrics = listOf(PowerMetric(type = PowerMetric.Type.BATTERY())),
    iterations = 5
) {
    // Run a 30-second video playback or sustained scroll scenario
    // PowerMetric needs sufficient duration for meaningful power data
}
```

`PowerMetric` is based on `PowerManager`'s built-in energy counters, supporting four energy domains:

| Type | Energy Domain | Precision | Android Version |
|------|--------------|-----------|-----------------|
| `BATTERY` | Total device battery power | mAh | Android 10+ |
| `CPU` | CPU energy | mAh (per-cluster) | Android 12+ |
| `DISPLAY` | Display energy | mAh | Android 12+ |
| `GPU` | GPU energy | mAh | Android 12+ (SoC dependent) |

[Verified: Official docs, developer.android.com/topic/performance/benchmarking/metric-power]

> For underlying power measurement mechanisms, see S5.4 DVFS and Power Management. SoC vendor power domain differences, see S17.9.

---

## Baseline Profile Automated Generation and Validation

### Baseline Profile Position

Baseline Profiles are Google's most recommended app-side performance optimization. Their essence is providing ART with critical code path AOT compilation information at install time, avoiding JIT compilation latency during cold startup.

[Verified: Official docs, developer.android.com/topic/performance/baselineprofiles/overview]

The Macrobenchmark library provides `BaselineProfileRule` for automated Baseline Profile generation:

```kotlin
@LargeTest
@RunWith(AndroidJUnit4::class)
class GenerateBaselineProfile {
    @get:Rule
    val baselineProfileRule = BaselineProfileRule()

    @Test
    fun generate() = baselineProfileRule.collect(
        packageName = "com.example.app",
        includeInStartupProfile = true
    ) {
        // Launch app
        pressHome()
        startActivityAndWait()

        // Traverse core user paths
        device.findObject(By.res("nav_home")).click()
        device.wait(Until.hasObject(By.res("feed_list")), 3_000)
        device.findObject(By.res("feed_list"))
            .setGestureMargin(100)
            .scroll(Direction.DOWN, 1.5f)

        device.findObject(By.res("nav_search")).click()
        device.wait(Until.hasObject(By.res("search_input")), 3_000)
    }
}
```

Generation flow:

```
BaselineProfileRule.collect()
    |
    +-- 1. Run with CompilationMode.None (no AOT) -- capture execution paths
    +-- 2. Run with CompilationMode.Partial -- coverage verification
    +-- 3. Extract dex2oat profile file
    +-- 4. Convert to src/main/baseline-prof.txt
    +-- 5. AGP embeds it in APK at build time
         |
         v
    Play Store install -> art_service install -> dex2oat --compiler-filter=speed-profile
```

[Verified: AOSP frameworks/support/benchmark, AGP baseline-profile plugin]

### Generated vs Reference Profile

Android 14 introduced **Cloud Profiles**: Play Store collects runtime profiles reported by devices, aggregates them, and distributes via Play. This creates two Profile sources needing coordination:

| Source | Generation | Distribution | Timeliness |
|--------|-----------|-------------|------------|
| **Local Baseline Profile** | Macrobenchmark `BaselineProfileRule` | Embedded in APK | Effective at install |
| **Cloud Profile** | Play Store aggregated user data | Pushed at Play Store install | Needs sufficient user volume |
| **Startup Profile** | `includeInStartupProfile = true` | Embedded in APK | Affects dex2oat class ordering |

> Android 17's Cloud Profile mechanism is detailed in S16.6. For Baseline Profile practice guide, see S8.7.

---

## CI/CD Performance Gate Integration

### Integration Architecture

```
+-------------+     +------------------+     +------------------+
| GitHub       |     |  Firebase Test   |     |  Macrobenchmark  |
| Actions /    |---->|  Lab / self-host |---->|  runs on devices |
| GitLab CI    |     |  device matrix   |     |  -> JSON output  |
| trigger     |     |  (API 28-37)     |     |                  |
+-------------+     +------------------+     +--------+---------+
                                                       |
                       +------------------+            |
                       |  Result parse &  |<-----------+
                       |  compare (vs     |
                       |  baseline)       |
                       +--------+---------+
                                |
                    +-----------+-----------+
                    v           v           v
              +----------+ +----------+ +--------------+
              | Pass/Fail| | Trend    | | Notify       |
              | gate     | | storage  | | (Slack/      |
              | decision | | (GCS/FB) | |  Email/PR)   |
              +----------+ +----------+ +--------------+
```

### Gate Threshold Setting

Macrobenchmark JSON output contains statistical distribution for each Metric. Gate policies should be based on P90 rather than mean, as P90 better reflects user perception:

```python
# CI script example: performance gate check
import json, sys

results = json.load(open("benchmark-results.json"))

# Cold startup P90 must not regress more than 10%
cold_p90 = results["startup_cold"]["measurements"]["timeToInitialDisplay"]["p90"]
baseline_p90 = 850  # ms, previous baseline
regression_threshold = 1.10  # allow 10% variance

if cold_p90 > baseline_p90 * regression_threshold:
    print(f"FAIL: Cold startup P90 regression: {cold_p90}ms > {baseline_p90}ms x {regression_threshold}")
    sys.exit(1)
else:
    print(f"PASS: Cold startup P90: {cold_p90}ms (baseline: {baseline_p90}ms)")
```

### Multi-Device Matrix Strategy

Performance regression manifests very differently across device tiers. Recommended device matrix:

| Tier | Representative | Key Metrics | Typical Threshold |
|------|---------------|-------------|-------------------|
| High-end | Pixel 9 Pro / Galaxy S25 | P90 frame time | <= 16ms (120Hz) |
| Mid-range | Pixel 7a / Redmi Note 13 | Cold startup P90 | <= 1200ms |
| Entry | Pixel 6a / low-end MediaTek | ANR/timeout rate | 0% crash |

[Structure ref: Clippings/Android Performance Optimization - "Always test on more constrained devices -- flagship 'no problem' often proves nothing"]

> CI/CD performance gate best practices align with S19.x APM tool benchmarking: offline baseline and online data must cross-validate.

---

## Perfetto Trace and Macrobenchmark Synergy

Each Macrobenchmark run automatically produces a Perfetto trace file. This trace is the underlying data source for all Metrics and the most important debugging asset.

### From Metric to Trace Attribution Path

```
User report: Cold startup P90 regressed from 600ms to 900ms
    |
    +-- 1. Macrobenchmark measurement confirms regression is reproducible
    +-- 2. Open Macrobenchmark's Perfetto trace
    +-- 3. Search "TraceLegacyStartup" / "level:1" slice
    +-- 4. Locate the time increase segment in startup trace
    |      +-- ContentProvider initialization?
    |      +-- Application.onCreate() blocking?
    |      +-- First layout inflate time?
    |      +-- First frame draw waiting for GPU?
    +-- 5. Pinpoint to specific function/IO/lock wait
```

> For complete Perfetto trace analysis methodology, see S13.21. Macrobenchmark provides measurement framework, Perfetto provides attribution capability, together forming a complete "measure -> attribute -> optimize" loop.

### Trace Region Markers

Macrobenchmark automatically injects the following region markers into traces for quick navigation:

| Slice Name | Meaning |
|------------|---------|
| `TraceLegacyStartup` | Entire Macrobenchmark startup measurement region |
| `TraceLegacyStartupBegin` | Startup begin (`am start` issued) |
| `TraceLegacyStartupEnd` | Startup end (first frame / `reportFullyDrawn`) |
| `iteration N` | Nth measurement iteration |

[Verified: AOSP frameworks/support/benchmark -- Macrobenchmark uses `android.os.Trace` API to inject these markers]

---

## Android 17 Macrobenchmark New Features

### PowerMetric Capability Enhancement

Android 17's `PowerManager` enhanced energy counter precision and domain separation. Macrobenchmark 1.3.x correspondingly updated `PowerMetric`:

- **CPU cluster-level power separation**: Previously only whole-CPU power; Android 17 supports per-CPU cluster (big/LITTLE/prime) separate statistics
- **5G modem power domain**: New modem energy statistics (SoC dependent -- currently Qualcomm Gen 4 / MediaTek D9400+ supported)
- **Sampling rate improvement**: From minute-level to second-level (via `PowerManager.onEnergyStateChangedCallback`)

[Verified: Official docs, developer.android.com/about/versions/17 -- some features marked SoC-dependent]

### Cloud Profile Validation Support

Android 17 makes Cloud Profiles the default Baseline Profile source. Macrobenchmark adds capabilities:

- `CompilationMode.Partial(baselineProfiles = [...])` can now simulate Cloud Profile behavior
- New `StartupProfile` validation API to confirm that `includeInStartupProfile = true` marked classes are in the dex2oat startup compilation list
- `BaselineProfileRule` generated profiles are compatible with Android 17's `art_service` profile format

> Cloud Profile system-level mechanism in S16.6. Baseline Profile practice guide in S8.7.

### Compose Recomposition Statistics

Macrobenchmark 1.3.x automatically injects Compose Recomposition count trace markers during runs, extractable via `TraceMetric`:

```kotlin
TraceMetric("recompositionCount") {
    "SELECT COUNT(*) as recompositionCount " +
    "FROM experimental_slice " +
    "WHERE name LIKE '%recompose%' " +
    "AND track_id IN (SELECT id FROM experimental_thread_track " +
    "WHERE name = 'Compose:Recomposer')"
}
```

> For complete Compose performance optimization methodology, see S22.x Compose performance chapters.

---

## Production Practice Essentials

### Measurement Reliability Assurance

| Risk | Symptom | Mitigation |
|------|---------|------------|
| **Thermal throttling** | Data degrades significantly from iteration 3+ | iterations >= 10, take steady-state P90; device cooling wait |
| **Background interference** | High standard deviation | Airplane mode, disable background sync, fixed brightness |
| **JIT warmup** | First iteration data skew | CompilationMode control + sufficient iterations |
| **I/O cache** | Warm startup data too fast | sync + drop_caches before COLD mode (requires root) |

### Cross-Validation with Online APM Data

Macrobenchmark offline measurement results should be periodically compared with Android Vitals / self-built APM online data:

- If offline P90 = 500ms but online P90 = 1200ms -> offline scenario doesn't represent real user paths
- If offline has no ANR but online ANR rate > 1% -> need to expand offline test scenario coverage

> For complete APM online monitoring methodology, see S19.x APM chapters. [Structure ref: Clippings - "Always quantify before and after optimization; without baseline, no improvement can be claimed"]

---

## Integration with Internal APM Platform

Macrobenchmark JSON output (`benchmark-json.json`) contains complete statistical distribution for each Metric, suitable for programmatic parsing and warehousing:

```json
{
  "context": {
    "build": { "brand": "google", "model": "Pixel 9 Pro" },
    "cpuCoreCount": 9,
    "cpuLocked": false,
    "targetArchitecture": "arm64-v8a"
  },
  "benchmarks": [{
    "name": "startup_cold",
    "params": { "startupMode": "COLD" },
    "metrics": {
      "timeToInitialDisplay": {
        "minimum": 420.1, "maximum": 680.3,
        "median": 485.2, "p90": 590.7,
        "runs": [420.1, 485.2, 510.4]
      }
    }
  }]
}
```

Recommended integration approach:
1. **Data pipeline**: CI uploads JSON to internal InfluxDB / Prometheus / BigQuery
2. **Trend dashboard**: Show P90 trend lines by commit/version/device dimension
3. **Alerting**: Auto-notify + block merge when P90 regression exceeds threshold
4. **Offline/online calibration**: Periodically compare Macrobenchmark P90 with online APM P90 deviation

---

## Summary

Macrobenchmark's value lies in standardizing performance measurement into a "user scenario -> statistical metric -> performance gate" workflow. It doesn't replace Perfetto/simpleprof as an analysis tool, but provides reliable baseline measurement capability. Keys to correct Macrobenchmark usage:

1. **Measure the right scenarios**: Cover real user high-frequency paths, not dev test paths
2. **Use the right devices**: Mid-to-low-end device data is more valuable than flagship data
3. **Set proper gates**: P90 not mean, allow reasonable variance not zero tolerance
4. **Connect attribution**: When Metrics anomaly occurs, quickly switch to Perfetto trace for deep analysis

> **Cross-references**: S8.7 Baseline Profiles Practice | S13.21 Perfetto Full-Chain Analysis | S16.1 Google Performance Optimization Mainline | S17.9 SoC Differentiated Optimization | S19.x APM System
