import logging
import re

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.api_client import CubeBotApiClient, CubeBotApiError

logger = logging.getLogger(__name__)

SESSION_CHANNEL_PATTERN = re.compile(r"^draft-session-(\d+)$")
TERMINAL_SESSION_STATUSES = ("COMPLETED", "CANCELLED")


def _card_label(assignment: dict) -> str:
    return assignment.get("card_name") or f"Carte #{assignment['card_id']}"


class MtgoUsernameModal(discord.ui.Modal, title="Confirme ton pseudo MTGO"):
    mtgo_username = discord.ui.TextInput(
        label="Pseudo MTGO",
        placeholder="Ton nom d'utilisateur exact sur Magic Online",
        max_length=255,
    )

    def __init__(
            self,
            cog: "SessionFlowCog",
            session_id: int,
            player_name: str,
    ):
        super().__init__()
        self.cog = cog
        self.session_id = session_id
        self.player_name = player_name

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.complete_identification(
            interaction,
            self.session_id,
            self.player_name,
            self.mtgo_username.value,
        )


class PlayerSelect(discord.ui.Select):

    def __init__(
            self,
            cog: "SessionFlowCog",
            session_id: int,
            player_names: list[str],
    ):
        options = [
            discord.SelectOption(label=name, value=name)
            for name in player_names
        ]

        super().__init__(
            placeholder="Sélectionne ton nom dans la liste",
            options=options,
            custom_id=f"session:{session_id}:player-select",
        )

        self.cog = cog
        self.session_id = session_id

    async def callback(self, interaction: discord.Interaction):
        player_name = self.values[0]

        await interaction.response.send_modal(
            MtgoUsernameModal(
                self.cog,
                self.session_id,
                player_name,
            )
        )


class PlayerSelectView(discord.ui.View):
    """Posted in the public session channel. Not player-restricted at the
    Discord permission level — the channel only ever shows player names,
    never card assignments, so it's safe for everyone in it to see.
    """

    def __init__(
            self,
            cog: "SessionFlowCog",
            session_id: int,
            player_names: list[str],
    ):
        super().__init__(timeout=None)
        self.add_item(
            PlayerSelect(cog, session_id, player_names)
        )


class CorrectMtgoUsernameView(discord.ui.View):
    """Sent alongside the initial DM card list. Lets the player reopen the
    pseudo modal if they mistyped it — resubmitting restarts identification
    from that point (re-links every assignment and resends a fresh card
    list + action buttons).
    """

    def __init__(
            self,
            cog: "SessionFlowCog",
            session_id: int,
            player_name: str,
    ):
        super().__init__(timeout=None)
        self.cog = cog
        self.session_id = session_id
        self.player_name = player_name

        button = discord.ui.Button(
            label="Corriger mon pseudo MTGO",
            style=discord.ButtonStyle.secondary,
            custom_id=f"session:{session_id}:correct:{player_name}",
        )

        async def callback(interaction: discord.Interaction):
            await interaction.response.send_modal(
                MtgoUsernameModal(
                    self.cog,
                    self.session_id,
                    self.player_name,
                )
            )

        button.callback = callback

        self.add_item(button)


class AssignmentActionView(discord.ui.View):
    """Sent by DM for a single card assignment. Shows the one action that
    makes sense for the assignment's current status, if any.

    Note: because the assignment id is baked into each button's callback
    closure, these views are not restored automatically if the bot process
    restarts — a player would need to re-run /draft-session identification
    (or the bot would need a persistent-view registry keyed by custom_id,
    which is a reasonable follow-up once this is running for real).
    """

    def __init__(
            self,
            cog: "SessionFlowCog",
            assignment: dict,
    ):
        super().__init__(timeout=None)
        self.cog = cog
        self.assignment_id = assignment["id"]

        status = assignment["status"]

        if status == "DISTRIBUTED":
            self._add_action_button(
                "J'ai reçu cette carte",
                "confirm",
                discord.ButtonStyle.success,
            )
        elif status == "CONFIRMED":
            self._add_action_button(
                "J'ai rendu cette carte",
                "return",
                discord.ButtonStyle.primary,
            )

    def _add_action_button(
            self,
            label: str,
            action: str,
            style: discord.ButtonStyle,
    ):
        button = discord.ui.Button(
            label=label,
            style=style,
            custom_id=f"assignment:{self.assignment_id}:{action}",
        )

        async def callback(interaction: discord.Interaction):
            logger.info(
                "Button clicked: assignment=%s action=%s",
                self.assignment_id,
                action,
            )
            await self.cog.handle_assignment_action(
                interaction,
                self.assignment_id,
                action,
            )

        button.callback = callback

        self.add_item(button)


