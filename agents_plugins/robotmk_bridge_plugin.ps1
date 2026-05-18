# Robotmk Bridge Plugin — Windows wrapper (PowerShell)
# Checks for Python and the main Python script before execution.

# Determine script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonScript = Join-Path $ScriptDir "robotmk_bridge_plugin.py"

# Error section helper
function Emit-Error {
    param([string]$Message)
    Write-Output "<<<robotmk_bridge>>>"
    Write-Output "{`"status`": `"error`", `"error_type`": `"wrapper`", `"message`": `"$Message`"}"
}

# Check 1: Python available on PATH (try python3 first, then python)
$PythonCmd = $null
if (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PythonCmd = "python3"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} else {
    Emit-Error "Python not found on PATH."
    exit 1
}

# Check 2: Python script exists next to this wrapper
if (-not (Test-Path $PythonScript)) {
    Emit-Error "robotmk_bridge_plugin.py not found next to wrapper."
    exit 1
}

# All checks passed — set marker env var and invoke Python script
# This env var tells the Python script it's being called via the wrapper
$env:ROBOTMK_BRIDGE_WRAPPER = "1"
& $PythonCmd $PythonScript
exit $LASTEXITCODE
