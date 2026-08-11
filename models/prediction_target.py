from dataclasses import dataclass
from enum import StrEnum


class PredictionTargetKind(StrEnum):
    HARBOR = "harbor"
    MODEL_POINT = "model_point"


class PredictionTargetSource(StrEnum):
    SAPM = "sapm"
    LOCAL = "local"
    MANUAL = "manual"


@dataclass(frozen=True, slots=True)
class PredictionTarget:
    identifier: str
    name: str

    kind: PredictionTargetKind
    selection_source: PredictionTargetSource

    provider: str = "SHOM"

    latitude: float | None = None
    longitude: float | None = None

    distance_km: float | None = None

    # Distance telle que renvoyée par le fournisseur.
    # On ne lui attribue pas encore d'unité.
    provider_distance: float | None = None

    official: bool | None = None
    coefficients_available: bool | None = None