from app.models.mtgo_job import MtgoJob
from app.services.mtgo.mtgo_account_resolver import resolve_mtgo_account
from app.services.mtgo.mtgo_job_argv import build_job_argv
from app.services.mtgo.mtgo_job_service import MtgoJobService


class TriggerIntegrityCheckJobUseCase:

    def __init__(
            self,
            job_service: MtgoJobService,
            runner,
    ):
        self.job_service = job_service
        self.runner = runner

    def execute(
            self,
            cube_instance_id: int,
            requested_by: str | None = None,
    ) -> MtgoJob:
        job = self.job_service.create(
            job_type="INTEGRITY_CHECK",
            cube_instance_id=cube_instance_id,
            requested_by=requested_by,
        )

        argv = build_job_argv(
            "INTEGRITY_CHECK",
            cube_instance_id=cube_instance_id,
        )

        mtgo_account_id, mtgo_account_username = resolve_mtgo_account(
            self.job_service.db,
            cube_instance_id,
        )

        started = self.runner.start(
            job.id,
            argv,
            mtgo_account_id=mtgo_account_id,
            mtgo_account_username=mtgo_account_username,
        )

        if not started:
            return self.job_service.mark_failed(
                job,
                "Le compte MTGO ciblé est déjà occupé par un autre job.",
            )

        return job
