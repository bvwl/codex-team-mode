#!/usr/bin/env python3
"""Summarize locally retained Codex token usage by model, task, and Agent."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


RATE_DATE = "2026-07-18"
RATE_SOURCE = "https://help.openai.com/en/articles/20001106-codex-rate-card"
RATES = {
    "gpt-5.6-luna": {"input": 25.0, "cached": 2.5, "output": 150.0},
    "gpt-5.6-terra": {"input": 62.5, "cached": 6.25, "output": 375.0},
    "gpt-5.6-sol": {"input": 125.0, "cached": 12.5, "output": 750.0},
}
PROFILE_MANIFEST = Path(__file__).resolve().parents[1] / "references" / "profiles.json"


def default_sessions_root() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    return (Path(codex_home) if codex_home else Path.home() / ".codex") / "sessions"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report locally retained Codex token usage and estimated Standard credits by model."
    )
    period = parser.add_mutually_exclusive_group()
    period.add_argument("--days", type=int, default=1, help="Include the last N local calendar days (default: 1).")
    period.add_argument("--all", action="store_true", help="Include every retained local session.")
    period.add_argument(
        "--task-id",
        metavar="ID|current",
        help="Include one root task and its subagents; 'current' reads CODEX_THREAD_ID.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--by-agent", action="store_true", help="Also group usage by custom Agent role.")
    parser.add_argument("--by-session", action="store_true", help="Also show each root or subagent session separately.")
    parser.add_argument(
        "--audit-routing",
        action="store_true",
        help="Check child role, model, effort, sandbox, and nesting against the bundled profile manifest.",
    )
    parser.add_argument("--sessions-root", type=Path, default=default_sessions_root(), help="Override the sessions directory.")
    args = parser.parse_args()
    if not args.all and args.days < 1:
        parser.error("--days must be at least 1")
    if args.task_id == "current":
        args.task_id = os.environ.get("CODEX_THREAD_ID")
        if not args.task_id:
            parser.error("--task-id current requires CODEX_THREAD_ID")
    return args


def load_profile_manifest(path: Path = PROFILE_MANIFEST) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("profiles"), dict):
        raise ValueError(f"Unsupported or malformed profile manifest: {path}")
    profiles = data["profiles"]
    required = {"filename", "working_role", "model", "effort", "sandbox"}
    for name, expected in profiles.items():
        if not isinstance(expected, dict):
            raise ValueError(f"Profile manifest entry must be an object: {name}")
        missing = required - expected.keys()
        if missing:
            raise ValueError(f"Profile manifest entry {name!r} is missing: {sorted(missing)}")
        filename = expected["filename"]
        if not isinstance(filename, str) or Path(filename).name != filename:
            raise ValueError(f"Profile manifest entry {name!r} has an unsafe filename")
        for field in ("model", "effort", "sandbox"):
            if not isinstance(expected[field], str) or not expected[field]:
                raise ValueError(f"Profile manifest entry {name!r} has an invalid {field}")
        if not isinstance(expected["working_role"], bool):
            raise ValueError(f"Profile manifest entry {name!r} has an invalid working_role")
    return profiles


def session_date(path: Path, root: Path) -> date:
    try:
        year, month, day = path.relative_to(root).parts[:3]
        return date(int(year), int(month), int(day))
    except (ValueError, IndexError):
        return date.fromtimestamp(path.stat().st_mtime)


def trace_files(root: Path, cutoff: date | None) -> Iterable[Path]:
    for path in root.rglob("*.jsonl"):
        if cutoff is None or session_date(path, root) >= cutoff:
            yield path


def nested_spawn(payload: dict[str, Any]) -> dict[str, Any]:
    source = payload.get("source")
    if not isinstance(source, dict):
        return {}
    subagent = source.get("subagent")
    if not isinstance(subagent, dict):
        return {}
    spawn = subagent.get("thread_spawn")
    return spawn if isinstance(spawn, dict) else {}


def read_trace_metadata(path: Path) -> tuple[dict[str, Any], int]:
    malformed = 0
    try:
        lines = path.open("r", encoding="utf-8")
    except OSError:
        return {}, malformed
    with lines:
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if not isinstance(event, dict):
                malformed += 1
                continue
            if event.get("type") != "session_meta":
                continue
            payload = event.get("payload")
            if not isinstance(payload, dict):
                malformed += 1
                continue
            spawn = nested_spawn(payload)
            session_id = payload.get("id") or path.stem
            parent_thread_id = payload.get("parent_thread_id") or spawn.get("parent_thread_id")
            is_child = bool(parent_thread_id or spawn)
            role = payload.get("agent_role") or spawn.get("agent_role")
            return {
                "path": path,
                "session_id": session_id,
                "task_hint": payload.get("session_id"),
                "parent_thread_id": parent_thread_id,
                "agent_role": role or ("subagent/unknown" if is_child else "main"),
                "agent_path": payload.get("agent_path") or spawn.get("agent_path"),
                "cwd": payload.get("cwd"),
            }, malformed
    return {}, malformed


def resolve_trace_tasks(metadata: list[dict[str, Any]]) -> None:
    by_session = {item["session_id"]: item for item in metadata}

    def resolve(item: dict[str, Any]) -> str:
        task_hint = item.get("task_hint")
        if isinstance(task_hint, str) and task_hint:
            return task_hint
        current = item
        seen: set[str] = set()
        while True:
            session_id = str(current["session_id"])
            if session_id in seen:
                return session_id
            seen.add(session_id)
            parent = current.get("parent_thread_id")
            if not isinstance(parent, str) or not parent:
                return session_id
            parent_metadata = by_session.get(parent)
            if parent_metadata is None:
                return parent
            task_hint = parent_metadata.get("task_hint")
            if isinstance(task_hint, str) and task_hint:
                return task_hint
            current = parent_metadata

    for item in metadata:
        item["task_id"] = resolve(item)


def discover_traces(root: Path, cutoff: date | None) -> tuple[list[dict[str, Any]], int, int]:
    metadata: list[dict[str, Any]] = []
    file_count = 0
    malformed = 0
    for path in trace_files(root, cutoff):
        file_count += 1
        item, item_malformed = read_trace_metadata(path)
        malformed += item_malformed
        if item:
            metadata.append(item)
    resolve_trace_tasks(metadata)
    by_session = {item["session_id"]: item for item in metadata}
    def depth(item: dict[str, Any]) -> int:
        current = item
        seen: set[str] = set()
        value = 0
        while True:
            sid = str(current.get("session_id"))
            if sid in seen:
                return value
            seen.add(sid)
            parent = current.get("parent_thread_id")
            if not parent or parent not in by_session:
                return value
            value += 1
            current = by_session[parent]
    for item in metadata:
        item["depth"] = depth(item)
    return metadata, file_count, malformed


def parse_timestamp(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (ValueError, OverflowError, OSError):
            return None
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def resolve_requested_task(metadata: list[dict[str, Any]], requested_id: str | None) -> str | None:
    if requested_id is None:
        return None
    for item in metadata:
        if item["session_id"] == requested_id:
            return str(item["task_id"])
    return requested_id


def blank_usage() -> dict[str, int]:
    return {"events": 0, "input": 0, "cached": 0, "output": 0, "reasoning": 0}


def add_usage(target: dict[str, int], usage: Any) -> bool:
    if not isinstance(usage, dict):
        return False
    parsed: dict[str, int] = {}
    for field in (
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
        "reasoning_output_tokens",
    ):
        value = usage.get(field, 0)
        if value is None:
            value = 0
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return False
        parsed[field] = value
    if parsed["cached_input_tokens"] > parsed["input_tokens"]:
        return False
    target["events"] += 1
    target["input"] += parsed["input_tokens"]
    target["cached"] += parsed["cached_input_tokens"]
    target["output"] += parsed["output_tokens"]
    target["reasoning"] += parsed["reasoning_output_tokens"]
    return True


def merge_usage(target: dict[str, int], source: dict[str, int]) -> None:
    for key in target:
        target[key] += source[key]


def scan(
    root: Path,
    cutoff: date | None,
    task_id: str | None = None,
) -> tuple[
    dict[str, dict[str, int]],
    dict[str, dict[str, int]],
    list[dict[str, Any]],
    int,
    int,
    int,
    str | None,
]:
    by_model: dict[str, dict[str, int]] = defaultdict(blank_usage)
    by_agent: dict[str, dict[str, int]] = defaultdict(blank_usage)
    sessions: list[dict[str, Any]] = []
    metadata, file_count, malformed_lines = discover_traces(root, cutoff)
    resolved_task_id = resolve_requested_task(metadata, task_id)
    included_count = 0

    for trace in metadata:
        if resolved_task_id is not None and trace["task_id"] != resolved_task_id:
            continue
        path = trace["path"]
        included_count += 1
        model: str | None = None
        effort: str | None = None
        usage_by_segment: dict[tuple[str, str | None], dict[str, int]] = defaultdict(blank_usage)
        timestamps: list[datetime] = []
        sandboxes: set[str] = set()
        approvals: set[str] = set()
        interrupted_count = 0
        has_complete = False
        last_terminal: str | None = None
        try:
            lines = path.open("r", encoding="utf-8")
        except OSError:
            continue
        seen_metadata = False
        with lines:
            for line in lines:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    if seen_metadata:
                        malformed_lines += 1
                    continue
                if not isinstance(event, dict):
                    if seen_metadata:
                        malformed_lines += 1
                    continue
                payload = event.get("payload")
                if not isinstance(payload, dict):
                    if seen_metadata:
                        malformed_lines += 1
                    continue
                timestamp = parse_timestamp(event.get("timestamp") or payload.get("timestamp"))
                if timestamp:
                    timestamps.append(timestamp)
                if event.get("type") == "session_meta":
                    seen_metadata = True
                elif event.get("type") == "turn_context":
                    model = payload.get("model") or model
                    effort = payload.get("effort") or effort
                    sandbox = payload.get("sandbox_policy")
                    if isinstance(sandbox, dict):
                        sandbox = sandbox.get("type")
                    if isinstance(sandbox, str) and sandbox:
                        sandboxes.add(sandbox)
                    approval = payload.get("approval_policy")
                    if isinstance(approval, str) and approval:
                        approvals.add(approval)
                elif event.get("type") == "event_msg":
                    event_kind = payload.get("type")
                    if event_kind == "task_complete":
                        has_complete = True
                        last_terminal = "completed"
                    elif event_kind == "task_started":
                        last_terminal = None
                    elif event_kind == "turn_aborted":
                        interrupted_count += 1
                        last_terminal = "interrupted"
                if (
                    event.get("type") == "event_msg"
                    and payload.get("type") == "token_count"
                    and model
                ):
                    info = payload.get("info")
                    if not isinstance(info, dict):
                        malformed_lines += 1
                        continue
                    usage = info.get("last_token_usage")
                    if usage is not None and not add_usage(usage_by_segment[(model, effort)], usage):
                        malformed_lines += 1
        role = trace["agent_role"]
        started = min(timestamps) if timestamps else None
        ended = max(timestamps) if timestamps else None
        terminal = last_terminal or "incomplete"
        if not usage_by_segment and model:
            usage_by_segment[(model, effort)]
        for (session_model, session_effort), usage in usage_by_segment.items():
            merge_usage(by_model[session_model], usage)
            merge_usage(by_agent[f"{role} · {session_model}"], usage)
            sessions.append({
                **trace,
                "model": session_model,
                "effort": session_effort,
                "usage": usage,
                "started_at": started.isoformat().replace("+00:00", "Z") if started else None,
                "ended_at": ended.isoformat().replace("+00:00", "Z") if ended else None,
                "elapsed_seconds": (ended - started).total_seconds() if started and ended else None,
                "terminal_status": terminal,
                "final_report_present": has_complete,
                "interrupted_count": interrupted_count,
                "effective_sandbox": sorted(sandboxes),
                "approval_policy": sorted(approvals),
            })
    return (
        dict(by_model),
        dict(by_agent),
        sessions,
        file_count,
        included_count,
        malformed_lines,
        resolved_task_id,
    )


def usage_row(name: str, usage: dict[str, int]) -> dict[str, Any]:
    uncached = max(usage["input"] - usage["cached"], 0)
    total = usage["input"] + usage["output"]
    rate = RATES.get(name.split(" · ")[-1])
    credits = None
    credit_breakdown = None
    if rate:
        credit_breakdown = {
            "uncached_input": uncached * rate["input"] / 1_000_000,
            "cached_input": usage["cached"] * rate["cached"] / 1_000_000,
            "output": usage["output"] * rate["output"] / 1_000_000,
        }
        credits = sum(credit_breakdown.values())
    return {
        "name": name,
        "token_events": usage["events"],
        "total_processed_tokens": total,
        "input_tokens": usage["input"],
        "cached_input_tokens": usage["cached"],
        "uncached_input_tokens": uncached,
        "output_tokens": usage["output"],
        "reasoning_output_tokens": usage["reasoning"],
        "estimated_standard_credit_breakdown": credit_breakdown,
        "estimated_standard_credits": credits,
        "effective_processed_tokens_per_credit": total / credits if credits else None,
    }


def rate_card_rows() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for model, rate in RATES.items():
        result.append({
            "model": model,
            "credits_per_million_tokens": {
                "uncached_input": rate["input"],
                "cached_input": rate["cached"],
                "output": rate["output"],
            },
            "tokens_per_credit": {
                "uncached_input": 1_000_000 / rate["input"],
                "cached_input": 1_000_000 / rate["cached"],
                "output": 1_000_000 / rate["output"],
            },
        })
    return result


def usage_summary(data: list[dict[str, Any]]) -> dict[str, Any]:
    total_tokens = sum(row["total_processed_tokens"] for row in data)
    known_credits = sum(row["estimated_standard_credits"] or 0 for row in data)
    return {
        "token_events": sum(row["token_events"] for row in data),
        "total_processed_tokens": total_tokens,
        "input_tokens": sum(row["input_tokens"] for row in data),
        "cached_input_tokens": sum(row["cached_input_tokens"] for row in data),
        "uncached_input_tokens": sum(row["uncached_input_tokens"] for row in data),
        "output_tokens": sum(row["output_tokens"] for row in data),
        "reasoning_output_tokens": sum(row["reasoning_output_tokens"] for row in data),
        "estimated_standard_credits": known_credits,
        "effective_processed_tokens_per_credit": total_tokens / known_credits if known_credits else None,
        "unpriced_models": [row["name"] for row in data if row["estimated_standard_credits"] is None],
    }


def add_credit_shares(result: list[dict[str, Any]]) -> list[dict[str, Any]]:
    known_total = sum(row["estimated_standard_credits"] or 0 for row in result)
    for row in result:
        credits = row["estimated_standard_credits"]
        row["known_credit_share_percent"] = (credits / known_total * 100) if credits is not None and known_total else None
    return result


def rows(source: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
    return add_credit_shares([usage_row(name, usage) for name, usage in sorted(source.items())])


def session_rows(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for session in sessions:
        role = session["agent_role"]
        model = session["model"]
        result.append({
            **usage_row(f"{role} · {model}", session["usage"]),
            "session_id": session["session_id"],
            "task_id": session["task_id"],
            "parent_thread_id": session["parent_thread_id"],
            "agent_role": role,
            "agent_path": session["agent_path"],
            "model": model,
            "effort": session["effort"],
            "cwd": session["cwd"],
            "started_at": session.get("started_at"),
            "ended_at": session.get("ended_at"),
            "elapsed_seconds": session.get("elapsed_seconds"),
            "terminal_status": session.get("terminal_status", "incomplete"),
            "final_report_present": session.get("final_report_present", False),
            "interrupted_count": session.get("interrupted_count", 0),
            "effective_sandbox": session.get("effective_sandbox", []),
            "approval_policy": session.get("approval_policy", []),
            "depth": session.get("depth", 0),
        })
    result.sort(key=lambda row: (row["agent_path"] or "/root", row["session_id"], row["model"]))
    return add_credit_shares(result)


def summarize_sessions(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse model/effort usage segments into one runtime record per session."""
    summaries: dict[str, dict[str, Any]] = {}
    for row in data:
        session_id = row["session_id"]
        summary = summaries.get(session_id)
        if summary is None:
            summary = {
                "session_id": session_id,
                "task_id": row["task_id"],
                "parent_thread_id": row["parent_thread_id"],
                "agent_role": row["agent_role"],
                "agent_path": row["agent_path"],
                "cwd": row["cwd"],
                "started_at": row.get("started_at"),
                "ended_at": row.get("ended_at"),
                "elapsed_seconds": row.get("elapsed_seconds"),
                "terminal_status": row.get("terminal_status", "incomplete"),
                "task_complete_seen": row.get("final_report_present", False),
                "interrupted_count": row.get("interrupted_count", 0),
                "effective_sandbox": row.get("effective_sandbox", []),
                "approval_policy": row.get("approval_policy", []),
                "depth": row.get("depth", 0),
                "usage_segments": [],
            }
            summaries[session_id] = summary
        summary["usage_segments"].append({
            "model": row["model"],
            "effort": row["effort"],
            "total_processed_tokens": row["total_processed_tokens"],
            "estimated_standard_credits": row["estimated_standard_credits"],
        })
    return sorted(
        summaries.values(),
        key=lambda row: (row["agent_path"] or "/root", row["session_id"]),
    )


