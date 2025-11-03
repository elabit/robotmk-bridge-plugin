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

import re
import json
from collections.abc import Mapping
from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    get_rate,
    get_value_store,
    GetRateError,
    render,
    Result,
    RuleSetType,
    Service,
    State,
)


def parse_vector_component(string_table):
    return {
        data.pop('componentId'): data
        for data in [
            json.loads(line[0])
            for line in string_table
        ]
    }


agent_section_vector_source = AgentSection(
    name='vector_source',
    parse_function=parse_vector_component,
)

agent_section_vector_transform = AgentSection(
    name='vector_transform',
    parse_function=parse_vector_component,
)

agent_section_vector_sink = AgentSection(
    name='vector_sink',
    parse_function=parse_vector_component,
)


def merge_params(params):
    param = dict(ignore=[])
    for p in params:
        if 'ignore' in p:
            param['ignore'] += p['ignore']
        if 'source' in p and 'source' not in param:
            param['source'] = p['source']
        if 'transform' in p and 'transform' not in param:
            param['transform'] = p['transform']
        if 'sink' in p and 'sink' not in param:
            param['sink'] = p['sink']
    return param


def discovery_vector_component(type, params, section):
    param = merge_params(params)
    if param.get(type, 'discover') == 'not_discover':
        return
    for comp in section:
        if any(
            ignore['component'] in [type, 'any'] and re.match(f"^{ignore['name']}", comp)
            for ignore in param['ignore']
        ):
            continue
        yield Service(item=comp)


def discovery_vector_source(params, section):
    yield from discovery_vector_component('source', params, section)


def discovery_vector_transform(params, section):
    yield from discovery_vector_component('transform', params, section)


def discovery_vector_sink(params, section):
    yield from discovery_vector_component('sink', params, section)


def check_vector_component(item, params, section):
    if item not in section:
        return

    comp = section[item]

    yield Result(state=State.OK, summary=f"Type: {comp['componentType']}")

    import time
    now = time.time()
    if 'receivedEventsTotal' in comp or 'recv_event_upper' in params or 'recv_event_lower' in params:
        try:
            value = get_rate(
                get_value_store(),
                f"vector_components.{item}.recv_event",
                now,
                comp.get('receivedEventsTotal', 0)
            )
        except GetRateError:
            value = 0
        yield from check_levels(value,
                                label='Events received',
                                render_func=lambda v: f"{v:.2f}/s",
                                levels_upper=params.get('recv_event_upper'),
                                levels_lower=params.get('recv_event_lower'),
                                metric_name='recv_event',
                                boundaries=(0, None))

    if 'sentEventsTotal' in comp or 'sent_event_upper' in params or 'sent_event_lower' in params:
        try:
            value = get_rate(
                get_value_store(),
                f"vector_components.{item}.sent_event",
                now,
                comp.get('sentEventsTotal', 0)
            )
        except GetRateError:
            value = 0
        yield from check_levels(value,
                                label='Events sent',
                                render_func=lambda v: f"{v:.2f}/s",
                                levels_upper=params.get('sent_event_upper'),
                                levels_lower=params.get('sent_event_lower'),
                                metric_name='sent_event',
                                boundaries=(0, None))

    if 'receivedBytesTotal' in comp or 'recv_byte_upper' in params or 'recv_byte_lower' in params:
        try:
            value = get_rate(
                get_value_store(),
                f"vector_components.{item}.recv_byte",
                now,
                comp.get('receivedBytesTotal', 0)
            )
        except GetRateError:
            value = 0
        yield from check_levels(value,
                                label='Bytes received',
                                render_func=render.networkbandwidth,
                                levels_upper=params.get('recv_byte_upper'),
                                levels_lower=params.get('recv_byte_lower'),
                                metric_name='recv_byte',
                                boundaries=(0, None))

    if 'sentBytesTotal' in comp or 'sent_byte_upper' in params or 'sent_byte_lower' in params:
        try:
            value = get_rate(
                get_value_store(),
                f"vector_components.{item}.sent_byte",
                now,
                comp.get('sentBytesTotal', 0)
            )
        except GetRateError:
            value = 0
        yield from check_levels(value,
                                label='Bytes sent',
                                render_func=render.networkbandwidth,
                                levels_upper=params.get('sent_byte_upper'),
                                levels_lower=params.get('sent_byte_lower'),
                                metric_name='sent_byte',
                                boundaries=(0, None))


def cluster_check_vector_component(
    item,
    params,
    section: Mapping[str, dict | None]
) -> CheckResult:
    section_combined = {}
    for member in section:
        if item not in section[member]:
            continue

        for key in section[member][item]:
            if key == 'componentType':
                section_combined['componentType'] = section[member][item]['componentType']
                continue
            section_combined[key] = section_combined.get(key, 0) + section[member][item].get(key, 0)

    if not section_combined:
        return
    yield from check_vector_component(item, params, {item: section_combined})


check_plugin_vector_source = CheckPlugin(
    name='vector_source',
    service_name='Vector Source %s',
    discovery_function=discovery_vector_source,
    discovery_ruleset_name='vector_component',
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters={},
    check_function=check_vector_component,
    check_ruleset_name='vector_source',
    check_default_parameters={},
    cluster_check_function=cluster_check_vector_component,
)

check_plugin_vector_transform = CheckPlugin(
    name='vector_transform',
    service_name='Vector Transform %s',
    discovery_function=discovery_vector_transform,
    discovery_ruleset_name='vector_component',
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters={},
    check_function=check_vector_component,
    check_ruleset_name='vector_transform',
    check_default_parameters={},
    cluster_check_function=cluster_check_vector_component,
)

check_plugin_vector_sink = CheckPlugin(
    name='vector_sink',
    service_name='Vector Sink %s',
    discovery_function=discovery_vector_sink,
    discovery_ruleset_name='vector_component',
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters={},
    check_function=check_vector_component,
    check_ruleset_name='vector_sink',
    check_default_parameters={},
    cluster_check_function=cluster_check_vector_component,
)
