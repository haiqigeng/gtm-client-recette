#!/usr/bin/env python3
"""Shared client-side evidence-layer applicability rules."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from acceptance_contract import expects_absence

CANONICAL_LAYERS = (
    "raw_api_call",
    "resolved_data_layer",
    "gtm_variable",
    "tag_configuration",
    "tag_firing",
    "tag_parameter",
    "consent_when_applicable",
    "source_signal_when_no_data_layer_push",
    "destination_request_when_applicable",
    "trigger_logic_when_applicable",
    "tag_sequence_when_applicable",
    "business_rules_when_declared",
    "sensitive_data_scan",
    "client_checks_when_applicable",
    "regression_when_baseline_provided",
    "container_context_when_applicable",
    "conditional_scenarios_when_applicable",
)

TAG_DELIVERY_TYPES = {"browser_request", "local_only"}

DESTINATION_EXPECTATION_FIELDS = (
    "vendor_family",
    "destination_id",
    "destination_event_name",
    "destination_id_parameter_path",
    "destination_event_parameter_path",
    "destination_parameter_path",
    "expected_endpoint_pattern",
    "expected_request_behavior",
)


def has_value(value: Any) -> bool:
    """Return whether a declarative field contains an applicable value."""
    return value not in (None, "")


def is_browser_sending_tag(expectation: dict[str, Any]) -> bool:
    """Return whether the requirement declares a browser-side destination send."""
    return expectation.get("tag_delivery") == "browser_request" or any(
        has_value(expectation.get(field)) for field in DESTINATION_EXPECTATION_FIELDS
    )


def requirement_layers(requirement: dict[str, Any]) -> set[str]:
    """Derive the applicable evidence layers for one normalized requirement."""
    if requirement.get("scope_status") == "OUT_OF_SCOPE":
        return set()
    expectation = requirement.get("expectation")
    if not isinstance(expectation, dict):
        return set()
    mechanism = expectation.get("source_mechanism", "data_layer_push")
    occurrence = expectation.get("expected_occurrence")
    occurrence_rule = occurrence.get("rule") if isinstance(occurrence, dict) else occurrence
    layers = {
        (
            "raw_api_call"
            if mechanism == "data_layer_push"
            else "source_signal_when_no_data_layer_push"
        )
    }
    applicability = (
        (
            "resolved_data_layer",
            expectation.get(
                "resolved_data_layer_applicable",
                mechanism in {"data_layer_push", "gtm_native_event", "gtm_auto_event"},
            ),
        ),
        ("gtm_variable", has_value(expectation.get("variable_name"))),
        ("tag_configuration", has_value(expectation.get("tag_name"))),
        ("tag_firing", has_value(expectation.get("tag_name"))),
        (
            "tag_parameter",
            has_value(expectation.get("tag_configuration_field")),
        ),
        (
            "consent_when_applicable",
            has_value(expectation.get("expected_consent_state"))
            or expectation.get("consent_contract") is not None,
        ),
        (
            "destination_request_when_applicable",
            is_browser_sending_tag(expectation),
        ),
        (
            "trigger_logic_when_applicable",
            expectation.get("trigger_contract") is not None,
        ),
        (
            "tag_sequence_when_applicable",
            expectation.get("sequence_contract") is not None,
        ),
        (
            "business_rules_when_declared",
            bool(expectation.get("business_rules")) and not expects_absence(expectation),
        ),
        ("sensitive_data_scan", bool(expectation.get("sensitive_data_policy"))),
        (
            "client_checks_when_applicable",
            bool(requirement.get("client_checks")),
        ),
        (
            "regression_when_baseline_provided",
            requirement.get("regression") is not None,
        ),
        (
            "conditional_scenarios_when_applicable",
            occurrence_rule in {"conditional", "non_deterministic"},
        ),
    )
    layers.update(layer for layer, applies in applicability if applies)
    return layers


def applicable_layers(
    requirements: Iterable[dict[str, Any]],
    *,
    container_count: int = 1,
) -> list[str]:
    """Return a stable, canonical layer list for a requirement collection."""
    layers: set[str] = set()
    for requirement in requirements:
        layers.update(requirement_layers(requirement))
    if container_count > 1:
        layers.add("container_context_when_applicable")
    return [layer for layer in CANONICAL_LAYERS if layer in layers]
