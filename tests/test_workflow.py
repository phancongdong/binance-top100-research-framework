import json
import tempfile
import unittest
from pathlib import Path

from research_framework.artifacts import canonical_hash, safe_path, verify_manifest, write_protected
from research_framework.workflow import PHASES, Workflow


class CountAdapter:
    def execute(self, phase, context):
        return {"accepted": True, "synthetic_record_count": 2}


class WorkflowTests(unittest.TestCase):
    SPEC = "a" * 64
    CODE = "b" * 64
    DATA = "c" * 64

    def test_identity_must_be_sha256(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                Workflow(Path(directory) / "new", "not-a-hash", self.CODE, self.DATA, CountAdapter())

    def test_phase_order_and_holdout_once(self):
        with tempfile.TemporaryDirectory() as directory:
            flow = Workflow(Path(directory), self.SPEC, self.CODE, self.DATA, CountAdapter())
            with self.assertRaises(ValueError):
                flow.advance("TRAIN")
            for phase in PHASES:
                flow.advance(phase)
            self.assertEqual(flow.completed, PHASES)
            with self.assertRaises(ValueError):
                flow.advance("HOLDOUT")
            self.assertEqual(Workflow(Path(directory), self.SPEC, self.CODE, self.DATA, CountAdapter()).run(), PHASES)
            with self.assertRaises(ValueError):
                Workflow(Path(directory), "d" * 64, self.CODE, self.DATA, CountAdapter())
            with self.assertRaises(ValueError):
                Workflow(Path(directory), "not-a-hash", self.CODE, self.DATA, CountAdapter())

    def test_stale_instance_and_failed_callback_are_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = Workflow(root, self.SPEC, self.CODE, self.DATA, CountAdapter())
            stale = Workflow(root, self.SPEC, self.CODE, self.DATA, CountAdapter())
            first.advance("RESERVE_HOLDOUT")
            with self.assertRaises(ValueError):
                stale.advance("RESERVE_HOLDOUT")
        class Failure:
            def execute(self, phase, context):
                raise RuntimeError("interrupted")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            flow = Workflow(root, self.SPEC, self.CODE, self.DATA, Failure())
            with self.assertRaises(RuntimeError):
                flow.advance("RESERVE_HOLDOUT")
            with self.assertRaises(ValueError):
                Workflow(root, self.SPEC, self.CODE, self.DATA, CountAdapter())
        class Rejected:
            def execute(self, phase, context):
                return {"accepted": False}
        with tempfile.TemporaryDirectory() as directory:
            flow = Workflow(Path(directory), self.SPEC, self.CODE, self.DATA, Rejected())
            with self.assertRaises(ValueError):
                flow.advance("RESERVE_HOLDOUT")

    def test_tamper_and_stale_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            flow = Workflow(root, self.SPEC, self.CODE, self.DATA, CountAdapter())
            flow.advance("RESERVE_HOLDOUT")
            verify_manifest(root)
            (root / "phases" / "RESERVE_HOLDOUT.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_manifest(root)
            with self.assertRaises(ValueError):
                Workflow(root, self.SPEC, self.CODE, self.DATA, CountAdapter())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            flow = Workflow(root, self.SPEC, self.CODE, self.DATA, CountAdapter())
            flow.advance("RESERVE_HOLDOUT")
            state = root / "state.json"
            payload = json.loads(state.read_text(encoding="utf-8"))
            payload["completed"] = []
            state.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_manifest(root)

    def test_canonical_and_path_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(canonical_hash({"b": 2, "a": 1}), canonical_hash({"a": 1, "b": 2}))
            with self.assertRaises(ValueError):
                canonical_hash({"bad": float("nan")})
            with self.assertRaises(ValueError):
                safe_path(root, "../escape")
            with self.assertRaises(ValueError):
                safe_path(root, str(root / "absolute"))
            with self.assertRaises(ValueError):
                safe_path(root, "folder\\..\\escape")
            with self.assertRaises(ValueError):
                safe_path(root, chr(90) + ":/escape")
            write_protected(root, "evidence.json", {"one": 1})
            with self.assertRaises(ValueError):
                write_protected(root, "evidence.json", {"one": 2})
            outside = root.parent / "external-for-symlink-test"
            try:
                (root / "link").symlink_to(outside, target_is_directory=True)
            except OSError:
                pass
            else:
                with self.assertRaises(ValueError):
                    safe_path(root, "link/evidence.json")
