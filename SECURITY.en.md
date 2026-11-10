# Security policy

[Русский](SECURITY.md)

## Reporting vulnerabilities

Do not disclose working exploits, credentials, proprietary RTL or personal data in public issues. Use GitHub's private vulnerability reporting feature if enabled, otherwise contact the maintainer privately through an available channel. Do not assume a public issue is confidential.

## Threat model

MCP tools consume untrusted client arguments. A future feature may execute a commercial vendor program with the permissions of the local user; this is a high-risk action even with stdio transport.

The bootstrap version never executes EDA, Tcl or shell, never reads project RTL, has bounded text diagnostic inputs and uses no external telemetry/network service. Executable discovery intentionally does not return absolute paths.

Before implementing process execution, require an explicitly trusted executable, a restricted workspace root, protection against path traversal and symlink escapes, bounded time/logs/memory, reliable child-process cleanup and explicit user opt-in. Do not rely on MCP readOnlyHint as an access-control mechanism.

## Confidentiality

Local stdio prevents this server from listening on network ports. It does *not* prevent the MCP client or its underlying model from sending tool responses elsewhere. Never connect private corporate projects to an unapproved cloud agent or upload log contents without authorization.

## Supported versions

Before the first stable release, there is no fixed security support timeline. Each report is triaged individually. A version support table will be published with the first stable release.
