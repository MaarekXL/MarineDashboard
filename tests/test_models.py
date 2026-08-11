from datetime import datetime, timezone

from models import (
    Position,
    PositionSource,
    TideEvent,
    TideEventType,
    WeatherPoint,
)


def test_position() -> None:
    position = Position(
        latitude=43.1242,
        longitude=5.9280,
        timestamp=datetime.now(timezone.utc),
        source=PositionSource.MANUAL,
    )

    assert position.latitude == 43.1242
    assert position.longitude == 5.9280
    assert position.valid is True


def test_weather() -> None:
    weather = WeatherPoint(
        timestamp=datetime.now(timezone.utc),
        temperature_c=27.4,
        humidity_percent=58,
        pressure_hpa=1014,
        wind_speed_kmh=18,
        wind_gust_kmh=31,
        wind_direction_deg=135,
        precipitation_probability_percent=20,
    )

    assert weather.temperature_c == 27.4
    assert weather.wind_gust_kmh == 31


def test_tide_event() -> None:
    tide = TideEvent(
        timestamp=datetime.now(timezone.utc),
        event_type=TideEventType.HIGH,
        height_m=0.82,
        station_id="TOULON",
        coefficient=76,
    )

    assert tide.event_type == TideEventType.HIGH
    assert tide.height_m == 0.82