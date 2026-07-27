from app.models.mtgo_job import MtgoJob
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
            requested_by: str | None = None,
    ) -> MtgoJob:
        job = self.job_service.create(
            job_type="RETURN",
            session_id=session_id,
            mtgo_username=mtgo_username,
            requested_by=requested_by,
        )

        argv = build_job_argv(
            "RETURN",
            session_id=session_id,
            mtgo_username=mtgo_username,
        )

        self.runner.start(
            job.id,
            argv,
        )

        return job
