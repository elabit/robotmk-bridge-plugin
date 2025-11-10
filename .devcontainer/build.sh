#!/bin/bash

#set -Eeuo pipefail

main() {
	if [[ $# -ne 1 ]]; then
		usage
		exit 1
	fi

	local pkg_version=$1

	ensure_workspace	
	load_site_profile
    load_project_name
	load_cmk_version_util

	OMD_VER=$(omd version | awk '{print $NF}')
	export OMD_VER

	prepare_git
	generate_package_file "$pkg_version" "$CMK_VERSION_MM"
	build_mkp "$pkg_version" "$CMK_VERSION_MM"
	set_github_outputs
	log "END OF build.sh"
}

err() {
	printf 'ERROR: %s\n' "$*" >&2
}

log() {
	printf '%s\n' "$*"
}

usage() {
	err "Usage: $0 <PKG_VERSION>"
}

trap 'err "Unexpected error at line $LINENO"; exit 1' ERR

PROJECT_NAME=""
PACKAGE_FILE=""
PKG_PATH=""
OMD_VER=""

ensure_workspace() {
	if [[ -n "${WORKSPACE:-}" ]]; then
		return
	fi

	if [[ -n "${GITHUB_WORKSPACE:-}" ]]; then
		WORKSPACE="$GITHUB_WORKSPACE"
		export WORKSPACE
		return
	fi

	err "WORKSPACE environment variable not set and GITHUB_WORKSPACE not available."
	exit 1
}

report_workspace() {
	log "Workspace folder: $WORKSPACE"
	ls -la "$WORKSPACE"
}

load_site_profile() {
	local profile_path="/omd/sites/cmk/.profile"
	if [[ ! -f "$profile_path" ]]; then
		err "Site profile not found at $profile_path."
		exit 1
	fi

	log "Loading site profile $profile_path"
	set -a
	# shellcheck disable=SC1090
	source "$profile_path" || true
	set +a

	if [[ -z "${OMD_SITE:-}" ]]; then
		err "OMD_SITE variable not set after sourcing profile."
		exit 1
	fi
}

load_cmk_version_util() {
	# shellcheck disable=SC1090
	source "${WORKSPACE}/.devcontainer/cmk_version.sh"
	if [[ -z "${CMK_VERSION_MM:-}" ]]; then
		err "CMK_VERSION_MM not exported by cmk_version.sh"
		exit 1
	fi
    echo "  - CMK_VERSION_MM=${CMK_VERSION_MM}"
}


load_project_name() {
    # project.env contains some generic useful variables
    set -a
    source $WORKSPACE/project.env
    set +a
    echo "  - PROJECT_NAME=${PROJECT_NAME}"
}

prepare_git() {
	git config --global --add safe.directory "$WORKSPACE"
}

generate_package_file() {
	local pkg_version=$1
	local cmk_mm=$2
	local template

	template="$WORKSPACE/pkginfo/cmk${cmk_mm}.json"
	PACKAGE_FILE="$OMD_ROOT/var/check_mk/packages/${PROJECT_NAME}"

	if [[ ! -f "$template" ]]; then
		err "Template $template not found."
		exit 1
	fi

	log "  - Package template: $template"
	jq \
		--arg version "$pkg_version" \
		--arg version_packaged "$OMD_VER" \
		--arg version_min_required "${cmk_mm}.0p1" \
		--arg version_usable_until "${cmk_mm}.200" \
		'
		.version = $version
		| .["version.packaged"] = $version_packaged
		| .["version.min_required"] = $version_min_required
		| .["version.usable_until"] = $version_usable_until
		' \
		"$template" >"$PACKAGE_FILE"

	log "  - Package file: $PACKAGE_FILE"
}

latest_mkp() {
	local pkgdir=$1
	local entries

	mapfile -t entries < <(find "$pkgdir" -maxdepth 1 -type f -name '*.mkp' -printf '%T@ %p\n' | sort -n)
	if [[ ${#entries[@]} -eq 0 ]]; then
		err "No MKP files found in $pkgdir"
		exit 1
	fi

	printf '%s' "${entries[-1]##* }"
}

build_mkp() {
	local pkg_version=$1
	local cmk_mm=$2
	local pkgdir pkg_dest latest

	pkgdir="$OMD_ROOT/var/check_mk/packages_local"
	pkg_dest="$WORKSPACE/build"

	log "Building MKP ${PROJECT_NAME} v${pkg_version} for CMK ${cmk_mm}"
	mkp -v package "$PACKAGE_FILE"

	latest=$(latest_mkp "$pkgdir")
	mkdir -p "$pkg_dest"
	PKG_PATH="$pkg_dest/${PROJECT_NAME}.${pkg_version}-cmk${cmk_mm}.mkp"
	mv "$latest" "$PKG_PATH"
	log "  - PKG_PATH: $PKG_PATH"
}

set_github_outputs() {
	if [[ -n "${GITHUB_WORKSPACE:-}" && -n "${GITHUB_OUTPUT:-}" ]]; then
		log "Publishing GitHub Actions outputs"
		printf 'pkgfile=%s\n' "$PKG_PATH" >>"$GITHUB_OUTPUT"
		printf 'artifactname=%s\n' "$(basename "$PKG_PATH")" >>"$GITHUB_OUTPUT"
	else
		log "No GitHub Actions environment detected"
	fi
}

folder_of() {
  DIR="${1%/*}"
  (cd "$DIR" && echo "$(pwd -P)")
}


main "$@"

