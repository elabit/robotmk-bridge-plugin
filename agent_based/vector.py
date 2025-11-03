#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#
# jb_fls_licenses - JetBrains Floating Licenses check
#
# Copyright (C) 2020-2024  Marius Rieder <marius.rieder@durchmesser.ch>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import json
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    Metric,
    Result,
    Service,
    State,
)


def parse_vector(string_table):
    if string_table and string_table[0]:
        return json.loads("".join(string_table[0]))
    return {}


agent_section_vector = AgentSection(
    name='vector',
    parse_function=parse_vector,
)


def discovery_vector(section):
    if section:
        yield Service()


def check_vector(section):
    yield Result(
        state=State.OK if section.get('health', False) else State.CRIT,
        summary='Health' if section.get('health', False) else 'Not Health',
    )
    yield Result(state=State.OK, notice=f"Version: {section.get('version', 'unknown')}")

    if 'sources' in section:
        yield Metric("vector_source", section['sources'], boundaries=(0, None))
    if 'transforms' in section:
        yield Metric("vector_transform", section['transforms'], boundaries=(0, None))
    if 'sinks' in section:
        yield Metric("vector_sink", section['sinks'], boundaries=(0, None))


check_plugin_vector = CheckPlugin(
    name='vector',
    service_name='Vector',
    discovery_function=discovery_vector,
    check_function=check_vector,
)
