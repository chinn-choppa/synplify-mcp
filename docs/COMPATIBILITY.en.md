# Compatibility

[Русский](COMPATIBILITY.md)

| Level | Target | Evidence |
| --- | --- | --- |
| Python | 3.11+ | Integration CI on 3.11, 3.13 and 3.15; confirm results before claiming PASS |
| MCP | Official SDK 2.3.0 | Native in-memory and subprocess stdio tests |
| Windows/Linux | Local report tools and mock executor | Public CI on both OS families |
| Synplify Pro | Release-dependent | NOT_RUN with licensed commercial binary |
| FPGA device families | Device-dependent | Synthetic-only metric grammar |
| Confidential corporate designs | Operator-approved environment only | Not used for public testing |

Discovery or a vendor process exit code does **not** verify commercial compatibility.
Preliminary Synplify timing is not post-place-and-route timing for any FPGA family.
