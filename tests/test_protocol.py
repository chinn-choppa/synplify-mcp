"""MCP SDK v2 protocol acceptance without commercial EDA."""

from __future__ import annotations

import asyncio
import os
import sys
import unittest

from mcp import Client, StdioServerParameters
from synplify_mcp.server import create_server

EXPECTED_TOOLS = {"server_info", "tool_status", "parse_diagnostics",
                  "parse_srr", "compare_srr_reports", "run_approved_synthesis"}


class ProtocolTests(unittest.TestCase):
    def test_in_memory_mcp_exchange(self) -> None:
        async def check() -> None:
            async with Client(create_server()) as client:
                page = await client.list_tools()
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
                self.assertTrue(runner.open_world_hint)
                response = await client.call_tool("server_info", {})
                self.assertFalse(response.is_error)
                self.assertEqual(response.structured_content["server"], "synplify-mcp")
                self.assertFalse(response.structured_content["eda_execution_supported"])
                self.assertFalse(response.structured_content["eda_execution_enabled"])
                self.assertFalse(response.structured_content["eda_execution_validated"])
                parsed = await client.call_tool(
                    "parse_diagnostics", {"text": "@W: rtl/top.sv(14): Width mismatch"}
                )
                self.assertFalse(parsed.is_error)
                self.assertEqual(parsed.structured_content["count"], 1)
                invalid = await client.call_tool("parse_diagnostics", {"text": "", "limit": 0})
                self.assertTrue(invalid.is_error)
                self.assertIsNone(invalid.structured_content)

        asyncio.run(asyncio.wait_for(check(), timeout=25))

    def test_enabled_env_cannot_execute_vendor_over_real_mcp_stdio(self) -> None:
        async def check() -> None:
            # This is the public alpha safety boundary: even an MCP client
            # that sends acknowledge=True with ENABLE_SYNTHESIS=1 cannot start
            # vendor Tcl before a reviewed isolation/approval design exists.
            env = dict(os.environ, SYNPLIFY_MCP_ENABLE_SYNTHESIS="1")
            params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "synplify_mcp"],
                env=env,
            )
            async with Client(params) as client:
                info = await client.call_tool("server_info", {})
                self.assertFalse(info.is_error)
                self.assertTrue(info.structured_content["eda_execution_configured"])
                self.assertFalse(info.structured_content["eda_execution_supported"])
                self.assertFalse(info.structured_content["eda_execution_enabled"])
                outcome = await client.call_tool(
                    "run_approved_synthesis",
                    {"project_id": "demo", "acknowledge_side_effects": True},
                )
                self.assertFalse(outcome.is_error)
                self.assertEqual(
                    outcome.structured_content["state"],
                    "VENDOR_EXECUTION_NOT_VALIDATED",
                )
                self.assertFalse(outcome.structured_content["executed"])

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
