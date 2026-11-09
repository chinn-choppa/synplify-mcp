"""Локальный MCP: анализ без запуска и опциональный одобренный EDA-процесс."""

from __future__ import annotations

import os

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from . import __version__
from .approved_run import ENABLE_ENV, run_approved_project
from .compare import compare_srr
from .diagnostics import parse_diagnostics_text
from .runtime import inspect_tool
from .srr import read_srr_report


def create_server() -> MCPServer:
    """Создать сервер с минимальным проверяемым интерфейсом."""
    server = MCPServer("synplify-mcp")

    @server.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
    def server_info() -> dict[str, object]:
        """Сообщить о возможностях прототипа без запуска EDA."""
        return {
            "server": "synplify-mcp",
            "version": __version__,
            "vendor_tool": "synplify_pro",
            "stage": "experimental",
            "operations": ["server_info", "tool_status", "parse_diagnostics", "parse_srr", "compare_srr_reports", "run_approved_synthesis"],
            "eda_execution_enabled": os.getenv(ENABLE_ENV) == "1",
            "eda_execution_supported": True,
            "eda_execution_validated": False,
        }

    @server.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
    def tool_status() -> dict[str, object]:
        """Найти установленный инструмент, не выполняя его."""
        return inspect_tool("synplify_pro", "SYNPLIFY_MCP_EXECUTABLE")

    @server.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
    def parse_diagnostics(text: str, limit: int = 200) -> dict[str, object]:
        """Распознать известные диагностические строки с ограничением размера."""
        return parse_diagnostics_text(text, "synplify_pro", limit)

    @server.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
    def parse_srr(relative_path: str, encoding: str = "auto", limit: int = 200) -> dict[str, object]:
        """Читать .srr из заранее разрешённого локального каталога, без запуска EDA."""
        return read_srr_report(relative_path, encoding, limit)

    @server.tool(annotations=ToolAnnotations(
        read_only_hint=True, open_world_hint=False,
    ))
    def compare_srr_reports(baseline_path: str, candidate_path: str,
                            encoding: str = "auto") -> dict[str, object]:
        """Сопоставить два отчёта из разрешённого workspace без запуска EDA."""
        return compare_srr(baseline_path, candidate_path, encoding)

    @server.tool(annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=False,
        open_world_hint=True,
    ))
    def run_approved_synthesis(project_id: str, acknowledge_side_effects: bool = False,
                               timeout_seconds: int = 30) -> dict[str, object]:
        """Может менять файлы: только доверенный .prj с явным разрешением."""
        return run_approved_project(project_id, acknowledge_side_effects, timeout_seconds)

    return server


def main() -> None:
    """Запустить локальный stdio MCP."""
    create_server().run(transport="stdio")
