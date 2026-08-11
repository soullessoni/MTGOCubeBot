import threading
import time
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.mtgo_agent_config import MtgoAgentConfig
from app.db.base import Base
from app.models.mtgo_job import MtgoJob
from app.services.mtgo import mtgo_job_runner_service as runner_module
from app.services.mtgo.mtgo_job_runner_service import MtgoJobRunnerService


class FakeNotifier:
    def notify(self, job):
        pass


_RealThread = threading.Thread


class TrackedThreads:
    """Wraps threading.Thread so tests can join every background thread
    `runner.start()` spawns before returning — avoids a stray thread still
    committing on a StaticPool connection after the test's engine (and
    thus that connection) has already gone out of scope, which pytest
    reports as an unraisable "not an error" sqlite3 warning.

    Captures the real class at import time — `monkeypatch.setattr` below
    replaces `threading.Thread` process-wide (it's the same module
    object everywhere), so building instances via a freshly-looked-up
    `threading.Thread` would recurse into this wrapper forever."""

    def __init__(self):
        self.threads = []

    def Thread(self, *args, **kwargs):
        thread = _RealThread(*args, **kwargs)
        self.threads.append(thread)
        return thread

    def join_all(self, timeout=5):
        for thread in self.threads:
            thread.join(timeout=timeout)


class FakeStdout:
    def __init__(self, lines):
        self._lines = lines

    def __iter__(self):
        return iter(self._lines)


class BlockingFakeProcess:
    """Simulates a real MTGO automation subprocess that's still running —
    `wait()` blocks until the test releases it, so a second `start()` call
    for the same account has a real window to observe "still busy" in."""

    def __init__(self, release_event):
        self.stdout = FakeStdout(['{"ok": true}\n'])
        self._release_event = release_event

    def wait(self):
        self._release_event.wait(timeout=5)
        return 0


def _make_session_local():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _create_job(session_local, **overrides) -> int:
    db = session_local()
    defaults = dict(
        job_type="GIVE",
        status="PENDING",
        session_id=1,
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


def test_second_start_for_same_account_is_rejected_while_first_runs(monkeypatch):
    session_local = _make_session_local()
    monkeypatch.setattr(runner_module, "SessionLocal", session_local)

    tracked = TrackedThreads()
    monkeypatch.setattr(runner_module.threading, "Thread", tracked.Thread)

    release_event = threading.Event()
    monkeypatch.setattr(
        runner_module.subprocess,
        "Popen",
        lambda *args, **kwargs: BlockingFakeProcess(release_event),
    )

    runner = MtgoJobRunnerService(
        MtgoAgentConfig(agent_python=Path("python"), agent_cwd=Path(".")),
        FakeNotifier(),
    )

    job_one_id = _create_job(session_local)
    job_two_id = _create_job(session_local)

    try:
        started_one = runner.start(job_one_id, [], mtgo_account_id=5, mtgo_account_username="TheLegionCube")
        assert started_one is True

        # Give the background thread a moment to register itself as busy.
        time.sleep(0.2)

        started_two = runner.start(job_two_id, [], mtgo_account_id=5, mtgo_account_username="TheLegionCube")
        assert started_two is False
    finally:
        release_event.set()
        tracked.join_all()


def test_different_accounts_can_start_concurrently(monkeypatch):
    session_local = _make_session_local()
    monkeypatch.setattr(runner_module, "SessionLocal", session_local)

    tracked = TrackedThreads()
    monkeypatch.setattr(runner_module.threading, "Thread", tracked.Thread)

    release_event = threading.Event()
    monkeypatch.setattr(
        runner_module.subprocess,
        "Popen",
        lambda *args, **kwargs: BlockingFakeProcess(release_event),
    )

    runner = MtgoJobRunnerService(
        MtgoAgentConfig(agent_python=Path("python"), agent_cwd=Path(".")),
        FakeNotifier(),
    )

    job_one_id = _create_job(session_local)
    job_two_id = _create_job(session_local)

    try:
        started_one = runner.start(job_one_id, [], mtgo_account_id=5, mtgo_account_username="AccountOne")
        started_two = runner.start(job_two_id, [], mtgo_account_id=6, mtgo_account_username="AccountTwo")

        assert started_one is True
        assert started_two is True
    finally:
        release_event.set()
        tracked.join_all()


def test_account_freed_after_job_finishes(monkeypatch):
    session_local = _make_session_local()
    monkeypatch.setattr(runner_module, "SessionLocal", session_local)

    monkeypatch.setattr(
        runner_module.subprocess,
        "Popen",
        lambda *args, **kwargs: BlockingFakeProcess(threading.Event()),
    )

    runner = MtgoJobRunnerService(
        MtgoAgentConfig(agent_python=Path("python"), agent_cwd=Path(".")),
        FakeNotifier(),
    )

    job_id = _create_job(session_local)

    runner._run(job_id, [], mtgo_account_id=5, mtgo_account_username="TheLegionCube")

    assert 5 not in runner._busy_account_ids


def test_start_with_no_account_id_is_never_treated_as_busy(monkeypatch):
    session_local = _make_session_local()
    monkeypatch.setattr(runner_module, "SessionLocal", session_local)

    tracked = TrackedThreads()
    monkeypatch.setattr(runner_module.threading, "Thread", tracked.Thread)

    release_event = threading.Event()
    monkeypatch.setattr(
        runner_module.subprocess,
        "Popen",
        lambda *args, **kwargs: BlockingFakeProcess(release_event),
    )

    runner = MtgoJobRunnerService(
        MtgoAgentConfig(agent_python=Path("python"), agent_cwd=Path(".")),
        FakeNotifier(),
    )

    job_one_id = _create_job(session_local)
    job_two_id = _create_job(session_local)

    try:
        started_one = runner.start(job_one_id, [])
        started_two = runner.start(job_two_id, [])

        assert started_one is True
        assert started_two is True
    finally:
        release_event.set()
        tracked.join_all()
