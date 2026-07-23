from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.exceptions.loan import CardNotFoundError

from app.api.inventory import inventory_router
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

app.include_router(
    inventory_router,
)


class NoCacheStaticFiles(StaticFiles):
    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


app.mount(
    "/dashboard",
    NoCacheStaticFiles(
        directory=Path(__file__).parent / "web" / "static",
        html=True,
    ),
    name="dashboard",
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