# ML2 — Engineer Network Activity Features

## Objective

Create a small, explainable feature table for the High-Activity Risk prediction problem defined in ML1.

The features must be calculated strictly from historical activity data available at or before the feature timestamp `t`.

The prediction target is for the following hour `t+1`.

The feature table is generated from the existing hourly grid analytics stored at:

```text
C:\Users\vimalraj.ck\network_project\data\analytics\hourly_grid_summary
```

The resulting feature table is stored at:

```text
C:\Users\vimalraj.ck\network_project\data\analytics\network_feature_table
```

---

## Feature Window Convention

For a prediction made for `t+1`, every feature is calculated using data available only through `t`.

The feature timestamp is therefore:

```text
feature_timestamp = t
```

### Recent Window

The recent activity window contains exactly three hours:

```text
t-2, t-1, t
```

### Baseline Window

The previous baseline window contains exactly three hours:

```text
t-5, t-4, t-3
```

### Prediction Boundary

```text
Baseline          Recent              Target
t-5  t-4  t-3 | t-2  t-1  t | t+1
                 ↑
          feature_timestamp
```

No data from `t+1` or later may be used when calculating the features.

---

## Input Data

The existing hourly grid summary contains the required fields:

```text
grid_id
timestamp
total_activity
internet_activity
```

The data is already aggregated to the grid + hourly level, so feature engineering does not operate on the lower-level country records.

Duplicate `(grid_id, timestamp)` records are removed before feature calculation.

---

## Feature Definitions

Six features are created for every valid `grid_id` and `feature_timestamp`.

| Feature           | Definition                                       | Window             | Meaning                                          |
| ----------------- | ------------------------------------------------ | ------------------ | ------------------------------------------------ |
| `avg_activity`    | Mean of `total_activity`                         | `t-2..t`           | Recent average network activity                  |
| `activity_growth` | `(recent_avg - baseline_avg) / baseline_avg`     | Recent vs baseline | Relative change in recent activity               |
| `active_hours`    | Count of hours where `total_activity > 0`        | `t-2..t`           | Number of active hours                           |
| `peak_ratio`      | `recent_peak / recent_avg`                       | `t-2..t`           | Relative size of the recent activity peak        |
| `variability`     | Standard deviation of `total_activity`           | `t-2..t`           | Recent activity variability                      |
| `internet_share`  | Recent internet activity / recent total activity | `t-2..t`           | Share of activity attributable to internet usage |

---

## 1. avg_activity

Formula:

```text
avg_activity =
mean(total_activity[t-2], total_activity[t-1], total_activity[t])
```

This represents the recent average activity level for a grid.

---

## 2. activity_growth

First calculate:

```text
recent_avg =
mean(total_activity[t-2..t])
```

and:

```text
baseline_avg =
mean(total_activity[t-5..t-3])
```

Then:

```text
activity_growth =
(recent_avg - baseline_avg) / baseline_avg
```

If `baseline_avg` is zero, the feature is explicitly set to `0.0` to prevent division by zero.

Positive values indicate that recent activity is above the previous baseline.

Negative values indicate that recent activity is below the previous baseline.

---

## 3. active_hours

Formula:

```text
active_hours =
count(total_activity > 0)
```

within:

```text
t-2..t
```

The expected maximum is:

```text
3
```

when all three recent hours contain positive activity.

---

## 4. peak_ratio

Formula:

```text
peak_ratio =
max(total_activity[t-2..t]) / avg_activity
```

If `avg_activity` is zero, the feature is explicitly set to `0.0`.

A value close to `1` means the recent activity values are relatively similar.

A larger value indicates that one recent hour is substantially higher than the recent average.

---

## 5. variability

Standard deviation of recent activity:

```text
variability =
stddev(total_activity[t-2..t])
```

If the calculated standard deviation is null, it is explicitly converted to `0.0`.

Higher values indicate greater variation in recent activity.

---

## 6. internet_share

Recent internet activity and recent total activity are aggregated independently:

```text
recent_internet =
sum(internet_activity[t-2..t])
```

```text
recent_total =
sum(total_activity[t-2..t])
```

Then:

```text
internet_share =
recent_internet / recent_total
```

If `recent_total` is zero, the feature is explicitly set to `0.0`.

The existing hourly `internet_share` field is not copied directly because ML2 requires the feature to represent the complete trailing three-hour window.

---

## Valid Feature Rows

A feature row is only produced when both required windows contain the complete number of observations.

Recent window:

```text
3 rows
```

Baseline window:

```text
3 rows
```

Therefore, six historical hourly observations are required before a feature row is considered valid.

For example:

