#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#
# Copyright (C) 2024  Marius Rieder <marius.rieder@durchmesser.ch>
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

from cmk.graphing.v1 import (
    graphs as g,
    metrics as m,
    perfometers as p,
)

metric_vector_source = m.Metric(
    name='vector_source',
    title=m.Title('Sources'),
    unit=m.Unit(m.DecimalNotation(""), m.StrictPrecision(0)),
    color=m.Color.BLUE,
)

metric_vector_transform = m.Metric(
    name='vector_transform',
    title=m.Title('Transforms'),
    unit=m.Unit(m.DecimalNotation(""), m.StrictPrecision(0)),
    color=m.Color.ORANGE,
)

metric_vector_sink = m.Metric(
    name='vector_sink',
    title=m.Title('Sinks'),
    unit=m.Unit(m.DecimalNotation(""), m.StrictPrecision(0)),
    color=m.Color.GREEN,
)

graph_vector = g.Graph(
    name='vector',
    title=g.Title('Vector'),
    compound_lines=[
        'vector_source',
        'vector_transform',
        'vector_sink',
    ],
)

perfometer_vector = p.Perfometer(
    name='vector',
    focus_range=p.FocusRange(p.Closed(0), p.Open(1)),
    segments=[
        'vector_source',
        'vector_transform',
        'vector_sink',
    ],
)
