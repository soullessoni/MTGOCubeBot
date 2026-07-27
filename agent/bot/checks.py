import discord
from discord import app_commands

ADMIN_ROLE_NAME = "Admin"


def user_is_admin(user: discord.Member | discord.User) -> bool:
    """True if `user` has the guild's "Administrator" permission or a
    role literally named "Admin". `discord.User` (DMs, no guild context)
    never has `guild_permissions`/`roles`, so it's always False there —
    these admin actions are guild-only."""
    guild_permissions = getattr(user, "guild_permissions", None)
    if guild_permissions is not None and guild_permissions.administrator:
        return True

    roles = getattr(user, "roles", None)
    if roles is not None:
        return discord.utils.get(roles, name=ADMIN_ROLE_NAME) is not None

    return False


def is_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        return user_is_admin(interaction.user)

    return app_commands.check(predicate)
