"""Pobla la BD con 14 días de datos sintéticos al primer despliegue.

Uso:
    cd backend
    py seed.py
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).parent))

from db import database
from collector.sources.synthetic import _generate
import config


def seed() -> None:
    database.init_db()

    if database.get_latest_metric() is not None:
        print("La base de datos ya contiene datos. Seed omitido.")
        return

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=14)
    step = timedelta(minutes=5)

    current = start
    count = 0
    while current <= now:
        reading = _generate(current)
        ts = current.strftime("%Y-%m-%dT%H:%M:%SZ")
        database.insert_metric(
            instance=config.INSTANCE_NAME,
            timestamp=ts,
            cpu_pct=reading.cpu_pct,
            ram_pct=reading.ram_pct,
            net_bytes_in=reading.net_bytes_in,
            net_bytes_out=reading.net_bytes_out,
        )
        current += step
        count += 1

    print(f"Seed completado: {count} registros insertados ({14} días de historial).")


if __name__ == "__main__":
    seed()
