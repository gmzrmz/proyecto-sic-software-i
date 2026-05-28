from datetime import datetime, timezone, timedelta

import config
import simulator
from db import database

_WINDOW_LABEL = {1: "la ultima hora", 3: "las ultimas 3 horas", 24: "las ultimas 24 horas"}
_BOGOTA = timezone(timedelta(hours=-5))


def _bogota_time(ts: str) -> str:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(_BOGOTA)
    h, m = dt.hour, dt.minute
    suffix = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d} {suffix}"


def _cpu_level(value: float) -> str:
    if value >= config.THRESHOLD_CPU:
        return "por encima del umbral critico"
    if value >= config.THRESHOLD_CPU - 10:
        return "elevado"
    return "normal"


def _ram_level(value: float) -> str:
    if value >= config.THRESHOLD_RAM:
        return "por encima del umbral critico"
    if value >= config.THRESHOLD_RAM - 10:
        return "elevado"
    return "normal"


def _net_desc(max_in_mb: float, max_out_mb: float) -> str:
    if max_in_mb > 10 and max_out_mb < 2:
        return (f"ALERTA DE FLOOD: entrada muy alta ({max_in_mb:.1f} MB/s) con salida casi nula, "
                f"patron tipico de DDoS o flood")
    if max_out_mb > 10:
        return f"salida intensa ({max_out_mb:.1f} MB/s), servidor respondio alto volumen de peticiones"
    if max_in_mb > 1 or max_out_mb > 1:
        return f"trafico activo durante el periodo (entrada {max_in_mb:.2f} MB/s, salida {max_out_mb:.2f} MB/s)"
    return f"trafico bajo durante todo el periodo (entrada {max_in_mb*1000:.0f} KB/s, salida {max_out_mb*1000:.0f} KB/s)"


def _trend_desc(pct: float) -> str:
    if abs(pct) < 5:
        return "estable respecto al historico"
    if pct > 20:
        return "muy por encima del historico (subida pronunciada)"
    if pct > 0:
        return "ligeramente por encima del historico"
    if pct < -20:
        return "muy por debajo del historico (caida notable)"
    return "ligeramente por debajo del historico"


def build_context(recent: list, hours: int = 1) -> str:
    if not recent:
        return ""

    avg_cpu  = sum(m["cpu_pct"] for m in recent) / len(recent)
    avg_ram  = sum(m["ram_pct"] for m in recent) / len(recent)

    peak_cpu_m = max(recent, key=lambda m: m["cpu_pct"])
    peak_ram_m = max(recent, key=lambda m: m["ram_pct"])
    peak_cpu   = peak_cpu_m["cpu_pct"]
    peak_ram   = peak_ram_m["ram_pct"]
    peak_cpu_t = _bogota_time(peak_cpu_m["timestamp"])
    peak_ram_t = _bogota_time(peak_ram_m["timestamp"])

    max_net_in  = max(m["net_bytes_in"]  for m in recent) / 1_000_000
    max_net_out = max(m["net_bytes_out"] for m in recent) / 1_000_000

    current_hour = datetime.now(timezone.utc).hour
    week_data    = database.get_metrics_by_hours(24 * 7)
    same_hour    = [m for m in week_data if int(m["timestamp"][11:13]) == current_hour]

    if same_hour:
        hist_cpu = sum(m["cpu_pct"] for m in same_hour) / len(same_hour)
        hist_ram = sum(m["ram_pct"] for m in same_hour) / len(same_hour)
    else:
        hist_cpu = avg_cpu
        hist_ram = avg_ram

    cpu_trend = ((avg_cpu - hist_cpu) / hist_cpu * 100) if hist_cpu else 0
    ram_trend = ((avg_ram - hist_ram) / hist_ram * 100) if hist_ram else 0

    avg_cpu_level  = _cpu_level(avg_cpu)
    avg_ram_level  = _ram_level(avg_ram)
    peak_cpu_level = _cpu_level(peak_cpu)
    peak_ram_level = _ram_level(peak_ram)

    any_peak_significant = (
        peak_cpu >= config.THRESHOLD_CPU - 25 or
        peak_ram >= config.THRESHOLD_RAM - 25 or
        cpu_trend > 15 or
        ram_trend > 15
    )

    flood = max_net_in > 10 and max_net_out < 2

    description = database.get_setting("instance_description") or getattr(config, "INSTANCE_DESCRIPTION", "")

    window = _WINDOW_LABEL.get(hours, f"las ultimas {hours} horas")

    return (
        f"Eres un ingeniero senior de AWS. Escribe un diagnostico tecnico en espanol.\n\n"
        f"INSTANCIA: {simulator.INSTANCE['label']} | Periodo: {window}\n"
        + (f"CONTEXTO DE NEGOCIO (usa esto para explicar los picos con causas reales del negocio): {description}\n\n" if description else "\n")
        +
        f"METRICAS (razona sobre esto, no lo copies literalmente):\n"
        f"- CPU: promedio {avg_cpu:.1f}% ({avg_cpu_level}) | pico {peak_cpu:.1f}% ({peak_cpu_level}) a las {peak_cpu_t} | tendencia {_trend_desc(cpu_trend)}\n"
        f"- RAM: promedio {avg_ram:.1f}% ({avg_ram_level}) | pico {peak_ram:.1f}% ({peak_ram_level}) a las {peak_ram_t} | tendencia {_trend_desc(ram_trend)}\n"
        f"- Red maxima en el periodo: {_net_desc(max_net_in, max_net_out)}\n\n"
        f"ESCRIBE exactamente 1 oracion descriptiva de prosa corrida, sin titulos ni listas:\n"
        + (
            f"- Describe el pico de CPU o RAM mas alto, menciona la hora exacta "
            f"tal como aparece en los datos ({peak_cpu_t} o {peak_ram_t}), y explica brevemente la causa "
            f"usando el contexto de negocio (parafraseado, no copiado textual). "
            f"No menciones la red ni hagas recomendaciones.\n"
            if any_peak_significant else
            f"- Indica que CPU y RAM se mantuvieron en niveles normales durante {window}. "
            f"Puedes mencionar que el valor mas alto se registro a las {peak_cpu_t} pero sin calificarlo "
            f"como pico significativo. NO menciones campanas, descuentos ni eventos de negocio. "
            f"No menciones la red ni hagas recomendaciones.\n"
        )
        +
        f"REGLAS: usa las horas exactamente como aparecen en los datos (formato X:XX AM/PM, sin convertirlas). "
        f"No hagas recomendaciones ni menciones servicios AWS. "
        f"No uses 'nuestro'/'nuestra', no inventes numeros, no uses asteriscos ni bullets, exactamente 1 oracion."
    )


