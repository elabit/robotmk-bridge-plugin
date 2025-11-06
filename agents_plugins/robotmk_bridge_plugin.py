#!/usr/bin/env python3

"""Robotmk-Bridge agent plugin (minimal start)

This module will grow into the agent-side plugin that reads configured
test-result paths, dispatches handlers and writes Robotmk JSON results.
For now it contains a config loader used by the agent.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import glob
import stat
import oxygen


DEFAULT_CONFIG_PATH = "/etc/check_mk/robotmk-bridge-plugin.json"


@dataclass
class Config:
    path: str
    handler: str
    plan: Optional[str] = None
    max_age: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def load_config(path: Optional[str] = None) -> List[Config]:
    """Load and validate the bakery/agent config JSON.

    The function attempts to read `path` if provided, otherwise falls back
    to `DEFAULT_CONFIG_PATH`. The expected format is a JSON object with a
    top-level "paths" array. Each entry must at least provide `path`,
    `handler`, and `max_age` keys.

    Returns a list of PathConfig instances.
    Raises FileNotFoundError or ValueError for invalid content.
    """
    config_path = path or DEFAULT_CONFIG_PATH

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)

    if not isinstance(raw, dict):
        raise ValueError("Config file must be a JSON object")

    paths = raw.get("paths")
    if paths is None:
        raise ValueError("Config missing required 'paths' array")
    if not isinstance(paths, list):
        raise ValueError("Config 'paths' must be a list")

    result: List[Config] = []
    for i, entry in enumerate(paths):
        if not isinstance(entry, dict):
            raise ValueError(f"Path entry at index {i} must be an object")

        p = entry.get("path")
        h = entry.get("handler")
        if not p or not isinstance(p, str):
            raise ValueError(f"Path entry at index {i} missing valid 'path'")
        if not h or not isinstance(h, str):
            raise ValueError(f"Path entry at index {i} missing valid 'handler'")

        plan = entry.get("plan")
        if plan is not None and not isinstance(plan, str):
            raise ValueError(f"Path entry at index {i} has non-string 'plan'")

        max_age_value = entry.get("max_age")
        if max_age_value is None:
            raise ValueError(f"Path entry at index {i} missing required 'max_age'")
        if not isinstance(max_age_value, int):
            raise ValueError(f"Path entry at index {i} must provide integer 'max_age'")
        if max_age_value < 0:
            raise ValueError(f"Path entry at index {i} has negative 'max_age'")

        metadata_raw = entry.get("metadata")
        if metadata_raw is None:
            metadata = {}
        elif isinstance(metadata_raw, dict):
            metadata = dict(metadata_raw)
        else:
            raise ValueError(f"Path entry at index {i} must have object metadata if provided")

        result.append(
            Config(path=p, handler=h, plan=plan, max_age=max_age_value, metadata=metadata)
        )

    return result


def _demo_main(cfg_path: Optional[str] = None) -> int:
    """Small demo runner used when invoking this file directly.

    Prints parsed config entries to stdout. Returns exit code 0 on success.
    """
    try:
        configs = load_config(cfg_path)
    except Exception as e:  # keep narrow in production code
        print(f"Error loading config: {e}")
        return 2

    print(f"Loaded {len(configs)} path(s):")
    for c in configs:
        print(
            " - path={path!r}, handler={handler!r}, plan={plan!r}, max_age={max_age}".format(
                path=c.path, handler=c.handler, plan=c.plan, max_age=c.max_age
            )
        )

    return 0


if __name__ == "__main__":
    import sys

    cfg = sys.argv[1] if len(sys.argv) > 1 else None
    raise SystemExit(_demo_main(cfg))


def discover_files(
    path_pattern: str, max_age: Optional[int] = None, reference_time: Optional[float] = None
) -> List[str]:
    """Discover files for a concrete path or a glob pattern.

    - If `path_pattern` contains glob chars, expand them.
    - If it is a concrete path, return it if it exists, otherwise return
      an empty list.
    - When `max_age` is provided, exclude files older than `reference_time - max_age`.
    """
    # simple heuristic: any glob-special char
    if any(ch in path_pattern for ch in "*?[]{}"):
        candidates = sorted(glob.glob(path_pattern))
    else:
        candidates = [path_pattern] if os.path.exists(path_pattern) else []

    if max_age is None:
        return candidates

    reference = reference_time if reference_time is not None else time.time()
    cutoff = reference - max_age
    fresh: List[str] = []
    for candidate in candidates:
        try:
            mtime = os.path.getmtime(candidate)
        except OSError:
            continue
        if mtime >= cutoff:
            fresh.append(candidate)

    return fresh


def stat_file(path: str) -> Dict[str, Any]:
    """Return basic file stats and readability checks.

    Result keys: exists (bool), readable (bool), size (int|None), mtime (float|None), error (str|None)
    """
    info: Dict[str, Any] = {"path": path, "exists": False, "readable": False, "size": None, "mtime": None, "error": None}
    try:
        if not os.path.exists(path):
            info["error"] = "not found"
            return info

        info["exists"] = True
        st = os.stat(path)
        info["size"] = st.st_size
        info["mtime"] = st.st_mtime
        # readability: try opening for read
        try:
            with open(path, "rb"):
                pass
            info["readable"] = True
        except Exception as e:
            info["error"] = f"unreadable: {e}"

    except Exception as e:
        info["error"] = str(e)

    return info
