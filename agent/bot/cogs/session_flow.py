import discord
from discord import app_commands
from discord.ext import commands

from bot.api_client import CubeBotApiClient, CubeBotApiError


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
    ):
        self.bot = bot
        self.api_client = api_client

    @app_commands.command(
        name="draft-session",
        description=(
            "Crée le salon d'identification pour une session de prêt "
            "existante"
        ),
    )
    @app_commands.describe(
        session_id="Identifiant de la session de prêt (voir le dashboard)",
    )
    async def draft_session(
            self,
            interaction: discord.Interaction,
            session_id: int,
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            session = self.api_client.get_session(session_id)
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

        channel = await interaction.guild.create_text_channel(
            name=f"draft-session-{session_id}",
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

    async def complete_identification(
            self,
            interaction: discord.Interaction,
            session_id: int,
            player_name: str,
            mtgo_username: str,
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            session = self.api_client.get_session(session_id)
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
                linked = self.api_client.link_discord_identity(
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

            lines = [f"**Session de prêt #{session_id} — tes cartes**"]

            for assignment in linked_assignments:
                lines.append(
                    f"- {_card_label(assignment)} "
                    f"(statut : {assignment['status']})"
                )

            await dm_channel.send("\n".join(lines))

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
            "Pseudo confirmé, tu as reçu tes cartes en message privé.",
            ephemeral=True,
        )

    async def handle_assignment_action(
            self,
            interaction: discord.Interaction,
            assignment_id: int,
            action: str,
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            if action == "confirm":
                result = self.api_client.confirm_assignment(
                    assignment_id,
                )
            else:
                result = self.api_client.return_assignment(
                    assignment_id,
                )
        except CubeBotApiError as error:
            await interaction.followup.send(
                f"Action impossible : {error.detail}",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"Statut mis à jour : {result['status']}",
            ephemeral=True,
        )

        if interaction.message:
            await interaction.message.edit(
                view=AssignmentActionView(self, result),
            )
