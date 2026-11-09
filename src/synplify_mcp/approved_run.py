"""Опциональный запуск только заранее утверждённых оператором проектов Synplify.

Проект .prj может содержать исполняемый Tcl. Отсюда обязательны
операторский manifest, SHA256 проекта, отдельный enable-флаг и доверенный
каталог. Это не OS sandbox для враждебных EDA-проектов.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import stat
import subprocess
import tempfile
import threading
import time
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Callable

ENABLE_ENV = "SYNPLIFY_MCP_ENABLE_SYNTHESIS"
MANIFEST_ENV = "SYNPLIFY_MCP_RUN_MANIFEST"
EXECUTABLE_ENV = "SYNPLIFY_MCP_EXECUTABLE"
WORKSPACE_ENV = "SYNPLIFY_MCP_WORKSPACE"

MAX_MANIFEST_BYTES = 65_536
MAX_PROJECT_BYTES = 262_144
MAX_LOG_BYTES = 65_536
MAX_TIMEOUT_SECONDS = 120
_PROJECT_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
_SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")
_LICENSE_PROBLEM = re.compile(
    rb"(?:license[ \t_-]*(?:checkout|check[ -]?out|acquisition|request)"
    rb"[^.\r\n]{0,100}(?:fail|denied|unavailable|error))|"
    rb"(?:no[ \t]+valid[ \t]+license)|"
    rb"(?:license[ \t_-]*(?:unavailable|denied|expired|not[ \t]+found))",
    flags=re.IGNORECASE,
)


def _result(state: str, *, executed: bool = False, **data: Any) -> dict[str, Any]:
    return {"state": state, "executed": executed, "eda_validation": "NOT_VERIFIED", **data}


def _duplicate_rejecting_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def _approved_relative(root: Path, relative: str, *, suffix: str | None) -> Path:
    if (not isinstance(relative, str) or not relative or len(relative) > 256
            or "\x00" in relative or "\\" in relative or ":" in relative
            or PureWindowsPath(relative).root
            or PurePosixPath(relative).is_absolute()):
        raise ValueError("INVALID_PATH")
    path = PurePosixPath(relative)
    if ".." in path.parts or not path.parts:
        raise ValueError("INVALID_PATH")
    if suffix is not None and path.suffix.lower() != suffix:
        raise ValueError("INVALID_PATH")
    cursor = root
    for component in path.parts:
        cursor = cursor / component
        if cursor.is_symlink() or getattr(cursor, "is_junction", lambda: False)():
            raise ValueError("SYMLINK_DENIED")
    try:
        target = cursor.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError("PATH_NOT_FOUND") from exc
    if not target.is_relative_to(root):
        raise ValueError("OUTSIDE_WORKSPACE")
    return target


def _read_manifest(path: Path) -> dict[str, Any]:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError("INVALID_MANIFEST")
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("MANIFEST_TOO_LARGE")
    with path.open("rb") as stream:
        data = stream.read(MAX_MANIFEST_BYTES + 1)
    if len(data) > MAX_MANIFEST_BYTES:
        raise ValueError("MANIFEST_TOO_LARGE")
    try:
        manifest = json.loads(data.decode("utf-8"), object_pairs_hook=_duplicate_rejecting_object)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("INVALID_MANIFEST") from exc
    if (not isinstance(manifest, dict)
            or set(manifest) != {"schema", "projects"} or type(manifest["schema"]) is not int
            or manifest["schema"] != 1 or not isinstance(manifest["projects"], dict)
            or len(manifest["projects"]) > 32):
        raise ValueError("INVALID_MANIFEST")
    for key, item in manifest["projects"].items():
        if (not isinstance(key, str) or not _PROJECT_ID.fullmatch(key)
                or not isinstance(item, dict)
                or set(item) != {"project", "sha256", "artifacts"}
                or not isinstance(item["sha256"], str)
                or not _SHA256.fullmatch(item["sha256"])):
            raise ValueError("INVALID_MANIFEST")
    return manifest


def _read_project_hash(project: Path) -> str:
    if not project.is_file() or project.stat().st_size > MAX_PROJECT_BYTES:
        raise ValueError("INVALID_PROJECT")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(project, flags), "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_PROJECT_BYTES:
            raise ValueError("INVALID_PROJECT")
        data = stream.read(MAX_PROJECT_BYTES + 1)
        after = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise ValueError("PROJECT_CHANGED")
        if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
            raise ValueError("PROJECT_CHANGED")
    if len(data) > MAX_PROJECT_BYTES:
        raise ValueError("INVALID_PROJECT")
    return hashlib.sha256(data).hexdigest()


def _terminate_tree(process: subprocess.Popen[bytes]) -> None:
    """Best effort: отдельная POSIX process group / фиксированный Windows taskkill."""
    if os.name == "nt":
        system_root = os.getenv("SystemRoot", r"C:\Windows")
        executable = Path(system_root) / "System32" / "taskkill.exe"
        try:
            subprocess.run(
                [str(executable), "/F", "/T", "/PID", str(process.pid)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, check=False, timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except OSError:
            pass
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        pass
    if os.name != "nt":
        # Даже если parent завершился, потомки в той же группе могли выжить.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass
    if process.poll() is None:
        try:
            process.kill()
        except OSError:
            pass
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass


def _execute_batch(
    argv: tuple[str, ...], cwd: Path, timeout_seconds: int, log_path: Path
) -> dict[str, Any]:
    """Реальный process executor: нет shell, stdin закрыт, stdout ограничен."""
    flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
    buffer = bytearray()
    over_limit = threading.Event()
    collector_error = threading.Event()
    observed_bytes = 0
    collected_hash = hashlib.sha256()
    timed_out = False
    with log_path.open("xb") as saved:
        process = subprocess.Popen(
            list(argv), cwd=str(cwd), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            shell=False, start_new_session=os.name != "nt",
            creationflags=flags,
        )
        assert process.stdout is not None

        def drain() -> None:
            nonlocal observed_bytes
            try:
                with process.stdout as stream:
                    while True:
                        chunk = stream.read(8192)
                        if not chunk:
                            break
                        observed_bytes += len(chunk)
                        allowed = max(0, MAX_LOG_BYTES - len(buffer))
                        if allowed:
                            accepted = chunk[:allowed]
                            buffer.extend(accepted)
                            collected_hash.update(accepted)
                            saved.write(accepted)
                        if observed_bytes > MAX_LOG_BYTES:
                            over_limit.set()
            except OSError:
                collector_error.set()

        thread = threading.Thread(target=drain, daemon=True, name="synplify-log-reader")
        thread.start()
        deadline = time.monotonic() + timeout_seconds
        while process.poll() is None:
            if over_limit.is_set() or collector_error.is_set():
                break
            if time.monotonic() >= deadline:
                timed_out = True
                break
            time.sleep(0.05)
        if timed_out or over_limit.is_set() or collector_error.is_set():
            _terminate_tree(process)
        thread.join(timeout=2)
        if thread.is_alive():
            _terminate_tree(process)
            return _result("PROCESS_TREE_UNCERTAIN", executed=True,
                           exit_code=process.poll())
        exit_code = process.poll()

    evidence = {
        "exit_code": exit_code,
        "captured_log_bytes": len(buffer),
        "observed_log_bytes": observed_bytes,
        "captured_log_sha256": collected_hash.hexdigest(),
        "log_truncated": over_limit.is_set(),
    }
    if timed_out:
        return _result("TIMEOUT", executed=True, **evidence)
    if over_limit.is_set():
        return _result("LOG_LIMIT", executed=True, **evidence)
    if collector_error.is_set():
        return _result("LOG_READ_ERROR", executed=True, **evidence)
    if _LICENSE_PROBLEM.search(bytes(buffer)):
        return _result("LICENSE_UNAVAILABLE", executed=True, **evidence)
    if exit_code != 0:
        return _result("TOOL_FAILED", executed=True, **evidence)
    return _result("PROCESS_EXIT_ZERO_UNVERIFIED", executed=True, **evidence)


Executor = Callable[[tuple[str, ...], Path, int, Path], dict[str, Any]]


def run_approved_project(
    project_id: str, acknowledge_side_effects: bool = False,
    timeout_seconds: int = 30, *, executor: Executor | None = None
) -> dict[str, Any]:
    """Нельзя вызвать с произвольными argv/Tcl/project path через MCP."""
    if (not isinstance(project_id, str) or not _PROJECT_ID.fullmatch(project_id)):
        return _result("INVALID_PROJECT_ID")
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= MAX_TIMEOUT_SECONDS:
        return _result("INVALID_TIMEOUT")
    if type(acknowledge_side_effects) is not bool or not acknowledge_side_effects:
        return _result("CONFIRMATION_REQUIRED")
    if os.environ.get(ENABLE_ENV) != "1":
        return _result("DISABLED")

    configured_exe = os.environ.get(EXECUTABLE_ENV)
    if not configured_exe:
        return _result("NOT_INSTALLED")
    executable = Path(configured_exe)
    if not executable.is_absolute() or executable.is_symlink() or not executable.is_file():
        return _result("INVALID_EXECUTABLE")
    # Windows dispatches .bat/.cmd through cmd.exe even with shell=False.
    if os.name == "nt" and executable.suffix.lower() != ".exe":
        return _result("INVALID_EXECUTABLE")
    if os.name != "nt" and not os.access(executable, os.X_OK):
        return _result("INVALID_EXECUTABLE")
    manifest_path = os.environ.get(MANIFEST_ENV)
    workspace_path = os.environ.get(WORKSPACE_ENV)
    if not manifest_path or not workspace_path:
        return _result("NOT_CONFIGURED")

    manifest_file = Path(manifest_path)
    root = Path(workspace_path)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        return _result("INVALID_WORKSPACE")
    try:
        root = root.resolve(strict=True)
        # Preserve INVALID_MANIFEST for a missing/untrusted approval file,
        # rather than reporting an unrelated process LAUNCH_ERROR.
        if (not manifest_file.is_absolute() or manifest_file.is_symlink()
                or not manifest_file.is_file()):
            return _result("INVALID_MANIFEST")
        # Approval data editable through the agent workspace defeats the allowlist.
        if manifest_file.resolve(strict=True).is_relative_to(root):
            return _result("INVALID_MANIFEST")
        manifest = _read_manifest(manifest_file)
        entry = manifest["projects"].get(project_id)
        if entry is None:
            return _result("PROJECT_NOT_APPROVED")
        project = _approved_relative(root, entry["project"], suffix=".prj")
        artifacts = _approved_relative(root, entry["artifacts"], suffix=None)
        if not artifacts.is_dir() or not project.is_file():
            return _result("INVALID_PATH")
        if project.is_relative_to(artifacts):
            # Не храним утверждённый проект внутри каталога артефактов.
            return _result("INVALID_ARTIFACT_ROOT")
        digest = _read_project_hash(project)
        if digest != entry["sha256"].lower():
            return _result("PROJECT_CHANGED")

        # Синтез может создать другие файлы по правилам самого доверенного .prj.
        # Только cwd и собственный журнал изолированы в уникальном каталоге.
        run_folder = Path(tempfile.mkdtemp(prefix="synthesis-", dir=str(artifacts)))
        if os.name != "nt":
            os.chmod(run_folder, 0o700)
        command = (str(executable), "-batch", str(project))
        selected = executor or _execute_batch
        result = selected(command, run_folder, timeout_seconds, run_folder / "stdout.log")
        # Никакие абсолютные пути к EDA или исходникам не возвращаются клиенту.
        result = dict(result)
        result["project_id"] = project_id
        result["project_sha256"] = digest
        result["artifact_run_id"] = run_folder.name
        result["invocation"] = "APPROVED_PROJECT_BATCH"
        return result
    except ValueError as exc:
        code = str(exc)
        return _result(code if code in {
            "INVALID_MANIFEST", "MANIFEST_TOO_LARGE", "INVALID_PATH",
            "SYMLINK_DENIED", "OUTSIDE_WORKSPACE", "PATH_NOT_FOUND",
            "INVALID_PROJECT", "PROJECT_CHANGED",
        } else "INVALID_CONFIGURATION")
    except (OSError, subprocess.SubprocessError):
        return _result("LAUNCH_ERROR")
