---
applyTo: "agents_plugins/robotmk_bridge_plugin.py"
---

# Robotmk-Bridge — Agent plugin specification

## Purpose

This document describes the core features, acceptance criteria and recommended implementation order for the Robotmk-Bridge agent plugin (agent-side). The Bridge plugin's role is to read native test result files from configured paths, use the oxygen package to convert them internally to Robot Framework XML, produce a log.html with rebot, and produce Robotmk JSON results that the Robotmk scheduler/Checkmk can consume.


## Minimal contract (2–4 bullets)

- Inputs: configuration JSON (bakery/agent rule) file mapping concrete file paths (or globs) to the oxygen handler names; the test result files (tool-specific) on disk.
- Outputs: Robotmk JSON result files in the scheduler results folder (default: `/var/lib/check_mk_agent/robotmk/scheduler/results/plans/<plan>.json`) containing the Robot Framework XML and optional log.html content.
- Error modes: missing files, unreadable files (permissions), unknown handler name, handler conversion failure (malformed output), write permission errors when saving JSON.
- Success criteria: for each configured path, a JSON result is produced (or detailed error recorded) and a concise agent health section is emitted.
- Agent section is build with JSON and contains valuable data and metrics about all converted files, and runtimes for the conversion.

## Key features (prioritized)

1. Configuration parsing and validation
   - Read local config `/etc/check_mk/robotmk-bridge-plugin.json` and validate entries.
   - Support per-path settings: handler, plan name, optional metadata.
2. Safe file discovery and reading
   - Accept concrete files or simple glob patterns; validate size and timestamps.
   - Treat configured path as concrete by default (per repo design) with optional glob mode.
   - only accept files which do not have a mtime older than now - max_age (specified in the config)
3. Implement conversion
   - We leverage the oxygen package (already insalled) for the conversion. 
   - Ech result file gets read and converted using oxygen's "parse_results" from the handler. For that to work, the handelr name in the config must match the handler available to rmkbridge. 
   - A wrong handler name leads to an error. 
   - our plugin receives the Robot Framework XML (as string)
   - Fail fast with meaningful error messages if handler missing or raises.
4. Construct JSON wrapper output (Robotmk JSON)
   - For each converted file, create JSON using same structure as in `sample_data/globetrack_simple.json`. Fill missing metadata with reasonable defaults.
   - Write it to the results dir. ThisTo determine this folder: in the Agent config dir (MK_CONFDIR) in `robotmk.json` (If this variable is not set, assume `/etc/check_mk/robotmk.json`, on Windows `C:\ProgramData\checkmk\agent\config\robotmk.json"`.), there is key "runtime_directory".  Below of that there is a folder "results/plans". Below of that, place the JSON results. The plan name is taken from the config per path (or default).

Not yet refined: 

5. Support the Enum values for "outcome" (See Code "Ref: 0001")
6. Support float for "runtime" (See Code "Ref: 0002")
7. Support reading interval, timeout, n_attempts_max from metadata (See Code "Ref: 0003")
8. Agent health section and lightweight metrics
   - Emit an agent plugin section summarizing processed files, successful conversions, last run times and failures for the server-side check.
9. Robust logging and error reporting
   - Log at various levels, include stack traces for failures and produce structured error objects in health output.
10. Tests: unit and integration
   - Unit tests for config parse, dispatch, and wrapping. Integration test using `rf_tests/simple/output.xml`.
11. Packaging & Bakery rule integration
   - Provide a bakery rule example and `pkginfo/` metadata to make installation easy.


## Implementation order (recommended)

1. Implement config loader and validation to read `/etc/check_mk/robotmk-bridge-plugin.json`, ensuring required keys, numeric `max_age`, and sensible defaults (plan name, metadata).
2. Build file discovery layer that resolves paths/globs, filters by `max_age`, checks file size thresholds, and yields concrete files with rich error states.
3. Integrate oxygen handlers: instantiate the correct handler per entry, feed file contents, capture Robot Framework XML/log output, and surface handler-level errors.
4. Construct the Robotmk JSON result files and store them. 
5. Emit bridge agent section summarizing each processed file, success/failure details, conversion durations, and cumulative metrics for the server-side check.
6. Add structured logging and error handling (warnings vs. fatal), making sure failures propagate to agent section and optional debug logs.
7. Cover functionality with unit tests (config, discovery, JSON builder, handler dispatch) plus an integration test against `rf_tests/simple` fixtures.
8. Finalize packaging artifacts (bakery rule example, `pkginfo/` metadata) and document deployment/operations steps.


## Acceptance criteria and quality gates

- Build: The plugin is one single Python file; a basic linter (flake8/ruff) should pass on changed files. (PASS/FAIL reported during PR.)
- Lint/Typecheck: Keep typing minimal but consistent; add typing for public functions. (PASS/FAIL)
- Tests: Unit tests for config and handler dispatch, one integration test. (PASS/FAIL)

## Edge cases to handle

All these errors should be refelcted in the Agent plugin output section:

- Files disappear between discovery and read.
- Files with very large size: implement size limit or stream processing.
- Permission errors when reading or writing.
- Handler timeouts or memory spikes.
- Corrupt/malformed handler output.

## Tests & examples

- Unit tests: config loader, handler registry, JSON writer.
- Integration test: use `rf_tests/simple/output.xml`, call `noop` handler and assert `specs/expected_json` or existence in scheduler folder.
s