# Test Data Generator - Continuous Mode

The test data generator now supports continuous mode, which regenerates test result files at regular intervals with fresh timestamps and varying execution times.

## Why Continuous Mode?

Continuous mode is useful for:

1. **Testing the agent plugin** - Continuously generate new result files to test how the agent picks them up
2. **Integration testing** - Simulate an environment where tests are constantly running
3. **Monitoring development** - Keep fresh test data available while developing
4. **Load testing** - Generate continuous data flow for performance testing

## Usage

### Basic Continuous Mode

```bash
# Default: regenerate every 5 seconds
python3 -m tests.data_generator --continuous

# Short form
python3 -m tests.data_generator -c
```

### Custom Interval

```bash
# Regenerate every 10 seconds
python3 -m tests.data_generator -c -i 10

# Fast updates every 2 seconds
python3 -m tests.data_generator -c -i 2
```

### With Other Options

```bash
# Continuous with failed status
python3 -m tests.data_generator -c -i 5 -s failed

# Continuous with mixed status and verbose output
python3 -m tests.data_generator -c -i 3 -s mixed -v

# Continuous for specific handlers only
python3 -m tests.data_generator -c -i 5 --handlers junit gatling

# Custom output directory
python3 -m tests.data_generator -c -i 5 -o /tmp/continuous-results
```

### Using Task Commands

```bash
# Continuous mode (5 second interval)
task gen-data-continuous

# Fast continuous mode (2 second interval)
task gen-data-continuous-fast
```

## Stopping Continuous Mode

Press **Ctrl+C** to stop. The generator will finish the current generation and then stop gracefully:

```
[2026-05-15 18:02:57] Generation #5: 3 files updated

Shutdown requested. Stopping after current generation...

Stopped after 5 generation(s)
```

## Features

### Current Timestamps

Every generation creates files with the **current timestamp**, making them appear as if they were just created:

```xml
<!-- JUnit XML -->
<testsuite ... timestamp="2026-05-15T18:04:12" ...>

<!-- ZAP XML -->
<OWASPZAPReport ... generated="2026-05-15T18:04:12Z">
```

```
# Gatling Log (Unix milliseconds)
RUN    RobotmkBridgeSimulation    simulation-001    1778870652123    ...
```

### Varying Execution Times

Each generation produces **different execution times** due to randomization:

- JUnit: Test durations vary by ±30%
- Gatling: Request durations vary by ±40%
- All timestamps reflect actual generation time

## Integration Testing Example

### Scenario: Test Agent Plugin File Pick-up

Terminal 1 - Generate test data continuously:
```bash
task gen-data-continuous
```

Terminal 2 - Run agent plugin in watch mode:
```bash
# Configure the bridge plugin to read from tests/e2e/data/
watch -n 5 python3 agents_plugins/robotmk_bridge_plugin.py
```

Terminal 3 - Monitor generated JSON results:
```bash
# Assuming agent writes to /var/lib/check_mk_agent/robotmk/results/
watch -n 5 'ls -lth /var/lib/check_mk_agent/robotmk/results/ | head -10'
```

### Scenario: Test CMK Integration End-to-End

```bash
# 1. Start continuous data generation
python3 -m tests.data_generator -c -i 10 -s mixed -v &

# 2. Configure bridge plugin via bakery
# (configure paths to point to your output directory)

# 3. Bake and deploy agent
task sync-to-cmk
task cmk-restart

# 4. Monitor services in CMK
# Check that new results appear every 10 seconds

# 5. Stop continuous generation
fg  # Bring to foreground
^C  # Press Ctrl+C
```

## Output Modes

### Verbose Mode (`-v`)

Shows detailed information for each generation:

```
[2026-05-15 18:02:30] Generation #1
Generated 3 test file(s):
  ✓ junit        → junit.xml            (876 bytes)
  ✓ gatling      → gatling.log          (1,244 bytes)
  ✓ zaproxy      → zaproxy.xml          (4,080 bytes)
Waiting 3.0s until next generation...
```

### Compact Mode (default)

Shows first generation details, then compact updates:

```
Generated 3 test file(s):
  ✓ junit        → junit.xml            (876 bytes)
  ✓ gatling      → gatling.log          (1,244 bytes)
  ✓ zaproxy      → zaproxy.xml          (4,080 bytes)
[2026-05-15 18:02:33] Generation #2: 3 files updated
[2026-05-15 18:02:36] Generation #3: 3 files updated
[2026-05-15 18:02:39] Generation #4: 3 files updated
```

## Tips

- **Start with verbose mode** (`-v`) to see what's happening
- **Use shorter intervals** (2-3s) for rapid testing
- **Use longer intervals** (10-30s) for realistic scenarios
- **Check file timestamps** to verify fresh generation: `stat tests/e2e/data/junit.xml`
- **Monitor with watch**: `watch -n 1 'ls -lth tests/e2e/data/'`

## Troubleshooting

**Q: Files aren't being updated?**
- Check the output directory path
- Verify permissions on the output directory
- Run with `-v` to see error messages

**Q: Can I run multiple instances?**
- Yes, as long as they write to different output directories
- Example: `python3 -m tests.data_generator -c -o /tmp/test1 & python3 -m tests.data_generator -c -o /tmp/test2 &`

**Q: How do I see what's happening in the background?**
- Use verbose mode: `-v`
- Or tail the files: `tail -f tests/e2e/data/junit.xml`

## See Also

- **[Taskfile Guide](taskfile-guide.md)** - All available task commands
- **[Development Guide](development-guide.md)** - Development environment setup
- **[User Guide](user-guide.md)** - Plugin deployment and configuration
- **[Documentation Index](index.md)** - Complete documentation overview
- [Test Data Generator README](../tests/data_generator/) - Code documentation
- [handlers.yaml](../handlers.yaml) - Supported handler types
