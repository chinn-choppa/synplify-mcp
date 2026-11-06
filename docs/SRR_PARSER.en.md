# .srr report parser (M2 / #4)

[Русский](SRR_PARSER.md)

The `parse_srr(relative_path, encoding="auto", limit=200)` tool reads
only a permitted `.srr` file under an **operator-configured** workspace.
It never invokes Synplify, runs arbitrary Tcl/shell commands or opens
network sockets.

Set an absolute, trusted workspace root before starting the server:

```bash
export SYNPLIFY_MCP_WORKSPACE="/absolute/path/to/workspace"
uv run synplify-mcp
```

PowerShell:

```powershell
$env:SYNPLIFY_MCP_WORKSPACE = "D:\projects\authorized-workspace"
uv run synplify-mcp
```

The MCP argument is a **relative** `/`-separated path, e.g.
`reports/build.srr`. Absolute paths, traversal, symlink escape,
non-.srr files and inputs larger than 1 MiB are rejected.
Line count, output size and message count are also bounded.
The workspace is considered trusted; this is not a hardened sandbox
against concurrent malicious local filesystem changes.

## Result contract

- `state="PARSED"` means the report was read and examined, **not**
  that synthesis passed. `synthesis_status` remains `UNKNOWN`.
- `parse_health` is one of `PARSED`, `PARTIAL`, `EMPTY`,
  `NO_DIAGNOSTICS` or `UNRECOGNIZED`. No diagnostics never implies
  a successful synthesis job.
- Failures have `state="ERROR"` and a machine-readable `error_code`
  (including `INVALID_PATH`, `WORKSPACE_NOT_CONFIGURED`,
  `TOO_LARGE`, `DECODE_ERROR`, `SYMLINK_DENIED`).
- Diagnostics include exact `raw`, report line number and byte offset,
  section, severity, optional code and HDL source location, and a
  conservative latch/black-box category.
- `report_sha256`, `size_bytes` and `encoding` identify the input.
  Unknown `tool_version` and `device` are `null`, not guessed.
- Utilization and timing remain `NOT_EXTRACTED` until #5. Synplify
  timing is a preliminary synthesis estimate, never a routed result.

Supported encodings: UTF-8, UTF-8 BOM, UTF-16 LE/BE BOM, and explicit
`encoding="cp1252"` for Windows-1252. Malformed bytes cause a
structured error, never silent replacement. Fixtures are invented,
and real Synplify version compatibility remains NOT_RUN.

**Confidentiality:** the MCP client may forward returned source paths
and message fragments to an external AI model. Use confidential
projects only in approved local/enterprise environments.
