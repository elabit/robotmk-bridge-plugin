#!/usr/bin/env python3
"""WATO Bakery rule for the Robotmk Bridge Plugin. """

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    List,
    String,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _handler_params_junit() -> FixedValue:
    return FixedValue(
        value=None,
        title=Title("JUnit (no additional parameters)"),
    )


def _handler_params_gatling() -> FixedValue:
    return FixedValue(
        value=None,
        title=Title("Gatling (no additional parameters)"),
    )


def _handler_params_zaproxy() -> Dictionary:
    return Dictionary(
        title=Title("OWASP ZAP parameters"),
        elements={
            "accepted_risk_level": DictElement(
                parameter_form=Integer(
                    title=Title("Accepted risk level"),
                    help_text=Help(
                        "Minimum risk level of alerts to include. "
                        "0=Info, 1=Low, 2=Medium, 3=High. "
                        "Alerts below this level are ignored."
                    ),
                    prefill=DefaultValue(2),
                ),
                required=False,
            ),
            "required_confidence_level": DictElement(
                parameter_form=Integer(
                    title=Title("Required confidence level"),
                    help_text=Help(
                        "Minimum confidence level of alerts to include. "
                        "1=Low, 2=Medium, 3=High. "
                        "Alerts below this confidence are ignored."
                    ),
                    prefill=DefaultValue(2),
                ),
                required=False,
            ),
        },
    )


def _handler_cascade() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Result Handler"),
        help_text=Help(
            "Select the Robotmk Bridge result handler that matches the test tool producing the result files. "
            "See <a href=https://github.com/elabit/robotmk-bridge#features>Robotmk Bridge</a> for a list of all supported result formats." 
        ),
        elements=[
            CascadingSingleChoiceElement(
                name="junit",
                title=Title("JUnit"),
                parameter_form=_handler_params_junit(),
            ),
            CascadingSingleChoiceElement(
                name="gatling",
                title=Title("Gatling"),
                parameter_form=_handler_params_gatling(),
            ),
            CascadingSingleChoiceElement(
                name="zaproxy",
                title=Title("OWASP ZAP (Zed Attack Proxy)"),
                parameter_form=_handler_params_zaproxy(),
            ),
        ],
        prefill=DefaultValue("junit"),
    )


def _source_cascade() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Source"),
        help_text=Help("Specify where the test result files are located on the monitored system."),
        elements=[
            CascadingSingleChoiceElement(
                name="single_file",
                title=Title("Single file"),
                parameter_form=String(
                    title=Title("Path to result file"),
                    help_text=Help(
                        "Absolute path to one single specific test result file on the monitored system. This file gets read every time."
                    ),
                ),
            ),
            CascadingSingleChoiceElement(
                name="directory_newest",
                title=Title("Newest file in directory"),
                parameter_form=String(
                    title=Title("Path to directory"),
                    help_text=Help(
                        "Absolute path to a directory on the monitored system where test result files are written to. "
                        "Only the most recently modified file in this directory will be processed."
                    ),
                ),
            ),
            CascadingSingleChoiceElement(
                name="directory_all",
                title=Title("All files in directory"),
                parameter_form=String(
                    title=Title("Path to directory"),
                    help_text=Help(
                        "Absolute path to a directory on the monitored system where test result files are written to. "
                        "<b>All</b> files in this directory will be processed."
                    ),
                ),
            ),
        ],
        prefill=DefaultValue("single_file"),
    )


def _plan_element() -> Dictionary:
    return Dictionary(
        title=Title("Plan"),
        elements={
            "plan_name": DictElement(
                parameter_form=String(
                    title=Title("Plan name"),
                    help_text=Help(
                        "Unique identifier for this plan. Used as the Robotmk plan ID."
                    ),
                ),
                required=True,
            ),
            "handler": DictElement(
                parameter_form=_handler_cascade(),
                required=True,
            ),
            "application": DictElement(
                parameter_form=String(
                    title=Title("Application"),
                    help_text=Help(
                        "Application name shown in the Checkmk service description."
                    ),
                ),
                required=True,
            ),
            "source": DictElement(
                parameter_form=_source_cascade(),
                required=True,
            ),
        },
    )


def _rule_form() -> Dictionary:
    return Dictionary(
        elements={
            "plans": DictElement(
                parameter_form=List(
                    title=Title("Plans"),
                    help_text=Help(
                        "Each plan defines one test result source to be converted into a "
                        "Robotmk result and monitored by Checkmk."
                    ),
                    element_template=_plan_element(),
                    add_element_label=Label("Add plan"),
                    remove_element_label=Label("Remove plan"),
                    no_element_label=Label("No plans configured"),
                ),
                required=True,
            ),
        },
    )


rule_spec_robotmk_bridge_plugin = AgentConfig(
    title=Title("Robotmk Bridge"),
    topic=Topic.GENERAL,
    parameter_form=_rule_form,
    name="robotmk_bridge_plugin",
    help_text=Help(
        "The Robotmk Bridge Plugin integrates any test automation tool into Robotmk "
        "and Checkmk by converting native result files into the Robotmk JSON format."
    ),
)