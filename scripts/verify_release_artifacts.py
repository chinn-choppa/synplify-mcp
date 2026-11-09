"""Проверить wheel и sdist через новый venv и настоящий MCP stdio, без EDA."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TOOLS = {
    "server_info", "tool_status", "parse_diagnostics", "parse_srr",
    "compare_srr_reports", "run_approved_synthesis",
}

# Executed in a fresh venv with the installed artifact, not from the source tree.
INSTALLED_SMOKE = r'''
import asyncio
import os
import sys
from importlib.metadata import version
from pathlib import Path

from mcp import Client, StdioServerParameters

EXPECTED_TOOLS = {
    "server_info", "tool_status", "parse_diagnostics", "parse_srr",
    "compare_srr_reports", "run_approved_synthesis",
}

async def check():
    assert version("synplify-mcp") == sys.argv[1]
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "synplify_mcp"],
        env=dict(os.environ, SYNPLIFY_MCP_ENABLE_SYNTHESIS="0"),
    )
    async with Client(params) as client:
        tools = await client.list_tools()
        assert {t.name for t in tools.tools} == EXPECTED_TOOLS
        info = await client.call_tool("server_info", {})
        assert not info.is_error
        assert info.structured_content["version"] == sys.argv[1]
        assert info.structured_content["eda_execution_enabled"] is False
        parsed = await client.call_tool(
            "parse_diagnostics", {"text": "@W: top.sv(2): Synthetic warning"}
        )
        assert not parsed.is_error
        assert parsed.structured_content["count"] == 1
        refused = await client.call_tool(
            "run_approved_synthesis",
            {"project_id": "demo", "acknowledge_side_effects": True},
        )
        assert not refused.is_error
        assert refused.structured_content["state"] == "DISABLED"
        assert refused.structured_content["executed"] is False

    # Validate the actual installed console script, not just python -m.
    executable = Path(sys.executable).parent / (
        "synplify-mcp.exe" if os.name == "nt" else "synplify-mcp"
    )
    assert executable.is_file(), f"Installed entry point not found: {executable.name}"
    entrypoint = StdioServerParameters(
        command=str(executable), args=[],
        env=dict(os.environ, SYNPLIFY_MCP_ENABLE_SYNTHESIS="0"),
    )
    async with Client(entrypoint) as client:
        tools = await client.list_tools()
        assert {t.name for t in tools.tools} == EXPECTED_TOOLS
        result = await client.call_tool("server_info", {})
        assert not result.is_error
        assert result.structured_content["version"] == sys.argv[1]

asyncio.run(asyncio.wait_for(check(), timeout=35))
'''


def run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run(args, cwd=cwd, env=env, timeout=180, check=True)


def main() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    expected = metadata["project"]["version"]
    dist = ROOT / "dist"
    wheels = sorted(dist.glob("synplify_mcp-*.whl"))
    sdists = sorted(dist.glob("synplify_mcp-*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise RuntimeError("Expected exactly one wheel and one sdist")
    for archive in (wheels[0], sdists[0]):
        if f"-{expected}" not in archive.name:
            raise RuntimeError(f"Unexpected version in {archive.name}")
        with tempfile.TemporaryDirectory(prefix="synplify-package-") as tmp:
            folder = Path(tmp)
            venv = folder / "venv"
            python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            run("uv", "venv", "--python", sys.executable, str(venv), cwd=folder)
            run("uv", "pip", "install", "--python", str(python),
                str(archive.resolve()), cwd=folder)
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            env["SYNPLIFY_MCP_ENABLE_SYNTHESIS"] = "0"
            run(str(python), "-I", "-c", INSTALLED_SMOKE, expected, cwd=folder, env=env)
            print(f"RELEASE_SMOKE_PASS {archive.name}", flush=True)


if __name__ == "__main__":
    main()
