# Comparing synthesis report snapshots (.srr)

[Русский](COMPARE.md)

## MCP operation

`compare_srr_reports(baseline_path, candidate_path, encoding="auto")`
compares two **operator-authorized local** `.srr` files under
`SYNPLIFY_MCP_WORKSPACE`. The operation never runs Synplify, executes
shell/Tcl, writes RTL/artifacts, or transmits data to outside services.

Both files undergo the existing `parse_srr` checks for bounded size
(1 MiB per report), encoding, symlink escape and workspace traversal.
SHA-256 binds source evidence to each file. `baseline`/`candidate`
are input reports, **not** Git revisions independently verified
by the MCP server.

## Compatibility gates

The result includes `state`, `context`, `diagnostics`,
`resources`, `timing`, `baseline` and `candidate`.

- Numeric resource deltas require matching, explicitly `KNOWN`
  tool versions and target devices. Missing metadata yields
  `UNVERIFIED`; mismatches yield `INCOMPATIBLE` without numeric
  comparisons.
- Both resource sections must be `PARSED`, with exact original
  primitive names and `count` units. Missing resource identities
  or different reported capacity are not interpreted as a numeric
  change: **missing is not zero**.
- Diagnostic differences are based on severity, code, category, HDL
  location and message text. Report-line provenance is retained.
  Truncated or unrecognized reports use `PARTIAL_OBSERVATION` and
  cannot prove the absence of other warnings/errors.
- Timing requires matching clock sets, known requested values and
  matching units. Otherwise report `UNKNOWN_CONSTRAINTS`,
  `INCOMPATIBLE_CLOCK_REQUESTS`, or `INCOMPATIBLE_CLOCK_SET`.
  Even identical requested clock periods do **not** establish
  equivalence of complete SDC/FDC files, false/multicycle paths,
  clock groups and I/O constraints. Therefore observed
  `estimated`/`slack` values are reported with evidence, while
  numeric `estimated_delta`/`slack_delta` are **null**. The state
  is `UNVERIFIED_FULL_CONSTRAINTS`: do not claim improvement.
- Timing is a `SYNTHESIS_ESTIMATE` and
  `implementation_timing=false`, never post-route timing, including
  legacy Virtex-4 and other Xilinx families.

`synthesis_status="UNKNOWN"` and `executed=false` always hold.
`IDENTICAL_BYTES` means matching file bytes, **not** `EDA_PASS`.

## Bounded provenance and reproducibility

The output contains short excerpts (maximum 256 characters each),
report lines and byte offsets tied to the report SHA-256 — never whole
logs. Lists of changes are capped at 16 entries per category.
An input failure yields `INPUT_ERROR`, the selected side and a safe
machine-readable `error_code`.

The tests use entirely original synthetic files
`compare_base.srr` and `compare_changed.srr`; no licensed Synplify
version or FPGA device has been verified (`NOT_RUN`). The MCP server
cannot independently prove that input reports correspond to particular
Git revisions.

## MCP request

```json
{
  "baseline_path": "reports/before.srr",
  "candidate_path": "reports/after.srr",
  "encoding": "auto"
}
```

See the [safe parser guide](SRR_PARSER.en.md) for workspace setup,
encoding and client-side confidentiality considerations.
