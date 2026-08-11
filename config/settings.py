import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ShomSettings:
    subscription_key: str | None
    username: str | None
    password: str | None

    @property
    def configured(self) -> bool:
        return bool(
            self.subscription_key
            and self.username
            and self.password
        )


def load_shom_settings() -> ShomSettings:
    return ShomSettings(
        subscription_key=os.getenv(
            "SHOM_SUBSCRIPTION_KEY"
        ),
        username=os.getenv(
            "SHOM_USERNAME"
        ),
        password=os.getenv(
            "SHOM_PASSWORD"
        ),
    )