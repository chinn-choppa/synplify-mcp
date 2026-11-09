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

## Alpha `0.1.0a1` candidate

`uv sync --locked` runs on Windows/Linux with Python 3.11/3.13/3.15. Both wheel and sdist are installed in fresh environments on Windows/Linux Python 3.13 and tested with the real MCP stdio client. This validates protocol and synthetic parsing only; licensed Synplify Pro, devices and real synthesis are `NOT_RUN`.
