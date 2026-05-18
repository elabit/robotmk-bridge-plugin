#!/bin/bash
# Validate that requirements.txt uses exact version pins (==) for all packages.
# No range pins (>=, ~=, etc.) or unpinned entries allowed.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

REQUIREMENTS_FILE="requirements.txt"
ISSUES_FOUND=0

echo "Validating requirements.txt for exact version pinning..."
echo ""

if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
    echo -e "${RED}Error: $REQUIREMENTS_FILE not found${NC}"
    exit 1
fi

# Process each non-comment, non-empty line
while IFS= read -r line || [[ -n "$line" ]]; do
    # Skip empty lines and comments
    if [[ -z "$line" ]] || [[ "$line" =~ ^[[:space:]]*# ]]; then
        continue
    fi
    
    # Extract package name (everything before ==, >=, etc.)
    PACKAGE_NAME=$(echo "$line" | sed -E 's/([a-zA-Z0-9_-]+).*/\1/')
    
    # Check if line has exact pin (==)
    if echo "$line" | grep -qE '^[a-zA-Z0-9_-]+==([0-9]+\.)*[0-9]+$'; then
        echo -e "${GREEN}✓ $line${NC}"
    else
        # Check for range or unpinned specifiers
        if echo "$line" | grep -qE '(>=|<=|>|<|~=|\^)'; then
            echo -e "${RED}✗ $line${NC}"
            echo -e "   Error: Range or flexible version specifier detected. Use exact pin (==)."
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        elif ! echo "$line" | grep -q '=='; then
            echo -e "${RED}✗ $line${NC}"
            echo -e "   Error: No version specified. Use exact pin (==)."
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        else
            # Has == but doesn't match the strict pattern (maybe extras, comments, etc.)
            echo -e "${YELLOW}⚠ $line${NC}"
            echo -e "   Warning: Unusual format. Verify this is correct."
        fi
    fi
done < "$REQUIREMENTS_FILE"

echo ""
if [[ $ISSUES_FOUND -eq 0 ]]; then
    echo -e "${GREEN}✓ All packages are exactly pinned. Requirements are valid.${NC}"
    exit 0
else
    echo -e "${RED}✗ Found $ISSUES_FOUND issue(s). All packages must use exact version pins (==).${NC}"
    exit 1
fi
