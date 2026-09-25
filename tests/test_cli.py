import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def call(self, *args):
        return subprocess.run([sys.executable, "-B", "-m", "research_framework", *args], cwd=ROOT, text=True, capture_output=True)

    def test_demo_resume_and_verify_detects_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            output = str(Path(directory) / "demo")
            first = self.call("demo", "--output", output)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn("SYNTHETIC_WORKFLOW_DEMO", first.stdout)
            self.assertEqual(self.call("demo", "--output", output).returncode, 0)
            self.assertEqual(self.call("verify", "--output", output).returncode, 0)
            artifact = Path(output) / "phases" / "PIT.json"
            payload = json.loads(artifact.read_text(encoding="utf-8"))
            payload["evidence"]["synthetic_record_count"] = 900
            artifact.write_text(json.dumps(payload), encoding="utf-8")
            self.assertNotEqual(self.call("verify", "--output", output).returncode, 0)
