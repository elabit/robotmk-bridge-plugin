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
from cmk_addons.plugins.vector.agent_based import vector

EXAMPLE_STRING_TABLE = [
    ['{"health":true,"version":"0.38.0 (x86_64-unknown-linux-gnu ea0ec6f 2024-05-07 14:34:39.794027186)","sources":2,"transforms":2,"sinks":1}'],
]
EXAMPLE_SECTION = {
    "health": True,
    "version": "0.38.0 (x86_64-unknown-linux-gnu ea0ec6f 2024-05-07 14:34:39.794027186)",
    "sources": 2,
    "transforms": 2,
    "sinks": 1,
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
    assert vector.parse_vector(string_table) == result


@pytest.mark.parametrize('section, result', [
    ({}, []),
    (None, []),
    (EXAMPLE_SECTION, [Service()]),
])
def test_discovery_vector_component(section, result):
    assert list(vector.discovery_vector(section)) == result


@pytest.mark.parametrize('section, result', [
    (
        {},
        [
            Result(state=State.CRIT, summary='Not Health'),
            Result(state=State.OK, notice='Version: unknown'),
        ]
    ),
    (
        {"healthy": False},
        [
            Result(state=State.CRIT, summary='Not Health'),
            Result(state=State.OK, notice='Version: unknown'),
        ]
    ),
    (
        {"healthy": False, "version": "mock"},
        [
            Result(state=State.CRIT, summary='Not Health'),
            Result(state=State.OK, notice='Version: mock'),
        ]
    ),
    (
        {"healthy": False, "version": "mock", "sources": 2, "transforms": 0, "sinks": 2},
        [
            Result(state=State.CRIT, summary='Not Health'),
            Result(state=State.OK, notice='Version: mock'),
            Metric('vector_source', 2.0, boundaries=(0.0, None)),
            Metric('vector_transform', 0.0, boundaries=(0.0, None)),
            Metric('vector_sink', 2.0, boundaries=(0.0, None)),
        ]
    ),
])
def test_check_vector(section, result):
    assert list(vector.check_vector(section)) == result
