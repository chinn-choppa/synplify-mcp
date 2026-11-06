# Changelog

[Русский](CHANGELOG.md)

## [Unreleased]

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

- Experimental FastMCP 4.1.6 server adapter; EDA logic unchanged and official SDK client still validates stdio. Not merged; see [experiment](docs/FASTMCP_EXPERIMENT.en.md).
