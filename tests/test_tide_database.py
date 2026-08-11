from datetime import datetime, timedelta, timezone

from database import MarineDatabase
from models import (
    TideEvent,
    TideEventType,
    TidePoint,
)


def make_day() -> datetime:
    return datetime(
        2026,
        8,
        11,
        tzinfo=timezone.utc,
    )


def test_insert_tide_points(
    tmp_path,
) -> None:
    database = MarineDatabase(
        tmp_path / "marine.db"
    )

    start = make_day()

    points = [
        TidePoint(
            timestamp=start,
            height_m=0.42,
            station_id="TOULON",
        ),
        TidePoint(
            timestamp=(
                start
                + timedelta(minutes=10)
            ),
            height_m=0.45,
            station_id="TOULON",
        ),
    ]

    count = database.upsert_tide_points(
        points
    )

    assert count == 2


def test_get_tide_points(
    tmp_path,
) -> None:
    database = MarineDatabase(
        tmp_path / "marine.db"
    )

    start = make_day()
    end = start + timedelta(days=1)

    database.upsert_tide_points(
        [
            TidePoint(
                timestamp=start,
                height_m=0.42,
                station_id="TOULON",
            ),
            TidePoint(
                timestamp=(
                    start
                    + timedelta(minutes=10)
                ),
                height_m=0.45,
                station_id="TOULON",
            ),
        ]
    )

    result = database.get_tide_points(
        "TOULON",
        start,
        end,
    )

    assert len(result) == 2
    assert result[0].height_m == 0.42
    assert result[1].height_m == 0.45


def test_tide_point_upsert(
    tmp_path,
) -> None:
    database = MarineDatabase(
        tmp_path / "marine.db"
    )

    timestamp = make_day()

    database.upsert_tide_points(
        [
            TidePoint(
                timestamp=timestamp,
                height_m=0.42,
                station_id="TOULON",
            )
        ]
    )

    database.upsert_tide_points(
        [
            TidePoint(
                timestamp=timestamp,
                height_m=0.55,
                station_id="TOULON",
            )
        ]
    )

    result = database.get_tide_points(
        "TOULON",
        timestamp,
        timestamp + timedelta(hours=1),
    )

    assert len(result) == 1
    assert result[0].height_m == 0.55


def test_insert_tide_events(
    tmp_path,
) -> None:
    database = MarineDatabase(
        tmp_path / "marine.db"
    )

    start = make_day()

    events = [
        TideEvent(
            timestamp=(
                start
                + timedelta(hours=4)
            ),
            event_type=TideEventType.HIGH,
            height_m=0.82,
            station_id="TOULON",
            coefficient=76,
        ),
        TideEvent(
            timestamp=(
                start
                + timedelta(hours=10)
            ),
            event_type=TideEventType.LOW,
            height_m=0.31,
            station_id="TOULON",
        ),
    ]

    database.upsert_tide_events(
        events
    )

    result = database.get_tide_events(
        "TOULON",
        start,
        start + timedelta(days=1),
    )

    assert len(result) == 2

    assert result[0].event_type == (
        TideEventType.HIGH
    )

    assert result[0].coefficient == 76

    assert result[1].event_type == (
        TideEventType.LOW
    )


def test_clear_tides(
    tmp_path,
) -> None:
    database = MarineDatabase(
        tmp_path / "marine.db"
    )

    start = make_day()
    end = start + timedelta(days=1)

    database.upsert_tide_points(
        [
            TidePoint(
                timestamp=start,
                height_m=0.42,
                station_id="TOULON",
            )
        ]
    )

    database.upsert_tide_events(
        [
            TideEvent(
                timestamp=(
                    start
                    + timedelta(hours=4)
                ),
                event_type=TideEventType.HIGH,
                height_m=0.82,
                station_id="TOULON",
            )
        ]
    )

    database.clear_tides(
        "TOULON",
        start,
        end,
    )

    assert (
        database.get_tide_points(
            "TOULON",
            start,
            end,
        )
        == []
    )

    assert (
        database.get_tide_events(
            "TOULON",
            start,
            end,
        )
        == []
    )


def test_empty_tide_database(
    tmp_path,
) -> None:
    database = MarineDatabase(
        tmp_path / "marine.db"
    )

    start = make_day()

    assert (
        database.get_tide_points(
            "TOULON",
            start,
            start + timedelta(days=1),
        )
        == []
    )

    assert (
        database.get_tide_events(
            "TOULON",
            start,
            start + timedelta(days=1),
        )
        == []
    )