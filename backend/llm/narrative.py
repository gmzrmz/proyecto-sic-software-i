import logging
import time
from datetime import datetime, timezone

import httpx

import config
from db import database
from llm.context import build_context

logger = logging.getLogger(__name__)


def generate_and_store() -> None:
    recent = database.get_metrics_by_hours(3)
    context = build_context(recent)
    if not context:
        logger.warning("narrative_skip - sin metricas disponibles")
        return

    text = _call_with_retry(context)
    if not text:
        return

    level = _classify(recent)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    database.insert_narrative(timestamp=ts, text=text, level=level)
    logger.info("narrative_stored level=%s words=%d", level, len(text.split()))


def _call_with_retry(prompt: str, attempts: int = 2) -> str:
    for attempt in range(1, attempts + 1):
        try:
            return _call_llm(prompt)
        except Exception as exc:
            logger.warning("narrative_attempt_%d_failed: %s", attempt, exc)
            if attempt < attempts:
                time.sleep(3)
    logger.error("narrative_failed - todos los intentos agotados")
    return ""


def _call_llm(prompt: str) -> str:
    if config.LLM_PROVIDER == "ollama":
        resp = httpx.post(
            f"{config.LLM_BASE_URL}/api/generate",
            json={"model": config.LLM_MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()

    # OpenAI-compatible: openai, anthropic, openrouter
    resp = httpx.post(
        f"{config.LLM_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {config.LLM_API_KEY}"},
        json={
            "model": config.LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _classify(recent: list) -> str:
    if not recent:
        return "normal"
    avg_cpu = sum(m["cpu_pct"] for m in recent) / len(recent)
    avg_ram = sum(m["ram_pct"] for m in recent) / len(recent)
    if avg_cpu >= config.THRESHOLD_CPU or avg_ram >= config.THRESHOLD_RAM:
        return "critico"
    if avg_cpu >= config.THRESHOLD_CPU - 10 or avg_ram >= config.THRESHOLD_RAM - 10:
        return "atencion"
    return "normal"
