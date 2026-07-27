from app.models.mtgo_job import MtgoJob
from app.services.mtgo.mtgo_job_argv import build_job_argv
from app.services.mtgo.mtgo_job_service import MtgoJobService


class RetryMtgoJobUseCase:
    """Re-issue a job identical in kind to `original_job`, based purely
    on its stored fields — covers both "retry a still_owed RETURN" and
    "generically retry anything that failed outright," since both are
    just re-running the same command."""

    def __init__(
            self,
            job_service: MtgoJobService,
            runner,
    ):
        self.job_service = job_service
        self.runner = runner

    def execute(
            self,
            original_job: MtgoJob,
            requested_by: str | None = None,
    ) -> MtgoJob:
        job = self.job_service.create(
            job_type=original_job.job_type,
            session_id=original_job.session_id,
            mtgo_username=original_job.mtgo_username,
            params=original_job.params,
            requested_by=requested_by,
            retry_of_job_id=original_job.id,
        )

        argv = build_job_argv(
            original_job.job_type,
            session_id=original_job.session_id,
            mtgo_username=original_job.mtgo_username,
            params=original_job.params,
            job_id=job.id,
        )

        self.runner.start(
            job.id,
            argv,
        )

        return job
