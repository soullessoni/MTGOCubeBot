from app.models.loan_assignment import LoanAssignment


class LoanAssignmentService:

    def __init__(self, db):
        self.db = db

    def mark_handed_out(
        self,
        assignment: LoanAssignment,
    ) -> LoanAssignment:

        assignment.status = "HANDED_OUT"

        self.db.commit()
        self.db.refresh(assignment)

        return assignment

    def mark_returned(
        self,
        assignment: LoanAssignment,
    ) -> LoanAssignment:

        assignment.status = "RETURNED"

        self.db.commit()
        self.db.refresh(assignment)

        return assignment