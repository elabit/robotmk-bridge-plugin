#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#
# jb_fls_licenses - JetBrains Floatingcheck
#
# Copyright (C) 2020  Marius Rieder <marius.rieder@durchmesser.ch>
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

import pytest  # type: ignore[import]
from cmk.agent_based.v2 import (
    Metric,
    Result,
    Service,
    State,
)
from cmk_addons.plugins.vector.agent_based import vector_component

EXAMPLE_STRING_TABLE = [
    ['{"componentId":"dhcp_log","componentType":"file","sentEventsTotal":0}'],
    ['{"componentId":"nps_log","componentType":"file","receivedBytesTotal":2967,"receivedEventsTotal":2,"sentEventsTotal":2}'],
    ['{"componentId":"parse_nps_log","componentType":"remap","receivedEventsTotal":2,"sentEventsTotal":2}'],
    ['{"componentId":"parse_dhcp_log","componentType":"remap","receivedEventsTotal":0,"sentEventsTotal":0}'],
    ['{"componentId":"print","componentType":"console","receivedEventsTotal":2,"sentEventsTotal":2,"sentBytesTotal":5007}'],
]
EXAMPLE_SECTION = {
    "dhcp_log": {"componentType": "file", "sentEventsTotal": 0},
    "nps_log": {"componentType": "file", "receivedBytesTotal": 2967, "receivedEventsTotal": 2, "sentEventsTotal": 2},
    "parse_nps_log": {"componentType": "remap", "receivedEventsTotal": 2, "sentEventsTotal": 2},
    "parse_dhcp_log": {"componentType": "remap", "receivedEventsTotal": 0, "sentEventsTotal": 0},
    "print": {"componentType": "console", "receivedEventsTotal": 2, "sentEventsTotal": 2, "sentBytesTotal": 5007},
}


@pytest.mark.parametrize('string_table, result', [
    (
        [], {}
    ),
    (
        EXAMPLE_STRING_TABLE, EXAMPLE_SECTION
    ),
])
def test_parse_jb_fls_licenses(string_table, result):
    assert vector_component.parse_vector_component(string_table) == result


@pytest.mark.parametrize('section, params, result', [
    ({}, {}, []),
    (
        EXAMPLE_SECTION, [{}],
        [
            Service(item='dhcp_log'),
            Service(item='nps_log'),
            Service(item='parse_nps_log'),
            Service(item='parse_dhcp_log'),
            Service(item='print'),
        ]
    ),
    (
        EXAMPLE_SECTION, [{'source': 'not_discover'}],
        []
    ),
    (
        EXAMPLE_SECTION, [{'source': 'not_discover'}, {'source': 'discover'}],
        []
    ),
    (
        EXAMPLE_SECTION, [{'ignore': [{'component': 'sink', 'name': '.*'}]}],
        [
            Service(item='dhcp_log'),
            Service(item='nps_log'),
            Service(item='parse_nps_log'),
            Service(item='parse_dhcp_log'),
            Service(item='print'),
        ]
    ),
    (
        EXAMPLE_SECTION, [{'ignore': [{'component': 'source', 'name': '.*'}]}],
        []
    ),
    (
        EXAMPLE_SECTION, [{'ignore': [{'component': 'any', 'name': '.*'}]}],
        []
    ),
    (
        EXAMPLE_SECTION, [{'ignore': [{'component': 'source', 'name': '.*nps'}]}],
        [
            Service(item='dhcp_log'),
            Service(item='parse_dhcp_log'),
            Service(item='print'),
        ]
    ),
    (
        EXAMPLE_SECTION, [{'ignore': [{'component': 'source', 'name': 'dhcp'}]}],
        [
            Service(item='nps_log'),
            Service(item='parse_nps_log'),
            Service(item='parse_dhcp_log'),
            Service(item='print'),
        ]
    ),
])
def test_discovery_vector_component(section, params, result):
    assert list(vector_component.discovery_vector_source(params, section)) == result


JB_FLS_LICENSES_SECTION = {
    'All Products Pack Toolbox': (42, 21),
    'CLion Toolbox': (23, 23)
}


