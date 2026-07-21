from dataclasses import dataclass

from app.models.loan_session import LoanSession


@dataclass
class LoanSessionValidationResult:
    valid: bool
    errors: list[str]


class LoanSessionValidationService:

    def validate(
        self,
        session: LoanSession,
    ) -> LoanSessionValidationResult:

        errors = []

        if not session.assignments:
            errors.append(
                "Loan session has no assignments"
            )

        for assignment in session.assignments:
            if assignment.status != "CREATED":
                errors.append(
                    f"Assignment {assignment.id} "
                    f"is not in CREATED state"
                )

        return LoanSessionValidationResult(
            valid=len(errors) == 0,
            errors=errors,
        )