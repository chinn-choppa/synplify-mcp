# Compatibility

[Русский](COMPATIBILITY.md)

| Component | Intended support | Evidence |
| --- | --- | --- |
| Python | 3.11+ | Public CI tests 3.11 and 3.13 on Windows/Linux; Python 3.15 NOT_RUN |
| MCP | Official SDK 2.3.0, stdio | Native tests included; consult CI for observed result |
| Windows | Local Python and read-only reports | Native MCP CI; Synplify EDA NOT_RUN |
| Linux | Local Python and read-only reports | Native MCP CI; Synplify EDA NOT_RUN |
| Synplify Pro | Version-dependent, to be investigated | Licensed synthesis NOT_RUN |
| Private corporate designs | Only in explicitly authorized environments | Never part of public tests |

The executable is discovered from PATH or SYNPLIFY_MCP_EXECUTABLE, but discovery is not a license or compatibility test. No commercial binary, licensed documentation or private input is shipped.

Preliminary Synplify timing and resource estimates must never be presented as measured post-place-and-route performance; the target FPGA and implementation flow materially affect results.
