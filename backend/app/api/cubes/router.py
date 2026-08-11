import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.cube import Cube
from app.schemas.cube.cube import CreateCubeRequest, CubeResponse
from app.services.cube.cube_import_service import CubeImportService

router = APIRouter(
    prefix="/cubes",
    tags=["cube"],
)


@router.post(
    "/",
    response_model=CubeResponse,
)
def create_cube(
        payload: CreateCubeRequest,
        db: Session = Depends(get_db),
):
    service = CubeImportService(db)

    try:
        return service.import_cube(
            payload.cube_url,
            payload.name,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Could not fetch the cube from CubeCobra: {error}",
        )


@router.get(
    "/",
    response_model=list[CubeResponse],
)
def list_cubes(
        db: Session = Depends(get_db),
):
    return (
        db.query(Cube)
        .order_by(Cube.id)
        .all()
    )
