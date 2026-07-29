from app.models.loan_deposit import LoanDeposit
from app.models.loan_session import LoanSession


class LoanDepositService:

    def __init__(self, db):
        self.db = db

    def create(
            self,
            session: LoanSession,
            mtgo_username: str,
    ) -> LoanDeposit:
        if not session.deposit_required:
            raise ValueError(
                "This session does not require a deposit"
            )

        deposit = LoanDeposit(
            session_id=session.id,
            mtgo_username=mtgo_username,
            required_amount=session.deposit_amount,
        )

        self.db.add(deposit)
        self.db.commit()
        self.db.refresh(deposit)

        return deposit

    def record_collected(
            self,
            deposit: LoanDeposit,
            collected_amount: int,
    ) -> LoanDeposit:
        deposit.collected_amount = collected_amount

        self.db.commit()
        self.db.refresh(deposit)

        return deposit

    def record_returned(
            self,
            deposit: LoanDeposit,
            returned_amount: int,
    ) -> LoanDeposit:
        deposit.returned_amount = returned_amount

        self.db.commit()
        self.db.refresh(deposit)

        return deposit

    def list_for_session(
            self,
            session_id: int,
    ) -> list[LoanDeposit]:
        return (
            self.db.query(LoanDeposit)
            .filter(
                LoanDeposit.session_id == session_id
            )
            .all()
        )

    def get(
            self,
            deposit_id: int,
    ) -> LoanDeposit | None:
        return (
            self.db.query(LoanDeposit)
            .filter(
                LoanDeposit.id == deposit_id
            )
            .first()
        )
