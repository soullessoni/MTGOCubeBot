from pydantic import BaseModel


class CubeInstanceResponse(BaseModel):
    id: int
    cube_id: int
    mtgo_account_id: int
    label: str
    active: bool

    model_config = {
        "from_attributes": True,
    }


class CreateCubeInstanceRequest(BaseModel):
    cube_id: int
    mtgo_account_id: int
    label: str


class SetCubeInstanceActiveRequest(BaseModel):
    active: bool
