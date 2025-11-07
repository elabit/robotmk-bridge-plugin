#!/bin/bash
# SPDX-FileCopyrightText: © 2022 ELABIT GmbH <mail@elabit.de>
# SPDX-License-Identifier: GPL-3.0-or-later
# This file is part of the Robotmk project (https://www.robotmk.org)

# Source CMK version detection utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/cmk_version.sh"
source "${SCRIPT_DIR}/../project.env"

if [ -z "$PROJECT_NAME" ]; then
    echo "ERROR: PROJECT_NAME is not set in project.env"
    exit 1  
fi

LINKTYPE=$1
# ARG1 must be either "cmkonly" or "full" => linkfiles.sh
if [ "$LINKTYPE" != "cmkonly" ] && [ "$LINKTYPE" != "full" ]; then
    echo "ERROR: Argument must be either 'common' or 'full'."
    exit 1
fi


echo "▹ WORKSPACE: $WORKSPACE"

# This step ties the workspace files with the Devcontainer. lsyncd is used to synchronize files. 
echo "▹ Linking the project files into the container (linkfiles.sh $LINKTYPE)..."
$WORKSPACE/.devcontainer/linkfiles.sh $LINKTYPE

# Tell bash to load aliases and functions
echo "▹ Loading aliases and functions..."
echo ". $HOME/.bash_aliases" >> $HOME/.bashrc

# Create the folder to source agent output for easy debugging.
# Sync is done by lsyncd in linkfiles.sh.
mkdir -p $OMD_ROOT/var/check_mk/agent_output
chown -R cmk:cmk $OMD_ROOT/var/check_mk/agent_output

echo "▹ Disabling the EC..."
sed -i '/mkeventd_enabled/d' $OMD_ROOT/etc/check_mk/conf.d/mkeventd.mk
echo "mkeventd_enabled = False" >> $OMD_ROOT/etc/check_mk/conf.d/mkeventd.mk
sed -i '/mkeventd_enabled/d' $OMD_ROOT/etc/check_mk/multisite.d/wato/global.mk
echo "mkeventd_enabled = False" >> $OMD_ROOT/etc/check_mk/multisite.d/wato/global.mk


echo "▹ Disabling the Liveproxyd..."
sed -i '/liveproxyd_enabled/d' $OMD_ROOT/etc/check_mk/multisite.d/mkeventd.mk
echo "liveproxyd_enabled = False" >> $OMD_ROOT/etc/check_mk/multisite.d/mkeventd.mk

#echo "▹ Enabling the Web API..."
#sed -i '/disable_web_api/d' $OMD_ROOT/etc/check_mk/multisite.d/wato/global.mk
#echo "disable_web_api = False" >> $OMD_ROOT/etc/check_mk/multisite.d/wato/global.mk

echo "▹ Installing Python modules for Robotmk... (Log file: /tmp/pip_install.log )"
pip3 install -r $WORKSPACE/requirements.txt 2>&1 > /tmp/pip_install.log

echo "▹ Starting OMD... "
omd restart



# If variable GITHUB_WORKSPACE does not exist, we are in a local execution.
# Perform additional steps for local devcontainer usage which require some user interaction.
if [ -z "${GITHUB_WORKSPACE-}" ]; then
    read -p "Start interactive devcontainer setup? (y/n) " -n 1 -r
    echo    # move to a new line
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping interactive devcontainer setup."
        exit 0
    fi

    echo "Preparing the dev setup (not in a Github Workflow):"

    echo "■ Creating a dummyhost"
    echo "Create NOW an automation user with administrator rights / store the secret in clear text. Then press ENTER to continue."
    read -p "Press ENTER to continue..."
    bash $WORKSPACE/.devcontainer/create_dummyhost_${CMK_VERSION_MM}.sh
    if [ $? -ne 0 ]; then
        echo "ERROR: Creating the dummyhost failed."
        exit 1
    fi
    echo "✅ Dummyhost created, WATO rules set."
    echo "■ Baking the agent"
    echo "Baking agent for $HOSTNAME ... "
    cmk -Avf $HOSTNAME
    echo "■ Installing the agent"
    echo "Open a root terminal and execute 'install_agent_localhost'."
    read -p "Press ENTER to continue..."

    echo "■ Trying to start the Robotmk Scheduler ..."
    if [ -z "$(pidof systemd)"] ; then
        echo "  ...no systemd detected. Robotmk Scheduler won't start automatically."
        echo "  Start the Scheduler manally as root with this command:"
        echo "    start_robotmk_scheduler"
        echo "  To stop the scheduler:"
        echo "    stop_robotmk_scheduler"
    fi

    read -p "Press ENTER to continue..."

    if [ -z "$(pgrep -f /usr/lib/check_mk_agent/robotmk/robotmk_scheduler)" ] ; then
        echo "  ERROR: Robotmk Scheduler did not start properly. Check /var/log/robotmk_scheduler_CURRENT.log for details."
        exit 1
    fi

    echo "Discovering ... "
    cmk -IIv 2>&1 > /dev/null
    echo "Reloading CMK config ... "
    cmk -R
    echo "■ Generating VS Code launch file ..."
    bash $WORKSPACE/.devcontainer/launch_gen.sh

fi
echo "✅ postCreateCommand.sh finished."