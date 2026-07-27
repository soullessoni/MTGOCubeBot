import logging

import discord
from discord import app_commands

logger = logging.getLogger(__name__)


async def handle_app_command_error(
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
) -> None:
    """Shared `CommandTree.on_error` handler — without this, a failed
    `@is_admin()` check (or any other app_commands.CheckFailure) surfaces
    to the user as a raw "The application did not respond" instead of a
    readable message."""
    if isinstance(error, app_commands.CheckFailure):
        message = "Réservé aux admins."
    else:
        logger.exception(
            "Unhandled app command error",
            exc_info=error,
        )
        message = "Une erreur est survenue."

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)