@pytest.mark.parametrize('item, params, result', [
    (
        'Foo', {},
        []
    ),
    (
        'dhcp_log', {},
        [
            Result(state=State.OK, summary='Type: file'),
            Result(state=State.OK, summary='Events sent: 0.00/s'),
            Metric('sent_event', 0.0, boundaries=(0.0, None)),
        ]
    ),
    (
        'nps_log', {},
        [
            Result(state=State.OK, summary='Type: file'),
            Result(state=State.OK, summary='Events received: 2.00/s'),
            Metric('recv_event', 2.0, boundaries=(0.0, None)),
            Result(state=State.OK, summary='Events sent: 2.00/s'),
            Metric('sent_event', 2.0, boundaries=(0.0, None)),
            Result(state=State.OK, summary='Bytes received: 23.7 kBit/s'),
            Metric('recv_byte', 2967.0, boundaries=(0.0, None)),
        ]
    ),
    (
        'parse_nps_log', {},
        [
            Result(state=State.OK, summary='Type: remap'),
            Result(state=State.OK, summary='Events received: 2.00/s'),
            Metric('recv_event', 2.0, boundaries=(0.0, None)),
            Result(state=State.OK, summary='Events sent: 2.00/s'),
            Metric('sent_event', 2.0, boundaries=(0.0, None)),
        ]
    ),
    (
        'print', {},
        [
            Result(state=State.OK, summary='Type: console'),
            Result(state=State.OK, summary='Events received: 2.00/s'),
            Metric('recv_event', 2.0, boundaries=(0.0, None)),
            Result(state=State.OK, summary='Events sent: 2.00/s'),
            Metric('sent_event', 2.0, boundaries=(0.0, None)),
            Result(state=State.OK, summary='Bytes sent: 40.1 kBit/s'),
            Metric('sent_byte', 5007.0, boundaries=(0.0, None)),
        ]
    ),
    (
        'dhcp_log', {'recv_event_upper': ('no_levels', None)},
        [
            Result(state=State.OK, summary='Type: file'),
            Result(state=State.OK, summary='Events received: 0.00/s'),
            Metric('recv_event', 0.0, boundaries=(0.0, None)),
            Result(state=State.OK, summary='Events sent: 0.00/s'),
            Metric('sent_event', 0.0, boundaries=(0.0, None)),
        ]
    ),
    (
        'nps_log',
        {
            'recv_event_lower': ('fixed', (5.0, 1.0)),
            'sent_event_lower': ('fixed', (5.0, 1.0)),
            'recv_byte_lower': ('fixed', (4096, 1024)),
        },
        [
            Result(state=State.OK, summary='Type: file'),
            Result(state=State.WARN, summary='Events received: 2.00/s (warn/crit below 5.00/s/1.00/s)'),
            Metric('recv_event', 2.0, boundaries=(0.0, None)),
            Result(state=State.WARN, summary='Events sent: 2.00/s (warn/crit below 5.00/s/1.00/s)'),
            Metric('sent_event', 2.0, boundaries=(0.0, None)),
            Result(state=State.WARN, summary='Bytes received: 23.7 kBit/s (warn/crit below 32.8 kBit/s/8.19 kBit/s)'),
            Metric('recv_byte', 2967.0, boundaries=(0.0, None)),
        ]
    ),
    (
        'nps_log',
        {
            'recv_event_lower': ('fixed', (5.0, 3.0)),
            'sent_event_lower': ('fixed', (5.0, 3.0)),
            'recv_byte_lower': ('fixed', (4096, 3072)),
        },
        [
            Result(state=State.OK, summary='Type: file'),
            Result(state=State.CRIT, summary='Events received: 2.00/s (warn/crit below 5.00/s/3.00/s)'),
            Metric('recv_event', 2.0, boundaries=(0.0, None)),
            Result(state=State.CRIT, summary='Events sent: 2.00/s (warn/crit below 5.00/s/3.00/s)'),
            Metric('sent_event', 2.0, boundaries=(0.0, None)),
            Result(state=State.CRIT, summary='Bytes received: 23.7 kBit/s (warn/crit below 32.8 kBit/s/24.6 kBit/s)'),
            Metric('recv_byte', 2967.0, boundaries=(0.0, None)),
        ]
    ),
    (
        'nps_log',
        {
            'recv_event_upper': ('fixed', (1.0, 3.0)),
            'sent_event_upper': ('fixed', (1.0, 3.0)),
            'recv_byte_upper': ('fixed', (1024, 4096)),
        },
        [
            Result(state=State.OK, summary='Type: file'),
            Result(state=State.WARN, summary='Events received: 2.00/s (warn/crit at 1.00/s/3.00/s)'),
            Metric('recv_event', 2.0, levels=(1.0, 3.0), boundaries=(0.0, None)),
            Result(state=State.WARN, summary='Events sent: 2.00/s (warn/crit at 1.00/s/3.00/s)'),
            Metric('sent_event', 2.0, levels=(1.0, 3.0), boundaries=(0.0, None)),
            Result(state=State.WARN, summary='Bytes received: 23.7 kBit/s (warn/crit at 8.19 kBit/s/32.8 kBit/s)'),
            Metric('recv_byte', 2967.0, levels=(1024.0, 4096.0), boundaries=(0.0, None)),
        ]
    ),
    (
        'nps_log',
        {
            'recv_event_upper': ('fixed', (1.0, 1.5)),
            'sent_event_upper': ('fixed', (1.0, 1.5)),
            'recv_byte_upper': ('fixed', (1024, 2048)),
        },
        [
            Result(state=State.OK, summary='Type: file'),
            Result(state=State.CRIT, summary='Events received: 2.00/s (warn/crit at 1.00/s/1.50/s)'),
            Metric('recv_event', 2.0, levels=(1.0, 1.5), boundaries=(0.0, None)),
            Result(state=State.CRIT, summary='Events sent: 2.00/s (warn/crit at 1.00/s/1.50/s)'),
            Metric('sent_event', 2.0, levels=(1.0, 1.5), boundaries=(0.0, None)),
            Result(state=State.CRIT, summary='Bytes received: 23.7 kBit/s (warn/crit at 8.19 kBit/s/16.4 kBit/s)'),
            Metric('recv_byte', 2967.0, levels=(1024.0, 2048.0), boundaries=(0.0, None)),
        ]
    ),
])
def test_check_vector_component(monkeypatch, freezer, item, params, result):
    freezer.move_to('2024-06-02 10:43')
    store = {}
    from cmk.agent_based.v2 import get_rate, GetRateError
    import time
    now = time.time() - 1
    for metric_name in ('recv_byte', 'recv_event', 'sent_event', 'sent_byte'):
        try:
            get_rate(store, f"vector_components.{item}.{metric_name}", now, 0)
        except GetRateError:
            pass

    monkeypatch.setattr(vector_component, 'get_value_store', lambda: store)
    assert list(vector_component.check_vector_component(item, params, EXAMPLE_SECTION)) == result


