"""Макетная приёмка разрешённого синтеза; коммерческий EDA не требуется."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from synplify_mcp.approved_run import (
    _execute_batch, run_approved_project, MAX_LOG_BYTES,
)

_MOCK_SUCCESS = {"state": "PROCESS_EXIT_ZERO_UNVERIFIED", "executed": True,
                 "eda_validation": "NOT_VERIFIED", "exit_code": 0}


class ApprovedProjectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "workspace"
        self.root.mkdir()
        self.sources = self.root / "sources"
        self.sources.mkdir()
        self.artifacts = self.root / "artifacts"
        self.artifacts.mkdir()
        self.project = self.sources / "demo.prj"
        self.project.write_text(
            "# Original synthetic fixture: no proprietary project data.\n"
            "# Do not execute as vendor synthesis in public CI.\n",
            encoding="utf-8",
        )
        self.manifest = Path(self.tmp.name) / "operator-manifest.json"
        self.write_manifest()
        self.config = {
            "SYNPLIFY_MCP_WORKSPACE": str(self.root),
            "SYNPLIFY_MCP_RUN_MANIFEST": str(self.manifest),
            "SYNPLIFY_MCP_EXECUTABLE": str(Path(sys.executable).resolve()),
            "SYNPLIFY_MCP_ENABLE_SYNTHESIS": "1",
        }
        self.env = patch.dict(os.environ, self.config)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.calls = []

    def write_manifest(self, *, project="sources/demo.prj",
                       artifacts="artifacts", sha256=None):
        content = {
            "schema": 1,
            "projects": {
                "demo": {
                    "project": project,
                    "sha256": sha256 or hashlib.sha256(self.project.read_bytes()).hexdigest(),
                    "artifacts": artifacts,
                }
            }
        }
        self.manifest.write_text(json.dumps(content), encoding="utf-8")

    def fake_executor(self, argv, cwd, timeout_seconds, log_path):
        self.calls.append((argv, cwd, timeout_seconds, log_path))
        return dict(_MOCK_SUCCESS)

    def run_mock(self, project_id="demo", confirm=True, timeout=10):
        return run_approved_project(project_id, confirm, timeout,
                                    executor=self.fake_executor)

    def test_explicit_opt_in_approved_sha_and_fixed_batch_only(self):
        result = self.run_mock()
        self.assertEqual(result["state"], "PROCESS_EXIT_ZERO_UNVERIFIED")
        self.assertTrue(result["executed"])
        self.assertEqual(result["eda_validation"], "NOT_VERIFIED")
        self.assertEqual(result["project_id"], "demo")
        self.assertEqual(result["project_sha256"],
                         hashlib.sha256(self.project.read_bytes()).hexdigest())
        self.assertEqual(result["invocation"], "APPROVED_PROJECT_BATCH")
        self.assertEqual(len(self.calls), 1)
        argv, cwd, timeout, log = self.calls[0]
        self.assertEqual(argv, (str(Path(sys.executable).resolve()), "-batch",
                                str(self.project.resolve())))
        self.assertEqual(timeout, 10)
        self.assertEqual(cwd.parent.resolve(), self.artifacts.resolve())
        self.assertTrue(cwd.name.startswith("synthesis-"))
        self.assertEqual(log, cwd / "stdout.log")
        self.assertNotIn(str(self.root), str(result))
        self.assertNotIn(str(Path(sys.executable).resolve()), str(result))

    def test_denied_before_any_process_side_effect(self):
        cases = [
            ("demo", False, 10, "CONFIRMATION_REQUIRED"),
            ("../evil", True, 10, "INVALID_PROJECT_ID"),
            ("demo", True, 0, "INVALID_TIMEOUT"),
            ("demo", True, 121, "INVALID_TIMEOUT"),
            ("demo", True, True, "INVALID_TIMEOUT"),
            ("absent", True, 10, "PROJECT_NOT_APPROVED"),
        ]
        for project_id, confirm, timeout, expected in cases:
            with self.subTest(expected=expected):
                r = self.run_mock(project_id, confirm, timeout)
                self.assertEqual(r["state"], expected)
                self.assertFalse(r["executed"])
        self.assertFalse(self.calls)
        self.assertEqual(list(self.artifacts.iterdir()), [])

    def test_disabled_and_missing_executable(self):
        with patch.dict(os.environ, {"SYNPLIFY_MCP_ENABLE_SYNTHESIS": "0"}):
            self.assertEqual(self.run_mock()["state"], "DISABLED")
        with patch.dict(os.environ, {"SYNPLIFY_MCP_EXECUTABLE": ""}):
            self.assertEqual(self.run_mock()["state"], "NOT_INSTALLED")
        with patch.dict(os.environ, {"SYNPLIFY_MCP_EXECUTABLE": "relative"}):
            self.assertEqual(self.run_mock()["state"], "INVALID_EXECUTABLE")
        self.assertFalse(self.calls)

    @unittest.skipUnless(os.name == "nt", "Windows-only executable safety")
    def test_windows_script_launchers_rejected(self):
        for suffix in (".bat", ".cmd", ".ps1"):
            with self.subTest(suffix=suffix):
                script = self.root / ("untrusted" + suffix)
                script.write_text("echo malicious", encoding="utf-8")
                with patch.dict(os.environ, {"SYNPLIFY_MCP_EXECUTABLE": str(script)}):
                    result = self.run_mock()
                self.assertEqual(result["state"], "INVALID_EXECUTABLE")
                self.assertFalse(result["executed"])
                self.assertEqual(self.calls, [])

    def test_missing_operator_manifest_is_invalid_not_launch_error(self):
        with patch.dict(os.environ, {
            "SYNPLIFY_MCP_RUN_MANIFEST": str(self.root / "absent-manifest.json"),
        }):
            result = self.run_mock()
        self.assertEqual(result["state"], "INVALID_MANIFEST")
        self.assertFalse(result["executed"])
        self.assertFalse(self.calls)

    def test_agent_editable_manifest_in_workspace_is_denied(self):
        # A project root exposed to a coding agent must not contain the
        # operator's allowlist; otherwise that agent can reauthorize itself.
        inside = self.root / "editable-manifest.json"
        inside.write_bytes(self.manifest.read_bytes())
        with patch.dict(os.environ, {"SYNPLIFY_MCP_RUN_MANIFEST": str(inside)}):
            outcome = self.run_mock()
        self.assertEqual(outcome["state"], "INVALID_MANIFEST")
        self.assertFalse(outcome["executed"])
        self.assertFalse(self.calls)

    def test_hardlinked_operator_manifest_rejected_without_launch(self):
        hardlink = self.root / "linked-manifest.json"
        try:
            os.link(self.manifest, hardlink)
        except (OSError, NotImplementedError):
            self.skipTest("Hard links unavailable on this filesystem")
        result = self.run_mock()
        self.assertEqual(result["state"], "INVALID_MANIFEST")
        self.assertFalse(result["executed"])
        self.assertFalse(self.calls)

    def test_hardlinked_project_rejected_without_launch(self):
        link = self.root / "project-hardlink.prj"
        try:
            os.link(self.project, link)
        except (OSError, NotImplementedError):
            self.skipTest("Hard links unavailable on this filesystem")
        result = self.run_mock()
        self.assertEqual(result["state"], "INVALID_PROJECT")
        self.assertFalse(result["executed"])
        self.assertFalse(self.calls)

    def test_real_vendor_execution_blocked_even_when_enabled(self):
        result = run_approved_project("demo", True, 10)
        self.assertEqual(result["state"], "VENDOR_EXECUTION_NOT_VALIDATED")
        self.assertFalse(result["executed"])
        self.assertFalse(self.calls)
        self.assertEqual(list(self.artifacts.iterdir()), [])

    def test_symlinked_operator_manifest_rejected_without_launch(self):
        link = self.root / "manifest-link.json"
        try:
            link.symlink_to(self.manifest)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable on this OS")
        with patch.dict(os.environ, {"SYNPLIFY_MCP_RUN_MANIFEST": str(link)}):
            result = self.run_mock()
        self.assertEqual(result["state"], "INVALID_MANIFEST")
        self.assertFalse(result["executed"])
        self.assertEqual(self.calls, [])

    def test_symlinked_artifact_directory_rejected_without_launch(self):
        link = self.root / "linked-artifacts"
        try:
            link.symlink_to(self.artifacts, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable on this OS")
        self.write_manifest(artifacts="linked-artifacts")
        result = self.run_mock()
        self.assertEqual(result["state"], "SYMLINK_DENIED")
        self.assertFalse(result["executed"])
        self.assertEqual(self.calls, [])

    def test_untrusted_executable_symlink_rejected_without_launch(self):
        link = self.root / ("untrusted.exe" if os.name == "nt" else "untrusted")
        try:
            link.symlink_to(Path(sys.executable).resolve())
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable on this OS")
        with patch.dict(os.environ, {"SYNPLIFY_MCP_EXECUTABLE": str(link)}):
            result = self.run_mock()
        self.assertEqual(result["state"], "INVALID_EXECUTABLE")
        self.assertFalse(result["executed"])
        self.assertEqual(self.calls, [])

    def test_project_modification_and_manifest_ambiguity(self):
        self.project.write_text("modified", encoding="utf-8")
        self.assertEqual(self.run_mock()["state"], "PROJECT_CHANGED")
        self.write_manifest(sha256="0" * 64)
        self.assertEqual(self.run_mock()["state"], "PROJECT_CHANGED")
        self.manifest.write_text('{"schema":1,"schema":1,"projects":{}}',
                                 encoding="utf-8")
        self.assertEqual(self.run_mock()["state"], "INVALID_MANIFEST")
        self.assertFalse(self.calls)

    def test_path_traversal_extension_and_symlink(self):
        for path in ("../escape.prj", "/etc/secret.prj", r"C:\secret.prj",
                     "sources/demo.tcl"):
            self.write_manifest(project=path)
            with self.subTest(path=path):
                self.assertEqual(self.run_mock()["state"], "INVALID_PATH")
        self.write_manifest(artifacts="../outside")
        self.assertEqual(self.run_mock()["state"], "INVALID_PATH")
        self.write_manifest()
        link = self.sources / "linked.prj"
        try:
            link.symlink_to(self.project)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable")
        self.write_manifest(project="sources/linked.prj")
        self.assertEqual(self.run_mock()["state"], "SYMLINK_DENIED")
        self.assertFalse(self.calls)

    def test_invalid_manifest_and_unconfigured_workspace(self):
        self.manifest.write_bytes(b" " * 65_537)
        self.assertEqual(self.run_mock()["state"], "MANIFEST_TOO_LARGE")
        self.write_manifest()
        with patch.dict(os.environ, {"SYNPLIFY_MCP_WORKSPACE": "relative"}):
            self.assertEqual(self.run_mock()["state"], "INVALID_WORKSPACE")
        with patch.dict(os.environ, {"SYNPLIFY_MCP_RUN_MANIFEST": ""}):
            self.assertEqual(self.run_mock()["state"], "NOT_CONFIGURED")

    def test_mock_license_failed_timeout_and_fail_status_are_distinct(self):
        for outcome in ("LICENSE_UNAVAILABLE", "TIMEOUT", "TOOL_FAILED", "LOG_LIMIT"):
            def fake(argv, cwd, timeout, log):
                return {"state": outcome, "executed": True,
                        "eda_validation": "NOT_VERIFIED", "exit_code": 1}
            with self.subTest(state=outcome):
                r = run_approved_project("demo", True, 2, executor=fake)
                self.assertEqual(r["state"], outcome)
                self.assertTrue(r["executed"])
                self.assertEqual(r["eda_validation"], "NOT_VERIFIED")

    def test_unsafe_manifest_fields_rejected(self):
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["projects"]["demo"]["tcl"] = "exec something"
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(self.run_mock()["state"], "INVALID_MANIFEST")
        self.assertFalse(self.calls)


class ProcessRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def run_python(self, script, *, timeout=5):
        name = f"log-{len(list(self.root.iterdir()))}.txt"
        file = self.root / name
        result = _execute_batch(
            (sys.executable, "-c", script), self.root, timeout, file
        )
        return result, file

    def test_real_subprocess_exit_zero_without_vendor_pass_claim(self):
        result, path = self.run_python("print('mock process complete')")
        self.assertEqual(result["state"], "PROCESS_EXIT_ZERO_UNVERIFIED")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["eda_validation"], "NOT_VERIFIED")
        self.assertTrue(result["executed"])
        self.assertEqual(result["captured_log_sha256"],
                         hashlib.sha256(path.read_bytes()).hexdigest())

    def test_nonzero_exit_and_license_signal(self):
        outcome, _ = self.run_python("import sys; print('compile failed');sys.exit(4)")
        self.assertEqual(outcome["state"], "TOOL_FAILED")
        self.assertEqual(outcome["exit_code"], 4)
        license, log = self.run_python(
            "import sys;print('license checkout failed');sys.exit(3)"
        )
        self.assertEqual(license["state"], "LICENSE_UNAVAILABLE")
        self.assertEqual(license["exit_code"], 3)
        self.assertNotIn("license checkout failed", str(license))
        self.assertIn(b"license checkout failed", log.read_bytes())

    @unittest.skipUnless(os.name == "nt", "Windows-only taskkill location")
    def test_taskkill_uses_windows_system_directory_not_environment(self):
        from synplify_mcp.approved_run import _terminate_tree

        class FakeProcess:
            pid = 12345

            def wait(self, timeout=None):
                return 0

            def poll(self):
                return 0

        # The agent's inherited environment must not redirect an auxiliary
        # cancellation binary to an executable of its choice.
        with patch.dict(os.environ, {"SystemRoot": r"C:\attacker-controlled"}):
            with patch("synplify_mcp.approved_run.subprocess.run") as call:
                _terminate_tree(FakeProcess())
        self.assertTrue(call.called)
        argv = call.call_args.args[0]
        self.assertEqual(Path(argv[0]).name.lower(), "taskkill.exe")
        self.assertNotIn("attacker-controlled", str(argv[0]).lower())
        self.assertEqual(argv[1:4], ["/F", "/T", "/PID"])

    def test_timeout_terminates_mock_process(self):
        r, _ = self.run_python("import time;time.sleep(5)", timeout=1)
        self.assertEqual(r["state"], "TIMEOUT")
        self.assertTrue(r["executed"])

    def test_stdout_is_capped_and_overflow_terminates(self):
        r, path = self.run_python(
            "import sys;sys.stdout.write('X'*300000);sys.stdout.flush()"
        )
        self.assertEqual(r["state"], "LOG_LIMIT")
        self.assertTrue(r["log_truncated"])
        self.assertLessEqual(path.stat().st_size, MAX_LOG_BYTES)
        self.assertLessEqual(r["captured_log_bytes"], MAX_LOG_BYTES)


if __name__ == "__main__":
    unittest.main()
