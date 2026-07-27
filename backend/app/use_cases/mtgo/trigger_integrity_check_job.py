from app.models.mtgo_job import MtgoJob
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
            requested_by: str | None = None,
    ) -> MtgoJob:
        job = self.job_service.create(
            job_type="INTEGRITY_CHECK",
            requested_by=requested_by,
        )

        argv = build_job_argv(
            "INTEGRITY_CHECK",
        )

        self.runner.start(
            job.id,
            argv,
        )

        return job
