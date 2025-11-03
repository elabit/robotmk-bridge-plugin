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

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    DictGroup,
    Dictionary,
    DefaultValue,
    List,
    SingleChoice,
    SingleChoiceElement,
    InputHint,
    RegularExpression,
    MatchingScope,
)
from cmk.rulesets.v1.rule_specs import DiscoveryParameters, Topic


def _parameter_form_vector_component_discovery():
    group_type = DictGroup(title=Title('Discovery by component type'))
    return Dictionary(
        elements={
            'source': DictElement(
                parameter_form=SingleChoice(
                    title=Title('Discover Sources'),
                    elements=[
                        SingleChoiceElement(name='discover', title=Title("Discover")),
                        SingleChoiceElement(name='not_discover', title=Title("Do not discover")),
                    ],
                    prefill=DefaultValue('discover'),
                ),
                required=False,
                group=group_type,
            ),
            'transform': DictElement(
                parameter_form=SingleChoice(
                    title=Title('Discover Transforms'),
                    elements=[
                        SingleChoiceElement(name='discover', title=Title("Discover")),
                        SingleChoiceElement(name='not_discover', title=Title("Do not discover")),
                    ],
                    prefill=DefaultValue('discover'),
                ),
                required=False,
                group=group_type,
            ),
            'sinks': DictElement(
                parameter_form=SingleChoice(
                    title=Title('Discover Sinks'),
                    elements=[
                        SingleChoiceElement(name='discover', title=Title("Discover")),
                        SingleChoiceElement(name='not_discover', title=Title("Do not discover")),
                    ],
                    prefill=DefaultValue('discover'),
                ),
                required=False,
                group=group_type,
            ),
            'ignore': DictElement(
                parameter_form=List(
                    title=Title('Componenty to ignore'),
                    element_template=Dictionary(
                        elements={
                            'component': DictElement(
                                parameter_form=SingleChoice(
                                    elements=[
                                        SingleChoiceElement(name='any', title=Title("Any")),
                                        SingleChoiceElement(name='source', title=Title("Source")),
                                        SingleChoiceElement(name='transform', title=Title("Transform")),
                                        SingleChoiceElement(name='sink', title=Title("Sink")),
                                    ],
                                    prefill=DefaultValue('any'),
                                ),
                                required=True,
                            ),
                            'name': DictElement(
                                parameter_form=RegularExpression(
                                    predefined_help_text=MatchingScope.PREFIX,
                                    prefill=InputHint('Component ID')
                                ),
                                required=True
                            ),
                        }
                    ),
                ),
                required=True,
            ),
        }
    )


rule_spec_vector_component_discovery = DiscoveryParameters(
    title=Title('Vector Source, Transform, Sink discovery'),
    name='vector_component',
    parameter_form=_parameter_form_vector_component_discovery,
    topic=Topic.APPLICATIONS,
)
