from datetime import datetime, timezone

from models import Position, PositionSource


class NMEAError(ValueError):
    """Erreur lors du décodage d'une trame NMEA."""


def calculate_checksum(sentence: str) -> int:
    """
    Calcule le checksum NMEA entre '$' et '*'.
    """
    data = sentence.strip()

    if data.startswith("$"):
        data = data[1:]

    if "*" in data:
        data = data.split("*", 1)[0]

    checksum = 0

    for char in data:
        checksum ^= ord(char)

    return checksum


def validate_checksum(sentence: str) -> bool:
    """
    Vérifie le checksum d'une trame NMEA.
    """
    sentence = sentence.strip()

    if "*" not in sentence:
        return False

    data, expected = sentence.rsplit("*", 1)

    try:
        expected_checksum = int(
            expected[:2],
            16,
        )
    except ValueError:
        return False

    return calculate_checksum(data) == expected_checksum


def _parse_coordinate(
    value: str,
    hemisphere: str,
    degree_digits: int,
) -> float:
    """
    Convertit une coordonnée NMEA DDMM.MMMM
    ou DDDMM.MMMM en degrés décimaux.
    """
    if not value:
        raise NMEAError("Coordonnée NMEA absente.")

    try:
        degrees = float(
            value[:degree_digits]
        )

        minutes = float(
            value[degree_digits:]
        )
    except ValueError as exc:
        raise NMEAError(
            f"Coordonnée NMEA invalide : {value}"
        ) from exc

    coordinate = degrees + minutes / 60.0

    hemisphere = hemisphere.upper()

    if hemisphere in ("S", "W"):
        coordinate *= -1

    elif hemisphere not in ("N", "E"):
        raise NMEAError(
            f"Hémisphère invalide : {hemisphere}"
        )

    return coordinate


def _parse_datetime(
    time_value: str,
    date_value: str,
) -> datetime:
    """
    Convertit les champs RMC :
        heure = HHMMSS.SS
        date  = DDMMYY

    en datetime UTC.
    """
    if len(time_value) < 6:
        raise NMEAError(
            "Heure NMEA invalide."
        )

    if len(date_value) != 6:
        raise NMEAError(
            "Date NMEA invalide."
        )

    try:
        hour = int(time_value[0:2])
        minute = int(time_value[2:4])

        seconds_float = float(
            time_value[4:]
        )

        second = int(seconds_float)

        microsecond = int(
            round(
                (seconds_float - second)
                * 1_000_000
            )
        )

        day = int(date_value[0:2])
        month = int(date_value[2:4])
        year = 2000 + int(
            date_value[4:6]
        )

        return datetime(
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            second=second,
            microsecond=microsecond,
            tzinfo=timezone.utc,
        )

    except ValueError as exc:
        raise NMEAError(
            "Date ou heure NMEA invalide."
        ) from exc


def parse_rmc(
    sentence: str,
) -> Position:
    """
    Décode une trame GPRMC ou GNRMC.

    Exemple :
    $GPRMC,123519,A,4807.038,N,01131.000,E,
    022.4,084.4,230394,003.1,W*6A
    """
    sentence = sentence.strip()

    if not validate_checksum(sentence):
        raise NMEAError(
            "Checksum NMEA invalide."
        )

    payload = sentence[1:].split(
        "*",
        1,
    )[0]

    fields = payload.split(",")

    message_type = fields[0]

    if message_type not in (
        "GPRMC",
        "GNRMC",
    ):
        raise NMEAError(
            f"Trame non supportée : {message_type}"
        )

    if len(fields) < 10:
        raise NMEAError(
            "Trame RMC incomplète."
        )

    time_value = fields[1]
    status = fields[2]

    latitude_value = fields[3]
    latitude_hemisphere = fields[4]

    longitude_value = fields[5]
    longitude_hemisphere = fields[6]

    speed_value = fields[7]
    course_value = fields[8]

    date_value = fields[9]

    valid = status == "A"

    latitude = _parse_coordinate(
        latitude_value,
        latitude_hemisphere,
        degree_digits=2,
    )

    longitude = _parse_coordinate(
        longitude_value,
        longitude_hemisphere,
        degree_digits=3,
    )

    timestamp = _parse_datetime(
        time_value,
        date_value,
    )

    speed_knots = (
        float(speed_value)
        if speed_value
        else None
    )

    course_deg = (
        float(course_value)
        if course_value
        else None
    )

    return Position(
        latitude=latitude,
        longitude=longitude,
        timestamp=timestamp,
        source=PositionSource.NMEA,
        valid=valid,
        speed_knots=speed_knots,
        course_deg=course_deg,
    )