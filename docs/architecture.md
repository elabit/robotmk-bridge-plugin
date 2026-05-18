# Robotmk Bridge Plugin - Architecture Documentation

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Component Architecture](#component-architecture)
4. [Data Flow Architecture](#data-flow-architecture)
5. [Plugin Integration Architecture](#plugin-integration-architecture)
6. [Handler Resolution System](#handler-resolution-system)
7. [Configuration Architecture](#configuration-architecture)
8. [Deployment Architecture](#deployment-architecture)
9. [Testing Architecture](#testing-architecture)
10. [Design Patterns & Principles](#design-patterns--principles)

---

## Executive Summary

The Robotmk Bridge Plugin implements a **Plugin Architecture** that extends Checkmk's monitoring capabilities to support arbitrary test automation tools. It follows Checkmk's **Agent-Check Plugin Pattern** with three coordinated components:

1. **Agent Plugin** - Converts test results on monitored hosts
2. **Check Plugin** - Monitors bridge operations from Checkmk server
3. **Web Plugins** - Provides UI configuration via Checkmk Bakery

**Key Architectural Decisions:**
- **Handler-based extensibility** via `robotframework-robotmk-bridge` package
- **Robot Framework XML as canonical format** for universal compatibility
- **Robotmk JSON as output format** for seamless integration with existing Robotmk infrastructure
- **Self-monitoring design** - bridge reports its own health via agent sections

---

## Architecture Overview

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    MONITORED HOST                                │
│                                                                   │
│  ┌──────────────┐       ┌─────────────────────────────────────┐│
│  │  Test Tool   │────▶  │   Test Result Files                  ││
│  │ (Tosca, etc) │       │   /path/to/results/test.xml          ││
│  └──────────────┘       └───────────────┬─────────────────────┘│
│                                          │                        │
│                         ┌────────────────▼──────────────────┐   │
│  ┌──────────────┐      │   Robotmk Bridge Agent Plugin      │   │
│  │ Checkmk      │──────▶│   • Read config JSON               │   │
│  │ Agent        │ exec  │   • Discover files (glob/concrete) │   │
│  └──────────────┘       │   • Resolve handlers               │   │
│         │               │   • Convert via rmkbridge          │   │
│         │               │   • Generate Robotmk JSON          │   │
│         │               └────────────────┬───────────────────┘   │
│         │                                │                        │
│         │               ┌────────────────▼───────────────────┐   │
│         │               │   Robotmk Scheduler Results        │   │
│         │               │   /var/lib/.../results/plans/      │   │
│         │               │   • plan_name.json (Robotmk fmt)   │   │
│         │               └────────────────────────────────────┘   │
│         │                                                         │
│         ▼                                                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Agent Section: <<<robotmk_bridge>>>                      │   │
│  │  { "summary": {...}, "plans": {...}, "runtime_s": ... }  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────────┘
                          │ Network
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CHECKMK SERVER                                │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │   Check Plugin: robotmk_bridge_plugin                     │   │
│  │   • Parse agent section                                   │   │
│  │   • Discover services:                                    │   │
│  │     - "RMKBridge Status" (overall)                        │   │
│  │     - "RMKBridge Plan: <name>" (per-plan)                │   │
│  │   • Check states (OK/WARN/CRIT)                          │   │
│  │   • Report metrics (runtime, files, errors)              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          │                                        │
│                          ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │   Checkmk Monitoring Services                             │   │
│  │   ✓ RMKBridge Status: OK                                  │   │
│  │   ✓ RMKBridge Plan: integration_tests: OK                │   │
│  │   ✓ Robotmk Suite: <test_name>: OK  (from Robotmk)      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          │                                        │
│                          ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │   Web UI: WATO Configuration                              │   │
│  │   • Bakery Rule: "Robotmk Bridge Plugin"                  │   │
│  │   • Configure paths, handlers, plans                      │   │
│  │   • Bake agents with generated config                     │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### 1. Agent Plugin Component

**File:** `agents_plugins/robotmk_bridge_plugin.py`

**Responsibilities:**
- Read configuration from `/etc/check_mk/robotmk-bridge-plugin.json`
- Discover test result files (concrete paths or glob patterns)
- Apply age filters (`max_age` parameter)
- Resolve handler names to `robotframework-robotmk-bridge` handlers
- Execute handler conversion (test result → Robot Framework XML)
- Generate Robot Framework `log.html` via `robot.api.ResultWriter`
- Construct Robotmk JSON format output
- Write results to Robotmk scheduler results folder
- Generate agent section output for self-monitoring

**Key Classes & Data Structures:**

```python
@dataclass
class Config:
    path: str              # Test result file path (concrete or glob)
    handler: str           # Handler name (e.g., "junit", "rmkbridge.junit")
    plan_name: Optional[str]      # Robotmk plan name
    piggyback_host: Optional[str] # Target host for piggyback
    max_age: Optional[int]        # Max file age in seconds
    metadata: Dict[str, Any]      # Handler-specific metadata

@dataclass
class FileRunRecord:
    plan: str
    handler: str
    source_path: str
    status: str  # "success", "error", "missing"
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
```

**External Dependencies:**
- `rmkbridge.rmkbridge.RobotmkBridgeCore` - Handler registry and resolution
- `rmkbridge.robot_interface.RobotInterface` - Robot XML manipulation
- `robot.api.ResultWriter` - Generate Robot HTML logs

**Error Handling:**
- `HandlerResolutionError` - Handler not found
- `HandlerConfigurationError` - Invalid handler parameters
- `HandlerExecutionError` - Handler conversion failed
- Continues processing remaining files on error

**Performance Considerations:**
- Caches `RobotmkBridgeCore` instance (`_get_rmkbridgeCORE()`)
- Processes files sequentially (no parallelization)
- Skips old files via `max_age` filter
- Typical execution time: seconds to minutes depending on test result size

---

### 2. Check Plugin Component

**File:** `checks/robotmk_bridge_plugin.py`

**Responsibilities:**
- Parse agent section JSON payload
- Discover Checkmk services
- Evaluate check states (OK/WARN/CRIT)
- Generate service metrics
- Provide detailed output for troubleshooting

**Service Types:**

**A. Main Status Service**
- **Name:** "RMKBridge Status"
- **Discovery:** Always discovered if agent section present
- **Check Logic:**
  - CRIT if any file has `status == "error"`
  - WARN if any file has `status == "missing"`
  - OK otherwise
- **Metrics:**
  - `runtime_conversion` - Total conversion time
  - `files_total` - Total files processed
  - `files_success`, `files_missing`, `files_error` - Outcome counts

**B. Per-Plan Services**
- **Name:** "RMKBridge Plan: `<plan_name>`"
- **Discovery:** One service per configured plan
- **Check Logic:** Same as main status, but scoped to plan
- **Metrics:** Per-plan runtime, file counts
- **Details:** Lists all files for the plan with status, paths, timestamps

**Integration:**
- Uses Checkmk Agent Based API v2 (`cmk.agent_based.v2`)
- Registered via `AgentSection` and `CheckPlugin` descriptors
- Standard Checkmk service lifecycle (discovery → check → metrics)

---

### 3. Web Plugins Component

**Directory:** `web_plugins/wato/`

**Files:**
- `robotmk-bridge-plugin_bakery-params.py` - Bakery rule definition
- `robotmk-bridge-plugin_check-params.py` - Check parameter configuration
- `robotmk-bridge-plugin_discovery-params.py` - Discovery rules

**Bakery Rule Configuration:**
- **Title:** "Robotmk Bridge Plugin"
- **Rule Type:** Agent plugin configuration
- **Parameters:**
  ```json
  [
    {
      "path": "/path/to/results/*.xml",
      "handler": "junit",
      "plan_name": "integration_tests",
      "piggyback_host": null,
      "max_age": 3600,
      "metadata": {}
    }
  ]
  ```
- **Output:** Generates `/etc/check_mk/robotmk-bridge-plugin.json` during agent baking

**Configuration Flow:**
1. Administrator defines rule in WATO UI
2. Rule applies to host/folder
3. Agent baking generates JSON config
4. Config deployed with baked agent
5. Agent plugin reads config on execution

---

## Data Flow Architecture

### End-to-End Data Flow

```
Step 1: Test Execution
  Test Tool (Tosca, Cypress, etc.)
    ↓ writes
  Test Result File (/path/to/result.xml)

Step 2: Agent Execution (every 60s)
  Checkmk Agent
    ↓ executes
  robotmk_bridge_plugin.py
    ↓ reads
  /etc/check_mk/robotmk-bridge-plugin.json
    ↓ discovers
  /path/to/result.xml (via glob or concrete path)
    ↓ checks
  File age < max_age?
    ↓ yes → resolves
  Handler "junit" → rmkbridge.junit
    ↓ calls
  handler.parse_results(source_path, **metadata)
    ↓ returns
  Robot Framework XML string
    ↓ generates via robot.api
  log.html (Robot Framework HTML log)
    ↓ constructs
  Robotmk JSON format:
    {
      "plan": {"id": "integration_tests", ...},
      "suite": {"xml": "<robot>...</robot>", ...},
      "html_log": "<html>...</html>",
      "metadata": {...}
    }
    ↓ writes
  /var/lib/check_mk_agent/robotmk/scheduler/results/plans/integration_tests.json
    ↓ prints to stdout
  <<<robotmk_bridge>>>
  {
    "summary": {"configs": 1, "files_total": 1, "files_success": 1, ...},
    "plans": {
      "integration_tests": {
        "handler": "junit",
        "files": [{
          "source_path": "/path/to/result.xml",
          "status": "success",
          "runtime_s": 1.234,
          "result_path": "/var/lib/.../integration_tests.json",
          "timestamp": 1234567890
        }]
      }
    },
    "runtime_s": 1.5
  }

Step 3: Agent Data Collection
  Checkmk Agent
    ↓ includes section
  Agent Output (sent to Checkmk server)

Step 4: Check Plugin Evaluation
  Checkmk Server
    ↓ parses
  <<<robotmk_bridge>>> section
    ↓ discovers (if needed)
  Services:
    - "RMKBridge Status"
    - "RMKBridge Plan: integration_tests"
    ↓ checks
  Evaluate states, generate metrics
    ↓ displays
  Checkmk UI (services visible)

Step 5: Robotmk Integration
  Robotmk (running separately)
    ↓ reads
  /var/lib/.../results/plans/integration_tests.json
    ↓ parses
  Robot Framework XML from JSON
    ↓ discovers (via separate Robotmk plugin)
  Services: "Robotmk Suite: <test_name>"
    ↓ renders in UI
  Test results visible as Robotmk services
```

---

### Data Format Specifications

#### 1. Agent Plugin Configuration Format

**Location:** `/etc/check_mk/robotmk-bridge-plugin.json`

```json
[
  {
    "path": "/path/to/results/test*.xml",
    "handler": "junit",
    "plan_name": "integration_tests",
    "piggyback_host": "test-server",
    "max_age": 3600,
    "metadata": {
      "custom_key": "custom_value"
    }
  }
]
```

**Fields:**
- `path` (required) - File path or glob pattern
- `handler` (required) - Handler name (e.g., "junit", "rmkbridge.tosca")
- `plan_name` (optional) - Robotmk plan name (defaults to handler name)
- `piggyback_host` (optional) - Target host for piggyback data
- `max_age` (optional) - Max file age in seconds (default: no limit)
- `metadata` (optional) - Handler-specific parameters

---

#### 2. Robotmk JSON Output Format

**Location:** `/var/lib/check_mk_agent/robotmk/scheduler/results/plans/<plan_name>.json`

```json
{
  "plan": {
    "id": "integration_tests",
    "execution_interval": 60,
    "status": "completed"
  },
  "suite": {
    "xml": "<robot generator=\"Robotmk Bridge\" generated=\"...\">...</robot>",
    "xml_base64": "PHJvYm90Li4uPg==",
    "name": "integration_tests",
    "tests": 5,
    "passed": 4,
    "failed": 1
  },
  "html_log": "<html>...</html>",
  "html_log_base64": "PGh0bWwuLi4+",
  "metadata": {
    "handler": "junit",
    "source_path": "/path/to/result.xml",
    "conversion_timestamp": 1234567890,
    "conversion_runtime_s": 1.234
  },
  "timestamps": {
    "started": 1234567890,
    "finished": 1234567900
  }
}
```

**Note:** This is a conceptual format. Actual implementation may vary to match Robotmk scheduler output exactly.

---

#### 3. Agent Section Format

**Section Name:** `<<<robotmk_bridge>>>`

**Format:** Single-line JSON

```json
{
  "summary": {
    "configs": 2,
    "files_total": 3,
    "files_success": 2,
    "files_missing": 1,
    "files_error": 0
  },
  "plans": {
    "integration_tests": {
      "handler": "junit",
      "files": [
        {
          "source_path": "/path/to/result.xml",
          "status": "success",
          "runtime_s": 1.234,
          "result_path": "/var/lib/.../integration_tests.json",
          "timestamp": 1234567890,
          "message": null
        }
      ]
    },
    "e2e_tests": {
      "handler": "cypress",
      "files": [
        {
          "source_path": "/path/to/cypress.json",
          "status": "missing",
          "runtime_s": null,
          "result_path": null,
          "timestamp": null,
          "message": "File not found"
        }
      ]
    }
  },
  "runtime_s": 2.5
}
```

---

## Plugin Integration Architecture

### Integration with robotframework-robotmk-bridge

**Package:** `robotframework-robotmk-bridge` (separate repository)

**Handler Discovery:**
```python
from rmkbridge.rmkbridge import RobotmkBridgeCore

core = RobotmkBridgeCore()
handlers = core.handlers  # Dict[str, Any]

# Example handlers:
# - "rmkbridge.junit"
# - "rmkbridge.tosca"
# - "rmkbridge.cypress"
# - "rmkbridge.playwright"
```

**Handler Interface:**
```python
class BaseHandler:
    def parse_results(self, source_path: str, **metadata) -> Dict[str, Any]:
        """
        Parse test results from source_path.
        
        Args:
            source_path: Path to test result file
            **metadata: Handler-specific parameters
        
        Returns:
            Dict with keys:
            - "robot_xml": Robot Framework XML string
            - "parsed_data": Extracted test information
        """
        pass
```

**Handler Resolution Algorithm:**
1. Try exact match: `handlers[handler_name]`
2. Try with prefix: `handlers["rmkbridge." + handler_name]`
3. Try keyword match: Find handler where `handler.keyword == handler_name.lower().replace(" ", "_")`
4. Raise `HandlerResolutionError` if not found

---

### Integration with Robot Framework

**Purpose:** Generate HTML log from Robot XML

```python
from robot.api import ResultWriter

# After handler converts to Robot XML:
robot_xml_string = handler_result["robot_xml"]

# Generate HTML log:
with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as xml_file:
    xml_file.write(robot_xml_string.encode("utf-8"))
    xml_path = xml_file.name

html_path = xml_path.replace(".xml", ".html")
ResultWriter(xml_path).write_results(log=html_path)

with open(html_path, "r") as f:
    html_log = f.read()
```

---

### Integration with Robotmk

**Robotmk Result Folder Discovery:**
```python
# Read Robotmk config to find results folder:
with open("/etc/check_mk/robotmk.json", "r") as f:
    robotmk_config = json.load(f)

results_folder = robotmk_config.get("results_folder") or \
    "/var/lib/check_mk_agent/robotmk/scheduler/results/plans"
```

**Result File Naming:**
```python
result_path = f"{results_folder}/{plan_name}.json"
```

**Robotmk Service Discovery:**
- Robotmk plugin (separate) reads JSON files from results folder
- Discovers services like "Robotmk Suite: <test_name>"
- Bridge plugin and Robotmk plugin operate independently
- Bridge provides input (JSON files) for Robotmk consumption

---

## Handler Resolution System

### Handler Resolution Flow

```
User Config: "handler": "junit"
  ↓
resolve_handler("junit")
  ↓
_get_rmkbridgeCORE()  # Cached instance
  ↓
core.handlers  # Dict of all available handlers
  ↓
Try exact match: "junit" in handlers?
  ↓ no
Try with prefix: "rmkbridge.junit" in handlers?
  ↓ yes ✓
Return ResolvedHandler(handler_key="rmkbridge.junit", handler=<handler_obj>)
  ↓
Prepare call: _prepare_handler_call(handler, source_path, metadata)
  ↓
Introspect handler.parse_results signature
  ↓
Map source_path to first parameter
  ↓
Map metadata dict to named parameters
  ↓
Call: handler.parse_results(*args, **kwargs)
  ↓
Catch exceptions → HandlerExecutionError
  ↓
Return: HandlerConversionResult
```

---

### Parameter Injection

**Handler Signature Introspection:**

Example handler signature:
```python
def parse_results(self, source: str, suite_name: str = "default", **extra):
    pass
```

**Configured metadata:**
```json
{
  "suite_name": "MyTests",
  "custom_param": "value"
}
```

**Prepared call:**
```python
args = ["/path/to/result.xml"]  # source_path
kwargs = {
    "suite_name": "MyTests",      # From metadata, matches parameter
    "custom_param": "value"        # Captured by **extra
}

handler.parse_results(*args, **kwargs)
```

**Parameter Binding Rules:**
1. First parameter always receives `source_path`
2. Named parameters matched from `metadata` dict
3. Missing required parameters → `HandlerConfigurationError`
4. Extra metadata keys captured by `**kwargs` if present
5. Parameters with defaults are optional

---

## Configuration Architecture

### Configuration Sources

```
┌─────────────────────────────────────────────────────────┐
│  Configuration Hierarchy                                 │
├─────────────────────────────────────────────────────────┤
│  1. Checkmk WATO UI                                      │
│     • User defines Bakery rule                           │
│     • Per-host or folder-based                           │
│                                                          │
│  2. Agent Baking                                         │
│     • Generates /etc/check_mk/robotmk-bridge-plugin.json │
│     • Includes only rules applying to baked host         │
│                                                          │
│  3. Agent Plugin Runtime                                 │
│     • Reads JSON config file                             │
│     • Validates config structure                         │
│     • Applies defaults (plan_name, piggyback_host)       │
│                                                          │
│  4. Handler Metadata                                     │
│     • Handler-specific parameters in config.metadata     │
│     • Injected into handler.parse_results()              │
└─────────────────────────────────────────────────────────┘
```

---

### Configuration Schema Validation

**Agent Plugin Config Validation:**
```python
def validate_config(config_list: List[Dict]) -> List[Config]:
    """Validate and parse configuration."""
    configs = []
    for item in config_list:
        if "path" not in item:
            raise ValueError("Missing required field: path")
        if "handler" not in item:
            raise ValueError("Missing required field: handler")
        
        configs.append(Config(
            path=item["path"],
            handler=item["handler"],
            plan_name=item.get("plan_name") or item["handler"],
            piggyback_host=item.get("piggyback_host"),
            max_age=item.get("max_age"),
            metadata=item.get("metadata") or {}
        ))
    return configs
```

---

## Deployment Architecture

### Deployment Components

```
┌─────────────────────────────────────────────────────────┐
│  CHECKMK SERVER                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  MKP Package (robotmk-bridge-plugin-VERSION.mkp)   │ │
│  │  ┌──────────────────────────────────────────────┐  │ │
│  │  │  agents/plugins/robotmk_bridge_plugin.py     │  │ │
│  │  │  checks/robotmk_bridge_plugin.py             │  │ │
│  │  │  web/plugins/wato/*bakery-params.py          │  │ │
│  │  │  web/plugins/wato/*check-params.py           │  │ │
│  │  └──────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
            │
            │ (1) Install MKP
            ▼
┌─────────────────────────────────────────────────────────┐
│  CHECKMK SERVER (post-install)                           │
│  /omd/sites/<site>/local/                                │
│    ├── share/check_mk/                                   │
│    │   ├── agents/plugins/robotmk_bridge_plugin.py       │
│    │   ├── checks/robotmk_bridge_plugin.py               │
│    │   └── web/plugins/wato/*.py                         │
└─────────────────────────────────────────────────────────┘
            │
            │ (2) Configure Bakery Rule
            │ (3) Bake Agent
            ▼
┌─────────────────────────────────────────────────────────┐
│  BAKED AGENT PACKAGE                                     │
│  ┌────────────────────────────────────────────────────┐ │
│  │  check-mk-agent-<host>.deb / .rpm                   │ │
│  │  ┌──────────────────────────────────────────────┐  │ │
│  │  │  usr/lib/check_mk_agent/plugins/             │  │ │
│  │  │    robotmk_bridge_plugin.py                   │  │ │
│  │  │  etc/check_mk/                                │  │ │
│  │  │    robotmk-bridge-plugin.json (from Bakery)   │  │ │
│  │  └──────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
            │
            │ (4) Deploy Agent
            ▼
┌─────────────────────────────────────────────────────────┐
│  MONITORED HOST                                          │
│  /usr/bin/check_mk_agent                                 │
│  /usr/lib/check_mk_agent/plugins/robotmk_bridge_plugin.py││  /etc/check_mk/robotmk-bridge-plugin.json               │
│                                                          │
│  Dependencies (must be pre-installed):                   │
│  • Python 3.x                                            │
│  • robotframework-robotmk-bridge package                 │
│  • Robot Framework                                       │
└─────────────────────────────────────────────────────────┘
```

---

### Deployment Steps

1. **Install MKP on Checkmk Server**
   ```bash
   cmk -P install robotmk-bridge-plugin-0.3.0-cmk2.4.mkp
   ```

2. **Configure Bakery Rule**
   - Navigate to Setup → Agents → Windows, Linux, Solaris, AIX → Agent rules
   - Find "Robotmk Bridge Plugin"
   - Create rule with configurations (paths, handlers, etc.)
   - Save & apply

3. **Bake Agent**
   - Navigate to Agents → Agent Bakery
   - Select target hosts
   - Bake agents
   - Download baked agent packages

4. **Deploy Agent to Monitored Hosts**
   ```bash
   # Install baked agent
   dpkg -i check-mk-agent-<host>.deb  # Debian/Ubuntu
   rpm -i check-mk-agent-<host>.rpm   # RHEL/CentOS
   
   # Install dependencies
   pip3 install robotframework<7 robotframework-robotmk-bridge==0.1.1
   ```

5. **Verify Installation**
   ```bash
   # Test agent plugin execution
   /usr/lib/check_mk_agent/plugins/robotmk_bridge_plugin.py
   
   # Check agent section output
   /usr/bin/check_mk_agent | grep -A 20 "<<<robotmk_bridge>>>"
   ```

6. **Service Discovery**
   - Run service discovery on host
   - Discover "RMKBridge Status" and per-plan services
   - Activate changes

---

## Testing Architecture

### Test Structure

```
tests/
├── agent_plugin/               # Agent plugin unit tests
│   ├── test_agent_output.py    # Agent section generation
│   ├── test_file_discovery.py  # File discovery & age filtering
│   └── test_robotmk_result.py  # Robotmk JSON generation
│
├── check/                      # Check plugin unit tests
│   ├── test_check.py           # Main check function
│   ├── test_check_plan.py      # Per-plan checks
│   ├── test_discovery.py       # Service discovery
│   └── test_discovery_plan.py  # Per-plan discovery
│
├── resources/                  # Test fixtures
│   ├── test_output/            # Sample test tool outputs
│   └── conftest.py             # Pytest fixtures
│
└── conftest.py                 # Root fixtures
```

---

### Test Categories

**1. Agent Plugin Tests**
- **File Discovery:** Glob patterns, concrete paths, age filtering
- **Handler Resolution:** Name matching, error handling
- **Conversion:** Mock handlers, parameter injection
- **Robotmk JSON:** Structure validation, field population
- **Agent Output:** Section formatting, JSON encoding

**2. Check Plugin Tests**
- **Parsing:** Valid/invalid JSON, missing fields
- **Discovery:** Service creation, per-plan services
- **Check Logic:** State determination (OK/WARN/CRIT)
- **Metrics:** Metric generation, value validation
- **Edge Cases:** Empty sections, missing plans

**3. Integration Tests** (future)
- End-to-end: Test file → conversion → agent section → check
- Real handlers from `robotframework-robotmk-bridge`
- Checkmk service lifecycle

---

### Test Execution

```bash
# Run all tests
pytest

# Run specific category
pytest tests/agent_plugin/
pytest tests/check/

# Run with coverage
pytest --cov=agents_plugins --cov=checks --cov-report=html

# Run single test
pytest tests/agent_plugin/test_file_discovery.py::test_discover_files_glob
```

---

### Mocking Strategy

**Example: Mock Handler**
```python
@pytest.fixture
def mock_handler():
    """Mock robotframework-robotmk-bridge handler."""
    handler = MagicMock()
    handler.parse_results.return_value = {
        "robot_xml": "<robot>...</robot>",
        "parsed_data": {"tests": 5, "passed": 4, "failed": 1}
    }
    return handler
```

**Example: Mock Agent Section**
```python
@pytest.fixture
def section_payload_string():
    """Agent section as string table (Checkmk format)."""
    payload = {
        "summary": {"configs": 1, "files_total": 1, "files_success": 1},
        "plans": {...},
        "runtime_s": 1.5
    }
    return [[json.dumps(payload)]]
```

---

## Design Patterns & Principles

### 1. Plugin Architecture Pattern

**Pattern:** Each component (agent, check, web) is loosely coupled via well-defined interfaces.

**Benefits:**
- Components can evolve independently
- Easy to test in isolation
- Clear separation of concerns

**Implementation:**
- Agent outputs structured JSON
- Check consumes JSON via standard Checkmk APIs
- Web plugins generate configuration files

---

### 2. Handler Pattern

**Pattern:** Conversion logic delegated to external handlers in `robotframework-robotmk-bridge`.

**Benefits:**
- Extensibility without modifying core plugin
- Community can contribute handlers
- Separation of parsing logic from orchestration

**Implementation:**
- Dynamic handler resolution from package
- Signature introspection for parameter injection
- Error isolation (handler failure doesn't crash plugin)

---

### 3. Strategy Pattern (Handler Selection)

**Pattern:** Handler selection based on configuration, resolved at runtime.

**Benefits:**
- Flexible configuration
- Support for multiple test tools
- User controls conversion strategy

**Implementation:**
```python
handler_name = config.handler  # From user config
resolved = resolve_handler(handler_name)  # Runtime resolution
result = resolved.handler.parse_results(...)  # Execute strategy
```

---

### 4. Adapter Pattern (Robot Framework Integration)

**Pattern:** Bridge plugin acts as adapter between arbitrary test formats and Robotmk's expected format.

**Benefits:**
- Preserves existing Robotmk infrastructure
- No changes needed to Robotmk plugin
- Universal compatibility

**Implementation:**
- Any format → Robot XML (via handlers)
- Robot XML → Robotmk JSON (via bridge)
- Robotmk JSON → Checkmk services (via Robotmk plugin)

---

### 5. Self-Monitoring Pattern

**Pattern:** Agent plugin reports its own health and performance metrics.

**Benefits:**
- Visibility into bridge operations
- Early detection of configuration errors
- Troubleshooting support

**Implementation:**
- Agent section: `<<<robotmk_bridge>>>`
- Check plugin: `robotmk_bridge_plugin.py`
- Services: "RMKBridge Status", per-plan services

---

### 6. Dataclass Pattern

**Pattern:** Use Python dataclasses for structured data.

**Benefits:**
- Type safety
- Auto-generated `__init__`, `__repr__`
- Clear data contracts

**Examples:**
- `Config` - Configuration entry
- `FileRunRecord` - File processing record
- `BridgeRunReport` - Overall execution report
- `HandlerConversionResult` - Conversion output

---

### SOLID Principles Applied

**Single Responsibility:**
- Agent plugin: file discovery & conversion
- Check plugin: monitoring & metrics
- Web plugins: UI configuration
- Handlers: format-specific parsing

**Open/Closed:**
- Open for extension: new handlers via `robotframework-robotmk-bridge`
- Closed for modification: core plugin logic stable

**Liskov Substitution:**
- Handlers implement consistent interface
- Any handler can replace another (for its format)

**Interface Segregation:**
- Minimal interface for handlers (`parse_results()`)
- Minimal interface for check plugin (Checkmk API v2)

**Dependency Inversion:**
- Depends on abstractions: handler interface, Checkmk APIs
- Not on concrete implementations

---

## Security Considerations

### File Access
- Agent plugin runs with Checkmk agent privileges
- Reads test result files (configured paths)
- Writes to Robotmk results folder
- **Risk:** Misconfigured paths could expose sensitive files
- **Mitigation:** Validate paths, use permissions

### Handler Execution
- Dynamic handler resolution from `robotframework-robotmk-bridge` package
- Handler code executes in agent context
- **Risk:** Malicious handler could execute arbitrary code
- **Mitigation:** Only install trusted handlers, review handler code

### Configuration Injection
- Configuration comes from Checkmk Bakery (trusted source)
- **Risk:** Compromised Checkmk server could inject malicious config
- **Mitigation:** Secure Checkmk server, use RBAC

---

## Performance Characteristics

### Agent Plugin
- **Execution Frequency:** Every agent run (typically 60s)
- **Processing Time:** Seconds to minutes depending on:
  - Number of configured paths
  - Size of test result files
  - Complexity of handler parsing
  - Robot HTML generation time
- **Memory:** Depends on test result size (loaded into memory)
- **Disk I/O:** Read test files, write Robotmk JSON, write agent section

### Check Plugin
- **Evaluation Frequency:** Every check interval (typically 60s)
- **Processing Time:** Milliseconds (parse JSON, evaluate logic)
- **Memory:** Minimal (only agent section data)

---

## Future Architecture Enhancements

### Planned
1. **Result Merging** - Use `rebot` to merge multiple test files before conversion
2. **Async Processing** - Parallelize file conversions
3. **Caching** - Skip unchanged files (checksum-based)
4. **Handler Validation** - Pre-flight handler compatibility checks
5. **Extended Metrics** - Per-handler performance, conversion success rates

### Under Consideration
1. **Webhook Support** - Trigger conversions on test completion
2. **Streaming** - Process large files without loading entirely
3. **Handler Marketplace** - Centralized handler discovery
4. **Configuration Validation UI** - Pre-deployment config testing

---

## Related Documentation

### Technical Documentation

- [Project Overview](./project-overview.md) - High-level project summary
- [Source Tree Analysis](./source-tree-analysis.md) - Detailed directory structure
- [Development Guide](./development-guide.md) - Setup and development workflow
- [Taskfile Guide](./taskfile-guide.md) - Development tasks and workflows
- [Test Data Generator](./test-data-generator-continuous.md) - Synthetic test data

### User Documentation

- [User Guide](./user-guide.md) - Complete deployment and configuration guide
- [Documentation Index](./index.md) - Complete documentation overview

### Quick References

- [README.md](../README.md) - Quick start and introduction
- [DEVELOPMENT.md](../DEVELOPMENT.md) - Dev container setup

---

*Generated: 2026-05-15 via bmad-document-project workflow*
