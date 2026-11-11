# Roadmap

[Русский](ROADMAP.md)

## Prototype milestones

- [x] #2 Native MCP protocol and reciprocal bilingual documentation
- [x] #3 Report-format inventory and original synthetic fixture corpus
- [x] #4 Safe .srr reader and structured diagnostics with evidence
- [x] #5 Device-specific resource names and preliminary multi-clock timing
- [x] #6 Mock-tested approved synthesis runner; **real vendor MCP execution is blocked in alpha**
- [x] #7 Evidence-gated comparison of report snapshots

These checks mark prototype implementation, **not** vendor compatibility or merge approval.

## Outstanding acceptance

- [x] Green combined Windows/Linux CI including Python 3.15
- [ ] Authorized commercial Synplify integration for tested releases and devices
- [ ] Validate license behavior, output paths, child-process cancellation and formats
- [x] Document .prj/Tcl/includes trust limits and restrict the approval manifest and Windows launchers (no OS sandbox provided)
- [ ] Prepare supported-versions/security policy for public release

Never present preliminary timing as implementation timing.

## Alpha release candidate

- [x] Stage `0.1.0a1` with universal `uv.lock`.
- [x] Verify fresh wheel/sdist installations through CI.
- [x] Prepare a tag-gated GitHub prerelease workflow.
- [ ] Complete release PR review and obtain merge approval.
- [ ] Check GitHub Private Vulnerability Reporting through owner permissions.
- [ ] After approval create `v0.1.0a1` and publish the prerelease.

A stable release still needs separate licensed Synplify and real-device acceptance.

## Before enabling actual vendor EDA execution

- [ ] Enforce OS-level restrictions for Tcl and descendant processes (identity, memory, CPU, workspace).
- [ ] Protect operator approval data and inputs against agent writes and check/use races.
- [ ] Enforce human authorization outside caller-controlled MCP arguments.
- [ ] Complete licensed vendor acceptance and a separate security review before enabling execution.
