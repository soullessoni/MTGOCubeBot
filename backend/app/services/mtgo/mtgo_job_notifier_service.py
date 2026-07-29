import logging

import httpx

from app.core.notification_config import NotificationConfig
from app.models.mtgo_job import MtgoJob

logger = logging.getLogger(__name__)


def _format_card_counts(counts: dict) -> str:
    return ", ".join(
        f"{name} x{quantity}"
        for name, quantity in counts.items()
    )


def _format_nested_card_counts(nested: dict) -> str:
    return "; ".join(
        f"{player} ({_format_card_counts(counts)})"
        for player, counts in nested.items()
        if counts
    )


def build_notification_message(job: MtgoJob) -> str | None:
    """Pure function deciding whether `job`'s terminal state warrants
    proactively alerting an admin, and if so, what to say. Returns
    `None` for anything routine (a clean SUCCEEDED job, or a job/result
    shape this function doesn't recognize) so the caller can treat
    `None` as "do nothing"."""
    if job.status == "FAILED":
        return (
            f"⚠️ Job #{job.id} ({job.job_type}) a échoué : "
            f"{job.error_message or 'erreur inconnue'}"
        )

    if job.status != "SUCCEEDED" or not isinstance(job.result, dict):
        return None

    if job.job_type == "GIVE":
        not_taken = job.result.get("not_taken") or {}

        if not not_taken:
            return None

        return (
            f"⚠️ Job #{job.id} (GIVE, session {job.session_id}) terminé avec un écart — "
            f"non récupéré par le joueur : {_format_nested_card_counts(not_taken)}"
        )

    if job.job_type == "RETURN":
        reconciliation = job.result.get("reconciliation") or {}
        still_owed = reconciliation.get("still_owed") or {}
        to_give_back = reconciliation.get("to_give_back") or {}

        if not still_owed and not to_give_back:
            return None

        details = []

        if still_owed:
            details.append(f"encore dû : {_format_card_counts(still_owed)}")

        if to_give_back:
            details.append(f"excédent à rendre : {_format_card_counts(to_give_back)}")

        return (
            f"⚠️ Job #{job.id} (RETURN, session {job.session_id}, {job.mtgo_username}) "
            f"terminé avec un écart — {' / '.join(details)}"
        )

    if job.job_type == "INTEGRITY_CHECK":
        missing = job.result.get("missing") or {}
        extra = job.result.get("extra") or {}

        if not missing and not extra:
            return None

        details = []

        if missing:
            details.append(f"manquant : {_format_card_counts(missing)}")

        if extra:
            details.append(f"en trop : {_format_card_counts(extra)}")

        return (
            f"⚠️ Job #{job.id} (INTEGRITY_CHECK) terminé avec un écart — "
            f"{' / '.join(details)}"
        )

    return None


class MtgoJobNotifierService:

    def __init__(
            self,
            config: NotificationConfig,
    ):
        self.config = config
        self.client = httpx.Client()

    def notify(
            self,
            job: MtgoJob,
    ) -> None:
        message = build_notification_message(job)

        if message is None:
            return

        if self.config.webhook_url is None:
            logger.info(
                "Skipping admin notification for job #%s: no Discord webhook configured",
                job.id,
            )
            return

        try:
            self.client.post(
                self.config.webhook_url,
                json={"content": message},
            )
        except Exception:
            logger.exception(
                "Failed to send Discord notification for job #%s",
                job.id,
            )
