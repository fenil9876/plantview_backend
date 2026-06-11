"""Analytics endpoints (any authenticated user)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.enums import BatchStatus
from app.schemas.analytics import (
    CountByStatus,
    CountByTemplate,
    FieldAggregateResult,
    MachineActivity,
    MachineIO,
    Overview,
    StageDistribution,
    TimeseriesPoint,
)
from app.services import analytics_service

router = APIRouter(
    prefix="/analytics", tags=["analytics"], dependencies=[Depends(get_current_user)]
)


@router.get("/overview", response_model=Overview)
def overview(db: Session = Depends(get_db)):
    return analytics_service.overview(db)


@router.get("/batches/by-status", response_model=list[CountByStatus])
def batches_by_status(db: Session = Depends(get_db)):
    return analytics_service.batches_by_status(db)


@router.get("/batches/by-template", response_model=list[CountByTemplate])
def batches_by_template(db: Session = Depends(get_db)):
    return analytics_service.batches_by_template(db)


@router.get("/batches/timeseries", response_model=list[TimeseriesPoint])
def batches_timeseries(
    interval: str = Query("day", pattern="^(day|week|month)$"),
    template_id: int | None = None,
    status: BatchStatus | None = None,
    db: Session = Depends(get_db),
):
    return analytics_service.batches_timeseries(
        db, interval=interval, template_id=template_id,
        status=status.value if status else None,
    )


@router.get("/batches/by-current-stage", response_model=list[StageDistribution])
def batches_by_current_stage(template_id: int, db: Session = Depends(get_db)):
    return analytics_service.batches_by_current_stage(db, template_id=template_id)


@router.get("/machines/activity", response_model=list[MachineActivity])
def machine_activity(db: Session = Depends(get_db)):
    return analytics_service.machine_activity(db)


@router.get("/field-aggregate", response_model=FieldAggregateResult)
def field_aggregate(
    scope: str = Query(..., description="stage | machine_input | machine_output"),
    field: str = Query(..., description="the field_def key to aggregate"),
    op: str = Query(..., description="sum | avg | min | max | count"),
    template_id: int | None = None,
    stage_id: int | None = None,
    machine_id: int | None = None,
    group_by: str | None = Query(None, description="'machine' to group machine-scope results"),
    db: Session = Depends(get_db),
):
    return analytics_service.field_aggregate(
        db, scope=scope, field=field, op=op, template_id=template_id,
        stage_id=stage_id, machine_id=machine_id, group_by=group_by,
    )


@router.get("/machines/io-summary", response_model=list[MachineIO])
def machine_io_summary(
    input_field: str,
    output_field: str,
    stage_id: int | None = None,
    template_id: int | None = None,
    db: Session = Depends(get_db),
):
    return analytics_service.machine_io_summary(
        db, input_field=input_field, output_field=output_field,
        stage_id=stage_id, template_id=template_id,
    )
