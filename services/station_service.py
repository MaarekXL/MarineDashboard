from typing import Protocol

from models import (
    Position,
    PredictionTarget,
    PredictionTargetKind,
    PredictionTargetSource,
    TideStation,
)

from positioning import (
    find_nearest_station,
    haversine_distance_km,
)

from providers import (
    ProviderError,
    ShomNearestLocalities,
)


class LocalityProvider(Protocol):
    @property
    def sapm_configured(self) -> bool:
        ...

    def get_nearest_localities(
        self,
        latitude: float,
        longitude: float,
    ) -> ShomNearestLocalities:
        ...


class StationUnavailableError(RuntimeError):
    """Aucune cible de prédiction exploitable."""


class StationService:
    def __init__(
        self,
        provider: LocalityProvider,
        local_stations: list[TideStation] | None = None,
        max_local_distance_km: float = 100.0,
    ) -> None:
        if max_local_distance_km <= 0:
            raise ValueError(
                "max_local_distance_km doit être supérieur à zéro."
            )

        self.provider = provider
        self.local_stations = (
            local_stations or []
        )

        self.max_local_distance_km = (
            max_local_distance_km
        )

    def select_target(
        self,
        position: Position,
        manual_station: TideStation | None = None,
    ) -> PredictionTarget:
        """
        Sélectionne la meilleure cible de prédiction.

        Priorités :

        1. choix manuel explicite
        2. SAPM
        3. catalogue local
        """

        # 1. L'utilisateur force une station.
        if manual_station is not None:
            distance = haversine_distance_km(
                position.latitude,
                position.longitude,
                manual_station.latitude,
                manual_station.longitude,
            )

            return PredictionTarget(
                identifier=manual_station.station_id,
                name=manual_station.name,
                kind=PredictionTargetKind.HARBOR,
                selection_source=(
                    PredictionTargetSource.MANUAL
                ),
                provider=manual_station.source,
                latitude=manual_station.latitude,
                longitude=manual_station.longitude,
                distance_km=distance,
            )

        # 2. SAPM
        if self.provider.sapm_configured:
            try:
                localities = (
                    self.provider
                    .get_nearest_localities(
                        latitude=position.latitude,
                        longitude=position.longitude,
                    )
                )

                target = (
                    self._select_from_sapm(
                        localities
                    )
                )

                if target is not None:
                    return target

            except ProviderError:
                # Mode dégradé :
                # on tente le catalogue local.
                pass

        # 3. Catalogue local
        target = self._select_from_local(
            position
        )

        if target is not None:
            return target

        raise StationUnavailableError(
            "Aucune station ou cible SHOM "
            "n'est disponible pour cette position."
        )

    @staticmethod
    def _select_from_sapm(
        localities: ShomNearestLocalities,
    ) -> PredictionTarget | None:
        """
        Priorité aux ports.

        Si aucun port n'est disponible,
        utilise le point de modèle SAPM
        le plus proche.
        """

        if localities.harbors:
            harbor = min(
                localities.harbors,
                key=lambda item: item.distance,
            )

            return PredictionTarget(
                identifier=harbor.cst,
                name=harbor.name,
                kind=PredictionTargetKind.HARBOR,
                selection_source=(
                    PredictionTargetSource.SAPM
                ),
                provider="SHOM",
                provider_distance=harbor.distance,
                official=harbor.official,
                coefficients_available=(
                    harbor.coefficients_available
                ),
            )

        if localities.points:
            point = min(
                localities.points,
                key=lambda item: item.distance,
            )

            return PredictionTarget(
                identifier=point.gid,
                name=f"Point SHOM {point.gid}",
                kind=(
                    PredictionTargetKind.MODEL_POINT
                ),
                selection_source=(
                    PredictionTargetSource.SAPM
                ),
                provider="SHOM",
                latitude=point.latitude,
                longitude=point.longitude,
                provider_distance=point.distance,
                coefficients_available=(
                    point.coefficients_available
                ),
            )

        return None

    def _select_from_local(
        self,
        position: Position,
    ) -> PredictionTarget | None:
        match = find_nearest_station(
            position,
            self.local_stations,
            max_distance_km=(
                self.max_local_distance_km
            ),
        )

        if match is None:
            return None

        station = match.station

        return PredictionTarget(
            identifier=station.station_id,
            name=station.name,
            kind=PredictionTargetKind.HARBOR,
            selection_source=(
                PredictionTargetSource.LOCAL
            ),
            provider=station.source,
            latitude=station.latitude,
            longitude=station.longitude,
            distance_km=match.distance_km,
        )