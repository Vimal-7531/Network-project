from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from phase4.api.models import (
    NetworkSummaryResponse,
    GridActivityResponse,
    GridActivityPoint,
    HotspotResponse,
    AlertResponse,
    GridLocationResponse,
    RiskPredictionRequest,
    RiskPredictionResponse,
    PipelineStatusResponse
)
from phase4.services.network_service import (
    get_network_summary,
    get_grid_activity,
    get_network_hotspots,
    get_network_alerts,
    get_grid_location,
    predict_network_risk,
    get_pipeline_status
)

router = APIRouter(
    prefix="/network",
    tags=["Network"]
)
pipeline_router = APIRouter(
    tags=["Operations"]
)

@router.get(
    "/summary",
    response_model=NetworkSummaryResponse
)
def network_summary(
    as_of: datetime | None = Query(default=None)
):
    try:
        return get_network_summary(as_of)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )


@router.get(
    "/grid/{grid_id}",
    response_model=GridActivityResponse
)
def grid_activity(
    grid_id: int,
    date: str | None = Query(default=None),
    hour: int | None = Query(default=None),
    as_of: datetime | None = Query(default=None)
):
    try:
        data = get_grid_activity(
            grid_id=grid_id,
            date=date,
            hour=hour,
            as_of=as_of
        )

        effective_as_of = (
            as_of
            if as_of is not None
            else datetime.fromisoformat(
                data[-1]["timestamp"].isoformat()
            )
        )

        return {
            "grid_id": grid_id,
            "as_of": effective_as_of,
            "data": [
                GridActivityPoint(**row)
                for row in data
            ]
        }

    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc)
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )

@router.get(
    "/hotspots",
    response_model=HotspotResponse
)
def network_hotspots(
    limit: int = Query(
        default=50,
        ge=1
    ),
    severity: str | None = Query(
        default=None
    ),
    as_of: datetime | None = Query(
        default=None
    )
):
    try:
        return get_network_hotspots(
            limit=limit,
            severity=severity,
            as_of=as_of
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )


@router.get(
    "/alerts",
    response_model=AlertResponse
)
def network_alerts(
    limit: int = Query(
        default=50,
        ge=1
    ),
    severity: str | None = Query(
        default=None
    ),
    as_of: datetime | None = Query(
        default=None
    )
):
    try:
        return get_network_alerts(
            limit=limit,
            severity=severity,
            as_of=as_of
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )

@router.get(
    "/grid/{grid_id}/location",
    response_model=GridLocationResponse
)
def grid_location(grid_id: int):
    try:
        return get_grid_location(grid_id)

    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc)
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )
@router.post(
    "/predict-risk",
    response_model=RiskPredictionResponse
)
def predict_risk(request: RiskPredictionRequest):
    return predict_network_risk(request)

@pipeline_router.get(
    "/pipeline/status",
    response_model=PipelineStatusResponse
)
def pipeline_status():
    try:
        return get_pipeline_status()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )