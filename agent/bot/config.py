import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class BotConfig:
    discord_token: str
    guild_id: int | None
    backend_api_url: str

    @classmethod
    def from_env(cls) -> "BotConfig":
        token = os.environ.get("DISCORD_BOT_TOKEN")

        if not token:
            raise RuntimeError(
                "DISCORD_BOT_TOKEN is not set. Copy .env.example to .env "
                "and fill it in."
            )

        guild_id_raw = os.environ.get("DISCORD_GUILD_ID")
        guild_id = int(guild_id_raw) if guild_id_raw else None

        backend_api_url = os.environ.get(
            "BACKEND_API_URL",
            "http://localhost:8000",
        )

        return cls(
            discord_token=token,
            guild_id=guild_id,
            backend_api_url=backend_api_url,
        )
