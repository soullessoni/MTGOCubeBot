from app.models.loan_session import LoanSession
from app.services.loan.loan_session_validation_service import (
    LoanSessionValidationService,
)


class LoanSessionStatusService:
    CREATED = "CREATED"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

    ALLOWED_TRANSITIONS = {
        CREATED: [
            READY,
            CANCELLED,
        ],
        READY: [
            IN_PROGRESS,
            CANCELLED,
        ],
        IN_PROGRESS: [
            COMPLETED,
            CANCELLED,
        ],
        COMPLETED: [],
        CANCELLED: [],
    }

    def __init__(self):
        self.validation_service = LoanSessionValidationService()

    def mark_ready(
            self,
            session: LoanSession,
    ) -> LoanSession:

        validation = self.validation_service.validate(
            session,
        )

        if not validation.valid:
            raise ValueError(
                "; ".join(validation.errors)
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

    def cancel(
            self,
            session: LoanSession,
    ) -> LoanSession:

        return self._transition(
            session,
            self.CANCELLED,
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
