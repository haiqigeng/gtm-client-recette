#!/usr/bin/env python3
"""Deterministic client-side evidence-layer and tag-scope policy."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from acceptance_contract import expects_absence

CANONICAL_LAYERS = (
    "action_boundary",
    "raw_api_call",
    "resolved_data_layer",
    "concerned_tag_inventory",
    "gtm_variable",
    "tag_configuration",
    "tag_firing",
    "tag_parameter",
    "destination_request_when_applicable",
    "sensitive_data_scan",
    "consent_when_applicable",
    "source_signal_when_no_data_layer_push",
    "trigger_logic_when_applicable",
    "tag_sequence_when_applicable",
    "business_rules_when_declared",
    "client_checks_when_applicable",
    "regression_when_baseline_provided",
    "container_context_when_applicable",
    "conditional_scenarios_when_applicable",
)

TAG_RESULT_LAYERS = (
    "gtm_variable",
    "tag_configuration",
    "tag_firing",
    "tag_parameter",
    "destination_request_when_applicable",
    "consent_when_applicable",
    "trigger_logic_when_applicable",
    "tag_sequence_when_applicable",
)

TAG_SCOPE_MODES = {
    "analytics_only",
    "all_relevant_client_side_tags",
    "explicit_tag_set",
}
TAG_CATEGORIES = {"analytics", "media", "other_client_side"}
TAG_SCOPE_STATUSES = {"IN_SCOPE", "OUT_OF_SCOPE"}
TAG_DELIVERY_TYPES = {"browser_request", "local_only"}
LAYER_APPLICABILITY_MODES = {"MANDATORY", "CONDITIONAL"}

ANALYTICS_VENDOR_FAMILIES = {
    "ga4",
    "piano",
    "adobe_analytics",
    "matomo",
    "piwik_pro",
    "snowplow",
    "realytics",
}
ANALYTICS_VENDOR_ALIASES = {
    "google_analytics": "ga4",
    "google_analytics_4": "ga4",
    "piano_analytics": "piano",
    "at_internet": "piano",
    "adobe": "adobe_analytics",
    "adobe_analytics": "adobe_analytics",
    "matomo_analytics": "matomo",
    "piwikpro": "piwik_pro",
    "piwik_pro_analytics_suite": "piwik_pro",
    "snowplow_analytics": "snowplow",
    "realytics_io": "realytics",
}
MEDIA_VENDOR_FAMILIES = {
    "google_ads",
    "floodlight",
    "meta",
    "linkedin",
    "tiktok",
    "pinterest",
    "microsoft_ads",
    "x_ads",
}

GA4_ECOMMERCE_EVENTS = {
    "view_promotion",
    "select_promotion",
    "view_item_list",
    "select_item",
    "view_item",
    "add_to_wishlist",
    "add_to_cart",
    "remove_from_cart",
    "view_cart",
    "begin_checkout",
    "add_shipping_info",
    "add_payment_info",
    "purchase",
    "refund",
}

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

CONDITIONAL_PREDICATES = {
    "consent_when_applicable": (
        "A concerned tag has consent settings, the acceptance contract declares consent "
        "behaviour, the event state is non-granted, or behaviour differs by consent."
    ),
    "source_signal_when_no_data_layer_push": (
        "The source mechanism intentionally has no custom dataLayer.push."
    ),
    "trigger_logic_when_applicable": (
        "A tag unexpectedly fires, does not fire, fires the wrong count, or an explicit "
        "trigger/exception rule is under acceptance."
    ),
    "tag_sequence_when_applicable": (
        "GTM sequencing is configured or the acceptance contract declares an event/tag order."
    ),
    "business_rules_when_declared": (
        "The event is ecommerce or a cross-field/business rule is declared."
    ),
    "client_checks_when_applicable": (
        "The site or tag uses a detected/declared SPA, iframe, cross-domain, responsive, "
        "Custom JavaScript, linker, cookie, dependency, or related client-side feature."
    ),
    "regression_when_baseline_provided": "A prior accepted baseline is supplied.",
    "container_context_when_applicable": "More than one client-side container is present.",
    "conditional_scenarios_when_applicable": (
        "A finite material branch, responsive variant, personalization, or conditional "
        "occurrence is present."
    ),
}


def has_value(value: Any) -> bool:
    """Return whether a declarative field contains an applicable value."""
    return value not in (None, "")


def is_browser_sending_tag(expectation: dict[str, Any]) -> bool:
    """Return whether a plan row explicitly declares a browser-side destination send."""
    return expectation.get("tag_delivery") == "browser_request" or any(
        has_value(expectation.get(field)) for field in DESTINATION_EXPECTATION_FIELDS
    )


def inferred_tag_category(tag: dict[str, Any]) -> str | None:
    """Infer an unambiguous analytics/media category from direct tag metadata."""
    vendor_family = re.sub(
        r"[^a-z0-9]+", "_", str(tag.get("vendor_family", "")).strip().lower()
    ).strip("_")
    vendor_family = ANALYTICS_VENDOR_ALIASES.get(vendor_family, vendor_family)
    if vendor_family in ANALYTICS_VENDOR_FAMILIES:
        return "analytics"
    if vendor_family in MEDIA_VENDOR_FAMILIES:
        return "media"
    template = str(tag.get("template_type", "")).strip().lower()
    if any(
        token in template
        for token in (
            "ga4",
            "google analytics",
            "piano analytics",
            "at internet",
            "adobe analytics",
            "adobe experience cloud",
            "matomo",
            "piwik pro",
            "snowplow",
            "realytics",
        )
    ):
        return "analytics"
    if any(
        token in template
        for token in (
            "google ads",
            "floodlight",
            "meta pixel",
            "facebook pixel",
            "linkedin insight",
            "tiktok pixel",
            "pinterest tag",
            "microsoft advertising",
            "uet",
            "x pixel",
            "twitter pixel",
        )
    ):
        return "media"
    return None


def normalize_tag_scope(value: Any) -> dict[str, Any]:
    """Return a normalized run-level tag-scope contract."""
    if isinstance(value, str):
        value = {"mode": value}
    scope = dict(value) if isinstance(value, dict) else {}
    scope.setdefault("mode", "analytics_only")
    scope.setdefault("explicit_tag_names", [])
    scope.setdefault("include_plan_declared_media", True)
    scope.setdefault(
        "reason",
        "Analytics tags are the default; declared media tags remain in scope and all other "
        "detected client-side tags remain visible as out of scope.",
    )
    return scope


def declared_tag_contracts(requirements: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract exact plan-declared tag/destination contracts without using them as layer policy."""
    contracts: list[dict[str, Any]] = []
    for requirement in requirements:
        expectation = requirement.get("expectation")
        if not isinstance(expectation, dict):
            continue
        if not any(
            has_value(expectation.get(field))
            for field in ("tag_name", "vendor_family", "destination_id")
        ):
            continue
        contracts.append(
            {
                "tag_name": expectation.get("tag_name"),
                "vendor_family": expectation.get("vendor_family"),
                "destination_id": expectation.get("destination_id"),
            }
        )
    return contracts


