"""Isolated, side-effect-free probes of FastMCP-only conveniences.

These tests are not production server behavior, EDA execution or a proposal
to enable an aggregated HTTP service.
"""

from __future__ import annotations

import asyncio
import unittest

from fastmcp import Client, FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext


class CountingMiddleware(Middleware):
    """Collect only counts; do not log private tool arguments or results."""

    def __init__(self) -> None:
        super().__init__()
        self.tool_calls = 0

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        self.tool_calls += 1
        return await call_next(context)


class FastMCPCapabilitiesTests(unittest.TestCase):
    def test_namespaced_eda_server_composition(self) -> None:
        async def check() -> None:
            synplify = FastMCP("Synthetic Synplify")
            verilator = FastMCP("Synthetic Verilator")

            @synplify.tool
            def tool_status() -> dict[str, str]:
                return {"vendor": "synplify", "state": "SYNTHETIC"}

            @verilator.tool
            def tool_status() -> dict[str, str]:
                return {"vendor": "verilator", "state": "SYNTHETIC"}

            hub = FastMCP("Synthetic EDA hub")
            hub.mount(synplify, namespace="synplify")
            hub.mount(verilator, namespace="verilator")

            async with Client(hub) as client:
                listed = await client.list_tools_mcp()
                self.assertEqual(
                    {tool.name for tool in listed.tools},
                    {"synplify_tool_status", "verilator_tool_status"},
                )
                for name, expected in (
                    ("synplify_tool_status", "synplify"),
                    ("verilator_tool_status", "verilator"),
                ):
                    result = await client.call_tool_mcp(name, {})
                    self.assertFalse(result.is_error)
                    self.assertEqual(result.structured_content["vendor"], expected)
                    self.assertEqual(result.structured_content["state"], "SYNTHETIC")

        asyncio.run(asyncio.wait_for(check(), timeout=25))

    def test_middleware_counts_without_logging_private_arguments(self) -> None:
        async def check() -> None:
            server = FastMCP("Middleware sample")
            metrics = CountingMiddleware()
            server.add_middleware(metrics)

            @server.tool
            def ping(secret: str) -> dict[str, bool]:
                # This value is deliberately not stored by middleware.
                return {"ok": bool(secret)}

            async with Client(server) as client:
                first = await client.call_tool_mcp("ping", {"secret": "private-sample"})
                second = await client.call_tool_mcp("ping", {"secret": "another-private"})
                self.assertFalse(first.is_error)
                self.assertFalse(second.is_error)
            self.assertEqual(metrics.tool_calls, 2)
            self.assertEqual(set(vars(metrics)), {"tool_calls"})

        asyncio.run(asyncio.wait_for(check(), timeout=25))


if __name__ == "__main__":
    unittest.main()
