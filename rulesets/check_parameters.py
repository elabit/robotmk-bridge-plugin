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

from cmk.rulesets.v1 import Title, Label
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DictElement,
    DictGroup,
    Dictionary,
    IECMagnitude,
    InputHint,
    Float,
    LevelDirection,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, Topic, HostAndItemCondition


def _parameter_form_vector_component(recv_byte=False, sent_byte=False):
    group_recv_event = DictGroup(title=Title('Number of received events per second'))
    group_sent_event = DictGroup(title=Title('Number of sent events per second'))
    elements = {
        'recv_event_upper': DictElement(
            parameter_form=SimpleLevels(
                title=Title('Upper limits'),
                level_direction=LevelDirection.UPPER,
                form_spec_template=Float(unit_symbol='event/s'),
                prefill_fixed_levels=InputHint(value=(1000, 5000)),
            ),
            required=False,
            group=group_recv_event,
        ),
        'recv_event_lower': DictElement(
            parameter_form=SimpleLevels(
                title=Title('Lower limits.'),
                level_direction=LevelDirection.LOWER,
                form_spec_template=Float(unit_symbol='event/s'),
                prefill_fixed_levels=InputHint(value=(0.1, 0)),
            ),
            required=False,
            group=group_recv_event,
        ),
        'sent_event_upper': DictElement(
            parameter_form=SimpleLevels(
                title=Title('Upper limits.'),
                level_direction=LevelDirection.UPPER,
                form_spec_template=Float(unit_symbol='event/s'),
                prefill_fixed_levels=InputHint(value=(1000, 5000)),
            ),
            required=False,
            group=group_sent_event,
        ),
        'sent_event_lower': DictElement(
            parameter_form=SimpleLevels(
                title=Title('Lower limits.'),
                level_direction=LevelDirection.LOWER,
                form_spec_template=Float(unit_symbol='event/s'),
                prefill_fixed_levels=InputHint(value=(0.1, 0)),
            ),
            required=False,
            group=group_sent_event,
        ),
    }
    if recv_byte:
        group_recv_byte = DictGroup(title=Title('Number of received bytes per second'))
        elements.update({
            'recv_byte_upper': DictElement(
                parameter_form=SimpleLevels(
                    title=Title('Upper limits'),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(
                        displayed_magnitudes=IECMagnitude,
                    ),
                    prefill_fixed_levels=InputHint(value=(1024**2, 1024**3)),
                ),
                required=False,
                group=group_recv_byte,
            ),
            'recv_byte_lower': DictElement(
                parameter_form=SimpleLevels(
                    title=Title('Lower limits'),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=DataSize(
                        displayed_magnitudes=IECMagnitude,
                    ),
                    prefill_fixed_levels=InputHint(value=(1024**2, 1024**3)),
                ),
                required=False,
                group=group_recv_byte,
            ),
        })
    if sent_byte:
        group_sent_byte = DictGroup(title=Title('Number of sent bytes per second'))
        elements.update({
            'sent_byte_upper': DictElement(
                parameter_form=SimpleLevels(
                    title=Title('Upper limits'),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(
                        label=Label('/s'),
                        displayed_magnitudes=IECMagnitude,
                    ),
                    prefill_fixed_levels=InputHint(value=(86400 * 1, 86400 * 2)),
                ),
                required=False,
                group=group_sent_byte,
            ),
            'sent_byte_lower': DictElement(
                parameter_form=SimpleLevels(
                    title=Title('Lower limits'),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=DataSize(
                        label=Label('/s'),
                        displayed_magnitudes=IECMagnitude,
                    ),
                    prefill_fixed_levels=InputHint(value=(86400 * 1, 86400 * 2)),
                ),
                required=False,
                group=group_sent_byte,
            ),
        })
    return Dictionary(
        elements=elements
    )


rule_spec_vector_source = CheckParameters(
    name='vector_source',
    topic=Topic.APPLICATIONS,
    parameter_form=lambda: _parameter_form_vector_component(recv_byte=True),
    title=Title('Vector Source'),
    condition=HostAndItemCondition(item_title=Title('Vector Source ID')),
)

rule_spec_vector_transform = CheckParameters(
    name='vector_transform',
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_vector_component,
    title=Title('Vector Transform'),
    condition=HostAndItemCondition(item_title=Title('Vector Transform ID')),
)

rule_spec_vector_sink = CheckParameters(
    name='vector_sink',
    topic=Topic.APPLICATIONS,
    parameter_form=lambda: _parameter_form_vector_component(sent_byte=True),
    title=Title('Vector Sink'),
    condition=HostAndItemCondition(item_title=Title('Vector Sink ID')),
)
