import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
import requests
from scripts import refresh_explorer_data as explorer


class ExplorerDataTests(unittest.TestCase):
    def application(self, volume=5, unit="P"):
        return {"Year": 2025, "Country of asylum (ISO)": "GBR",
                "Country of asylum": "United Kingdom", "Cases / Persons": unit, "applied": volume}

    def decision(self):
        return {"Year": 2025, "Country of asylum (ISO)": "DEU",
                "Country of asylum": "Germany", "Cases / Persons": "P",
                "Recognized decisions": 3, "Complementary protection": 2,
                "Rejected decisions": 4, "Otherwise closed": 0, "Total decisions": 9}

    def test_units_stay_separate_and_decision_only_country_survives(self):
        frames = {"asylum-applications": pd.DataFrame([
            self.application(5), self.application(2), self.application(11, "C")]),
            "asylum-decisions": pd.DataFrame([self.decision()])}
        data = explorer.build(frames, {})
        by_key = {(row["country"], row["unit"]): row for row in data["rows"]}
        self.assertEqual(by_key["GBR", "P"]["applications"], 7)
        self.assertEqual(by_key["GBR", "C"]["applications"], 11)
        self.assertEqual(by_key["DEU", "P"]["decisions"], 9)
        self.assertIsNone(by_key["DEU", "P"]["applications"])
        self.assertIsNone(by_key["GBR", "P"]["decisions"])
        self.assertEqual(data["metadata"]["outcome_total_mismatch_rows"], 0)

    def test_invalid_source_values_fail(self):
        for field, value in [("applied", -1), ("applied", 2.5),
                             ("Year", 2026), ("Cases / Persons", "unknown")]:
            with self.subTest(field=field, value=value):
                row = self.application()
                row[field] = value
                with self.assertRaises(ValueError):
                    explorer.validate(pd.DataFrame([row]), "asylum-applications", 2025)

    def test_failed_download_does_not_replace_previous_dataset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "explorer.json"
            previous = '{"previous":"published snapshot"}'
            path.write_text(previous, encoding="utf-8")
            with patch.object(explorer, "DEST", Path(directory)), patch.object(
                    explorer.requests, "get", side_effect=requests.HTTPError("Unavailable")):
                with self.assertRaises(requests.HTTPError):
                    explorer.refresh()
            self.assertEqual(path.read_text(encoding="utf-8"), previous)


if __name__ == "__main__":
    unittest.main()
