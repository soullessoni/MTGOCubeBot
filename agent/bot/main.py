import logging

import discord
from discord.ext import commands

from bot.api_client import CubeBotApiClient
from bot.config import BotConfig
from bot.cogs.mtgo_admin import MtgoAdminCog
from bot.cogs.session_flow import AssignmentGroupActionButton, SessionFlowCog
from bot.error_handler import handle_app_command_error

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
        self.tree.on_error = self._on_app_command_error

    async def _on_app_command_error(
            self,
            interaction: discord.Interaction,
            error: discord.app_commands.AppCommandError,
    ):
        await handle_app_command_error(interaction, error)

    async def setup_hook(self):
        # Registers the class (not an instance) so discord.py can match its
        # template regex against incoming custom_ids and rebuild the button
        # on demand — this is what makes assignment-group buttons on
        # messages sent by a previous process still work after a restart.
        # Must happen once here rather than per-view, since views built
        # later (e.g. inside AssignmentActionView) never get a chance to
        # register anything themselves once the original process is gone.
        self.add_dynamic_items(AssignmentGroupActionButton)

        await self.add_cog(
            SessionFlowCog(
                self,
                self.api_client,
                self.config.category_name,
                self.config.cleanup_interval_minutes,
            )
        )

        await self.add_cog(
            MtgoAdminCog(
                self,
                self.api_client,
            )
        )

        if self.config.guild_id:
            guild = discord.Object(id=self.config.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

            # Wipe any stale global registration from a previous run made
            # before DISCORD_GUILD_ID was set — otherwise Discord shows
            # both the guild-scoped command (instant, up to date) and the
            # old global one (up to an hour to update/remove) side by
            # side in the picker.
            self.tree.clear_commands(guild=None)
            await self.tree.sync()
        else:
            await self.tree.sync()

    async def on_interaction(self, interaction: discord.Interaction):
        # Deliberately logs only the interaction's shape, not its data —
        # modal submits carry the raw text a player typed (e.g. their MTGO
        # pseudo) and that shouldn't end up in plaintext logs.
        logging.info(
            "on_interaction: type=%s custom_id=%s command=%s",
            interaction.type,
            (interaction.data or {}).get("custom_id"),
            getattr(interaction.command, "qualified_name", None),
        )

    async def on_ready(self):
        logging.info(
            "Logged in as %s (id=%s)",
            self.user,
            self.user.id,
        )

        for guild in self.guilds:
            logging.info(
                "Connected to guild: %s (id=%s)",
                guild.name,
                guild.id,
            )


def main():
    config = BotConfig.from_env()
    api_client = CubeBotApiClient(base_url=config.backend_api_url)
    bot = CubeBot(config, api_client)

    bot.run(config.discord_token)


if __name__ == "__main__":
    main()
