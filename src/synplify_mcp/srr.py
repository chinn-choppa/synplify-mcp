"""Безопасное чтение .srr и ограниченный разбор диагностик.

Формат не имеет универсальной схемы; не выводим статус синтеза из
отсутствия совпадений, не нормализуем timing/resource без подтверждения.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath, PureWindowsPath

MAX_REPORT_BYTES = 1_048_576
MAX_ITEMS = 200
MAX_LINES = 20_000
MAX_RAW_CHARS = 4_096
MAX_MESSAGE_CHARS = 2_048
MAX_SECTIONS = 100
MAX_DIAGNOSTIC_OUTPUT_BYTES = 65_536

_DIAGNOSTIC = re.compile(r"^\s*@(?P<level>[EWIN]):\s*(?P<body>.*)$")
_CODE = re.compile(r"^(?P<code>[A-Za-z][A-Za-z0-9_]{1,14}\d[A-Za-z0-9_]*)\s*:\s*(?P<body>.*)$")
_LOCATION = re.compile(
    r"^(?P<file>.+?)\((?P<line>\d+)(?:,(?P<column>\d+))?\):\s*(?P<body>.*)$"
)
_COLON_LOCATION = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+)(?::(?P<column>\d+))?:\s*(?P<body>.*)$"
)
_SEVERITY = {"E": "error", "W": "warning", "I": "info", "N": "note"}


def _error(code: str, *, source_path: str | None = None) -> dict[str, object]:
    """Возвращать статусы ошибок без утечки абсолютных путей."""
    return {
        "state": "ERROR",
        "error_code": code,
        "source_path": source_path,
        "executed": False,
        "synthesis_status": "UNKNOWN",
        "diagnostics": [],
    }


def _decode(data: bytes, encoding: str) -> tuple[str, str, int]:
    """Определить только BOM/UTF-8; legacy-кодировку разрешает вызывающий."""
    if encoding not in {"auto", "utf-8", "cp1252"}:
        raise ValueError("UNSUPPORTED_ENCODING")
    bom = 0
    codec = "utf-8" if encoding == "auto" else encoding
    if data.startswith(b"\xef\xbb\xbf"):
        if encoding == "cp1252":
            raise ValueError("ENCODING_CONFLICT")
        codec, bom = "utf-8", 3
    elif data.startswith(b"\xff\xfe"):
        if encoding != "auto":
            raise ValueError("ENCODING_CONFLICT")
        codec, bom = "utf-16-le", 2
    elif data.startswith(b"\xfe\xff"):
        if encoding != "auto":
            raise ValueError("ENCODING_CONFLICT")
        codec, bom = "utf-16-be", 2
    try:
        text = data[bom:].decode(codec, errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("DECODE_ERROR") from exc
    if "\x00" in text:
        raise ValueError("BINARY_OR_UNSUPPORTED_ENCODING")
    return text, codec, bom


def _section(line: str) -> str | None:
    normalized = line.strip().upper()
    if normalized in {"COMPILER REPORT", "PREMAP REPORT", "MAPPER REPORT"}:
        return normalized.replace(" ", "_")
    if normalized.startswith(("START TIMING REPORT", "START OF TIMING REPORT")):
        return "TIMING"
    if normalized.startswith("RESOURCE USAGE REPORT"):
        return "RESOURCE_USAGE"
    return None


def _category(message: str) -> str | None:
    msg = message.lower()
    if re.search(r"\binferred\s+latch\b|\blatch\s+inferred\b", msg):
        return "INFERRED_LATCH"
    if re.search(r"\bblack[\s-]?box\b", msg):
        return "BLACK_BOX"
    return None


def parse_srr_bytes(
    data: bytes, *, encoding: str = "auto", limit: int = MAX_ITEMS,
    source_path: str | None = None,
) -> dict[str, object]:
    """Разобрать публичные/разрешённые .srr-байты с точными смещениями."""
    if not isinstance(data, bytes):
        return _error("INVALID_BYTES", source_path=source_path)
    if len(data) > MAX_REPORT_BYTES:
        return _error("TOO_LARGE", source_path=source_path)
    if type(limit) is not int or not 1 <= limit <= MAX_ITEMS:
        return _error("INVALID_LIMIT", source_path=source_path)
    try:
        text, codec, offset = _decode(data, encoding)
    except ValueError as exc:
        return _error(str(exc), source_path=source_path)

    items: list[dict[str, object]] = []
    sections: list[dict[str, object]] = []
    total = 0
    line_count = 0
    unrecognized_markers = 0
    oversized_lines = 0
    truncated_messages = 0
    diagnostic_output_bytes = 0
    output_limited = False
    section_count = 0
    current_section: str | None = None
    has_content = False

    with io.StringIO(text, newline="") as lines:
        for original in lines:
            line_count += 1
            if line_count > MAX_LINES:
                return _error("TOO_MANY_LINES", source_path=source_path)
            start = offset
            offset += len(original.encode(codec, errors="strict"))
            if original.endswith("\r\n"):
                raw = original[:-2]
            elif original.endswith(("\r", "\n")):
                raw = original[:-1]
            else:
                raw = original
            if raw.strip():
                has_content = True
            if len(raw) > MAX_RAW_CHARS:
                oversized_lines += 1
                continue

            section = _section(raw)
            if section is not None:
                current_section = section
                section_count += 1
                if len(sections) < MAX_SECTIONS:
                    sections.append({"name": section, "report_line": line_count, "byte_offset": start})
                continue

            match = _DIAGNOSTIC.match(raw)
            if not match:
                if raw.lstrip().startswith("@"):
                    unrecognized_markers += 1
                continue

            total += 1
            if len(items) == limit:
                continue

            body = match["body"]
            code_match = _CODE.match(body)
            code: str | None = None
            if code_match:
                code = code_match["code"]
                body = code_match["body"]

            loc = _LOCATION.match(body) or _COLON_LOCATION.match(body)
            source_file: str | None = None
            source_line: int | None = None
            source_column: int | None = None
            if loc:
                source_file = loc["file"]
                source_line = int(loc["line"])
                source_column = int(loc["column"]) if loc["column"] else None
                body = loc["body"]

            if len(body) > MAX_MESSAGE_CHARS:
                truncated_messages += 1
            item = {
                "severity": _SEVERITY[match["level"]],
                "code": code,
                "category": _category(body),
                "file": source_file,
                "line": source_line,
                "column": source_column,
                "message": body[:MAX_MESSAGE_CHARS],
                "message_truncated": len(body) > MAX_MESSAGE_CHARS,
                "raw": raw,
                "report_line": line_count,
                "byte_offset": start,
                "section": current_section,
            }
            item_size = len(json.dumps(item, ensure_ascii=False).encode("utf-8"))
            if diagnostic_output_bytes + item_size > MAX_DIAGNOSTIC_OUTPUT_BYTES:
                output_limited = True
                continue
            diagnostic_output_bytes += item_size
            items.append(item)

    truncated = (total > len(items) or oversized_lines > 0
                 or truncated_messages > 0 or section_count > MAX_SECTIONS
                 or output_limited)
    if not has_content:
        health = "EMPTY"
    elif unrecognized_markers or truncated:
        health = "PARTIAL"
    elif total == 0:
        health = "NO_DIAGNOSTICS" if sections else "UNRECOGNIZED"
    else:
        health = "PARSED"

    return {
        "state": "PARSED",
        "parse_health": health,
        "error_code": None,
        "source_path": source_path,
        "report_sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
        "encoding": codec,
        "line_count": line_count,
        "diagnostic_count": total,
        "diagnostics": items,
        "truncated": truncated,
        "unrecognized_markers": unrecognized_markers,
        "oversized_lines": oversized_lines,
        "truncated_messages": truncated_messages,
        "diagnostic_output_bytes": diagnostic_output_bytes,
        "output_limited": output_limited,
        "section_count": section_count,
        "sections": sections,
        "tool_version": None,
        "device": None,
        "resources": {"state": "NOT_EXTRACTED"},
        "timing": {"state": "NOT_EXTRACTED", "kind": "SYNTHESIS_ESTIMATE"},
        "executed": False,
        "synthesis_status": "UNKNOWN",
    }


def read_srr_report(relative_path: str, encoding: str = "auto", limit: int = 200) -> dict[str, object]:
    """Читать только относительный .srr-файл из доверенного workspace.

    Workspace задаёт оператор через SYNPLIFY_MCP_WORKSPACE, а не MCP-клиент.
    """
    if not isinstance(relative_path, str) or not relative_path or "\x00" in relative_path:
        return _error("INVALID_PATH")
    if type(limit) is not int or not 1 <= limit <= MAX_ITEMS:
        return _error("INVALID_LIMIT")
    if encoding not in {"auto", "utf-8", "cp1252"}:
        return _error("UNSUPPORTED_ENCODING")
    if ("\\" in relative_path or ":" in relative_path
            or PureWindowsPath(relative_path).root
            or PurePosixPath(relative_path).is_absolute()):
        return _error("INVALID_PATH")
    rel = Path(relative_path)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts or rel.suffix.lower() != ".srr":
        return _error("INVALID_PATH")

    configured = os.getenv("SYNPLIFY_MCP_WORKSPACE")
    if not configured:
        return _error("WORKSPACE_NOT_CONFIGURED")
    root_config = Path(configured).expanduser()
    if not root_config.is_absolute():
        return _error("INVALID_WORKSPACE")
    try:
        root = root_config.resolve(strict=True)
        if not root.is_dir():
            return _error("INVALID_WORKSPACE")
        cursor = root
        for part in rel.parts:
            cursor = cursor / part
            if cursor.is_symlink() or getattr(cursor, "is_junction", lambda: False)():
                return _error("SYMLINK_DENIED", source_path=relative_path)
        candidate = cursor.resolve(strict=True)
        if not candidate.is_relative_to(root):
            return _error("OUTSIDE_WORKSPACE", source_path=relative_path)
        info = candidate.stat()
        if not stat.S_ISREG(info.st_mode):
            return _error("NOT_REGULAR_FILE", source_path=relative_path)
        if info.st_size > MAX_REPORT_BYTES:
            return _error("TOO_LARGE", source_path=relative_path)
        # O_NOFOLLOW защищает конечный компонент на Unix при подмене ссылки.
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(candidate, flags)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                return _error("NOT_REGULAR_FILE", source_path=relative_path)
            if (before.st_dev, before.st_ino) != (info.st_dev, info.st_ino):
                return _error("FILE_CHANGED_DURING_READ", source_path=relative_path)
            data = stream.read(MAX_REPORT_BYTES + 1)
            after = os.fstat(stream.fileno())
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                return _error("FILE_CHANGED_DURING_READ", source_path=relative_path)
        # Проверяем, что имя файла после чтения не стало выходить за root.
        if cursor.resolve(strict=True) != candidate:
            return _error("FILE_CHANGED_DURING_READ", source_path=relative_path)
    except FileNotFoundError:
        return _error("NOT_FOUND", source_path=relative_path)
    except (OSError, RuntimeError, ValueError):
        return _error("FILE_ACCESS_DENIED", source_path=relative_path)
    return parse_srr_bytes(data, encoding=encoding, limit=limit, source_path=relative_path)
