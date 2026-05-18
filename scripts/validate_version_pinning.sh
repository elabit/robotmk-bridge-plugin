#!/bin/bash
# Validate that all documentation references to robotframework-robotmk-bridge
# include the version number from requirements.txt

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Extract version from requirements.txt
REQUIREMENTS_FILE="requirements.txt"
if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
    echo -e "${RED}Error: $REQUIREMENTS_FILE not found${NC}"
    exit 1
fi

# Extract the exact version pin from requirements.txt
PACKAGE_LINE=$(grep "^robotframework-robotmk-bridge==" "$REQUIREMENTS_FILE" || true)
if [[ -z "$PACKAGE_LINE" ]]; then
    echo -e "${RED}Error: robotframework-robotmk-bridge not found or not pinned in $REQUIREMENTS_FILE${NC}"
    echo "Expected format: robotframework-robotmk-bridge==x.x.x"
    exit 1
fi

EXPECTED_VERSION=$(echo "$PACKAGE_LINE" | sed 's/robotframework-robotmk-bridge==\(.*\)/\1/')
echo -e "${GREEN}✓ Current version from $REQUIREMENTS_FILE: ${EXPECTED_VERSION}${NC}"

# Files to check
DOC_FILES=(
    "README.md"
    "docs/user-guide.md"
    "docs/development-guide.md"
    "docs/architecture.md"
)

# Track if any issues found
ISSUES_FOUND=0

echo ""
echo "Checking documentation files for version pinning..."
echo ""

for file in "${DOC_FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo -e "${YELLOW}⚠ Warning: $file not found, skipping${NC}"
        continue
    fi
    
    echo "Checking $file..."
    
    # Find lines with robotframework-robotmk-bridge
    MATCHES=$(grep -n "robotframework-robotmk-bridge" "$file" || true)
    
    if [[ -z "$MATCHES" ]]; then
        echo "  No references found"
        continue
    fi
    
    # Check each match
    while IFS= read -r line; do
        LINE_NUM=$(echo "$line" | cut -d: -f1)
        LINE_CONTENT=$(echo "$line" | cut -d: -f2-)
        
        # Skip lines that are:
        # - Links to GitHub repo (containing github.com/elabit/robotmk-bridge)
        # - Already properly pinned with ==x.x.x
        # - Comments about the package name itself (just references)
        if echo "$LINE_CONTENT" | grep -q "github.com/elabit/robotmk-bridge"; then
            continue
        fi
        
        if echo "$LINE_CONTENT" | grep -q "robotframework-robotmk-bridge==$EXPECTED_VERSION"; then
            echo -e "  ${GREEN}✓ Line $LINE_NUM: Correct version pinning${NC}"
        elif echo "$LINE_CONTENT" | grep -qE "robotframework-robotmk-bridge(==|>=|<=|>|<|~=)"; then
            # Has some version specifier but not the correct one
            FOUND_VERSION=$(echo "$LINE_CONTENT" | grep -oE "robotframework-robotmk-bridge[=<>~]+[0-9.]+" || true)
            echo -e "  ${RED}✗ Line $LINE_NUM: Incorrect version${NC}"
            echo -e "    Expected: robotframework-robotmk-bridge==${EXPECTED_VERSION}"
            echo -e "    Found: $FOUND_VERSION"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        elif echo "$LINE_CONTENT" | grep -qE "pip[3]?\s+install"; then
            # Installation commands MUST have version (pip show is OK without version)
            if ! echo "$LINE_CONTENT" | grep -q "robotframework-robotmk-bridge=="; then
                echo -e "  ${RED}✗ Line $LINE_NUM: Missing version in pip install command${NC}"
                echo -e "    Line: $LINE_CONTENT"
                echo -e "    Should be: robotframework-robotmk-bridge==${EXPECTED_VERSION}"
                ISSUES_FOUND=$((ISSUES_FOUND + 1))
            fi
        else
            # Just a mention/reference in prose - this is OK
            echo "  - Line $LINE_NUM: Reference only (OK)"
        fi
    done <<< "$MATCHES"
    
    echo ""
done

# Summary
echo "================================"
if [[ $ISSUES_FOUND -eq 0 ]]; then
    echo -e "${GREEN}✓ All documentation references are properly version-pinned!${NC}"
    exit 0
else
    echo -e "${RED}✗ Found $ISSUES_FOUND issue(s) with version pinning${NC}"
    echo ""
    echo "Action required:"
    echo "  Update all references to use: robotframework-robotmk-bridge==${EXPECTED_VERSION}"
    exit 1
fi
