---
applyTo: "agents_plugins/robotmk_bridge_plugin.py, /omd/sites/cmk/local/lib/python3/cmk_addons/plugins/robotmk-bridge-plugin/agent_based/robotmk_bridge_plugin.py"

---
# Coding standards for Checkmk Agent Plugins in Python

## Role & Goal (for Copilot)

You are a senior Checkmk engineer.
Generate **Python agent plugins** that run on monitored hosts and print **agent section data** to STDOUT in the canonical Checkmk agent format. Your code must be:

* **Portable** (Linux + Windows),
* **Robust** (timeouts, errors → exit non-0 or print nothing; never print partial/broken sections),
* **Deterministic** (stable keys/order),
* **Safe** (no secrets in output; handle Unicode; don’t crash if dependencies are missing).

**You are NOT writing a Check plugin on the server.** You are writing an **agent plugin** that produces *sections* which Checkmk parses later.

---

## What an Agent Plugin Is (and Isn’t)

* Runs **on the target host** via the Checkmk agent.
* Prints **one or more sections** like:

  ```
  <<<mysection:sep(0)>>>
  key1 value1
  key2 value2
  ```
* Can also contain json. E.g.,

  ```
  <<<myjsonsection>>>
  {"key": "value", "list": [1, 2, 3]}
  ```
* Can be **executables** (in `plugins/`) or **spool files**
* **No HTML.**
* Output must be **UTF-8** to STDOUT; log errors to **STDERR**.

### Typical install locations (default)

* **Linux**

  * Executables: `/usr/lib/check_mk_agent/plugins/`
  * Spool files: `/var/lib/check_mk_agent/spool/`
  * Local checks: `/usr/lib/check_mk_agent/local/`
  * Config(s) you own: `/etc/check_mk/yourplugin/…`
* **Windows**

  * Executables: `%ProgramData%\checkmk\agent\plugins\`
  * Spool files: `%ProgramData%\checkmk\agent\spool\`
  * Local checks: `%ProgramData%\checkmk\agent\local\`
  * Config(s) you own: `%ProgramData%\checkmk\agent\config\yourplugin\`

> On Enterprise with the **Agent Bakery**, these paths are populated by baked packages. Your code shouldn’t hard-depend on the Bakery; it should also work when copied manually.

---

## Environment Variables available 

### Windows

```
MK_LOCALDIR="C:\ProgramData\checkmk\agent\local"
MK_STATEDIR="C:\ProgramData\checkmk\agent\state"
MK_PLUGINSDIR="C:\ProgramData\checkmk\agent\plugins"
MK_TEMPDIR="C:\ProgramData\checkmk\agent\tmp"
MK_LOGDIR="C:\ProgramData\checkmk\agent\log"
MK_CONFDIR="C:\ProgramData\checkmk\agent\config"
MK_SPOOLDIR="C:\ProgramData\checkmk\agent\spool"
MK_INSTALLDIR="C:\ProgramData\checkmk\agent\install"
MK_MSI_PATH="C:\ProgramData\checkmk\agent\update"
```

### Linux

```
MK_LIBDIR=/usr/lib/check_mk_agent
MK_CONFDIR=/etc/check_mk
MK_VARDIR=/var/lib/check_mk_agent
```

---

## Section Format Cheatsheet

**Header**

```
<<<section_name>>>
```

or with options:

```
<<<section_name:sep(0)>>>
```

* `section_name`: lowercase, snake_case, unique.
* `sep(0)` means fields are **NUL-separated** (`\0`). Preferred if values can contain spaces. Without it, use space-separated fields.

**Body rows**: your tabular or key-value data. Keep a **stable schema**.
**Multiple sections**? Print headers repeatedly in the same run.

**Don’ts**

* Don’t print BOMs, color codes, stack traces to STDOUT.
* Don’t interleave different sections.
* Don’t print empty headers; either print a valid section or nothing.

---

## Caching & Spool: When and How

### Option A — Let the agent cache your plugin

* On Linux, executable files in `…/plugins/` can be **executed with caching** by the agent/wrapper (configurable via Bakery or agent config).
* Your plugin should **just run and print fresh data**. The **agent** decides whether to use cached output.

### Option B — You cache via **spool**

* Write a ready-made section file into the **spool directory**.
* File naming can carry a max-age prefix:

  * Example (Linux): `/var/lib/check_mk_agent/spool/600_myplugin` → valid for **600s**.
* The agent **reads the file** (if not older than the prefix) and forwards it verbatim.
* Your Python script can be run by cron/scheduled task and produce/refresh the spool file.

**Rule of thumb**

* **Fast** collections: keep as executable in `plugins/`.
* **Slow/expensive**: use **spool** and schedule yourself.

---

## Cross-Platform Basics for Copilot

* Shebang (Linux): `#!/usr/bin/env python3`
* Windows: will run via `python.exe` or Py-embedded; no shebang needed, but keep files `.py`.
* Use only stdlib unless you vendor dependencies; **don’t assume third-party libs are present**.
* Set **`PYTHONIOENCODING=UTF-8`** (you can enforce in code).
* **Timeout** external calls to avoid blocking the agent.
* **Exit 0** if you print valid sections; **exit non-0** if a fatal error (and print nothing to STDOUT).

