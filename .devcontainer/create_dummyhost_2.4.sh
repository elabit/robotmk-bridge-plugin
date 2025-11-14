#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../project.env"


SECRETFILE=/opt/omd/sites/cmk/var/check_mk/web/automation/automation.secret

if [ ! -r $SECRETFILE ]; then 
    echo "ERROR: Secretfile $SECRETFILE not found or not readable."
    echo "Make sure the automation user has admin rights and the password is stored in clear text."
    echo "Exiting."
    exit 1
fi

CMK_HOST="localhost"
SITE_NAME="cmk"
HOST="$HOSTNAME"
PROTO="http"
PORT=5000
API_URL="$PROTO://$CMK_HOST:$PORT/$SITE_NAME/check_mk/api/1.0"

USERNAME="automation"
PASSWORD=$(cat $SECRETFILE)

CMK_ETC_DIR=/omd/sites/cmk/etc/check_mk
CMK_RULES_DIR=$WORKSPACE/.devcontainer/conf/checkmk

echo "Automation password: $PASSWORD"
echo "+ Creating a dummy host via API... "

curl \
  --request POST \
  --header "Authorization: Bearer $USERNAME $PASSWORD" \
  --header "Accept: application/json" \
  --header "Content-Type: application/json" \
  --data '{"attributes": {"ipaddress": "127.0.0.1"},"folder": "/","host_name": "'$HOST'"}' \
  "$API_URL/domain-types/host_config/collections/all"


echo "▹ WORKSPACE: $WORKSPACE"

if ! $(grep -q ADDEDBYSCRIPT $CMK_ETC_DIR/conf.d/wato/rules.mk); then
    echo "+ Adding rules to $CMK_ETC_DIR/conf.d/wato/rules.mk, replacing HOSTNAME with $HOST via envsubst ... "
    
    CFG=$(envsubst < $CMK_RULES_DIR/rules.mk.txt)

    echo "$CFG" >> $CMK_ETC_DIR/conf.d/wato/rules.mk  
else 
    echo
    echo "+ rules are already applied in $CMK_ETC_DIR/conf.d/wato/rules.mk ... "
fi


echo "+ Adding ignore rules to $CMK_ETC_DIR/final.mk ... "
cat $CMK_RULES_DIR/final.mk.txt > $CMK_ETC_DIR/final.mk

# cmk -R
