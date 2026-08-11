from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.mtgo.cube_instance import (
    CreateCubeInstanceRequest,
    CubeInstanceResponse,
    SetCubeInstanceActiveRequest,
)
from app.services.cube.cube_instance_service import CubeInstanceService

router = APIRouter(
    prefix="/mtgo/cube-instances",
    tags=["mtgo"],
)


@router.post(
    "/",
    response_model=CubeInstanceResponse,
)
def create_cube_instance(
        payload: CreateCubeInstanceRequest,
        db: Session = Depends(get_db),
):
    service = CubeInstanceService(db)

    try:
        return service.create(
            payload.cube_id,
            payload.mtgo_account_id,
            payload.label,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                f"An instance labelled {payload.label!r} already exists "
                f"for this account"
            ),
        )


@router.get(
    "/",
    response_model=list[CubeInstanceResponse],
)
def list_cube_instances(
        mtgo_account_id: int | None = None,
        cube_id: int | None = None,
        db: Session = Depends(get_db),
):
    service = CubeInstanceService(db)

    if mtgo_account_id is not None:
        return service.list_for_account(mtgo_account_id)

    if cube_id is not None:
        return service.list_for_cube(cube_id)

    return service.list_all()


@router.get(
    "/{instance_id}",
    response_model=CubeInstanceResponse,
)
def get_cube_instance(
        instance_id: int,
        db: Session = Depends(get_db),
):
    service = CubeInstanceService(db)
    instance = service.get(instance_id)

    if instance is None:
        raise HTTPException(
            status_code=404,
            detail="Cube instance not found",
        )

    return instance


@router.patch(
    "/{instance_id}/active",
    response_model=CubeInstanceResponse,
)
def set_cube_instance_active(
        instance_id: int,
        payload: SetCubeInstanceActiveRequest,
        db: Session = Depends(get_db),
):
    service = CubeInstanceService(db)
    instance = service.get(instance_id)

    if instance is None:
        raise HTTPException(
            status_code=404,
            detail="Cube instance not found",
        )

    return service.set_active(instance, payload.active)