---

## Minimal Skeleton (single section, space-separated)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Checkmk Agent Plugin: mysection
- Cross-platform
- Safe output
"""

from __future__ import annotations
import sys
import os
import platform
import subprocess
import shlex
import json
from typing import List, Tuple

SECTION = "mysection"  # lowercase snake_case

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def run(cmd: List[str], timeout: int = 5) -> Tuple[int, str, str]:
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return cp.returncode, cp.stdout.strip(), cp.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s: {cmd}"
    except Exception as exc:
        return 1, "", f"exec error: {exc}"

def safe(s: str) -> str:
    # Ensure single-line, no control chars that break space-separated format
    return " ".join(s.replace("\r", " ").replace("\n", " ").split())

def collect() -> List[Tuple[str, str]]:
    """Return stable key-value pairs for the section."""
    rows: List[Tuple[str, str]] = []
    rows.append(("os", platform.system()))
    rows.append(("hostname", platform.node()))

    # Example external command (Linux only) — guard by platform:
    if platform.system() == "Linux":
        rc, out, err = run(["uptime", "-p"], timeout=2)
        if rc == 0:
            rows.append(("uptime_pretty", safe(out)))
        else:
            eprint(f"uptime failed: rc={rc} err={err}")

    # Finalize
    return rows

def print_section(rows: List[Tuple[str, str]]) -> None:
    if not rows:
        return  # print nothing if no data
    print(f"<<<{SECTION}>>>")
    for k, v in rows:
        print(f"{k} {v}")

def main() -> int:
    try:
        rows = collect()
        print_section(rows)
        return 0
    except Exception as exc:
        eprint(f"fatal: {exc}")
        return 2

if __name__ == "__main__":
    sys.exit(main())
```

---

## Preferred Robust Variant (NUL-separated, safer for spaces)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Checkmk Agent Plugin: mysection2 (NUL-separated)
"""

from __future__ import annotations
import sys, platform, json

SECTION = "mysection2"
SEP = "\0"  # NUL

def rows():
    yield ("os", platform.system())
    yield ("hostname", platform.node())
    # Any value can contain spaces safely when using sep(0).
    yield ("message", "hello world with spaces")

