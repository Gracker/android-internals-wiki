---
title: RecyclerView 性能测试
chapter: "22.2"
status: finalized
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
task9_result: pass-tech-review
applicable_versions: Android 10-17
last_verified: "2026-07-18"
confidence: high
tags: [RecyclerView, rendering]
sources:
  - type: official
    path: https://developer.android.com/develop/ui/views/layout/recyclerview
---
# RecyclerView 滑动

RecyclerView 复用 ViewHolder，避免每次滚动都创建完整视图。

## Trace 验证

```sql
SELECT name, dur FROM slice WHERE name GLOB '*RecyclerView*';
```

| 信号 | 含义 |
| --- | --- |
| bind | 绑定开销 |
