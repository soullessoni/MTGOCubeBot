from pydantic import BaseModel


class MtgoAccountResponse(BaseModel):
    id: int
    name: str
    mtgo_username: str
    active: bool

    model_config = {
        "from_attributes": True,
    }


class CreateMtgoAccountRequest(BaseModel):
    name: str
    mtgo_username: str


class SetMtgoAccountActiveRequest(BaseModel):
    active: bool
