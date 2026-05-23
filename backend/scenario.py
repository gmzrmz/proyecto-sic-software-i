import random
from datetime import datetime, timedelta, timezone

from db import database


def generate_scenario(instance: str) -> int:
    now   = datetime.now(timezone.utc)
    start = now - timedelta(hours=24)

    spikes = _plan_spikes(start, now)

    rows    = []
    step    = timedelta(minutes=5)
    current = start

    while current <= now:
        cpu, ram, net_in, net_out = _baseline(current)
        for spike in spikes:
            cpu, ram = _apply_spike(current, spike, cpu, ram)
        rows.append((
            instance,
            current.strftime("%Y-%m-%dT%H:%M:%SZ"),
            round(min(max(cpu, 1.0), 99.0), 2),
            round(min(max(ram, 1.0), 99.0), 2),
            max(0, net_in),
            max(0, net_out),
        ))
        current += step

    database.insert_metrics_batch(rows)
    return len(rows)


def _plan_spikes(start: datetime, end: datetime) -> list:
    num_spikes = random.randint(1, 3)
    window_h   = 24 / num_spikes
    spikes     = []

    for i in range(num_spikes):
        # Cada pico cae dentro de su ventana temporal
        w_start = start + timedelta(hours=i * window_h + 0.5)
        w_end   = start + timedelta(hours=(i + 1) * window_h - 0.5)
        center  = w_start + timedelta(
            seconds=random.uniform(0, (w_end - w_start).total_seconds())
        )

        duration_min = random.choice([15, 30, 45, 60, 90, 120, 180])
        half         = timedelta(minutes=duration_min / 2)

        severity   = random.choices(["warning", "critical"], weights=[55, 45])[0]
        spike_type = random.choices(["cpu", "ram", "both"],  weights=[35, 20, 45])[0]

        if severity == "critical":
            cpu_peak = random.uniform(88, 98)
            ram_peak = random.uniform(82, 97)
        else:
            cpu_peak = random.uniform(74, 87)
            ram_peak = random.uniform(70, 83)

        spikes.append({
            "start":    center - half,
            "end":      center + half,
            "cpu_peak": cpu_peak,
            "ram_peak": ram_peak,
            "type":     spike_type,
        })

    return spikes


def _baseline(ts: datetime) -> tuple:
    h = ts.hour
    if 8 <= h < 17:                          # horario de negocio
        cpu     = random.gauss(58, 9)
        ram     = random.gauss(62, 7)
        net_in  = int(random.uniform(700_000, 4_000_000))
        net_out = int(random.uniform(280_000, 1_600_000))
    elif 17 <= h < 21:                       # tarde / descenso
        cpu     = random.gauss(36, 7)
        ram     = random.gauss(47, 6)
        net_in  = int(random.uniform(180_000, 1_200_000))
        net_out = int(random.uniform(70_000,  480_000))
    else:                                    # nocturno
        cpu     = random.gauss(13, 4)
        ram     = random.gauss(27, 5)
        net_in  = int(random.uniform(25_000,  220_000))
        net_out = int(random.uniform(8_000,   90_000))
    return cpu, ram, net_in, net_out


def _apply_spike(ts: datetime, spike: dict, cpu: float, ram: float) -> tuple:
    if ts <= spike["start"] or ts >= spike["end"]:
        return cpu, ram

    duration = (spike["end"] - spike["start"]).total_seconds()
    elapsed  = (ts - spike["start"]).total_seconds()
    ramp     = min(duration * 0.28, 18 * 60)  # rampa suave, máximo 18 min

    if elapsed < ramp:
        factor = elapsed / ramp
    elif elapsed > duration - ramp:
        factor = (duration - elapsed) / ramp
    else:
        factor = 1.0
    factor = max(0.0, min(1.0, factor))

    if spike["type"] in ("cpu", "both"):
        cpu = cpu + (spike["cpu_peak"] - cpu) * factor
    if spike["type"] in ("ram", "both"):
        ram = ram + (spike["ram_peak"] - ram) * factor

    return cpu, ram
