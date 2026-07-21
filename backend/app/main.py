from fastapi import FastAPI

from app.api.loan import session_actions
from app.api.loan.sessions import router as loan_sessions_router

app = FastAPI(
    title="MTGO CubeBot API",
    version="0.1.0",
    description="Backend for automated MTGO Cube management",
)

app.include_router(
    loan_sessions_router,
)

app.include_router(
    session_actions.router
)


@app.get("/")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "MTGO CubeBot",
    }
