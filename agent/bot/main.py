import logging

import discord
from discord.ext import commands

from bot.api_client import CubeBotApiClient
from bot.config import BotConfig
from bot.cogs.session_flow import SessionFlowCog

logging.basicConfig(level=logging.INFO)


class CubeBot(commands.Bot):

    def __init__(
            self,
            config: BotConfig,
            api_client: CubeBotApiClient,
    ):
        intents = discord.Intents.default()

        super().__init__(
            command_prefix="!",
            intents=intents,
        )

        self.config = config
        self.api_client = api_client

    async def setup_hook(self):
        await self.add_cog(
            SessionFlowCog(self, self.api_client)
        )

        if self.config.guild_id:
            guild = discord.Object(id=self.config.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()


def main():
    config = BotConfig.from_env()
    api_client = CubeBotApiClient(base_url=config.backend_api_url)
    bot = CubeBot(config, api_client)

    bot.run(config.discord_token)


if __name__ == "__main__":
    main()