def main():
    data = list(rows())
    if not data:
        return 0
    sys.stdout.write(f"<<<{SECTION}:sep(0)>>>\n")
    for k, v in data:
        sys.stdout.write(f"{k}{SEP}{v}\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

---

## Spool Producer Example (slow data, scheduled independently)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Writes a spool file valid for 300s with a section 'expensive_metrics'.
Linux path shown; adjust for Windows.
"""
import os, time, tempfile, shutil, sys

SECTION = "expensive_metrics"
SPOOL_DIR = "/var/lib/check_mk_agent/spool"  # Windows: %ProgramData%\checkmk\agent\spool
MAX_AGE = 300  # seconds
TARGET = os.path.join(SPOOL_DIR, f"{MAX_AGE}_{SECTION}")

def compute_expensive():
    # pretend this is slow
    return [("cost", "42"), ("unit", "ms")]

def write_atomic(path: str, text: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(tmp, 0o644)
    shutil.move(tmp, path)

def main():
    rows = compute_expensive()
    if not rows:
        return 0
    out = [f"<<<{SECTION}:sep(0)>>>"]
    for k, v in rows:
        out.append(f"{k}\0{v}")
    text = "\n".join(out) + "\n"
    write_atomic(TARGET, text)
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

Schedule with cron/systemd (Linux) or Task Scheduler (Windows).

---

## Config Handling (INI/YAML/ENV)

Keep config optional and robust:

* Look for config in these places (first found wins):

  1. Env vars (`MYPLUGIN_…`)
  2. File in `/etc/check_mk/yourplugin/config.yaml` (Linux) or `%ProgramData%\checkmk\agent\config\yourplugin\config.yaml` (Windows)
  3. Built-in defaults

Example (YAML optional, fallback to env/defaults):

```python
import os, json
from pathlib import Path
try:
    import yaml  # if not present, handle gracefully
except Exception:
    yaml = None

def load_config():
    cfg = {
        "timeout": int(os.getenv("MYPLUGIN_TIMEOUT", "5")),
        "targets": os.getenv("MYPLUGIN_TARGETS", "localhost").split(","),
    }
    candidates = [
        Path("/etc/check_mk/yourplugin/config.yaml"),
        Path(os.getenv("ProgramData", "C:\\ProgramData")) / "checkmk" / "agent" / "config" / "yourplugin" / "config.yaml",
    ]
    for p in candidates:
        try:
            if p.exists() and yaml:
                with p.open("r", encoding="utf-8") as f:
                    cfg.update(yaml.safe_load(f) or {})
                break
        except Exception as exc:
            pass
    return cfg
```

---

## Error Handling & Logging

* **Never** print stack traces to STDOUT.
* Use `stderr` for diagnostics.
* If you cannot produce a **valid section**, print **nothing** and exit **non-0**.

Patterns:

```python
def guarded_section(printer):
    try:
        rows = collect()
        if rows:
            printer(rows)
        return 0
    except Exception as exc:
        eprint(f"section {SECTION} failed: {exc}")
        return 1
```

---

## Testing Locally

1. **Run the script**: it should print exactly one or more valid sections.
2. **Embed into agent output** (quick simulation):

   ```bash
   (check_mk_agent 2>/dev/null; python3 ./myplugin.py) | less
   ```

   Ensure your section appears once, cleanly.
3. **Validate charset**:

   ```bash
   python3 - <<'PY'
   import sys, codecs
   data = sys.stdin.buffer.read()
   codecs.decode(data, 'utf-8')  # raises if invalid
   PY
   ```
4. **Regex sanity**: header, no stray lines before headers.

---

## Common Pitfalls (avoid them)

* ❌ Printing non-UTF-8 bytes.
* ❌ Mixing spaces/tabs inconsistently; changing column order run-to-run.
* ❌ Long-running logic blocking the agent (use timeouts or spool).
* ❌ Depending on unavailable system tools (guard by OS).
* ❌ Emitting headers with **zero** rows repeatedly (prefer silence).
* ❌ Leaking secrets/tokens.

---

## Multi-Section Plugins (pattern)

```python
def print_section(name, rows, sep0=True):
    if not rows: 
        return
    head = f"<<<{name}:sep(0)>>>" if sep0 else f"<<<{name}>>>"
    print(head)
    for k, v in rows:
        if sep0:
            print(f"{k}\0{v}")
        else:
            print(f"{k} {v}")

def main():
    rc = 0
    try:
        print_section("my_cpu", collect_cpu())
        print_section("my_mem", collect_mem())
    except Exception as exc:
        eprint(f"fatal: {exc}")
        rc = 2
    return rc
```

---

## Windows Notes

* Use `subprocess.run` with **shell=False**; prefer PowerShell calls only if strictly needed and present.
* Paths: use `os.environ["ProgramData"]` to construct locations.
* Newlines: Python handles `\r\n`; no special action needed if you print with `print()`.
* If you redistribute Python, ensure the agent user can execute the script.

---

## Packaging & Deployment

* **Manual**: copy `.py` to the `plugins/` dir, make executable on Linux (`chmod 755`).
* **Spool**: schedule your producer; ensure file owner/permissions allow the agent to read.
* **Enterprise (Agent Bakery)**: supply your script + rule to configure execution and cache age; don’t hardcode bakery assumptions in your code.

---

## Security & Privacy

* Don’t print API tokens/credentials.
* Redact obvious secrets (`***`).
* Limit data volume; avoid flooding agent output.
* Handle **permissions**: your plugin runs with the agent’s account/user.

---

## Quick Checklist (for every new plugin)

* [ ] Prints **valid** headers `<<<name(:sep(0))>>>` before any data.
* [ ] Output is **UTF-8**, deterministic order, no trailing garbage.
* [ ] Handles **timeouts** & errors cleanly (stderr, no partial sections).
* [ ] Linux/Windows path handling guarded.
* [ ] Config optional, with sane defaults.
* [ ] Spool/caching strategy chosen appropriately.
* [ ] No secrets in output; large payloads avoided.

---

## Example: Realistic Section (service health table)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, time, platform

SECTION = "app_services"

def collect():
    # Pretend we polled a local supervisor/SCM
    services = [
        {"name": "api", "state": "running", "uptime_s": 123456, "restart_cnt": 1},
        {"name": "worker", "state": "running", "uptime_s": 9876, "restart_cnt": 0},
        {"name": "scheduler", "state": "stopped", "uptime_s": 0, "restart_cnt": 3},
    ]
    return services

def main():
    data = collect()
    if not data:
        return 0
    print(f"<<<{SECTION}:sep(0)>>>")
    print("name\0state\0uptime_s\0restart_cnt")  # header row for clarity (optional but stable)
    for s in data:
        print(f"{s['name']}\0{s['state']}\0{s['uptime_s']}\0{s['restart_cnt']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

This yields a stable, parseable table. Your future Check plugin (on the server) can map states and derive metrics from these fields.

---

### Final Tip for Copilot

When the user asks for *“a new agent plugin that collects X and prints a Checkmk section”*, default to:

1. **NUL-separated** format `sep(0)`.
2. **Timeouts** on all external calls (2–5s).
3. **Silence on failure** (no section), log to `stderr`.
4. **Spool** for anything slow or rate-limited.
