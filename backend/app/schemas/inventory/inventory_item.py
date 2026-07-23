from pydantic import BaseModel


class InventoryItemResponse(BaseModel):
    card_id: int
    card_name: str | None = None
    quantity: int
    available_quantity: int

    model_config = {
        "from_attributes": True,
    }


class InventoryUpdateRequest(BaseModel):
    quantity: int
