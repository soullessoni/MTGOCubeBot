import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.api_client import CubeBotApiClient, CubeBotApiError
from bot.checks import is_admin, user_is_admin

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

    async def _poll_and_report(
            self,
            interaction: discord.Interaction,
            job: dict,
    ) -> None:
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
