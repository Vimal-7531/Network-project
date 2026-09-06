# API5 — Prediction Endpoint Contract

## Endpoint

`POST /network/predict-risk`

## Purpose

Provide a stable prediction API contract before the machine-learning model is implemented.

The current implementation is a stub.

ML5 must replace the prediction implementation without changing the API request or response contract.

## Request

### Content Type

`application/json`

### Required Fields

| Field            | Type     | Description                          |
| ---------------- | -------- | ------------------------------------ |
| `grid_id`        | integer  | Network grid identifier              |
| `timestamp`      | datetime | Timestamp for the prediction         |
| `total_activity` | number   | Activity measure used as model input |

### Example Request

```json
{
  "grid_id": 4821,
  "timestamp": "2013-11-07T23:00:00",
  "total_activity": 5000
}
```

## Response

### Response Fields

| Field              | Type   | Description                                          |
| ------------------ | ------ | ---------------------------------------------------- |
| `risk_score`       | number | Risk score produced by the prediction implementation |
| `risk_level`       | string | Risk classification                                  |
| `model_version`    | string | Version of the prediction implementation             |
| `explanation_note` | string | Explanation of the prediction                        |

### Example Stub Response

```json
{
  "risk_score": 0.5,
  "risk_level": "MEDIUM",
  "model_version": "stub-v1",
  "explanation_note": "Prediction implementation is currently a stub."
}
```

## Validation

The request body is validated using Pydantic.

### Missing Required Field

If a required field is missing, the API returns:

```text
HTTP 422 Unprocessable Entity
```

Example request with a missing field:

```json
{
  "grid_id": 4821,
  "timestamp": "2013-11-07T23:00:00"
}
```

The `total_activity` field is missing.

The response contains a readable validation error identifying the missing field.

### Invalid Field Type

If a field contains an invalid value or type, the API returns:

```text
HTTP 422 Unprocessable Entity
```

Example:

```json
{
  "grid_id": "invalid",
  "timestamp": "not-a-date",
  "total_activity": "invalid"
}
```

FastAPI/Pydantic returns validation details for the invalid fields.

## Current Implementation

The current prediction implementation is a stub.

The stub returns a fixed response:

```json
{
  "risk_score": 0.5,
  "risk_level": "MEDIUM",
  "model_version": "stub-v1",
  "explanation_note": "Prediction implementation is currently a stub."
}
```

The stub allows React and Claude development to proceed before the machine-learning model is available.

## ML5 Integration

ML5 will replace the stub implementation with the trained prediction model.

The API contract must remain unchanged.

ML5 must preserve:

* `POST /network/predict-risk`
* request field names
* request structure
* response field names
* response structure
* `risk_score`
* `risk_level`
* `model_version`
* `explanation_note`

Only the prediction implementation should change.

## Client Compatibility

React clients should not require changes when the stub is replaced by the real model.

The client should continue sending the same request:

```json
{
  "grid_id": 4821,
  "timestamp": "2013-11-07T23:00:00",
  "total_activity": 5000
}
```

The client should continue reading the same response fields:

```text
risk_score
risk_level
model_version
explanation_note
```

## Contract Stability Rule

The prediction endpoint is an API contract between the service layer and its consumers.

Future ML implementation must not require changes to the endpoint path, request field names, or response field names.

## Acceptance Criteria

* [x] Prediction endpoint contract defined
* [x] Request model defined
* [x] Response model defined
* [x] Stub prediction implementation defined
* [x] `model_version` is present and clearly marked as a stub
* [x] Missing required fields return HTTP 422
* [x] Invalid inputs return HTTP 422
* [x] Contract documented in `docs/`
* [ ] Validation tests completed
* [ ] ML5 real model integration completed

## Future State

```text
React / Claude
       |
       v
POST /network/predict-risk
       |
       v
Stable API Contract
       |
       +-------------------+
       |                   |
       v                   v
   Current Stub        Future ML5 Model
       |                   |
       v                   v
  Stub Response       Real Prediction
       |                   |
       +---------+---------+
                 |
                 v
        Same Response Contract
```
