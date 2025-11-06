#!/usr/bin/env python3

"""Robotmk-Bridge agent plugin utilities.

Implements configuration loading, file discovery and handler integration for
Oxygen-based conversions. The full agent entry point will build on these
utilities in future implementation steps.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import dataclass, field
from inspect import Parameter, Signature, signature
from io import StringIO
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import glob

from oxygen.oxygen import OxygenCore
from oxygen.robot_interface import RobotInterface
from oxygen.utils import validate_with_deprecation_warning
from robot.api import ResultWriter


DEFAULT_CONFIG_PATH = "/etc/check_mk/robotmk-bridge-plugin.json"


@dataclass
class Config:
    path: str
    handler: str
    plan: Optional[str] = None
    max_age: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResolvedHandler:
    """Stores the resolved Oxygen handler instance and metadata."""

    handler_key: str
    handler: Any


@dataclass
class HandlerConversionResult:
    """Captures artifacts produced by an Oxygen handler conversion."""

    config: Config
    source_path: str
    handler_key: str
    handler_keyword: str
    parsed_results: Dict[str, Any]
    robot_output_xml: str
    log_html: Optional[str]
    duration_s: float


class HandlerError(RuntimeError):
    """Base exception for handler related failures."""


class HandlerResolutionError(HandlerError):
    """Raised when a configured handler name cannot be mapped to Oxygen."""


class HandlerConfigurationError(HandlerError):
    """Raised when handler arguments cannot be satisfied."""


class HandlerExecutionError(HandlerError):
    """Raised when handler execution fails."""


_OXYGENCORE: Optional[OxygenCore] = None


def _get_oxygenCORE() -> OxygenCore:
    """Return a cached OxygenCore instance."""

    global _OXYGENCORE
    if _OXYGENCORE is None:
        try:
            _OXYGENCORE = OxygenCore()
        except Exception as exc:  # noqa: BLE001 - propagate as domain error
            raise HandlerResolutionError(f"Failed to initialise Oxygen.OxygenCore: {exc}") from exc
    return _OXYGENCORE


def _iter_handler_keys(handler_name: str) -> Iterable[str]:
    """Yield plausible handler keys for the given configuration name."""

    names: List[str] = [handler_name]
    if not handler_name.startswith("oxygen."):
        names.append(f"oxygen.{handler_name}")
    return names


def resolve_handler(handler_name: str) -> ResolvedHandler:
    """Resolve a configured handler name to an Oxygen handler instance."""

    core = _get_oxygenCORE()
    handlers = core.handlers

    for candidate in _iter_handler_keys(handler_name):
        if candidate in handlers:
            return ResolvedHandler(handler_key=candidate, handler=handlers[candidate])

    normalized = handler_name.replace(" ", "_").lower()
    for key, handler in handlers.items():
        if getattr(handler, "keyword", None) == normalized:
            return ResolvedHandler(handler_key=key, handler=handler)

    available = ", ".join(sorted(handlers.keys()))
    raise HandlerResolutionError(
        f"Unknown handler '{handler_name}'. Available handlers: {available}"
    )


def _prepare_handler_call(handler: Any, source_path: str, metadata: Dict[str, Any]) -> Tuple[List[Any], Dict[str, Any]]:
    """
    Prepare positional and keyword arguments to call handler.parse_results(source, ...).

    This function introspects the handler.parse_results' signature and builds the
    positional (args) and keyword (kwargs) arguments that should be passed when
    invoking that method. It maps the provided source_path and metadata dictionary
    into the handler's declared parameters following these rules:

    Parameters
    - handler (Any): An object that exposes a parse_results method. Its signature is
        inspected to determine how to map source_path and metadata into arguments.
    - source_path (str): The path (or other primary input) to be supplied as the
        first argument to parse_results (positionally or as the first parameter's name).
    - metadata (Dict[str, Any]): A mapping of additional fields that may be bound
        to named parameters of parse_results or forwarded into a catch-all **kwargs.
    
    Behavior summary
    - The function inspects the signature of handler.parse_results using inspect.signature.
    - The first parameter of parse_results receives the source_path:
        - If the first parameter is positional (POSITIONAL_ONLY, POSITIONAL_OR_KEYWORD)
            or a var-positional (*args), source_path is appended to the positional args list.
        - If the first parameter is keyword-only, the source_path is placed in kwargs
            under that parameter name and that name is marked as consumed.
        - If the first parameter is a var-keyword (**kwargs), the source_path is placed
            in kwargs under the var-keyword parameter name (i.e., kwargs[<var_kw_name>] = source_path).
        - Any other first-parameter kind is treated as unsupported.
    - For each subsequent declared parameter:
        - If the parameter is positional-only, positional-or-keyword, or keyword-only:
            - If metadata contains a value for that parameter name, the value is added
                to kwargs and the name is marked consumed.
            - If metadata does not contain the name and the parameter has no default,
                a HandlerConfigurationError is raised (required metadata missing).
        - Var-positional parameters (*args) are ignored (no attempt is made to fill them).
        - Var-keyword parameters (**kwargs) collect any remaining metadata items whose
            names were not already consumed; each such item is added to kwargs.

    Returns
    - Tuple[List[Any], Dict[str, Any]]: A 2-tuple (args, kwargs) suitable for calling
        handler.parse_results(*args, **kwargs). args is a list of positional arguments
        (possibly empty); kwargs is a dict of keyword arguments prepared from metadata
        and the source_path mapping rules described above.

    Errors / Exceptions
    - HandlerConfigurationError is raised when:
        - handler.parse_results declares no parameters.
        - A required parameter (no default) is not present in metadata.
        - The first parameter uses an unsupported parameter kind.

    Notes and examples
    - Consumed parameter names are tracked to avoid supplying the same metadata key
        twice or forwarding it twice into **kwargs.
    - Example mappings (informal):
        - parse_results(source, foo, **rest) -> args = [source], kwargs['foo'] from metadata if present,
            remaining metadata items go into kwargs via **rest.
        - parse_results(*args, **kwargs) -> args = [source], kwargs = {'kwargs': source, ...} (the
            var-keyword name receives source_path under that name).
    - The function does not attempt type conversion; it purely maps names and values
        according to the declared signature.
    """
    """Build positional/keyword arguments for handler.parse_results."""

    parse: Signature = signature(handler.parse_results)
    params: Sequence[Parameter] = tuple(parse.parameters.values())
    if not params:
        raise HandlerConfigurationError(
            f"Handler '{handler.__class__.__name__}' declares no parameters"
        )

    args: List[Any] = []
    kwargs: Dict[str, Any] = {}
    consumed: set[str] = set()

    first = params[0]
    if first.kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD, Parameter.VAR_POSITIONAL):
        args.append(source_path)
    elif first.kind == Parameter.KEYWORD_ONLY:
        kwargs[first.name] = source_path
        consumed.add(first.name)
    elif first.kind == Parameter.VAR_KEYWORD:
        kwargs[first.name] = source_path
    else:
        raise HandlerConfigurationError(
            f"Unsupported parameter kind for first argument: {first.kind}"
        )

    for param in params[1:]:
        if param.kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY):
            if param.name in metadata:
                kwargs[param.name] = metadata[param.name]
                consumed.add(param.name)
            elif param.default is Parameter.empty:
                raise HandlerConfigurationError(
                    f"Missing required metadata field '{param.name}' for handler "
                    f"'{handler.__class__.__name__}'"
                )
        elif param.kind == Parameter.VAR_POSITIONAL:
            continue
        elif param.kind == Parameter.VAR_KEYWORD:
            for key, value in metadata.items():
                if key not in consumed:
                    kwargs[key] = value
                    consumed.add(key)

    return args, kwargs


def _render_robot_artifacts(parsed_results: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    """Render Robot Framework XML and log HTML for parsed results."""

    suite = RobotInterface().running.build_suite(parsed_results)
    stdout_buffer = StringIO()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "output.xml")
        log_path = os.path.join(tmpdir, "log.html")

        suite.run(output=output_path, log=None, report=None, stdout=stdout_buffer)
        ResultWriter(output_path).write_results(log=log_path, report=None)

        with open(output_path, "r", encoding="utf-8") as fh:
            output_xml = fh.read()

        log_html: Optional[str] = None
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as fh:
                    log_html = fh.read()
            except OSError:
                log_html = None

    return output_xml, log_html


def convert_with_handler(config: Config, source_path: str) -> HandlerConversionResult:
    """Convert a test result file using the configured Oxygen handler."""

    resolved = resolve_handler(config.handler)
    handler = resolved.handler

    args, kwargs = _prepare_handler_call(handler, source_path, config.metadata)

    start = time.perf_counter()
    try:
        parsed = handler.parse_results(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 - we wrap into domain error
        raise HandlerExecutionError(str(exc)) from exc

    validate_with_deprecation_warning(parsed, handler.parse_results)

    output_xml, log_html = _render_robot_artifacts(parsed)
    duration = time.perf_counter() - start

    return HandlerConversionResult(
        config=config,
        source_path=source_path,
        handler_key=resolved.handler_key,
        handler_keyword=getattr(handler, "keyword", config.handler),
        parsed_results=parsed,
        robot_output_xml=output_xml,
        log_html=log_html,
        duration_s=duration,
    )


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
