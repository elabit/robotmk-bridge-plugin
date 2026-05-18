# Taskfile Usage Guide

This document describes the available tasks in the project's Taskfile.yml and suggests additional tasks that could be implemented.

## Prerequisites

Install [Task](https://taskfile.dev/) if not already available:

```bash
# macOS
brew install go-task/tap/go-task

# Linux (snap)
sudo snap install task --classic

# Or download binary from https://github.com/go-task/task/releases
```

## Quick Start

```bash
# Show all available tasks
task --list

# Run default task (shows help)
task

# Run a specific task
task gen-data
```

## Available Tasks

### Test Data Generator Tasks

| Task | Description |
|------|-------------|
| `gen-data` | Generate all handler test data files (passed status) |
| `gen-data-failed` | Generate test data with failed status |
| `gen-data-mixed` | Generate test data with mixed pass/fail status |
| `gen-data-custom` | Generate with custom options (e.g., `task gen-data-custom -- --handlers junit`) |
| `gen-data-clean` | Remove generated test data files |
| `gen-data-continuous` | Continuous mode: regenerate every 5 seconds (Ctrl+C to stop) |
| `gen-data-continuous-fast` | Continuous mode: regenerate every 2 seconds (Ctrl+C to stop) |
| `gen-handlers-list` | List all supported handlers |

**Examples:**
```bash
# Generate default test data
task gen-data

# Generate only JUnit test data with failed status
task gen-data-custom -- --status failed --handlers junit

# Clean test data
task gen-data-clean

# Continuous mode (useful for testing agent plugin pick-up)
task gen-data-continuous
# Or faster updates
task gen-data-continuous-fast
```

### Testing Tasks

| Task | Description |
|------|-------------|
| `test` | Run all tests |
| `test-unit` | Run unit tests only (agent_plugin, check, fixtures) |
| `test-e2e` | Run e2e tests only |
| `test-cov` | Run tests with coverage report |
| `test-cov-view` | Open HTML coverage report in browser |
| `test-specific` | Run specific test file (e.g., `task test-specific -- tests/check/test_check.py`) |
| `test-watch` | Run tests in watch mode (requires pytest-watch) |

**Examples:**
```bash
# Run all tests
task test

# Run with coverage
task test-cov

# Run specific test
task test-specific -- tests/agent_plugin/test_conversion.py
```

### Code Quality Tasks

| Task | Description |
|------|-------------|
| `lint` | Run flake8 linter |
| `format` | Format code with black |
| `format-check` | Check formatting without modifying (CI mode) |
| `validate-docs` | Validate version pinning in documentation |
| `validate` | Run all validation checks (format-check + lint + validate-docs + test) |

**Examples:**
```bash
# Format all code
task format

# Run linter
task lint

# Validate documentation version pinning
task validate-docs

# Run all validation checks (recommended before committing)
task validate
```

# Check if formatting is needed (CI)
task format-check

# Run full validation suite
task validate
```

### Build Tasks

| Task | Description |
|------|-------------|
| `build` | Build the MKP package |
| `build-clean` | Clean build artifacts and caches |

### Development/Deployment Tasks

| Task | Description |
|------|-------------|
| `sync-to-cmk` | Sync workspace files to CMK site |
| `sync-from-cmk` | Sync CMK site files back to workspace |
| `cmk-restart` | Restart the CMK site |
| `cmk-status` | Show CMK site status |
| `cmk-errors` | Check Python syntax in plugins |

**Examples:**
```bash
# Deploy changes to CMK
task sync-to-cmk
task cmk-restart

# Pull changes from CMK back to workspace
task sync-from-cmk
```

### Setup Tasks

| Task | Description |
|------|-------------|
| `setup` | Install Python dependencies |
| `setup-verify` | Verify development environment setup |

### Documentation Tasks

| Task | Description |
|------|-------------|
| `docs-schema` | Validate Robotmk JSON schema |
| `docs-handlers` | Show handlers.yaml contents |

### Utility Tasks

| Task | Description |
|------|-------------|
| `clean` | Clean all generated files (test data, build, cache) |
| `info` | Show project information |
| `help` | Show all available tasks |

## Common Workflows

### Development Workflow

```bash
# 1. Generate test data
task gen-data

# 2. Run tests
task test

# 3. Format code
task format

# 4. Validate everything
task validate

# 5. Sync to CMK and restart
task sync-to-cmk
task cmk-restart
```

### Testing Agent Plugin with Continuous Data Generation

```bash
# Start continuous data generation in one terminal
task gen-data-continuous

# In another terminal, run the agent plugin repeatedly
watch -n 5 python3 agents_plugins/robotmk_bridge_plugin.py

# Or start the agent plugin in a loop with the bridge config
while true; do
  python3 agents_plugins/robotmk_bridge_plugin.py
  sleep 10
done
```

### Using Continuous Mode CLI Directly

```bash
# Continuous mode with default 5s interval
python3 -m tests.data_generator --continuous

# Custom interval (10 seconds)
python3 -m tests.data_generator -c -i 10

# Continuous with mixed status and verbose output
python3 -m tests.data_generator -c -i 3 -s mixed -v

# Continuous mode with specific handlers only
python3 -m tests.data_generator -c -i 5 --handlers junit gatling

# Stop with Ctrl+C - graceful shutdown after current generation
```

### CI/CD Pipeline

```bash
# Check code quality
task format-check
task lint

# Run tests with coverage
task test-cov

# Build package
task build
```

## Suggested Additional Tasks

The following tasks could be added to enhance the Taskfile:

### 1. Integration Testing Tasks

```yaml
  test-integration:
    desc: Run full integration tests against live CMK site
    cmds:
      - task: gen-data
      - task: sync-to-cmk
      - task: cmk-restart
      - sleep 5  # Wait for site to fully restart
      - python3 tests/integration/test_live_site.py

  test-integration-clean:
    desc: Clean up after integration tests
    cmds:
      - rm -rf /tmp/robotmk-bridge-test-*
```

### 2. Package Management Tasks

```yaml
  build-mkp:
    desc: Build MKP package with version from git
    vars:
      VERSION:
        sh: git describe --tags --always
    cmds:
      - python3 scripts/build_mkp.py --version {{.VERSION}}

  build-version:
    desc: Show build version
    cmds:
      - git describe --tags --always

  release-check:
    desc: Check if ready for release (tests, format, changelog)
    cmds:
      - task: validate
      - test -f CHANGELOG.md || (echo "CHANGELOG.md missing" && exit 1)
      - echo "✓ Ready for release"
```

### 3. Documentation Tasks

```yaml
  docs-generate:
    desc: Generate API documentation
    cmds:
      - python3 -m pydoc -w agents_plugins.robotmk_bridge_plugin
      - python3 -m pydoc -w checks.robotmk_bridge_plugin

  docs-serve:
    desc: Serve documentation locally
    cmds:
      - python3 -m http.server 8000 -d docs/

  docs-update-readme:
    desc: Update README with latest examples
    cmds:
      - python3 scripts/update_readme_examples.py
```

### 4. Debugging Tasks

```yaml
  debug-agent-output:
    desc: Show agent plugin output
    cmds:
      - python3 agents_plugins/robotmk_bridge_plugin.py

  debug-config:
    desc: Show current configuration
    cmds:
      - cat /omd/sites/cmk/etc/check_mk/robotmk_bridge.json

  debug-logs:
    desc: Tail CMK logs
    cmds:
      - tail -f /omd/sites/cmk/var/log/cmc.log

  debug-section:
    desc: Show agent section output for testing
    cmds:
      - python3 agents_plugins/robotmk_bridge_plugin.py | grep -A 100 "<<<robotmk_bridge>>>"
```

### 5. Performance Tasks

```yaml
  bench-conversion:
    desc: Benchmark conversion performance
    cmds:
      - python3 -m pytest tests/benchmarks/ --benchmark-only

  profile-agent:
    desc: Profile agent plugin execution
    cmds:
      - python3 -m cProfile -o profile.stats agents_plugins/robotmk_bridge_plugin.py
      - python3 -m pstats profile.stats -c "sort cumtime" -c "stats 20"
```

### 6. Environment Tasks

```yaml
  env-check:
    desc: Check environment variables and paths
    cmds:
      - echo "BRIDGE_E2E_DATA_DIR=${BRIDGE_E2E_DATA_DIR:-not set}"
      - echo "MK_CONFDIR=${MK_CONFDIR:-not set}"
      - echo "LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-not set}"

  env-activate:
    desc: Show activation command for venv
    cmds:
      - echo "source venv/bin/activate"

  venv-create:
    desc: Create Python virtual environment
    cmds:
      - python3 -m venv venv
      - ./venv/bin/pip install -r requirements.txt
```

### 7. Git Workflow Tasks

```yaml
  git-status:
    desc: Show git status with ignored files
    cmds:
      - git status
      - echo ""
      - echo "=== Untracked (ignored) ==="
      - git status --ignored

  git-clean:
    desc: Clean git-ignored files (interactive)
    cmds:
      - git clean -fdX -i

  git-pre-commit:
    desc: Pre-commit checks (format, lint, test)
    cmds:
      - task: format
      - task: lint
      - task: test-unit
      - echo "✓ Ready to commit"
```

### 8. Security Tasks

```yaml
  security-scan:
    desc: Scan dependencies for security issues
    cmds:
      - python3 -m pip install safety
      - python3 -m safety check --file requirements.txt

  security-audit:
    desc: Run security audit with bandit
    cmds:
      - python3 -m pip install bandit
      - python3 -m bandit -r agents_plugins/ checks/ -ll
```

## Task Dependencies

Tasks can depend on other tasks. Example from existing Taskfile:

```yaml
  test-cov-view:
    desc: Open coverage report in browser
    deps: [test-cov]  # Runs test-cov first
    cmds:
      - xdg-open htmlcov/index.html
```

## Environment Variables

Customize behavior with environment variables:

```bash
# Use different Python
PYTHON=python3.11 task test

# Use different test data directory
BRIDGE_E2E_DATA_DIR=/tmp/test-data task gen-data
```

## Tips

1. **Tab completion**: Enable shell completion for task commands
   ```bash
   # bash
   source <(task --completion bash)
   
   # zsh
   source <(task --completion zsh)
   ```

2. **Watch mode**: Use `-w` flag to run task on file changes
   ```bash
   task -w test
   ```

3. **Silent mode**: Use `-s` flag to suppress task echo
   ```bash
   task -s test
   ```

4. **Parallel execution**: Some tasks can run in parallel
   ```bash
   task lint format  # Runs sequentially by default
   ```


---

## Related Documentation

- **[Development Guide](./development-guide.md)** — Development environment setup
- **[User Guide](./user-guide.md)** — Plugin deployment and configuration
- **[Test Data Generator](./test-data-generator-continuous.md)** — Synthetic test data generation
- **[Architecture](./architecture.md)** — Technical design
- **[Documentation Index](./index.md)** — Complete documentation overview