def tag_matches_declared_contract(
    tag: dict[str, Any],
    contracts: Iterable[dict[str, Any]],
) -> bool:
    """Return whether a discovered tag matches a plan-declared media/tag contract."""
    for contract in contracts:
        comparable = [
            ("tag_name", "tag_name"),
            ("vendor_family", "vendor_family"),
            ("destination_id", "destination_id"),
        ]
        declared = [
            (tag_key, contract_key)
            for tag_key, contract_key in comparable
            if has_value(contract.get(contract_key))
        ]
        if declared and all(
            tag.get(tag_key) == contract.get(contract_key) for tag_key, contract_key in declared
        ):
            return True
    return False


def tag_scope_decision(
    tag: dict[str, Any],
    tag_scope: dict[str, Any] | str | None,
    contracts: Iterable[dict[str, Any]] = (),
) -> tuple[str, str]:
    """Classify one discovered tag deterministically and return status plus reason."""
    scope = normalize_tag_scope(tag_scope)
    mode = scope["mode"]
    name = str(tag.get("tag_name", "")).strip()
    category = inferred_tag_category(tag) or tag.get("tag_category")
    explicit_names = {str(value).strip() for value in scope.get("explicit_tag_names", [])}
    declared = tag_matches_declared_contract(tag, contracts)
    if mode == "all_relevant_client_side_tags":
        return "IN_SCOPE", "User requested every relevant client-side tag."
    if mode == "explicit_tag_set":
        if name in explicit_names:
            return "IN_SCOPE", "Tag is in the user-declared fixed tag set."
        return "OUT_OF_SCOPE", "Detected tag is outside the user-declared fixed tag set."
    if category == "analytics":
        return "IN_SCOPE", "Analytics tags are in scope by default."
    if declared and scope.get("include_plan_declared_media") is True:
        return "IN_SCOPE", "Non-analytics tag is explicitly declared by the acceptance plan."
    return (
        "OUT_OF_SCOPE",
        "Detected client-side tag is outside the analytics-only default and is retained visibly.",
    )


