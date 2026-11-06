"""Сравнение двух разрешённых .srr без заявлений о достоверности EDA.

Нельзя автоматически считать близкие временные ограничения одним и тем же
набором SDC/FDC. Без хеша исходных ограничений числовые дельты timing
не вычисляются даже при совпадающих периодах.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .srr import read_srr_report

MAX_CHANGED_ITEMS = 16
MAX_RAW_EVIDENCE = 256


def _evidence(item: dict[str, Any] | None) -> dict[str, Any] | None:
    if item is None:
        return None
    # Исходная строка привязана к sha256 отчёта, который есть в summary.
    return {
        "report_line": item.get("report_line"),
        "byte_offset": item.get("byte_offset"),
        "section": item.get("section"),
        "raw": str(item.get("raw", ""))[:MAX_RAW_EVIDENCE],
    }


def _snapshot(parsed: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_sha256": parsed.get("report_sha256"),
        "source_path": parsed.get("source_path"),
        "parse_health": parsed.get("parse_health"),
        "synthesis_status": parsed.get("synthesis_status"),
        "tool_version": parsed.get("tool_version"),
        "device": parsed.get("device"),
        "context": parsed.get("context"),
        "resource_state": parsed.get("resources", {}).get("state"),
        "timing_state": parsed.get("timing", {}).get("state"),
    }


def _identity(parsed: dict[str, Any], name: str) -> str | None:
    context = parsed.get("context", {}).get(name, {})
    if context.get("state") == "KNOWN" and isinstance(context.get("value"), str):
        return context["value"]
    return None


def _context(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    states: list[str] = []
    for field in ("tool_version", "device"):
        before = _identity(baseline, field)
        after = _identity(candidate, field)
        state = "UNKNOWN" if before is None or after is None else (
            "MATCH" if before == after else "MISMATCH"
        )
        states.append(state)
        checks.append({
            "field": field,
            "state": state,
            "baseline": before,
            "candidate": after,
            "baseline_evidence": [_evidence(x) for x in baseline.get(
                "context", {}).get(field, {}).get("evidence", [])[:2]],
            "candidate_evidence": [_evidence(x) for x in candidate.get(
                "context", {}).get(field, {}).get("evidence", [])[:2]],
        })
    overall = ("INCOMPATIBLE" if "MISMATCH" in states else
               "UNVERIFIED" if "UNKNOWN" in states else "MATCHED")
    return {"state": overall, "checks": checks}


def _diagnostic_key(entry: dict[str, Any]) -> tuple[Any, ...]:
    return (entry.get("severity"), entry.get("code"), entry.get("category"),
            entry.get("file"), entry.get("line"), entry.get("column"),
            entry.get("message"))


def _diagnostics(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    left = baseline.get("diagnostics", [])
    right = candidate.get("diagnostics", [])
    lc = Counter(_diagnostic_key(x) for x in left)
    rc = Counter(_diagnostic_key(x) for x in right)
    left_loc: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    right_loc: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for item in left:
        left_loc[_diagnostic_key(item)].append(item)
    for item in right:
        right_loc[_diagnostic_key(item)].append(item)

    complete = (baseline.get("parse_health") == "PARSED"
                and candidate.get("parse_health") == "PARSED"
                and not baseline.get("truncated") and not candidate.get("truncated"))
    changes: list[dict[str, Any]] = []
    change_count = 0
    for key in sorted(lc.keys() | rc.keys(), key=repr):
        removed = max(0, lc[key] - rc[key])
        added = max(0, rc[key] - lc[key])
        for kind, count, loc in (
            ("REMOVED", removed, left_loc),
            ("ADDED", added, right_loc),
        ):
            if not count:
                continue
            change_count += count
            if len(changes) >= MAX_CHANGED_ITEMS:
                continue
            evidence = [_evidence(x) for x in loc[key][:2]]
            changes.append({
                "change": kind,
                "count": count,
                "severity": key[0],
                "code": key[1],
                "category": key[2],
                "file": key[3],
                "line": key[4],
                "column": key[5],
                "message": key[6],
                "evidence": evidence,
            })
    return {
        "state": "COMPLETE_OBSERVATION" if complete else "PARTIAL_OBSERVATION",
        "baseline_count": baseline.get("diagnostic_count"),
        "candidate_count": candidate.get("diagnostic_count"),
        "observed_change_count": change_count,
        "changes": changes,
        "entries_limited": len(changes) >= MAX_CHANGED_ITEMS and change_count > len(changes),
        "synthesis_success_inferred": False,
    }


def _metric_map(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]] | None:
    if not isinstance(items, list):
        return None
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        identity = item.get(key)
        if not isinstance(identity, str) or identity in result:
            return None
        result[identity] = item
    return result


def _resources(baseline: dict[str, Any], candidate: dict[str, Any],
               context_state: str) -> dict[str, Any]:
    if context_state != "MATCHED":
        return {"state": "BLOCKED_CONTEXT", "changes": [], "reason": context_state}
    before, after = baseline["resources"], candidate["resources"]
    if before.get("state") != "PARSED" or after.get("state") != "PARSED":
        return {
            "state": "UNVERIFIED_DATA", "changes": [],
            "reason": [before.get("state"), after.get("state")],
        }
    lb = _metric_map(before.get("items", []), "key")
    rb = _metric_map(after.get("items", []), "key")
    if lb is None or rb is None:
        return {"state": "AMBIGUOUS", "changes": []}
    changes: list[dict[str, Any]] = []
    count = 0
    mismatches = []
    for key in sorted(lb.keys() | rb.keys()):
        left, right = lb.get(key), rb.get(key)
        if left is None or right is None:
            count += 1
            if len(changes) < MAX_CHANGED_ITEMS:
                changes.append({
                    "resource": key, "state": "ADDED" if left is None else "REMOVED",
                    "delta": None,
                    "baseline_evidence": _evidence(left["evidence"]) if left else None,
                    "candidate_evidence": _evidence(right["evidence"]) if right else None,
                })
            continue
        lu, ru = left["used"], right["used"]
        la, ra = left["available"], right["available"]
        capacity_compatible = (
            la.get("state") == ra.get("state")
            and la.get("value") == ra.get("value")
            and la.get("unit") == ra.get("unit")
            and la.get("reported") == ra.get("reported")
        )
        comparable = (capacity_compatible and lu.get("state") == "KNOWN"
                      and ru.get("state") == "KNOWN"
                      and lu.get("unit") == "count" and ru.get("unit") == "count")
        if not comparable:
            mismatches.append(key)
            count += 1
        elif lu["value"] == ru["value"]:
            continue
        else:
            count += 1
        if len(changes) >= MAX_CHANGED_ITEMS:
            continue
        changes.append({
            "resource": key, "state": "COMPARABLE" if comparable else "INCOMPATIBLE_CAPACITY",
            "baseline_used": lu.get("value"), "candidate_used": ru.get("value"),
            "unit": "count" if comparable else None,
            "delta": (ru["value"] - lu["value"]) if comparable else None,
            "baseline_evidence": _evidence(left["evidence"]),
            "candidate_evidence": _evidence(right["evidence"]),
        })
    return {
        "state": "PARTIAL" if mismatches else "COMPARABLE",
        "change_count": count,
        "changes": changes,
        "entries_limited": count > len(changes),
        "incompatible_resources": mismatches[:MAX_CHANGED_ITEMS],
    }


def _timing(baseline: dict[str, Any], candidate: dict[str, Any],
            context_state: str) -> dict[str, Any]:
    if context_state != "MATCHED":
        return {"state": "BLOCKED_CONTEXT", "changes": [], "reason": context_state}
    before, after = baseline["timing"], candidate["timing"]
    if before.get("kind") != "SYNTHESIS_ESTIMATE" or after.get("kind") != "SYNTHESIS_ESTIMATE":
        return {"state": "INCOMPATIBLE_TIMING_KIND", "changes": []}
    if before.get("state") != "PARSED" or after.get("state") != "PARSED":
        return {"state": "UNVERIFIED_DATA", "changes": [],
                "reason": [before.get("state"), after.get("state")]}
    lb = _metric_map(before.get("clocks", []), "clock")
    rb = _metric_map(after.get("clocks", []), "clock")
    if lb is None or rb is None:
        return {"state": "AMBIGUOUS", "changes": []}
    if set(lb) != set(rb):
        return {
            "state": "INCOMPATIBLE_CLOCK_SET", "changes": [],
            "baseline_clocks": sorted(lb), "candidate_clocks": sorted(rb),
        }

    changes: list[dict[str, Any]] = []
    for clock in sorted(lb):
        left, right = lb[clock], rb[clock]
        lreq, rreq = left["requested"], right["requested"]
        if (left.get("constraints") != "CONSTRAINED"
                or right.get("constraints") != "CONSTRAINED"
                or lreq.get("state") != "KNOWN" or rreq.get("state") != "KNOWN"):
            return {"state": "UNKNOWN_CONSTRAINTS", "changes": [], "clock": clock}
        if lreq.get("unit") != rreq.get("unit") or lreq.get("value") != rreq.get("value"):
            return {"state": "INCOMPATIBLE_CLOCK_REQUESTS", "changes": [], "clock": clock}

    # Даже совпавшие запрошенные частоты не подтверждают равенство
    # multicycle/false path/IO constraints, поэтому дельта остаётся null.
    for clock in sorted(lb):
        left, right = lb[clock], rb[clock]
        changed = (left.get("estimated") != right.get("estimated")
                   or left.get("slack") != right.get("slack"))
        if not changed or len(changes) >= MAX_CHANGED_ITEMS:
            continue
        changes.append({
            "clock": clock,
            "state": "OBSERVED_NOT_COMPARABLE",
            "baseline_estimated": left["estimated"],
            "candidate_estimated": right["estimated"],
            "baseline_slack": left["slack"],
            "candidate_slack": right["slack"],
            "estimated_delta": None,
            "slack_delta": None,
            "baseline_evidence": _evidence(left.get("evidence")),
            "candidate_evidence": _evidence(right.get("evidence")),
            "baseline_header": _evidence(left.get("header_evidence")),
            "candidate_header": _evidence(right.get("header_evidence")),
        })
    return {
        "state": "UNVERIFIED_FULL_CONSTRAINTS",
        "clock_request_match": True,
        "observed_changes": changes,
        "changes": [],
        "numeric_deltas_permitted": False,
        "kind": "SYNTHESIS_ESTIMATE",
        "implementation_timing": False,
    }


def compare_srr(baseline_path: str, candidate_path: str,
                encoding: str = "auto") -> dict[str, Any]:
    """Сравнить два локальных отчёта, не выполняя EDA и не придумывая PASS."""
    left = read_srr_report(baseline_path, encoding=encoding, limit=200)
    if left.get("state") != "PARSED":
        return {"state": "INPUT_ERROR", "side": "baseline",
                "error_code": left.get("error_code"), "synthesis_status": "UNKNOWN"}
    right = read_srr_report(candidate_path, encoding=encoding, limit=200)
    if right.get("state") != "PARSED":
        return {"state": "INPUT_ERROR", "side": "candidate",
                "error_code": right.get("error_code"), "synthesis_status": "UNKNOWN"}
    context = _context(left, right)
    return {
        "state": "IDENTICAL_BYTES" if left["report_sha256"] == right["report_sha256"]
                 else context["state"],
        "baseline": _snapshot(left),
        "candidate": _snapshot(right),
        "context": context,
        "diagnostics": _diagnostics(left, right),
        "resources": _resources(left, right, context["state"]),
        "timing": _timing(left, right, context["state"]),
        "synthesis_status": "UNKNOWN",
        "executed": False,
        "post_route_timing": False,
    }
