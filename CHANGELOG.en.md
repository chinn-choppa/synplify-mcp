# Changelog

[Русский](CHANGELOG.md)

## [Unreleased]

### 0.1.0a1 candidate (not yet published)
- Six MCP operations; reject Windows script wrappers and agent-editable approval manifests.
- Universal uv.lock, locked matrix CI and fresh wheel/sdist stdio integration tests.
- Tag-gated GitHub prerelease, with commercial EDA validation remaining NOT_RUN.

### Added
- Native MCP SDK 2.3.0 tests using in-memory and local stdio clients (#2)
- Original synthetic Synplify .srr format research and fixtures (#3)
- Bounded .srr report parsing with diagnostics and line/byte provenance (#4)
- Conservative resource and preliminary timing metadata (#5)
- Operator-gated approved .prj batch runner with mock-only public tests (#6)
- Report comparison with source evidence and compatibility gates (#7)
- Reciprocal full Russian and English documentation, Python 3.15 test matrix

### Not verified
- No licensed Synplify product/version or production FPGA design has been run
- Process exit code zero never establishes verified vendor synthesis success
