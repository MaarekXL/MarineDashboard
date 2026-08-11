from datetime import datetime, timezone

from database import MarineDatabase
from models import Position, PositionSource


def test_database_creation(tmp_path) -> None:
    database_file = (
        tmp_path
        / "test_marine.db"
    )

    database = MarineDatabase(
        database_file
    )

    assert database_file.exists()
    assert database.get_schema_version() == 2


def test_insert_position(tmp_path) -> None:
    database = MarineDatabase(
        tmp_path / "test_marine.db"
    )

    position = Position(
        latitude=43.1242,
        longitude=5.9280,
        timestamp=datetime.now(
            timezone.utc
        ),
        source=PositionSource.MANUAL,
    )

    position_id = database.insert_position(
        position
    )

    assert position_id > 0


def test_get_latest_position(tmp_path) -> None:
    database = MarineDatabase(
        tmp_path / "test_marine.db"
    )

    position = Position(
        latitude=43.1242,
        longitude=5.9280,
        timestamp=datetime.now(
            timezone.utc
        ),
        source=PositionSource.MANUAL,
        speed_knots=4.7,
        course_deg=125.0,
    )

    database.insert_position(
        position
    )

    result = database.get_latest_position()

    assert result is not None

    assert result.latitude == 43.1242
    assert result.longitude == 5.9280

    assert (
        result.source
        == PositionSource.MANUAL
    )

    assert result.speed_knots == 4.7
    assert result.course_deg == 125.0


def test_empty_database_returns_none(
    tmp_path,
) -> None:
    database = MarineDatabase(
        tmp_path / "test_marine.db"
    )

    result = database.get_latest_position()

    assert result is None