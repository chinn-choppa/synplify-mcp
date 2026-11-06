"""Консервативные метрики .srr с происхождением чисел и явной неопределённостью.

Поддерживается только небольшой *искусственный* поднабор подписанных
таблиц. Другие версии/секции не подгоняются под эти выражения.
"""

from __future__ import annotations

import io
import math
import re
from typing import Any

MAX_METRIC_LINE = 512
MAX_RESOURCES = 64
MAX_CLOCKS = 32
MAX_ISSUES = 20

_TOOL = re.compile(r"^Synplify Pro Version:\s*(.+?)\s*$", re.I)
_DEVICE = re.compile(r"^Target Device:\s*(.+?)\s*$", re.I)
_RESOURCE_LABEL = re.compile(
    r"^(?P<name>Total LUTs|Register bits not including I/Os|I/O ports|Block RAMs)"
    r"\s*:\s*(?P<value>\d[\d,]*|N/A|Unknown)$", re.I
)
_RESOURCE_HEADER = re.compile(r"^Resource\s+Used\s+Available$", re.I)
_RESOURCE_ROW = re.compile(
    r"^(?P<name>[A-Za-z][\w .-]{0,48}?)\s+"
    r"(?P<used>\d[\d,]*|N/A|Unknown)\s+"
    r"(?P<available>\d[\d,]*|N/A|Unknown)$", re.I
)
_TIMING_HEADER = re.compile(
    r"^Clock\s+Requested\s+(?P<requested_kind>Period|Frequency)\s*"
    r"\((?P<requested_unit>ns|MHz)\)\s+Estimated\s+"
    r"(?P<estimated_kind>Period|Frequency)\s*"
    r"\((?P<estimated_unit>ns|MHz)\)\s+Slack\s*\((?P<slack_unit>ns)\)$",
    re.I,
)
_NUMBER = re.compile(r"^-?(?:\d+(?:\.\d+)?|\.\d+)$")
_COUNT = re.compile(r"^(?:0|[1-9]\d{0,8})(?:,\d{3})*$")
_UNKNOWN = {"n/a", "unknown"}
_UNCONSTRAINED = {"unconstrained"}
_SECTIONS = {
    "COMPILER REPORT", "PREMAP REPORT", "MAPPER REPORT",
    "RESOURCE USAGE REPORT",
}
_END_TIMING = {"END TIMING REPORT", "END OF TIMING REPORT"}


def _source(raw: str, number: int, offset: int, section: str) -> dict[str, Any]:
    return {"report_line": number, "byte_offset": offset, "raw": raw, "section": section}


def _count(raw: str) -> int | None:
    if not _COUNT.fullmatch(raw):
        return None
    value = int(raw.replace(",", ""))
    return value if value <= 1_000_000_000 else None


def _quantity(raw: str, unit: str, *, allow_negative: bool = False) -> dict[str, Any]:
    token = raw.casefold()
    if token in _UNKNOWN or token == "unconstrained":
        status = "UNCONSTRAINED" if token == "unconstrained" else "UNKNOWN"
        return {"value": None, "unit": unit, "state": status}
    if not _NUMBER.fullmatch(raw):
        return {"value": None, "unit": unit, "state": "UNKNOWN"}
    value = float(raw)
    if not math.isfinite(value) or (not allow_negative and value <= 0):
        return {"value": None, "unit": unit, "state": "UNKNOWN"}
    return {"value": value, "unit": unit, "state": "KNOWN"}


def _resource(name: str, used: str, available: str | None, raw: str,
              line: int, offset: int) -> dict[str, Any]:
    used_value = _count(used)
    available_value = _count(available) if available is not None else None
    # Нельзя отождествлять LUT, logic cells и FPGA-specific primitives.
    return {
        "name": name,
        "key": name.casefold(),
        "used": {"value": used_value, "unit": "count",
                 "state": "KNOWN" if used_value is not None else "UNKNOWN"},
        "available": {"value": available_value, "unit": "count", "reported": available is not None,
                      "state": "KNOWN" if available_value is not None else "UNKNOWN"},
        "evidence": _source(raw, line, offset, "RESOURCE_USAGE"),
    }


