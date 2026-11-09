"""Сравнение синтетических отчетов: безопасные и воспроизводимые тесты."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from synplify_mcp.compare import compare_srr

FIXTURES = Path(__file__).parent / "fixtures" / "srr"


class CompareTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ("compare_base.srr", "compare_changed.srr", "metrics_unknown.srr"):
            (self.root / name).write_bytes((FIXTURES / name).read_bytes())
        env = patch.dict(os.environ, {"SYNPLIFY_MCP_WORKSPACE": self.tmp.name})
        env.start()
        self.addCleanup(env.stop)

    def compare(self, baseline="compare_base.srr", candidate="compare_changed.srr"):
        return compare_srr(baseline, candidate)

    def test_comparable_resources_diagnostics_and_unverified_timing(self):
        r = self.compare()
        self.assertEqual(r["state"], "MATCHED")
        self.assertEqual(r["context"]["state"], "MATCHED")
        self.assertEqual(r["baseline"]["tool_version"], "MOCK-CMP-1")
        self.assertEqual(r["candidate"]["device"], "DEMO-CMP")
        self.assertNotEqual(r["baseline"]["report_sha256"], r["candidate"]["report_sha256"])
        self.assertEqual(r["synthesis_status"], "UNKNOWN")
        self.assertFalse(r["executed"])
        d = r["diagnostics"]
        self.assertEqual(d["state"], "COMPLETE_OBSERVATION")
        self.assertEqual(d["observed_change_count"], 2)
        self.assertEqual({x["change"] for x in d["changes"]}, {"REMOVED", "ADDED"})
        self.assertEqual({x["code"] for x in d["changes"]}, {"DEMO221", "DEMO222"})
        self.assertTrue(all(x["evidence"] for x in d["changes"]))
        q = r["resources"]
        self.assertEqual(q["state"], "COMPARABLE")
        self.assertEqual(q["change_count"], 2)
        by_name = {x["resource"]: x for x in q["changes"]}
        self.assertEqual(by_name["total luts"]["delta"], 4)
        self.assertEqual(by_name["register bits not including i/os"]["delta"], -1)
        self.assertEqual(by_name["total luts"]["unit"], "count")
        self.assertEqual(by_name["total luts"]["baseline_evidence"]["raw"], "Total LUTs: 10")
        self.assertEqual(by_name["total luts"]["candidate_evidence"]["raw"], "Total LUTs: 14")
        self.assertIsInstance(by_name["total luts"]["candidate_evidence"]["byte_offset"], int)
        t = r["timing"]
        self.assertEqual(t["state"], "UNVERIFIED_FULL_CONSTRAINTS")
        self.assertTrue(t["clock_request_match"])
        self.assertEqual({x["clock"] for x in t["observed_changes"]}, {"core", "aux"})
        self.assertTrue(all(x["slack_delta"] is None for x in t["observed_changes"]))
        self.assertTrue(all(x["estimated_delta"] is None for x in t["observed_changes"]))
        self.assertFalse(t["numeric_deltas_permitted"])
        self.assertFalse(t["implementation_timing"])
        self.assertFalse(r["post_route_timing"])

    def test_determinism_and_reverse(self):
        original = self.compare()
        self.assertEqual(original, self.compare())
        back = self.compare("compare_changed.srr", "compare_base.srr")
        self.assertEqual(next(x for x in back["resources"]["changes"]
                              if x["resource"] == "total luts")["delta"], -4)

    def test_same_bytes_not_synthesis_success(self):
        r = self.compare("compare_base.srr", "compare_base.srr")
        self.assertEqual(r["state"], "IDENTICAL_BYTES")
        self.assertEqual(r["diagnostics"]["observed_change_count"], 0)
        self.assertEqual(r["resources"]["changes"], [])
        self.assertEqual(r["timing"]["observed_changes"], [])
        self.assertEqual(r["synthesis_status"], "UNKNOWN")

    def test_incompatible_device_version_and_unknown(self):
        txt = (self.root / "compare_changed.srr").read_text(encoding="utf-8")
        (self.root / "other.srr").write_text(
            txt.replace("MOCK-CMP-1", "MOCK-CMP-2").replace("DEMO-CMP", "DEMO-OTHER"),
            encoding="utf-8")
        r = self.compare(candidate="other.srr")
        self.assertEqual(r["state"], "INCOMPATIBLE")
        self.assertEqual(r["resources"]["state"], "BLOCKED_CONTEXT")
        self.assertEqual(r["timing"]["state"], "BLOCKED_CONTEXT")
        self.assertEqual(r["resources"]["changes"], [])
        self.assertEqual(r["diagnostics"]["state"], "COMPLETE_OBSERVATION")
        self.assertEqual(self.compare(candidate="metrics_unknown.srr")["state"],
                         "UNVERIFIED")

    def test_constraint_clock_and_resource_mismatches(self):
        txt = (self.root / "compare_changed.srr").read_text(encoding="utf-8")
        variants = {
            "request.srr": txt.replace("core 10.0", "core 9.0"),
            "clock.srr": txt.replace("aux 20.0", "new_clock 20.0"),
            "duplicate.srr": txt.replace("Total LUTs: 14",
                                         "Total LUTs: 14\nTotal LUTs: 15"),
            "extra.srr": txt.replace("Register bits not including I/Os: 5",
                                     "Register bits not including I/Os: 5\nI/O ports: 2"),
        }
        for filename, value in variants.items():
            (self.root / filename).write_text(value, encoding="utf-8")
        self.assertEqual(self.compare(candidate="request.srr")["timing"]["state"],
                         "INCOMPATIBLE_CLOCK_REQUESTS")
        self.assertEqual(self.compare(candidate="clock.srr")["timing"]["state"],
                         "INCOMPATIBLE_CLOCK_SET")
        self.assertEqual(self.compare(candidate="duplicate.srr")["resources"]["state"],
                         "UNVERIFIED_DATA")
        extra = self.compare("compare_changed.srr", "extra.srr")["resources"]
        self.assertEqual(extra["state"], "PARTIAL")
        self.assertIsNone(next(x for x in extra["changes"] if x["resource"] == "i/o ports")["delta"])

    def test_capacity_mismatch_blocks_delta(self):
        txt = (self.root / "compare_base.srr").read_text(encoding="utf-8")
        (self.root / "cap_a.srr").write_text(
            txt.replace("Total LUTs: 10", "Resource Used Available\nSB_LUT4 10 100"),
            encoding="utf-8")
        (self.root / "cap_b.srr").write_text(
            txt.replace("Total LUTs: 10", "Resource Used Available\nSB_LUT4 11 200"),
            encoding="utf-8")
        q = self.compare("cap_a.srr", "cap_b.srr")["resources"]
        self.assertEqual(q["state"], "PARTIAL")
        self.assertIn("sb_lut4", q["incompatible_resources"])
        self.assertIsNone(next(x for x in q["changes"] if x["resource"] == "sb_lut4")["delta"])

    def test_truncated_resource_section_blocks_numerical_delta(self):
        before = (self.root / "compare_base.srr").read_text(encoding="utf-8")
        after = (self.root / "compare_changed.srr").read_text(encoding="utf-8")
        (self.root / "cut_base.srr").write_text(
            before.split("Register bits not including I/Os:")[0], encoding="utf-8"
        )
        (self.root / "cut_candidate.srr").write_text(
            after.split("Register bits not including I/Os:")[0], encoding="utf-8"
        )
        r = self.compare("cut_base.srr", "cut_candidate.srr")
        self.assertEqual(r["context"]["state"], "MATCHED")
        self.assertEqual(r["resources"]["state"], "UNVERIFIED_DATA")
        self.assertEqual(r["resources"]["changes"], [])

    def test_common_128_character_prefix_does_not_verify_context(self):
        before = (self.root / "compare_base.srr").read_text(encoding="utf-8")
        after = (self.root / "compare_changed.srr").read_text(encoding="utf-8")
        (self.root / "long_base.srr").write_text(
            before.replace("MOCK-CMP-1", "A" * 128 + "X"), encoding="utf-8"
        )
        (self.root / "long_candidate.srr").write_text(
            after.replace("MOCK-CMP-1", "A" * 128 + "Y"), encoding="utf-8"
        )
        r = self.compare("long_base.srr", "long_candidate.srr")
        self.assertEqual(r["context"]["state"], "UNVERIFIED")
        self.assertEqual(r["resources"]["state"], "BLOCKED_CONTEXT")

    def test_invalid_and_malformed_path(self):
        for value in ("../secret.srr", "/etc/secret.srr", r"C:\secret.srr"):
            with self.subTest(path=value):
                r = self.compare(candidate=value)
                self.assertEqual(r["state"], "INPUT_ERROR")
                self.assertEqual(r["error_code"], "INVALID_PATH")
                self.assertEqual(r["side"], "candidate")
        self.assertEqual(self.compare("../secret.srr")["side"], "baseline")
        (self.root / "bad.srr").write_bytes(b"\xff")
        self.assertEqual(self.compare(candidate="bad.srr")["error_code"], "DECODE_ERROR")

    def test_incomplete_warning_list_not_claimed_complete(self):
        txt = (self.root / "compare_base.srr").read_text(encoding="utf-8")
        (self.root / "large.srr").write_text(
            txt + ("\n@W: synthetic repeated\n" * 250), encoding="utf-8")
        d = self.compare(candidate="large.srr")["diagnostics"]
        self.assertEqual(d["state"], "PARTIAL_OBSERVATION")
        self.assertLessEqual(len(d["changes"]), 16)

    def test_unconstrained_clock_prevents_timing_delta(self):
        txt = (self.root / "compare_changed.srr").read_text(encoding="utf-8")
        (self.root / "unconstrained.srr").write_text(
            txt.replace("core 10.0", "core Unconstrained"), encoding="utf-8")
        t = self.compare(candidate="unconstrained.srr")["timing"]
        self.assertEqual(t["state"], "UNVERIFIED_DATA")


if __name__ == "__main__":
    unittest.main()
