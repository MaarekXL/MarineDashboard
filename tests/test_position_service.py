from datetime import datetime, timedelta, timezone

import pytest

from database import MarineDatabase
from models import Position, PositionSource
from positioning import create_manual_position
from services import (
    PositionService,
    PositionUnavailableError,
)


class FakePositionReader:
    def __init__(
        self,
        position: Position | None,
    ) -> None:
        self.position = position

    def read_next_position(
        self,
        max_lines: int = 100,
    ) -> Position | None:
        return self.position


def test_nmea_position_has_priority(
    tmp_path,
) -> None:
    database = MarineDatabase(
        tmp_path / "marine.db"
    )

    service = PositionService(
        database
    )

    gps_position = Position(
        latitude=43.1242,
        longitude=5.9280,
        timestamp=datetime.now(
            timezone.utc
        ),
        source=PositionSource.NMEA,
    )

    reader = FakePositionReader(
        gps_position
    )

    result = service.resolve_position(
        reader=reader
    )

    assert result.source == (
        PositionSource.NMEA
    )

    assert result.latitude == 43.1242

    stored = (
        database
        .get_latest_valid_position()
    )

    assert stored is not None
    assert stored.latitude == 43.1242


def test_fallback_to_last_known(
    tmp_path,
) -> None:
    database = MarineDatabase(
        tmp_path / "marine.db"
    )

    previous = Position(
        latitude=43.10,
        longitude=5.90,
        timestamp=datetime.now(
            timezone.utc
        ),
        source=PositionSource.NMEA,
    )

    database.insert_position(
        previous
    )

    reader = FakePositionReader(
        None
    )

    service = PositionService(
        database
    )

    result = service.resolve_position(
        reader=reader
    )

    assert result.latitude == 43.10

    assert result.source == (
        PositionSource.LAST_KNOWN
    )


def test_fallback_to_manual_position(
    tmp_path,
) -> None:
    database = MarineDatabase(
        tmp_path / "marine.db"
    )

    service = PositionService(
        database
    )

    manual = create_manual_position(
        latitude=43.1242,
        longitude=5.9280,
    )

    result = service.resolve_position(
        reader=None,
        manual_position=manual,
    )

    assert result.source == (
        PositionSource.MANUAL
    )

    assert result.latitude == 43.1242
    assert result.longitude == 5.9280


def test_no_position_available(
    tmp_path,
) -> None:
    database = MarineDatabase(
        tmp_path / "marine.db"
    )

    service = PositionService(
        database
    )

    with pytest.raises(
        PositionUnavailableError
    ):
        service.resolve_position()


def test_stale_position_is_rejected(
    tmp_path,
) -> None:
    database = MarineDatabase(
        tmp_path / "marine.db"
    )

    old_position = Position(
        latitude=43.1242,
        longitude=5.9280,
        timestamp=(
            datetime.now(timezone.utc)
            - timedelta(hours=2)
        ),
        source=PositionSource.NMEA,
    )

    database.insert_position(
        old_position
    )

    service = PositionService(
        database,
        max_cached_age=timedelta(
            minutes=30
        ),
    )

    with pytest.raises(
        PositionUnavailableError
    ):
        service.resolve_position()


def test_stale_position_falls_back_to_manual(
    tmp_path,
) -> None:
    database = MarineDatabase(
        tmp_path / "marine.db"
    )

    old_position = Position(
        latitude=43.1242,
        longitude=5.9280,
        timestamp=(
            datetime.now(timezone.utc)
            - timedelta(hours=2)
        ),
        source=PositionSource.NMEA,
    )

    database.insert_position(
        old_position
    )

    manual = create_manual_position(
        latitude=43.10,
        longitude=5.90,
    )

    service = PositionService(
        database,
        max_cached_age=timedelta(
            minutes=30
        ),
    )

    result = service.resolve_position(
        manual_position=manual
    )

    assert result.source == (
        PositionSource.MANUAL
    )

    assert result.latitude == 43.10
    assert result.longitude == 5.90