class SessionFlowCog(commands.Cog):

    def __init__(
            self,
            bot: commands.Bot,
            api_client: CubeBotApiClient,
            category_name: str,
            cleanup_interval_minutes: float,
    ):
        self.bot = bot
        self.api_client = api_client
        self.category_name = category_name

        self.cleanup_finished_sessions.change_interval(
            minutes=cleanup_interval_minutes,
        )
        self.cleanup_finished_sessions.start()

    def cog_unload(self):
        self.cleanup_finished_sessions.cancel()

    def _find_category(
            self,
            guild: discord.Guild,
    ) -> discord.CategoryChannel | None:
        return discord.utils.get(
            guild.categories,
            name=self.category_name,
        )

    @tasks.loop(minutes=2)
    async def cleanup_finished_sessions(self):
        for guild in self.bot.guilds:
            category = self._find_category(guild)

            if category is None:
                continue

            for channel in category.text_channels:
                match = SESSION_CHANNEL_PATTERN.match(channel.name)

                if not match:
                    continue

                session_id = int(match.group(1))

                try:
                    session = await self.api_client.get_session(
                        session_id,
                    )
                except CubeBotApiError as error:
                    logger.warning(
                        "Impossible de vérifier la session %s : %s",
                        session_id,
                        error.detail,
                    )
                    continue

                if session["status"] in TERMINAL_SESSION_STATUSES:
                    logger.info(
                        "Session %s %s — suppression du salon %s",
                        session_id,
                        session["status"],
                        channel.name,
                    )

                    await channel.delete(
                        reason=(
                            f"Session de prêt {session_id} "
                            f"{session['status'].lower()}"
                        )
                    )

    @cleanup_finished_sessions.before_loop
    async def before_cleanup_finished_sessions(self):
        await self.bot.wait_until_ready()

    @app_commands.command(
        name="draft-session",
        description=(
            "Crée le salon d'identification pour une session de prêt "
            "existante"
        ),
    )
    @app_commands.describe(
        session_id="Session de prêt active à ouvrir",
    )
    async def draft_session(
            self,
            interaction: discord.Interaction,
            session_id: int,
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            session = await self.api_client.get_session(session_id)
        except CubeBotApiError as error:
            await interaction.followup.send(
                f"Session introuvable ou erreur API : {error.detail}",
                ephemeral=True,
            )
            return

        player_names = sorted({
            assignment["player_name"]
            for assignment in session["assignments"]
        })

        if not player_names:
            await interaction.followup.send(
                "Cette session n'a aucune carte assignée.",
                ephemeral=True,
            )
            return

        channel_name = f"draft-session-{session_id}"

        existing_channel = discord.utils.get(
            interaction.guild.text_channels,
            name=channel_name,
        )

        if existing_channel is not None:
            await interaction.followup.send(
                f"Le salon existe déjà : {existing_channel.mention}",
                ephemeral=True,
            )
            return

        category = self._find_category(interaction.guild)

        channel = await interaction.guild.create_text_channel(
            name=channel_name,
            category=category,
        )

        if category is None:
            await interaction.followup.send(
                f"⚠️ Catégorie \"{self.category_name}\" introuvable sur ce "
                f"serveur — le salon a été créé hors catégorie.",
                ephemeral=True,
            )

        await channel.send(
            f"**Session de prêt #{session_id}**\n"
            f"Joueurs concernés : {', '.join(player_names)}\n\n"
            f"Clique sur ton nom ci-dessous pour confirmer ton pseudo "
            f"MTGO et recevoir en message privé la liste de tes cartes.",
            view=PlayerSelectView(self, session_id, player_names),
        )

        await interaction.followup.send(
            f"Salon créé : {channel.mention}",
            ephemeral=True,
        )

    @draft_session.autocomplete("session_id")
    async def draft_session_id_autocomplete(
            self,
            interaction: discord.Interaction,
            current: str,
    ) -> list[app_commands.Choice[int]]:
        logger.info(
            "Autocomplete session_id invoked, current=%r",
            current,
        )

        try:
            sessions = await self.api_client.list_sessions()
        except CubeBotApiError as error:
            logger.warning(
                "Autocomplete failed to list sessions: %s",
                error.detail,
            )
            return []

        choices = []

        for session in sessions:
            if session["status"] in TERMINAL_SESSION_STATUSES:
                continue

            players = sorted({
                assignment["player_name"]
                for assignment in session["assignments"]
            })

            label = (
                f"#{session['id']} ({session['status']}) — "
                f"{', '.join(players) if players else 'aucun joueur'}"
            )[:100]

            if current and current not in str(session["id"]) \
                    and current.lower() not in label.lower():
                continue

            choices.append(
                app_commands.Choice(name=label, value=session["id"])
            )

        return choices[:25]

    async def complete_identification(
            self,
            interaction: discord.Interaction,
            session_id: int,
            player_name: str,
            mtgo_username: str,
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            session = await self.api_client.get_session(session_id)
        except CubeBotApiError as error:
            await interaction.followup.send(
                f"Erreur lors de la récupération de la session : "
                f"{error.detail}",
                ephemeral=True,
            )
            return

        matching_assignments = [
            assignment
            for assignment in session["assignments"]
            if assignment["player_name"] == player_name
        ]

        linked_assignments = []

        for assignment in matching_assignments:
            try:
                linked = await self.api_client.link_discord_identity(
                    assignment["id"],
                    str(interaction.user.id),
                    mtgo_username,
                )
                linked_assignments.append(linked)
            except CubeBotApiError as error:
                await interaction.followup.send(
                    f"Erreur lors de la liaison de "
                    f"{_card_label(assignment)} : {error.detail}",
                    ephemeral=True,
                )

        if not linked_assignments:
            return

        try:
            dm_channel = await interaction.user.create_dm()

            lines = [
                f"**Session de prêt #{session_id} — tes cartes**",
                f"Identifié comme **{player_name}**, "
                f"pseudo MTGO enregistré : **{mtgo_username}**",
                "",
            ]

            for assignment in linked_assignments:
                lines.append(
                    f"- {_card_label(assignment)} "
                    f"(statut : {assignment['status']})"
                )

            await dm_channel.send(
                "\n".join(lines),
                view=CorrectMtgoUsernameView(
                    self,
                    session_id,
                    player_name,
                ),
            )

            for assignment in linked_assignments:
                await dm_channel.send(
                    _card_label(assignment),
                    view=AssignmentActionView(self, assignment),
                )

        except discord.Forbidden:
            await interaction.followup.send(
                "Je n'arrive pas à t'envoyer de message privé — vérifie "
                "tes paramètres de confidentialité Discord (autoriser "
                "les MP des membres du serveur).",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"Pseudo MTGO enregistré : **{mtgo_username}** — tu as reçu "
            f"tes cartes en message privé.",
            ephemeral=True,
        )

    async def handle_assignment_action(
            self,
            interaction: discord.Interaction,
            assignment_id: int,
            action: str,
    ):
        try:
            if action == "confirm":
                result = await self.api_client.confirm_assignment(
                    assignment_id,
                )
            else:
                result = await self.api_client.return_assignment(
                    assignment_id,
                )
        except CubeBotApiError as error:
            await interaction.response.send_message(
                f"Action impossible : {error.detail}",
                ephemeral=True,
            )
            return

        # Respond by editing the clicked message directly, in one step —
        # more reliably reflected client-side than defer + a separate
        # followup + a separate message.edit() call.
        await interaction.response.edit_message(
            content=(
                f"{_card_label(result)} — statut : {result['status']}"
            ),
            view=AssignmentActionView(self, result),
        )
