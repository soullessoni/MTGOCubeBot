from app.models.loan_session import LoanSession


class LoanSessionReadinessService:

    def validate(
        self,
        session: LoanSession,
    ) -> bool:
        """
        Check whether a loan session is ready to start.
        """

        if session.status == "COMPLETED":
            raise ValueError(
                "Completed session cannot become ready"
            )

        if not session.assignments:
            raise ValueError(
                "Loan session has no assignments"
            )

        invalid_assignments = [
            assignment
            for assignment in session.assignments
            if assignment.status != "CREATED"
        ]

        if invalid_assignments:
            raise ValueError(
                "Loan session contains invalid assignments"
            )

        return True