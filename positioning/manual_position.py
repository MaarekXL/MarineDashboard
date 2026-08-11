from datetime import datetime, timezone

from models import Position, PositionSource


def create_manual_position(
    latitude: float,
    longitude: float,
) -> Position:
    """
    Crée une position définie manuellement
    par l'utilisateur.
    """
    return Position(
        latitude=latitude,
        longitude=longitude,
        timestamp=datetime.now(
            timezone.utc
        ),
        source=PositionSource.MANUAL,
        valid=True,
    )