import json
import math
from dataclasses import dataclass
from pathlib import Path

from models import Position, TideStation


EARTH_RADIUS_KM = 6371.0088


@dataclass(frozen=True, slots=True)
class StationMatch:
    station: TideStation
    distance_km: float


def haversine_distance_km(
    latitude1: float,
    longitude1: float,
    latitude2: float,
    longitude2: float,
) -> float:
    """
    Calcule la distance orthodromique entre deux coordonnées GPS.
    """

    lat1 = math.radians(latitude1)
    lon1 = math.radians(longitude1)
    lat2 = math.radians(latitude2)
    lon2 = math.radians(longitude2)

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a),
    )

    return EARTH_RADIUS_KM * c


def find_nearest_station(
    position: Position,
    stations: list[TideStation],
    max_distance_km: float | None = None,
) -> StationMatch | None:
    """
    Recherche la station la plus proche.

    Retourne None si :
    - aucune station n'est disponible ;
    - la station la plus proche dépasse max_distance_km.
    """

    if not stations:
        return None

    nearest_station: TideStation | None = None
    nearest_distance = float("inf")

    for station in stations:
        distance = haversine_distance_km(
            position.latitude,
            position.longitude,
            station.latitude,
            station.longitude,
        )

        if distance < nearest_distance:
            nearest_distance = distance
            nearest_station = station

    if nearest_station is None:
        return None

    if (
        max_distance_km is not None
        and nearest_distance > max_distance_km
    ):
        return None

    return StationMatch(
        station=nearest_station,
        distance_km=nearest_distance,
    )


def load_station_catalog(
    file_path: str | Path,
) -> list[TideStation]:
    """
    Charge un catalogue JSON de stations.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Catalogue introuvable : {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            "Le catalogue doit contenir une liste."
        )

    stations: list[TideStation] = []

    for item in data:
        try:
            station = TideStation(
                station_id=str(
                    item["station_id"]
                ),
                name=str(
                    item["name"]
                ),
                latitude=float(
                    item["latitude"]
                ),
                longitude=float(
                    item["longitude"]
                ),
                source=str(
                    item.get(
                        "source",
                        "SHOM",
                    )
                ),
            )
        except (
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                f"Station invalide : {item}"
            ) from exc

        stations.append(station)

    return stations