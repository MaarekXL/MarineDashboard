import requests
import pytest

from providers import (
    ProviderConnectionError,
    ProviderDataError,
    ShomProvider,
)


SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<harbors>
    <harbor
        cst="TOULON"
        name="Toulon"
        country="France"
        defaultUT="1"
        additionalUT="2"
        isCoeffAvailable="0"
        isOfficial="1"
    />
    <harbor
        cst="TEST_PORT"
        name="Port Test"
        country="France"
        defaultUT="1"
        additionalUT="1,2"
        isCoeffAvailable="1"
        isOfficial="0"
    />
</harbors>
"""


SAMPLE_NEAREST = {
    "harbors": [
        {
            "cst": "TOULON",
            "toponyme": "Toulon",
            "ut": 1,
            "ut_sup": "2",
            "pays": "France",
            "official": 1,
            "coeff": 0,
            "distance": 2.8,
        }
    ],
    "points": [
        {
            "gid": 12345,
            "lon": 5.93,
            "lat": 43.10,
            "qualite": 1,
            "coeff": 0,
            "baie_de_se": 0,
            "distance": 0.8,
        }
    ],
}


class FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
    ) -> None:
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"HTTP {self.status_code}"
            )


class FakeSession:
    def __init__(
        self,
        status_code: int = 200,
    ) -> None:
        self.status_code = status_code

        self.last_url: str | None = None
        self.last_auth = None
        self.last_timeout = None

    def get(
        self,
        url,
        auth=None,
        timeout=None,
        **kwargs,
    ) -> FakeResponse:
        self.last_url = url
        self.last_auth = auth
        self.last_timeout = timeout

        return FakeResponse(
            self.status_code
        )


def test_parse_harbors() -> None:
    harbors = ShomProvider.parse_harbors_xml(
        SAMPLE_XML
    )

    assert len(harbors) == 2

    toulon = harbors[0]

    assert toulon.cst == "TOULON"
    assert toulon.name == "Toulon"
    assert toulon.country == "France"

    assert toulon.default_utc == 1.0
    assert toulon.additional_utc == (2.0,)

    assert (
        toulon.coefficients_available
        is False
    )

    assert toulon.official is True


def test_multiple_additional_utc() -> None:
    harbors = ShomProvider.parse_harbors_xml(
        SAMPLE_XML
    )

    harbor = harbors[1]

    assert harbor.additional_utc == (
        1.0,
        2.0,
    )


def test_invalid_xml() -> None:
    with pytest.raises(
        ProviderDataError
    ):
        ShomProvider.parse_harbors_xml(
            "<invalid"
        )


def test_empty_xml() -> None:
    with pytest.raises(
        ProviderDataError
    ):
        ShomProvider.parse_harbors_xml(
            ""
        )


def test_no_harbors() -> None:
    with pytest.raises(
        ProviderDataError
    ):
        ShomProvider.parse_harbors_xml(
            "<harbors></harbors>"
        )


def test_parse_nearest_localities() -> None:
    result = (
        ShomProvider
        .parse_nearest_localities(
            SAMPLE_NEAREST
        )
    )

    assert len(result.harbors) == 1
    assert len(result.points) == 1

    harbor = result.harbors[0]

    assert harbor.cst == "TOULON"
    assert harbor.name == "Toulon"
    assert harbor.official is True
    assert harbor.distance == 2.8

    point = result.points[0]

    assert point.gid == "12345"
    assert point.latitude == 43.10
    assert point.longitude == 5.93


def test_sapm_not_configured() -> None:
    provider = ShomProvider()

    assert provider.sapm_configured is False

    with pytest.raises(
        ProviderConnectionError
    ):
        provider.get_nearest_localities(
            latitude=43.12,
            longitude=5.93,
        )


def test_sapm_configured() -> None:
    provider = ShomProvider(
        subscription_key="TEST_KEY",
        username="user",
        password="password",
    )

    assert provider.sapm_configured is True

    assert (
        provider.authenticated_access_configured
        is True
    )


def test_spm_check_access() -> None:
    session = FakeSession(
        status_code=200
    )

    provider = ShomProvider(
        subscription_key="KEY",
        username="user",
        password="password",
        session=session,
    )

    result = provider.check_spm_access()

    assert result.allowed is True
    assert result.service == "spm"

    assert session.last_url is not None

    assert session.last_url.endswith(
        "/KEY/spm/checkaccess"
    )

    assert session.last_auth == (
        "user",
        "password",
    )

    assert session.last_timeout == 10.0


def test_sapm_check_access() -> None:
    session = FakeSession(
        status_code=200
    )

    provider = ShomProvider(
        subscription_key="KEY",
        username="user",
        password="password",
        session=session,
    )

    result = provider.check_sapm_access()

    assert result.allowed is True
    assert result.service == "sapm"

    assert session.last_url is not None

    assert session.last_url.endswith(
        "/KEY/sapm/checkaccess"
    )

    assert session.last_auth == (
        "user",
        "password",
    )


def test_check_access_denied() -> None:
    session = FakeSession(
        status_code=401
    )

    provider = ShomProvider(
        subscription_key="KEY",
        username="bad",
        password="bad",
        session=session,
    )

    result = provider.check_spm_access()

    assert result.allowed is False
    assert result.service == "spm"


def test_check_access_without_credentials() -> None:
    provider = ShomProvider()

    assert (
        provider.authenticated_access_configured
        is False
    )

    with pytest.raises(
        ProviderConnectionError
    ):
        provider.check_spm_access()