def _known_conditional_layers(
    requirements: list[dict[str, Any]],
    *,
    container_count: int,
    tag_inventory: Iterable[dict[str, Any]],
) -> dict[str, str]:
    expectations = [
        row.get("expectation", {})
        for row in requirements
        if isinstance(row.get("expectation"), dict)
    ]
    known: dict[str, str] = {}
    if any(
        has_value(row.get("expected_consent_state")) or row.get("consent_contract") is not None
        for row in expectations
    ) or any(
        tag.get("scope_status") == "IN_SCOPE" and tag.get("consent_required") is True
        for tag in tag_inventory
    ):
        known["consent_when_applicable"] = "Consent acceptance/configuration is explicitly present."
    if any(
        row.get("source_mechanism", "data_layer_push") != "data_layer_push" for row in expectations
    ):
        known["source_signal_when_no_data_layer_push"] = (
            "A non-dataLayer source mechanism is declared."
        )
    if any(row.get("trigger_contract") is not None for row in expectations):
        known["trigger_logic_when_applicable"] = (
            "An explicit trigger/exception contract is present."
        )
    if any(row.get("sequence_contract") is not None for row in expectations):
        known["tag_sequence_when_applicable"] = "An explicit sequence contract is present."
    if any(
        not expects_absence(row)
        and (
            bool(row.get("business_rules"))
            or str(row.get("event_name", "")) in GA4_ECOMMERCE_EVENTS
        )
        for row in expectations
    ):
        known["business_rules_when_declared"] = "Ecommerce or declared cross-field rules apply."
    if any(row.get("client_checks") for row in requirements):
        known["client_checks_when_applicable"] = "A detected/declared client-side check applies."
    if any(row.get("regression") is not None for row in requirements):
        known["regression_when_baseline_provided"] = "A prior-run baseline is attached."
    if container_count > 1:
        known["container_context_when_applicable"] = "Multiple client-side containers are present."
    if any(
        (
            (row.get("expected_occurrence") or {}).get("rule")
            if isinstance(row.get("expected_occurrence"), dict)
            else row.get("expected_occurrence")
        )
        in {"conditional", "non_deterministic"}
        for row in expectations
    ):
        known["conditional_scenarios_when_applicable"] = "A conditional occurrence is declared."
    return known


