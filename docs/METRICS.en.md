# Synplify synthesis metrics: conservative normalization (#5)

[Русский](METRICS.md)

## Evidence rule

`parse_srr` exposes `resources`, `timing` and `context` **only**
from explicitly marked sections, labelled fields and units.
No numbers are scraped from arbitrary diagnostics or prose.
The current grammar is a small **synthetic-only prototype**;
no commercial Synplify Pro version has been tested.

## Resource mapping

Within `Resource Usage Report`, only the following patterns are
accepted:

- Explicit `Total LUTs`, `Register bits not including I/Os`,
  `I/O ports`, `Block RAMs` with an integer count;
- `Resource Used Available` tables with numeric counts and raw names
  of device-specific primitives.

`resources.state` is one of `PARSED`, `PARTIAL`, `ABSENT`,
`AMBIGUOUS` or `UNSUPPORTED`. Entries retain their original names
(no vendor-agnostic aliasing), `used/available` quantities with
`unit="count"` and `KNOWN/UNKNOWN` status, and `evidence` with
original text, source section, physical report line and byte offset.

Do not equate LUT, logic cells, FF, BRAM or vendor primitives or add
unrelated categories without verified device mapping. Missing capacity
or counts are `null`, not zero. Duplicates are marked `AMBIGUOUS`
and all observed evidence remains available.

## Preliminary timing

Only a `START [OF] TIMING REPORT` / `Performance Summary` section
with explicit `ns` or `MHz` headers plus `Slack (ns)` is accepted.
The result contains separate records in `timing.clocks` for each
clock domain rather than selecting an arbitrary main clock.

Each clock includes `clock`, `requested`, `estimated`, `slack`,
`constraints`, `evidence` and `header_evidence`. Unsupported units,
missing values, malformed tables and unterminated sections are not
silently mapped to zero. Only the literal `Unconstrained` is reported
as `constraints="UNCONSTRAINED"`; unproven cases are `UNKNOWN`.
Duplicate clock names yield `timing.state="AMBIGUOUS"`.

`timing.kind="SYNTHESIS_ESTIMATE"` and
`timing.implementation_timing=false`: these are **pre-place-and-route
estimates**, not measured implementation timing from ISE/Vivado,
Microchip, Lattice or other vendor flows. For legacy Virtex-4 designs
in particular, never equate Synplify estimates with post-route
WNS or maximum frequency. A positive estimate does not prove EDA
success: `synthesis_status="UNKNOWN"` until a vendor run is verified.

## Context and provenance

`context.tool_version` and `context.device` are extracted only
from explicit `Synplify Pro Version:` and `Target Device:` lines.
Each carries `state`, `value` and `evidence`. If absent or
contradictory, `value=null`. Invented device/version labels in
fixtures must never be described as verified compatibility.

Limits: at most 64 resource rows and 32 clock domains; limits and
partial data are recorded in `issues` and state. Malformed input
encoding fails at the original report-reading layer.

## Original synthetic fixtures

- `metrics_frequency.srr`: labelled resources and two MHz clocks;
- `metrics_period.srr`: resource table and two ns clocks;
- `metrics_unknown.srr`: N/A, missing data and Unconstrained;
- `metrics_ambiguous.srr`: conflicting versions, devices, metrics;
- `metrics_unknown_units.srr`: unrecognized units/sections.

All inputs were written from scratch with **MOCK/DEMO** values; they
were not produced by Synplify and do not certify support for any vendor
release or FPGA family. Extend the grammar only with public,
legally shareable evidence and documented acceptance of a specific
version/device.

## Future work

#7 should compare builds only when tool, device, constraints, resource
identity and units can be proven compatible; otherwise report
UNKNOWN/INCOMPATIBLE rather than fabricating deltas.
#6 separately governs explicitly authorized synthesis execution and
must never accept arbitrary shell/Tcl.

## Conservative alpha boundaries

All tool/device identity declarations are checked for conflicts even though returned evidence is capped at eight rows. Values over 128 characters are `AMBIGUOUS`, never compared by prefix. Each new timing section resets completion state. A resource section ending at EOF without an explicit section transition is `PARTIAL`, blocking numerical resource comparison.
