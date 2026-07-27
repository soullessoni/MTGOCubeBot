import pytest

from app.services.mtgo.mtgo_job_service import MtgoJobService
from app.use_cases.mtgo.retry_mtgo_job import RetryMtgoJobUseCase
from app.use_cases.mtgo.trigger_give_back_job import TriggerGiveBackJobUseCase
from app.use_cases.mtgo.trigger_give_job import TriggerGiveJobUseCase
from app.use_cases.mtgo.trigger_integrity_check_job import (
    TriggerIntegrityCheckJobUseCase,
)
from app.use_cases.mtgo.trigger_return_job import TriggerReturnJobUseCase


class FakeRunner:
    def __init__(self):
        self.calls = []

    def start(self, job_id, argv):
        self.calls.append((job_id, argv))


@pytest.fixture
def job_service(db_session):
    return MtgoJobService(db_session)


@pytest.fixture
def runner():
    return FakeRunner()


def test_trigger_give_creates_job_and_starts_runner(job_service, runner):
    use_case = TriggerGiveJobUseCase(job_service, runner)

    job = use_case.execute(session_id=7, requested_by="dashboard")

    assert job.job_type == "GIVE"
    assert job.session_id == 7
    assert job.status == "PENDING"
    assert runner.calls == [(job.id, ["-m", "mtgo.prepare_session_binders", "7"])]


def test_trigger_return_creates_job_and_starts_runner(job_service, runner):
    use_case = TriggerReturnJobUseCase(job_service, runner)

    job = use_case.execute(session_id=11, mtgo_username="FruitDuChene", requested_by="discord:1")

    assert job.job_type == "RETURN"
    assert job.session_id == 11
    assert job.mtgo_username == "FruitDuChene"
    assert runner.calls == [
        (job.id, ["-m", "mtgo.process_session_returns", "11", "FruitDuChene"]),
    ]


def test_trigger_integrity_check_creates_job_and_starts_runner(job_service, runner):
    use_case = TriggerIntegrityCheckJobUseCase(job_service, runner)

    job = use_case.execute(requested_by="dashboard")

    assert job.job_type == "INTEGRITY_CHECK"
    assert job.session_id is None
    assert runner.calls == [(job.id, ["-m", "mtgo.cube_integrity_check"])]


def test_trigger_give_back_creates_job_with_params_and_starts_runner(job_service, runner):
    use_case = TriggerGiveBackJobUseCase(job_service, runner)

    job = use_case.execute(
        mtgo_username="FruitDuChene",
        cards={"Mulldrifter": 1},
        requested_by="dashboard",
    )

    assert job.job_type == "GIVE_BACK"
    assert job.params == {"cards": {"Mulldrifter": 1}}
    assert len(runner.calls) == 1
    called_job_id, argv = runner.calls[0]
    assert called_job_id == job.id
    assert argv[0:2] == ["-m", "mtgo.give_back_excess_cards"]
    assert argv[-1] == str(job.id)


def test_trigger_give_back_rejects_empty_cards(job_service, runner):
    use_case = TriggerGiveBackJobUseCase(job_service, runner)

    with pytest.raises(ValueError):
        use_case.execute(mtgo_username="FruitDuChene", cards={}, requested_by="dashboard")

    assert runner.calls == []


def test_retry_rebuilds_argv_from_original_job_and_links_retry_of(job_service, runner):
    original = job_service.create(job_type="RETURN", session_id=11, mtgo_username="FruitDuChene")
    use_case = RetryMtgoJobUseCase(job_service, runner)

    retry_job = use_case.execute(original_job=original, requested_by="discord:1")

    assert retry_job.id != original.id
    assert retry_job.retry_of_job_id == original.id
    assert retry_job.job_type == "RETURN"
    assert retry_job.session_id == 11
    assert retry_job.mtgo_username == "FruitDuChene"
    assert runner.calls == [
        (retry_job.id, ["-m", "mtgo.process_session_returns", "11", "FruitDuChene"]),
    ]


def test_retry_of_give_back_job_reuses_stored_params(job_service, runner):
    original = job_service.create(
        job_type="GIVE_BACK",
        mtgo_username="FruitDuChene",
        params={"cards": {"Mulldrifter": 1}},
    )
    use_case = RetryMtgoJobUseCase(job_service, runner)

    retry_job = use_case.execute(original_job=original)

    assert retry_job.params == {"cards": {"Mulldrifter": 1}}
    called_job_id, argv = runner.calls[0]
    assert called_job_id == retry_job.id
    assert argv[-1] == str(retry_job.id)
