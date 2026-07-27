import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MtgoAgentConfig:
    agent_python: Path
    agent_cwd: Path

    @classmethod
    def from_env(cls) -> "MtgoAgentConfig":
        repo_root = Path(__file__).resolve().parents[3]
        agent_cwd = Path(os.environ.get("MTGO_AGENT_DIR", repo_root / "agent"))
        default_python = agent_cwd / ".venv" / "Scripts" / "python.exe"
        agent_python = Path(os.environ.get("MTGO_AGENT_PYTHON", default_python))

        return cls(
            agent_python=agent_python,
            agent_cwd=agent_cwd,
        )
