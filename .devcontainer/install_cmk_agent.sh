#!/bin/bash

# https://docs.checkmk.com/latest/en/agent_linux_legacy.html#unencrypted

case "${1:-host}" in
  vanilla)
    AGENT_DEB="/omd/sites/cmk/var/check_mk/agents/linux_deb/references/_VANILLA"
    ;;
  localhost|host)
    AGENT_DEB="/omd/sites/cmk/var/check_mk/agents/linux_deb/references/localhost"
    ;;
  *)
    echo "Usage: $0 [vanilla|localhost|host]" >&2
    exit 1
    ;;
esac

echo "▹ Installing the Checkmk agent..."

dpkg -i "$AGENT_DEB" 2> /dev/null

if [ -d /opt/checkmk/agent/ ]; then
    echo "USER-Agent detected: running "
    echo "  - /opt/checkmk/agent/default/package/scripts/super-server/1_xinetd/setup deploy"
    echo "  - /opt/checkmk/agent/default/package/scripts/super-server/1_xinetd/setup trigger"
    SETUP=/opt/checkmk/agent/default/package/scripts/super-server/1_xinetd/setup
    bash "$SETUP" deploy
    bash "$SETUP" trigger
    if [[ -f /opt/checkmk/agent/default/package/config/robotmk.json ]]; then
      echo "▹ robotmk.json found — starting RobotMK scheduler in the background..."
      pkill -f "robotmk_scheduler" 2>/dev/null && echo "  - killed existing robotmk_scheduler instance"
      /opt/checkmk/agent/default/package/robotmk/robotmk_scheduler /opt/checkmk/agent/default/package/config/robotmk.json &
    fi
else
    echo "ROOT-Agent detected: running "
    echo "  - /var/lib/cmk-agent/scripts/super-server/1_xinetd/setup deploy"
    echo "  - /var/lib/cmk-agent/scripts/super-server/1_xinetd/setup trigger"
    SETUP=/var/lib/cmk-agent/scripts/super-server/1_xinetd/setup
    bash "$SETUP" deploy
    bash "$SETUP" trigger
    if [[ -f /etc/check_mk/robotmk.json ]]; then
      echo "▹ robotmk.json found — starting RobotMK scheduler in the background..."
      pkill -f "robotmk_scheduler" 2>/dev/null && echo "  - killed existing robotmk_scheduler instance"
      /usr/lib/check_mk_agent/robotmk/robotmk_scheduler /etc/check_mk/robotmk.json &
    fi
fi