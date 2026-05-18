# Validation Scripts

## validate_version_pinning.sh

Validates that all documentation references to `robotframework-robotmk-bridge` include the correct version number from `requirements.txt`.

### Purpose

Ensures documentation consistency and prevents users from installing incompatible or untested package versions.

### Usage

```bash
# Run directly
./scripts/validate_version_pinning.sh

# Via task runner
task validate-docs
```

### What It Checks

The script validates version pinning in:
- `README.md`
- `docs/user-guide.md`
- `docs/development-guide.md`
- `docs/architecture.md`

### Validation Rules

✅ **Pass:** Installation commands with correct version  
```bash
pip3 install robotframework-robotmk-bridge==0.1.1
```

✅ **Pass:** Prose references (no version needed)  
```markdown
The `robotframework-robotmk-bridge` package provides handlers...
```

✅ **Pass:** Informational commands (no version needed)  
```bash
pip3 show robotframework-robotmk-bridge
```

❌ **Fail:** Installation commands without version  
```bash
pip3 install robotframework-robotmk-bridge  # Missing ==0.1.1
```

❌ **Fail:** Installation commands with wrong version  
```bash
pip3 install robotframework-robotmk-bridge==0.2.0  # Wrong version
```

### Exit Codes

- `0`: All documentation is properly version-pinned ✓
- `1`: Issues found or validation error ✗

### GitHub Action

This script runs automatically in CI via `.github/workflows/validate-docs.yml` on:
- Pull requests
- Pushes to main
- Manual workflow dispatch

### Adding New Files

To check additional documentation files, edit the `DOC_FILES` array in the script:

```bash
DOC_FILES=(
    "README.md"
    "docs/user-guide.md"
    "docs/development-guide.md"
    "docs/architecture.md"
    "docs/new-file.md"  # Add here
)
```
