# Security policy

[Русский](SECURITY.md)

## Reporting security issues

Never disclose exploits, credentials or proprietary RTL in public issues. Use private GitHub vulnerability reporting if configured, otherwise contact maintainers privately.

## Threat model

The MCP client supplies untrusted tool arguments. Read-only report operations use an operator-defined workspace, reject traversal and symlinks, and limit file bytes, diagnostics and responses. These checks do not form an OS security sandbox against an attacker who can mutate the local filesystem concurrently.

The `run_approved_synthesis` operation is disabled by default. It requires an operator-owned allowlist, exact .prj SHA-256, executable path and separate enable flag. It exposes no arbitrary shell/Tcl arguments, but **a Synplify .prj is itself executable Tcl**: included scripts, HDL files, output destinations and external commands must all be reviewed and protected. The executor is not a VM/container, and child process cleanup is best effort. The server does not redistribute or upload licenses and confidential source code.

`acknowledge_side_effects=true` can be sent by an agent; it is not guaranteed human consent. MCP tool annotations are hints, never authorization. Require host approval and restrictive OS credentials. A zero exit code is reported as `PROCESS_EXIT_ZERO_UNVERIFIED`, not `EDA_PASS`.

Local stdio does not ensure privacy from the model backing an MCP client: a client can forward source paths and diagnostic excerpts. Use confidential data only in authorized environments.

## Support

Until the first stable release, vulnerabilities are reviewed individually; a versioned maintenance policy will follow.

## Alpha trust-boundary hardening

On Windows the approved-run executable must be a native `.exe`, not a `.bat`/`.cmd`/`.ps1` wrapper. This is **not** vendor-binary authenticity verification. Operator approval manifests must be kept outside the agent-writable `SYNPLIFY_MCP_WORKSPACE`. Referenced Tcl, RTL, constraints and other mutable `.prj` dependencies are not protected by the project file's SHA-256. Check-to-use races remain. Use a restricted VM/OS account and actual human approval in the MCP client: there is no OS sandbox.
