"""MCP SDK v2 protocol acceptance without commercial EDA."""

from __future__ import annotations

import asyncio
import os
import sys
import unittest

from mcp import Client, StdioServerParameters
from fastmcp import Client as FastMCPClient
from synplify_mcp.server import create_server

EXPECTED_TOOLS = {"server_info", "tool_status", "parse_diagnostics",
                  "parse_srr", "compare_srr_reports", "run_approved_synthesis"}


class ProtocolTests(unittest.TestCase):
    def test_in_memory_mcp_exchange(self) -> None:
        async def check() -> None:
            async with FastMCPClient(create_server()) as client:
                page = await client.list_tools_mcp()
                self.assertIsNone(page.next_cursor)
                self.assertEqual({tool.name for tool in page.tools}, EXPECTED_TOOLS)
                annotations = {tool.name: tool.annotations for tool in page.tools}
                for name in EXPECTED_TOOLS - {"run_approved_synthesis"}:
                    self.assertIsNotNone(annotations[name])
                    self.assertTrue(annotations[name].read_only_hint, name)
                    self.assertFalse(annotations[name].open_world_hint, name)
                runner = annotations["run_approved_synthesis"]
                self.assertFalse(runner.read_only_hint)
                self.assertTrue(runner.destructive_hint)
                self.assertFalse(runner.open_world_hint)
                response = await client.call_tool_mcp("server_info", {})
                self.assertFalse(response.is_error)
                self.assertEqual(response.structured_content["server"], "synplify-mcp")
                self.assertTrue(response.structured_content["eda_execution_supported"])
                self.assertFalse(response.structured_content["eda_execution_validated"])
                parsed = await client.call_tool_mcp(
                    "parse_diagnostics", {"text": "@W: rtl/top.sv(14): Width mismatch"}
                )
                self.assertFalse(parsed.is_error)
                self.assertEqual(parsed.structured_content["count"], 1)
                invalid = await client.call_tool_mcp("parse_diagnostics", {"text": "", "limit": 0})
                self.assertTrue(invalid.is_error)
                self.assertIsNone(invalid.structured_content)

        asyncio.run(asyncio.wait_for(check(), timeout=25))

    def test_real_stdio_mcp_exchange(self) -> None:
        async def check() -> None:
            params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "synplify_mcp"],
                env=os.environ.copy(),
            )
            async with Client(params) as client:
                page = await client.list_tools()
                self.assertIsNone(page.next_cursor)
                self.assertEqual({tool.name for tool in page.tools}, EXPECTED_TOOLS)
                response = await client.call_tool("server_info", {})
                self.assertFalse(response.is_error)
                self.assertEqual(response.structured_content["stage"], "experimental")

        asyncio.run(asyncio.wait_for(check(), timeout=25))


if __name__ == "__main__":
    unittest.main()
