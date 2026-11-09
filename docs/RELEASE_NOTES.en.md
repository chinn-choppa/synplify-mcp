# synplify-mcp 0.1.0a1 — experimental release candidate

[Русский](RELEASE_NOTES.md)

**Status: candidate only; tag and GitHub Release have not been published.**

First experimental Synopsys Synplify Pro MCP adapter on the **official MCP SDK 2.3.0** (not FastMCP). Six tools: `server_info`, `tool_status`, `parse_diagnostics`, `parse_srr`, `compare_srr_reports`, `run_approved_synthesis`.

- Bounded `.srr` diagnostics, provenance, resource metrics, preliminary timing, and evidence-gated comparisons.
- Approved-project synthesis is **disabled by default**, and `.prj` may execute Tcl; not a sandbox.
- Security guardrails: operator-owned allowlist manifest outside the agent workspace, `.prj` SHA-256, native Windows `.exe` only, bounded logging and timeouts.
- `uv.lock`, Windows/Linux CI on Python 3.11/3.13/3.15 and independent wheel/sdist installation with real MCP `stdio` calls.

**Not validated:** commercial Synplify Pro, licenses, actual FPGA targets and successful vendor synthesis. **EDA_PASS=NOT_RUN**; process exit 0 does not prove EDA success.

[README](../README.en.md) · [Security](../SECURITY.en.md) · [Release procedure](RELEASE_PROCESS.en.md).
