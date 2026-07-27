from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.mtgo.mtgo_job import MtgoJobResponse
from app.services.mtgo.mtgo_job_service import MtgoJobService

router = APIRouter(
    prefix="/mtgo",
    tags=["mtgo"],
)


@router.get(
    "/jobs/",
    response_model=list[MtgoJobResponse],
)
def list_jobs(
        session_id: int | None = None,
        limit: int = 50,
        db: Session = Depends(get_db),
):
    service = MtgoJobService(db)

    return service.list_recent(
        limit=limit,
        session_id=session_id,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=MtgoJobResponse,
)
def get_job(
        job_id: int,
        db: Session = Depends(get_db),
):
    service = MtgoJobService(db)
    job = service.get(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="MTGO job not found",
        )

    return job
