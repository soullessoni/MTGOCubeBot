import os
from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationConfig:
    webhook_url: str | None

    @classmethod
    def from_env(cls) -> "NotificationConfig":
        webhook_url = os.environ.get("DISCORD_ADMIN_WEBHOOK_URL")

        return cls(
            webhook_url=webhook_url,
        )
