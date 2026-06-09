"""Storage-policy tests: installer env defaults, dir creation, cleanup safety.

Filesystem + subprocess assertions; runs in the same unittest suite.
"""
import os
import subprocess
import tempfile
import time
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class EnvDefaultsTests(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(REPO, "install.sh"), encoding="utf-8") as fh:
            self.src = fh.read()

    def test_minimal_storage_env_defaults_present(self):
        for line in (
            "FILE_KEEP_ORIGINAL=false",
            "FILE_RETENTION_HOURS=24",
            "TRANSCRIPTS_ENABLED=true",
            "TRANSCRIPTS_DIR=transcripts",
            "UPLOADS_TMP_DIR=uploads/tmp",
        ):
            self.assertIn(line, self.src, f"missing env default: {line}")

    def test_installer_creates_storage_dirs(self):
        self.assertIn("uploads/tmp", self.src)
        self.assertIn("/transcripts", self.src)


class CleanupScriptTests(unittest.TestCase):
    """The cleanup script must delete aged uploads/tmp files but NEVER transcripts."""

    def setUp(self):
        self.lab = tempfile.mkdtemp(prefix="wayan-lab-")
        self.script = os.path.join(REPO, "scripts", "cleanup-uploads.sh")

    def _touch_aged(self, path, hours_old):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write("x")
        old = time.time() - hours_old * 3600
        os.utime(path, (old, old))

    def test_deletes_aged_uploads_but_keeps_transcripts(self):
        ws = os.path.join(self.lab, "jupiter")
        old_upload = os.path.join(ws, "uploads", "tmp", "old.bin")
        new_upload = os.path.join(ws, "uploads", "tmp", "fresh.bin")
        transcript = os.path.join(ws, "transcripts", "keep.md")
        self._touch_aged(old_upload, hours_old=48)     # older than retention
        self._touch_aged(new_upload, hours_old=0)      # fresh
        self._touch_aged(transcript, hours_old=48)     # old, but protected

        env = dict(os.environ, WAYAN_LAB_DIR=self.lab, FILE_RETENTION_HOURS="1")
        res = subprocess.run(["bash", self.script], env=env,
                             capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)

        self.assertFalse(os.path.exists(old_upload), "aged upload should be deleted")
        self.assertTrue(os.path.exists(new_upload), "fresh upload must be kept")
        self.assertTrue(os.path.exists(transcript), "transcripts must NEVER be deleted")


if __name__ == "__main__":
    unittest.main()
