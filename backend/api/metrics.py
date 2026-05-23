from fastapi import APIRouter, HTTPException, Query

from db import database

router = APIRouter(prefix="/metricas", tags=["metricas"])


@router.get("/actuales", summary="Metricas mas recientes de la instancia")
def get_current_metrics():
    row = database.get_latest_metric()
    if row is None:
        raise HTTPException(status_code=404, detail="Sin datos disponibles")
    return row


@router.get("/historial", summary="Historial de metricas por ventana de tiempo")
def get_metrics_history(horas: int = Query(default=3, ge=1, le=720)):
    return database.get_metrics_by_hours(horas)
