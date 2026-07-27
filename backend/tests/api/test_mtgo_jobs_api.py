import pytest

from app.api.mtgo.dependencies import get_job_runner
from app.main import app
from app.models.loan_session import LoanSession


class FakeRunner:
    def __init__(self):
        self.calls = []

    def start(self, job_id, argv):
        self.calls.append((job_id, argv))


@pytest.fixture
def fake_runner():
    runner = FakeRunner()
    app.dependency_overrides[get_job_runner] = lambda: runner
    yield runner
    app.dependency_overrides.pop(get_job_runner, None)


def _make_session(db_session) -> LoanSession:
    session = LoanSession(status="IN_PROGRESS")
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


def test_trigger_give_returns_pending_job(client, db_session, fake_runner):
    session = _make_session(db_session)

    response = client.post(f"/mtgo/sessions/{session.id}/give")

    assert response.status_code == 200
    data = response.json()
    assert data["job_type"] == "GIVE"
    assert data["session_id"] == session.id
    assert data["status"] in ("PENDING", "RUNNING")
    assert fake_runner.calls == [(data["id"], ["-m", "mtgo.prepare_session_binders", str(session.id)])]


def test_trigger_give_404s_for_missing_session(client, fake_runner):
    response = client.post("/mtgo/sessions/999/give")

    assert response.status_code == 404
    assert fake_runner.calls == []


def test_trigger_return_requires_mtgo_username_in_body(client, db_session, fake_runner):
    session = _make_session(db_session)

    response = client.post(
        f"/mtgo/sessions/{session.id}/return",
        json={"mtgo_username": "FruitDuChene"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["job_type"] == "RETURN"
    assert data["mtgo_username"] == "FruitDuChene"
    assert fake_runner.calls == [
        (data["id"], ["-m", "mtgo.process_session_returns", str(session.id), "FruitDuChene"]),
    ]


def test_trigger_integrity_check(client, fake_runner):
    response = client.post("/mtgo/integrity-check", json={})

    assert response.status_code == 200
    data = response.json()
    assert data["job_type"] == "INTEGRITY_CHECK"
    assert data["session_id"] is None


def test_trigger_give_back_rejects_empty_cards(client, fake_runner):
    response = client.post(
        "/mtgo/give-back",
        json={"mtgo_username": "FruitDuChene", "cards": {}},
    )

    assert response.status_code == 400
    assert fake_runner.calls == []


def test_trigger_give_back_success(client, fake_runner):
    response = client.post(
        "/mtgo/give-back",
        json={"mtgo_username": "FruitDuChene", "cards": {"Mulldrifter": 1}},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["job_type"] == "GIVE_BACK"
    assert data["params"] == {"cards": {"Mulldrifter": 1}}


def test_get_job_returns_404_for_missing(client):
    response = client.get("/mtgo/jobs/999")

    assert response.status_code == 404


def test_get_job_after_trigger(client, db_session, fake_runner):
    session = _make_session(db_session)
    triggered = client.post(f"/mtgo/sessions/{session.id}/give").json()

    response = client.get(f"/mtgo/jobs/{triggered['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == triggered["id"]


def test_list_jobs_filters_by_session(client, db_session, fake_runner):
    session_a = _make_session(db_session)
    session_b = _make_session(db_session)
    client.post(f"/mtgo/sessions/{session_a.id}/give")
    client.post(f"/mtgo/sessions/{session_b.id}/give")

    response = client.get(f"/mtgo/jobs/?session_id={session_a.id}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["session_id"] == session_a.id


def test_retry_job_creates_new_job_linked_to_original(client, db_session, fake_runner):
    session = _make_session(db_session)
    original = client.post(
        f"/mtgo/sessions/{session.id}/return",
        json={"mtgo_username": "FruitDuChene"},
    ).json()

    response = client.post(f"/mtgo/jobs/{original['id']}/retry")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] != original["id"]
    assert data["retry_of_job_id"] == original["id"]
    assert data["job_type"] == "RETURN"
    assert data["mtgo_username"] == "FruitDuChene"


def test_retry_job_404s_for_missing_original(client, fake_runner):
    response = client.post("/mtgo/jobs/999/retry")

    assert response.status_code == 404
