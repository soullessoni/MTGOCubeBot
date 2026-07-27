from app.models.mtgo_job import MtgoJob


class MtgoJobService:

    def __init__(
            self,
            db,
    ):
        self.db = db

    def create(
            self,
            job_type: str,
            session_id: int | None = None,
            mtgo_username: str | None = None,
            params: dict | None = None,
            requested_by: str | None = None,
            retry_of_job_id: int | None = None,
    ) -> MtgoJob:
        job = MtgoJob(
            job_type=job_type,
            status="PENDING",
            session_id=session_id,
            mtgo_username=mtgo_username,
            params=params,
            requested_by=requested_by,
            retry_of_job_id=retry_of_job_id,
            log_output="",
        )

        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        return job

    def get(
            self,
            job_id: int,
    ) -> MtgoJob | None:
        return (
            self.db.query(MtgoJob)
            .filter(MtgoJob.id == job_id)
            .first()
        )

    def list_recent(
            self,
            limit: int = 50,
            session_id: int | None = None,
    ) -> list[MtgoJob]:
        query = self.db.query(MtgoJob)

        if session_id is not None:
            query = query.filter(MtgoJob.session_id == session_id)

        return (
            query
            .order_by(MtgoJob.id.desc())
            .limit(limit)
            .all()
        )
