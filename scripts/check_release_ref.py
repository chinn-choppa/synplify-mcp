"""Fail-closed proof that the release tag points to the current main HEAD."""

from __future__ import annotations

import argparse
import re
import tomllib
from pathlib import Path


def check_release_ref(tag: str, tag_commit: str, main_commit: str, version: str) -> None:
    """Reject malformed tags, off-main commits and mismatched versions."""
    if not re.fullmatch(r"0\.1\.0a[1-9][0-9]*", version):
        raise ValueError("Release version is not an allowed 0.1.0 alpha")
    if tag != f"v{version}":
        raise ValueError("Release tag and package version differ")
    if (not re.fullmatch(r"[0-9a-f]{40}", tag_commit)
            or not re.fullmatch(r"[0-9a-f]{40}", main_commit)):
        raise ValueError("Commit IDs must be 40-character lowercase Git SHA-1")
    if tag_commit != main_commit:
        raise ValueError("Release tag is not on the current main HEAD")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--tag-commit", required=True)
    parser.add_argument("--main-commit", required=True)
    args = parser.parse_args()
    config = tomllib.loads(
        (Path(__file__).resolve().parents[1] / "pyproject.toml")
        .read_text(encoding="utf-8")
    )
    try:
        check_release_ref(
            args.tag, args.tag_commit, args.main_commit,
            config["project"]["version"],
        )
    except (ValueError, KeyError) as exc:
        parser.exit(status=1, message=f"RELEASE_REF_DENIED: {exc}\n")
    print(f"RELEASE_REF_ACCEPTED: {args.tag} on main HEAD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
