# Testing

[Русский](TESTING.md)

Run the full public test suite in a local uv-managed environment:

```bash
uv sync
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q src tests
```

For domain-only tests without SDK installation, use PYTHONPATH=src, but do not describe this as an MCP protocol pass.

## Native MCP acceptance

tests/test_protocol.py uses the real MCP SDK v2 client for both in-memory transport and a child-process stdio transport. It asserts tools/list, tools/call, structured outputs, error signaling and implicit stdout hygiene. CI runs on Windows and Linux with Python 3.11 and 3.13. Read the actual job result before recording MCP_TOOL_PASS.

## Commercial EDA acceptance

Not part of public CI and currently NOT_RUN. Once authorized, use freely publishable minimal RTL and test successful completion, license denial, tool failure, invalid paths, timeouts, process cancellation, log limits and vendor-version-specific .srr parsing. Record OS, Python, SDK and Synplify versions, and source hashes. Never publish license files or proprietary reports.
