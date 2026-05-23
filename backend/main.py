import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import simulator
from db import database
from collector import scheduler, worker
from seed import seed, fill_gaps
from api import metrics as metrics_router
from api import narratives as narratives_router
from api import thresholds as thresholds_router
from api import simulation as simulation_router
from llm import narrative

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","module":"%(module)s","msg":"%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    seed()
    fill_gaps()
    saved = database.get_simulator_state()
    simulator.mode = saved["mode"]
    scheduler.start(
        collect_fn=worker.collect_and_store,
        narrative_fn=narrative.generate_and_store,
    )
    yield
    scheduler.stop()


app = FastAPI(
    title="CloudSense API",
    description="Plataforma de monitoreo de infraestructura AWS con narrativas en lenguaje natural.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(metrics_router.router)
app.include_router(narratives_router.router)
app.include_router(thresholds_router.router)
app.include_router(simulation_router.router)

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

@app.get("/", include_in_schema=False)
def landing():
    return FileResponse(Path(__file__).parent / "static" / "landing.html")

@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(Path(__file__).parent / "static" / "index.html")

@app.get("/simulacion-panel", include_in_schema=False)
def sim_panel():
    return FileResponse(Path(__file__).parent / "static" / "simulacion.html")


@app.get("/health", tags=["sistema"], summary="Estado operativo del sistema")
def health():
    db_ok        = database.check_db()
    scheduler_ok = scheduler.is_running()
    body = {
        "api_status":       "OK",
        "bd_status":        "OK"       if db_ok        else "DEGRADED",
        "scheduler_status": "OK"       if scheduler_ok else "DOWN",
    }
    return JSONResponse(content=body, status_code=200 if (db_ok and scheduler_ok) else 503)
