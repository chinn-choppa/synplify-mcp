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
                with patch.dict(os.environ, {"SYNPLIFY_MCP_WORKSPACE": tmp}):
                    async with Client(create_server()) as client:
                        page = await client.list_tools()
                        self.assertIn("parse_srr", {t.name for t in page.tools})
                        result = await client.call_tool("parse_srr",
                                                        {"relative_path": "synthetic.srr"})
                        self.assertFalse(result.is_error)
                        self.assertEqual(result.structured_content["state"], "PARSED")
                        self.assertEqual(result.structured_content["diagnostic_count"], 1)
                        self.assertEqual(result.structured_content["synthesis_status"], "UNKNOWN")
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
                env = dict(os.environ, SYNPLIFY_MCP_WORKSPACE=tmp)
                params = StdioServerParameters(
                    command=sys.executable, args=["-m", "synplify_mcp"], env=env
                )
                async with Client(params) as client:
                    page = await client.list_tools()
                    self.assertIn("parse_srr", {t.name for t in page.tools})
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
