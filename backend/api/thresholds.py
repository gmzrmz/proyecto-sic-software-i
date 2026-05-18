from fastapi import APIRouter
from pydantic import BaseModel, Field

import config

router = APIRouter(prefix="/config", tags=["configuracion"])


class Umbrales(BaseModel):
    threshold_cpu: float = Field(ge=0, le=100)
    threshold_ram: float = Field(ge=0, le=100)


@router.get("/umbrales", summary="Umbrales de alerta actuales")
def get_umbrales():
    return {
        "threshold_cpu": config.THRESHOLD_CPU,
        "threshold_ram": config.THRESHOLD_RAM,
    }


@router.put("/umbrales", summary="Actualizar umbrales sin reiniciar")
def update_umbrales(body: Umbrales):
    config.THRESHOLD_CPU = body.threshold_cpu
    config.THRESHOLD_RAM = body.threshold_ram
    return {
        "threshold_cpu": config.THRESHOLD_CPU,
        "threshold_ram": config.THRESHOLD_RAM,
    }
