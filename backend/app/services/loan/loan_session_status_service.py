from app.models.loan_session import LoanSession
from app.services.loan.loan_session_readiness_service import (
    LoanSessionReadinessService,
)


class LoanSessionStatusService:

    CREATED = "CREATED"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"

    ALLOWED_TRANSITIONS = {
        CREATED: [
            READY,
        ],
        READY: [
            IN_PROGRESS,
        ],
        IN_PROGRESS: [
            COMPLETED,
        ],
        COMPLETED: [],
    }

    def __init__(
        self,
        readiness_service: LoanSessionReadinessService | None = None,
    ):
        self.readiness_service = (
            readiness_service
            or LoanSessionReadinessService()
        )

    def mark_ready(
        self,
        session: LoanSession,
    ) -> LoanSession:

        self.readiness_service.validate(
            session,
        )

        return self._transition(
            session,
            self.READY,
        )

    def start(
        self,
        session: LoanSession,
    ) -> LoanSession:
        return self._transition(
            session,
            self.IN_PROGRESS,
        )

    def complete(
        self,
        session: LoanSession,
    ) -> LoanSession:
        return self._transition(
            session,
            self.COMPLETED,
        )

    def _transition(
        self,
        session: LoanSession,
        new_status: str,
    ) -> LoanSession:

        current_status = session.status

        allowed = self.ALLOWED_TRANSITIONS.get(
            current_status,
            [],
        )

        if new_status not in allowed:
            raise ValueError(
                f"Invalid transition: "
                f"{current_status} -> {new_status}"
            )

        session.status = new_status

        return session