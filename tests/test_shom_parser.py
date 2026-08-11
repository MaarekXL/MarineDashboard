from datetime import (
    timedelta,
    timezone,
)

import pytest

from models import TideEventType

from providers import (
    ProviderDataError,
    ShomPredictionParser,
)


SAMPLE_EVENTS_XML = """
<root>
    <city>
        <port type="principal">
            <name>Toulon</name>
        </port>

        <values content="prediction">

            <value
                coef="76"
                state="high"
            >
                <dateTime>
                    2026-08-11T08:42:00+02:00
                </dateTime>
                <height>0.82</height>
            </value>

            <value state="low">
                <dateTime>
                    2026-08-11T14:51:00+02:00
                </dateTime>
                <height>0.31</height>
            </value>

        </values>
    </city>
</root>
"""


SAMPLE_HEIGHTS_TXT = """
Site : TOULON (France)
latitude : 43.100000 - longitude : 5.930000
Systeme horaire : UTC+02:00

2026-08-11 00:00:00 0.42
2026-08-11 00:10:00 0.45
2026-08-11 00:20:00 0.49
"""


def test_parse_events_xml() -> None:
    events = (
        ShomPredictionParser
        .parse_tide_events_xml(
            SAMPLE_EVENTS_XML,
            "TOULON",
        )
    )

    assert len(events) == 2

    assert events[0].event_type == (
        TideEventType.HIGH
    )

    assert events[0].height_m == 0.82
    assert events[0].coefficient == 76

    assert events[1].event_type == (
        TideEventType.LOW
    )

    assert events[1].height_m == 0.31
    assert events[1].coefficient is None


def test_xml_timezone_preserved() -> None:
    events = (
        ShomPredictionParser
        .parse_tide_events_xml(
            SAMPLE_EVENTS_XML,
            "TOULON",
        )
    )

    assert (
        events[0]
        .timestamp
        .utcoffset()
        == timedelta(hours=2)
    )


def test_parse_water_heights_txt() -> None:
    tz = timezone(
        timedelta(hours=2)
    )

    points = (
        ShomPredictionParser
        .parse_water_heights_txt(
            SAMPLE_HEIGHTS_TXT,
            "TOULON",
            timezone_info=tz,
        )
    )

    assert len(points) == 3

    assert points[0].height_m == 0.42
    assert points[1].height_m == 0.45
    assert points[2].height_m == 0.49

    assert points[0].station_id == (
        "TOULON"
    )


def test_txt_timezone_applied() -> None:
    tz = timezone(
        timedelta(hours=2)
    )

    points = (
        ShomPredictionParser
        .parse_water_heights_txt(
            SAMPLE_HEIGHTS_TXT,
            "TOULON",
            timezone_info=tz,
        )
    )

    assert (
        points[0]
        .timestamp
        .utcoffset()
        == timedelta(hours=2)
    )


def test_invalid_prediction_data() -> None:
    with pytest.raises(
        ProviderDataError
    ):
        (
            ShomPredictionParser
            .parse_tide_events_xml(
                "<invalid",
                "TOULON",
            )
        )

    with pytest.raises(
        ProviderDataError
    ):
        (
            ShomPredictionParser
            .parse_water_heights_txt(
                "aucune donnée",
                "TOULON",
                timezone_info=timezone.utc,
            )
        )