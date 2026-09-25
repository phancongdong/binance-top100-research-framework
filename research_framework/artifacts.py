"""Canonical hashes and root-bound immutable evidence."""
import hashlib
import json
import os
import re
from pathlib import Path, PureWindowsPath


def canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False, ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("not canonical JSON") from exc


def canonical_hash(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_path(root: Path, relative: str) -> Path:
    root = Path(root)
    if not isinstance(relative, str) or "\\" in relative or PureWindowsPath(relative).drive:
        raise ValueError("portable root-relative slash paths required")
    candidate = Path(relative)
    if root.is_symlink() or not relative or candidate.is_absolute() or ".." in candidate.parts or candidate.drive or candidate.anchor:
        raise ValueError("path must be relative and inside the allowed root")
    path = root / candidate
    if any((root / Path(*candidate.parts[:index])).is_symlink() for index in range(1, len(candidate.parts) + 1)):
        raise ValueError("symlink in path")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("path escapes allowed root")
    return path


def read_json(path: Path) -> dict:
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    try:
        value = json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")), object_pairs_hook=unique_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("unreadable evidence") from exc
    if not isinstance(value, dict):
        raise ValueError("evidence must be an object")
    return value


def write_protected(root: Path, relative: str, value: object) -> str:
    path = safe_path(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = canonical_bytes(value)
    try:
        with path.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise ValueError("protected artifact already exists") from exc
    return hashlib.sha256(content).hexdigest()


def verify_manifest(root: Path) -> dict:
    from .workflow import PHASES
    root = Path(root)
    state = read_json(safe_path(root, "state.json"))
    checksum = state.pop("checksum", None)
    if not isinstance(checksum, str) or checksum != canonical_hash(state):
        raise ValueError("state checksum mismatch")
    if state.get("schema") != 1 or set(state) != {"schema", "label", "identity", "completed", "artifacts", "inflight"} or state["label"] != "SYNTHETIC_WORKFLOW_DEMO":
        raise ValueError("invalid state contract")
    completed = state["completed"]
    if not isinstance(completed, list) or completed != list(PHASES[:len(completed)]) or len(completed) > len(PHASES):
        raise ValueError("invalid phase sequence")
    if state["inflight"] is not None:
        raise ValueError("unresolved phase invocation; manual evidence recovery required")
    if not isinstance(state["identity"], dict) or set(state["identity"]) != {"spec", "code", "data"} or not all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) for value in state["identity"].values()):
        raise ValueError("invalid identity")
    artifacts = state["artifacts"]
    if not isinstance(artifacts, dict) or set(artifacts) != {f"phases/{phase}.json" for phase in completed}:
        raise ValueError("manifest artifact set differs")
    for relative, expected in artifacts.items():
        path = safe_path(root, relative)
        if not path.is_file() or file_hash(path) != expected:
            raise ValueError("artifact hash mismatch")
        payload = read_json(path)
        if payload.get("phase") != Path(relative).stem or payload.get("identity") != state["identity"]:
            raise ValueError("artifact identity differs")
    phase_root = safe_path(root, "phases")
    if phase_root.exists() and {path.name for path in phase_root.iterdir()} != {f"{phase}.json" for phase in completed}:
        raise ValueError("unmanifested phase artifact")
    state["checksum"] = checksum
    return state
