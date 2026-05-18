from fastapi import APIRouter, HTTPException

from db import database

router = APIRouter(prefix="/narrativa", tags=["narrativa"])


@router.get("/ultima", summary="Ultima narrativa generada")
def get_latest_narrative():
    row = database.get_latest_narrative()
    if row is None:
        raise HTTPException(status_code=404, detail="Aun no hay narrativas generadas")
    return row


@router.get("/historial", summary="Ultimas narrativas generadas")
def get_narrative_history():
    return database.get_recent_narratives(limit=5)
