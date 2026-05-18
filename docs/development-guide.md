# Development Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Development Environment Setup](#development-environment-setup)
3. [Dev Container Workflow](#dev-container-workflow)
4. [Local Development](#local-development)
5. [Testing](#testing)
6. [Building MKP Packages](#building-mkp-packages)
7. [Debugging](#debugging)
8. [Code Quality](#code-quality)
9. [Contribution Workflow](#contribution-workflow)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools

- **Docker** - For dev container environment
- **Visual Studio Code** - With Remote Containers extension
- **Git** - For version control

### Optional Tools

- **Python 3.x** - For local development without containers
- **pytest** - For running tests locally

---

## Development Environment Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/elabit/robotmk-bridge-plugin.git
cd robotmk-bridge-plugin
```

---

### Step 2: Configure Checkmk Versions

Edit `.devcontainer/devcontainer_img_versions.env` to specify which Checkmk versions you want to develop against:

```bash
CMKVERSIONS="2.4.0p12
2.3.0p37
2.2.0p32"
```

**Note:** Each version requires a Docker image (~2-3GB each). Add only versions you need.

---

### Step 3: Build Dev Container Images

```bash
.devcontainer/scripts/devcontainer_img_build.sh
```

**What it does:**
1. Downloads Checkmk Docker images from registry.checkmk.com
2. Builds custom dev images with:
   - Python packages from `.devcontainer/requirements.txt`
   - Utilities: `jq`, `tree`, `htop`, `vim`, `git`, etc.
3. Tags images as `cmk-python3-dev:VERSION`

**Expected Output:**
```
Checkmk 2.4.0p12 ... OK
Building dev image cmk-python3-dev:2.4.0p12 ...
Successfully built abc123
```

**Time:** ~10-15 minutes per version (first run)

---

### Step 4: Generate Dev Container Config

Select which Checkmk version to develop with:

```bash
.devcontainer/scripts/devcontainer_gen.sh
```

**Interactive Selection:**
```
No cmk version (arg1) specified. Select a version:
1) 2.4.0p12
2) 2.3.0p37
3) 2.2.0p32
#? 1
Selected version: 2.4.0p12
+ Generating CMK devcontainer file ...
```

**Or specify version directly:**
```bash
.devcontainer/scripts/devcontainer_gen.sh 2.4.0p12
```

**What it does:**
- Uses `.devcontainer/devcontainer_tpl.json` as template
- Substitutes `${VARIANT}` with selected version
- Writes `.devcontainer/devcontainer.json`

---

### Step 5: Start Dev Container

In VSCode:
1. Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux)
2. Select: **"Remote-Containers: Rebuild Container"**
3. Wait for container to build and start (~3-5 minutes first run)

**What happens:**
1. Docker container starts based on generated config
2. Checkmk site `cmk` is created and started automatically
3. Workspace files are symlinked into OMD site via `.devcontainer/linkfiles.sh`
4. Terminal opens inside container
5. Checkmk UI available at http://127.0.0.1:4999

**Default Credentials:**
- Username: `cmkadmin`
- Password: `cmk`

---

### Step 6: Add OMD Site to Workspace (Optional but Recommended)

For full code completion and debugging:

1. In VSCode, click **File → Add Folder to Workspace**
2. Navigate to `/omd/sites/cmk`
3. Add folder

**Benefits:**
- Code completion works with Checkmk libraries
- Can set breakpoints in symlinked files
- Navigate Checkmk source code

---

## Dev Container Workflow

### File Synchronization

Workspace files are automatically symlinked to OMD site directories.

**Sync Mapping:**
```
Workspace                              → OMD Site
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
agents_plugins/robotmk_bridge_plugin.py → local/share/check_mk/agents/plugins/
checks/robotmk_bridge_plugin.py         → local/share/check_mk/checks/
web_plugins/wato/*.py                   → local/share/check_mk/web/plugins/wato/
checkman/*                              → local/share/check_mk/checkman/
```

**Managed by:** `.devcontainer/linkfiles.sh`

**Force Re-sync:**
```bash
.devcontainer/linkfiles.sh full
```

---

### Common Tasks

#### Run Agent Plugin Directly

```bash
# Execute agent plugin
/omd/sites/cmk/local/share/check_mk/agents/plugins/robotmk_bridge_plugin.py

# Or from workspace
python3 agents_plugins/robotmk_bridge_plugin.py
```

#### Run Full Agent

```bash
# Execute full Checkmk agent (includes all plugins)
/usr/bin/check_mk_agent

# Filter for bridge section
/usr/bin/check_mk_agent | grep -A 50 "<<<robotmk_bridge>>>"
```

#### Check Plugin Validation

```bash
# Validate check plugin syntax
cmk -vv <hostname>

# Test service discovery
cmk -IIv <hostname>

# Manual check execution
cmk --check <hostname>
```

#### Reload Checkmk Configuration

```bash
# After modifying check plugin or web plugins
omd reload

# Or restart site completely
omd restart
```

---

## Local Development

### Run Tests

```bash
# Run all tests
pytest

# Run with output
pytest -v

# Run specific test file
pytest tests/agent_plugin/test_file_discovery.py

# Run single test
pytest tests/agent_plugin/test_file_discovery.py::test_discover_files_glob

# Run with coverage
pytest --cov=agents_plugins --cov=checks --cov-report=html

# View coverage report
open htmlcov/index.html  # Mac
xdg-open htmlcov/index.html  # Linux
```

---

### Code Formatting

```bash
# Format all Python files
black .

# Check without modifying
black --check agents_plugins/ checks/ tests/

# Format specific file
black agents_plugins/robotmk_bridge_plugin.py
```

---

### Linting

```bash
# Lint all files
flake8

# Lint specific directory
flake8 agents_plugins/

# Lint with detailed output
flake8 --show-source --statistics
```

**Configuration:** `.flake8`

---

## Testing

### Test Structure

```
tests/
├── agent_plugin/         # Agent plugin tests
├── check/               # Check plugin tests
├── resources/           # Test fixtures
└── conftest.py          # Shared fixtures
```

---

### Writing Tests

#### Example: Agent Plugin Test

```python
import pytest
from agents_plugins.robotmk_bridge_plugin import discover_files, Config

def test_discover_files_concrete(tmp_path):
    """Test discovery of concrete file path."""
    # Setup
    test_file = tmp_path / "result.xml"
    test_file.write_text("test data")
    
    config = Config(path=str(test_file), handler="junit")
    
    # Execute
    files = list(discover_files(config))
    
    # Assert
    assert len(files) == 1
    assert files[0] == str(test_file)
```

#### Example: Check Plugin Test

```python
import pytest
from checks.robotmk_bridge_plugin import check_robotmk_bridge
from cmk.agent_based.v2 import State

def test_check_state_ok():
    """Test check returns OK when no errors."""
    section = {
        "summary": {
            "files_total": 1,
            "files_success": 1,
            "files_error": 0,
            "files_missing": 0
        },
        "plans": {},
        "runtime_s": 1.5
    }
    
    results = list(check_robotmk_bridge(section))
    
    assert any(r.state == State.OK for r in results)
```

---

### Test Fixtures

Common fixtures are defined in `tests/conftest.py` and `tests/*/conftest.py`:

```python
@pytest.fixture
def tmpdir(tmp_path):
    """Temporary directory for test files."""
    return tmp_path

@pytest.fixture
def mock_handler():
    """Mock robotframework-robotmk-bridge handler."""
    handler = MagicMock()
    handler.parse_results.return_value = {
        "robot_xml": "<robot>...</robot>",
        "parsed_data": {}
    }
    return handler

@pytest.fixture
def section_payload_parsed():
    """Parsed agent section for check plugin tests."""
    return {
        "summary": {"configs": 1, "files_total": 1, "files_success": 1},
        "plans": {...},
        "runtime_s": 1.5
    }
```

---

## Building MKP Packages

### Build for Single Version

```bash
# From workspace root
.devcontainer/build.sh 0.3.0

# Specify Checkmk version
.devcontainer/build.sh 0.3.0 2.4
```

**What it does:**
1. Validates version format
2. Selects appropriate `pkginfo/cmk2.X.json`
3. Runs `cmk -P pack` command
4. Outputs MKP to `build/` directory

**Output:**
```
build/robotmk-bridge-plugin-0.3.0-cmk2.4.mkp
```

---

### Build for All Versions (CI/CD)

GitHub Actions workflow builds MKPs automatically on release.

**Workflow:** `.github/workflows/build-mkp.yml`

**Triggers:**
- Manual dispatch (workflow_dispatch)
- Release tag push (`v*`)

**Jobs:**
- `build-mkp-cmk23` - Build for Checkmk 2.3
- `build-mkp-cmk24` - Build for Checkmk 2.4
- `build-mkp-cmk25` - Build for Checkmk 2.5 (commented out)

---

### Install MKP Locally

```bash
# Inside dev container
cmk -P install build/robotmk-bridge-plugin-0.3.0-cmk2.4.mkp

# Verify installation
cmk -P list | grep robotmk-bridge

# Reload Checkmk
omd reload
```

---

## Debugging

### Debug Agent Plugin

#### Method 1: Direct Execution with Print Statements

```python
# agents_plugins/robotmk_bridge_plugin.py

def main():
    print(f"DEBUG: Config path={config_path}", file=sys.stderr)
    configs = load_config(config_path)
    print(f"DEBUG: Loaded {len(configs)} configs", file=sys.stderr)
    ...
```

```bash
# Run plugin
python3 agents_plugins/robotmk_bridge_plugin.py 2>&1 | less
```

---

#### Method 2: VSCode Debugger

1. Add `/omd/sites/cmk` folder to workspace
2. Open `local/share/check_mk/agents/plugins/robotmk_bridge_plugin.py` (symlinked file)
3. Set breakpoints
4. Run Python debugger (F5) with launch config:

```json
{
    "name": "Debug Agent Plugin",
    "type": "debugpy",
    "request": "launch",
    "program": "/omd/sites/cmk/local/share/check_mk/agents/plugins/robotmk_bridge_plugin.py",
    "console": "integratedTerminal",
    "justMyCode": false
}
```

---

### Debug Check Plugin

#### Method 1: Manual Check Execution

```bash
# Enable debug output
cmk -vvv --debug <hostname>

# Check specific service
cmk --check-discoveryonly <hostname> "RMKBridge Status"
```

---

#### Method 2: Interactive Python

```python
# Inside dev container Python shell
import sys
sys.path.insert(0, '/omd/sites/cmk/local/share/check_mk/checks')

import robotmk_bridge_plugin

# Load test data
section = {...}

# Run discovery
services = list(robotmk_bridge_plugin.discover_robotmk_bridge(section))
print(services)

# Run check
results = list(robotmk_bridge_plugin.check_robotmk_bridge(section))
print(results)
```

---

### Debug Web Plugins

#### View Generated Configuration

```bash
# Agent configuration generated by Bakery
cat /etc/check_mk/robotmk-bridge-plugin.json | jq
```

#### Test Bakery Rule

1. Navigate to Web UI: http://127.0.0.1:4999
2. Setup → Agents → Agent rules → Robotmk Bridge Plugin
3. Create test rule
4. Bake agent for test host
5. Download and inspect baked agent package

---

## Code Quality

### Pre-Commit Checks

Before committing, run:

```bash
# Format code
black .

# Lint code
flake8

# Validate documentation
task validate-docs  # or ./scripts/validate_version_pinning.sh

# Run tests
pytest

# Check coverage
pytest --cov=agents_plugins --cov=checks --cov-report=term-missing

# Or run all validation checks at once
task validate
```

---

### Version Pinning Validation

All documentation references to `robotframework-robotmk-bridge` must include the exact version number from `requirements.txt`.

**Why?** This ensures users always install the tested, compatible version of the handler package.

**Validation:**
```bash
# Run validation script
task validate-docs

# Or directly
./scripts/validate_version_pinning.sh
```

**Rules:**
- `pip install` commands must specify version: `pip3 install robotframework-robotmk-bridge==0.1.1`
- `pip show` commands can omit version (informational only)
- Prose references to the package name don't need version numbers

**GitHub Action:**
The `validate-docs.yml` workflow automatically checks version pinning on all PRs.

---

### Code Style Guidelines

**Follow:** `.github/instructions/python.instructions.md`

**Key Points:**
- Use `black` for formatting (line length: 100)
- Follow PEP 8 conventions
- Use type hints where applicable
- Write docstrings for public functions
- Use dataclasses for structured data

---

### Docstring Format

```python
def resolve_handler(handler_name: str) -> ResolvedHandler:
    """
    Resolve a configured handler name to a robotframework-robotmk-bridge handler instance.
    
    Args:
        handler_name: Handler name from configuration (e.g., "junit", "rmkbridge.tosca")
    
    Returns:
        ResolvedHandler containing handler_key and handler instance
    
    Raises:
        HandlerResolutionError: If handler cannot be found
    
    Examples:
        >>> resolve_handler("junit")
        ResolvedHandler(handler_key="rmkbridge.junit", handler=<junit_handler>)
    """
    ...
```

---

## Contribution Workflow

### Commit Message Format

This project uses **Conventional Commits** for automated changelog generation.

**Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat` - New feature (minor version bump)
- `fix` - Bug fix (patch version bump)
- `chore` - Maintenance (no version bump)
- `docs` - Documentation changes
- `test` - Test additions/changes
- `refactor` - Code refactoring

**Scopes:**
- `agent` - Agent plugin changes
- `check` - Check plugin changes
- `web` - Web plugins changes
- `tests` - Test changes
- `ci` - CI/CD changes

**Examples:**
```
feat(agent): add support for glob patterns in file paths

fix(check): correct state determination for missing files

chore(ci): update GitHub Actions to v4

docs(readme): add deployment instructions
```

---

### Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make Changes**
   - Write code
   - Add/update tests
   - Update documentation

3. **Run Quality Checks**
   ```bash
   black .
   flake8
   pytest
   ```

4. **Commit with Conventional Format**
   ```bash
   git add .
   git commit -m "feat(agent): add piggyback support"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/my-feature
   ```
   - Create PR on GitHub
   - CI workflows run automatically
   - Wait for review

6. **Address Review Comments**
   - Make requested changes
   - Push additional commits
   - CI re-runs automatically

7. **Merge**
   - Squash merge (recommended)
   - release-please creates automated release

---

### Release Process

**Automated via release-please:**

1. Commits with conventional format are analyzed
2. `release-please` bot creates/updates "Release PR"
3. Release PR includes:
   - Updated `CHANGELOG.md`
   - Version bump in `pkginfo/*.json`
   - Release notes
4. Merge Release PR → triggers:
   - Git tag creation (`v0.3.0`)
   - GitHub Release creation
   - MKP build workflow (attaches MKP files to release)

**Manual Release (if needed):**
```bash
# Tag release
git tag v0.3.0
git push origin v0.3.0

# Manually trigger build-mkp workflow from GitHub UI
```

---

## Troubleshooting

### Dev Container Won't Start

**Symptom:** Container fails to build or start

**Solutions:**
1. Check Docker is running
2. Verify disk space (dev images are large ~2-3GB each)
3. Rebuild container: `Cmd+Shift+P` → "Rebuild Container"
4. Check Docker logs: `docker logs <container_id>`

---

### Agent Plugin Not Executing

**Symptom:** No agent section output

**Checks:**
1. Verify plugin is executable:
   ```bash
   chmod +x /omd/sites/cmk/local/share/check_mk/agents/plugins/robotmk_bridge_plugin.py
   ```

2. Check Python shebang:
   ```python
   #!/usr/bin/env python3
   ```

3. Test direct execution:
   ```bash
   python3 agents_plugins/robotmk_bridge_plugin.py
   ```

4. Check agent output:
   ```bash
   /usr/bin/check_mk_agent 2>&1 | grep -A 20 robotmk_bridge
   ```

---

### Handler Not Found

**Symptom:** `HandlerResolutionError: Unknown handler 'xyz'`

**Solutions:**
1. Verify `robotframework-robotmk-bridge` is installed:
   ```bash
   pip3 list | grep robotframework-robotmk-bridge
   ```

2. List available handlers:
   ```python
   from rmkbridge.rmkbridge import RobotmkBridgeCore
   core = RobotmkBridgeCore()
   print(list(core.handlers.keys()))
   ```

3. Check handler name spelling in configuration

---

### Check Plugin Not Discovering Services

**Symptom:** Services not appearing in Checkmk

**Checks:**
1. Verify agent section is present:
   ```bash
   /usr/bin/check_mk_agent | grep robotmk_bridge
   ```

2. Test service discovery:
   ```bash
   cmk -IIv <hostname>
   ```

3. Check for errors:
   ```bash
   tail -f /omd/sites/cmk/var/log/web.log
   tail -f /omd/sites/cmk/var/log/cmc.log
   ```

4. Reload Checkmk:
   ```bash
   omd reload
   ```

---

### Tests Failing

**Symptom:** `pytest` shows failures

**Solutions:**
1. Verify dependencies are installed:
   ```bash
   pip3 install -r requirements.txt
   ```

2. Check Python version (3.x required):
   ```bash
   python3 --version
   ```

3. Run tests with verbose output:
   ```bash
   pytest -vvv
   ```

4. Check for missing fixtures or imports

---

### Coverage Reports Not Generating

**Solution:**
```bash
# Install coverage package
pip3 install pytest-cov

# Generate report
pytest --cov=agents_plugins --cov=checks --cov-report=html

# View report
open htmlcov/index.html
```

---

## Related Documentation

### For Developers

- **[Architecture](./architecture.md)** — Technical design and component details
- **[Source Tree Analysis](./source-tree-analysis.md)** — Codebase structure guide
- **[Taskfile Guide](./taskfile-guide.md)** — Development workflow tasks and commands
- **[Test Data Generator](./test-data-generator-continuous.md)** — Synthetic test data for development

### For Users

- **[User Guide](./user-guide.md)** — End-to-end guide for deploying and configuring the plugin
- **[Documentation Index](./index.md)** — Complete documentation overview

---

## Additional Resources

- **Checkmk Plugin API:** https://docs.checkmk.com/latest/en/devel_check_plugins.html
- **Robot Framework:** https://robotframework.org/
- **robotframework-robotmk-bridge:** https://github.com/elabit/robotmk-bridge
- **Conventional Commits:** https://www.conventionalcommits.org/
- **release-please:** https://github.com/googleapis/release-please

---

## Getting Help

- **GitHub Issues:** https://github.com/elabit/robotmk-bridge-plugin/issues
- **Discussions:** Use GitHub Discussions for questions
- **Email:** Contact ELABIT GmbH for commercial support

---

*Generated: 2026-05-15 via bmad-document-project workflow*
