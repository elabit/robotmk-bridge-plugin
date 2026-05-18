#!/usr/bin/env python3
"""WATO Check Parameters rule for the Robotmk Bridge Plugin."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Float,
    InputHint,
    LevelDirection,
    SimpleLevels,
    SimpleLevelsConfigModel,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _missing_files_status() -> SingleChoice:
    return SingleChoice(
        title=Title("Missing files status"),
        help_text=Help(
            "The state to produce when a configured result file is absent. "
            "Set to OK if missing results should not trigger alerts, or CRIT if they "
            "represent critical test failures."
        ),
        elements=[
            SingleChoiceElement(name="ok", title=Title("OK")),
            SingleChoiceElement(name="warn", title=Title("WARN")),
            SingleChoiceElement(name="crit", title=Title("CRIT")),
            SingleChoiceElement(name="unknown", title=Title("UNKNOWN")),
        ],
        prefill=DefaultValue("warn"),
    )


def _conversion_time_levels() -> SimpleLevels:
    return SimpleLevels[float](
        form_spec_template=Float(
            title=Title("Conversion time threshold"),
            unit_symbol="s",
            help_text=Help("Time in seconds"),
        ),
        level_direction=LevelDirection.UPPER,
        title=Title("Result conversion time"),
        help_text=Help(
            "Thresholds for the conversion time metric. "
            "This measures how long the Bridge takes to convert test results into "
            "the Robotmk format. Exceeding these thresholds indicates performance issues "
            "with the handler or the result files."
        ),
        prefill_fixed_levels=InputHint((10.0, 30.0)),
    )


def parameter_form() -> Dictionary:
    return Dictionary(
        elements={
            "missing_files_status": DictElement[str](
                parameter_form=_missing_files_status(),
                required=False,
            ),
            "conversion_time_levels": DictElement[SimpleLevelsConfigModel[float]](
                parameter_form=_conversion_time_levels(),
                required=False,
            ),
        },
    )


rule_spec_robotmk_bridge_plugin_plan = CheckParameters(
    name="robotmk_bridge_plugin_plan",
    title=Title("Robotmk Bridge"),
    topic=Topic.APPLICATIONS,
    parameter_form=parameter_form,
    condition=HostAndItemCondition(item_title=Title("Plan")),
)
