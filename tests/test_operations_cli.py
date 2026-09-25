import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OperationsCliTests(unittest.TestCase):
    def call(self, *args):
        return subprocess.run([sys.executable, "-B", "-m", "operations_demo", *args], cwd=ROOT, text=True, capture_output=True)

    def test_demo_resume_verify_and_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "operations"
            first = self.call("demo", "--output", str(output))
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn("SYNTHETIC_OPERATIONS_DEMO", first.stdout)
            before = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
            self.assertEqual(self.call("demo", "--output", str(output)).returncode, 0)
            self.assertEqual({p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}, before)
            self.assertEqual(self.call("verify", "--output", str(output)).returncode, 0)
            (output / "evidence" / "worker-summary.json").write_text("{}", encoding="utf-8")
            self.assertEqual(self.call("verify", "--output", str(output)).returncode, 2)
