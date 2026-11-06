# Testing

[Русский](TESTING.md)

Use isolated environments managed with uv:

```bash
uv sync
uv run --no-sync python -m compileall -q src tests
uv run --no-sync python -m unittest discover -s tests -v
```

The integration CI matrix runs Windows and Linux on Python 3.11, 3.13 and 3.15.
It must verify domain/unit/contract tests, original .srr fixtures, path and encoding
failures, mock process timeout/log limits, native in-memory MCP and real subprocess
stdio `tools/list`/`tools/call`. Import-only or stub tests cannot substitute
for a real protocol test.

Public CI does **not** require Synplify Pro, a commercial license, or proprietary RTL.
Real vendor acceptance must be recorded separately: verified Synplify version,
target device, operating system, Python/MCP version, constraints, project/report
SHA-256, exit status and artifacts. Until performed it remains `NOT_RUN`.

## FastMCP experiment

`uv sync` pins FastMCP 4.1.6 and official MCP SDK 2.3.0. The in-memory `fastmcp.Client` validates tool enumeration, annotations and schemas. The independent official `mcp.Client` invokes real subprocess `stdio` `tools/list`/`tools/call`, including strict unexpected-input rejection and default-off synthesis. See the [reproducible matrix and dependency comparison](FASTMCP_EXPERIMENT.en.md).
