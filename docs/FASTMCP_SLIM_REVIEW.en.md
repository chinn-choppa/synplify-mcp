# FastMCP slim investigation: dependencies and practical capabilities

[Русский](FASTMCP_SLIM_REVIEW.md)

## Scope and package split

The branch `experiment/fastmcp-slim-runtime` starts from
`experiment/fastmcp-v4` (draft PR #16); it does not alter
`main` or existing integration PRs.

FastMCP 4.1.6 has an official package split:

- **Runtime:** `fastmcp-slim[server]==4.1.6` with pinned `mcp==2.3.0`.
- **Development only:** `fastmcp-slim[client]==4.1.6` in the uv
  `dev` dependency group for in-memory test clients.
- **Independent interoperability:** official `mcp.Client`
  connects through a real subprocess stdio transport in both
  regular tests and production-only smoke tests.
- Production-only jobs run `uv sync --no-dev`, then
  `test_runtime_only.py`. The test client extra is absent from
  this installation.

The basic `fastmcp-slim` distribution without `[server]`
is not the documented server installation; FastMCP itself requires
`fastmcp-slim[server]` for server imports. Avoid manually removing
its server dependencies; that would bypass supported packaging.

## Measured dependency footprint

| Configuration | Packages installed |
| --- | ---: |
| Official `mcp==2.3.0` server | 29 |
| Full `fastmcp==4.1.6` server | 63 |
| `fastmcp-slim[server]==4.1.6` + dev client | 62 |
| `fastmcp-slim[server]==4.1.6`, **no dev** | 62 |

Evidence: `Installed N packages` in GitHub Actions `uv sync`
on ubuntu-latest / Python 3.13 / uv 0.13.0:
[SDK run 42203127472](https://github.com/chinn-choppa/synplify-mcp/actions/runs/42203127472),
[full FastMCP run 42213862834](https://github.com/chinn-choppa/synplify-mcp/actions/runs/42213862834),
[slim run 42223925259](https://github.com/chinn-choppa/synplify-mcp/actions/runs/42223925259).
Use **installed**, not just **resolved** package counts:
the resolver may consider dependency groups even when `--no-dev`
excludes them from the active environment.

Slim saves **one installed package** compared to full FastMCP,
but still costs **33 extra installed packages** over the official SDK.
This is not a measurement of wheel sizes or runtime performance.

## Verified capabilities

[Run #42223925259](https://github.com/chinn-choppa/synplify-mcp/actions/runs/42223925259)
passed **12/12** jobs (Windows/Linux × Python 3.11/3.13/3.15.2):
six regular runs of **84 tests** each and six production-only
runs of **2 tests** each.

Tests preserve six tool names, schema validation, strict denial of
unknown agent arguments, official SDK stdio interoperability,
default-disabled synthesis, and synthetic report parsing/comparison.
Production-only tests specifically exercise server import and
MCP protocol calls *without* installing the FastMCP client extra.

Two test-only convenience probes (not production features) were
also executed successfully:

- **Namespace composition:** synthetic Synplify and Verilator
  tool sets can coexist via `mount(namespace=...)` and keep
  separate public names.
- **Privacy-preserving middleware:** an `on_call_tool` hook
  counts calls without persisting tool arguments or results.

Neither validates a real multi-EDA hub, licenses, production
limits or isolation. Co-locating vendor servers in one process
could erode separate workspace, permission, and licensing boundaries.

| Feature | Present need |
| --- | --- |
| Strict rejection of unexpected arguments | Helpful, not sufficient to justify migration |
| FastMCP namespaced mount | Not needed while EDA servers remain independent |
| Middleware | Possibly useful for private metrics/limits later |
| HTTP, proxy, OAuth | Not required for local stdio; wider attack surface |
| Secure EDA execution | Still requires our own trusted-project and OS controls |

## Recommendation

**Keep the official MCP SDK `MCPServer` in production.**
It is already supported by the tested OS/Python matrix and has
a much smaller dependency footprint. FastMCP remains a documented,
technically validated option for a future EDA hub or advanced
middleware requirement, not an automatic standard for
Synplify/Verilator/Questa.

Both experimental PRs should remain drafts and must not be merged
into `main` without explicit owner approval.

Licensed vendor synthesis: **EDA_PASS=NOT_RUN**. A reviewed
cross-platform `uv.lock` remains an open reproducibility task.
