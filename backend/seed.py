import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).parent))

from db import database
from collector.sources.synthetic import _generate
import simulator

logger = logging.getLogger(__name__)


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
            instance=simulator.INSTANCE["id"],
            timestamp=ts,
            cpu_pct=reading.cpu_pct,
            ram_pct=reading.ram_pct,
            net_bytes_in=reading.net_bytes_in,
            net_bytes_out=reading.net_bytes_out,
        )
        current += step
        count += 1

    print(f"Seed completado: {count} registros insertados ({14} dias de historial).")


def fill_gaps() -> None:
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=24)

    existing = database.get_metrics_by_hours(24)
    existing_ts = {m["timestamp"] for m in existing}

    step = timedelta(minutes=5)
    current = start
    count = 0
    while current <= now:
        ts = current.strftime("%Y-%m-%dT%H:%M:%SZ")
        if ts not in existing_ts:
            reading = _generate(current)
            database.insert_metric(
                instance=simulator.INSTANCE["id"],
                timestamp=ts,
                cpu_pct=reading.cpu_pct,
                ram_pct=reading.ram_pct,
                net_bytes_in=reading.net_bytes_in,
                net_bytes_out=reading.net_bytes_out,
            )
            count += 1
        current += step

    if count:
        logger.info("fill_gaps: %d registros insertados", count)


if __name__ == "__main__":
    seed()
