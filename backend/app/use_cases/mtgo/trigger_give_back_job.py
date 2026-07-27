from app.models.mtgo_job import MtgoJob
from app.services.mtgo.mtgo_job_argv import build_job_argv
from app.services.mtgo.mtgo_job_service import MtgoJobService


class TriggerGiveBackJobUseCase:

    def __init__(
            self,
            job_service: MtgoJobService,
            runner,
    ):
        self.job_service = job_service
        self.runner = runner

    def execute(
            self,
            mtgo_username: str,
            cards: dict[str, int],
            requested_by: str | None = None,
            retry_of_job_id: int | None = None,
    ) -> MtgoJob:
        if not cards:
            raise ValueError("cards must not be empty")

        job = self.job_service.create(
            job_type="GIVE_BACK",
            mtgo_username=mtgo_username,
            params={"cards": cards},
            requested_by=requested_by,
            retry_of_job_id=retry_of_job_id,
        )

        argv = build_job_argv(
            "GIVE_BACK",
            mtgo_username=mtgo_username,
            params={"cards": cards},
            job_id=job.id,
        )

        self.runner.start(
            job.id,
            argv,
        )

        return job
