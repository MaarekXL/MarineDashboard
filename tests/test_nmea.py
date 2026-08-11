import pytest

from models import PositionSource
from positioning import (
    NMEAError,
    parse_rmc,
    validate_checksum,
)


VALID_RMC = (
    "$GPRMC,123519,A,4807.038,N,"
    "01131.000,E,022.4,084.4,"
    "230394,003.1,W*6A"
)


def test_checksum() -> None:
    assert validate_checksum(
        VALID_RMC
    ) is True


def test_parse_rmc() -> None:
    position = parse_rmc(
        VALID_RMC
    )

    assert position.source == (
        PositionSource.NMEA
    )

    assert position.valid is True

    assert position.latitude == pytest.approx(
        48.1173,
        abs=0.0001,
    )

    assert position.longitude == pytest.approx(
        11.5166667,
        abs=0.0001,
    )

    assert position.speed_knots == 22.4
    assert position.course_deg == 84.4

    assert position.timestamp.hour == 12
    assert position.timestamp.minute == 35
    assert position.timestamp.second == 19


def test_invalid_checksum() -> None:
    invalid = VALID_RMC.replace(
        "*6A",
        "*00",
    )

    with pytest.raises(
        NMEAError
    ):
        parse_rmc(invalid)