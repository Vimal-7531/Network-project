# ML3 — Model Training and Evaluation

## Objective

Train a machine-learning classifier to predict whether a grid will experience high communication activity in the next hour.

The model uses the six features generated in ML2 and predicts:

`high_activity_risk = 1` when `total_activity(t+1) > 1186.8269`.

The prediction is an operational investigation signal, not a confirmation of network congestion.

## Model

**Algorithm:** Logistic Regression

Logistic Regression was selected because it provides an interpretable model through feature coefficients.

Features:

* `avg_activity`
* `activity_growth`
* `active_hours`
* `peak_ratio`
* `variability`
* `internet_share`

## Data Split

A chronological 80/20 split was used instead of a random split.

### Training

* Earliest: `2013-11-01 05:00:00`
* Latest: `2013-11-06 13:00:00`
* Rows: `1,289,991`
* Positive rate: `8.95%`

### Testing

* Earliest: `2013-11-06 14:00:00`
* Latest: `2013-11-07 22:00:00`
* Rows: `329,998`
* Positive rate: `11.40%`

Train and test timestamps do not overlap.

## Evaluation

| Metric                  |  Result |
| ----------------------- | ------: |
| Accuracy                |  95.95% |
| Precision               |  74.56% |
| Recall                  |  97.85% |
| Test base rate          |  11.40% |
| Majority-class baseline | ~88.60% |

The model performs substantially better than the majority-class baseline.

The high recall indicates that the model identifies most high-activity-risk cases, while precision indicates that some positive predictions are false positives.

Because accuracy exceeded 95%, the result was investigated rather than accepted automatically. The t+1 target alignment and ML2 leakage test provide no evidence of the known feature-window leakage problem.

## Model Coefficients

| Feature           | Coefficient |
| ----------------- | ----------: |
| `avg_activity`    |    7.679884 |
| `peak_ratio`      |    0.941436 |
| `variability`     |   -0.482541 |
| `internet_share`  |    0.433973 |
| `activity_growth` |    0.333272 |
| `active_hours`    |    0.000000 |

`avg_activity` is the strongest positive predictor, which is operationally plausible because higher recent activity is associated with higher activity in the following hour.

## NP3 Comparison

For comparison, NP3 positive alerts were defined as:

`HIGH_ACTIVITY OR ACTIVITY_SPIKE`

Results:

| Comparison    |  Count |
| ------------- | -----: |
| ML3 positive  | 49,363 |
| NP3 positive  |  9,042 |
| Both positive |  4,402 |
| ML3 only      | 44,961 |
| NP3 only      |  4,640 |

The model does not simply reproduce NP3's rule-based alerts. It identifies many additional cases that require operational validation.

## Key Observations

1. **Strong predictive performance:** ML3 achieved 95.95% accuracy, 74.56% precision and 97.85% recall, outperforming the approximately 88.60% majority-class baseline.

2. **Recent activity is important:** `avg_activity` has the strongest coefficient at 7.679884, providing an operationally plausible predictive signal.

3. **ML3 differs from NP3:** The large number of ML3-only predictions shows that the model identifies patterns not captured by the existing rule-based alerts.

## Limitations

* Only seven days of historical data are available.
* The target is a high-activity proxy rather than a direct measurement of network congestion.
* ML3 predictions require further operational validation before deployment.

## Output

Trained model:

`phase6\ml\ml3_output\logistic_regression_model.joblib`

Evaluation outputs are stored in:

`phase6\ml\ml3_output`

## Acceptance Criteria

* [x] Logistic Regression trained
* [x] Chronological train/test split
* [x] Train/test ranges reported
* [x] Accuracy reported
* [x] Precision and recall reported separately
* [x] Base rate reported
* [x] Class balance evaluated
* [x] High accuracy investigated
* [x] Model coefficients inspected
* [x] NP3 comparison completed
* [x] Three observations documented
* [x] Limitations documented
* [x] Model persisted

## Status

**ML3 — COMPLETE**
