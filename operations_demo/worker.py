import time
from dataclasses import asdict, dataclass
from pathlib import Path

from .storage import atomic_json, read_json, safe_path


@dataclass(frozen=True)
class WorkerConfig:
    max_steps: int = 3
    retry_limit: int = 1
    max_seconds: int = 10

    def __post_init__(self):
        for name, lower, upper in (("max_steps", 1, 100), ("retry_limit", 0, 5), ("max_seconds", 1, 300)):
            value = getattr(self, name)
            if type(value) is not int or not lower <= value <= upper:
                raise ValueError(f"{name} must be an integer from {lower} to {upper}")


def validate_progress(state: dict, config: WorkerConfig) -> None:
    records = state.get("records")
    if state.get("label") != "SYNTHETIC_OPERATIONS_DEMO" or state.get("config") != asdict(config):
        raise ValueError("Worker identity or configuration differs")
    if state.get("status") not in ("IN_PROGRESS", "BLOCKED", "INTERRUPTED", "DONE") or not isinstance(records, list):
        raise ValueError("Worker status or records invalid")
    if type(state.get("next_step")) is not int or state["next_step"] != len(records) or not 0 <= len(records) <= config.max_steps:
        raise ValueError("Worker progress is inconsistent")
    for index, record in enumerate(records):
        if not isinstance(record, dict) or record.get("step") != index or record.get("health") != "OK" or type(record.get("attempts")) is not int or not 1 <= record["attempts"] <= config.retry_limit + 1:
            raise ValueError("Worker record is inconsistent")
    if (state["status"] == "DONE") != (state["next_step"] == config.max_steps):
        raise ValueError("Worker completion status inconsistent")


def verify_worker(root: Path, config: WorkerConfig) -> dict:
    state = read_json(safe_path(root, "worker-state.json"))
    validate_progress(state, config)
    if state["status"] != "DONE":
        raise ValueError("Worker is incomplete")
    return state


class WorkerRun:
    def __init__(self, root: Path, config: WorkerConfig):
        self.root = Path(root).absolute()
        self.path = safe_path(self.root, "worker-state.json")
        self.config = config

    def run(self, *, failures: dict[int, int] | None = None, interrupt_at: int | None = None) -> dict:
        failures = failures or {}
        self.path = safe_path(self.root, "worker-state.json")
        if self.path.exists():
            state = read_json(self.path)
            validate_progress(state, self.config)
            if state.get("status") == "DONE":
                return verify_worker(self.root, self.config)
        else:
            state = {"label": "SYNTHETIC_OPERATIONS_DEMO", "config": asdict(self.config),
                     "status": "IN_PROGRESS", "next_step": 0, "records": []}
            atomic_json(self.path, state)
        deadline = time.monotonic() + self.config.max_seconds
        for step in range(state["next_step"], self.config.max_steps):
            if interrupt_at == step:
                state["status"] = "INTERRUPTED"
                atomic_json(self.path, state)
                raise InterruptedError("Synthetic interruption before checkpoint")
            for attempt in range(self.config.retry_limit + 1):
                if time.monotonic() >= deadline:
                    state["status"] = "BLOCKED"
                    atomic_json(self.path, state)
                    raise TimeoutError("Worker time budget exceeded")
                if attempt < failures.get(step, 0):
                    if attempt == self.config.retry_limit:
                        state["status"] = "BLOCKED"
                        atomic_json(self.path, state)
                        raise RuntimeError("Synthetic retry budget exceeded")
                    continue
                state["records"].append({"step": step, "health": "OK", "attempts": attempt + 1})
                state["next_step"] = step + 1
                state["status"] = "DONE" if step + 1 == self.config.max_steps else "IN_PROGRESS"
                atomic_json(self.path, state)
                break
        return verify_worker(self.root, self.config)
