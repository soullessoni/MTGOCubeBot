from app.models.mtgo_account import MtgoAccount


class MtgoAccountService:

    def __init__(
            self,
            db,
    ):
        self.db = db

    def create(
            self,
            name: str,
            mtgo_username: str,
    ) -> MtgoAccount:
        account = MtgoAccount(
            name=name,
            mtgo_username=mtgo_username,
        )

        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)

        return account

    def get(
            self,
            account_id: int,
    ) -> MtgoAccount | None:
        return (
            self.db.query(MtgoAccount)
            .filter(
                MtgoAccount.id == account_id
            )
            .first()
        )

    def get_by_username(
            self,
            mtgo_username: str,
    ) -> MtgoAccount | None:
        return (
            self.db.query(MtgoAccount)
            .filter(
                MtgoAccount.mtgo_username == mtgo_username
            )
            .first()
        )

    def list_all(
            self,
    ) -> list[MtgoAccount]:
        return (
            self.db.query(MtgoAccount)
            .order_by(MtgoAccount.id)
            .all()
        )

    def list_active(
            self,
    ) -> list[MtgoAccount]:
        return (
            self.db.query(MtgoAccount)
            .filter(
                MtgoAccount.active.is_(True)
            )
            .all()
        )

    def set_active(
            self,
            account: MtgoAccount,
            active: bool,
    ) -> MtgoAccount:
        account.active = active

        self.db.commit()
        self.db.refresh(account)

        return account
