from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class TideEventType(StrEnum):
    HIGH = "high"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class TideStation:
    station_id: str
    name: str
    latitude: float
    longitude: float
    source: str = "SHOM"


@dataclass(frozen=True, slots=True)
class TidePoint:
    timestamp: datetime
    height_m: float
    station_id: str


@dataclass(frozen=True, slots=True)
class TideEvent:
    timestamp: datetime
    event_type: TideEventType
    height_m: float
    station_id: str

    coefficient: int | None = None