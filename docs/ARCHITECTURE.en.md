# Architecture

[Русский](ARCHITECTURE.md)

```text
MCP client -> local stdio -> synplify_mcp.server
                                |          |
                             runtime   diagnostics
                           (discovery) (log parsing)
                                |
                    Synplify Pro (future opt-in only)
```

The bootstrap exposes three strictly read-only MCP tools; it does not run synthesis or Tcl commands. The future report parser will consume a trusted read-only .srr path, return structured evidence and report uncertainty. The future process executor must live behind a separate, narrow authorization boundary and cannot accept arbitrary command lines.

## Isolation

This repository is versioned independently of agent-dev-toolkit and the Verilator/Questa adapters. MCP operations must remain client-agnostic. Shared abstractions should only be extracted after two verified implementations justify them.

Default transport is local stdio. There is no required network service or telemetry. A future executor must require explicit workspace/output roots, emit observed tool version and exit status, preserve artifact provenance, and report NOT_RUN when nothing was actually executed.

## Evidence levels

Python import, tools/list, tools/call, report PARSED and licensed EDA_PASS are distinct facts. Discovering an executable does not prove a license is usable; missing parsed errors do not establish a successful synthesis. Synplify preliminary timing is not post-route timing from vendor implementation software.
