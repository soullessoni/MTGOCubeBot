import logging
import re

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.api_client import CubeBotApiClient, CubeBotApiError

logger = logging.getLogger(__name__)

SESSION_CHANNEL_PATTERN = re.compile(r"^draft-session-(\d+)$")
TERMINAL_SESSION_STATUSES = ("COMPLETED", "CANCELLED")

# custom_id shape for the assignment-group action button:
#   assignment-group:<id1>-<id2>-...:<action>
# Hyphen-joined ids rather than comma/colon-separated — colons already
# delimit the three top-level segments, and a hyphen can't appear in an
# int id, so there's no ambiguity when splitting back apart. Encoding the
# full id list (not just the first one) plus the action into the
# custom_id is what lets AssignmentGroupActionButton.from_custom_id
# rebuild a working item after a bot restart, with no dependency on the
# original Python object that built the button still being alive.
ASSIGNMENT_GROUP_CUSTOM_ID_PATTERN = re.compile(
    r"^assignment-group:(?P<ids>\d+(?:-\d+)*):(?P<action>confirm|return)$"
)


def _card_label(assignment: dict) -> str:
    return assignment.get("card_name") or f"Carte #{assignment['card_id']}"


def _format_assignment_line(assignment: dict) -> str:
    return f"- {_card_label(assignment)} (statut : {assignment['status']})"


def _group_by_status(assignments: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}

    for assignment in assignments:
        groups.setdefault(assignment["status"], []).append(assignment)

    return groups


def _encode_assignment_group_custom_id(
        assignment_ids: list[int],
        action: str,
) -> str:
    ids_segment = "-".join(str(assignment_id) for assignment_id in assignment_ids)
    return f"assignment-group:{ids_segment}:{action}"


def _decode_assignment_group_match(
        match: re.Match[str],
) -> tuple[list[int], str]:
    assignment_ids = [
        int(part) for part in match.group("ids").split("-")
    ]
    action = match.group("action")
    return assignment_ids, action


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

    Note: like AssignmentActionView used to be, PlayerSelect's callback
    is a plain closure holding a `cog` reference, so this view is not
    restored after a bot restart either. Its custom_id already encodes
    everything needed (session_id) to rebuild via a discord.ui.DynamicItem
    the same way AssignmentGroupActionButton does — left as a follow-up
    rather than done here, to keep this change scoped to the assignment
    action buttons.
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

    Note: same restart-survival gap as PlayerSelect above — the button's
    callback closure holds `self.cog`/`self.session_id`/`self.player_name`
    directly rather than decoding them from the custom_id via a
    discord.ui.DynamicItem. Left as a follow-up alongside PlayerSelect.
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


class AssignmentGroupActionButton(
        discord.ui.DynamicItem[discord.ui.Button],
        template=ASSIGNMENT_GROUP_CUSTOM_ID_PATTERN,
):
    """The confirm/return button for a group of card assignments, as a
    discord.ui.DynamicItem (discord.py 2.4+) rather than a plain
    discord.ui.Button with an inline closure callback.

    A closure captures its assignment ids and cog reference in the
    Python object that built it — fine for the process that sent the
    message, but useless after a restart, since Discord only re-sends
    the interaction's custom_id, never the original view object. A
    DynamicItem instead gets rebuilt on demand: discord.py matches the
    incoming custom_id against `template` and calls `from_custom_id`,
    which decodes the assignment ids and action straight out of the
    custom_id string (see ASSIGNMENT_GROUP_CUSTOM_ID_PATTERN), so the
    button keeps working even for messages sent by a previous process —
    as long as this class is registered once via
    `bot.add_dynamic_items(...)` in CubeBot.setup_hook.
    """

    def __init__(
            self,
            assignment_ids: list[int],
            action: str,
            label: str,
            style: discord.ButtonStyle,
    ):
        super().__init__(
            discord.ui.Button(
                label=label,
                style=style,
                custom_id=_encode_assignment_group_custom_id(
                    assignment_ids,
                    action,
                ),
            )
        )
        self.assignment_ids = assignment_ids
        self.action = action

    @classmethod
    async def from_custom_id(
            cls,
            interaction: discord.Interaction,
            item: discord.ui.Item,
            match: re.Match[str],
            /,
    ) -> "AssignmentGroupActionButton":
        assignment_ids, action = _decode_assignment_group_match(match)

        # Reconstructed from an already-sent message, so label/style just
        # mirror what's already on screen — only assignment_ids/action
        # (decoded above) matter for handling the click itself.
        return cls(
            assignment_ids,
            action,
            label=item.label,
            style=item.style,
        )

    async def callback(self, interaction: discord.Interaction):
        logger.info(
            "Button clicked: assignments=%s action=%s",
            self.assignment_ids,
            self.action,
        )

        cog = interaction.client.get_cog("SessionFlowCog")
        await cog.handle_assignment_action(
            interaction,
            self.assignment_ids,
            self.action,
        )


