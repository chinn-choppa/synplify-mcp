# MCP tool contract v0

[Русский](TOOL_CONTRACT.md)

All bootstrap operations use local stdio, have bounded inputs, do not send network traffic and never launch commercial EDA software.

## server_info()

Returns server, version, vendor_tool, stage, operations and eda_execution_supported=false. The bootstrap stage is not a claim that synthesis works.

## tool_status()

Discovers synplify_pro on PATH or uses SYNPLIFY_MCP_EXECUTABLE; it never runs the file. Fields are tool, state, configured and executed=false. States: DETECTED_UNVERIFIED, NOT_FOUND and INVALID_OVERRIDE. It does not expose full executable paths or license settings.

## parse_diagnostics(text, limit=200)

Accepts at most 1 MiB of UTF-8 text and returns at most 200 recognized diagnostics. Returns tool, count, truncated and items containing severity, code, file, line, column, message and raw. Unknown messages remain unrecognized rather than being fabricated. count is the number of recognized messages before output truncation.

An example synthetic line is `@W: rtl/top.sv(14): Width mismatch`. No recognized messages never implies successful synthesis; callers must inspect the actual run status.

## Future tools

A future read-only .srr parser must enforce an explicit workspace, bounded file size, source-line provenance and explicit unknown/unparsed status. A future synthesis runner will need explicit opt-in and constrained project entrypoints. There must be no general-purpose command/shell/Tcl argument.
