# MCP tool contract — experimental

[Русский](TOOL_CONTRACT.md)

All tools use local stdio with the official MCP Python SDK 2.3.0.

## Read-only operations

- `server_info()`: server/version/stage, registered tools, separate availability,
  enablement and commercial EDA validation flags
- `tool_status()`: executable discovery, never launch or expose license information
- `parse_diagnostics(text,limit=200)`: bounded text diagnostics, not build PASS
- `parse_srr(relative_path,encoding="auto",limit=200)`: bounded authorized workspace
  reader with report SHA-256, original line/byte evidence and unknown data states.
  See [parser guide](SRR_PARSER.en.md).
- `compare_srr_reports(baseline_path,candidate_path,encoding="auto")`:
  compare two authorized reports with known tool/device compatibility gates.
  Numerical timing deltas remain null without evidence that **all constraints** match.
  See [comparison guide](COMPARE.en.md).

## Potentially side-effecting operation

`run_approved_synthesis(project_id,acknowledge_side_effects=false,timeout_seconds=30)`
is disabled by default. Only an operator-approved project SHA and fixed batch arguments
are permitted. The MCP client may not supply shell/Tcl commands, but the trusted .prj
can itself execute Tcl; see [operator guide](APPROVED_RUN.en.md).
MCP host human confirmation is required for safe operation;
`acknowledge_side_effects` alone does not prove it.
An exit code zero returns `PROCESS_EXIT_ZERO_UNVERIFIED`, **not** EDA_PASS.

The server never automatically uploads source code, logs or licenses.

**Alpha 0.1.0a1: actual vendor execution is blocked**, regardless of the environment. The MCP endpoint returns `VENDOR_EXECUTION_NOT_VALIDATED` with `executed=false` when configured, or `DISABLED` by default. Both `server_info.eda_execution_supported` and `.eda_execution_enabled` are always `false`. Synthetic internal executor successes are not MCP or licensed EDA successes.
