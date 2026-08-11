from app.models.cube_instance import CubeInstance
from app.models.mtgo_account import MtgoAccount


def resolve_mtgo_account(db, cube_instance_id: int | None) -> tuple[int | None, str | None]:
    """(mtgo_account_id, mtgo_username) for the account hosting
    `cube_instance_id`, or (None, None) if there's no instance to route
    through (job type not wired to one yet) or it doesn't exist."""
    if cube_instance_id is None:
        return None, None

    row = (
        db.query(CubeInstance.mtgo_account_id, MtgoAccount.mtgo_username)
        .join(MtgoAccount, CubeInstance.mtgo_account_id == MtgoAccount.id)
        .filter(CubeInstance.id == cube_instance_id)
        .first()
    )

    if row is None:
        return None, None

    return row[0], row[1]
