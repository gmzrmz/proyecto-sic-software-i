import logging
import re
import time
from datetime import datetime, timezone

import httpx

import config
from db import database
from llm.context import build_context, build_recommendation

logger = logging.getLogger(__name__)


def generate_and_store() -> None:
    hours = int(database.get_setting("analysis_hours", "1"))
    recent = database.get_metrics_by_hours(hours)
    context = build_context(recent, hours)
    if not context:
        logger.warning("narrative_skip - sin metricas disponibles")
        return

    text = _call_with_retry(context)
    if not text:
        return

    net = _build_net_sentence(recent)
    rec = build_recommendation(recent)
    text = _truncate_sentences(text, 1) + " " + net
    if rec:
        text += " " + rec

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


def _strip_markdown(text: str) -> str:
    text = re.sub(r'(\w)\*{1,3}', r'\1 ', text)
    text = re.sub(r'\*{1,3}([^*\n]+)\*{1,3}', r'\1', text)
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove plain-text label prefixes like "Diagnóstico Técnico:" or "Análisis:"
    # Only match when the text before the colon contains no digits (avoids stripping "a las 1:03 AM")
    text = re.sub(r'^[A-ZÁÉÍÓÚÑ][a-záéíóúñA-ZÁÉÍÓÚÑ\s]{1,38}:\s*', '', text)
    # Remove bare title lines (no colon) that precede the actual narrative on a new line
    text = re.sub(r'^[A-ZÁÉÍÓÚÑ][a-záéíóúñA-ZÁÉÍÓÚÑ\s]{1,38}\s*\n+', '', text)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


_REC_KEYWORDS = ('se recomienda', 'es fundamental', 'se debe activar', 'se debe implementar',
                  'es necesario', 'es importante activar', 'ante estos picos')


def _build_net_sentence(recent: list) -> str:
    max_in  = max(m["net_bytes_in"]  for m in recent) / 1_000_000
    max_out = max(m["net_bytes_out"] for m in recent) / 1_000_000
    if max_in > 10 and max_out < 2:
        return (f"La red registro una alerta de flood: entrada de {max_in:.1f} MB/s con salida "
                f"casi nula, patron tipico de DDoS o flood de paquetes.")
    if max_out > 10:
        return (f"La red registro una salida intensa de {max_out:.1f} MB/s durante el periodo, "
                f"indicando un alto volumen de respuestas del servidor.")
    if max_in > 1 or max_out > 1:
        return (f"La red registro trafico activo durante el periodo, con entrada maxima de "
                f"{max_in:.2f} MB/s y salida de {max_out:.2f} MB/s.")
    return (f"La red registro trafico bajo durante todo el periodo, con entrada de "
            f"{max_in*1000:.0f} KB/s y salida de {max_out*1000:.0f} KB/s.")


def _truncate_sentences(text: str, max_sentences: int = 2) -> str:
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ])', text)
    descriptive = [s for s in sentences if not any(kw in s.lower() for kw in _REC_KEYWORDS)]
    return ' '.join(descriptive[:max_sentences]).strip()


def _call_llm(prompt: str) -> str:
    if config.LLM_PROVIDER == "ollama":
        resp = httpx.post(
            f"{config.LLM_BASE_URL}/api/generate",
            json={"model": config.LLM_MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return _strip_markdown(resp.json()["response"].strip())

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
    return _strip_markdown(resp.json()["choices"][0]["message"]["content"].strip())


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
