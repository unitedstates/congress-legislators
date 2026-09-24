"""Tests for comments in manually maintained YAML addenda."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


LINTER = Path(__file__).resolve().parent / "are_files_linted.py"


class TestManualAddendumLint(unittest.TestCase):
    def check_yaml(self, filename, body):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / filename
            path.write_text(body)
            result = subprocess.run(
                [sys.executable, str(LINTER)],
                cwd=directory,
                capture_output=True,
                text=True,
            )
            self.assertEqual(path.read_text(), body)
            return result

    def test_interior_manual_comments_are_preserved(self):
        body = "AA:\n- name: One\n\n# Source note for BB\nBB:\n- name: Two\n"
        result = self.check_yaml("committee-membership-manual-addendum.yaml", body)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_manual_data_still_must_be_canonical(self):
        body = "AA: {name: One}\n\n# Source note for BB\nBB:\n- name: Two\n"
        result = self.check_yaml("committee-membership-manual-addendum.yaml", body)
        self.assertEqual(result.returncode, 1)
        self.assertIn("AA:", result.stdout)

    def test_comment_exception_is_limited_to_manual_addendum(self):
        body = "AA:\n- name: One\n\n# Source note for BB\nBB:\n- name: Two\n"
        result = self.check_yaml("other.yaml", body)
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
