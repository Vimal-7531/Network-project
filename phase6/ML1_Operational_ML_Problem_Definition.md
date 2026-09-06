# ML1 — Operational ML Problem Definition

## Objective

Define a simple, explainable predictive problem for the Network Operations Predictive Intelligence System.

The model must predict a future high-activity condition using only information that would have been available at prediction time.

The model must not claim that a grid is congested because the available dataset does not contain network capacity, throughput, latency, packet loss, or radio-utilization measurements.

## Primary ML Problem

### Selected Problem — High-Activity Risk

The system will predict whether a network grid is likely to experience unusually high communication activity during the next hourly interval.

The prediction is made using historical activity information available up to time `t`.

The model therefore predicts:

```text
Will this grid experience unusually high activity at time t+1?
```

The operational purpose is to identify grid-hour combinations that deserve further investigation.

A positive prediction means:

```text
Investigate this grid for elevated activity.
```

It does not mean:

```text
The network is congested.
```

## Prediction Unit

The prediction unit is:

```text
Grid + hourly time window
```

Each prediction represents one grid for one hourly interval.

Example:

```text
Grid: 4857
Prediction time: 2013-11-07 22:00
Target interval: 2013-11-07 23:00
```

The model uses information available through the prediction time and predicts the condition of the following hour.

## Time Boundary

The ML problem uses a strict `t → t+1` boundary.

```text
Historical information
        │
        ▼
t-N ... t
        │
        │  prediction
        ▼
      MODEL
        │
        ▼
       t+1
        │
        ▼
Future high-activity label
```

### Feature Window

Features describe activity from the trailing historical window ending at `t`.

Examples include:

* trailing average activity
* trailing peak activity
* activity variability
* recent activity growth

The features must not use activity from `t+1`.

### Target Window

The target describes the next hourly interval:

```text
t+1
```

This ensures that the model is predicting a future state rather than reproducing a condition it has already seen.

## Target Definition

The target is a binary high-activity label.

The calculated 99th percentile of `total_activity` in the available processed dataset is:

```text
P99 = 1186.8269
```

Therefore:

```text
target = 1
if total_activity at t+1 > 1186.8269

target = 0
otherwise
```

### Target Meaning

```text
1 → unusually high activity during the next hour
0 → activity does not exceed the high-activity threshold
```

The threshold is a training proxy for unusually high activity.

It is not a measurement of congestion.

## Threshold Selection

The observed activity distribution is:

| Percentile | total_activity |
| ---------- | -------------- |
| P50        | 0.2041         |
| P75        | 1.1020         |
| P90        | 45.5286        |
| P95        | 247.1788       |
| P99        | 1186.8269      |

The P99 threshold was selected because the objective is to identify the unusually high tail of activity rather than ordinary high-activity observations.

The threshold must be documented and treated as a proxy-label rule.

## Business Action

The model output supports human investigation.

### Positive prediction

```text
High-activity risk detected
        ↓
Investigate grid
        ↓
Review recent activity and operational context
```

### Negative prediction

```text
No elevated high-activity risk detected
        ↓
No immediate investigation triggered by this model
```

The model does not automatically determine the operational state of the network.

## Non-Goals

The model must not claim to predict:

* network congestion
* network capacity
* throughput
* latency
* packet loss
* radio utilization
* service quality
* infrastructure failure

These measurements are not available in the current dataset.

Therefore:

```text
High activity ≠ proven congestion
```

## Proxy-Label Limitation

The target is based on a statistical activity threshold rather than a directly observed operational outcome.

The label:

```text
total_activity at t+1 > 1186.8269
```

only indicates that activity is unusually high relative to the observed dataset distribution.

It does not establish that the network is overloaded or congested.

This limitation must remain visible when interpreting model predictions.

## Leakage Risks

### Risk 1 — Same-Window Label Construction

A circular formulation would be:

```text
Features from t
        ↓
Label also from t
        ↓
Model learns the threshold directly
```

For example, calculating `avg_activity`, `peak_activity`, or other features from the same interval used to create the label could allow the model to reconstruct the target.

This can produce unrealistically high model performance.

### Prevention

The label is moved to the next interval:

```text
Features → trailing window ending at t
Target   → activity at t+1
```

The model therefore cannot directly observe the activity used to create its target.

### Risk 2 — Future Information

Any feature containing information from `t+1` or later would leak future information into the prediction.

Prevention:

```text
Allowed:
t-N ... t

Not allowed:
t+1 and later
```

### Risk 3 — Random Time Splitting

Randomly distributing observations across training and testing sets can cause future observations to influence the training set while earlier observations appear in the test set.

For this operational problem, chronological validation should be used in later ML stages.

## What the Model Knows vs the Threshold

The threshold rule only evaluates:

```text
Is future total_activity > 1186.8269?
```

The trained model will instead learn patterns from historical features available before the target interval.

For example:

```text
Recent activity
Recent peak
Recent average
Activity variability
Recent growth
        ↓
      MODEL
        ↓
Predicted probability of high activity at t+1
```

Therefore, the model attempts to identify patterns that precede elevated activity rather than simply restating the target threshold.

## Data Availability Limitation

The current project contains seven days of processed activity history:

```text
2013-11-01
2013-11-02
2013-11-03
2013-11-04
2013-11-05
2013-11-06
2013-11-07
```

The recommended ML history is at least 10 days, with 14 days preferred.

The current seven-day dataset is therefore a limitation of the available project data.

Later model validation should take this limited historical period into account.

## Feature and Target Sheet

| Item                      | Time boundary | Definition                                           |
| ------------------------- | ------------- | ---------------------------------------------------- |
| Trailing average activity | ≤ t           | Average activity over the historical window          |
| Trailing peak activity    | ≤ t           | Maximum activity in the historical window            |
| Activity variability      | ≤ t           | Variation in recent activity                         |
| Recent activity growth    | ≤ t           | Change in activity over the historical window        |
| High-activity target      | t+1           | `1` when `total_activity > 1186.8269`, otherwise `0` |

The key boundary is:

```text
Features: t-N ... t
Target:          t+1
```

## ML1 Operational Definition

The final ML problem can be stated as:

> Predict whether a network grid will experience unusually high communication activity during the next hourly interval (`t+1`) using only trailing-window activity features available through the current interval (`t`). High activity is defined as `total_activity > 1186.8269`, based on the P99 of the available processed dataset. A positive prediction is an instruction to investigate the grid, not a claim that the network is congested.

## ML1 Acceptance Criteria

* [x] Primary ML problem selected
* [x] Prediction unit defined as grid + hourly window
* [x] Target refers to the future interval `t+1`
* [x] Trailing feature window ends at `t`
* [x] High-activity threshold calculated from actual data
* [x] P99 threshold documented as `1186.8269`
* [x] Proxy-label limitation documented
* [x] Business action defined as investigation
* [x] Congestion is explicitly identified as a non-goal
* [x] Capacity, throughput, latency, packet loss, and radio utilization identified as unsupported claims
* [x] Leakage risks identified
* [x] Same-window circularity prevention documented
* [x] Future-information leakage prevention documented
* [x] Seven-day data limitation documented
* [x] Feature and target sheet defined
* [ ] Feature engineering implemented in ML2
* [ ] Chronological train/test split implemented
* [ ] Model trained and evaluated in ML3
