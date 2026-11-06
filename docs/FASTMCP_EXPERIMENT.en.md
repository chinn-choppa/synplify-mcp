# Experiment: FastMCP 4 as the MCP server framework

[Русский](FASTMCP_EXPERIMENT.md)

## Scope

`experiment/fastmcp-v4` branches from
`integration/mvp-review-2026-11-06` (draft PR #15).
It compares the **official MCP SDK 2.3.0 MCPServer**
with **FastMCP 4.1.6 as an alternative server framework**.
The MCP protocol stays unchanged; FastMCP 4 shares the SDK v2
protocol types and retains `mcp.types.ToolAnnotations`.

## Minimal migration

- Replace `MCPServer` with `FastMCP` and pin dependencies.
- Preserve six public tool names, required input-schema fields,
  dictionary responses, read-only/destructive annotations,
  local-only `stdio` and the existing `synplify-mcp` entry point.
- Leave `diagnostics.py`, `srr.py`, `metrics.py`,
  `compare.py` and `approved_run.py` untouched.
  A server framework is not an EDA execution sandbox.
- Use `fastmcp.Client` in process, while an **independent**
  official `mcp.Client` connects over a real subprocess stdio
  transport and verifies interoperability.

## Acceptance criteria

1. All six Windows/Linux × Python 3.11/3.13/3.15.2 CI jobs
   pass, including real protocol calls.
2. Preserve six tool names, required `inputSchema` parameters
   and read-only/destructive metadata.
3. Reject unexpected parameters such as `command`, rather
   than silently accepting arbitrary agent input.
4. Confirm official SDK `tools/list` and `tools/call`
   over stdio; `run_approved_synthesis` must return `DISABLED`
   with operator execution disabled.
5. Synthetic tests must never be described as commercial
   `EDA_PASS`; licensed Synplify and real targets remain `NOT_RUN`.
6. Consider additional dependencies and long-term maintenance
   costs before recommending adoption across EDA adapters.

## Known limitations

- `fastmcp` and `mcp` are explicitly pinned but there is
  currently no reviewed `uv.lock`; transitive versions can vary.
- FastMCP enforces strict unexpected-input rejection, which
  intentionally changes behavior for non-conforming clients.
- An operator-approved `.prj` may execute Tcl; its SHA-256 does
  not authenticate all included Tcl, RTL and constraint files.
  Use trusted OS accounts/VMs. No transport or framework can
  enforce those permissions automatically.
- This experiment does **not** enable HTTP, proxying, external
  middleware, remote APIs or telemetry.

Official FastMCP documentation:
[MCP SDK v2 migration](https://gofastmcp.com/getting-started/upgrading/from-mcp-sdk-v2),
[client testing](https://gofastmcp.com/clients/client).

Do not merge into `main` or PR #15 without separate owner approval.
