from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.mtgo.mtgo_account import (
    CreateMtgoAccountRequest,
    MtgoAccountResponse,
    SetMtgoAccountActiveRequest,
)
from app.services.mtgo.mtgo_account_service import MtgoAccountService

router = APIRouter(
    prefix="/mtgo/accounts",
    tags=["mtgo"],
)


@router.post(
    "/",
    response_model=MtgoAccountResponse,
)
def create_account(
        payload: CreateMtgoAccountRequest,
        db: Session = Depends(get_db),
):
    service = MtgoAccountService(db)

    if service.get_by_username(payload.mtgo_username) is not None:
        raise HTTPException(
            status_code=409,
            detail=f"An account for {payload.mtgo_username!r} already exists",
        )

    return service.create(
        payload.name,
        payload.mtgo_username,
    )


@router.get(
    "/",
    response_model=list[MtgoAccountResponse],
)
def list_accounts(
        active_only: bool = False,
        db: Session = Depends(get_db),
):
    service = MtgoAccountService(db)

    if active_only:
        return service.list_active()

    return service.list_all()


@router.get(
    "/{account_id}",
    response_model=MtgoAccountResponse,
)
def get_account(
        account_id: int,
        db: Session = Depends(get_db),
):
    service = MtgoAccountService(db)
    account = service.get(account_id)

    if account is None:
        raise HTTPException(
            status_code=404,
            detail="MTGO account not found",
        )

    return account


@router.patch(
    "/{account_id}/active",
    response_model=MtgoAccountResponse,
)
def set_account_active(
        account_id: int,
        payload: SetMtgoAccountActiveRequest,
        db: Session = Depends(get_db),
):
    service = MtgoAccountService(db)
    account = service.get(account_id)

    if account is None:
        raise HTTPException(
            status_code=404,
            detail="MTGO account not found",
        )

    return service.set_active(account, payload.active)
