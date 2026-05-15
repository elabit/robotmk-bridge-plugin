#!/bin/bash
# SPDX-FileCopyrightText: © 2022 ELABIT GmbH <mail@elabit.de>
# SPDX-License-Identifier: GPL-3.0-or-later

# This file is used to generate the devcontainer.json file. It is called from the project 
# root directory. It sets the container name to the project name and Checkmk version to
# ARG1 = Checkmk version, e.g. 2.1.0p11

# You can also place a devcontainer_local.json file in the same folder. It gets 
# applied on top of the generated devcontainer.json file. This allows you to
# customize the devcontainer.json further.

export VERSION=$1

DEVC_FILE=".devcontainer/devcontainer.json"
DEVC_LOCAL_FILE=".devcontainer/devcontainer_local.json"




function main() {
    SCRIPTDIR=$(folder_of $0)
    # project.env contains some generic useful variables
    source $SCRIPTDIR/../project.env

    # If version is unset, offer interactive selection from devcontainer_img_versions.env
    if [ -z "$VERSION" ]; then
        VERS_FILE="$SCRIPTDIR/devcontainer_img_versions.env"
        if [ ! -f "$VERS_FILE" ]; then
            echo "No cmk version (arg1) specified and $VERS_FILE not found."
            exit 1
        fi
        # shellcheck disable=SC1090
        source "$VERS_FILE"
        if [ -z "$CMKVERSIONS" ]; then
            echo "No CMKVERSIONS defined in $VERS_FILE."
            exit 1
        fi
        echo "No cmk version (arg1) specified. Select a version:"
        versions=()
        while IFS= read -r line; do
            [ -n "$line" ] && versions+=("$line")
        done < <(printf '%s\n' "$CMKVERSIONS")
        select v in "${versions[@]}"; do
            if [ -n "$v" ]; then
                VERSION="$v"
                export VERSION
                echo "Selected version: $VERSION"
                break
            else
                echo "Invalid selection. Try again."
            fi
        done
    fi
    export CMK_VERSION_MM=$(echo "$VERSION" | cut -d. -f1-2)
    export CONTAINER_NAME=${PROJECT_NAME}-devc-cmk${CMK_VERSION_MM}


    ########################
    echo "+ Generating CMK devcontainer file ..."
    # Ref LeP3qq
    DEVC_TPL_FILE=".devcontainer/devcontainer_tpl.json"
    # Always use absolute paths for temp and target files to avoid confusion
    TMP_FILE="$SCRIPTDIR/devcontainer.json.tmp"
    TARGET_FILE="$SCRIPTDIR/devcontainer.json"

    envsubst < "$DEVC_TPL_FILE" > "$TMP_FILE"
    # devcontainer.json contains a VS Code Variable ${containerWorkspaceFolder}, which would also 
    # be processed by envsubst. To avoid this, the template files contain ###{containerWorkspaceFolder}.
    # The three hashes are replaced with $ _after_ envsusbt has done its work. 
    # Mac-only sed... 
    sed -i 's/###/$/' "$TMP_FILE"

    # If a local devcontainer file exists, merge it, else just move the tmp file
    if [ -f "$DEVC_LOCAL_FILE" ]; then
        echo "+ Merging local devcontainer file for project $PROJECT_NAME ..."
        jq -s '.[0] * .[1]' "$TMP_FILE" "$DEVC_LOCAL_FILE" > "$TARGET_FILE"
        rm "$TMP_FILE"
    else
        mv "$TMP_FILE" "$TARGET_FILE"
    fi
    
    # Merge main requirements into the devcontainer requirements file,
    # keeping everything up to the line that starts with "# --" and
    # replacing everything after that line with the main requirements.
    MAIN_REQ="$SCRIPTDIR/../requirements.txt"
    DEV_REQ="$SCRIPTDIR/requirements.txt"

    if [ ! -f "$MAIN_REQ" ]; then
        echo "Warning: main requirements file not found: $MAIN_REQ" >&2
    else
        TMPFILE="$(mktemp)"
        # If DEV_REQ contains the marker line, keep up to and including it,
        # otherwise keep the whole file and append a marker.
        if grep -q '^# --' "$DEV_REQ"; then
            sed -n '1,/^# --/p' "$DEV_REQ" > "$TMPFILE"
        else
            cat "$DEV_REQ" > "$TMPFILE"
            printf '\n# --\n' >> "$TMPFILE"
        fi

        echo "Merging main requirements from $MAIN_REQ into $DEV_REQ (keeping custom entries above the marker line)."
        # Append a blank line and the contents of the main requirements file
        printf '\n' >> "$TMPFILE"
        cat "$MAIN_REQ" >> "$TMPFILE"

        mv "$TMPFILE" "$DEV_REQ"
    fi

}


function folder_of() {
  DIR="${1%/*}"
  (cd "$DIR" && echo "$(pwd -P)")
}

main $@