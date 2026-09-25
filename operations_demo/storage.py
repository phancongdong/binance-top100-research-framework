import json
import os
import tempfile
from pathlib import Path


def safe_path(root: Path, relative: str) -> Path:
    root = Path(root).absolute()
    if root.is_symlink() or not relative or "\\" in relative or ":" in relative:
        raise ValueError("Invalid output path")
    parts = Path(relative).parts
    if Path(relative).is_absolute() or any(part in ("..", ".") for part in parts):
        raise ValueError("Output path escapes root")
    path = root.joinpath(*parts)
    for candidate in (root, *(root.joinpath(*parts[:index]) for index in range(1, len(parts) + 1))):
        if candidate.is_symlink():
            raise ValueError("Symlink in output path")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Output path escapes root")
    return path


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".pending-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def read_json(path: Path) -> dict:
    def reject_nonfinite(value: str):
        raise ValueError(f"Non-finite JSON value: {value}")

    value = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_nonfinite)
    if not isinstance(value, dict):
        raise ValueError(f"Invalid JSON object: {path.name}")
    return value
