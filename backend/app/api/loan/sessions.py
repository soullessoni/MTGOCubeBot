from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.card import Card
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession
from app.schemas.loan.loan_session import (
    LoanSessionCreate,
    LoanSessionResponse,
)
from app.services.inventory.inventory_service import (
    InventoryService,
)
from app.services.loan.loan_planning_service import (
    LoanPlanningService,
    PlayerPool,
)
from app.services.loan.loan_session_status_service import (
    LoanSessionStatusService,
)
from app.services.loan.loan_session_workflow_service import (
    LoanSessionWorkflowService,
)
from app.use_cases.loan.create_loan_session import (
    CreateLoanSessionUseCase,
)
from app.use_cases.loan.hand_out_loan_session import (
    HandOutLoanSessionUseCase,
)

router = APIRouter(
    prefix="/loan/sessions",
    tags=["loan"],
)


@router.post(
    "",
    response_model=LoanSessionResponse,
)
def create_loan_session(
        payload: LoanSessionCreate,
        db: Session = Depends(get_db),
):
    pools = []

    for player in payload.players:

        cards = []

        for card_request in player.cards:

            card = (
                db.query(Card)
                .filter(
                    Card.id == card_request.card_id
                )
                .first()
            )

            if card is None:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"Card {card_request.card_id} not found"
                    ),
                )

            cards.append(card)

        pools.append(
            PlayerPool(
                player_name=player.player_name,
                cards=cards,
            )
        )

    inventory_service = InventoryService(
        db
    )

    planning_service = LoanPlanningService(
        inventory_service,
    )

    plan = planning_service.generate(
        pools,
    )

    use_case = CreateLoanSessionUseCase(
        db,
    )

    session = use_case.execute(
        plan,
    )

    return session


@router.get(
    "/{session_id}",
    response_model=LoanSessionResponse,
)
def get_loan_session(
        session_id: int,
        db: Session = Depends(get_db),
):
    session = (
        db.query(LoanSession)
        .filter(
            LoanSession.id == session_id
        )
        .first()
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Loan session not found",
        )

    return session


@router.post(
    "/{session_id}/ready",
    response_model=LoanSessionResponse,
)
def mark_ready_loan_session(
        session_id: int,
        db: Session = Depends(get_db),
):
    session = (
        db.query(LoanSession)
        .filter(
            LoanSession.id == session_id
        )
        .first()
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Loan session not found",
        )

    status_service = LoanSessionStatusService()

    try:
        status_service.mark_ready(
            session,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    db.commit()
    db.refresh(session)

    return session


@router.post(
    "/{session_id}/hand-out",
    response_model=LoanSessionResponse,
)
def hand_out_loan_session(
        session_id: int,
        db: Session = Depends(get_db),
):
    session = (
        db.query(LoanSession)
        .filter(
            LoanSession.id == session_id
        )
        .first()
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Loan session not found",
        )

    workflow_service = LoanSessionWorkflowService(
        db,
    )

    use_case = HandOutLoanSessionUseCase(
        workflow_service,
    )

    return use_case.execute(
        session,
    )


@router.post(
    "/{session_id}/start",
    response_model=LoanSessionResponse,
)
def start_loan_session(
        session_id: int,
        db: Session = Depends(get_db),
):
    session = (
        db.query(LoanSession)
        .filter(
            LoanSession.id == session_id
        )
        .first()
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Loan session not found",
        )

    workflow_service = LoanSessionWorkflowService(
        db,
    )

    try:
        return workflow_service.start(
            session,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

@router.post(
    "/{session_id}/complete",
    response_model=LoanSessionResponse,
)
def complete_loan_session(
        session_id: int,
        db: Session = Depends(get_db),
):
    session = (
        db.query(LoanSession)
        .filter(
            LoanSession.id == session_id
        )
        .first()
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Loan session not found",
        )

    workflow_service = LoanSessionWorkflowService(
        db,
    )

    try:
        workflow_service.complete(
            session,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    return session


@router.post(
    "/assignments/{assignment_id}/return",
)
def return_loan_assignment(
        assignment_id: int,
        db: Session = Depends(get_db),
):
    assignment = (
        db.query(LoanAssignment)
        .filter(
            LoanAssignment.id == assignment_id
        )
        .first()
    )

    if assignment is None:
        raise HTTPException(
            status_code=404,
            detail="Loan assignment not found",
        )

    workflow_service = LoanSessionWorkflowService(
        db,
    )

    try:
        result = workflow_service.return_card(
            assignment,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    return {
        "id": result.id,
        "status": result.status,
    }
