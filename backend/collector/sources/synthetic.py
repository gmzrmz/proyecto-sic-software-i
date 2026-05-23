import random
from datetime import datetime

import simulator
from .base import MetricReading, MetricSource


class SyntheticSource(MetricSource):
    def collect(self) -> MetricReading:
        return _generate(datetime.utcnow())


def _generate(ts: datetime) -> MetricReading:
    mode_cfg = simulator.MODES.get(simulator.mode)

    if simulator.mode != "normal" and mode_cfg:
        cpu_min, cpu_max = mode_cfg["cpu"]
        ram_min, ram_max = mode_cfg["ram"]
        cpu = random.uniform(cpu_min, cpu_max)
        ram = random.uniform(ram_min, ram_max)
        ni_min, ni_max = mode_cfg["net_in"]
        no_min, no_max = mode_cfg["net_out"]
        net_in  = int(random.uniform(ni_min, ni_max))
        net_out = int(random.uniform(no_min, no_max))
    else:
        is_business = 8 <= ts.hour < 17
        if is_business:
            cpu = random.uniform(50.0, 85.0)
            ram = random.uniform(55.0, 80.0)
            net_in  = int(random.uniform(500_000, 5_000_000))
            net_out = int(random.uniform(200_000, 2_000_000))
        else:
            cpu = random.uniform(20.0, 45.0)
            ram = random.uniform(30.0, 55.0)
            net_in  = int(random.uniform(50_000, 500_000))
            net_out = int(random.uniform(20_000, 200_000))

        if random.random() < 0.05:
            cpu = min(cpu * random.uniform(1.2, 1.5), 99.0)

    return MetricReading(
        cpu_pct=round(cpu, 2),
        ram_pct=round(ram, 2),
        net_bytes_in=net_in,
        net_bytes_out=net_out,
    )
