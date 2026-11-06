# Synplify Pro report format inventory (M1 research)

[Русский](REPORT_FORMATS.md)

## Scope and legal provenance

This inventory is based on **links** to publicly reachable Synplify Pro
reference documentation from different eras/editions and open-source projects.
We do not redistribute vendor manual text, licensed reports, proprietary source
code or license files. Every fixture is newly invented for this repository
and is not proof of compatibility with a real Synplify version.

| Reference | Observable behavior | Unsupported assumption |
| --- | --- | --- |
| [Synplify Pro 7.0 (2001)](https://www.arl.wustl.edu/projects/fpx/cse535/resources/synpro_ref_1001.pdf) | .srr is a common synthesis/compile log | identical structure in recent releases |
| [Microsemi (2020)](https://ww1.microchip.com/downloads/aemdocuments/documents/FPGA/swdocs/synopsys/fpga_p201903asp1_reference_2019_03.pdf) | compiler, mapper, resources, timing sections | timing present for compile-only runs |
| [Microchip (2021)](https://ww1.microchip.com/downloads/aemdocuments/documents/FPGA/swdocs/synopsys/fpga_reference_R2021_03M_2021_03.pdf) | timing reports and device-specific resources | stable resource naming |
| [Microchip (2024)](https://device.report/m/94056ecebc055a70aebc77378845a5256a55b33b9752377e2478bd8df3ed939e) | text/HTML logs and compiler/mapper summaries | a machine-readable schema contract |
| [Alchitry Labs V2 parser](https://github.com/alchitry/Alchitry-Labs-V2/blob/main/src/main/kotlin/com/alchitry/labs2/project/builders/IceCubeTimingReportParser.kt) | open-source iCEcube2/Synplify timing parser | transferability to every FPGA/vendor |

Documentation may carry proprietary reproduction restrictions. We link to it,
but copy no vendor examples, screenshots, or tables into the synthetic corpus.

## Version-sensitive behavior

- Known diagnostic marker families include `@E:`, `@W:`, `@N:` and
  `@I:`. A message may have a code, source location or neither; none is
  universally guaranteed.
- Paths may be Windows or POSIX paths, including whitespace and parentheses.
- Timing sections may use `START TIMING REPORT` or
  `START OF TIMING REPORT`. Compiler-only output may omit mapping/timing.
- LUTs, registers, memory, DSP, buffers, I/O and primitive names vary with
  architecture; zero must not be fabricated when a section is missing.
- Units such as MHz/ns must be explicit, and Synplify timing is a
  **pre-place-and-route estimate**, never a final implementation result.
- Input encoding can vary: retain source bytes/offsets, recognize UTF-8 and
  UTF-16 BOM, and use an explicitly selected legacy encoding only if needed.
  Do not silently replace malformed bytes.

## Original synthetic test corpus

All files in `tests/fixtures/srr/` are written from scratch, with no
commercial Synplify run. DEMO identifiers and every reported value are
invented, and do not claim a specific product version.

| File | Purpose |
| --- | --- |
| `basic.srr` | legacy-style messages without codes |
| `sections.srr` | named sections, invented message IDs, latch/black-box messages |
| `windows.srr` | CRLF, Windows absolute paths |
| `truncated.srr` | missing timing end marker, incomplete diagnostics |
| `unrecognized.srr` | unknown material that must not be reported as success |
| `empty.srr` | empty report |
| generated in tests | malformed encodings, oversized inputs, symlink/path denial |

The fixture patterns are **hypotheses** for parser testing, not a
vendor-certified grammar or verified compatibility matrix.

## Next steps

#4 will provide bounded read-only .srr parsing with source-line evidence,
explicit parse-health states and safe workspace restriction. #5 will handle
version-aware resource and timing normalization separately. Commercial
product acceptance and exact Synplify version support remain NOT_RUN.

## Further #5 fixtures

The [metric normalization contract](METRICS.en.md) introduces five original synthetic `metrics_*.srr` fixtures covering explicit counts, multi-clock timing, unknown units, contradictory values and missing constraints. No real Synplify release is claimed supported.
