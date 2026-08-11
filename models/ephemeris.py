from dataclasses import dataclass
from datetime import date, datetime, timedelta


@dataclass(frozen=True, slots=True)
class Ephemeris:
    date: date

    sunrise: datetime | None = None
    sunset: datetime | None = None

    civil_dawn: datetime | None = None
    civil_dusk: datetime | None = None

    nautical_dawn: datetime | None = None
    nautical_dusk: datetime | None = None

    moonrise: datetime | None = None
    moonset: datetime | None = None

    moon_phase: float | None = None

    day_length: timedelta | None = None

    def __post_init__(self) -> None:
        if self.moon_phase is not None:
            if not 0.0 <= self.moon_phase <= 1.0:
                raise ValueError(
                    "La phase lunaire doit être comprise entre 0 et 1."
                )