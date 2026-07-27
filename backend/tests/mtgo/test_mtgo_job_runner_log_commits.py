from pathlib import Path

from sqlalchemy import create_engine, event
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


def test_run_does_not_commit_once_per_stdout_line(monkeypatch):
    session_local = _make_session_local()
    monkeypatch.setattr(runner_module, "SessionLocal", session_local)
    job_id = _create_job(session_local)

    lines = [f"line {i}\n" for i in range(50)] + ['{"ok": true}\n']
    monkeypatch.setattr(
        runner_module.subprocess,
        "Popen",
        lambda *args, **kwargs: FakeProcess(lines, 0),
    )

    commit_count = 0

    def _count_commit(session):
        nonlocal commit_count
        commit_count += 1

    event.listen(session_local, "after_commit", _count_commit)
    try:
        runner = MtgoJobRunnerService(
            MtgoAgentConfig(agent_python=Path("python"), agent_cwd=Path(".")),
            FakeNotifier(),
        )
        runner._run(job_id, [])
    finally:
        event.remove(session_local, "after_commit", _count_commit)

    # Previously: one commit per stdout line (51) plus the RUNNING/terminal
    # transitions. A verbose job must not turn every line of output into
    # its own SQLite write.
    assert commit_count <= 4

    db = session_local()
    job = db.get(MtgoJob, job_id)
    assert job.log_output == "\n".join(line.rstrip("\n") for line in lines)
    assert job.status == "SUCCEEDED"
    db.close()
