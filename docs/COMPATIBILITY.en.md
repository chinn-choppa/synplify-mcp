# Compatibility

[Русский](COMPATIBILITY.md)

| Level | Target | Evidence |
| --- | --- | --- |
| Python | 3.11+ | Integration CI on 3.11, 3.13 and 3.15.2; 6/6 integration CI jobs PASS |
| MCP | Official SDK 2.3.0 | Native in-memory and subprocess stdio tests |
| Windows/Linux | Local report tools and mock executor | Public CI on both OS families |
| Synplify Pro | Release-dependent | NOT_RUN with licensed commercial binary |
| FPGA device families | Device-dependent | Synthetic-only metric grammar |
| Confidential corporate designs | Operator-approved environment only | Not used for public testing |

Discovery or a vendor process exit code does **not** verify commercial compatibility.
Preliminary Synplify timing is not post-place-and-route timing for any FPGA family.

## FastMCP server experiment

The `experiment/fastmcp-v4` branch pins `fastmcp==4.1.6` as the server framework and `mcp==2.3.0` as the independent subprocess stdio protocol client. The original Python/OS CI matrix is reused. This is not licensed Synplify product acceptance. See [experiment rationale and evidence](FASTMCP_EXPERIMENT.en.md).
