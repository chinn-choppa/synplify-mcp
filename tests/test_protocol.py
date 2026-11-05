"""MCP SDK v2 protocol acceptance without commercial EDA."""

from __future__ import annotations

import asyncio
import os
import sys
import unittest

from mcp import Client, StdioServerParameters
from synplify_mcp.server import create_server

EXPECTED_TOOLS = {"server_info", "tool_status", "parse_diagnostics"}


class ProtocolTests(unittest.TestCase):
    def test_in_memory_mcp_exchange(self) -> None:
        async def check() -> None:
            async with Client(create_server()) as client:
                tools = await client.list_tools()
                self.assertEqual({tool.name for tool in tools}, EXPECTED_TOOLS)
                response = await client.call_tool("server_info", {})
                self.assertFalse(response.is_error)
                self.assertEqual(response.structured_content["server"], "synplify-mcp")
                parsed = await client.call_tool(
                    "parse_diagnostics", {"text": "@W: rtl/top.sv(14): Width mismatch"}
                )
                self.assertFalse(parsed.is_error)
                self.assertEqual(parsed.structured_content["count"], 1)
                invalid = await client.call_tool("parse_diagnostics", {"text": "", "limit": 0})
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
                tools = await client.list_tools()
                self.assertEqual({tool.name for tool in tools}, EXPECTED_TOOLS)
                response = await client.call_tool("server_info", {})
                self.assertFalse(response.is_error)
                self.assertEqual(response.structured_content["stage"], "bootstrap")

        asyncio.run(asyncio.wait_for(check(), timeout=25))


if __name__ == "__main__":
    unittest.main()
