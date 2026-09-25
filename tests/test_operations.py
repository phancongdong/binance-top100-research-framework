import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from operations_demo.goals import GoalStore
from operations_demo.worker import WorkerConfig, WorkerRun, verify_worker


class GoalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = GoalStore(self.root)

    def test_transition_identity_and_evidence(self):
        self.store.create("sample-goal", "Deliver sample", "sample-owner")
        with self.assertRaises(ValueError):
            self.store.create("replacement", "Other", "other-owner")
        with self.assertRaises(ValueError):
            self.store.transition("sample-goal", "DONE_VERIFIED", next_action="handover")
        self.store.transition("sample-goal", "IN_PROGRESS", next_action="check")
        self.store.transition("sample-goal", "BLOCKED", blocker="missing", next_action="produce")
        self.store.transition("sample-goal", "IN_PROGRESS", next_action="check")
        self.assertEqual(GoalStore(self.root).load_active()["goal_id"], "sample-goal")
        with self.assertRaises(ValueError):
            self.store.transition("sample-goal", "DONE_VERIFIED", next_action="handover")
        evidence = self.root / "evidence" / "sample.json"
        evidence.parent.mkdir()
        evidence.write_text('{"status":"ok"}', encoding="utf-8")
        digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
        self.store.attach_evidence("sample-goal", "evidence/sample.json", digest)
        evidence.write_text("tampered", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.store.transition("sample-goal", "DONE_VERIFIED", next_action="handover")
        evidence.unlink()
        with self.assertRaises(ValueError):
            self.store.transition("sample-goal", "DONE_VERIFIED", next_action="handover")
        evidence.write_text('{"status":"ok"}', encoding="utf-8")
        self.store.transition("sample-goal", "DONE_VERIFIED", next_action="handover")
        self.assertEqual(self.store.verify_active()["state"], "DONE_VERIFIED")
        evidence.write_text("tampered", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.store.verify_active()
        with self.assertRaises(ValueError):
            self.store.create("replacement", "Other", "other-owner")

    def test_path_escape(self):
        self.store.create("sample-goal", "Deliver sample", "sample-owner")
        for path in ("../outside.json", "/outside.json", "evidence/../../outside.json", chr(67) + ":/outside.json"):
            with self.assertRaises(ValueError):
                self.store.attach_evidence("sample-goal", path, "0" * 64)

    def test_symlinked_goal_directory_is_rejected(self):
        external = self.root / "external"
        external.mkdir()
        try:
            (self.root / "goals").symlink_to(external, target_is_directory=True)
        except OSError:
            self.skipTest("Symlinks unavailable")
        with self.assertRaises(ValueError):
            self.store.create("sample-goal", "Deliver sample", "sample-owner")


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_invalid_config(self):
        for values in ({"max_steps": 0}, {"retry_limit": -1}, {"max_seconds": 0}, {"max_steps": True}):
            with self.assertRaises(ValueError):
                WorkerConfig(**values)

    def test_failure_and_interruption_resume(self):
        config = WorkerConfig(max_steps=3, retry_limit=1, max_seconds=10)
        run = WorkerRun(self.root, config)
        with self.assertRaises(RuntimeError):
            run.run(failures={1: 2})
        state = json.loads((self.root / "worker-state.json").read_text(encoding="utf-8"))
        self.assertEqual((state["next_step"], state["status"]), (1, "BLOCKED"))
        with self.assertRaises(InterruptedError):
            run.run(interrupt_at=2)
        state = json.loads((self.root / "worker-state.json").read_text(encoding="utf-8"))
        self.assertEqual((state["next_step"], state["status"]), (2, "INTERRUPTED"))
        run.run()
        self.assertEqual([item["step"] for item in verify_worker(self.root, config)["records"]], [0, 1, 2])

    def test_corrupt_incomplete_checkpoint_rejected(self):
        config = WorkerConfig(max_steps=3, retry_limit=1, max_seconds=10)
        run = WorkerRun(self.root, config)
        with self.assertRaises(InterruptedError):
            run.run(interrupt_at=1)
        state_path = self.root / "worker-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["records"][0]["attempts"] = 900
        state_path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaises(ValueError):
            run.run()