def _context_value(rows: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    distinct = {value for value, _ in rows}
    if not rows:
        return {"state": "UNKNOWN", "value": None, "evidence": []}
    if len(distinct) != 1:
        return {"state": "AMBIGUOUS", "value": None,
                "evidence": [entry for _, entry in rows[:4]]}
    value = next(iter(distinct))
    return {"state": "KNOWN", "value": value,
            "evidence": [entry for _, entry in rows[:4]]}


def extract_metrics(text: str, codec: str, bom: int) -> dict[str, Any]:
    """Разбирать только секции с явными подписанными единицами измерения."""
    resources: list[dict[str, Any]] = []
    clocks: list[dict[str, Any]] = []
    tool_rows: list[tuple[str, dict[str, Any]]] = []
    device_rows: list[tuple[str, dict[str, Any]]] = []
    issues: list[str] = []

    def flag(code: str) -> None:
        if code not in issues and len(issues) < MAX_ISSUES:
            issues.append(code)

    timing_started = False
    timing_ended = False
    performance_seen = False
    timing_active = False
    resource_active = False
    resource_header = False
    timing_header: re.Match[str] | None = None
    timing_header_evidence: dict[str, Any] | None = None
    resource_section_seen = False
    timing_section_seen = False
    offset = bom

    with io.StringIO(text, newline="") as stream:
        for number, original in enumerate(stream, start=1):
            pos = offset
            offset += len(original.encode(codec))
            raw = (original[:-2] if original.endswith("\r\n")
                   else original[:-1] if original.endswith(("\n", "\r"))
                   else original)
            line = raw.strip()
            if len(raw) > MAX_METRIC_LINE:
                if timing_active or resource_active:
                    flag("METRIC_LINE_TOO_LONG")
                continue

            tool = _TOOL.fullmatch(line)
            device = _DEVICE.fullmatch(line)
            if tool and len(tool_rows) < 8:
                tool_rows.append((tool[1][:128], _source(raw, number, pos, "CONTEXT")))
            if device and len(device_rows) < 8:
                device_rows.append((device[1][:128], _source(raw, number, pos, "CONTEXT")))

            upper = line.upper()
            if upper in _SECTIONS:
                resource_active = upper == "RESOURCE USAGE REPORT"
                resource_header = False
                if resource_active:
                    resource_section_seen = True
                if timing_active:
                    flag("TIMING_SECTION_UNTERMINATED")
                timing_active = False
                timing_header = None
                timing_header_evidence = None
                performance_seen = False
                continue

            if upper in {"START TIMING REPORT", "START OF TIMING REPORT"}:
                if timing_active:
                    flag("TIMING_SECTION_UNTERMINATED")
                timing_started = timing_active = timing_section_seen = True
                timing_header = None
                timing_header_evidence = None
                performance_seen = False
                resource_active = resource_header = False
                continue
            if upper in _END_TIMING:
                if timing_active:
                    timing_ended = True
                timing_active = False
                timing_header = None
                timing_header_evidence = None
                performance_seen = False
                continue

            if resource_active:
                if not line:
                    resource_header = False
                    continue
                if _RESOURCE_HEADER.fullmatch(line):
                    resource_header = True
                    continue
                labelled = _RESOURCE_LABEL.fullmatch(line)
                if labelled:
                    if len(resources) >= MAX_RESOURCES:
                        flag("RESOURCE_LIMIT")
                        continue
                    resources.append(_resource(
                        labelled["name"], labelled["value"], None, raw, number, pos
                    ))
                    continue
                if resource_header:
                    row = _RESOURCE_ROW.fullmatch(line)
                    if row:
                        if len(resources) >= MAX_RESOURCES:
                            flag("RESOURCE_LIMIT")
                            continue
                        resources.append(_resource(
                            row["name"], row["used"], row["available"], raw, number, pos
                        ))
                    else:
                        flag("UNSUPPORTED_RESOURCE_ROW")
                elif ":" in line:
                    flag("UNSUPPORTED_RESOURCE_FIELD")
                continue

            if not timing_active:
                continue
            if upper == "PERFORMANCE SUMMARY":
                performance_seen = True
                timing_header = None
                timing_header_evidence = None
                continue
            header = _TIMING_HEADER.fullmatch(line) if performance_seen else None
            if header:
                timing_header = header
                timing_header_evidence = _source(raw, number, pos, "TIMING")
                # Колонки должны согласовываться с названиями единиц.
                for prefix in ("requested", "estimated"):
                    expected = "ns" if header[f"{prefix}_kind"].lower() == "period" else "MHz"
                    if header[f"{prefix}_unit"].lower() != expected.lower():
                        flag("INCOMPATIBLE_TIMING_UNITS")
                        timing_header = None
                        timing_header_evidence = None
                continue

            if timing_header and not line:
                timing_header = None
                timing_header_evidence = None
                continue
            if timing_header:
                columns = line.split()
                if len(columns) != 4 or len(clocks) >= MAX_CLOCKS:
                    flag("UNSUPPORTED_TIMING_ROW" if len(columns) != 4 else "CLOCK_LIMIT")
                    continue
                name, req, est, slack = columns
                if len(name) > 128:
                    flag("UNSUPPORTED_TIMING_ROW")
                    continue
                req_q = _quantity(req, timing_header["requested_unit"])
                est_q = _quantity(est, timing_header["estimated_unit"])
                slack_q = _quantity(slack, "ns", allow_negative=True)
                if any(q["state"] != "KNOWN" for q in (req_q, est_q, slack_q)):
                    flag("UNKNOWN_TIMING_VALUE")
                constraints = ("CONSTRAINED" if req_q["state"] == "KNOWN"
                               else req_q["state"] if req_q["state"] == "UNCONSTRAINED"
                               else "UNKNOWN")
                clocks.append({
                    "clock": name,
                    "requested": req_q,
                    "estimated": est_q,
                    "slack": slack_q,
                    "constraints": constraints,
                    "evidence": _source(raw, number, pos, "TIMING"),
                    "header_evidence": timing_header_evidence,
                })
            elif line and (line.startswith("Clock") or "slack" in line.casefold()):
                flag("UNSUPPORTED_TIMING_FORMAT")

    if timing_started and not timing_ended:
        flag("TIMING_SECTION_UNTERMINATED")

    resource_names = [item["key"] for item in resources]
    clock_names = [item["clock"] for item in clocks]
    if len(resource_names) != len(set(resource_names)):
        flag("DUPLICATE_RESOURCE")
    if len(clock_names) != len(set(clock_names)):
        flag("DUPLICATE_CLOCK")

    resource_state = ("ABSENT" if not resource_section_seen else
                      "UNSUPPORTED" if not resources else
                      "AMBIGUOUS" if "DUPLICATE_RESOURCE" in issues else
                      "PARTIAL" if any(item["used"]["state"] != "KNOWN" or
                      (item["available"]["reported"] and item["available"]["state"] != "KNOWN")
                      for item in resources)
                      or any(x.startswith(("UNSUPPORTED_RESOURCE", "RESOURCE_LIMIT", "METRIC_LINE"))
                             for x in issues) else "PARSED")
    timing_state = ("ABSENT" if not timing_section_seen else
                    "UNSUPPORTED" if not clocks else
                    "AMBIGUOUS" if "DUPLICATE_CLOCK" in issues else
                    "PARTIAL" if not timing_ended or "TIMING_SECTION_UNTERMINATED" in issues or
                    any(q["state"] != "KNOWN" for row in clocks
                        for q in (row["requested"], row["estimated"], row["slack"]))
                    or any(x.startswith(("UNSUPPORTED_TIMING", "INCOMPATIBLE_TIMING",
                                         "CLOCK_LIMIT", "METRIC_LINE"))
                           for x in issues) else "PARSED")
    return {
        "context": {
            "tool_version": _context_value(tool_rows),
            "device": _context_value(device_rows),
        },
        "resources": {
            "state": resource_state,
            "scope": "SYNTHESIS_MAPPING",
            "items": resources,
            "issues": [x for x in issues if "RESOURCE" in x or x == "METRIC_LINE_TOO_LONG"],
        },
        "timing": {
            "state": timing_state,
            "kind": "SYNTHESIS_ESTIMATE",
            "implementation_timing": False,
            "clocks": clocks,
            "issues": [x for x in issues if "TIMING" in x or "CLOCK" in x
                       or x in {"METRIC_LINE_TOO_LONG", "UNKNOWN_TIMING_VALUE"}],
        },
    }
