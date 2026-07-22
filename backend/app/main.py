from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.exceptions.loan import CardNotFoundError

from app.api.loan import (
    sessions_router,
    assignments_router,
)

app = FastAPI(
    title="MTGO CubeBot API",
    version="0.1.0",
    description="Backend for automated MTGO Cube management",
)

app.include_router(
    sessions_router,
)

app.include_router(
    assignments_router,
)


@app.get("/")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "MTGO CubeBot",
    }

@app.exception_handler(CardNotFoundError)
def card_not_found_handler(
    request,
    exc: CardNotFoundError,
):
    return JSONResponse(
        status_code=404,
        content={
            "detail": str(exc),
        },
    )