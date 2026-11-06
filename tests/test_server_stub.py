"""Синтетический тест регистрации инструментов без внешнего MCP SDK."""

import importlib
import sys
import types
import unittest
from unittest.mock import patch


class MCPStub:
    def __init__(self, name):
        self.name = name
        self.tools = {}

    def tool(self, **kwargs):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register

    def run(self, transport):
        raise AssertionError("Нельзя запускать настоящий сервер из stub теста")


class ServerStubTests(unittest.TestCase):
    def test_tool_registration_and_responses(self):
        mcp = types.ModuleType("mcp")
        fastmcp_mod = types.ModuleType("fastmcp")
        fastmcp_mod.FastMCP = MCPStub
        types_mod = types.ModuleType("mcp.types")
        types_mod.ToolAnnotations = lambda **kwargs: types.SimpleNamespace(**kwargs)
        
        target = "synplify_mcp.server"
        with patch.dict(sys.modules, {"mcp": mcp, "mcp.types": types_mod,
                                      "fastmcp": fastmcp_mod}):
            sys.modules.pop(target, None)
            try:
                module = importlib.import_module(target)
                server = module.create_server()
                self.assertEqual(set(server.tools), {"server_info", "tool_status", "parse_diagnostics", "parse_srr", "compare_srr_reports", "run_approved_synthesis"})
                info = server.tools["server_info"]()
                self.assertEqual(info["stage"], "experimental")
                self.assertTrue(info["eda_execution_supported"])
                self.assertFalse(info["eda_execution_validated"])
                found = server.tools["parse_diagnostics"]("", limit=1)
                self.assertEqual(found["count"], 0)
            finally:
                sys.modules.pop(target, None)


if __name__ == "__main__":
    unittest.main()