def build_recommendation(recent: list) -> str:
    if not recent:
        return ""

    avg_cpu  = sum(m["cpu_pct"] for m in recent) / len(recent)
    avg_ram  = sum(m["ram_pct"] for m in recent) / len(recent)
    peak_cpu = max(m["cpu_pct"] for m in recent)
    peak_ram = max(m["ram_pct"] for m in recent)
    max_net_in  = max(m["net_bytes_in"]  for m in recent) / 1_000_000
    max_net_out = max(m["net_bytes_out"] for m in recent) / 1_000_000

    current_hour = datetime.now(timezone.utc).hour
    week_data    = database.get_metrics_by_hours(24 * 7)
    same_hour    = [m for m in week_data if int(m["timestamp"][11:13]) == current_hour]
    if same_hour:
        hist_cpu = sum(m["cpu_pct"] for m in same_hour) / len(same_hour)
        hist_ram = sum(m["ram_pct"] for m in same_hour) / len(same_hour)
    else:
        hist_cpu = avg_cpu
        hist_ram = avg_ram

    cpu_trend = ((avg_cpu - hist_cpu) / hist_cpu * 100) if hist_cpu else 0
    ram_trend = ((avg_ram - hist_ram) / hist_ram * 100) if hist_ram else 0

    recs = []

    cpu_high = peak_cpu >= config.THRESHOLD_CPU - 15 or cpu_trend > 20
    ram_high = peak_ram >= config.THRESHOLD_RAM - 15 or ram_trend > 20
    flood    = max_net_in > 10 and max_net_out < 2

    if cpu_high:
        recs.append("Auto Scaling Group y Balanceador de carga ALB para distribuir la carga entre instancias")
    if ram_high:
        recs.append("ElastiCache Redis para reducir la presion sobre RDS PostgreSQL")
    if cpu_high and not ram_high:
        recs.append("AWS X-Ray para identificar los endpoints con mayor tiempo de respuesta")
    if flood:
        recs.append("AWS WAF y AWS Shield para mitigar el trafico malicioso entrante")
    if not recs and (peak_cpu >= config.THRESHOLD_CPU - 25 or peak_ram >= config.THRESHOLD_RAM - 25):
        recs.append("Alarmas de CloudWatch con notificaciones via Amazon SNS para alertar al equipo ante proximos picos")

    if not recs:
        return ""

    return "Ante estos picos, se recomienda activar " + ", y ".join(recs) + "."
