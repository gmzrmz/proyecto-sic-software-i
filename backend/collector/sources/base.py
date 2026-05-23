from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class MetricReading:
    cpu_pct: float
    ram_pct: float
    net_bytes_in: int
    net_bytes_out: int


class MetricSource(ABC):
    @abstractmethod
    def collect(self) -> MetricReading: ...
