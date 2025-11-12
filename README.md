# Robotmk-Bridge-Plugin

A Checkmk Check Plugin for [Robotmk](https://robotmk.org/) to bring results from **any test tool** into [Checkmk](https://checkmk.com) monitoring with the help of [Robotmk](https://robotmk.org).



![](img/architecture.png)



- Configurable entirely from Checkmk via the Bakery rule, defining the paths that supply test results.
- Uses Python handler modules to translate arbitrary result formats into Robot Framework XML.
- Builds on a dedicated Python package [robotframework-bridge](https://github.com/elabit/robotmk-bridge) for an exensible handler based conversion of results.
- Produces Robotmk JSON outputs similar to native Robot Framework runs, enabling seamless Checkmk Synthetic Monitoring integration for any test source.

## Why Robotmk-Bridge?

Until now, a mature integration of test results in Checkmk was limited exclusively to Robot Framework, as Robotmk was originally built for the integration of Robot Framework results (hence the name).

However, we have seen that many customers are envious of this integration but cannot change their test framework.

That is why ELABIT developed the bridge, to provide a kind of compatibility layer that allows any testing tool to be integrated.

## Development

For the best development experience use [VSCode](https://code.visualstudio.com/) with the [Remote Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension.  
This maps your workspace into a checkmk docker container giving you access to the python environment and libraries the installed extension has.

## Directories

The following directories in this repo are getting mapped into the Checkmk site.

- `agents`, `checkman`, `checks`, `doc`, `inventory`, `notifications`, `pnp-templates`, `web` are mapped into `local/share/check_mk/`
- `agent_based` is mapped to `local/lib/check_mk/base/plugins/agent_based`
- `nagios_plugins` is mapped to `local/lib/nagios/plugins`

## Continuous integration

### Local


`pytest` can be executed from the terminal or the test ui.

### Github Workflow

The provided Github Workflows run `pytest` and `flake8` in the same checkmk docker conatiner as vscode.
