"""Additional data-integrity regressions using the CLI as a black box."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "format_references.py"


class DataIntegrityTests(unittest.TestCase):
    def run_records(self, records):
        with tempfile.TemporaryDirectory(prefix="gbt7714-integrity-") as temp:
            root = Path(temp)
            source = root / "input.json"
            source.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
            process = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(source), "--outdir", str(root / "output")],
                capture_output=True, text=True, encoding="utf-8",
            )
            self.assertEqual(process.returncode, 0, process.stderr)
            normalized = json.loads((root / "output" / "normalized.json").read_text(encoding="utf-8"))
            audit = json.loads((root / "output" / "audit.json").read_text(encoding="utf-8"))
            return normalized["records"], audit

    def test_original_values_survive_normalization_and_duplicate_merge(self):
        first = {"id": "raw-a", "type": "J", "authors": ["Gray A"], "language": "en",
                 "title": "Testing lossless provenance", "year": 2024, "container": "Example Journal",
                 "doi": "10.5555/provenance", "raw": "Original line with notes.",
                 "unrecognized_export_field": {"note": "do not silently discard"}}
        second = {**first, "id": "raw-b", "doi": "https://doi.org/10.5555/PROVENANCE",
                  "volume": {"ambiguous_original": "two possible volumes"}}
        records, audit = self.run_records([first, second])
        self.assertEqual(audit["summary"]["duplicate_count"], 1)
        self.assertEqual(records[0]["raw_input"], first)
        originals = [item["raw_input"] for item in records[0]["source_records"]]
        self.assertEqual(originals, [first, second])
        self.assertTrue(any(w["code"] == "invalid_field_type" and w["field"] == "volume"
                            for w in audit["warnings"]))

    def test_dois_differing_only_in_punctuation_are_not_merged(self):
        base = {"type": "J", "authors": ["Gray A"], "language": "en",
                "title": "Identical titles with conflicting identifiers", "year": 2024,
                "container": "Example Journal", "volume": "1", "issue": "1", "pages": "1-9"}
        records, audit = self.run_records([
            {**base, "id": "doi-a", "doi": "10.5555/foo-a"},
            {**base, "id": "doi-b", "doi": "10.5555/fooa"},
        ])
        self.assertEqual(len(records), 2)
        self.assertEqual(audit["summary"]["duplicate_count"], 0)
        self.assertTrue(any("doi" in pair["conflict_fields"]
                            for pair in audit["review_candidates"]))


if __name__ == "__main__":
    unittest.main()
