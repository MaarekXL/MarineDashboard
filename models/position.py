from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class PositionSource(StrEnum):
    NMEA = "nmea"
    MANUAL = "manual"
    LAST_KNOWN = "last_known"


@dataclass(frozen=True, slots=True)
class Position:
    latitude: float
    longitude: float
    timestamp: datetime
    source: PositionSource

    valid: bool = True
    speed_knots: float | None = None
    course_deg: float | None = None
    altitude_m: float | None = None

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError("Latitude invalide.")

        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError("Longitude invalide.")

        if self.speed_knots is not None and self.speed_knots < 0:
            raise ValueError("La vitesse ne peut pas être négative.")

        if self.course_deg is not None:
            if not 0.0 <= self.course_deg < 360.0:
                raise ValueError("Le cap doit être compris entre 0 et 360°.")