```text
feature_timestamp = 05:00

Baseline:
00:00
01:00
02:00

Recent:
03:00
04:00
05:00

Target:
06:00
```

The target hour is not used in any feature calculation.

---

## Hand-Check Validation

A manual calculation was performed for:

```text
grid_id = 1
feature_timestamp = 05:00
```

Underlying hourly activity:

```text
00:00 → 62.0092
01:00 → 46.3654
02:00 → 42.0870

03:00 → 35.0978
04:00 → 32.2741
05:00 → 35.4160
```

### avg_activity

Recent window:

```text
35.0978
32.2741
35.4160
```

Calculation:

```text
(35.0978 + 32.2741 + 35.4160) / 3
= 34.2626333333
```

Generated feature:

```text
avg_activity = 34.26263333333333
```

Result:

```text
PASS
```

### activity_growth

Baseline average:

```text
(62.0092 + 46.3654 + 42.0870) / 3
= 50.1538666667
```

Recent average:

```text
34.2626333333
```

Calculation:

```text
(34.2626333333 - 50.1538666667) / 50.1538666667
= -0.3168496148
```

Generated feature:

```text
activity_growth = -0.3168496147854336
```

Result:

```text
PASS
```

### peak_ratio

Recent peak:

```text
max(35.0978, 32.2741, 35.4160)
= 35.4160
```

Calculation:

```text
35.4160 / 34.2626333333
= 1.0336625225
```

Generated feature:

```text
peak_ratio = 1.033662522534267
```

Result:

```text
PASS
```

---

## Leakage Prevention

The central ML2 requirement is that features for prediction at `t+1` must not use data from `t+1` or later.

The implementation enforces this by defining:

```text
feature_timestamp = t
```

and calculating features only from:

```text
t-5 through t
```

The target hour:

```text
t+1
```

is outside the feature windows.

---

## Leakage Test

A dedicated test was created:

```text
C:\Users\vimalraj.ck\network_project\phase6\ml\test_features.py
```

The test checks that the real implementation does not use data after the feature timestamp.

The test produced:

```text
REAL IMPLEMENTATION LEAKAGE TEST: PASS
No feature uses data after feature_timestamp.
```

Result:

```text
PASS
```

---

## Deliberate Leakage Demonstration

A deliberately broken implementation was also tested to demonstrate that future-data leakage can be detected.

The broken version introduced future activity relative to the feature timestamp.

The test produced:

```text
BROKEN IMPLEMENTATION LEAKAGE TEST: FAIL AS EXPECTED
```

This demonstrates that the leakage check is capable of detecting the prohibited use of future information rather than merely passing on a correct implementation.

---

## Zero-Division Handling

Potential division-by-zero cases are explicitly handled.

### activity_growth

If:

```text
baseline_avg = 0
```

then:

```text
activity_growth = 0.0
```

### peak_ratio

If:

```text
avg_activity = 0
```

then:

```text
peak_ratio = 0.0
```

### internet_share

If:

```text
recent_total = 0
```

then:

```text
internet_share = 0.0
```

This prevents undefined or infinite feature values.

---

## Generated Feature Table

The resulting feature table contains:

```text
grid_id
feature_timestamp
avg_activity
activity_growth
active_hours
peak_ratio
variability
internet_share
```

The generated table contains:

```text
1,679,994
```

feature rows.

---

## Implementation

The feature engineering implementation is located at:

```text
C:\Users\vimalraj.ck\network_project\phase6\ml\features.py
```

The leakage validation is located at:

```text
C:\Users\vimalraj.ck\network_project\phase6\ml\test_features.py
```

---

## ML2 Outputs

```text
phase6/
├── ML2_Feature_Engineering.md
└── ml/
    ├── features.py
    └── test_features.py
```

Feature output:

```text
data/
└── analytics/
    └── network_feature_table/
```

---

## ML2 Acceptance Criteria

* [x] Feature lookback convention defined
* [x] Recent window defined as `t-2, t-1, t`
* [x] Baseline window defined as `t-5, t-4, t-3`
* [x] `feature_timestamp` represents `t`
* [x] Six required feature names implemented
* [x] Every feature row contains `grid_id`
* [x] Every feature row contains `feature_timestamp`
* [x] No feature uses data after `feature_timestamp`
* [x] Zero-division handling explicitly implemented
* [x] `avg_activity` manually reproduced
* [x] `peak_ratio` manually reproduced
* [x] Real implementation leakage test passes
* [x] Deliberately broken implementation detects leakage
* [x] Feature table persisted
* [x] Feature table contains 1,679,994 rows

## ML2 Status

**COMPLETE**

The engineered feature table is ready for ML3 target construction and subsequent model training.
