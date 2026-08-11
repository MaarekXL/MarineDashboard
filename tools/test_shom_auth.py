from config import load_shom_settings

from providers import (
    ProviderConnectionError,
    ShomProvider,
)


def main() -> None:
    settings = load_shom_settings()

    if not settings.configured:
        print(
            "Identifiants SHOM absents."
        )

        print()
        print(
            "Variables attendues :"
        )
        print(
            "SHOM_SUBSCRIPTION_KEY"
        )
        print(
            "SHOM_USERNAME"
        )
        print(
            "SHOM_PASSWORD"
        )

        return

    provider = ShomProvider(
        subscription_key=(
            settings.subscription_key
        ),
        username=settings.username,
        password=settings.password,
        timeout=15.0,
    )

    print("Test accès SHOM...")
    print()

    try:
        spm = provider.check_spm_access()

        print(
            f"SUP Marée / SPM : "
            f"{'OK' if spm.allowed else 'REFUSÉ'}"
        )

        sapm = provider.check_sapm_access()

        print(
            f"SAPM            : "
            f"{'OK' if sapm.allowed else 'REFUSÉ'}"
        )

    except ProviderConnectionError as exc:
        print(
            f"Erreur : {exc}"
        )


if __name__ == "__main__":
    main()