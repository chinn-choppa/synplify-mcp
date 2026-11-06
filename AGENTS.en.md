# Agent contract

[Русский](AGENTS.md)

This is an independent public EDA MCP server, not a copy of agent-dev-toolkit.

- Read README, SECURITY, and the MCP tool contract before editing; consult the current official MCP SDK documentation.
- Investigate existing implementations before writing new code; prefer minimal, verified changes.
- Distinguish Python import success, MCP tools/list, MCP tools/call, and actual licensed EDA runs.
- Do not add arbitrary shell, Tcl, DO, or general-purpose script execution.
- Publish only original synthetic fixtures and publicly shareable RTL. Never commit licenses, corporate reports, secrets or telemetry.
- Use uv for dependencies, with isolated environments, and target Windows and Linux.
- Test invalid inputs, limits, paths, protocol errors and idempotent setup for every new feature.
- Engineering prose may be in Russian, but major public documentation must have complete English and Russian versions.
- Check licenses and give attribution before incorporating third-party code.
