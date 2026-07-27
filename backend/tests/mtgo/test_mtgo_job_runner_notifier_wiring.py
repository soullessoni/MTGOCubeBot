from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.mtgo_agent_config import MtgoAgentConfig
from app.db.base import Base
from app.models.mtgo_job import MtgoJob
from app.services.mtgo import mtgo_job_runner_service as runner_module
from app.services.mtgo.mtgo_job_runner_service import MtgoJobRunnerService


class FakeNotifier:
    def __init__(self):
        self.notified = []

    def notify(self, job):
        self.notified.append((job.id, job.status, job.result, job.error_message))


class FakeStdout:
    def __init__(self, lines):
        self._lines = lines

    def __iter__(self):
        return iter(self._lines)


class FakeProcess:
    def __init__(self, lines, exit_code):
        self.stdout = FakeStdout(lines)
        self._exit_code = exit_code

    def wait(self):
        return self._exit_code


@pytest.fixture
def runner_db(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    Base.metadata.create_all(
        engine
    )

    session_local = sessionmaker(
        bind=engine
    )

    monkeypatch.setattr(runner_module, "SessionLocal", session_local)

    return session_local


def _create_job(session_local, **overrides) -> int:
    db = session_local()
    defaults = dict(
        job_type="RETURN",
        status="PENDING",
        session_id=1,
        mtgo_username="FruitDuChene",
        log_output="",
    )
    defaults.update(overrides)
    job = MtgoJob(**defaults)
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = job.id
    db.close()
    return job_id


def test_run_notifies_after_failed_job(runner_db, monkeypatch):
    job_id = _create_job(runner_db)

    monkeypatch.setattr(
        runner_module.subprocess,
        "Popen",
        lambda *args, **kwargs: FakeProcess(["not json at all\n"], 1),
    )

    notifier = FakeNotifier()
    runner = MtgoJobRunnerService(
        MtgoAgentConfig(
            agent_python=Path("python"),
            agent_cwd=Path("."),
        ),
        notifier,
    )

    runner._run(job_id, [])

    assert len(notifier.notified) == 1
    notified_id, status, result, error_message = notifier.notified[0]
    assert notified_id == job_id
    assert status == "FAILED"


def test_run_notifies_after_succeeded_job_with_discrepancy(runner_db, monkeypatch):
    job_id = _create_job(runner_db)

    result_line = (
        '{"ok": false, "reconciliation": '
        '{"still_owed": {"Mulldrifter": 1}, "to_give_back": {}}}\n'
    )

    monkeypatch.setattr(
        runner_module.subprocess,
        "Popen",
        lambda *args, **kwargs: FakeProcess([result_line], 0),
    )

    notifier = FakeNotifier()
    runner = MtgoJobRunnerService(
        MtgoAgentConfig(
            agent_python=Path("python"),
            agent_cwd=Path("."),
        ),
        notifier,
    )

    runner._run(job_id, [])

    assert len(notifier.notified) == 1
    notified_id, status, result, error_message = notifier.notified[0]
    assert notified_id == job_id
    assert status == "SUCCEEDED"
    assert result["reconciliation"]["still_owed"] == {"Mulldrifter": 1}


def test_run_notifies_after_clean_succeeded_job(runner_db, monkeypatch):
    job_id = _create_job(runner_db, job_type="GIVE")

    monkeypatch.setattr(
        runner_module.subprocess,
        "Popen",
        lambda *args, **kwargs: FakeProcess(['{"ok": true}\n'], 0),
    )

    notifier = FakeNotifier()
    runner = MtgoJobRunnerService(
        MtgoAgentConfig(
            agent_python=Path("python"),
            agent_cwd=Path("."),
        ),
        notifier,
    )

    runner._run(job_id, [])

    # The notifier itself decides a clean job needs no message; the
    # runner's job here is only to always call `.notify`, unconditionally,
    # after the terminal status is committed.
    assert len(notifier.notified) == 1
    assert notifier.notified[0][1] == "SUCCEEDED"
