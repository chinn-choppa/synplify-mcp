"""Read-only stdio MCP. В этой версии нет запуска EDA-команд."""

from __future__ import annotations

from mcp.server import MCPServer

from . import __version__
from .diagnostics import parse_diagnostics_text
from .runtime import inspect_tool


def create_server() -> MCPServer:
    """Создать сервер с минимальным проверяемым интерфейсом."""
    server = MCPServer("synplify-mcp")

    @server.tool()
    def server_info() -> dict[str, object]:
        """Сообщить о возможностях прототипа без запуска EDA."""
        return {
            "server": "synplify-mcp",
            "version": __version__,
            "vendor_tool": "synplify_pro",
            "stage": "bootstrap",
            "operations": ["server_info", "tool_status", "parse_diagnostics"],
            "eda_execution_supported": False,
        }

    @server.tool()
    def tool_status() -> dict[str, object]:
        """Найти установленный инструмент, не выполняя его."""
        return inspect_tool("synplify_pro", "SYNPLIFY_MCP_EXECUTABLE")

    @server.tool()
    def parse_diagnostics(text: str, limit: int = 200) -> dict[str, object]:
        """Распознать известные диагностические строки с ограничением размера."""
        return parse_diagnostics_text(text, "synplify_pro", limit)

    return server


def main() -> None:
    """Запустить локальный stdio MCP."""
    create_server().run(transport="stdio")
