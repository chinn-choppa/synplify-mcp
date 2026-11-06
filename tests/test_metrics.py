"""Ограниченная нормализация ресурсов/timing — только искусственные отчёты."""

from __future__ import annotations

import unittest
from pathlib import Path

from synplify_mcp.srr import parse_srr_bytes

FIXTURES = Path(__file__).parent / "fixtures" / "srr"


def parse(name: str) -> dict[str, object]:
    return parse_srr_bytes((FIXTURES / name).read_bytes())


class ReportMetricsTests(unittest.TestCase):
    def test_labeled_resources_with_explicit_units(self) -> None:
        result = parse("metrics_frequency.srr")
        self.assertEqual(result["resources"]["state"], "PARSED")
        self.assertEqual(result["resources"]["scope"], "SYNTHESIS_MAPPING")
        items = result["resources"]["items"]
        self.assertEqual([x["name"] for x in items],
                         ["Total LUTs", "Register bits not including I/Os", "I/O ports"])
        self.assertEqual([x["used"]["value"] for x in items], [1024, 512, 3])
        self.assertEqual({x["used"]["unit"] for x in items}, {"count"})
        self.assertTrue(all(x["available"]["value"] is None for x in items))
        self.assertTrue(all(x["available"]["state"] == "UNKNOWN" for x in items))
        self.assertEqual(items[0]["evidence"]["report_line"], 5)
        self.assertEqual(items[0]["evidence"]["raw"], "Total LUTs: 1,024")
        self.assertEqual(result["synthesis_status"], "UNKNOWN")

    def test_table_resources_do_not_alias_primitive_names(self) -> None:
        result = parse("metrics_period.srr")
        items = result["resources"]["items"]
        self.assertEqual(result["resources"]["state"], "PARSED")
        self.assertEqual([x["key"] for x in items], ["sb_ram40_4k", "sb_lut4"])
        self.assertEqual([x["used"]["value"] for x in items], [2, 35])
        self.assertEqual([x["available"]["value"] for x in items], [8, 128])
        self.assertEqual(items[0]["evidence"]["section"], "RESOURCE_USAGE")
        self.assertEqual(result["device"], "DEMO-FPGA-B")
        self.assertEqual(result["context"]["device"]["state"], "KNOWN")

    def test_two_frequency_clocks_and_header_provenance(self) -> None:
        result = parse("metrics_frequency.srr")
        timing = result["timing"]
        self.assertEqual(timing["state"], "PARSED")
        self.assertEqual(timing["kind"], "SYNTHESIS_ESTIMATE")
        self.assertFalse(timing["implementation_timing"])
        self.assertEqual([x["clock"] for x in timing["clocks"]], ["clk_fast", "clk_slow"])
        clk = timing["clocks"][0]
        self.assertEqual(clk["requested"], {"value": 100.0, "unit": "MHz", "state": "KNOWN"})
        self.assertEqual(clk["estimated"], {"value": 91.0, "unit": "MHz", "state": "KNOWN"})
        self.assertEqual(clk["slack"], {"value": -1.0, "unit": "ns", "state": "KNOWN"})
        self.assertEqual(clk["constraints"], "CONSTRAINED")
        self.assertEqual(clk["header_evidence"]["report_line"], 10)
        self.assertIn("Estimated Frequency (MHz)", clk["header_evidence"]["raw"])
        self.assertEqual(clk["evidence"]["report_line"], 11)
        self.assertEqual(result["tool_version"], "MOCK-OLD-1")
        self.assertEqual(result["context"]["tool_version"]["evidence"][0]["report_line"], 2)

    def test_period_variant_not_automatically_cross_compared(self) -> None:
        result = parse("metrics_period.srr")
        timing = result["timing"]
        self.assertEqual(timing["state"], "PARSED")
        self.assertEqual([c["requested"]["unit"] for c in timing["clocks"]], ["ns", "ns"])
        self.assertEqual([c["estimated"]["value"] for c in timing["clocks"]], [8.5, 14.5])
        self.assertEqual(timing["clocks"][1]["slack"]["value"], 1.5)
        self.assertNotIn("fmax", str(timing).lower())
        self.assertNotIn("PASS", str(result["synthesis_status"]))

    def test_missing_values_are_unknown_and_unconstrained_explicit(self) -> None:
        result = parse("metrics_unknown.srr")
        self.assertEqual(result["resources"]["state"], "PARTIAL")
        self.assertEqual(result["resources"]["items"][0]["used"]["state"], "UNKNOWN")
        self.assertIsNone(result["resources"]["items"][0]["used"]["value"])
        self.assertEqual(result["timing"]["state"], "PARTIAL")
        a, b = result["timing"]["clocks"]
        self.assertEqual(a["constraints"], "UNCONSTRAINED")
        self.assertEqual(a["requested"]["state"], "UNCONSTRAINED")
        self.assertIsNone(a["slack"]["value"])
        self.assertEqual(b["constraints"], "UNKNOWN")
        self.assertIsNone(b["requested"]["value"])
        self.assertEqual(result["tool_version"], None)
        self.assertEqual(result["context"]["tool_version"]["state"], "UNKNOWN")

    def test_ambiguity_never_picks_a_version_or_one_duplicate_metric(self) -> None:
        result = parse("metrics_ambiguous.srr")
        self.assertIsNone(result["tool_version"])
        self.assertIsNone(result["device"])
        self.assertEqual(result["context"]["tool_version"]["state"], "AMBIGUOUS")
        self.assertEqual(result["context"]["device"]["state"], "AMBIGUOUS")
        self.assertEqual(result["resources"]["state"], "AMBIGUOUS")
        self.assertEqual(result["timing"]["state"], "AMBIGUOUS")
        self.assertIn("DUPLICATE_RESOURCE", result["resources"]["issues"])
        self.assertIn("DUPLICATE_CLOCK", result["timing"]["issues"])

    def test_unknown_units_not_guessed_or_parsed_outside_sections(self) -> None:
        result = parse("metrics_unknown_units.srr")
        self.assertEqual(result["resources"]["state"], "UNSUPPORTED")
        self.assertEqual(result["resources"]["items"], [])
        self.assertEqual(result["timing"]["state"], "UNSUPPORTED")
        self.assertEqual(result["timing"]["clocks"], [])
        self.assertEqual(result["timing"]["kind"], "SYNTHESIS_ESTIMATE")
        self.assertIn("UNSUPPORTED_TIMING_FORMAT", result["timing"]["issues"])

    def test_absence_is_not_zero(self) -> None:
        result = parse("basic.srr")
        self.assertEqual(result["resources"]["state"], "ABSENT")
        self.assertEqual(result["timing"]["state"], "ABSENT")
        self.assertEqual(result["resources"]["items"], [])
        self.assertEqual(result["timing"]["clocks"], [])

    def test_existing_unsupported_timing_table_preserved_as_unknown(self) -> None:
        result = parse("sections.srr")
        self.assertEqual(result["timing"]["state"], "UNSUPPORTED")
        self.assertEqual(result["timing"]["clocks"], [])
        self.assertEqual(result["resources"]["state"], "UNSUPPORTED")

    def test_unterminated_timing_is_partial_without_claim(self) -> None:
        result = parse_srr_bytes(
            b"START TIMING REPORT\nPerformance Summary\n"
            b"Clock Requested Period (ns) Estimated Period (ns) Slack (ns)\n"
            b"clk_main 10.0 11.0 -1.0\n"
        )
        self.assertEqual(result["timing"]["state"], "PARTIAL")
        self.assertIn("TIMING_SECTION_UNTERMINATED", result["timing"]["issues"])
        self.assertEqual(result["synthesis_status"], "UNKNOWN")

    def test_only_whitelisted_resource_names(self) -> None:
        result = parse_srr_bytes(
            b"Resource Usage Report\n"
            b"RandomField: 100\nTotal LUTs: 22\n"
            b"START TIMING REPORT\nPerformance Summary\n"
            b"Clock Requested Period (ps) Estimated Period (ps) Slack (ps)\n"
            b"clk_main 100 110 -10\nEND TIMING REPORT\n"
        )
        self.assertEqual([x["used"]["value"] for x in result["resources"]["items"]], [22])
        self.assertEqual(result["resources"]["state"], "PARTIAL")
        self.assertEqual(result["timing"]["state"], "UNSUPPORTED")


    def test_explicitly_missing_table_capacity_marks_partial(self) -> None:
        r = parse_srr_bytes(
            b"Resource Usage Report\nResource Used Available\n"
            b"SB_LUT4 6 N/A\n"
        )
        self.assertEqual(r["resources"]["state"], "PARTIAL")
        entry = r["resources"]["items"][0]
        self.assertEqual(entry["used"]["value"], 6)
        self.assertIsNone(entry["available"]["value"])
        self.assertTrue(entry["available"]["reported"])

    def test_no_invented_synthesis_success_even_with_positive_slack(self) -> None:
        r = parse("metrics_period.srr")
        self.assertEqual(r["timing"]["clocks"][1]["slack"]["value"], 1.5)
        self.assertEqual(r["synthesis_status"], "UNKNOWN")

    def test_utf16_bom_metric_offsets(self) -> None:
        text = ("Synplify Pro Version: MOCK\n"
                "Resource Usage Report\nTotal LUTs: 7\n")
        data = b"\xff\xfe" + text.encode("utf-16-le")
        result = parse_srr_bytes(data)
        resource = result["resources"]["items"][0]
        expected_offset = 2 + len(
            "Synplify Pro Version: MOCK\nResource Usage Report\n".encode("utf-16-le")
        )
        self.assertEqual(resource["evidence"]["byte_offset"], expected_offset)
        self.assertEqual(resource["used"]["value"], 7)

    def test_large_corpus_is_bounded(self) -> None:
        data = b"Resource Usage Report\nResource Used Available\n" + (b"SB_LUT4 1 100\n" * 1_000)
        result = parse_srr_bytes(data)
        self.assertEqual(len(result["resources"]["items"]), 64)
        self.assertEqual(result["resources"]["state"], "AMBIGUOUS")
        self.assertIn("RESOURCE_LIMIT", result["resources"]["issues"])
        self.assertEqual(result["synthesis_status"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
