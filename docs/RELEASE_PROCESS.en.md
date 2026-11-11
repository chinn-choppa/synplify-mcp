# Experimental release procedure

[Русский](RELEASE_PROCESS.md)

## Prerequisites

1. Review the release PR and include integration #15 and security fix #14 **once**. Do not import experimental FastMCP #16/#17.
2. Confirm green CI on the final commit: Windows/Linux × Python 3.11/3.13/3.15, plus separately installed wheel/sdist.
3. Check `uv.lock`, `uv sync --locked`, `uv build`, and `python scripts/verify_release_artifacts.py`.
4. Verify GitHub Private Vulnerability Reporting through owner permissions. Do not package proprietary EDA data, licenses, RTL or secrets.
5. **After explicit owner approval**, merge into `main` and tag the verified commit as `v0.1.0a1`. No tag exists yet.

## Automation

`.github/workflows/release.yml` is triggered **only** for `v0.1.0a*` tags. It checks tag/package version, lockfile, tests and installed wheel/sdist, then creates a **GitHub prerelease** with both archives. There is **no PyPI publishing** and `--verify-tag` forbids implicit tag creation.

## Limits

The alpha validates MCP and synthetic report handling, not licensed Synplify. `run_approved_synthesis` remains disabled by default; approved `.prj` files may execute Tcl. Real vendor versions and device acceptance are required for a stable release (**EDA_PASS=NOT_RUN**).

**Tag provenance:** publishing additionally requires a tag matching `pyproject.toml` that targets **the exact current `origin/main` HEAD**. Off-main tags and stale main commits are denied. Merge the reviewed PR first, then create the tag on current main. If main advances before the release workflow starts, this deliberately fails closed.

**Alpha 0.1.0a1 never starts vendor EDA**: even with the enable flag the MCP tool refuses execution. Internal synthetic runner tests do not authorize real vendor launches; enabling requires a separate security and licensed acceptance milestone.
