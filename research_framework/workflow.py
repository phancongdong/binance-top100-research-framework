"""A resumable order gate, not an independent research approval."""
import os
import re
from pathlib import Path
from typing import Protocol

from .artifacts import canonical_bytes, canonical_hash, safe_path, verify_manifest, write_protected


PHASES = ("RESERVE_HOLDOUT", "FREEZE_SPEC", "SOURCE_AUDIT", "ETL_AUDIT", "TRAIN", "LOCK", "OOS", "PIT", "HOLDOUT", "FINALIZE")


class PhaseAdapter(Protocol):
    def execute(self, phase: str, context: dict) -> dict: ...


class Workflow:
    def __init__(self, root: Path, spec_hash: str, code_hash: str, data_hash: str, adapter: PhaseAdapter):
        self.root = Path(root)
        self.adapter = adapter
        self.identity = {"spec": spec_hash, "code": code_hash, "data": data_hash}
        if not all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) for value in self.identity.values()):
            raise ValueError("spec/code/data SHA-256 identities required")
        self.root.mkdir(parents=True, exist_ok=True)
        if safe_path(self.root, "state.json").exists():
            self.state = verify_manifest(self.root)
            if self.state["identity"] != self.identity:
                raise ValueError("resume identity drift")
        else:
            if any(self.root.iterdir()):
                raise ValueError("unmanifested output exists")
            self.state = {"schema": 1, "label": "SYNTHETIC_WORKFLOW_DEMO", "identity": self.identity, "completed": [], "artifacts": {}, "inflight": None}
            self._save()

    @property
    def completed(self) -> tuple[str, ...]:
        return tuple(self.state["completed"])

    def _save(self) -> None:
        content = {key: value for key, value in self.state.items() if key != "checksum"}
        content["checksum"] = canonical_hash(content)
        path = safe_path(self.root, "state.json")
        temporary = safe_path(self.root, "state.pending")
        if temporary.exists():
            raise ValueError("pending state write exists")
        try:
            with temporary.open("xb") as handle:
                handle.write(canonical_bytes(content))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()
        self.state = content

    def advance(self, phase: str) -> None:
        if verify_manifest(self.root) != self.state:
            raise ValueError("state changed since workflow opened")
        if len(self.completed) >= len(PHASES) or phase != PHASES[len(self.completed)]:
            raise ValueError("phase skipped, repeated or out of order")
        self.state["inflight"] = phase
        self._save()
        context = {"identity": dict(self.identity), "completed": self.completed, "label": self.state["label"], "locked_hash": self.state["artifacts"].get("phases/LOCK.json")}
        result = self.adapter.execute(phase, context)
        if not isinstance(result, dict) or result.get("accepted") is not True:
            raise ValueError("adapter did not accept the phase")
        relative = f"phases/{phase}.json"
        digest = write_protected(self.root, relative, {"phase": phase, "identity": self.identity, "evidence": result, "label": self.state["label"]})
        self.state["completed"].append(phase)
        self.state["artifacts"][relative] = digest
        self.state["inflight"] = None
        self._save()

    def run(self) -> tuple[str, ...]:
        while len(self.completed) < len(PHASES):
            self.advance(PHASES[len(self.completed)])
        return self.completed


def replay_label(completed: tuple[str, ...]) -> str:
    return "RETROSPECTIVE_REPLAY" if "HOLDOUT" in completed else "UNOPENED_HOLDOUT"
