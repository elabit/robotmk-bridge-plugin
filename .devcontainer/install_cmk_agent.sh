#!/usr/bin/env bash
# https://docs.checkmk.com/latest/en/agent_linux_legacy.html#unencrypted
set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve agent package path from argument
# ---------------------------------------------------------------------------
readonly AGENT_REFS_DIR="/omd/sites/cmk/var/check_mk/agents/linux_deb/references"

case "${1:-host}" in
  vanilla)
    AGENT_DEB="${AGENT_REFS_DIR}/_VANILLA"
    ;;
  localhost|host)
    AGENT_DEB="${AGENT_REFS_DIR}/$(hostname)"
    ;;
  *)
    echo "Usage: $0 [vanilla|localhost|host]" >&2
    exit 1
    ;;
esac
readonly AGENT_DEB

if [[ ! -f "$AGENT_DEB" ]]; then
    echo "ERROR: Checkmk agent deb package not found: $AGENT_DEB" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------
echo "▹ Installing Checkmk agent from: $AGENT_DEB"
dpkg -i "$AGENT_DEB" 2>/dev/null

# ---------------------------------------------------------------------------
# Configure xinetd and optionally start the RobotMK scheduler
# ---------------------------------------------------------------------------
setup_agent() {
    local setup_script="$1"
    local robotmk_config="$2"
    local scheduler_bin="$3"

    echo "  - $setup_script deploy"
    bash "$setup_script" deploy

    echo "  - $setup_script trigger"
    bash "$setup_script" trigger

    if [[ -f "$robotmk_config" ]]; then
        echo "▹ robotmk.json found — starting RobotMK scheduler in the background..."
        if pkill -f "robotmk_scheduler" 2>/dev/null; then
            echo "  - killed existing robotmk_scheduler instance"
        fi
        "$scheduler_bin" "$robotmk_config" &
    fi
}

if [[ -d /opt/checkmk/agent/ ]]; then
    echo "▹ USER-agent detected"
    setup_agent \
        "/opt/checkmk/agent/default/package/scripts/super-server/1_xinetd/setup" \
        "/opt/checkmk/agent/default/package/config/robotmk.json" \
        "/opt/checkmk/agent/default/package/robotmk/robotmk_scheduler"
else
    echo "▹ ROOT-agent detected"
    setup_agent \
        "/var/lib/cmk-agent/scripts/super-server/1_xinetd/setup" \
        "/etc/check_mk/robotmk.json" \
        "/usr/lib/check_mk_agent/robotmk/robotmk_scheduler"
fi