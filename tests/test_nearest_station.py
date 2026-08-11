from datetime import datetime, timezone
import json

import pytest

from models import (
    Position,
    PositionSource,
    TideStation,
)
from positioning import (
    find_nearest_station,
    haversine_distance_km,
    load_station_catalog,
)


def make_position(
    latitude: float,
    longitude: float,
) -> Position:
    return Position(
        latitude=latitude,
        longitude=longitude,
        timestamp=datetime.now(
            timezone.utc
        ),
        source=PositionSource.MANUAL,
    )


def test_haversine_same_position() -> None:
    distance = haversine_distance_km(
        43.0,
        5.0,
        43.0,
        5.0,
    )

    assert distance == pytest.approx(
        0.0
    )


def test_haversine_one_degree_latitude() -> None:
    distance = haversine_distance_km(
        0.0,
        0.0,
        1.0,
        0.0,
    )

    assert distance == pytest.approx(
        111.2,
        abs=0.2,
    )


def test_find_nearest_station() -> None:
    position = make_position(
        43.0,
        5.0,
    )

    stations = [
        TideStation(
            station_id="A",
            name="Station A",
            latitude=43.01,
            longitude=5.01,
        ),
        TideStation(
            station_id="B",
            name="Station B",
            latitude=44.0,
            longitude=6.0,
        ),
    ]

    match = find_nearest_station(
        position,
        stations,
    )

    assert match is not None

    assert (
        match.station.station_id
        == "A"
    )

    assert match.distance_km < 2.0


def test_station_too_far() -> None:
    position = make_position(
        43.0,
        5.0,
    )

    stations = [
        TideStation(
            station_id="FAR",
            name="Station distante",
            latitude=44.0,
            longitude=6.0,
        )
    ]

    match = find_nearest_station(
        position,
        stations,
        max_distance_km=10.0,
    )

    assert match is None


def test_load_station_catalog(
    tmp_path,
) -> None:
    catalog_file = (
        tmp_path / "stations.json"
    )

    catalog = [
        {
            "station_id": "TEST001",
            "name": "Port test",
            "latitude": 43.1,
            "longitude": 5.9,
            "source": "TEST",
        }
    ]

    catalog_file.write_text(
        json.dumps(catalog),
        encoding="utf-8",
    )

    stations = load_station_catalog(
        catalog_file
    )

    assert len(stations) == 1

    assert (
        stations[0].station_id
        == "TEST001"
    )

    assert stations[0].name == (
        "Port test"
    )