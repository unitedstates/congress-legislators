"""Regression tests for Senate member names used by the committee scraper."""

import sys
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from committee_membership import build_senator_lookup


class TestSenatorLookup(unittest.TestCase):
    def test_darline_graham_uses_senate_last_name(self):
        data_path = Path(__file__).resolve().parents[1] / "legislators-current.yaml"
        with data_path.open() as data_file:
            legislators = yaml.safe_load(data_file)

        senators = build_senator_lookup(legislators)
        senator = senators[("SC", "Graham")]

        self.assertEqual(senator["id"]["bioguide"], "G000608")
        self.assertEqual(senator["name"]["last"], "Graham Nordone")
        self.assertEqual(senator["name"]["official_full"], "Darline Graham")


if __name__ == "__main__":
    unittest.main()
