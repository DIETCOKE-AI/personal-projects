"""Black-box acceptance tests with independent, hand-written expected results.

Run from the skill directory: python -m unittest discover -s tests -v
Only the Python standard library is required. All actual outputs use temporary
directories, so the tests do not overwrite example or user files.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "format_references.py"
FIXTURE = ROOT / "examples" / "mixed_references.json"
EXPECTED = ROOT / "examples" / "expected_references.txt"


class FormatterAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="gbt7714-tests-")
        cls.work = Path(cls.tmp.name)
        cls.output = cls.work / "fixture-output"
        cls.fixture_run = subprocess.run(
            [sys.executable, str(SCRIPT), "--input", str(FIXTURE), "--outdir", str(cls.output)],
            capture_output=True, text=True, encoding="utf-8",
        )
        if cls.fixture_run.returncode != 0:
            raise AssertionError(f"Fixture run failed: {cls.fixture_run.stdout}\n{cls.fixture_run.stderr}")
        cls.references = (cls.output / "references.txt").read_text(encoding="utf-8")
        cls.lines = cls.references.splitlines()
        cls.audit = json.loads((cls.output / "audit.json").read_text(encoding="utf-8"))
        cls.normalized = json.loads((cls.output / "normalized.json").read_text(encoding="utf-8"))["records"]
        cls.drafts = (cls.output / "drafts.txt").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def by_source(self, source_id):
        return next(item for item in self.normalized if source_id in item["source_ids"])

    def run_input(self, name, payload, *args):
        source = self.work / f"{name}.json"
        source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        outdir = self.work / name
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--input", str(source), "--outdir", str(outdir), *args],
            capture_output=True, text=True, encoding="utf-8",
        )
        return result, outdir

    def test_full_fixture_matches_independently_written_golden_file(self):
        self.assertEqual(self.references.strip(), EXPECTED.read_text(encoding="utf-8").strip())

    def test_user_chinese_journal_example_exact(self):
        self.assertEqual(self.lines[0], "[1] 王泽昊, 朱振华, 谢童欣, 等. 混合专家大语言模型的系统与架构优化技术综述[J]. 电子与信息学报, 2025, 47(11): 4055-4078.")

    def test_user_english_conference_example_exact(self):
        self.assertEqual(self.lines[1], "[2] Sun Q, Wang H, Zhan J, et al. Generalizing motion planners with mixture of experts for autonomous driving[C]//2025 IEEE International Conference on Robotics and Automation (ICRA). IEEE, 2025: 6033-6039.")

    def test_counts_and_conservation(self):
        expected = json.loads((ROOT / "examples" / "expected_summary.json").read_text(encoding="utf-8"))
        summary = self.audit["summary"]
        for key in ("input_count", "unique_count", "duplicate_count", "formatted_count", "draft_count"):
            self.assertEqual(summary[key], expected[key], key)
        self.assertEqual(summary["input_count"], summary["unique_count"] + summary["duplicate_count"])
        self.assertEqual(summary["unique_count"], summary["formatted_count"] + summary["draft_count"])

    def test_duplicate_pairs_and_traceability(self):
        actual = {(item["kept_source_id"], item["duplicate_source_id"]) for item in self.audit["duplicates"]}
        self.assertEqual(actual, {("r04", "r07"), ("r03", "r08"), ("r09", "r10")})
        self.assertEqual(len(self.audit["source_to_output"]), 20)
        self.assertEqual(set(self.by_source("r04")["source_ids"]), {"r04", "r07"})

    def test_doi_variants_normalized(self):
        self.assertEqual(self.by_source("r07")["doi"], "10.5555/example.004")

    def test_duplicate_enriches_missing_pages(self):
        item = self.by_source("r09")
        self.assertEqual(item["pages"], "201-216")
        self.assertIn("r10", item["source_ids"])
        self.assertIn("201-216", self.lines[6])

    def test_missing_information_is_draft_without_invention(self):
        self.assertNotIn("面向边缘设备的模型压缩方法", self.references)
        self.assertNotIn("An evaluation protocol for expert routing", self.references)
        self.assertIn("面向边缘设备的模型压缩方法", self.drafts)
        self.assertIn("An evaluation protocol for expert routing", self.drafts)
        self.assertFalse(self.by_source("r13")["authors"])
        self.assertFalse(self.by_source("r14").get("year"))

    def test_same_title_different_editions_are_retained(self):
        self.assertIsNot(self.by_source("r03"), self.by_source("r11"))
        self.assertIn("2版. 北京: 示例出版社, 2022.", self.references)
        self.assertIn("3版. 北京: 示例出版社, 2022.", self.references)

    def test_conflicting_doi_does_not_silently_merge(self):
        self.assertIsNot(self.by_source("r04"), self.by_source("r15"))
        self.assertNotEqual(self.by_source("r04")["doi"], self.by_source("r15")["doi"])
        candidate_pairs = [set(item["left_source_ids"] + item["right_source_ids"]) for item in self.audit["review_candidates"]]
        self.assertTrue(any({"r04", "r15"} <= pair for pair in candidate_pairs))

    def test_fuzzy_title_is_retained_as_review_candidate(self):
        self.assertIsNot(self.by_source("r04"), self.by_source("r12"))
        self.assertIn("A survey of sparse experts routing", self.references)
        candidate_pairs = [set(item["left_source_ids"] + item["right_source_ids"]) for item in self.audit["review_candidates"]]
        self.assertTrue(any({"r04", "r12"} <= pair for pair in candidate_pairs))

    def test_five_types_are_formatted(self):
        for marker in ("[J]", "[C]//", "[M]", "[D]", "[EB/OL]"):
            self.assertIn(marker, self.references)

    def test_numbering_has_no_holes(self):
        self.assertEqual([line.split("]", 1)[0] for line in self.lines], [f"[{n}" for n in range(1, 16)])

    def test_four_authors_are_truncated_without_fabricating_names(self):
        self.assertIn("张研, 李文, 陈林, 等.", self.references)
        self.assertNotIn("赵澄", self.references)
        self.assertEqual(self.by_source("r01")["authors"][:3], ["王泽昊", "朱振华", "谢童欣"])

    def test_unicode_space_digits_and_page_range(self):
        self.assertIn("黄禾. 面向长文本的 检索评估方法[J]. 示例信息技术学报, 2025, 9(2): 107-118.", self.references)
        self.assertNotIn("–", self.references)
        self.assertNotIn("—", self.references)

    def test_rerun_is_deterministic(self):
        second = self.work / "second-output"
        result = subprocess.run([sys.executable, str(SCRIPT), "--input", str(FIXTURE), "--outdir", str(second)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("references.txt", "drafts.txt", "normalized.json", "audit.json"):
            self.assertEqual((second / name).read_bytes(), (self.output / name).read_bytes(), name)

    def test_normalized_round_trip_is_idempotent(self):
        result, outdir = self.run_input("round-trip", {"records": self.normalized})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((outdir / "references.txt").read_text(encoding="utf-8"), self.references)

    def test_uppercase_author_option(self):
        source = json.loads(FIXTURE.read_text(encoding="utf-8"))["records"][1]
        result, outdir = self.run_input("uppercase", [source], "--author-case", "upper")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SUN Q, WANG H, ZHAN J, et al.", (outdir / "references.txt").read_text(encoding="utf-8"))

    def test_empty_record_list_has_zero_counts(self):
        result, outdir = self.run_input("empty", [])
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads((outdir / "audit.json").read_text(encoding="utf-8"))["summary"]
        self.assertEqual(summary["input_count"], 0)
        self.assertEqual((outdir / "references.txt").read_text(encoding="utf-8").strip(), "")

    def test_invalid_json_is_reported_without_traceback(self):
        bad = self.work / "invalid.json"
        bad.write_text('{"records": [}', encoding="utf-8")
        result = subprocess.run([sys.executable, str(SCRIPT), "--input", str(bad), "--outdir", str(self.work / "invalid")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_wrong_top_level_structure_is_rejected(self):
        result, _ = self.run_input("wrong-structure", {"data": "not a record list"})
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
