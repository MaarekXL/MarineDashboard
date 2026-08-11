import re
from datetime import datetime, tzinfo
from xml.etree import ElementTree

from models import (
    TideEvent,
    TideEventType,
    TidePoint,
)

from .base_provider import ProviderDataError


class ShomPredictionParser:
    @staticmethod
    def parse_tide_events_xml(
        xml_data: str,
        target_id: str,
    ) -> list[TideEvent]:
        """
        Parse le fichier XML des pleines/basses mers SHOM.
        """

        if not xml_data.strip():
            raise ProviderDataError(
                "Fichier XML de marée vide."
            )

        if not target_id:
            raise ValueError(
                "target_id ne peut pas être vide."
            )

        try:
            root = ElementTree.fromstring(
                xml_data
            )

        except ElementTree.ParseError as exc:
            raise ProviderDataError(
                "XML de prédiction SHOM invalide."
            ) from exc

        events: list[TideEvent] = []

        for value in root.findall(".//value"):
            state = value.attrib.get(
                "state",
                "",
            ).strip().lower()

            if state == "high":
                event_type = TideEventType.HIGH

            elif state == "low":
                event_type = TideEventType.LOW

            else:
                continue

            datetime_element = value.find(
                "dateTime"
            )

            height_element = value.find(
                "height"
            )

            if (
                datetime_element is None
                or height_element is None
                or datetime_element.text is None
                or height_element.text is None
            ):
                raise ProviderDataError(
                    "Événement SHOM incomplet."
                )

            try:
                timestamp = datetime.fromisoformat(
                    datetime_element.text.strip()
                )

                height = float(
                    height_element.text.strip()
                )

            except ValueError as exc:
                raise ProviderDataError(
                    "Valeur SHOM invalide."
                ) from exc

            coefficient = _parse_coefficient(
                value.attrib.get("coef")
            )

            events.append(
                TideEvent(
                    timestamp=timestamp,
                    event_type=event_type,
                    height_m=height,
                    station_id=target_id,
                    coefficient=coefficient,
                )
            )

        if not events:
            raise ProviderDataError(
                "Aucun événement de marée "
                "trouvé dans le XML SHOM."
            )

        events.sort(
            key=lambda event: event.timestamp
        )

        return events

    @staticmethod
    def parse_water_heights_txt(
        text_data: str,
        target_id: str,
        timezone_info: tzinfo,
    ) -> list[TidePoint]:
        """
        Parse un fichier HTR SHOM contenant
        les hauteurs d'eau à pas régulier.

        Le fuseau horaire est fourni explicitement
        pour éviter toute hypothèse sur la commande.
        """

        if not text_data.strip():
            raise ProviderDataError(
                "Fichier de hauteurs d'eau vide."
            )

        if not target_id:
            raise ValueError(
                "target_id ne peut pas être vide."
            )

        pattern = re.compile(
            r"^"
            r"(\d{4}-\d{2}-\d{2})"
            r"\s+"
            r"(\d{2}:\d{2}:\d{2})"
            r"\s+"
            r"([-+]?\d+(?:\.\d+)?)"
            r"\s*$"
        )

        points: list[TidePoint] = []

        for raw_line in text_data.splitlines():
            line = raw_line.strip()

            if not line:
                continue

            match = pattern.match(
                line
            )

            # Les lignes d'en-tête sont ignorées.
            if match is None:
                continue

            date_value = match.group(1)
            time_value = match.group(2)
            height_value = match.group(3)

            try:
                timestamp = datetime.strptime(
                    f"{date_value} {time_value}",
                    "%Y-%m-%d %H:%M:%S",
                ).replace(
                    tzinfo=timezone_info
                )

                height = float(
                    height_value
                )

            except ValueError as exc:
                raise ProviderDataError(
                    "Hauteur d'eau SHOM invalide."
                ) from exc

            points.append(
                TidePoint(
                    timestamp=timestamp,
                    height_m=height,
                    station_id=target_id,
                )
            )

        if not points:
            raise ProviderDataError(
                "Aucune hauteur d'eau trouvée "
                "dans le fichier SHOM."
            )

        points.sort(
            key=lambda point: point.timestamp
        )

        return points


def _parse_coefficient(
    value: str | None,
) -> int | None:
    """
    Le coefficient n'est pas disponible
    pour tous les ports.
    """

    if value is None:
        return None

    value = value.strip()

    if not value:
        return None

    if value in (
        "---",
        "--",
        "-",
    ):
        return None

    try:
        return int(
            value
        )

    except ValueError as exc:
        raise ProviderDataError(
            f"Coefficient SHOM invalide : {value}"
        ) from exc