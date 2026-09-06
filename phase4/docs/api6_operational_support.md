# API6 — Operational Support Endpoints

## Purpose

API6 provides operational evidence for the Network Operations Claude phase.

The endpoints allow the assistant to determine whether the current pipeline data can be trusted and where a specific network grid is located.

## Endpoint 1 — Pipeline Status

### Request

GET /pipeline/status

### Purpose

Returns the machine-readable pipeline status record produced by the DE7 quality-check stage.

### Response

The response contains:

- healthy
- reasons
- run_id
- run_timestamp
- overall_status
- task_status
- rows_in
- rows_rejected
- nulls_handled
- rows_published
- as_of
- freshness_hours
- freshness_indicator

### Health Definition

The pipeline is considered healthy when the latest pipeline status record has overall_status equal to SUCCESS.

If the latest status is not SUCCESS, healthy is false and reasons contains an explanation.

### Evidence Use

This endpoint is a sanctioned evidence source for the Claude phase.

Claude should use this endpoint when answering operational questions such as:

- Can I trust the current pipeline data?
- Did the latest pipeline run succeed?
- What was the latest AS_OF?
- Were rows rejected?
- Which pipeline tasks succeeded or failed?

Claude should use the returned status record rather than recomputing pipeline health from raw data.

## Endpoint 2 — Grid Location

### Request

GET /network/grid/{grid_id}/location

Example:

GET /network/grid/4821/location

### Purpose

Returns the geographic reference information for a network grid.

### Response

The response contains:

- grid_id
- centroid_lat
- centroid_lon
- geometry_reference

The endpoint does not return the complete Polygon geometry.

### Evidence Use

This endpoint is a sanctioned evidence source for the Claude phase.

Claude should use this endpoint when answering questions about the geographic location of a network grid.

## DE8 Failure Demonstration

A deliberate failed status record was injected into the pipeline status CSV.

The API returned:

- healthy = false
- overall_status = FAILED
- populated reasons
- the injected run identifier and timestamp

The original pipeline status CSV was subsequently restored.

This demonstrates that API6 correctly reflects an unhealthy pipeline state from the DE7 status record.

## Acceptance Criteria

- [x] GET /pipeline/status implemented
- [x] Pipeline status is read from the DE7 status record
- [x] Healthy/unhealthy state is returned
- [x] Reasons are returned when unhealthy
- [x] Task status is returned
- [x] Row counts are returned
- [x] AS_OF is returned
- [x] Freshness indicator is returned
- [x] GET /network/grid/{grid_id}/location implemented
- [x] Grid centroid is returned
- [x] Polygon reference is returned
- [x] Full Polygon geometry is not returned
- [x] Deliberate failure scenario tested
- [x] Original status record restored
- [x] Both endpoints documented as Claude-phase evidence sources