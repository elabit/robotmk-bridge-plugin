#!/usr/bin/env python3

from cmk.agent_based.v2 import AgentSection, CheckPlugin, Service, Result, State, Metric, IgnoreResultsError
from cmk.ccc.exceptions import MKGeneralException
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

import json

def parse_robotmk_bridge(string_table):
    try:
        json_data = string_table[0][0]
        data = json.loads(json_data)
    except json.JSONDecodeError as e:
        raise MKGeneralException(f"Invalid JSON payload: {e}")
    return data

# ----------------------------------------------------------------------
# Status service
# ----------------------------------------------------------------------

def discover_robotmk_bridge(section: Dict[str, Any]):
    if section:
        yield Service()

def check_robotmk_bridge(section: Dict[str, Any]):
    plans = section.get("plans", {}) or {}
    summary = section.get("summary", {})
    runtime_s = float(section.get("runtime_s", 0.0))

    configs = int(summary.get("configs", 0))
    files_total = int(summary.get("files_total", 0))
    files_success = int(summary.get("files_success", 0))
    files_missing = int(summary.get("files_missing", 0))
    files_error = int(summary.get("files_error", 0))

    if files_error > 0:
        state = State.CRIT
    elif files_missing > 0:
        state = State.WARN
    else:
        state = State.OK

    msg = (
        f"{configs} configs, {files_total} files "
        f"(success: {files_success}, missing: {files_missing}, error: {files_error}), "
        f"conversion runtime: {runtime_s:.3f}s"
    )

    details_lines = []
    details_lines = plan_list(plans, details_lines)
    details_lines = "\n".join(details_lines)

    yield Result(state=state, summary=msg, details=details_lines)

    # A few useful metrics
    yield Metric("runtime_conversion", runtime_s)
    yield Metric("files_total", files_total)
    yield Metric("files_success", files_success)
    yield Metric("files_missing", files_missing)
    yield Metric("files_error", files_error)

check_plugin_robotmk_bridge = CheckPlugin(
    name = "robotmk_bridge",
    sections= ["robotmk_bridge"],
    service_name = "RMKBridge Status",
    discovery_function = discover_robotmk_bridge,
    check_function = check_robotmk_bridge,
)

# ----------------------------------------------------------------------
# Per-plan services
# ----------------------------------------------------------------------

def discover_robotmk_bridge_plan(section: Dict[str, Any]):
    """Create one service per plan."""
    plans = section.get("plans", {}) or {}
    for plan_name in plans.keys():
        yield Service(item=plan_name)

