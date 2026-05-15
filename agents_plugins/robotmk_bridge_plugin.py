#!/usr/bin/env python3

from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass, field
from inspect import Parameter, Signature, signature
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import glob

from rmkbridge.rmkbridge import RobotmkBridgeCore
from rmkbridge.robot_interface import RobotInterface
from rmkbridge.utils import validate_with_deprecation_warning
from robot.api import ResultWriter


DEFAULT_CONFIG_PATH = "/etc/check_mk/robotmk-bridge-plugin.json"
CMK_AGENT_SECTION = "robotmk_bridge"


@dataclass
class Config:
    path: str
    handler: str
    plan_name: Optional[str] = None
    piggyback_host: Optional[str] = None
    max_age: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FileRunRecord:
    plan: str
    handler: str
    source_path: str
    status: str
    runtime_s: Optional[float]
    result_path: Optional[str]
    host: Optional[str]
    message: Optional[str]
    timestamp: Optional[int]


@dataclass
class BridgeRunReport:
    started_at: float
    finished_at: float
    records: List[FileRunRecord]
    config_count: int
    messages: List[str]

    @property
    def duration_s(self) -> float:
        return self.finished_at - self.started_at


@dataclass
class ResolvedHandler:
    """Stores the resolved Robotmk Bridge handler instance and metadata."""

    handler_key: str
    handler: Any


@dataclass
class HandlerConversionResult:
    """Captures artifacts produced by an Robotmk Bridge handler conversion."""

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


_RMKBRIDGECORE: Optional[RobotmkBridgeCore] = None


def _get_rmkbridgeCORE() -> RobotmkBridgeCore:
    """Return a cached RobotmkBridgeCore instance."""

    global _RMKBRIDGECORE
    if _RMKBRIDGECORE is None:
        try:
            _RMKBRIDGECORE = RobotmkBridgeCore()
        except Exception as exc:  # noqa: BLE001 - propagate as domain error
            raise HandlerResolutionError(f"Failed to initialise Oxygen.RobotmkBridgeCore: {exc}") from exc
    return _RMKBRIDGECORE


def _iter_handler_keys(handler_name: str) -> Iterable[str]:
    """Yield plausible handler keys for the given configuration name."""

    names: List[str] = [handler_name]
    if not handler_name.startswith("rmkbridge."):
        names.append(f"rmkbridge.{handler_name}")
    return names


def resolve_handler(handler_name: str) -> ResolvedHandler:
    """Resolve a configured handler name to an Robotmk Bridge handler instance."""

    core = _get_rmkbridgeCORE()
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
    """Convert a test result file using the configured Robotmk Bridge handler."""

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

def _encode_log_html(log_html: Optional[str]) -> str:
    if not log_html:
        return ""
    return base64.b64encode(log_html.encode("utf-8")).decode("ascii")


def _assemble_metadata(conversion: HandlerConversionResult) -> Dict[str, Any]:
    metadata = dict(conversion.config.metadata)
    metadata.setdefault("application", "robotmk-bridge")
    metadata.setdefault("suite_name", Path(conversion.source_path).stem)
    metadata.setdefault("variant", conversion.handler_keyword)
    return metadata


