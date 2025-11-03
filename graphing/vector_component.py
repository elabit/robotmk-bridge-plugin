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

metric_vector_recv_event = m.Metric(
    name='recv_event',
    title=m.Title('Events received'),
    unit=m.Unit(m.DecimalNotation(""), m.StrictPrecision(0)),
    color=m.Color.GREEN,
)

metric_vector_sent_event = m.Metric(
    name='sent_event',
    title=m.Title('Events sent'),
    unit=m.Unit(m.DecimalNotation(""), m.StrictPrecision(0)),
    color=m.Color.BLUE,
)

graph_vector_component_events = g.Bidirectional(
    name='vector_component_events',
    title=g.Title('Vector Events'),
    upper=g.Graph(
        name='vector_component_events_recv_event',
        title=g.Title('upper'),
        compound_lines=['recv_event'],
    ),
    lower=g.Graph(
        name='vector_component_events_sent_event',
        title=g.Title('upper'),
        compound_lines=['sent_event'],
    ),
)

perfometer_vector_component = p.Bidirectional(
    name='vector_component',
    left=p.Perfometer(
        name='vector_component_recv_event',
        focus_range=p.FocusRange(p.Closed(0), p.Open(100)),
        segments=['recv_event']
    ),
    right=p.Perfometer(
        name='vector_component_sent_event',
        focus_range=p.FocusRange(p.Closed(0), p.Open(100)),
        segments=['sent_event']
    ),
)