def check_robotmk_bridge_plan(item, section: Dict[str, Any]):
    """Check a single plan (item = plan name)."""
    plans = section.get("plans", {}) or {}
    plan_data = plans.get(item)

    if not plan_data:
        # TODO: What to do if no data are available? 
        # http://localhost:4999/cmk/check_mk/plugin-api/cmk.agent_based/v2.html#cmk.agent_based.v2.IgnoreResults
        yield IgnoreResultsError("Plan '{item}' not found in agent data")        
        # yield Result(
        #     state=State.UNKNOWN,
        #     summary=f"Plan '{item}' not found in agent data",
        # )
        # return

    handler = plan_data.get("handler", "unknown")    
    files = plan_data.get("files", []) or []

    files_total = len(files)
    files_success = sum(1 for f in files if f.get("status") == "success")
    files_error = sum(1 for f in files if f.get("status") == "error")
    files_missing = sum(1 for f in files if f.get("status") == "missing")

    # Aggregate runtime over all files for that plan
    runtime_s = sum(float(f.get("runtime_s") or 0.0) for f in files)

    # Determine state
    if files_error > 0:
        state = State.CRIT
    elif files_missing > 0:
        state = State.WARN
    else:
        state = State.OK

    summary = (
        f"Plan '{item}' (handler: {handler}) - "
        f"{files_total} files (success: {files_success}, "
        f"missing: {files_missing}, error: {files_error}), "
        f"conversion runtime: {runtime_s:.3f}s"
    )

    details_lines = [
        f"Plan name: {item}",
        f"RobotmkBridge Handler: {handler}",
        "",
        "Converted result files:",
    ]

    if not files:
        details_lines.append("  (no files reported)")
    else:
        # invisible spaces
        indent1 = "\xa0" * 2
        indent2 = "\xa0" * 4
        for idx, f in enumerate(files, start=1):
            details_lines.append(f"{indent1}File #{idx}:")
            details_lines.append(f"{indent2}Status: {f.get('status', 'unknown')}")
            details_lines.append(
                f"{indent2}Conversion runtime: {float(f.get('runtime_s') or 0.0):.3f}s"
            )
            timestamp = f.get("timestamp")
            details_lines.append(f"{indent2}Last conversion: {timestamp_to_iso(timestamp)}")

            details_lines.append(
                f"{indent2}Source path: {f.get('source_path', 'n/a')}"
            )
            details_lines.append(
                f"{indent2}Destination path: {f.get('result_path', 'n/a')}"
            )
            message = f.get("message")
            if message:
                details_lines.append(f"{indent2}Message: {message}")
            details_lines.append("")  # blank line between files

    details = "\n".join(details_lines)

    yield Result(state=state, summary=summary, details=details)

    # Metrics per plan
    yield Metric("plan_runtime_conversion", runtime_s)
    yield Metric("plan_files_total", files_total)
    yield Metric("plan_files_success", files_success)
    yield Metric("plan_files_missing", files_missing)
    yield Metric("plan_files_error", files_error)

check_plugin_robotmk_bridge_plan = CheckPlugin(
    name = "robotmk_bridge_plan",
    sections= ["robotmk_bridge"],
    service_name = "RMKBridge Plan %s",
    discovery_function = discover_robotmk_bridge_plan,
    check_function = check_robotmk_bridge_plan,
)

# ----------------------------------------------------------------------
# 
# ----------------------------------------------------------------------


agent_section_robotmk_bridge = AgentSection(
    name = "robotmk_bridge",
    parsed_section_name = "robotmk_bridge",
    parse_function = parse_robotmk_bridge
)

def timestamp_to_iso(t):
    if t:
        iso_ts = datetime.fromtimestamp(t, tz=timezone.utc).isoformat()
    else:
        iso_ts = "n/a"
    return iso_ts

def plan_list(plans, lines):
    # invisible spaces
    indent1 = "\xa0" * 2
    indent2 = indent1 + "\xa0" * 2
    lines.append("Plans:")
    for p, data in plans.items():
        lines.append(f"{indent1}{p} (Handler: {data['handler']}):")
        file_list_lines = []
        file_list_lines = file_list(data['files'], file_list_lines, initial_indent=indent2)
        lines += file_list_lines
    return lines
        


def file_list(files, lines, initial_indent=""):
    # Generates the list of converted files
    if not files:
        lines.append("  (no files reported)")
    else:
        # invisible spaces
        indent1 = initial_indent + "\xa0" * 2
        indent2 = indent1 + "\xa0" * 2
        #lines.append(f"{initial_indent}Files:")
        for idx, f in enumerate(files, start=1):
            lines.append(f"{indent1}File #{idx}:")
            lines.append(f"{indent2}Status: {f.get('status', 'unknown')}")
            lines.append(
                f"{indent2}Conversion runtime: {float(f.get('runtime_s') or 0.0):.3f}s"
            )
            timestamp = f.get("timestamp")
            lines.append(f"{indent2}Last conversion: {timestamp_to_iso(timestamp)}")

            lines.append(
                f"{indent2}Source path: {f.get('source_path', 'n/a')}"
            )
            lines.append(
                f"{indent2}Destination path: {f.get('result_path', 'n/a')}"
            )
            message = f.get("message")
            if message:
                lines.append(f"{indent2}Message: {message}")
            lines.append("")  # blank line between files    
    return lines