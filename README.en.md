# synplify-mcp

[Русский](README.md) · [Contributing](CONTRIBUTING.en.md) · [Security](SECURITY.en.md)

An independent, local-first, open-source MCP adapter for **Synopsys Synplify Pro**, intended for FPGA engineers and compatible AI agents.

**Status: experimental bootstrap (0.0.1).** It currently provides an MCP server, no-execution executable discovery and bounded diagnostic parsing. Synthesis execution, full .srr parsing, resources, timing and report comparison are not yet implemented. No commercial EDA compatibility or license has been verified.

## Install

Requires Python 3.11+ and uv. The project depends on official MCP Python SDK 2.3.0.

```bash
git clone https://github.com/chinn-choppa/synplify-mcp.git
cd synplify-mcp
uv sync
uv run synplify-mcp
```

Example for clients with an mcpServers configuration; use absolute trusted local paths:

```json
{"mcpServers":{"synplify-mcp":{"command":"uv","args":["--directory","/absolute/path/to/synplify-mcp","run","synplify-mcp"]}}}
```

Codex and OpenCode can require different configuration formats.

## Bootstrap tools

| Tool | Behavior | Limits |
| --- | --- | --- |
| server_info | Reports server identity, stage and supported operations | Read-only |
| tool_status | Looks for Synplify, without launching it or leaking its path | Read-only |
| parse_diagnostics | Recognizes selected diagnostic lines in supplied text | Up to 1 MiB and 200 returned items |

This is not a full .srr parser and cannot certify that synthesis passed.

## Testing

```bash
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q src tests
```

The real MCP protocol is checked by in-memory and stdio clients in tests/test_protocol.py. These are different from licensed EDA acceptance, which remains NOT_RUN. See [testing](docs/TESTING.en.md) and [compatibility](docs/COMPATIBILITY.en.md).

## Project policies and design

[Architecture](docs/ARCHITECTURE.en.md) · [Roadmap](docs/ROADMAP.en.md) · [Tool contract](docs/TOOL_CONTRACT.en.md) · [Third-party components](docs/THIRD_PARTY.en.md) · [Changelog](CHANGELOG.en.md) · [Code of conduct](CODE_OF_CONDUCT.en.md) · [Agent guidance](AGENTS.en.md)

The server uses only local stdio, distributes no Synplify binaries or licenses, and never uploads RTL or reports. No arbitrary shell or Tcl execution is exposed. Apache License 2.0. Not affiliated with or endorsed by Synopsys.
