#!/bin/bash

# SPDX-FileCopyrightText: © 2022 ELABIT GmbH <mail@elabit.de>
# SPDX-License-Identifier: GPL-3.0-or-later
# This file is part of the Robotmk project (https://www.robotmk.org)

# This script installs the Checkmk agent package using dpkg,
# ignoring systemd and other errors that may occur in containers.

# Don't exit on errors - we want to continue even if some steps fail
set +e

# Check if user is root
if [ "$(id -u)" != "0" ]; then
    echo "This script must be run as root" 1>&2
    exit 1
fi

echo "==================================================================="
echo "  Checkmk Agent Installation (dpkg, ignore systemd errors)"
echo "==================================================================="
echo ""

HOSTNAME=$(hostname)
PKG_DIR="/omd/sites/cmk/var/check_mk/agents/linux_deb"

# Function to find the agent package for this host
find_package() {
    local pkg=""
    
    # Try to find package by hostname reference
    if [ -L "$PKG_DIR/references/$HOSTNAME" ]; then
        pkg=$(readlink -f "$PKG_DIR/references/$HOSTNAME")
        echo "▹ Found package via hostname reference: $HOSTNAME"
    elif [ -f "$PKG_DIR/localhost" ]; then
        pkg="$PKG_DIR/localhost"
        echo "▹ Using localhost package"
    else
        # Find most recent package in packages directory
        pkg=$(find "$PKG_DIR/packages" -type f -not -name "*.conf" 2>/dev/null | sort -r | head -1)
        if [ -n "$pkg" ]; then
            echo "▹ Using most recent package: $(basename "$pkg")"
        fi
    fi
    
    if [ -z "$pkg" ] || [ ! -f "$pkg" ]; then
        echo "ERROR: No agent package found"
        echo "Searched in:"
        echo "  - $PKG_DIR/references/$HOSTNAME"
        echo "  - $PKG_DIR/localhost"
        echo "  - $PKG_DIR/packages/"
        echo ""
        echo "Available references:"
        ls -lh "$PKG_DIR/references/" 2>/dev/null || echo "  Directory not found"
        exit 1
    fi
    
    echo "$pkg"
}

# Find package
PACKAGE=$(find_package)
echo "▹ Selected package: $PACKAGE"
echo ""

# Install package with dpkg, ignoring errors
echo "▹ Installing package with dpkg (ignoring errors)..."
echo ""

# Install and capture output but continue on failure
dpkg -i "$PACKAGE" 2>&1 | while IFS= read -r line; do
    # Skip/suppress common systemd-related errors
    if echo "$line" | grep -qiE "(systemctl|systemd|Failed to connect to bus|System has not been booted with systemd)"; then
        echo "  ⚠ Systemd: $line"
    elif echo "$line" | grep -qE "(Selecting previously unselected|Unpacking|Setting up|Processing triggers)"; then
        echo "  ✓ $line"
    elif echo "$line" | grep -qiE "(error|fail|warn)"; then
        echo "  ⚠ Warning: $line"
    else
        echo "  $line"
    fi
done

# Always return success from dpkg installation - we don't care about systemd errors
echo ""
echo "✓ Package installation completed (systemd errors ignored)"
echo ""

# Ensure essential directories exist
echo "▹ Ensuring directory structure..."
mkdir -p /var/lib/check_mk_agent/robotmk/scheduler/results/plans
chmod 755 /var/lib/check_mk_agent/robotmk/scheduler/results/plans 2>/dev/null || true
echo "  ✓ Created /var/lib/check_mk_agent/robotmk/scheduler/results/plans"

# Ensure agent is executable
if [ -f /usr/bin/check_mk_agent ]; then
    chmod 755 /usr/bin/check_mk_agent 2>/dev/null || true
    echo "  ✓ Agent binary is executable"
fi

# Try to start/restart xinetd if available (for agent communication)
echo ""
echo "▹ Configuring agent communication..."
if command -v xinetd >/dev/null 2>&1; then
    # Kill existing xinetd
    pkill xinetd 2>/dev/null || true
    sleep 1
    # Start xinetd in background
    nohup xinetd >/dev/null 2>&1 &
    echo "  ✓ Started xinetd (agent listens on port 6556)"
else
    echo "  ℹ xinetd not available - agent accessible via direct execution only"
fi

# Check for robotmk configuration
echo ""
if [ -f /etc/check_mk/robotmk.json ]; then
    echo "✓ Robotmk configuration found: /etc/check_mk/robotmk.json"
    
    # Try to start robotmk scheduler if available (but don't fail if it doesn't work)
    if [ -f /usr/lib/check_mk_agent/robotmk/robotmk_scheduler ]; then
        echo "  ℹ Robotmk scheduler is available but not auto-started"
        echo "  ℹ Start manually if needed: /usr/lib/check_mk_agent/robotmk/robotmk_scheduler --config /etc/check_mk/robotmk.json"
    fi
else
    echo "ℹ No robotmk.json found (not required for basic agent operation)"
fi

# Check for bridge plugin
if [ -f /usr/lib/check_mk_agent/plugins/robotmk_bridge_plugin.py ]; then
    echo "✓ Robotmk Bridge Plugin installed"
    if [ -f /etc/check_mk/robotmk_bridge_plugin.json ]; then
        echo "  ✓ Bridge plugin configuration found"
    else
        echo "  ⚠ No bridge plugin configuration found at /etc/check_mk/robotmk_bridge_plugin.json"
    fi
fi

echo ""
echo "==================================================================="
echo "✓ Installation Complete"
echo "==================================================================="
echo ""

# Test agent
echo "▹ Testing agent output..."
if /usr/bin/check_mk_agent 2>/dev/null | head -3 | grep -q "<<<check_mk>>>"; then
    echo "✓ Agent is working correctly"
    echo ""
    echo "View full agent output:"
    echo "  check_mk_agent | less"
    echo ""
    if [ -f /usr/lib/check_mk_agent/plugins/robotmk_bridge_plugin.py ]; then
        echo "View bridge plugin section:"
        echo "  check_mk_agent | grep -A20 '<<<robotmk_bridge>>>'"
    fi
else
    echo "⚠ Agent test failed or produced unexpected output"
    echo "  Try running: check_mk_agent"
fi

echo ""   