def layer_applicability(
    requirements: Iterable[dict[str, Any]],
    *,
    container_count: int = 1,
    tag_inventory: Iterable[dict[str, Any]] = (),
    activated_conditions: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    """Build the complete, pre-action applicability card for one event/case.

    The tracking plan supplies acceptance values and sometimes a journey. It never
    selects the evidence layers. A dataLayer source activates the complete core chain.
    Every other canonical layer remains visible with its explicit activation predicate.
    """
    rows = [row for row in requirements if row.get("scope_status") != "OUT_OF_SCOPE"]
    inventories = list(tag_inventory)
    mechanisms = {
        str((row.get("expectation") or {}).get("source_mechanism", "data_layer_push"))
        for row in rows
        if isinstance(row.get("expectation"), dict)
    }
    expectations = [
        row.get("expectation", {}) for row in rows if isinstance(row.get("expectation"), dict)
    ]
    has_data_layer = "data_layer_push" in mechanisms
    in_scope_tags = [tag for tag in inventories if tag.get("scope_status") == "IN_SCOPE"]
    declared_tag_expectations = [
        row.get("expectation", {})
        for row in rows
        if isinstance(row.get("expectation"), dict)
        and has_value(row["expectation"].get("tag_name"))
    ]
    all_local_only = (
        bool(in_scope_tags)
        and all(tag.get("tag_delivery") == "local_only" for tag in in_scope_tags)
    ) or (
        not inventories
        and bool(declared_tag_expectations)
        and all(row.get("tag_delivery") == "local_only" for row in declared_tag_expectations)
    )

    mandatory = {"action_boundary", "concerned_tag_inventory", "sensitive_data_scan"}
    reasons = {
        "action_boundary": "Every verdict must be bound to one completed website action window.",
        "concerned_tag_inventory": "Every event must expose its complete in-scope and excluded tag inventory.",
        "sensitive_data_scan": "Every captured payload/runtime/request chain is scanned for sensitive data.",
    }
    if has_data_layer:
        mandatory.update(
            {
                "raw_api_call",
                "resolved_data_layer",
                "gtm_variable",
                "tag_configuration",
                "tag_firing",
                "tag_parameter",
            }
        )
        reasons.update(
            {
                "raw_api_call": "A planned dataLayer event requires its exact live API Call payload.",
                "resolved_data_layer": "A planned dataLayer event requires the resolved event-state comparison.",
                "gtm_variable": "Variables consumed by in-scope tags must be resolved or positively shown unused.",
                "tag_configuration": "Every in-scope tag requires configuration evidence.",
                "tag_firing": "Every in-scope tag requires firing/non-firing and count evidence.",
                "tag_parameter": "Every in-scope tag requires exact runtime parameter evidence.",
            }
        )
        if not all_local_only:
            mandatory.add("destination_request_when_applicable")
            reasons["destination_request_when_applicable"] = (
                "Browser-sending in-scope tags require a matching browser request; local-only "
                "classification requires positive configuration proof."
            )
    elif mechanisms:
        mandatory.add("source_signal_when_no_data_layer_push")
        reasons["source_signal_when_no_data_layer_push"] = (
            "The accepted source mechanism is not a custom dataLayer.push."
        )
        if any(is_browser_sending_tag(row) for row in expectations):
            mandatory.add("destination_request_when_applicable")
            reasons["destination_request_when_applicable"] = (
                "The accepted non-dataLayer source declares a browser-side destination send."
            )

    known = _known_conditional_layers(
        rows,
        container_count=container_count,
        tag_inventory=inventories,
    )
    for layer, reason in (activated_conditions or {}).items():
        if layer not in CONDITIONAL_PREDICATES:
            raise ValueError(f"Unsupported conditional layer activation: {layer}")
        if not str(reason).strip():
            raise ValueError(f"Conditional activation for {layer} requires a reason")
        known[layer] = str(reason).strip()
    mandatory.update(known)
    reasons.update(known)

    output: list[dict[str, str]] = []
    for layer in CANONICAL_LAYERS:
        if layer in mandatory:
            output.append(
                {
                    "layer": layer,
                    "mode": "MANDATORY",
                    "predicate": "always_for_this_case",
                    "reason": reasons[layer],
                }
            )
        else:
            output.append(
                {
                    "layer": layer,
                    "mode": "CONDITIONAL",
                    "predicate": CONDITIONAL_PREDICATES.get(
                        layer,
                        "The layer becomes relevant from observed runtime or tag configuration.",
                    ),
                    "reason": "Predicate must be resolved after the action; omission is forbidden.",
                }
            )
    return output


def applicable_layers(
    requirements: Iterable[dict[str, Any]],
    *,
    container_count: int = 1,
    tag_inventory: Iterable[dict[str, Any]] = (),
    activated_conditions: dict[str, str] | None = None,
) -> list[str]:
    """Return mandatory layers in stable canonical order."""
    return [
        row["layer"]
        for row in layer_applicability(
            requirements,
            container_count=container_count,
            tag_inventory=tag_inventory,
            activated_conditions=activated_conditions,
        )
        if row["mode"] == "MANDATORY"
    ]
