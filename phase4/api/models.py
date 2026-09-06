from datetime import datetime

from pydantic import BaseModel


class NetworkSummaryResponse(BaseModel):
    total_activity: float
    active_grids: int
    peak_hour: int
    top_grid: int
    as_of: datetime


class GridActivityPoint(BaseModel):
    timestamp: datetime
    sms_in: float
    sms_out: float
    call_in: float
    call_out: float
    internet_activity: float
    total_activity: float


class GridActivityResponse(BaseModel):
    grid_id: int
    as_of: datetime
    data: list[GridActivityPoint]

class RiskFields(BaseModel):
    risk_score: float | None = None
    risk_level: str | None = None
    model_version: str | None = None


class HotspotRecord(RiskFields):
    grid_id: int
    timestamp: datetime
    total_activity: float
    status: str
    reason: str


class HotspotResponse(BaseModel):
    as_of: datetime
    data: list[HotspotRecord]


class AlertRecord(RiskFields):
    grid_id: int
    timestamp: datetime
    alert_type: str
    current_activity: float
    baseline_activity: float
    severity: str
    reason: str


class AlertResponse(BaseModel):
    as_of: datetime
    data: list[AlertRecord]

class GridLocationResponse(BaseModel):
    grid_id: int
    centroid_lat: float
    centroid_lon: float
    geometry_reference: str

class RiskPredictionRequest(BaseModel):
    grid_id: int
    timestamp: datetime
    total_activity: float

class RiskPredictionResponse(BaseModel):
    risk_score: float
    risk_level: str
    model_version: str
    explanation_note: str
    
class PipelineStatusResponse(BaseModel):
    healthy: bool
    reasons: list[str]
    run_id: str
    run_timestamp: datetime
    overall_status: str
    task_status: dict[str, str | None]
    rows_in: int | None
    rows_rejected: int | None
    nulls_handled: int | None
    rows_published: int | None
    as_of: datetime | None
    freshness_hours: float | None
    freshness_indicator: str