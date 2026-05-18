#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2025 ELABIT GmbH <mail@elabit.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Bakery plugin for robotmk-bridge-plugin.

Reads the Bakery rule configuration produced by the WATO ruleset and:
  1. Deploys ``robotmk_bridge_plugin.py`` (Python agent plugin) on Linux and Windows.
  2. Deploys platform wrappers: ``robotmk_bridge_plugin.sh`` (Linux/Solaris) and
     ``robotmk_bridge_plugin.ps1`` (Windows).
  3. Writes the JSON configuration file to the agent's config directory.

Config format written to the agent (``robotmk-bridge-plugin.json``):

.. code-block:: json

    {
        "plans": [
            {
                "plan_name": "my_junit_plan",
                "handler": "junit",
                "source_mode": "single_file",
                "path": "/path/to/result.xml",
                "metadata": {
                    "application": "My Application"
                }
            }
        ]
    }

The ``source_mode`` field controls how the agent plugin discovers result files:
- ``single_file``      – read exactly one file at the configured path.
- ``directory_all``    – read all files in the configured directory.
- ``directory_newest`` – read only the newest file in the configured directory.

Handler-specific parameters (e.g. ``accepted_risk_level`` for ZAP) are merged
into the ``metadata`` dict and forwarded to the handler's ``parse_results()`` call
by the agent plugin's signature-introspection logic.
"""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from cmk.base.cee.plugins.bakery.bakery_api.v1 import FileGenerator, OS, Plugin, PluginConfig, register


def _build_plan_config(plan_raw: Mapping[str, Any]) -> dict[str, Any]:
    """Translate one WATO plan entry into the agent config dict for that plan."""
    plan_name: str = plan_raw["plan_name"]
    application: str = plan_raw["application"]

    source_mode_key, source_path = plan_raw["source"]
    handler_key, handler_params_raw = plan_raw["handler"]

    metadata: dict[str, Any] = {"application": application}
    if isinstance(handler_params_raw, dict):
        metadata.update(handler_params_raw)

    return {
        "plan_name": plan_name,
        "handler": handler_key,
        "source_mode": source_mode_key,
        "path": source_path,
        "metadata": metadata,
    }


def get_robotmk_bridge_plugin_files(conf: Mapping[str, Any]) -> FileGenerator:
    """Generate agent artifacts for the robotmk-bridge-plugin bakery rule."""
    plans_raw = conf.get("plans", [])
    if not plans_raw:
        return

    plan_configs = [_build_plan_config(p) for p in plans_raw]
    config_content = json.dumps({"plans": plan_configs}, indent=2, ensure_ascii=False)
    config_lines = config_content.splitlines()

    for base_os in (OS.LINUX, OS.SOLARIS):
        # Deploy the main Python plugin
        yield Plugin(
            base_os=base_os,
            source=Path("robotmk_bridge_plugin.py"),
        )
        # Deploy the bash wrapper
        yield Plugin(
            base_os=base_os,
            source=Path("robotmk_bridge_plugin.sh"),
        )
        # Deploy the JSON config
        yield PluginConfig(
            base_os=base_os,
            lines=config_lines,
            target=Path("robotmk-bridge-plugin.json"),
            include_header=False,
        )

    # Windows: deploy Python plugin + PowerShell wrapper + config
    yield Plugin(
        base_os=OS.WINDOWS,
        source=Path("robotmk_bridge_plugin.py"),
    )
    yield Plugin(
        base_os=OS.WINDOWS,
        source=Path("robotmk_bridge_plugin.ps1"),
    )
    yield PluginConfig(
        base_os=OS.WINDOWS,
        lines=config_lines,
        target=Path("robotmk-bridge-plugin.json"),
        include_header=False,
    )


register.bakery_plugin(
    name="robotmk_bridge_plugin",
    files_function=get_robotmk_bridge_plugin_files,
)
