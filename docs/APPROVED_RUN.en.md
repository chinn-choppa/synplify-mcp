# Approved-project Synplify execution (experimental)

[Русский](APPROVED_RUN.md)

## Security boundary

The documented batch invocation is `synplify_pro -batch <project.prj>`.
The `.prj` file itself contains **executable Tcl**, so refusing
arbitrary shell arguments is not sufficient: the project and all
included source, Tcl, constraint and environment dependencies must
be reviewed and protected by the operator. Consult the
[historical batch reference](https://www.arl.wustl.edu/projects/fpx/cse535/resources/synpro_ref_1001.pdf);
batch licensing limitations vary by edition. No proprietary binaries
or reports are included here.

This is **not an OS sandbox**. Each run receives its own cwd and
local stdout log directory, but a trusted `.prj` can write elsewhere
or launch other programs. Use a restricted VM/OS account for
untrusted environments, and keep the approved project and its
dependencies immutable for the duration of a run.

## Operator-controlled configuration

Prepare a trusted workspace with `projects/demo.prj` and an
existing `artifacts/` directory. Create a small manifest outside
agent-editable areas:

```json
{
  "schema": 1,
  "projects": {
    "demo": {
      "project": "projects/demo.prj",
      "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "artifacts": "artifacts"
    }
  }
}
```

Replace the example digest with the **actual SHA-256** of the trusted
`.prj` (for example, using `sha256sum` or `Get-FileHash`).
Project and artifact paths are relative to the workspace; traversal,
symlinks and unapproved project IDs are rejected.

The operator sets these environment variables when starting the
MCP server, **not through the MCP client**:

```bash
export SYNPLIFY_MCP_ENABLE_SYNTHESIS=1
export SYNPLIFY_MCP_WORKSPACE=/srv/eda/workspace
export SYNPLIFY_MCP_RUN_MANIFEST=/srv/eda/operator/manifest.json
export SYNPLIFY_MCP_EXECUTABLE=/opt/synopsys/synplify/bin/synplify_pro
uv run synplify-mcp
```

Use platform-appropriate absolute paths on Windows. The executable
path shown above is illustrative and **not** a verified installation.

## Side-effecting MCP call

```json
{
  "project_id": "demo",
  "acknowledge_side_effects": true,
  "timeout_seconds": 30
}
```

**Important:** the agent can supply `acknowledge_side_effects=true`
itself. This does **not** prove human authorization; the MCP host
must enforce interactive approval as appropriate. Operator-enabled
execution should only be connected to trusted clients.

The command is fixed to the argv array
`[trusted_executable, "-batch", approved_project_path]` and uses
`shell=False`; it does not accept arbitrary `-tclcmd`, Tcl or shell
input. Timeout is bounded to 1–120 s. Only the first 64 KiB of stdout/
stderr is retained locally, and excess output terminates the process.
Process-tree termination uses a best-effort POSIX process group or
the fixed Windows `taskkill /T` tool. This is not a hard guarantee
against all descendants or independent vendor jobs.

## Result states and evidence

Before launch, returns structured refusals such as
`DISABLED`, `CONFIRMATION_REQUIRED`, `PROJECT_NOT_APPROVED`,
`PROJECT_CHANGED`, `INVALID_MANIFEST` or `NOT_INSTALLED`.

After launch, states include `LICENSE_UNAVAILABLE` (conservative
log heuristic), `TOOL_FAILED`, `TIMEOUT`, `LOG_LIMIT`,
`LAUNCH_ERROR` and `PROCESS_EXIT_ZERO_UNVERIFIED`.
An exit code of zero is **not evidence of a successful synthesis**:
`eda_validation="NOT_VERIFIED"` always, with no `EDA_PASS`
claim until authorized vendor-specific acceptance.

The MCP result contains only an approved project ID, its expected
project-file SHA-256, a short run directory ID, exit code and SHA-256
of the captured local log. It does **not** include full stdout,
absolute executable/project paths, source code or license files.
The installed Synplify tool may contact an operator-configured
license server; the MCP server performs no upload itself.

The run directory isolates the server's cwd and log only; a
Synplify `.prj` may generate other outputs at locations defined
in its trusted project configuration. Public CI tests mocked
executables and refusals; real licensed EDA acceptance, reported
versions and results remain `NOT_RUN`.

## Alpha security clarification

- On Windows, `SYNPLIFY_MCP_EXECUTABLE` must be a native `.exe`. Batch and script wrappers (`.bat`, `.cmd`, `.ps1`) are refused because Windows may launch batch files via an interpreter even with `shell=False`. An `.exe` extension does **not** authenticate a vendor binary.
- The project approval manifest **must be outside `SYNPLIFY_MCP_WORKSPACE`**. A coding agent with write access to its project workspace must not be able to rewrite its own allowlist. Its location is operator-controlled.
- A `.prj` digest does not protect referenced Tcl, RTL, constraints and other mutable inputs or close the check-to-use race. Use a dedicated restricted OS account or VM for untrusted workloads. This executor is **not** an OS sandbox.

**Windows process cancellation:** the native `taskkill.exe` path is resolved through WinAPI `GetSystemDirectoryW`, not the inherited `SystemRoot` environment variable. Overriding `SystemRoot` cannot redirect the helper to an attacker-controlled binary. Process-tree termination remains best-effort and is not an OS sandbox.

## Alpha execution security decision

**Actual vendor execution through the MCP endpoint is blocked for 0.1.0a1**, even if `SYNPLIFY_MCP_ENABLE_SYNTHESIS=1`. The tool returns `VENDOR_EXECUTION_NOT_VALIDATED` with `executed=false`, without launching Synplify. The injectable `executor` parameter exists solely for internal synthetic testing. Real execution requires a separately reviewed architecture with OS-enforced sandbox/resource isolation, protected operator manifest and .prj/Tcl inputs, server-side human authorization outside caller-controlled MCP arguments, and licensed vendor acceptance. An enable flag cannot substitute for these controls.

Manifest and .prj files with more than one hard link are now rejected. This blocks pre-existing hard-link aliases but **does not** prevent same-user writes or all TOCTOU races.
