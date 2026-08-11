from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from database import MarineDatabase
from models import (
    TideEvent,
    TideEventType,
    TidePoint,
)


class TideDirection(StrEnum):
    RISING = "rising"
    FALLING = "falling"
    SLACK = "slack"


@dataclass(frozen=True, slots=True)
class TideState:
    target_id: str
    timestamp: datetime

    height_m: float
    direction: TideDirection

    rate_cm_per_hour: float

    previous_point: TidePoint
    next_point: TidePoint

    next_high_tide: TideEvent | None
    next_low_tide: TideEvent | None


class TideDataUnavailableError(RuntimeError):
    """Données insuffisantes pour calculer la marée."""


class TideService:
    def __init__(
        self,
        database: MarineDatabase,
        slack_threshold_cm_per_hour: float = 1.0,
    ) -> None:
        if slack_threshold_cm_per_hour < 0:
            raise ValueError(
                "Le seuil d'étale ne peut pas être négatif."
            )

        self.database = database

        self.slack_threshold_cm_per_hour = (
            slack_threshold_cm_per_hour
        )

    def get_state(
        self,
        target_id: str,
        timestamp: datetime,
    ) -> TideState:
        """
        Calcule l'état de la marée à un instant donné.
        """

        if not target_id:
            raise ValueError(
                "target_id ne peut pas être vide."
            )

        previous_point = (
            self.database.get_tide_point_before(
                target_id,
                timestamp,
            )
        )

        next_point = (
            self.database.get_tide_point_after(
                target_id,
                timestamp,
            )
        )

        if (
            previous_point is None
            or next_point is None
        ):
            raise TideDataUnavailableError(
                "Pas assez de points pour "
                "interpoler la hauteur de marée."
            )

        height = self._interpolate_height(
            timestamp,
            previous_point,
            next_point,
        )

        rate = self._calculate_rate(
            previous_point,
            next_point,
        )

        direction = self._get_direction(
            rate
        )

        next_high = (
            self.database.get_next_tide_event(
                target_id,
                timestamp,
                TideEventType.HIGH,
            )
        )

        next_low = (
            self.database.get_next_tide_event(
                target_id,
                timestamp,
                TideEventType.LOW,
            )
        )

        return TideState(
            target_id=target_id,
            timestamp=timestamp,
            height_m=height,
            direction=direction,
            rate_cm_per_hour=rate,
            previous_point=previous_point,
            next_point=next_point,
            next_high_tide=next_high,
            next_low_tide=next_low,
        )

    @staticmethod
    def _interpolate_height(
        timestamp: datetime,
        previous: TidePoint,
        next_point: TidePoint,
    ) -> float:
        """
        Interpolation linéaire entre deux points
        de hauteur de marée.
        """

        if previous.timestamp == next_point.timestamp:
            return previous.height_m

        total_seconds = (
            next_point.timestamp
            - previous.timestamp
        ).total_seconds()

        if total_seconds <= 0:
            raise TideDataUnavailableError(
                "Ordre temporel des points de marée invalide."
            )

        elapsed_seconds = (
            timestamp
            - previous.timestamp
        ).total_seconds()

        ratio = (
            elapsed_seconds
            / total_seconds
        )

        height = (
            previous.height_m
            + (
                next_point.height_m
                - previous.height_m
            )
            * ratio
        )

        return height

    @staticmethod
    def _calculate_rate(
        previous: TidePoint,
        next_point: TidePoint,
    ) -> float:
        """
        Calcule la variation moyenne du niveau
        entre les deux points, en cm/h.
        """

        elapsed_hours = (
            next_point.timestamp
            - previous.timestamp
        ).total_seconds() / 3600.0

        if elapsed_hours <= 0:
            return 0.0

        difference_cm = (
            next_point.height_m
            - previous.height_m
        ) * 100.0

        return (
            difference_cm
            / elapsed_hours
        )

    def _get_direction(
        self,
        rate_cm_per_hour: float,
    ) -> TideDirection:
        """
        Détermine si la marée est montante,
        descendante ou proche de l'étale.
        """

        if (
            abs(rate_cm_per_hour)
            <= self.slack_threshold_cm_per_hour
        ):
            return TideDirection.SLACK

        if rate_cm_per_hour > 0:
            return TideDirection.RISING

        return TideDirection.FALLING