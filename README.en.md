# synplify-mcp

[Русский](README.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

Community-focused, local-first MCP adapter for **Synopsys Synplify Pro**. This is an independently maintained open-source project, not an official vendor product.

**Status: experimental bootstrap (0.0.1).** The initial release exposes a minimal MCP server, installation detection and bounded diagnostic parsing. By default it does **not** execute synthesis or simulation. Experimental execution of operator-approved projects requires an explicit opt-in; no vendor EDA success has been validated. Arbitrary shell/Tcl arguments remain unavailable.

## Setup

Python 3.11+ and `uv` are required:

```bash
git clone https://github.com/chinn-choppa/synplify-mcp.git
cd synplify-mcp
uv sync
uv run synplify-mcp
```

MCP tools: `server_info`, `tool_status`, `parse_diagnostics`, `parse_srr`. Use a local stdio-capable MCP client and configure it to launch the installed command. A real MCP client test is separate from Python unit tests.

## Development

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

Review [architecture](docs/ARCHITECTURE.md), [roadmap](docs/ROADMAP.md) and [security](SECURITY.md). Russian is used for most engineering documentation; international contributions are welcome, including improvements to English documentation.

Licensed under Apache-2.0. No proprietary EDA executables, licenses or private project data are distributed here.

## Format research

[Report format inventory and synthetic fixture provenance](docs/REPORT_FORMATS.en.md).

## Reading .srr reports (experimental)

The `parse_srr` tool reads only files inside an operator-approved `SYNPLIFY_MCP_WORKSPACE`. See [safe parser contract](docs/SRR_PARSER.en.md). Missing diagnostics never prove synthesis succeeded.

## Resource and preliminary timing metrics

Issue #5 adds conservative extraction only from explicitly labelled sections. Unknown or ambiguous values remain null, and Synplify estimates are **not** post-route timing. See the [metrics contract](docs/METRICS.en.md).

## Experimental approved-project execution

`run_approved_synthesis` (#6) is disabled by default. It requires an operator-owned project allowlist and checks the `.prj` SHA-256; it never accepts arbitrary Tcl/shell arguments. The project can itself execute Tcl, so this is **not a sandbox**. Exit zero is not EDA success. Read the [operator guide](docs/APPROVED_RUN.en.md).