def _build_result_config(metadata: Dict[str, Any]) -> Dict[str, int]:
    def _coerce(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    # Also these data are faked for now. 
    # TODO: Implement proper logic to extract these values from the metadata.
    # Ref: 0003
    return {
        "interval": 60,
        "timeout": 60,
        "n_attempts_max": 1,
    }

    return {
        "interval": _coerce(metadata.get("interval"), 0),
        "timeout": _coerce(metadata.get("timeout"), 0),
        "n_attempts_max": _coerce(metadata.get("n_attempts_max"), 1),
    }


def build_robotmk_result(
    conversion: HandlerConversionResult,
    host: Optional[str] = None,
    timestamp: Optional[float] = None,
) -> Dict[str, Any]:
    """Create a Robotmk JSON payload matching the scheduler expectations."""

    now = timestamp or time.time()
    plan_name = conversion.config.plan_name
    metadata = _assemble_metadata(conversion)
    html_base64 = _encode_log_html(conversion.log_html)
    config_host = (
        conversion.config.piggyback_host.strip()
        if conversion.config.piggyback_host
        else None
    )
    host_name = host if host is not None else (config_host or "Source")

    # TODO: robotmk parser expects one of the enum values
    # Ref: 0001
    # ('AllTestsPassed','TestFailures','RobotFailure','EnvironmentFailure','TimedOut').
    # Using "AllTests Passed" as a temporary placeholder — adjust to canonical enum later.

    # Also duration is curently only allows as int - convert to float later. 
    # Ref: 0002
    content = {
        "plan_id": plan_name,
        "timestamp": int(now),
        "attempts": [
            {
                "index": 1,
                "outcome": "AllTestsPassed",
                "runtime": int(conversion.duration_s) + 1,
            }
        ],
        "rebot": {
            "Ok": {
                "xml": conversion.robot_output_xml,
                "html_base64": html_base64,
                "timestamp": int(now),
            }
        },
        "config": _build_result_config(metadata),
        "metadata": metadata,
    }

    # (name becomes the section name in Robotmk scheduler)
    return {
        "host": host_name,
        "name": "robotmk_plan_execution_report",
        "content": json.dumps(content, separators=(",", ":")),
    }


def _default_robotmk_config_path() -> Path:
    conf_dir = os.environ.get("MK_CONFDIR")
    if conf_dir:
        return Path(conf_dir) / "robotmk.json"

    if os.name == "nt":
        program_data = os.environ.get("ProgramData", r"C:\\ProgramData")
        return Path(program_data) / "checkmk" / "agent" / "config" / "robotmk.json"

    return Path("/etc/check_mk/robotmk.json")


def _load_robotmk_scheduler_working_directory(config_path: Optional[str] = None) -> Path:
    path = Path(config_path) if config_path else _default_robotmk_config_path()

    if not path.exists():
        raise FileNotFoundError(f"robotmk config not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    runtime_directory = data.get("runtime_directory")
    if not runtime_directory or not isinstance(runtime_directory, str):
        raise ValueError("robotmk config missing valid 'runtime_directory'")

    return Path(runtime_directory)


def resolve_results_directory(
    *,
    runtime_directory: Optional[str] = None,
    robotmk_config_path: Optional[str] = None,
) -> Path:
    base = Path(runtime_directory) if runtime_directory else _load_robotmk_scheduler_working_directory(robotmk_config_path)
    return base / "results" / "plans"


def _write_atomic_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.replace(tmp_path, path)
    finally:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass


def write_robotmk_result(
    plan_name: str,
    result_payload: Dict[str, Any],
    results_dir: Optional[str] = None,
    runtime_directory: Optional[str] = None,
    robotmk_config_path: Optional[str] = None,
) -> Path:
    """Persist a Robotmk result payload into the scheduler results directory."""

    if not plan_name or not isinstance(plan_name, str):
        raise ValueError("Result payload missing string 'name'")

    target_dir = (
        Path(results_dir)
        if results_dir is not None
        else resolve_results_directory(
            runtime_directory=runtime_directory,
            robotmk_config_path=robotmk_config_path,
        )
    )

    target_path = target_dir / f"{plan_name}.json"
    serialized = json.dumps(result_payload, ensure_ascii=False, separators=(",", ":"))
    _write_atomic_text(target_path, serialized)
    return target_path


def process_config_entry(
    config: Config,
    reference_time: Optional[float] = None,
    results_dir: Optional[str] = None,
    runtime_directory: Optional[str] = None,
    robotmk_config_path: Optional[str] = None,

) -> List[FileRunRecord]:
    """Convert and store Robotmk results for a single configuration entry."""

    processed: List[Path] = []
    candidates = discover_files(
        config.path,
        max_age=config.max_age,
        reference_time=reference_time,
    )

    timestamp_value = reference_time if reference_time is not None else time.time()
    timestamp_int = int(timestamp_value)

    if not candidates:
        processed.append(
            FileRunRecord(
                plan=config.plan_name,
                handler=config.handler,
                source_path=config.path,
                status="missing",
                runtime_s=None,
                result_path=None,
                host=config.piggyback_host,
                message="no files matched pattern",
                timestamp=timestamp_int,
            )
        )
        return processed

    for source in candidates:
        status = "success"
        message: Optional[str] = None
        result_path: Optional[str] = None
        runtime_s: Optional[float] = None
        host_value: Optional[str] = config.piggyback_host
        try:
            conversion = convert_with_handler(config, source)
            runtime_s = conversion.duration_s
            payload = build_robotmk_result(conversion, timestamp=timestamp_value)
            host_value = payload.get("host", host_value)
            stored = write_robotmk_result(
                plan_name=config.plan_name,
                result_payload=payload,
                results_dir=results_dir,
                runtime_directory=runtime_directory,
                robotmk_config_path=robotmk_config_path,
            )
            result_path = str(stored)
        except HandlerError as exc:
            status = "error"
            message = str(exc)
        except Exception as exc:  # noqa: BLE001 - capture unexpected errors
            status = "error"
            message = str(exc)

        processed.append(
            FileRunRecord(
                plan=config.plan_name,
                handler=config.handler,
                source_path=source,
                status=status,
                runtime_s=runtime_s,
                result_path=result_path,
                host=host_value,
                message=message,
                timestamp=timestamp_int,
            )
        )

    return processed


def run_bridge(
    config_path: Optional[str] = None,
    reference_time: Optional[float] = None,
    results_dir: Optional[str] = None,
    runtime_directory: Optional[str] = None,
    robotmk_config_path: Optional[str] = None,

) -> BridgeRunReport:
    """Execute the bridge workflow for all configured paths."""

    started = time.time()
    configs = load_config(config_path)
    processed: List[FileRunRecord] = []
    messages: List[str] = []
    for cfg in configs:
        results = process_config_entry(
            cfg,
            reference_time=reference_time,
            results_dir=results_dir,
            runtime_directory=runtime_directory,
            robotmk_config_path=robotmk_config_path,
        )
        plan_name = cfg.plan_name
        if not results:
            messages.append(f"no files processed for plan {plan_name}")
        else:
            for record in results:
                if record.message:
                    messages.append(
                        f"{record.plan}:{record.source_path}:{record.message}"
                    )
        processed.extend(results)

    finished = time.time()
    return BridgeRunReport(
        started_at=started,
        finished_at=finished,
        records=processed,
        config_count=len(configs),
        messages=messages,
    )


def _serialise_record(record: FileRunRecord) -> Dict[str, Any]:
    return {
        "plan": record.plan,
        "handler": record.handler,
        "source_path": record.source_path,
        "status": record.status,
        "runtime_s": record.runtime_s,
        "result_path": record.result_path,
        "host": record.host,
        "message": record.message,
        "timestamp": record.timestamp,
    }


def build_agent_payload(report: BridgeRunReport) -> Dict[str, Any]:
    total = len(report.records)
    success = sum(1 for r in report.records if r.status == "success")
    errors = sum(1 for r in report.records if r.status == "error")
    missing = sum(1 for r in report.records if r.status == "missing")

    plans: Dict[str, Dict[str, Any]] = {}
    for record in report.records:
        plan_entry = plans.setdefault(
            record.plan,
            {
                "handler": record.handler,
                "host": record.host,
                "files": [],
            },
        )
        plan_entry["files"].append(_serialise_record(record))

    payload = {
        "timestamp": int(report.finished_at),
        "runtime_s": report.duration_s,
        "summary": {
            "configs": report.config_count,
            "files_total": total,
            "files_success": success,
            "files_missing": missing,
            "files_error": errors,
        },
        "plans": plans,
        "messages": report.messages,
    }

    return payload


def print_agent_section(report: BridgeRunReport) -> None:
    payload = build_agent_payload(report)
    sys.stdout.write(f"<<<{CMK_AGENT_SECTION}>>>\n")
    sys.stdout.write(json.dumps(payload, separators=(",", ":")))
    sys.stdout.write("\n")


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

        plan_name = entry.get("plan_name")
        if plan_name is not None and not isinstance(plan_name, str):
            raise ValueError(f"Path entry at index {i} has non-string 'plan_name'")

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

        piggyback_host = entry.get("piggyback_host")
        if piggyback_host is not None:
            if not isinstance(piggyback_host, str):
                raise ValueError(
                    f"Path entry at index {i} must have string 'piggyback_host' when provided"
                )
            piggyback_host = piggyback_host.strip()
            if not piggyback_host:
                raise ValueError(
                    f"Path entry at index {i} has empty 'piggyback_host' value"
                )

        result.append(
            Config(
                path=p,
                handler=h,
                plan_name=plan_name,
                piggyback_host=piggyback_host,
                max_age=max_age_value,
                metadata=metadata,
            )
        )

    return result




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

def _main(cfg_path: Optional[str] = None) -> int:
    try:
        report = run_bridge(cfg_path)
    except Exception as exc:  # noqa: BLE001 - errors elevate to non-zero exit
        print(f"Error running robotmk bridge: {exc}", file=sys.stderr)
        return 2

    print_agent_section(report)
    return 0


if __name__ == "__main__":
    cfg = sys.argv[1] if len(sys.argv) > 1 else None
    plan = sys.argv[2] if len(sys.argv) > 2 else None
    if plan:
        # Here we monkey-patck the load_config function to filter by plan name
        _orig_load_config = load_config

        def load_config(path: Optional[str] = None) -> List[Config]:
            configs = _orig_load_config(path)
            return [c for c in configs if c.plan_name == plan]
    raise SystemExit(_main(cfg))

