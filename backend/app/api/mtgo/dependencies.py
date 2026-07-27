from app.core.mtgo_agent_config import MtgoAgentConfig
from app.core.notification_config import NotificationConfig
from app.services.mtgo.mtgo_job_notifier_service import MtgoJobNotifierService
from app.services.mtgo.mtgo_job_runner_service import MtgoJobRunnerService

_runner = MtgoJobRunnerService(
    MtgoAgentConfig.from_env(),
    MtgoJobNotifierService(
        NotificationConfig.from_env(),
    ),
)


def get_job_runner() -> MtgoJobRunnerService:
    """A single process-wide runner instance — it holds no per-request
    state (only the agent's python/cwd paths), so unlike `get_db` it
    doesn't need a fresh instance per request. Exposed as a `Depends()`
    purely so tests can override it with a fake via
    `app.dependency_overrides`, the same way `get_db` is overridden."""
    return _runner
