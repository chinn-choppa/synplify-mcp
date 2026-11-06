# Synplify MCP integration review

[Русский](INTEGRATION_REVIEW.md)

## Scope

The `integration/mvp-review-2026-11-06` branch assembles code from
[#8](https://github.com/chinn-choppa/synplify-mcp/pull/8) (MCP/RU/EN),
[#9](https://github.com/chinn-choppa/synplify-mcp/pull/9) (formats),
[#10](https://github.com/chinn-choppa/synplify-mcp/pull/10) (parser),
[#11](https://github.com/chinn-choppa/synplify-mcp/pull/11) (metrics),
[#12](https://github.com/chinn-choppa/synplify-mcp/pull/12) (comparison),
and [#13](https://github.com/chinn-choppa/synplify-mcp/pull/13)
(approved execution). **No merge into main has taken place.**
This is review readiness, not a release or vendor product acceptance.

## Reconciled integration

- All six tools coexist in `server.py`, including report comparison
  and approved-project execution.
- `server_info` separates implementation availability
  (`eda_execution_supported=true`), operator enablement
  (`eda_execution_enabled`) and actual vendor validation
  (`eda_execution_validated=false`).
- Five read-only operations declare `read_only_hint=true` while
  the executor declares `read_only_hint=false`, `destructive_hint=true`.
  Annotations are only client hints, not permission checks.
- Both native MCP transports, offline tool stubs, bilingual navigation
  and six-tool enumeration are tested together, not only in isolation.
- Main English/Russian documents, cross-links and behavioral contracts
  are reconciled with the experimental code.

## CI evidence

[Integration run 42202788345](https://github.com/chinn-choppa/synplify-mcp/actions/runs/42202788345)
and preceding
[run 42202479309](https://github.com/chinn-choppa/synplify-mcp/actions/runs/42202479309):
**6/6 jobs passed** on Windows and Linux, Python 3.11, 3.13 and
**3.15.2**. Each job ran 79 tests for synthetic reports, path
security, mocked execution, timeouts and bounded logging, native
in-memory MCP and subprocess `stdio` plus reciprocal documentation.

`MCP_TOOL_PASS` is verified in this public matrix.
Synthetic report `PARSED` is verified only against original fixtures.
Licensed Synplify `EDA_PASS` remains **NOT_RUN**, with no verified
vendor release, license or target device family.

## Remaining risks and prerequisites

1. **High trust boundary:** the .prj SHA-256 covers only the project
   file, not included Tcl/RTL/constraint dependencies. A .prj can
   execute Tcl even with fixed `-batch` argv and `shell=False`.
   Protect dependencies and execute under a restricted operator OS
   account; the runner is **not an OS sandbox**.
2. Reports can contain private paths and signal names. Local stdio
   cannot prevent the MCP client from forwarding output externally.
3. Process-tree termination is best effort; real vendor cancellation,
   hangs and license failures have not been tested.
4. Version-specific .srr grammars and device names remain unverified.
   No product compatibility claim follows from synthetic fixtures.
5. Synplify timing is preliminary, never post-route; numeric timing
   deltas remain withheld without independently verified complete
   constraint equivalence.
6. A checked-in `uv.lock` and a separate dependency/trusted-binary
   review are recommended before stable release. The current CI
   pins MCP 2.3.0 and uv 0.13.0 but can resolve newer transitive
   package versions.

## After explicit owner approval

Preferred: review the integration PR, merge **only that PR** after
approval and then close superseded #8–#13 without merging them again.
Alternative: rebase and merge #8 → #9 → #10 → #11, then #12 and #13,
re-running shared CI after resolving conflicts.
Do not mix these approaches.

**No PR has been merged into main and no issue has been closed.**