@pytest.mark.parametrize('item, params, result', [
    (
        'Foo', {},
        []
    ),
    (
        'nps_log',
        {},
        [
            Result(state=State.OK, summary='Type: file'),
            Result(state=State.OK, summary='Events received: 4.00/s'),
            Metric('recv_event', 4.0, boundaries=(0.0, None)),
            Result(state=State.OK, summary='Events sent: 4.00/s'),
            Metric('sent_event', 4.0, boundaries=(0.0, None)),
            Result(state=State.OK, summary='Bytes received: 47.5 kBit/s'),
            Metric('recv_byte', 5934.0, boundaries=(0.0, None)),
        ]
    ),
])
def test_cluster_check_vector_component(monkeypatch, freezer, item, params, result):
    freezer.move_to('2024-06-02 10:43')
    store = {}
    from cmk.agent_based.v2 import get_rate, GetRateError
    import time
    now = time.time() - 1
    for metric_name in ('recv_byte', 'recv_event', 'sent_event', 'sent_byte'):
        try:
            get_rate(store, f"vector_components.{item}.{metric_name}", now, 0)
        except GetRateError:
            pass

    monkeypatch.setattr(vector_component, 'get_value_store', lambda: store)
    assert list(vector_component.cluster_check_vector_component(item, params, {'node1': EXAMPLE_SECTION, 'node2': EXAMPLE_SECTION})) == result
