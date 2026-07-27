import json
import subprocess
import threading
from datetime import UTC, datetime

from app.core.mtgo_agent_config import MtgoAgentConfig
from app.db.database import SessionLocal
from app.models.mtgo_job import MtgoJob
from app.services.mtgo.mtgo_job_notifier_service import MtgoJobNotifierService


def parse_job_output(exit_code: int, stdout: str) -> tuple[str, dict | None, str | None]:
    """Find the last line of `stdout` that parses as JSON — that's the
    script's structured final result, by convention (see mtgo_job
    scripts). Exit code 0 + a parseable JSON line is always SUCCEEDED,
    even if the JSON's own "ok" field is False — that field describes a
    reported domain discrepancy (still_owed, missing cards, ...), not a
    process failure. Anything else is FAILED, with the JSON's "error"
    field or a tail of the raw output as the error message."""
    lines = [line for line in stdout.splitlines() if line.strip()]

    parsed = None
    for line in reversed(lines):
        try:
            parsed = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        break

    if exit_code == 0 and parsed is not None:
        return "SUCCEEDED", parsed, None

    if parsed is not None and isinstance(parsed.get("error"), str):
        return "FAILED", parsed, parsed["error"]

    if lines:
        tail = "\n".join(lines[-40:])
        return "FAILED", None, tail

    return "FAILED", None, f"process exited with code {exit_code}"


class MtgoJobRunnerService:
    def __init__(
            self,
            config: MtgoAgentConfig,
            notifier: MtgoJobNotifierService,
    ):
        self.config = config
        self.notifier = notifier

    def start(self, job_id: int, argv: list[str]) -> None:
        thread = threading.Thread(
            target=self._run,
            args=(job_id, argv),
            daemon=True,
        )
        thread.start()

    def _run(self, job_id: int, argv: list[str]) -> None:
        db = SessionLocal()
        job = None

        try:
            job = db.get(MtgoJob, job_id)
            job.status = "RUNNING"
            job.started_at = datetime.now(UTC)
            db.commit()

            process = subprocess.Popen(
                [str(self.config.agent_python), *argv],
                cwd=str(self.config.agent_cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            output_lines: list[str] = []

            for line in process.stdout:
                output_lines.append(line.rstrip("\n"))
                job.log_output = "\n".join(output_lines)
                db.commit()

            exit_code = process.wait()
            status, result, error_message = parse_job_output(
                exit_code,
                "\n".join(output_lines),
            )

            job.status = status
            job.result = result
            job.error_message = error_message
            job.finished_at = datetime.now(UTC)
            db.commit()
        except Exception as error:
            db.rollback()
            job = db.get(MtgoJob, job_id)
            job.status = "FAILED"
            job.error_message = str(error)
            job.finished_at = datetime.now(UTC)
            db.commit()
        finally:
            # Notified only after the terminal status is safely committed —
            # `notifier.notify` guarantees it never raises, but it also
            # lives outside the try/except above on purpose, so a bug in
            # notification logic can never trigger the except branch and
            # overwrite an already-committed status with FAILED.
            if job is not None:
                self.notifier.notify(job)
            db.close()
