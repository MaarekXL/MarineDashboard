from providers import (
    ProviderConnectionError,
    ProviderDataError,
    ShomProvider,
)


def main() -> None:
    provider = ShomProvider(
        timeout=15.0
    )

    print("Connexion au SHOM...")
    print()

    try:
        harbors = provider.get_harbors()

    except ProviderConnectionError as exc:
        print(
            "ERREUR RÉSEAU :",
            exc,
        )
        return

    except ProviderDataError as exc:
        print(
            "ERREUR DE DONNÉES :",
            exc,
        )
        return

    print(
        f"{len(harbors)} ports/sites "
        "récupérés."
    )

    print()
    print("Premiers résultats :")
    print()

    for harbor in harbors[:20]:
        print(
            f"{harbor.cst:<12} "
            f"{harbor.name:<30} "
            f"{harbor.country:<15} "
            f"UTC={harbor.default_utc:<4} "
            f"Officiel={harbor.official}"
        )


if __name__ == "__main__":
    main()