class AssignmentActionView(discord.ui.View):
    """Sent by DM for a group of card assignments that share the same
    status. Shows the one action that makes sense for that status, if
    any, applied to every card in the group at once — a player usually
    has several cards moving through the same step together, so one
    button acting on the whole group beats one message+button per card
    (and grammar/labels need to say "ces cartes", not "cette carte",
    once there's more than one).

    The group action button is an AssignmentGroupActionButton
    (discord.ui.DynamicItem) rather than a plain button with a closure,
    specifically so it survives a bot restart — see that class's
    docstring. This view itself carries no state beyond what's needed
    to build the button; it isn't what makes the button restart-safe.
    """

    def __init__(
            self,
            cog: "SessionFlowCog",
            assignments: list[dict],
    ):
        super().__init__(timeout=None)
        self.cog = cog
        self.assignment_ids = [assignment["id"] for assignment in assignments]

        status = assignments[0]["status"]
        plural = len(assignments) > 1

        if status == "DISTRIBUTED":
            self._add_action_button(
                "J'ai reçu ces cartes" if plural else "J'ai reçu cette carte",
                "confirm",
                discord.ButtonStyle.success,
            )
        elif status == "CONFIRMED":
            self._add_action_button(
                "J'ai rendu ces cartes" if plural else "J'ai rendu cette carte",
                "return",
                discord.ButtonStyle.primary,
            )

    def _add_action_button(
            self,
            label: str,
            action: str,
            style: discord.ButtonStyle,
    ):
        self.add_item(
            AssignmentGroupActionButton(
                self.assignment_ids,
                action,
                label,
                style,
            )
        )


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
                lines.append(_format_assignment_line(assignment))

            await dm_channel.send(
                "\n".join(lines),
                view=CorrectMtgoUsernameView(
                    self,
                    session_id,
                    player_name,
                ),
            )

            for status, group in _group_by_status(linked_assignments).items():
                if status not in ("DISTRIBUTED", "CONFIRMED"):
                    continue

                await dm_channel.send(
                    "\n".join(_format_assignment_line(a) for a in group),
                    view=AssignmentActionView(self, group),
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
            assignment_ids: list[int],
            action: str,
    ):
        results = []
        errors = []

        for assignment_id in assignment_ids:
            try:
                if action == "confirm":
                    result = await self.api_client.confirm_assignment(
                        assignment_id,
                    )
                else:
                    result = await self.api_client.return_assignment(
                        assignment_id,
                    )
                results.append(result)
            except CubeBotApiError as error:
                errors.append((assignment_id, error.detail))

        if not results:
            await interaction.response.send_message(
                f"Action impossible : {errors[0][1]}",
                ephemeral=True,
            )
            return

        lines = [_format_assignment_line(result) for result in results]

        if errors:
            lines.append("")
            lines.append(
                "⚠️ Une erreur est survenue pour au moins une carte — "
                "relance l'action ou préviens un admin."
            )

        # Respond by editing the clicked message directly, in one step —
        # more reliably reflected client-side than defer + a separate
        # followup + a separate message.edit() call.
        await interaction.response.edit_message(
            content="\n".join(lines),
            view=AssignmentActionView(self, results),
        )
