import logging

from fastapi import APIRouter, HTTPException

import simulator
from collector import worker
from db import database
from llm import narrative
from scenario import generate_scenario

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simulacion", tags=["simulacion"])


@router.get("/estado")
def get_estado():
    return {
        "mode":     simulator.mode,
        "label":    simulator.MODES[simulator.mode]["label"],
        "instance": simulator.INSTANCE,
        "modes":    {k: v["label"] for k, v in simulator.MODES.items()},
    }


@router.post("/modo/{mode}")
def set_modo(mode: str):
    if mode not in simulator.MODES:
        raise HTTPException(status_code=400, detail="Modo invalido")
    simulator.mode = mode
    database.save_simulator_state(mode)
    return {"mode": mode, "label": simulator.MODES[mode]["label"]}


@router.post("/lectura")
def force_lectura():
    worker.collect_and_store()
    return {"ok": True}


@router.post("/narrativa")
def force_narrativa():
    narrative.generate_and_store()
    return {"ok": True}


@router.post("/reset")
def reset_all():
    deleted  = database.clear_all()
    simulator.mode = "normal"
    database.save_simulator_state("normal")
    inserted = generate_scenario(instance=simulator.INSTANCE["id"])
    logger.info(
        "reset_all: eliminados %d metricas %d narrativas; insertados %d puntos de escenario",
        deleted["metrics"], deleted["narratives"], inserted,
    )
    return {"ok": True, "deleted": deleted, "inserted": inserted}
