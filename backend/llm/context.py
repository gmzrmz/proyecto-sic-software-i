from datetime import datetime, timezone

import config
import simulator
from db import database


def build_context(recent: list) -> str:
    if not recent:
        return ""

    avg_cpu_3h = sum(m["cpu_pct"] for m in recent) / len(recent)
    avg_ram_3h = sum(m["ram_pct"] for m in recent) / len(recent)
    latest = recent[-1]

    current_hour = datetime.now(timezone.utc).hour
    week_data = database.get_metrics_by_hours(24 * 7)
    same_hour = [m for m in week_data if int(m["timestamp"][11:13]) == current_hour]

    if same_hour:
        hist_cpu = sum(m["cpu_pct"] for m in same_hour) / len(same_hour)
        hist_ram = sum(m["ram_pct"] for m in same_hour) / len(same_hour)
    else:
        hist_cpu = avg_cpu_3h
        hist_ram = avg_ram_3h

    cpu_trend = ((avg_cpu_3h - hist_cpu) / hist_cpu * 100) if hist_cpu else 0
    ram_trend = ((avg_ram_3h - hist_ram) / hist_ram * 100) if hist_ram else 0

    return (
        f"Estado actual del servidor '{simulator.INSTANCE['label']}':\n"
        f"- CPU: {latest['cpu_pct']}%"
        f" (promedio 3h: {avg_cpu_3h:.1f}%,"
        f" historico misma hora: {hist_cpu:.1f}%,"
        f" tendencia: {cpu_trend:+.1f}%)\n"
        f"- RAM: {latest['ram_pct']}%"
        f" (promedio 3h: {avg_ram_3h:.1f}%,"
        f" historico misma hora: {hist_ram:.1f}%,"
        f" tendencia: {ram_trend:+.1f}%)\n"
        f"- Red entrada: {latest['net_bytes_in']:,} bytes"
        f" | Red salida: {latest['net_bytes_out']:,} bytes\n"
        f"- Umbrales de alerta: CPU {config.THRESHOLD_CPU}%"
        f" | RAM {config.THRESHOLD_RAM}%\n\n"
        "Genera una narrativa en espanol de entre 60 y 200 palabras que explique "
        "el estado actual del servidor, identifique patrones relevantes y sugiera "
        "al menos una accion concreta."
    )
