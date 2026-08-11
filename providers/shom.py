from dataclasses import dataclass
from xml.etree import ElementTree

import requests

from .base_provider import (
    BaseProvider,
    ProviderConnectionError,
    ProviderDataError,
)


SHOM_BASE_URL = "https://services.data.shom.fr"
SHOM_HARBORS_URL = f"{SHOM_BASE_URL}/spm/listHarbors"


@dataclass(frozen=True, slots=True)
class ShomHarbor:
    """
    Métadonnées d'un port retourné par /spm/listHarbors.

    Attention :
    ce service ne fournit pas les coordonnées
    géographiques du port.
    """

    cst: str
    name: str
    country: str

    default_utc: float
    additional_utc: tuple[float, ...]

    coefficients_available: bool
    official: bool


@dataclass(frozen=True, slots=True)
class ShomNearbyHarbor:
    """
    Port proche retourné par le service SAPM.
    """

    cst: str
    name: str
    country: str

    utc: float
    additional_utc: tuple[float, ...]

    official: bool
    coefficients_available: bool

    distance: float


@dataclass(frozen=True, slots=True)
class ShomModelPoint:
    """
    Point du modèle SHOM proche d'une position GPS.
    """

    gid: str

    longitude: float
    latitude: float

    quality: int | None

    coefficients_available: bool
    bay_of_seine: bool

    distance: float


@dataclass(frozen=True, slots=True)
class ShomAccessStatus:
    """
    Résultat d'une vérification d'accès SHOM.
    """

    service: str
    allowed: bool


@dataclass(frozen=True, slots=True)
class ShomNearestLocalities:
    """
    Résultat de la recherche SAPM
    des localités proches.
    """

    harbors: tuple[ShomNearbyHarbor, ...]
    points: tuple[ShomModelPoint, ...]


