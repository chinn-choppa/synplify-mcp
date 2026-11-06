"""Нативная интеграция нового .srr-инструмента с MCP SDK, без EDA."""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from mcp import Client, StdioServerParameters
except ImportError:
    Client = None
    StdioServerParameters = None

from synplify_mcp.srr import read_srr_report


@unittest.skipUnless(Client is not None, "Requires installed official MCP SDK")
class SrrProtocolTests(unittest.TestCase):
    def test_in_memory_mcp_call(self) -> None:
        from synplify_mcp.server import create_server

        async def check() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "synthetic.srr"
                path.write_text("@W: DEMO001 : rtl/x.sv(5): Inferred latch\n",
                                encoding="utf-8")
                Path(tmp, "metrics.srr").write_text(
                    "Synplify Pro Version: MOCK\n"
                    "Resource Usage Report\nTotal LUTs: 4\n"
                    "START TIMING REPORT\nPerformance Summary\n"
                    "Clock Requested Period (ns) Estimated Period (ns) Slack (ns)\n"
                    "clk_mcp 10.0 11.0 -1.0\nEND TIMING REPORT\n",
                    encoding="utf-8",
                )
                with patch.dict(os.environ, {"SYNPLIFY_MCP_WORKSPACE": tmp,
                                          "SYNPLIFY_MCP_ENABLE_SYNTHESIS": "0"}):
                    async with Client(create_server()) as client:
                        page = await client.list_tools()
                        self.assertIn("parse_srr", {t.name for t in page.tools})
                        self.assertIn("run_approved_synthesis", {t.name for t in page.tools})
                        operation = next(t for t in page.tools
                                         if t.name == "run_approved_synthesis")
                        self.assertIsNotNone(operation.annotations)
                        self.assertFalse(operation.annotations.read_only_hint)
                        self.assertTrue(operation.annotations.destructive_hint)
                        refused = await client.call_tool(
                            "run_approved_synthesis",
                            {"project_id": "demo", "acknowledge_side_effects": True}
                        )
                        self.assertFalse(refused.is_error)
                        self.assertEqual(refused.structured_content["state"], "DISABLED")
                        self.assertFalse(refused.structured_content["executed"])
                        result = await client.call_tool("parse_srr",
                                                        {"relative_path": "synthetic.srr"})
                        self.assertFalse(result.is_error)
                        self.assertEqual(result.structured_content["state"], "PARSED")
                        self.assertEqual(result.structured_content["diagnostic_count"], 1)
                        self.assertEqual(result.structured_content["synthesis_status"], "UNKNOWN")
                        metrics = await client.call_tool(
                            "parse_srr", {"relative_path": "metrics.srr"}
                        )
                        self.assertFalse(metrics.is_error)
                        payload = metrics.structured_content
                        self.assertEqual(payload["tool_version"], "MOCK")
                        self.assertEqual(payload["resources"]["state"], "PARSED")
                        self.assertEqual(payload["resources"]["items"][0]["used"]["value"], 4)
                        self.assertEqual(payload["timing"]["kind"], "SYNTHESIS_ESTIMATE")
                        self.assertEqual(payload["timing"]["state"], "PARSED")
                        self.assertEqual(payload["timing"]["clocks"][0]["clock"], "clk_mcp")
                        self.assertEqual(payload["timing"]["clocks"][0]["slack"]["unit"], "ns")
                        self.assertEqual(payload["synthesis_status"], "UNKNOWN")
                        denied = await client.call_tool("parse_srr",
                                                       {"relative_path": "../secret.srr"})
                        self.assertFalse(denied.is_error)
                        self.assertEqual(denied.structured_content["state"], "ERROR")
                        self.assertEqual(denied.structured_content["error_code"], "INVALID_PATH")
        asyncio.run(asyncio.wait_for(check(), timeout=25))

    def test_real_stdio_mcp_call(self) -> None:
        async def check() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                Path(tmp, "sample.srr").write_text(
                    "Compiler Report\n@E: DEMO009 : rtl/test.sv(2): example\n", encoding="utf-8"
                )
                env = dict(os.environ, SYNPLIFY_MCP_WORKSPACE=tmp,
                           SYNPLIFY_MCP_ENABLE_SYNTHESIS="0")
                params = StdioServerParameters(
                    command=sys.executable, args=["-m", "synplify_mcp"], env=env
                )
                async with Client(params) as client:
                    page = await client.list_tools()
                    self.assertIn("parse_srr", {t.name for t in page.tools})
                    self.assertIn("run_approved_synthesis", {t.name for t in page.tools})
                    operation = next(t for t in page.tools
                                     if t.name == "run_approved_synthesis")
                    self.assertIsNotNone(operation.annotations)
                    self.assertFalse(operation.annotations.read_only_hint)
                    self.assertTrue(operation.annotations.destructive_hint)
                    refusal = await client.call_tool(
                        "run_approved_synthesis",
                        {"project_id": "demo", "acknowledge_side_effects": True}
                    )
                    self.assertFalse(refusal.is_error)
                    self.assertEqual(refusal.structured_content["state"], "DISABLED")
                    self.assertFalse(refusal.structured_content["executed"])
                    result = await client.call_tool(
                        "parse_srr", {"relative_path": "sample.srr"}
                    )
                    self.assertFalse(result.is_error)
                    self.assertEqual(result.structured_content["diagnostic_count"], 1)
                    self.assertEqual(result.structured_content["diagnostics"][0]["code"],
                                     "DEMO009")
        asyncio.run(asyncio.wait_for(check(), timeout=25))


if __name__ == "__main__":
    unittest.main()
