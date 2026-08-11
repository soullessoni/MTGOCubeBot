from app.models.mtgo_job import MtgoJob
from app.services.mtgo.mtgo_account_resolver import resolve_mtgo_account
from app.services.mtgo.mtgo_job_argv import build_job_argv
from app.services.mtgo.mtgo_job_service import MtgoJobService


class TriggerReturnJobUseCase:

    def __init__(
            self,
            job_service: MtgoJobService,
            runner,
    ):
        self.job_service = job_service
        self.runner = runner

    def execute(
            self,
            session_id: int,
            mtgo_username: str,
            cube_instance_id: int | None = None,
            requested_by: str | None = None,
    ) -> MtgoJob:
        job = self.job_service.create(
            job_type="RETURN",
            session_id=session_id,
            cube_instance_id=cube_instance_id,
            mtgo_username=mtgo_username,
            requested_by=requested_by,
        )

        argv = build_job_argv(
            "RETURN",
            session_id=session_id,
            mtgo_username=mtgo_username,
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
