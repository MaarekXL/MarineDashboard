from datetime import datetime, timezone

import pytest

from models import (
    Position,
    PositionSource,
    PredictionTargetKind,
    PredictionTargetSource,
    TideStation,
)

from providers import (
    ProviderConnectionError,
    ShomModelPoint,
    ShomNearbyHarbor,
    ShomNearestLocalities,
)

from services import (
    StationService,
    StationUnavailableError,
)


def make_position() -> Position:
    return Position(
        latitude=43.12,
        longitude=5.93,
        timestamp=datetime.now(
            timezone.utc
        ),
        source=PositionSource.NMEA,
    )


class FakeProvider:
    def __init__(
        self,
        configured: bool,
        result: ShomNearestLocalities | None = None,
        fail: bool = False,
    ) -> None:
        self._configured = configured
        self.result = result
        self.fail = fail

    @property
    def sapm_configured(self) -> bool:
        return self._configured

    def get_nearest_localities(
        self,
        latitude: float,
        longitude: float,
    ) -> ShomNearestLocalities:
        if self.fail:
            raise ProviderConnectionError(
                "Erreur simulée"
            )

        if self.result is None:
            return ShomNearestLocalities(
                harbors=(),
                points=(),
            )

        return self.result


def test_manual_station_has_priority() -> None:
    provider = FakeProvider(
        configured=True
    )

    manual = TideStation(
        station_id="MANUAL",
        name="Port manuel",
        latitude=43.11,
        longitude=5.92,
    )

    service = StationService(
        provider
    )

    result = service.select_target(
        make_position(),
        manual_station=manual,
    )

    assert result.identifier == "MANUAL"

    assert result.selection_source == (
        PredictionTargetSource.MANUAL
    )


def test_select_nearest_sapm_harbor() -> None:
    localities = ShomNearestLocalities(
        harbors=(
            ShomNearbyHarbor(
                cst="A",
                name="Port A",
                country="France",
                utc=1,
                additional_utc=(),
                official=True,
                coefficients_available=False,
                distance=8.0,
            ),
            ShomNearbyHarbor(
                cst="B",
                name="Port B",
                country="France",
                utc=1,
                additional_utc=(),
                official=True,
                coefficients_available=False,
                distance=2.0,
            ),
        ),
        points=(),
    )

    provider = FakeProvider(
        configured=True,
        result=localities,
    )

    service = StationService(
        provider
    )

    result = service.select_target(
        make_position()
    )

    assert result.identifier == "B"

    assert result.kind == (
        PredictionTargetKind.HARBOR
    )

    assert result.selection_source == (
        PredictionTargetSource.SAPM
    )


def test_sapm_model_point_fallback() -> None:
    localities = ShomNearestLocalities(
        harbors=(),
        points=(
            ShomModelPoint(
                gid="12345",
                longitude=5.94,
                latitude=43.13,
                quality=1,
                coefficients_available=False,
                bay_of_seine=False,
                distance=1.0,
            ),
        ),
    )

    provider = FakeProvider(
        configured=True,
        result=localities,
    )

    service = StationService(
        provider
    )

    result = service.select_target(
        make_position()
    )

    assert result.identifier == "12345"

    assert result.kind == (
        PredictionTargetKind.MODEL_POINT
    )


def test_local_catalog_fallback() -> None:
    provider = FakeProvider(
        configured=False
    )

    stations = [
        TideStation(
            station_id="LOCAL",
            name="Port local",
            latitude=43.121,
            longitude=5.931,
        )
    ]

    service = StationService(
        provider,
        local_stations=stations,
    )

    result = service.select_target(
        make_position()
    )

    assert result.identifier == "LOCAL"

    assert result.selection_source == (
        PredictionTargetSource.LOCAL
    )


def test_provider_failure_uses_local_catalog() -> None:
    provider = FakeProvider(
        configured=True,
        fail=True,
    )

    stations = [
        TideStation(
            station_id="BACKUP",
            name="Port secours",
            latitude=43.121,
            longitude=5.931,
        )
    ]

    service = StationService(
        provider,
        local_stations=stations,
    )

    result = service.select_target(
        make_position()
    )

    assert result.identifier == "BACKUP"


def test_no_station_available() -> None:
    provider = FakeProvider(
        configured=False
    )

    service = StationService(
        provider,
        local_stations=[],
    )

    with pytest.raises(
        StationUnavailableError
    ):
        service.select_target(
            make_position()
        )