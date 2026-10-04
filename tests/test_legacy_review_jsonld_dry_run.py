from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


class LegacyReviewJsonLdExactDryRunTest(unittest.TestCase):
    def test_exact_default_dry_run_721_of_721(self) -> None:
        root = Path(__file__).resolve().parents[1]
        cmd = [sys.executable, str(root / "scripts" / "remediate_legacy_review_jsonld.py")]
        proc = subprocess.run(
            cmd,
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.stderr:
            print(proc.stderr)
        print(proc.stdout)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)
        self.assertIs(data.get("ok"), True)
        self.assertEqual(data.get("mode"), "DRY_RUN")
        self.assertEqual(data.get("candidate_pages"), 721)
        self.assertEqual(data.get("expected_first_run_pages"), 721)
        files = data.get("files")
        self.assertIsInstance(files, list)
        self.assertEqual(len(files), 721)
        self.assertEqual(
            sorted(item["path"] for item in files),
            sorted(str(p.relative_to(root)).replace("\\", "/") for p in (root / "review").glob("*.html")),
        )


if __name__ == "__main__":
    unittest.main()
