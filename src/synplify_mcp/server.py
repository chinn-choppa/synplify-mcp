"""Read-only stdio MCP. В этой версии нет запуска EDA-команд."""

from __future__ import annotations

from mcp.server import MCPServer

from . import __version__
from .compare import compare_srr
from .diagnostics import parse_diagnostics_text
from .runtime import inspect_tool
from .srr import read_srr_report


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
            "operations": ["server_info", "tool_status", "parse_diagnostics", "parse_srr", "compare_srr_reports"],
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

    @server.tool()
    def parse_srr(relative_path: str, encoding: str = "auto", limit: int = 200) -> dict[str, object]:
        """Читать .srr из заранее разрешённого локального каталога, без запуска EDA."""
        return read_srr_report(relative_path, encoding, limit)

    @server.tool()
    def compare_srr_reports(baseline_path: str, candidate_path: str,
                            encoding: str = "auto") -> dict[str, object]:
        """Сравнить два разрешённых отчёта без запуска Synplify."""
        return compare_srr(baseline_path, candidate_path, encoding)

    return server


def main() -> None:
    """Запустить локальный stdio MCP."""
    create_server().run(transport="stdio")
