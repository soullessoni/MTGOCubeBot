import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.api_client import CubeBotApiClient, CubeBotApiError
from bot.checks import is_admin, user_is_admin
from bot.cogs.session_flow import AssignmentActionView, _format_assignment_line

logger = logging.getLogger(__name__)

TERMINAL_JOB_STATUSES = ("SUCCEEDED", "FAILED")
POLL_INTERVAL_SECONDS = 5
POLL_MAX_ATTEMPTS = 120  # ~10 minutes, generous since a return trade needs a live human to accept


def _format_reconciliation(reconciliation: dict) -> str:
    still_owed = reconciliation.get("still_owed") or {}
    to_give_back = reconciliation.get("to_give_back") or {}

    if not still_owed and not to_give_back:
        return "Aucun écart — tout est revenu comme prévu."

    parts = []
    if still_owed:
        parts.append(f"Encore dû : {still_owed}")
    if to_give_back:
        parts.append(f"Excédent reçu à rendre : {to_give_back}")
    return "\n".join(parts)


def _format_integrity(result: dict) -> str:
    missing = result.get("missing") or {}
    extra = result.get("extra") or {}

    if not missing and not extra:
        return "Intégrité du cube OK — aucun écart avec la référence."

    parts = []
    if missing:
        parts.append(f"Manquant : {missing}")
    if extra:
        parts.append(f"En trop : {extra}")
    return "\n".join(parts)


