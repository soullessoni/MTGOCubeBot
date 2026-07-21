from dataclasses import dataclass

from app.models.loan_session import LoanSession


@dataclass
class LoanSessionValidationResult:
    errors: list[str]

    @property
    def valid(self) -> bool:
        return len(self.errors) == 0


class LoanSessionValidationService:

    def validate(
            self,
            session: LoanSession,
    ) -> LoanSessionValidationResult:

        errors = []

        if session.status == "COMPLETED":
            errors.append(
                "Completed session cannot become ready"
            )

        if not session.assignments:
            errors.append(
                "Loan session has no assignments"
            )

        for assignment in session.assignments:
            if assignment.status != "CREATED":
                errors.append(
                    "Loan session contains invalid assignments"
                )

        return LoanSessionValidationResult(
            errors=errors,
        )
