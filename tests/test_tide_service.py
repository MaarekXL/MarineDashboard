from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest

from database import MarineDatabase

from models import (
    TideEvent,
    TideEventType,
    TidePoint,
)

from services import (
    TideDataUnavailableError,
    TideDirection,
    TideService,
)


def make_start() -> datetime:
    return datetime(
        2026,
        8,
        11,
        12,
        0,
        tzinfo=timezone.utc,
    )


def prepare_database(
    tmp_path,
) -> tuple[
    MarineDatabase,
    datetime,
]:
    database = MarineDatabase(
        tmp_path / "marine.db"
    )

    start = make_start()

    database.upsert_tide_points(
        [
            TidePoint(
                timestamp=start,
                height_m=0.40,
                station_id="TOULON",
            ),
            TidePoint(
                timestamp=(
                    start
                    + timedelta(minutes=10)
                ),
                height_m=0.50,
                station_id="TOULON",
            ),
        ]
    )

    return database, start


def test_interpolated_height(
    tmp_path,
) -> None:
    database, start = prepare_database(
        tmp_path
    )

    service = TideService(
        database
    )

    state = service.get_state(
        "TOULON",
        start + timedelta(minutes=5),
    )

    assert state.height_m == pytest.approx(
        0.45
    )


def test_rising_tide(
    tmp_path,
) -> None:
    database, start = prepare_database(
        tmp_path
    )

    service = TideService(
        database
    )

    state = service.get_state(
        "TOULON",
        start + timedelta(minutes=5),
    )

    assert state.direction == (
        TideDirection.RISING
    )

    assert state.rate_cm_per_hour == (
        pytest.approx(60.0)
    )


def test_falling_tide(
    tmp_path,
) -> None:
    database = MarineDatabase(
        tmp_path / "marine.db"
    )

    start = make_start()

    database.upsert_tide_points(
        [
            TidePoint(
                timestamp=start,
                height_m=0.60,
                station_id="TOULON",
            ),
            TidePoint(
                timestamp=(
                    start
                    + timedelta(minutes=30)
                ),
                height_m=0.40,
                station_id="TOULON",
            ),
        ]
    )

    service = TideService(
        database
    )

    state = service.get_state(
        "TOULON",
        start + timedelta(minutes=15),
    )

    assert state.direction == (
        TideDirection.FALLING
    )

    assert state.rate_cm_per_hour == (
        pytest.approx(-40.0)
    )


def test_slack_tide(
    tmp_path,
) -> None:
    database = MarineDatabase(
        tmp_path / "marine.db"
    )

    start = make_start()

    database.upsert_tide_points(
        [
            TidePoint(
                timestamp=start,
                height_m=0.50,
                station_id="TOULON",
            ),
            TidePoint(
                timestamp=(
                    start
                    + timedelta(hours=1)
                ),
                height_m=0.505,
                station_id="TOULON",
            ),
        ]
    )

    service = TideService(
        database,
        slack_threshold_cm_per_hour=1.0,
    )

    state = service.get_state(
        "TOULON",
        start + timedelta(minutes=30),
    )

    assert state.direction == (
        TideDirection.SLACK
    )


def test_next_tide_events(
    tmp_path,
) -> None:
    database, start = prepare_database(
        tmp_path
    )

    database.upsert_tide_events(
        [
            TideEvent(
                timestamp=(
                    start
                    + timedelta(hours=2)
                ),
                event_type=TideEventType.HIGH,
                height_m=0.82,
                station_id="TOULON",
                coefficient=76,
            ),
            TideEvent(
                timestamp=(
                    start
                    + timedelta(hours=8)
                ),
                event_type=TideEventType.LOW,
                height_m=0.31,
                station_id="TOULON",
            ),
        ]
    )

    service = TideService(
        database
    )

    state = service.get_state(
        "TOULON",
        start + timedelta(minutes=5),
    )

    assert state.next_high_tide is not None
    assert state.next_low_tide is not None

    assert (
        state.next_high_tide.height_m
        == 0.82
    )

    assert (
        state.next_high_tide.coefficient
        == 76
    )


def test_missing_tide_points(
    tmp_path,
) -> None:
    database = MarineDatabase(
        tmp_path / "marine.db"
    )

    service = TideService(
        database
    )

    with pytest.raises(
        TideDataUnavailableError
    ):
        service.get_state(
            "TOULON",
            make_start(),
        )