def audit_routing(
    session_details: list[dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    def add(severity: str, code: str, row: dict[str, Any], message: str) -> None:
        key = (row["session_id"], code, message)
        if key in seen:
            return
        seen.add(key)
        findings.append({
            "severity": severity,
            "code": code,
            "session_id": row["session_id"],
            "agent_role": row["agent_role"],
            "agent_path": row["agent_path"],
            "message": message,
        })

    for row in session_details:
        role = row["agent_role"]
        if role == "main":
            continue
        if row.get("depth", 0) > 1:
            add(
                "error",
                "nested_subagent",
                row,
                f"subagent depth is {row['depth']}; Team Mode allows direct children only",
            )
        if role == "subagent/unknown":
            add(
                "warning",
                "unknown_agent_role",
                row,
                "child role is unknown; this may be a guard probe or an omitted agent_type",
            )
            continue
        expected = profiles.get(role)
        if expected is None:
            add("error", "unrecognized_agent_role", row, f"role {role!r} is not in the profile manifest")
            continue
        if role == "default":
            add(
                "error",
                "dispatch_guard_selected",
                row,
                "default is a dispatch guard and must not perform working-agent tasks",
            )
        if row["model"] != expected["model"]:
            add(
                "error",
                "model_mismatch",
                row,
                f"model is {row['model']!r}; expected {expected['model']!r}",
            )
        if row["effort"] != expected["effort"]:
            add(
                "error",
                "effort_mismatch",
                row,
                f"effort is {row['effort']!r}; expected {expected['effort']!r}",
            )
        sandboxes = set(row.get("effective_sandbox") or [])
        if not sandboxes:
            add(
                "warning",
                "sandbox_unobserved",
                row,
                "no effective sandbox was observed in local turn_context events",
            )
        elif "danger-full-access" in sandboxes:
            add(
                "error",
                "danger_full_access",
                row,
                "effective sandbox includes danger-full-access",
            )
        elif expected["sandbox"] == "read-only" and sandboxes != {"read-only"}:
            add(
                "error",
                "readonly_boundary_mismatch",
                row,
                f"effective sandbox is {sorted(sandboxes)!r}; expected read-only",
            )
        elif expected["sandbox"] not in sandboxes:
            add(
                "warning",
                "sandbox_mismatch",
                row,
                f"effective sandbox is {sorted(sandboxes)!r}; profile default is {expected['sandbox']!r}",
            )

    counts = {
        severity: sum(1 for finding in findings if finding["severity"] == severity)
        for severity in ("error", "warning")
    }
    verdict = "fail" if counts["error"] else ("warn" if counts["warning"] else "pass")
    return {"verdict": verdict, "counts": counts, "findings": findings}


def print_table(title: str, data: list[dict[str, Any]]) -> None:
    print(title)
    print(
        f"{'Model / Agent':<34} {'Processed':>14} {'Uncached':>12} {'Cached':>12} "
        f"{'Output':>11} {'Reason':>10} {'Credits*':>11} {'Tok/Credit':>12} {'Share':>8}"
    )
    print("-" * 136)
    for row in data:
        credits = row["estimated_standard_credits"]
        share = row["known_credit_share_percent"]
        tokens_per_credit = row["effective_processed_tokens_per_credit"]
        credits_text = f"{credits:,.2f}" if credits is not None else "n/a"
        share_text = f"{share:.2f}%" if share is not None else "n/a"
        tokens_per_credit_text = f"{tokens_per_credit:,.0f}" if tokens_per_credit is not None else "n/a"
        print(
            f"{row['name']:<34} "
            f"{row['total_processed_tokens']:>14,} "
            f"{row['uncached_input_tokens']:>12,} "
            f"{row['cached_input_tokens']:>12,} "
            f"{row['output_tokens']:>11,} "
            f"{row['reasoning_output_tokens']:>10,} "
            f"{credits_text:>11} "
            f"{tokens_per_credit_text:>12} "
            f"{share_text:>8}"
        )
    summary = usage_summary(data)
    effective = summary["effective_processed_tokens_per_credit"]
    effective_text = f"{effective:,.0f}" if effective is not None else "n/a"
    print("-" * 136)
    print(
        f"{'TOTAL':<34} "
        f"{summary['total_processed_tokens']:>14,} "
        f"{summary['uncached_input_tokens']:>12,} "
        f"{summary['cached_input_tokens']:>12,} "
        f"{summary['output_tokens']:>11,} "
        f"{summary['reasoning_output_tokens']:>10,} "
        f"{summary['estimated_standard_credits']:>11,.2f} "
        f"{effective_text:>12} "
        f"{'100.00%':>8}"
    )
    print()


def print_session_table(data: list[dict[str, Any]]) -> None:
    print("By session / model segment")
    print(
        f"{'Role / Model':<26} {'Agent path':<22} {'Status':<11} {'Elapsed':>8} "
        f"{'Sandbox':<16} {'Processed':>11} {'Uncached':>10} {'Cached':>10} {'Output':>9} {'Credits*':>10}"
    )
    print("-" * 144)
    for row in data:
        credits = row["estimated_standard_credits"]
        credits_text = f"{credits:,.2f}" if credits is not None else "n/a"
        elapsed = f"{row['elapsed_seconds']:.1f}s" if row.get("elapsed_seconds") is not None else "n/a"
        sandbox = ",".join(row.get("effective_sandbox") or []) or "n/a"
        print(
            f"{row['name']:<26} {(row['agent_path'] or '/root'):<22} "
            f"{row.get('terminal_status', 'incomplete'):<11} {elapsed:>8} {sandbox:<16} "
            f"{row['total_processed_tokens']:>11,} {row['uncached_input_tokens']:>10,} "
            f"{row['cached_input_tokens']:>10,} {row['output_tokens']:>9,} {credits_text:>10}"
        )
    print()


def print_routing_audit(audit: dict[str, Any]) -> None:
    counts = audit["counts"]
    print(
        f"Routing audit: {audit['verdict'].upper()} · "
        f"{counts['error']} error(s) · {counts['warning']} warning(s)"
    )
    for finding in audit["findings"]:
        print(
            f"- {finding['severity'].upper()} {finding['code']} "
            f"[{finding['agent_path'] or finding['session_id']}]: {finding['message']}"
        )
    print()


def print_rate_card() -> None:
    print("Standard rate card · credits per 1M tokens / tokens per credit")
    print(
        f"{'Model':<18} {'Uncached cr':>11} {'Cached cr':>10} {'Output cr':>10} "
        f"{'Uncached tok/cr':>15} {'Cached tok/cr':>15} {'Output tok/cr':>14}"
    )
    print("-" * 110)
    for row in rate_card_rows():
        rates = row["credits_per_million_tokens"]
        equivalents = row["tokens_per_credit"]
        print(
            f"{row['model']:<18} {rates['uncached_input']:>10,.3f} {rates['cached_input']:>10,.3f} "
            f"{rates['output']:>10,.3f} {equivalents['uncached_input']:>14,.0f} "
            f"{equivalents['cached_input']:>15,.0f} {equivalents['output']:>14,.0f}"
        )
    print()


def main() -> int:
    args = parse_args()
    root = args.sessions_root.expanduser().resolve()
    if not root.is_dir():
        print(f"Sessions directory not found: {root}", file=sys.stderr)
        return 2

    cutoff = None if args.all or args.task_id else date.today() - timedelta(days=args.days - 1)
    (
        by_model,
        by_agent,
        sessions,
        file_count,
        included_count,
        malformed,
        resolved_task_id,
    ) = scan(root, cutoff, args.task_id)
    if args.task_id and not included_count:
        print(f"Task not found in retained local sessions: {args.task_id}", file=sys.stderr)
        return 2
    model_rows = rows(by_model)
    agent_rows = rows(by_agent) if args.by_agent else []
    all_session_details = session_rows(sessions)
    session_summaries = summarize_sessions(all_session_details)
    detailed_sessions = all_session_details if args.by_session else []
    routing_audit = None
    if args.audit_routing:
        try:
            routing_audit = audit_routing(all_session_details, load_profile_manifest())
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"Cannot load profile manifest: {exc}", file=sys.stderr)
            return 2
    if resolved_task_id:
        period = f"task {resolved_task_id}"
    else:
        period = "all retained sessions" if cutoff is None else f"{cutoff.isoformat()} through {date.today().isoformat()}"
    limitations = [
        "Local retained sessions only; ephemeral and unavailable remote sessions are excluded.",
        "Credits use configured Standard rates and do not detect mixed Fast usage.",
        "Account limits and resets remain authoritative in Codex /usage.",
        "Runtime fields come from local trace events; completed means only that the session has task_complete, not that artifact quality is assured.",
    ]
    status_counts = {status: sum(1 for row in session_summaries if row.get("terminal_status") == status)
                     for status in ("completed", "interrupted", "incomplete")}
    max_depth = max((row.get("depth", 0) for row in session_summaries), default=0)

    if args.json:
        print(json.dumps({
            "period": period,
            "task_id": resolved_task_id,
            "requested_task_or_session_id": args.task_id,
            "sessions_root": str(root),
            "files_scanned": file_count,
            "session_files_included": included_count,
            "malformed_lines_skipped": malformed,
            "credit_rates_as_of": RATE_DATE,
            "credit_rate_source": RATE_SOURCE,
            "credit_rates": rate_card_rows(),
            "summary": usage_summary(model_rows),
            "models": model_rows,
            "agents": agent_rows,
            "sessions": detailed_sessions,
            "session_summaries": session_summaries,
            "session_status_counts": status_counts,
            "max_subagent_depth": max_depth,
            "routing_audit": routing_audit,
            "limitations": limitations,
        }, ensure_ascii=False, indent=2))
        return 0

    print(f"Codex local usage · {period}")
    print(f"Scanned {file_count} session files · included {included_count} · Standard credit rates as of {RATE_DATE}")
    print("Processed tokens = input (cached included) + output; reasoning is already included in output.")
    print()
    print_table("By model", model_rows)
    if args.by_agent:
        print_table("By Agent role", agent_rows)
    if args.by_session:
        print_session_table(detailed_sessions)
    if routing_audit is not None:
        print_routing_audit(routing_audit)
    print_rate_card()
    print(f"Rate source: {RATE_SOURCE}")
    print("* Tok/Credit is the observed processed-token ratio for that row, not a universal conversion. ")
    print("* Estimated Standard credits. " + " ".join(limitations))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
