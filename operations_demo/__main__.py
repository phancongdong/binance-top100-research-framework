"""Offline, synthetic operations exercise; never contacts a service."""

import argparse
import hashlib
import json
from pathlib import Path

from .goals import GoalStore
from .storage import atomic_json, read_json, safe_path
from .worker import WorkerConfig, WorkerRun, verify_worker


GOAL_ID = "synthetic-delivery"
OBJECTIVE = "Verify a bounded local worker and hand over its evidence"
CONFIG = WorkerConfig()


def verify(output: Path) -> dict:
    goal = GoalStore(output).verify_active()
    if goal["goal_id"] != GOAL_ID:
        raise ValueError("Unexpected active goal")
    state = verify_worker(output, CONFIG)
    summary = read_json(safe_path(output, "evidence/worker-summary.json"))
    if summary != {"label": "SYNTHETIC_OPERATIONS_DEMO", "completed_steps": state["next_step"],
                   "worker_state_sha256": hashlib.sha256(safe_path(output, "worker-state.json").read_bytes()).hexdigest()}:
        raise ValueError("Worker summary does not match state")
    return {"label": "SYNTHETIC_OPERATIONS_DEMO", "goal_id": goal["goal_id"],
            "state": goal["state"], "integrity": "VERIFIED_LOCAL_HASHES_ONLY"}


def demo(output: Path) -> dict:
    store = GoalStore(output)
    if store.pointer.exists():
        goal = store.load_active()
        if goal["goal_id"] != GOAL_ID or goal["objective"] != OBJECTIVE:
            raise ValueError("Existing active goal belongs to another exercise")
        if goal["state"] == "DONE_VERIFIED":
            return verify(output)
    else:
        store.create(GOAL_ID, OBJECTIVE, "sample-owner")
        goal = store.load_active()
    if goal["state"] in ("PENDING", "BLOCKED"):
        store.transition(GOAL_ID, "IN_PROGRESS", next_action="Verify the bounded local worker")
    try:
        state = WorkerRun(output, CONFIG).run()
    except (RuntimeError, TimeoutError, InterruptedError):
        store.transition(GOAL_ID, "BLOCKED", blocker="Local worker did not finish",
                         next_action="Inspect the local checkpoint and resume")
        raise
    summary_path = safe_path(output, "evidence/worker-summary.json")
    atomic_json(summary_path, {"label": "SYNTHETIC_OPERATIONS_DEMO", "completed_steps": state["next_step"],
                               "worker_state_sha256": hashlib.sha256(safe_path(output, "worker-state.json").read_bytes()).hexdigest()})
    store.attach_evidence(GOAL_ID, "evidence/worker-summary.json", hashlib.sha256(summary_path.read_bytes()).hexdigest())
    store.transition(GOAL_ID, "DONE_VERIFIED", next_action="Hand over local evidence for human review")
    return verify(output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline synthetic operations example")
    parser.add_argument("command", choices=("demo", "verify"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = demo(args.output) if args.command == "demo" else verify(args.output)
        print(json.dumps(result, sort_keys=True))
    except (OSError, ValueError, RuntimeError, InterruptedError) as exc:
        parser.exit(2, f"local verification failed: {exc}\n")


if __name__ == "__main__":
    main()
