"""Публичные тесты .srr без Synplify Pro и без лицензии."""

from __future__ import annotations

import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from synplify_mcp.srr import MAX_REPORT_BYTES, parse_srr_bytes, read_srr_report

FIXTURES = Path(__file__).parent / "fixtures" / "srr"


class ParseSrrTests(unittest.TestCase):
    def test_basic_with_exact_positions(self) -> None:
        data = (FIXTURES / "basic.srr").read_bytes()
        result = parse_srr_bytes(data, source_path="basic.srr")
        self.assertEqual(result["state"], "PARSED")
        self.assertEqual(result["parse_health"], "PARSED")
        self.assertEqual(result["diagnostic_count"], 2)
        self.assertEqual(result["report_sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(result["synthesis_status"], "UNKNOWN")
        self.assertFalse(result["executed"])
        first, second = result["diagnostics"]
        self.assertEqual((first["severity"], first["file"], first["line"]),
                         ("warning", "rtl/top.sv", 14))
        self.assertEqual((first["report_line"], first["section"]), (3, "COMPILER_REPORT"))
        self.assertEqual(first["byte_offset"], data.find(b"@W:"))
        self.assertEqual(second["byte_offset"], data.find(b"@E:"))
        self.assertEqual(second["severity"], "error")
        self.assertIsNone(result["tool_version"])
        self.assertEqual(result["resources"]["state"], "NOT_EXTRACTED")
        self.assertEqual(result["timing"]["kind"], "SYNTHESIS_ESTIMATE")

    def test_sectioned_variation_and_categories(self) -> None:
        r = parse_srr_bytes((FIXTURES / "sections.srr").read_bytes())
        self.assertEqual(r["diagnostic_count"], 4)
        self.assertEqual([x["severity"] for x in r["diagnostics"]],
                         ["note", "warning", "warning", "info"])
        self.assertEqual([x["code"] for x in r["diagnostics"]],
                         ["DEMO010", "DEMO120", "DEMO121", "DEMO130"])
        self.assertEqual(r["diagnostics"][1]["category"], "INFERRED_LATCH")
        self.assertEqual(r["diagnostics"][2]["category"], "BLACK_BOX")
        self.assertIn("TIMING", [x["name"] for x in r["sections"]])
        self.assertIn("RESOURCE_USAGE", [x["name"] for x in r["sections"]])
        self.assertEqual(r["synthesis_status"], "UNKNOWN")

    def test_windows_crlf_offsets(self) -> None:
        data = (FIXTURES / "windows.srr").read_bytes()
        result = parse_srr_bytes(data)
        self.assertEqual(result["diagnostic_count"], 1)
        found = result["diagnostics"][0]
        self.assertEqual(found["report_line"], 3)
        self.assertEqual(found["byte_offset"], data.find(b"@W:"))
        self.assertEqual(found["file"], r"C:\design space\rtl\top.sv")
        self.assertEqual(found["line"], 42)
        self.assertEqual(found["code"], "DEMO210")
        self.assertTrue(found["raw"].startswith("@W:"))

    def test_empty_unrecognized_and_incomplete(self) -> None:
        self.assertEqual(parse_srr_bytes(b"")["parse_health"], "EMPTY")
        unknown = parse_srr_bytes((FIXTURES / "unrecognized.srr").read_bytes())
        self.assertEqual(unknown["parse_health"], "UNRECOGNIZED")
        self.assertEqual(unknown["synthesis_status"], "UNKNOWN")
        incomplete = parse_srr_bytes((FIXTURES / "truncated.srr").read_bytes())
        self.assertEqual(incomplete["diagnostic_count"], 1)
        self.assertEqual(incomplete["synthesis_status"], "UNKNOWN")
        self.assertIsNone(incomplete["tool_version"])

    def test_unknown_marker_partial_without_fabrication(self) -> None:
        result = parse_srr_bytes(b"@Q: unknown code\n@W: example\n")
        self.assertEqual(result["unrecognized_markers"], 1)
        self.assertEqual(result["parse_health"], "PARTIAL")
        self.assertEqual(result["diagnostic_count"], 1)

    def test_utf8_bom_and_utf16_bom_offsets(self) -> None:
        content = "@E: rtl/a.sv(5): bad\n"
        for encoded, expected, bom in [
            (b"\xef\xbb\xbf" + content.encode(), "utf-8", 3),
            (b"\xff\xfe" + content.encode("utf-16-le"), "utf-16-le", 2),
            (b"\xfe\xff" + content.encode("utf-16-be"), "utf-16-be", 2),
        ]:
            with self.subTest(encoding=expected):
                r = parse_srr_bytes(encoded)
                self.assertEqual(r["encoding"], expected)
                self.assertEqual(r["diagnostics"][0]["byte_offset"], bom)
                self.assertEqual(r["diagnostics"][0]["line"], 5)

    def test_legacy_encoding_is_opt_in(self) -> None:
        encoded = b"@W: new caf\xe9 warning\n"
        self.assertEqual(parse_srr_bytes(encoded)["error_code"], "DECODE_ERROR")
        r = parse_srr_bytes(encoded, encoding="cp1252")
        self.assertEqual(r["diagnostics"][0]["message"], "new café warning")
        self.assertEqual(r["encoding"], "cp1252")

    def test_malformed_bytes_and_encoding_conflict(self) -> None:
        self.assertEqual(parse_srr_bytes(b"\xff")["error_code"], "DECODE_ERROR")
        self.assertEqual(parse_srr_bytes(b"abc\x00def")["error_code"],
                         "BINARY_OR_UNSUPPORTED_ENCODING")
        self.assertEqual(parse_srr_bytes(b"\xff\xfe" + b"A\x00", encoding="utf-8")["error_code"],
                         "ENCODING_CONFLICT")
        self.assertEqual(parse_srr_bytes(b"x", encoding="latin1")["error_code"],
                         "UNSUPPORTED_ENCODING")

    def test_bounds_and_truncation(self) -> None:
        self.assertEqual(parse_srr_bytes(b"x" * (MAX_REPORT_BYTES + 1))["error_code"], "TOO_LARGE")
        self.assertEqual(parse_srr_bytes("wrong")["error_code"], "INVALID_BYTES")
        for limit in (0, -1, 201, True, 2.5):
            self.assertEqual(parse_srr_bytes(b"", limit=limit)["error_code"], "INVALID_LIMIT")
        data = b"@W: hello\n" * 250
        result = parse_srr_bytes(data, limit=3)
        self.assertEqual(result["diagnostic_count"], 250)
        self.assertEqual(len(result["diagnostics"]), 3)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["parse_health"], "PARTIAL")
        self.assertEqual(parse_srr_bytes(b"\n" * 20_001)["error_code"], "TOO_MANY_LINES")

    def test_oversized_line_is_not_returned(self) -> None:
        r = parse_srr_bytes(b"@W: " + b"x" * 4_100 + b"\n@E: known\n")
        self.assertEqual(r["oversized_lines"], 1)
        self.assertTrue(r["truncated"])
        self.assertEqual(r["diagnostic_count"], 1)
        self.assertEqual(r["parse_health"], "PARTIAL")

    def test_diagnostics_have_no_claimed_run_success(self) -> None:
        for name in ("basic.srr", "sections.srr", "truncated.srr"):
            r = parse_srr_bytes((FIXTURES / name).read_bytes())
            self.assertEqual(r["synthesis_status"], "UNKNOWN")
            self.assertNotIn("PASS", r.values())


class ReadSrrTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "workspace"
        self.root.mkdir()
        (self.root / "reports").mkdir()
        (self.root / "reports" / "sample.srr").write_bytes(
            (FIXTURES / "sections.srr").read_bytes()
        )

    def run_reader(self, relative_path: str) -> dict[str, object]:
        with patch.dict(os.environ, {"SYNPLIFY_MCP_WORKSPACE": str(self.root)}):
            return read_srr_report(relative_path)

    def test_allowed_nested_path(self) -> None:
        r = self.run_reader("reports/sample.srr")
        self.assertEqual(r["state"], "PARSED")
        self.assertEqual(r["source_path"], "reports/sample.srr")
        self.assertNotIn(str(self.root), str(r))

    def test_workspace_required_and_absolute(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(read_srr_report("reports/sample.srr")["error_code"],
                             "WORKSPACE_NOT_CONFIGURED")
        with patch.dict(os.environ, {"SYNPLIFY_MCP_WORKSPACE": "relative"}):
            self.assertEqual(read_srr_report("reports/sample.srr")["error_code"],
                             "INVALID_WORKSPACE")

    def test_paths_denied(self) -> None:
        for value in ("../outside.srr", "../../outside.srr", "/etc/secret.srr",
                      r"C:\windows\secret.srr", r"..\secret.srr",
                      "not-report.txt", "", ".", "reports/../../outside.srr"):
            with self.subTest(path=value):
                r = self.run_reader(value)
                self.assertEqual(r["state"], "ERROR")
                self.assertEqual(r["error_code"], "INVALID_PATH")
        self.assertEqual(self.run_reader("reports/missing.srr")["error_code"], "NOT_FOUND")

    def test_symlink_escape(self) -> None:
        outside = Path(self.tmp.name) / "secret.srr"
        outside.write_text("@E: should not be read\n", encoding="utf-8")
        link = self.root / "reports" / "link.srr"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks are unavailable on this runner")
        self.assertEqual(self.run_reader("reports/link.srr")["error_code"], "SYMLINK_DENIED")

    def test_symlink_parent(self) -> None:
        outside = Path(self.tmp.name) / "external"
        outside.mkdir()
        (outside / "secret.srr").write_text("@W: secret\n", encoding="utf-8")
        link = self.root / "alias"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Directory symlinks are unavailable on this runner")
        self.assertEqual(self.run_reader("alias/secret.srr")["error_code"], "SYMLINK_DENIED")

    def test_oversized_file(self) -> None:
        (self.root / "too_big.srr").write_bytes(b"x" * (MAX_REPORT_BYTES + 1))
        self.assertEqual(self.run_reader("too_big.srr")["error_code"], "TOO_LARGE")

    def test_malformed_file_and_permissions(self) -> None:
        (self.root / "bad.srr").write_bytes(b"\xff\xfe\x00")
        self.assertEqual(self.run_reader("bad.srr")["error_code"], "DECODE_ERROR")

    def test_false_success_is_never_reported(self) -> None:
        (self.root / "unknown.srr").write_text("unrecognized\n", encoding="utf-8")
        r = self.run_reader("unknown.srr")
        self.assertEqual(r["parse_health"], "UNRECOGNIZED")
        self.assertEqual(r["synthesis_status"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
