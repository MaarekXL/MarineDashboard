from abc import ABC, abstractmethod


class ProviderError(RuntimeError):
    """Erreur générique provenant d'une source externe."""


class ProviderConnectionError(ProviderError):
    """Impossible de joindre le fournisseur."""


class ProviderDataError(ProviderError):
    """Le fournisseur a renvoyé des données invalides."""


class BaseProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Nom du fournisseur."""
        raise NotImplementedError