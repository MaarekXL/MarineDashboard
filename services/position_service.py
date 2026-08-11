from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Protocol

from database import MarineDatabase
from models import Position, PositionSource


class PositionReader(Protocol):
    """Interface minimale attendue d'une source GPS."""

    def read_next_position(
        self,
        max_lines: int = 100,
    ) -> Position | None:
        ...


class PositionUnavailableError(RuntimeError):
    """Aucune position exploitable n'est disponible."""


class PositionService:
    def __init__(
        self,
        database: MarineDatabase,
        max_cached_age: timedelta = timedelta(minutes=30),
    ) -> None:
        if max_cached_age <= timedelta(0):
            raise ValueError(
                "max_cached_age doit être supérieur à zéro."
            )

        self.database = database
        self.max_cached_age = max_cached_age

    def resolve_position(
        self,
        reader: PositionReader | None = None,
        manual_position: Position | None = None,
        max_lines: int = 100,
    ) -> Position:
        """
        Résout la meilleure position disponible.

        Priorités :
        1. GPS / NMEA valide
        2. dernière position valide encore récente
        3. position manuelle
        """

        # 1. GPS / NMEA
        if reader is not None:
            position = reader.read_next_position(
                max_lines=max_lines
            )

            if position is not None and position.valid:
                self.database.insert_position(
                    position
                )

                return position

        # 2. Dernière position valide
        cached_position = (
            self.database.get_latest_valid_position()
        )

        if (
            cached_position is not None
            and self._is_fresh(cached_position)
        ):
            return replace(
                cached_position,
                source=PositionSource.LAST_KNOWN,
            )

        # 3. Position manuelle
        if manual_position is not None:
            if not manual_position.valid:
                raise PositionUnavailableError(
                    "La position manuelle est invalide."
                )

            self.database.insert_position(
                manual_position
            )

            return manual_position

        if cached_position is not None:
            raise PositionUnavailableError(
                "La dernière position GPS est périmée "
                "et aucune position manuelle n'est disponible."
            )

        raise PositionUnavailableError(
            "Aucune position disponible : "
            "GPS absent, cache vide et "
            "aucune position manuelle définie."
        )

    def _is_fresh(
        self,
        position: Position,
    ) -> bool:
        timestamp = position.timestamp

        # Sécurité pour d'anciennes données sans timezone.
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(
                tzinfo=timezone.utc
            )

        now = datetime.now(
            timezone.utc
        )

        age = (
            now
            - timestamp.astimezone(timezone.utc)
        )

        # Une légère avance de l'horloge GPS
        # ne rend pas la position invalide.
        if age < timedelta(0):
            return True

        return age <= self.max_cached_age