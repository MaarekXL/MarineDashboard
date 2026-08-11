import pytest

from positioning import NMEASerialReader


VALID_RMC = (
    "$GPRMC,123519,A,4807.038,N,"
    "01131.000,E,022.4,084.4,"
    "230394,003.1,W*6A\r\n"
)


class FakeSerial:
    def __init__(
        self,
        lines: list[bytes],
    ) -> None:
        self.lines = iter(lines)
        self.is_open = True

    def readline(self) -> bytes:
        try:
            return next(self.lines)
        except StopIteration:
            return b""

    def close(self) -> None:
        self.is_open = False


def test_read_sentence() -> None:
    reader = NMEASerialReader(
        "COM_TEST"
    )

    reader._serial = FakeSerial(
        [
            VALID_RMC.encode("ascii"),
        ]
    )

    sentence = reader.read_sentence()

    assert sentence is not None
    assert sentence.startswith("$GPRMC")


def test_ignore_non_nmea_data() -> None:
    reader = NMEASerialReader(
        "COM_TEST"
    )

    reader._serial = FakeSerial(
        [
            b"garbage data\r\n",
        ]
    )

    assert reader.read_sentence() is None


def test_read_next_position() -> None:
    reader = NMEASerialReader(
        "COM_TEST"
    )

    reader._serial = FakeSerial(
        [
            b"$GPGGA,test\r\n",
            VALID_RMC.encode("ascii"),
        ]
    )

    position = reader.read_next_position()

    assert position is not None

    assert position.latitude == pytest.approx(
        48.1173,
        abs=0.0001,
    )

    assert position.longitude == pytest.approx(
        11.5166667,
        abs=0.0001,
    )


def test_no_position_available() -> None:
    reader = NMEASerialReader(
        "COM_TEST"
    )

    reader._serial = FakeSerial(
        [
            b"$GPGGA,test\r\n",
            b"",
        ]
    )

    position = reader.read_next_position(
        max_lines=2
    )

    assert position is None