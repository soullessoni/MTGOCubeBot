from app.models.loan_session import LoanSession
from app.repositories.loan_session_repository import LoanSessionRepository


def test_create_and_get_session(
    db_session,
):

    repository = LoanSessionRepository(
        db_session,
    )

    session = LoanSession()

    created = repository.create(
        session,
    )

    assert created.id is not None

    loaded = repository.get(
        created.id,
    )

    assert loaded is not None
    assert loaded.id == created.id