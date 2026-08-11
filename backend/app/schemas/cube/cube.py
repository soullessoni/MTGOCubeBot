from pydantic import BaseModel


class CubeResponse(BaseModel):
    id: int
    name: str
    cubecobra_url: str
    active: bool

    model_config = {
        "from_attributes": True,
    }


class CreateCubeRequest(BaseModel):
    name: str
    cube_url: str
