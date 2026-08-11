from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class AlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertCategory(StrEnum):
    WEATHER = "weather"
    WIND = "wind"
    RAIN = "rain"
    TIDE = "tide"
    GPS = "gps"
    DATA = "data"


@dataclass(frozen=True, slots=True)
class Alert:
    category: AlertCategory
    severity: AlertSeverity

    title: str
    message: str

    created_at: datetime

    starts_at: datetime | None = None
    ends_at: datetime | None = None