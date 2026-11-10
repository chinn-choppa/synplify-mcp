# Architecture

[Русский](ARCHITECTURE.md)

```text
MCP client -> local stdio -> synplify_mcp.server
                                 |              |
                       report/compare      approved_run (OFF)
                       read-only tools     trusted .prj + executable
```

Six registered tools: `server_info`, `tool_status`, `parse_diagnostics`,
`parse_srr`, `compare_srr_reports`, and `run_approved_synthesis`.

Only the last operation can perform side effects. It requires the operator to enable
execution and explicitly approve a project and its hash. The .prj file can execute Tcl
and write outside the run directory; the module is **not an operating-system sandbox**.

The report parser is bounded, stores source-line and byte provenance and reports unknown data
without guessing. No resource type is universally comparable across FPGA devices.
Preliminary Synplify timing cannot substitute for routed implementation timing.

The comparison service requires explicit matching tool/device context for resource deltas.
Numerical timing deltas are withheld when full constraint equivalence is unverified.
Parsing, MCP protocol, process exit zero, and vendor-verified synthesis are distinct
evidence levels.

This independent repository has no mandatory external network service and
no dependency on Verilator MCP, Questa MCP, or agent-dev-toolkit.
