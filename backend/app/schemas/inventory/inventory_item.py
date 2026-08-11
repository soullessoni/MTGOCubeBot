from pydantic import BaseModel


class InventoryItemResponse(BaseModel):
    card_id: int
    card_name: str | None = None
    cube_instance_id: int
    quantity: int
    available_quantity: int

    model_config = {
        "from_attributes": True,
    }


class InventoryUpdateRequest(BaseModel):
    cube_instance_id: int
    quantity: int
