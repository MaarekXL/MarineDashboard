from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class WeatherPoint:
    timestamp: datetime

    temperature_c: float | None = None
    feels_like_c: float | None = None

    pressure_hpa: float | None = None
    humidity_percent: float | None = None

    wind_speed_kmh: float | None = None
    wind_gust_kmh: float | None = None
    wind_direction_deg: float | None = None

    precipitation_probability_percent: float | None = None
    precipitation_mm: float | None = None

    cloud_cover_percent: float | None = None

    def __post_init__(self) -> None:
        self._check_percent(
            self.humidity_percent,
            "Humidité",
        )

        self._check_percent(
            self.precipitation_probability_percent,
            "Probabilité de précipitation",
        )

        self._check_percent(
            self.cloud_cover_percent,
            "Nébulosité",
        )

        if self.wind_speed_kmh is not None and self.wind_speed_kmh < 0:
            raise ValueError("La vitesse du vent ne peut pas être négative.")

        if self.wind_gust_kmh is not None and self.wind_gust_kmh < 0:
            raise ValueError("La vitesse des rafales ne peut pas être négative.")

        if self.wind_direction_deg is not None:
            if not 0.0 <= self.wind_direction_deg < 360.0:
                raise ValueError(
                    "La direction du vent doit être comprise entre 0 et 360°."
                )

    @staticmethod
    def _check_percent(value: float | None, name: str) -> None:
        if value is not None and not 0.0 <= value <= 100.0:
            raise ValueError(f"{name} invalide : {value}")