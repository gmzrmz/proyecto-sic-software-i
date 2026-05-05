import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from db import database
from collector import scheduler, worker
from api import metrics as metrics_router

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","module":"%(module)s","msg":"%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    scheduler.start(collect_fn=worker.collect_and_store)
    yield
    scheduler.stop()


app = FastAPI(
    title="CloudSense API",
    description="Plataforma de monitoreo de infraestructura AWS con narrativas en lenguaje natural.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(metrics_router.router)


@app.get("/health", tags=["sistema"], summary="Estado operativo del sistema")
def health():
    return {
        "api_status": "OK",
        "scheduler_status": "OK" if scheduler.is_running() else "DOWN",
    }
