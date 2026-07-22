from fastapi import FastAPI

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