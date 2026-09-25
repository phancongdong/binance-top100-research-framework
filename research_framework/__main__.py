"""Offline synthetic demonstration and artifact verification."""
import argparse
import json
from pathlib import Path

from .artifacts import verify_manifest
from .demo import demo_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline synthetic research workflow")
    parser.add_argument("command", choices=("demo", "verify"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "demo":
            completed = demo_workflow(args.output).run()
            print(json.dumps({"label": "SYNTHETIC_WORKFLOW_DEMO", "completed": list(completed), "research_authority": "NONE"}))
        else:
            state = verify_manifest(args.output)
            print(json.dumps({"label": state["label"], "completed": state["completed"], "integrity": "VERIFIED_LOCAL_HASHES_ONLY"}))
    except (OSError, ValueError) as exc:
        parser.exit(2, f"verification failed: {exc}\n")


if __name__ == "__main__":
    main()
