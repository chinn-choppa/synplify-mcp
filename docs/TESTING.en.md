# Testing

[Русский](TESTING.md)

Use isolated environments managed with uv:

```bash
uv sync --locked
uv run --no-sync python -m compileall -q src tests
uv run --no-sync python -m unittest discover -s tests -v
```

The integration CI matrix runs Windows and Linux on Python 3.11, 3.13 and 3.15.
It must verify domain/unit/contract tests, original .srr fixtures, path and encoding
failures, mock process timeout/log limits, native in-memory MCP and real subprocess
stdio `tools/list`/`tools/call`. Import-only or stub tests cannot substitute
for a real protocol test.

Public CI does **not** require Synplify Pro, a commercial license, or proprietary RTL.
Real vendor acceptance must be recorded separately: verified Synplify version,
target device, operating system, Python/MCP version, constraints, project/report
SHA-256, exit status and artifacts. Until performed it remains `NOT_RUN`.

## Installed distribution smoke tests

```bash
uv sync --locked
uv run --no-sync python -m unittest discover -s tests -v
uv build
python scripts/verify_release_artifacts.py
```

The matrix tests Windows/Linux × Python 3.11/3.13/3.15. Additional Windows/Linux Python 3.13 jobs install each wheel and sdist **in a fresh venv**, then exercise the real official MCP stdio client, six tools, parsing and default-disabled EDA. This is not vendor acceptance. See [release procedure](RELEASE_PROCESS.en.md).
