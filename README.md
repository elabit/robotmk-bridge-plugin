# Checkmk extension for [Robotmk](https://robotmk.org/)

<!-- ![build](https://github.com/jiuka/checkmk_vector/workflows/build/badge.svg)
![flake8](https://github.com/jiuka/checkmk_vector/workflows/Lint/badge.svg)
![pytest](https://github.com/jiuka/checkmk_vector/workflows/pytest/badge.svg) -->

## About

Robotmk-Bridge is an agent plugin designed as a universal interface between any testing tool, Robotmk, and ultimately your Checkmk monitoring system.

It can be configured completely from Checkmk (Bakery rule) by setting paths from where the plugin should read test results.

Custom handlers (Python modules) take care of converting test results from arbitrary formats into the Robot Framework XML format.

The handler framework is based on the [robotframework-oxygen](https://github.com/eficode/robotframework-oxygen) library - currently used in this early POC phase. Later there will be a separate, forked package called [robotframework-bridge](https://github.com/elabit/robotmk-bridge).

For Robotmk, the result looks exactly as if the tests were executed by Robot Framework itself — enabling seamless integration of any test source into Checkmk Synthetic Monitoring.

## Development

For the best development experience use [VSCode](https://code.visualstudio.com/) with the [Remote Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension.  
This maps your workspace into a checkmk docker container giving you access to the python environment and libraries the installed extension has.

## Directories

The following directories in this repo are getting mapped into the Checkmk site.

* `agents`, `checkman`, `checks`, `doc`, `inventory`, `notifications`, `pnp-templates`, `web` are mapped into `local/share/check_mk/`
* `agent_based` is mapped to `local/lib/check_mk/base/plugins/agent_based`
* `nagios_plugins` is mapped to `local/lib/nagios/plugins`

## Continuous integration

### Local


`pytest` can be executed from the terminal or the test ui.

### Github Workflow

The provided Github Workflows run `pytest` and `flake8` in the same checkmk docker conatiner as vscode.
