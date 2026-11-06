"""Локальный stdio MCP с операторским разрешением на пакетный синтез."""

from __future__ import annotations

import os

from mcp.server import MCPServer

from . import __version__
from .approved_run import ENABLE_ENV, run_approved_project
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
            "operations": ["server_info", "tool_status", "parse_diagnostics", "parse_srr", "run_approved_synthesis"],
            "eda_execution_enabled": os.getenv(ENABLE_ENV) == "1",
            "eda_execution_supported": True,
            "eda_execution_mode": "OPERATOR_APPROVED_PROJECT_ONLY",
            "eda_vendor_test": "NOT_RUN",
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
    def run_approved_synthesis(project_id: str, acknowledge_side_effects: bool = False,
                               timeout_seconds: int = 30) -> dict[str, object]:
        """Может менять файлы: только доверенный .prj с явным разрешением."""
        return run_approved_project(project_id, acknowledge_side_effects, timeout_seconds)

    return server


def main() -> None:
    """Запустить локальный stdio MCP."""
    create_server().run(transport="stdio")
