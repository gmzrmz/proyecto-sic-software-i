import logging
import threading
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

import simulator
from collector import worker
from db import database
from llm import narrative
from scenario import generate_scenario

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simulacion", tags=["simulacion"])

_narrative_generating = False
_narrative_started_at: str | None = None


@router.get("/estado")
def get_estado():
    return {
        "mode":               simulator.mode,
        "label":              simulator.MODES[simulator.mode]["label"],
        "instance":           simulator.INSTANCE,
        "modes":              {k: v["label"] for k, v in simulator.MODES.items()},
        "narrative_generating": _narrative_generating,
        "narrative_started_at": _narrative_started_at if _narrative_generating else None,
        "analysis_hours":     int(database.get_setting("analysis_hours", "1")),
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
    global _narrative_generating
    if _narrative_generating:
        return {"ok": False, "status": "already_generating"}
    _narrative_generating = True
    _narrative_started_at = datetime.now(timezone.utc).isoformat()

    def run():
        global _narrative_generating, _narrative_started_at
        try:
            narrative.generate_and_store()
        finally:
            _narrative_generating = False
            _narrative_started_at = None

    threading.Thread(target=run, daemon=True).start()
    return {"ok": True, "status": "generating"}


@router.post("/ventana")
def set_ventana(body: dict):
    hours = int(body.get("hours", 1))
    if hours not in (1, 3, 24):
        raise HTTPException(status_code=400, detail="Ventana invalida")
    database.save_setting("analysis_hours", str(hours))
    return {"ok": True, "hours": hours}


@router.get("/descripcion")
def get_descripcion():
    return {"descripcion": database.get_setting("instance_description")}


@router.post("/descripcion")
def save_descripcion(body: dict):
    texto = str(body.get("descripcion", "")).strip()[:500]
    database.save_setting("instance_description", texto)
    return {"ok": True, "descripcion": texto}


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
