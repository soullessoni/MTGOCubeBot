from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.card import Card
from app.schemas.inventory.inventory_item import (
    InventoryItemResponse,
    InventoryUpdateRequest,
)
from app.services.inventory.inventory_service import InventoryService

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
)


@router.get(
    "/",
    response_model=list[InventoryItemResponse],
)
def list_inventory(
        cube_instance_id: int | None = None,
        db: Session = Depends(get_db),
):
    service = InventoryService(db)

    return [
        InventoryItemResponse(
            card_id=item.card_id,
            card_name=item.card_name,
            cube_instance_id=item.cube_instance_id,
            quantity=item.quantity,
            available_quantity=service.get_available_quantity(item.card, item.cube_instance_id),
        )
        for item in service.list_all(cube_instance_id)
    ]


@router.put(
    "/{card_id}",
    response_model=InventoryItemResponse,
)
def update_inventory_quantity(
        card_id: int,
        payload: InventoryUpdateRequest,
        db: Session = Depends(get_db),
):
    card = (
        db.query(Card)
        .filter(Card.id == card_id)
        .first()
    )

    if card is None:
        raise HTTPException(
            status_code=404,
            detail=f"Card {card_id} not found",
        )

    service = InventoryService(db)
    service.set_quantity(card, payload.cube_instance_id, payload.quantity)

    return InventoryItemResponse(
        card_id=card.id,
        card_name=card.name,
        cube_instance_id=payload.cube_instance_id,
        quantity=payload.quantity,
        available_quantity=service.get_available_quantity(card, payload.cube_instance_id),
    )
