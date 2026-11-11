"""No network: verify tag/main provenance cannot be bypassed."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_release_ref.py"
spec = importlib.util.spec_from_file_location("check_release_ref", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

MAIN_SHA = "a" * 40
OTHER_SHA = "b" * 40


class ReleaseReferenceTests(unittest.TestCase):
    def test_matching_alpha_tag_on_main(self) -> None:
        module.check_release_ref("v0.1.0a1", MAIN_SHA, MAIN_SHA, "0.1.0a1")

    def test_reject_tag_pointing_to_feature_branch(self) -> None:
        with self.assertRaisesRegex(ValueError, "current main HEAD"):
            module.check_release_ref("v0.1.0a1", OTHER_SHA, MAIN_SHA, "0.1.0a1")

    def test_reject_tag_version_mismatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "tag and package"):
            module.check_release_ref("v0.1.0a2", MAIN_SHA, MAIN_SHA, "0.1.0a1")

    def test_reject_non_alpha_tag_and_bad_sha(self) -> None:
        for version in ("0.1.0", "0.1.0a0", "0.1.0rc1", "0.1.0a1+local"):
            with self.subTest(version=version):
                with self.assertRaises(ValueError):
                    module.check_release_ref(f"v{version}", MAIN_SHA, MAIN_SHA, version)
        with self.assertRaisesRegex(ValueError, "SHA-1"):
            module.check_release_ref("v0.1.0a1", "abc", MAIN_SHA, "0.1.0a1")

    def test_ci_builds_and_installs_on_all_supported_targets(self) -> None:
        ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("os: [ubuntu-latest, windows-latest]", ci)
        self.assertIn("python-version: ['3.11', '3.13', '3.15']", ci)
        self.assertIn("uv sync --locked --python", ci)
        self.assertIn("uv build", ci)
        self.assertIn("python scripts/verify_release_artifacts.py", ci)
        self.assertNotIn("  distribution:", ci)

    def test_release_workflow_fails_closed_before_publication(self) -> None:
        workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        self.assertIn("fetch-depth: 0", workflow)
        self.assertIn("git fetch --no-tags origin main", workflow)
        self.assertIn("python scripts/check_release_ref.py", workflow)
        self.assertIn('$(git rev-parse HEAD^{commit})', workflow)
        self.assertIn('$(git rev-parse FETCH_HEAD^{commit})', workflow)
        self.assertLess(workflow.index("python scripts/check_release_ref.py"),
                        workflow.index("gh release create"))
        self.assertIn("--verify-tag --prerelease", workflow)
        self.assertNotIn("uv publish", workflow)
        self.assertNotIn("twine upload", workflow)
        self.assertNotIn("pypa/gh-action-pypi-publish", workflow)


if __name__ == "__main__":
    unittest.main()
