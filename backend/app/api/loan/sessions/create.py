from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.card import Card
from app.schemas.loan.loan_session import LoanSessionCreate, LoanSessionResponse
from app.services.inventory.inventory_service import InventoryService
from app.services.loan.loan_planning_service import (
    LoanPlanningService,
    PlayerPool,
)
from app.use_cases.loan.create_loan_session import (
    CreateLoanSessionUseCase,
)

router = APIRouter(
    tags=["loan"],
)


@router.post(
    "/",
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
                .filter(Card.id == card_request.card_id)
                .first()
            )

            if card is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Card {card_request.card_id} not found",
                )

            cards.append(card)

        pools.append(
            PlayerPool(
                player_name=player.player_name,
                cards=cards,
            )
        )

    inventory_service = InventoryService(db)

    planning_service = LoanPlanningService(
        inventory_service,
    )
    
    planning_result = planning_service.generate(
        pools,
    )

    if planning_result.conflicts:
        raise HTTPException(
            status_code=409,
            detail="Loan conflicts detected",
        )

    use_case = CreateLoanSessionUseCase(
        db,
    )

    return use_case.execute(
        planning_result.requests,
    )