class ShomProvider(BaseProvider):
    def __init__(
        self,
        timeout: float = 10.0,
        session: requests.Session | None = None,
        subscription_key: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        if timeout <= 0:
            raise ValueError(
                "Le timeout doit être supérieur à zéro."
            )

        self.timeout = timeout

        self.session = (
            session
            if session is not None
            else requests.Session()
        )

        self.subscription_key = subscription_key
        self.username = username
        self.password = password

    @property
    def name(self) -> str:
        return "SHOM"

    @property
    def authenticated_access_configured(
        self,
    ) -> bool:
        """
        Indique si les informations nécessaires
        aux services SHOM authentifiés sont présentes.
        """

        return bool(
            self.subscription_key
            and self.username
            and self.password
        )

    @property
    def sapm_configured(
        self,
    ) -> bool:
        """
        Compatibilité avec StationService.

        SAPM utilise les mêmes informations
        d'authentification.
        """

        return self.authenticated_access_configured

    # -------------------------------------------------------------------------
    # PUBLIC HARBORS
    # -------------------------------------------------------------------------

    def get_harbors(
        self,
    ) -> list[ShomHarbor]:
        """
        Télécharge la liste publique des ports SHOM.
        """

        try:
            response = self.session.get(
                SHOM_HARBORS_URL,
                timeout=self.timeout,
            )

            response.raise_for_status()

        except requests.RequestException as exc:
            raise ProviderConnectionError(
                "Impossible de récupérer "
                "la liste des ports SHOM."
            ) from exc

        return self.parse_harbors_xml(
            response.text
        )

    # -------------------------------------------------------------------------
    # ACCESS CHECK
    # -------------------------------------------------------------------------

    def check_spm_access(
        self,
    ) -> ShomAccessStatus:
        """
        Vérifie l'accès au service SPM / SUP Marée.
        """

        return self._check_access(
            service="spm"
        )

    def check_sapm_access(
        self,
    ) -> ShomAccessStatus:
        """
        Vérifie l'accès au service SAPM.
        """

        return self._check_access(
            service="sapm"
        )

    def _check_access(
        self,
        service: str,
    ) -> ShomAccessStatus:
        """
        Vérifie les droits d'accès
        à un service SHOM authentifié.
        """

        if service not in (
            "spm",
            "sapm",
        ):
            raise ValueError(
                f"Service SHOM inconnu : {service}"
            )

        if not self.authenticated_access_configured:
            raise ProviderConnectionError(
                "Identifiants SHOM non configurés."
            )

        url = (
            f"{SHOM_BASE_URL}/spm/"
            f"{self.subscription_key}/"
            f"{service}/checkaccess"
        )

        try:
            response = self.session.get(
                url,
                auth=(
                    self.username,
                    self.password,
                ),
                timeout=self.timeout,
            )

            if response.status_code in (
                401,
                403,
            ):
                return ShomAccessStatus(
                    service=service,
                    allowed=False,
                )

            response.raise_for_status()

        except requests.RequestException as exc:
            raise ProviderConnectionError(
                "Impossible de vérifier "
                f"l'accès SHOM {service.upper()}."
            ) from exc

        return ShomAccessStatus(
            service=service,
            allowed=True,
        )

    # -------------------------------------------------------------------------
    # SAPM
    # -------------------------------------------------------------------------

    def get_nearest_localities(
        self,
        latitude: float,
        longitude: float,
    ) -> ShomNearestLocalities:
        """
        Recherche les ports et points SHOM
        proches d'une position GPS.

        Nécessite une configuration SAPM.
        """

        if not -90.0 <= latitude <= 90.0:
            raise ValueError(
                "Latitude invalide."
            )

        if not -180.0 <= longitude <= 180.0:
            raise ValueError(
                "Longitude invalide."
            )

        if not self.sapm_configured:
            raise ProviderConnectionError(
                "SAPM non configuré : "
                "clé SHOM ou identifiants manquants."
            )

        url = (
            f"{SHOM_BASE_URL}/spm/"
            f"{self.subscription_key}/sapm/"
            "getNearestLocalities"
        )

        try:
            response = self.session.get(
                url,
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                },
                auth=(
                    self.username,
                    self.password,
                ),
                timeout=self.timeout,
            )

            response.raise_for_status()

        except requests.RequestException as exc:
            raise ProviderConnectionError(
                "Impossible d'interroger "
                "le service getNearestLocalities."
            ) from exc

        try:
            data = response.json()

        except ValueError as exc:
            raise ProviderDataError(
                "Réponse JSON SHOM invalide."
            ) from exc

        return self.parse_nearest_localities(
            data
        )

    # -------------------------------------------------------------------------
    # HARBORS XML PARSER
    # -------------------------------------------------------------------------

    @staticmethod
    def parse_harbors_xml(
        xml_data: str,
    ) -> list[ShomHarbor]:
        """
        Transforme la réponse XML SHOM
        en objets Python.
        """

        if not xml_data.strip():
            raise ProviderDataError(
                "Réponse SHOM vide."
            )

        try:
            root = ElementTree.fromstring(
                xml_data
            )

        except ElementTree.ParseError as exc:
            raise ProviderDataError(
                "XML SHOM invalide."
            ) from exc

        harbors: list[ShomHarbor] = []

        for element in root.findall(
            ".//harbor"
        ):
            try:
                cst = element.attrib["cst"]
                name = element.attrib["name"]

                country = element.attrib.get(
                    "country",
                    "",
                )

                default_utc = _parse_utc(
                    element.attrib.get(
                        "defaultUT",
                        "0",
                    )
                )

                additional_utc = (
                    _parse_additional_utc(
                        element.attrib.get(
                            "additionalUT",
                            "",
                        )
                    )
                )

                coefficients_available = (
                    _parse_bool_attribute(
                        element.attrib.get(
                            "isCoeffAvailable",
                            "0",
                        )
                    )
                )

                official = (
                    _parse_bool_attribute(
                        element.attrib.get(
                            "isOfficial",
                            "0",
                        )
                    )
                )

            except (
                KeyError,
                TypeError,
                ValueError,
            ) as exc:
                raise ProviderDataError(
                    "Port SHOM invalide : "
                    f"{element.attrib}"
                ) from exc

            harbors.append(
                ShomHarbor(
                    cst=cst,
                    name=name,
                    country=country,
                    default_utc=default_utc,
                    additional_utc=additional_utc,
                    coefficients_available=(
                        coefficients_available
                    ),
                    official=official,
                )
            )

        if not harbors:
            raise ProviderDataError(
                "Aucun port trouvé "
                "dans la réponse SHOM."
            )

        return harbors

    # -------------------------------------------------------------------------
    # SAPM JSON PARSER
    # -------------------------------------------------------------------------

    @staticmethod
    def parse_nearest_localities(
        data: dict,
    ) -> ShomNearestLocalities:
        """
        Transforme une réponse SAPM
        en objets Python.
        """

        if not isinstance(
            data,
            dict,
        ):
            raise ProviderDataError(
                "Réponse SAPM invalide."
            )

        harbors: list[
            ShomNearbyHarbor
        ] = []

        points: list[
            ShomModelPoint
        ] = []

        raw_harbors = data.get(
            "harbors",
            [],
        )

        raw_points = data.get(
            "points",
            [],
        )

        if not isinstance(
            raw_harbors,
            list,
        ):
            raise ProviderDataError(
                "Liste des ports SAPM invalide."
            )

        if not isinstance(
            raw_points,
            list,
        ):
            raise ProviderDataError(
                "Liste des points SAPM invalide."
            )

        for item in raw_harbors:
            if not isinstance(
                item,
                dict,
            ):
                raise ProviderDataError(
                    "Port SAPM invalide."
                )

            try:
                harbor = ShomNearbyHarbor(
                    cst=str(
                        item["cst"]
                    ),
                    name=str(
                        item["toponyme"]
                    ),
                    country=str(
                        item.get(
                            "pays",
                            "",
                        )
                    ),
                    utc=float(
                        item.get(
                            "ut",
                            0,
                        )
                    ),
                    additional_utc=(
                        _parse_additional_utc(
                            str(
                                item.get(
                                    "ut_sup",
                                    "",
                                )
                            )
                        )
                    ),
                    official=(
                        _parse_bool_value(
                            item.get(
                                "official",
                                0,
                            )
                        )
                    ),
                    coefficients_available=(
                        _parse_bool_value(
                            item.get(
                                "coeff",
                                0,
                            )
                        )
                    ),
                    distance=float(
                        item["distance"]
                    ),
                )

            except (
                KeyError,
                TypeError,
                ValueError,
            ) as exc:
                raise ProviderDataError(
                    "Port SAPM invalide : "
                    f"{item}"
                ) from exc

            harbors.append(
                harbor
            )

        for item in raw_points:
            if not isinstance(
                item,
                dict,
            ):
                raise ProviderDataError(
                    "Point SAPM invalide."
                )

            try:
                quality_value = (
                    item.get(
                        "qualite"
                    )
                )

                quality = (
                    int(quality_value)
                    if quality_value
                    is not None
                    else None
                )

                point = ShomModelPoint(
                    gid=str(
                        item["gid"]
                    ),
                    longitude=float(
                        item["lon"]
                    ),
                    latitude=float(
                        item["lat"]
                    ),
                    quality=quality,
                    coefficients_available=(
                        _parse_bool_value(
                            item.get(
                                "coeff",
                                0,
                            )
                        )
                    ),
                    bay_of_seine=(
                        _parse_bool_value(
                            item.get(
                                "baie_de_se",
                                0,
                            )
                        )
                    ),
                    distance=float(
                        item["distance"]
                    ),
                )

            except (
                KeyError,
                TypeError,
                ValueError,
            ) as exc:
                raise ProviderDataError(
                    "Point SAPM invalide : "
                    f"{item}"
                ) from exc

            points.append(
                point
            )

        return ShomNearestLocalities(
            harbors=tuple(
                harbors
            ),
            points=tuple(
                points
            ),
        )


# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------


def _parse_bool_attribute(
    value: str,
) -> bool:
    """
    Convertit une valeur texte SHOM
    0/1 en booléen.
    """

    value = value.strip()

    if value == "1":
        return True

    if value == "0":
        return False

    raise ValueError(
        f"Booléen SHOM invalide : {value}"
    )


def _parse_bool_value(
    value: object,
) -> bool:
    """
    Convertit différentes représentations
    booléennes provenant du JSON SHOM.
    """

    if isinstance(
        value,
        bool,
    ):
        return value

    if isinstance(
        value,
        int,
    ):
        if value == 1:
            return True

        if value == 0:
            return False

    if isinstance(
        value,
        str,
    ):
        normalized = (
            value
            .strip()
            .lower()
        )

        if normalized in (
            "1",
            "true",
            "yes",
        ):
            return True

        if normalized in (
            "0",
            "false",
            "no",
            "",
        ):
            return False

    raise ValueError(
        f"Booléen SHOM invalide : {value}"
    )


def _parse_utc(
    value: str,
) -> float:
    """
    Convertit un décalage UTC SHOM.
    """

    value = value.strip()

    if not value:
        return 0.0

    return float(
        value
    )


def _parse_additional_utc(
    value: str,
) -> tuple[float, ...]:
    """
    Convertit par exemple :

    "1,2"
    ou
    "1;2"

    en :

    (1.0, 2.0)
    """

    value = value.strip()

    if not value:
        return ()

    normalized = value.replace(
        ";",
        ",",
    )

    result: list[float] = []

    for item in normalized.split(
        ","
    ):
        item = item.strip()

        if not item:
            continue

        result.append(
            float(item)
        )

    return tuple(
        result
    )