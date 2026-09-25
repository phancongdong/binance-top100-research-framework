import hashlib
import re
from pathlib import Path, PurePosixPath

from .storage import atomic_json, read_json, safe_path


TRANSITIONS = {
    "PENDING": {"IN_PROGRESS"},
    "IN_PROGRESS": {"BLOCKED", "DONE_VERIFIED"},
    "BLOCKED": {"IN_PROGRESS"},
    "DONE_VERIFIED": set(),
}


class GoalStore:
    def __init__(self, root: Path):
        self.root = Path(root).absolute()
        safe_path(self.root, "active-goal.json")

    @property
    def pointer(self) -> Path:
        return safe_path(self.root, "active-goal.json")

    def _goal_path(self, goal_id: str) -> Path:
        if not isinstance(goal_id, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", goal_id) is None:
            raise ValueError("Invalid goal ID")
        return safe_path(self.root, f"goals/{goal_id}.json")

    def _evidence_path(self, reference: str) -> Path:
        if not isinstance(reference, str) or "\\" in reference:
            raise ValueError("Invalid evidence reference")
        relative = PurePosixPath(reference)
        if relative.is_absolute() or ".." in relative.parts or len(relative.parts) < 2 or relative.parts[0] != "evidence":
            raise ValueError("Evidence must be inside evidence/")
        return safe_path(self.root, reference)

    def create(self, goal_id: str, objective: str, owner: str) -> dict:
        path = self._goal_path(goal_id)
        if not objective or not owner:
            raise ValueError("Objective and owner are required")
        if self.pointer.exists():
            if self.load_active()["state"] != "DONE_VERIFIED":
                raise ValueError("An active goal already exists")
            self.verify_active()
        if path.exists():
            raise ValueError("Goal ID already exists")
        record = {"goal_id": goal_id, "objective": objective, "state": "PENDING", "owner": owner,
                  "blocker": None, "next_action": "Start work", "evidence": []}
        atomic_json(path, record)
        atomic_json(self.pointer, {"goal_id": goal_id})
        return record

    def load_active(self) -> dict:
        pointer = read_json(self.pointer)
        goal_id = pointer.get("goal_id")
        record = read_json(self._goal_path(goal_id))
        if record.get("goal_id") != goal_id or record.get("state") not in TRANSITIONS:
            raise ValueError("Active goal identity or state mismatch")
        if not all(isinstance(record.get(key), str) and record[key] for key in ("objective", "owner", "next_action")):
            raise ValueError("Active goal fields are incomplete")
        return record

    def _active_id(self, goal_id: str) -> dict:
        record = self.load_active()
        if record["goal_id"] != goal_id:
            raise ValueError("Requested goal is not active")
        return record

    def attach_evidence(self, goal_id: str, reference: str, sha256: str) -> dict:
        record = self._active_id(goal_id)
        self._evidence_path(reference)
        if record["state"] != "IN_PROGRESS" or not isinstance(sha256, str) or re.fullmatch(r"[0-9a-f]{64}", sha256) is None:
            raise ValueError("Evidence requires an in-progress goal and SHA-256")
        evidence = {"path": reference, "sha256": sha256}
        if evidence not in record["evidence"]:
            record["evidence"].append(evidence)
            atomic_json(self._goal_path(goal_id), record)
        return record

    def verify_evidence(self, record: dict) -> None:
        references = record.get("evidence")
        if not isinstance(references, list) or not references:
            raise ValueError("Completion requires local evidence")
        for item in references:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not isinstance(item.get("sha256"), str) or re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) is None:
                raise ValueError("Invalid evidence reference")
            path = self._evidence_path(item["path"])
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
                raise ValueError("Missing or stale local evidence")

    def transition(self, goal_id: str, state: str, *, next_action: str, blocker: str | None = None) -> dict:
        record = self._active_id(goal_id)
        if state not in TRANSITIONS[record["state"]] or not next_action:
            raise ValueError("Illegal goal transition or missing next action")
        if state == "BLOCKED" and not blocker:
            raise ValueError("Blocked goal requires a blocker")
        if state == "DONE_VERIFIED":
            self.verify_evidence(record)
        record.update(state=state, blocker=blocker if state == "BLOCKED" else None, next_action=next_action)
        atomic_json(self._goal_path(goal_id), record)
        return record

    def verify_active(self) -> dict:
        record = self.load_active()
        if record["state"] != "DONE_VERIFIED":
            raise ValueError("Goal has not been verified")
        self.verify_evidence(record)
        return record
