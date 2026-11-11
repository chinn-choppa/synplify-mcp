# Contributing

[Русский](CONTRIBUTING.md)

Thank you for helping improve synplify-mcp for FPGA/ASIC engineers and users of multiple MCP clients. Reproducible issues, independently created report fixtures, clear API contracts and security-focused patches are welcome.

## Before contributing

1. Review existing issues, the architecture and comparable open-source implementations.
2. Describe the observed behavior, operating system, Python version, Synplify version when known, and exact reproduction steps.
3. Discuss major public API changes in an issue before implementation.
4. Never submit confidential RTL, employer/customer reports, license files, internal hostnames or unredacted secret-bearing logs.

## Development

Use an isolated environment:

```bash
uv sync
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q src tests
```

If dependencies cannot be installed, run domain-only tests with PYTHONPATH=src, but report native MCP tests as NOT_RUN. A module import or stub test is not equivalent to MCP communication.

## Pull requests

- One coherent change per PR, with issue reference, risk assessment, verification steps and rollback.
- Add success, failure and boundary tests; enforce bounded inputs, paths, timeouts and outputs.
- Do not introduce general command runners or external data uploads.
- Update contracts, both language variants of documentation and CHANGELOG when behavior changes.
- Distinguish PARSED, MCP_TOOL_PASS, EDA_PASS, NOT_RUN, NOT_SUPPORTED and license failures.
- Use typed Python and Conventional Commits (feat, fix, docs, test).
- New external process execution requires a security review.

Contributors must have the right to license submitted code under Apache-2.0. Report security problems privately as described in SECURITY.en.md.
