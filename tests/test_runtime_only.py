"""Smoke-check production-only dependency set using independent official SDK client."""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import Client, StdioServerParameters

EXPECTED_TOOLS = {
    "server_info", "tool_status", "parse_diagnostics", "parse_srr",
    "compare_srr_reports", "run_approved_synthesis",
}


class RuntimeOnlyTests(unittest.TestCase):
    def test_fastmcp_server_imports_without_dev_client_extra(self) -> None:
        from fastmcp import FastMCP
        from synplify_mcp.server import create_server

        self.assertIsInstance(create_server(), FastMCP)

    def test_official_sdk_stdio_interoperability(self) -> None:
        async def check() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                Path(tmp, "base.srr").write_text(
                    "Compiler Report\\n@W: DEMO001 : top.sv(2): demo warning\\n",
                    encoding="utf-8",
                )
                Path(tmp, "next.srr").write_text(
                    "Compiler Report\\n@E: DEMO002 : top.sv(3): demo error\\n",
                    encoding="utf-8",
                )
                params = StdioServerParameters(
                    command=sys.executable,
                    args=["-m", "synplify_mcp"],
                    env=dict(os.environ, SYNPLIFY_MCP_WORKSPACE=tmp,
                             SYNPLIFY_MCP_ENABLE_SYNTHESIS="0"),
                )
                async with Client(params) as client:
                    listing = await client.list_tools()
                    self.assertEqual({x.name for x in listing.tools}, EXPECTED_TOOLS)
                    info = await client.call_tool("server_info", {})
                    self.assertFalse(info.is_error)
                    self.assertFalse(info.structured_content["eda_execution_enabled"])
                    parse = await client.call_tool(
                        "parse_srr", {"relative_path": "base.srr"},
                    )
                    self.assertFalse(parse.is_error)
                    self.assertEqual(parse.structured_content["state"], "PARSED")
                    comparison = await client.call_tool(
                        "compare_srr_reports",
                        {"baseline_path": "base.srr", "candidate_path": "next.srr"},
                    )
                    self.assertFalse(comparison.is_error)
                    self.assertEqual(comparison.structured_content["state"], "UNVERIFIED")
                    disabled = await client.call_tool(
                        "run_approved_synthesis",
                        {"project_id": "demo", "acknowledge_side_effects": True},
                    )
                    self.assertFalse(disabled.is_error)
                    self.assertEqual(disabled.structured_content["state"], "DISABLED")
                    self.assertFalse(disabled.structured_content["executed"])

        asyncio.run(asyncio.wait_for(check(), timeout=35))


if __name__ == "__main__":
    unittest.main()
