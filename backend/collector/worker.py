import logging
from datetime import datetime, timezone

import config
import simulator
from db import database
from collector.sources.base import MetricSource

logger = logging.getLogger(__name__)

_source: MetricSource | None = None


def _get_source() -> MetricSource:
    global _source
    if _source is None:
        _source = _build_source()
    return _source


def _build_source() -> MetricSource:
    if config.DATA_SOURCE == "synthetic":
        from collector.sources.synthetic import SyntheticSource
        return SyntheticSource()
    # Extension point: add "cloudwatch", "prometheus", etc.
    raise ValueError(f"DATA_SOURCE desconocido: {config.DATA_SOURCE!r}")


def collect_and_store() -> None:
    try:
        reading = _get_source().collect()
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        database.insert_metric(
            instance=simulator.INSTANCE["id"],
            timestamp=ts,
            cpu_pct=reading.cpu_pct,
            ram_pct=reading.ram_pct,
            net_bytes_in=reading.net_bytes_in,
            net_bytes_out=reading.net_bytes_out,
        )
        logger.info(
            "metric_collected instance=%s cpu=%.2f ram=%.2f",
            simulator.INSTANCE["label"], reading.cpu_pct, reading.ram_pct,
        )
    except Exception:
        logger.exception("collect_error - ciclo siguiente no se ve afectado")
