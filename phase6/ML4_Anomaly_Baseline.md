# ML4 — Anomaly Baseline

## Objective

Add a simple historical anomaly-detection layer to identify unusually high or low network activity for each grid and hour of day.

ML4 complements the ML3 high-activity classifier and NP3 rule-based alerts by answering a different question:

> Is the current activity unusual compared with the historical behaviour of this grid at the same hour?

The anomaly result is an **investigation signal**, not a diagnosis of network congestion.

## Baseline Method

The ML4 baseline uses historical activity for each:

```text
grid_id + hour
```

The existing NP3 baseline function was generalized and reused for ML4.

For each grid and hour, the baseline is calculated using the **leave-one-out median** of the available historical observations.

The current observation is excluded when calculating its own baseline.

Example:

```text
Grid 3019, Hour 14

Historical same-hour activity
        ↓
Median baseline = 480.1108
        ↓
Current activity = 14.1806
        ↓
Deviation = -465.9302
        ↓
Anomaly score = -0.9705
```

## Anomaly Score

The anomaly score is calculated as:

```text
anomaly_score = (current_activity - baseline_activity) / baseline_activity
```

Interpretation:

* `0` → activity is approximately equal to baseline
* positive → activity is above baseline
* negative → activity is below baseline

Operational thresholds:

| Condition                | Direction   |
| ------------------------ | ----------- |
| score >= 0.50            | HIGH        |
| score <= -0.50           | LOW         |
| otherwise                | NORMAL      |
| missing/invalid baseline | NO_BASELINE |

A 50% deviation was selected as a simple, explainable operational threshold.

## Implementation

Main script:

```text
phase6\ml\ml4_anomaly.py
```

Output:

```text
data\analytics\network_anomaly_scores
```

Actual CSV output:

```text
phase6\ml\ml4_output\network_anomaly_scores.csv
```

The output contains:

* `grid_id`
* `timestamp`
* `hour`
* `total_activity`
* `baseline_activity`
* `deviation`
* `anomaly_score`
* `direction`
* `reason`

The `reason` field provides a human-readable explanation of why the observation was classified as HIGH or LOW.

## Baseline Validation

The dataset contains 7 available days:

```text
2013-11-01 → 2013-11-07
```

Hour-of-day bucket validation produced:

```text
Minimum observations per bucket: 4
Maximum observations per bucket: 7
Average observations per bucket: 7.00
```

Therefore, the hour-of-day baseline uses multiple historical observations rather than a single observation.

## ML4 Results

Total anomaly-score records:

```text
1,679,994
```

Classification:

| Direction |   Records |
| --------- | --------: |
| NORMAL    | 1,526,103 |
| HIGH      |    83,298 |
| LOW       |    70,593 |

Anomaly score summary:

```text
Mean:   0.0201
Median: 0.0093
Minimum: -0.9769
Maximum: 56.1404
```

### Example HIGH anomaly

```text
Grid:              7724
Timestamp:         2013-11-07 15:00
Current activity:  16149.0844
Baseline:          1432.0359
Anomaly score:     10.2770
Direction:         HIGH
```

The activity was substantially above the historical same-hour baseline.

### Example LOW anomaly

```text
Grid:              3019
Timestamp:         2013-11-06 14:00
Current activity:  14.1806
Baseline:          480.1108
Anomaly score:     -0.9705
Direction:         LOW
```

The activity was approximately 97% below the historical same-hour baseline.

## Three-Way Comparison

ML4 was compared with:

* **NP3:** rule-based operational alerts
* **ML3:** high-activity risk classifier
* **ML4:** historical anomaly detector

Comparison period:

```text
2013-11-06 14:00 → 2013-11-07 22:00
```

| Result       |   Count |
| ------------ | ------: |
| ALL_NEGATIVE | 272,892 |
| ML3_ONLY     |  31,400 |
| ML4_ONLY     |  13,997 |
| ML4_NP3      |   3,518 |
| ML4_ML3      |   2,667 |
| ALL_THREE    |   2,595 |
| NP3_ONLY     |   1,978 |
| ML3_NP3      |     951 |

Positive counts:

```text
ML4: 22,777
ML3: 37,613
NP3: 9,042
```

## Why the Methods Disagree

The three methods have different purposes.

### ML3

Predicts:

```text
Will the next hour have high activity risk?
```

It uses features calculated at time `t` to predict activity at `t+1`.

### NP3

Detects rule-based conditions such as:

```text
Current activity > baseline × 2
```

or a sudden activity spike.

### ML4

Detects:

```text
Is the current activity unusual for this grid and hour?
```

Therefore, disagreement is expected.

For example, Grid 3019 at 14:00 was:

```text
ML4  → LOW anomaly
ML3  → No high-activity risk
NP3  → No alert
```

This is not a contradiction. ML4 detected an unusually low current value, while ML3 specifically targets future high activity.

## Output

Three-way comparison output:

```text
phase6\ml\ml4_output\three_way_comparison.csv
```

## Acceptance Criteria

* [x] Historical hour-of-day baseline implemented
* [x] Baseline uses more than one day of history
* [x] Shared baseline implementation reused from NP3
* [x] Deviation and anomaly score calculated
* [x] HIGH and LOW anomaly directions generated
* [x] Human-readable anomaly reasons generated
* [x] ML4 compared with ML3 and NP3
* [x] High and low anomaly cases inspected
* [x] Genuine disagreement explained

## Conclusion

ML4 adds historical context to the network intelligence pipeline. Instead of only detecting predefined rules or predicting future high activity, it identifies whether current grid activity is unusually high or low relative to historical same-hour behaviour.

The ML4 anomaly layer is therefore an additional **investigation signal** that complements NP3 and ML3.
