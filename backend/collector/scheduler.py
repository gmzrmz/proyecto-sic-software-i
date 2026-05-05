from typing import Callable, Optional

from apscheduler.schedulers.background import BackgroundScheduler

import config

_scheduler: Optional[BackgroundScheduler] = None


def start(collect_fn: Callable, narrative_fn: Optional[Callable] = None) -> None:
    global _scheduler
    _scheduler = BackgroundScheduler(timezone="UTC")

    _scheduler.add_job(
        collect_fn,
        trigger="interval",
        minutes=config.COLLECT_INTERVAL_MINUTES,
        id="collect_metrics",
        max_instances=1,
        coalesce=True,
    )

    if narrative_fn is not None:
        _scheduler.add_job(
            narrative_fn,
            trigger="interval",
            minutes=config.NARRATIVE_INTERVAL_MINUTES,
            id="generate_narrative",
            max_instances=1,
            coalesce=True,
        )

    _scheduler.start()


def stop() -> None:
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)


def is_running() -> bool:
    return bool(_scheduler and _scheduler.running)