class RetryButton(discord.ui.Button):
    def __init__(self, api_client: CubeBotApiClient, job_id: int):
        super().__init__(
            label="Relancer la récupération",
            style=discord.ButtonStyle.primary,
        )
        self.api_client = api_client
        self.job_id = job_id

    async def callback(self, interaction: discord.Interaction):
        if not user_is_admin(interaction.user):
            await interaction.response.send_message("Réservé aux admins.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            job = await self.api_client.retry_job(self.job_id)
        except CubeBotApiError as error:
            await interaction.followup.send(f"Erreur : {error.detail}", ephemeral=True)
            return

        await interaction.followup.send(f"Job #{job['id']} relancé.", ephemeral=True)


class GiveBackButton(discord.ui.Button):
    def __init__(
            self,
            api_client: CubeBotApiClient,
            mtgo_username: str,
            cards: dict,
            original_job_id: int,
    ):
        super().__init__(
            label="Rendre l'excédent",
            style=discord.ButtonStyle.danger,
        )
        self.api_client = api_client
        self.mtgo_username = mtgo_username
        self.cards = cards
        self.original_job_id = original_job_id

    async def callback(self, interaction: discord.Interaction):
        if not user_is_admin(interaction.user):
            await interaction.response.send_message("Réservé aux admins.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            job = await self.api_client.trigger_give_back(
                self.mtgo_username,
                self.cards,
                requested_by=f"discord:{interaction.user.id}",
                retry_of_job_id=self.original_job_id,
            )
        except CubeBotApiError as error:
            await interaction.followup.send(f"Erreur : {error.detail}", ephemeral=True)
            return

        await interaction.followup.send(
            f"Job #{job['id']} démarré (rendu de l'excédent à {self.mtgo_username}).",
            ephemeral=True,
        )


class CorrectiveActionView(discord.ui.View):
    def __init__(self, api_client: CubeBotApiClient, job: dict):
        super().__init__(timeout=3600)

        reconciliation = (job.get("result") or {}).get("reconciliation") or {}

        if reconciliation.get("still_owed"):
            self.add_item(RetryButton(api_client, job["id"]))

        if reconciliation.get("to_give_back"):
            self.add_item(GiveBackButton(
                api_client,
                job["mtgo_username"],
                reconciliation["to_give_back"],
                job["id"],
            ))


class MtgoAdminCog(commands.Cog):

    def __init__(
            self,
            bot: commands.Bot,
            api_client: CubeBotApiClient,
    ):
        self.bot = bot
        self.api_client = api_client
        self._background_tasks: set[asyncio.Task] = set()

    def _track_task(self, coro) -> asyncio.Task:
        # asyncio only holds a weak reference to a task's coroutine — a
        # task with no other reference can be garbage-collected mid-run.
        # Keeping it in this set until it finishes prevents that.
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task

    async def _trigger_and_poll(
            self,
            interaction: discord.Interaction,
            trigger,
            started_message: str,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        try:
            job = await trigger
        except CubeBotApiError as error:
            await interaction.followup.send(f"Erreur : {error.detail}", ephemeral=True)
            return

        await interaction.followup.send(
            f"Job #{job['id']} démarré ({started_message}).",
            ephemeral=True,
        )
        self._track_task(self._poll_and_report(interaction, job))

    async def _notify_affected_players(self, job: dict) -> None:
        """DM each player whose give didn't fully go through — either
        it failed outright (e.g. an insufficient ticket deposit
        cancelled the whole trade) or they didn't pick up everything
        offered — so they're not left wondering why nothing showed up
        on their MTGO account."""
        if job["job_type"] != "GIVE":
            return

        result = job.get("result") or {}
        failed = result.get("failed") or {}
        not_taken = result.get("not_taken") or {}

        affected = set(failed) | set(not_taken)
        if not affected:
            return

        session_id = job.get("session_id")
        if session_id is None:
            return

        try:
            session = await self.api_client.get_session(session_id)
        except CubeBotApiError as error:
            logger.warning(
                "Impossible de récupérer la session %s pour prévenir les joueurs : %s",
                session_id, error.detail,
            )
            return

        discord_ids_by_username = {
            assignment["mtgo_username"]: assignment["discord_user_id"]
            for assignment in session.get("assignments", [])
            if assignment.get("mtgo_username") and assignment.get("discord_user_id")
        }

        for mtgo_username in affected:
            discord_id = discord_ids_by_username.get(mtgo_username)
            if discord_id is None:
                continue

            if mtgo_username in failed:
                message = (
                    f"⚠️ Ta distribution pour la session {session_id} n'a pas pu être "
                    f"complétée : {failed[mtgo_username]}. L'admin va relancer une fois "
                    f"le souci réglé."
                )
            else:
                message = (
                    f"Pour la session {session_id}, tu n'as pas récupéré toutes les "
                    f"cartes proposées ({not_taken[mtgo_username]}) — vérifie ton "
                    f"échange MTGO, l'admin en a été informé."
                )

            try:
                user = await self.bot.fetch_user(int(discord_id))
                await user.send(message)
            except Exception:
                logger.exception(
                    "Impossible d'envoyer un MP à %s (discord_id=%s)",
                    mtgo_username, discord_id,
                )

    async def _notify_distributed_players(self, job: dict) -> None:
        """DM each player whose assignments this GIVE job just moved to
        DISTRIBUTED, with the same "J'ai reçu ces cartes" prompt
        `SessionFlowCog.complete_identification` sends at identification
        time — so a player gets it right away instead of having to
        reopen "Corriger mon pseudo MTGO" to trigger a fresh one. Fires
        even for a partial pool (some cards not_taken) — the player can
        confirm what they did receive."""
        if job["job_type"] != "GIVE":
            return

        result = job.get("result") or {}
        distributed = result.get("distributed") or {}
        if not distributed:
            return

        session_id = job.get("session_id")
        if session_id is None:
            return

        try:
            session = await self.api_client.get_session(session_id)
        except CubeBotApiError as error:
            logger.warning(
                "Impossible de récupérer la session %s pour notifier la distribution : %s",
                session_id, error.detail,
            )
            return

        assignments_by_id = {
            assignment["id"]: assignment
            for assignment in session.get("assignments", [])
        }
        session_flow_cog = self.bot.get_cog("SessionFlowCog")

        for mtgo_username, assignment_ids in distributed.items():
            group = [
                assignments_by_id[assignment_id]
                for assignment_id in assignment_ids
                if assignment_id in assignments_by_id
                and assignments_by_id[assignment_id]["status"] == "DISTRIBUTED"
            ]
            if not group:
                continue

            discord_id = group[0].get("discord_user_id")
            if discord_id is None:
                continue

            try:
                user = await self.bot.fetch_user(int(discord_id))
                await user.send(
                    f"Tes cartes de la session {session_id} sont prêtes — "
                    f"confirme leur réception ci-dessous :\n"
                    + "\n".join(_format_assignment_line(a) for a in group),
                    view=AssignmentActionView(session_flow_cog, group),
                )
            except Exception:
                logger.exception(
                    "Impossible d'envoyer le MP de distribution à %s (discord_id=%s)",
                    mtgo_username, discord_id,
                )

    async def _poll_and_report(
            self,
            interaction: discord.Interaction,
            job: dict,
    ) -> None:
        # The job just got triggered, so it's essentially never already
        # terminal — but skip the pointless first sleep in that case
        # instead of waiting a full interval before reporting.
        if job["status"] not in TERMINAL_JOB_STATUSES:
            for _ in range(POLL_MAX_ATTEMPTS):
                await asyncio.sleep(POLL_INTERVAL_SECONDS)

                try:
                    job = await self.api_client.get_job(job["id"])
                except CubeBotApiError as error:
                    logger.warning("Impossible de récupérer le job %s : %s", job["id"], error.detail)
                    continue

                if job["status"] in TERMINAL_JOB_STATUSES:
                    break

        view = None

        if job["status"] == "FAILED":
            message = f"Échec : {job.get('error_message') or 'erreur inconnue'}"
        elif job["job_type"] == "RETURN" and job["status"] == "SUCCEEDED":
            reconciliation = (job.get("result") or {}).get("reconciliation") or {}
            message = _format_reconciliation(reconciliation)
            if reconciliation.get("still_owed") or reconciliation.get("to_give_back"):
                view = CorrectiveActionView(self.api_client, job)
        elif job["job_type"] == "INTEGRITY_CHECK" and job["status"] == "SUCCEEDED":
            message = _format_integrity(job.get("result") or {})
        elif job["status"] == "SUCCEEDED":
            message = "Terminé avec succès."
        else:
            message = f"Toujours en cours après {POLL_MAX_ATTEMPTS * POLL_INTERVAL_SECONDS}s (statut : {job['status']}) — utilisez /mtgo-job-status pour vérifier plus tard."

        if job["status"] in TERMINAL_JOB_STATUSES:
            await self._notify_affected_players(job)
            await self._notify_distributed_players(job)

        await interaction.followup.send(
            f"Job #{job['id']} ({job['job_type']}) — {message}",
            ephemeral=True,
            view=view,
        )

    @app_commands.command(
        name="mtgo-give",
        description="Déclenche la distribution (création du binder) pour une session",
    )
    @app_commands.describe(
        session_id="Session de prêt",
    )
    @is_admin()
    async def mtgo_give(
            self,
            interaction: discord.Interaction,
            session_id: int,
    ):
        await self._trigger_and_poll(
            interaction,
            self.api_client.trigger_give(
                session_id,
                requested_by=f"discord:{interaction.user.id}",
            ),
            f"distribution, session {session_id}",
        )

    @app_commands.command(
        name="mtgo-return",
        description="Déclenche la récupération des cartes CONFIRMED d'un joueur",
    )
    @app_commands.describe(
        session_id="Session de prêt",
        mtgo_username="Pseudo MTGO exact du joueur",
    )
    @is_admin()
    async def mtgo_return(
            self,
            interaction: discord.Interaction,
            session_id: int,
            mtgo_username: str,
    ):
        await self._trigger_and_poll(
            interaction,
            self.api_client.trigger_return(
                session_id,
                mtgo_username,
                requested_by=f"discord:{interaction.user.id}",
            ),
            f"récupération, session {session_id}, {mtgo_username}",
        )

    @app_commands.command(
        name="mtgo-integrity-check",
        description="Vérifie l'intégrité du cube face à la référence",
    )
    @is_admin()
    async def mtgo_integrity_check(
            self,
            interaction: discord.Interaction,
    ):
        await self._trigger_and_poll(
            interaction,
            self.api_client.trigger_integrity_check(
                requested_by=f"discord:{interaction.user.id}",
            ),
            "vérification d'intégrité",
        )

    @app_commands.command(
        name="mtgo-job-status",
        description="Consulte le statut d'un job MTGO",
    )
    @app_commands.describe(
        job_id="Identifiant du job",
    )
    @is_admin()
    async def mtgo_job_status(
            self,
            interaction: discord.Interaction,
            job_id: int,
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            job = await self.api_client.get_job(job_id)
        except CubeBotApiError as error:
            await interaction.followup.send(f"Erreur : {error.detail}", ephemeral=True)
            return

        lines = [f"Job #{job['id']} ({job['job_type']}) — {job['status']}"]

        if job.get("log_output"):
            tail = "\n".join(job["log_output"].splitlines()[-10:])
            lines.append(f"```\n{tail}\n```")

        await interaction.followup.send("\n".join(lines), ephemeral=True)
