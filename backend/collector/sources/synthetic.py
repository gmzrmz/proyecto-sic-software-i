import random
from datetime import datetime

from .base import MetricReading, MetricSource


class SyntheticSource(MetricSource):
    def collect(self) -> MetricReading:
        return _generate(datetime.utcnow())


def _generate(ts: datetime) -> MetricReading:
    """Genera una lectura sintética con patrones de carga realistas.

    Horario laboral (8-17h): CPU 50-85%, RAM 55-80%, red alta.
    Horario nocturno: CPU 20-45%, RAM 30-55%, red baja.
    Spike aleatorio con probabilidad 5%.
    """
    is_business = 8 <= ts.hour < 17

    if is_business:
        cpu = random.uniform(50.0, 85.0)
        ram = random.uniform(55.0, 80.0)
        net_in = int(random.uniform(500_000, 5_000_000))
        net_out = int(random.uniform(200_000, 2_000_000))
    else:
        cpu = random.uniform(20.0, 45.0)
        ram = random.uniform(30.0, 55.0)
        net_in = int(random.uniform(50_000, 500_000))
        net_out = int(random.uniform(20_000, 200_000))

    if random.random() < 0.05:
        cpu = min(cpu * random.uniform(1.2, 1.5), 99.0)

    return MetricReading(
        cpu_pct=round(cpu, 2),
        ram_pct=round(ram, 2),
        net_bytes_in=net_in,
        net_bytes_out=net_out,
    )
