from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.mtgo.dependencies import get_job_runner
from app.db.session import get_db
from app.models.loan_session import LoanSession
from app.schemas.mtgo.mtgo_job import (
    MtgoJobResponse,
    RetryJobRequest,
    TriggerGiveBackRequest,
    TriggerGiveRequest,
    TriggerIntegrityCheckRequest,
    TriggerReturnRequest,
)
from app.services.mtgo.mtgo_job_service import MtgoJobService
from app.use_cases.mtgo.retry_mtgo_job import RetryMtgoJobUseCase
from app.use_cases.mtgo.trigger_give_back_job import TriggerGiveBackJobUseCase
from app.use_cases.mtgo.trigger_give_job import TriggerGiveJobUseCase
from app.use_cases.mtgo.trigger_integrity_check_job import (
    TriggerIntegrityCheckJobUseCase,
)
from app.use_cases.mtgo.trigger_return_job import TriggerReturnJobUseCase

router = APIRouter(
    prefix="/mtgo",
    tags=["mtgo"],
)


def _get_session_or_404(
        session_id: int,
        db: Session,
) -> LoanSession:
    session = (
        db.query(LoanSession)
        .filter(LoanSession.id == session_id)
        .first()
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Loan session not found",
        )

    return session


@router.post(
    "/sessions/{session_id}/give",
    response_model=MtgoJobResponse,
)
def trigger_give(
        session_id: int,
        body: TriggerGiveRequest = TriggerGiveRequest(),
        db: Session = Depends(get_db),
        runner=Depends(get_job_runner),
):
    _get_session_or_404(session_id, db)

    use_case = TriggerGiveJobUseCase(
        MtgoJobService(db),
        runner,
    )

    return use_case.execute(
        session_id=session_id,
        requested_by=body.requested_by,
    )


@router.post(
    "/sessions/{session_id}/return",
    response_model=MtgoJobResponse,
)
def trigger_return(
        session_id: int,
        body: TriggerReturnRequest,
        db: Session = Depends(get_db),
        runner=Depends(get_job_runner),
):
    _get_session_or_404(session_id, db)

    use_case = TriggerReturnJobUseCase(
        MtgoJobService(db),
        runner,
    )

    return use_case.execute(
        session_id=session_id,
        mtgo_username=body.mtgo_username,
        requested_by=body.requested_by,
    )


@router.post(
    "/integrity-check",
    response_model=MtgoJobResponse,
)
def trigger_integrity_check(
        body: TriggerIntegrityCheckRequest = TriggerIntegrityCheckRequest(),
        db: Session = Depends(get_db),
        runner=Depends(get_job_runner),
):
    use_case = TriggerIntegrityCheckJobUseCase(
        MtgoJobService(db),
        runner,
    )

    return use_case.execute(
        requested_by=body.requested_by,
    )


@router.post(
    "/give-back",
    response_model=MtgoJobResponse,
)
def trigger_give_back(
        body: TriggerGiveBackRequest,
        db: Session = Depends(get_db),
        runner=Depends(get_job_runner),
):
    use_case = TriggerGiveBackJobUseCase(
        MtgoJobService(db),
        runner,
    )

    try:
        return use_case.execute(
            mtgo_username=body.mtgo_username,
            cards=body.cards,
            requested_by=body.requested_by,
            retry_of_job_id=body.retry_of_job_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.post(
    "/jobs/{job_id}/retry",
    response_model=MtgoJobResponse,
)
def retry_job(
        job_id: int,
        body: RetryJobRequest = RetryJobRequest(),
        db: Session = Depends(get_db),
        runner=Depends(get_job_runner),
):
    job_service = MtgoJobService(db)
    original_job = job_service.get(job_id)

    if original_job is None:
        raise HTTPException(
            status_code=404,
            detail="MTGO job not found",
        )

    use_case = RetryMtgoJobUseCase(
        job_service,
        runner,
    )

    return use_case.execute(
        original_job=original_job,
        requested_by=body.requested_by,
    )
